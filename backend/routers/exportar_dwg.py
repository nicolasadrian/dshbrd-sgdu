import os
import sys
import time
import math
import argparse
import warnings
import ezdxf
from ezdxf.enums import TextEntityAlignment
from dotenv import load_dotenv
import geopandas as gpd
import pandas as pd
from sqlalchemy import text
from shapely.geometry import LineString, MultiLineString
import fiona

# Suppress warnings to keep terminal output clean
warnings.filterwarnings("ignore")

# Set environment variable globally for GDAL
os.environ["DXF_WRITE_HATCH"] = "FALSE"

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
try:
    from src.db import get_engine
except ImportError:
    try:
        from backend.database import geo_engine as get_engine
    except ImportError:
        from database import geo_engine as get_engine

FONTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fonts"))
if os.path.exists(FONTS_DIR) and FONTS_DIR not in ezdxf.options.support_dirs:
    ezdxf.options.support_dirs.append(FONTS_DIR)

def extract_lines(geom):
    """
    Recursively extracts all boundary outlines from Polygons, MultiPolygons,
    and GeometryCollections, returning a flat list of LineStrings.
    """
    if geom is None or geom.is_empty:
        return []
    
    gtype = geom.geom_type
    
    if gtype == 'Polygon':
        lines = [LineString(geom.exterior.coords)]
        for hole in geom.interiors:
            lines.append(LineString(hole.coords))
        return lines
        
    elif gtype == 'MultiPolygon':
        lines = []
        for poly in geom.geoms:
            lines.extend(extract_lines(poly))
        return lines
        
    elif gtype == 'LineString':
        return [geom]
        
    elif gtype == 'MultiLineString':
        return list(geom.geoms)
        
    elif gtype == 'GeometryCollection':
        lines = []
        for sub_geom in geom.geoms:
            lines.extend(extract_lines(sub_geom))
        return lines
        
    return []

def polygon_to_boundary(geom):
    """
    Uses extract_lines to decompose any complex geometry into a flat list of lines,
    and wraps them in a homogeneous MultiLineString.
    """
    lines = extract_lines(geom)
    if not lines:
        return None
    return MultiLineString(lines)

def exportar_seccion(engine, seccion_val, dxf_base_dir):
    t_sec_start = time.time()
    
    # Normalizar nombre de carpeta de la sección (ej. '001')
    try:
        sec_folder = f"{int(seccion_val):03d}"
    except ValueError:
        sec_folder = str(seccion_val).strip().zfill(3)
        
    print(f"\n==========================================")
    print(f"PROCESANDO SECCIÓN {sec_folder}...")
    print(f"==========================================")
    
    # Escapar la sección para SQL seguro
    sec_escaped = seccion_val.replace("'", "''")
    
    # 1. Cargar Manzanas de la sección con ST_Transform nativo en PostGIS
    query_manzanas = f"""
        SELECT ST_Transform(ST_SetSRID(geom, CASE WHEN ST_SRID(geom) = 0 THEN 3857 ELSE ST_SRID(geom) END), 22186) AS geom, seccion, manzana 
        FROM public.manzanas 
        WHERE (TRIM(seccion) = '{sec_escaped}' OR LPAD(TRIM(seccion), 3, '0') = '{sec_escaped}') 
          AND geom IS NOT NULL
    """
    try:
        gdf_manzanas = gpd.read_postgis(query_manzanas, con=engine, geom_col="geom", crs="EPSG:22186")
        if gdf_manzanas.empty:
            print(f"No se encontraron manzanas para la sección {seccion_val}.")
            return
    except Exception as e:
        print(f"Error al cargar manzanas de sección {seccion_val}: {e}")
        return

    # 2. Cargar Parcelas de la sección (con CUR y Unidades de Edificabilidad)
    query_parcelas = f"""
        SELECT geom, smp, seccion, manzana, cur_1, uni_edif_1, uni_edif_2, uni_edif_3, uni_edif_4 
        FROM public.cur_parcelas_ok 
        WHERE (TRIM(seccion) = '{sec_escaped}' OR LPAD(TRIM(seccion), 3, '0') = '{sec_escaped}') AND geom IS NOT NULL
    """
    try:
        gdf_parcelas = gpd.read_postgis(query_parcelas, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception as e:
        print(f"Error al cargar parcelas de sección {seccion_val}: {e}")
        gdf_parcelas = gpd.GeoDataFrame()

    # 2b. Cargar Calles con ST_Transform nativo en PostGIS
    if not gdf_manzanas.empty:
        sec_xmin, sec_ymin, sec_xmax, sec_ymax = gdf_manzanas.total_bounds
        query_calles = f"""
            SELECT c.nomoficial, ST_Transform(ST_SetSRID(c.geom, CASE WHEN ST_SRID(c.geom) = 0 THEN 22186 ELSE ST_SRID(c.geom) END), 22186) AS geom 
            FROM public.calles c 
            WHERE c.geom IS NOT NULL 
              AND c.nomoficial IS NOT NULL 
              AND TRIM(c.nomoficial) <> ''
              AND ST_Transform(ST_SetSRID(c.geom, CASE WHEN ST_SRID(c.geom) = 0 THEN 22186 ELSE ST_SRID(c.geom) END), 22186) && ST_MakeEnvelope({sec_xmin - 150}, {sec_ymin - 150}, {sec_xmax + 150}, {sec_ymax + 150}, 22186)
        """
        try:
            gdf_calles = gpd.read_postgis(query_calles, con=engine, geom_col="geom", crs="EPSG:22186")
        except Exception:
            try:
                fallback_q = f"""
                    SELECT c.nomoficial, ST_Transform(ST_SetSRID(c.geom, CASE WHEN ST_SRID(c.geom) = 0 THEN 22186 ELSE ST_SRID(c.geom) END), 22186) AS geom 
                    FROM calles c 
                    WHERE c.geom IS NOT NULL 
                      AND c.nomoficial IS NOT NULL 
                      AND TRIM(c.nomoficial) <> ''
                      AND ST_Transform(ST_SetSRID(c.geom, CASE WHEN ST_SRID(c.geom) = 0 THEN 22186 ELSE ST_SRID(c.geom) END), 22186) && ST_MakeEnvelope({sec_xmin - 150}, {sec_ymin - 150}, {sec_xmax + 150}, {sec_ymax + 150}, 22186)
                """
                gdf_calles = gpd.read_postgis(fallback_q, con=engine, geom_col="geom", crs="EPSG:22186")
            except Exception:
                gdf_calles = gpd.GeoDataFrame()
    else:
        gdf_calles = gpd.GeoDataFrame()

    # 3. Cargar LFI de la sección
    query_lfi = f"SELECT geom, seccion, manzana FROM mdr_lineadefrenteinterno WHERE seccion = '{sec_escaped}' AND geom IS NOT NULL"
    try:
        gdf_lfi = gpd.read_postgis(query_lfi, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception as e:
        gdf_lfi = gpd.GeoDataFrame()

    # 4. Cargar LIB de la sección
    query_lib = f"SELECT geom, seccion, manzana FROM mdr_lineadebasamento WHERE seccion = '{sec_escaped}' AND geom IS NOT NULL"
    try:
        gdf_lib = gpd.read_postgis(query_lib, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception as e:
        gdf_lib = gpd.GeoDataFrame()

    # 5. Cargar Troneras de la sección
    query_troneras = f"SELECT geom, seccion, manzana, id_tronera, sm, comuna, irregular FROM mdr_troneras WHERE seccion = '{sec_escaped}' AND geom IS NOT NULL"
    try:
        gdf_troneras = gpd.read_postgis(query_troneras, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception as e:
        gdf_troneras = gpd.GeoDataFrame()

    # 6. Cargar Banda Mínima de la sección
    query_bm = f"""
        SELECT bm.geom, bm.smp 
        FROM mdr_banda_minima bm 
        INNER JOIN cur_parcelas_ok p ON bm.smp = p.smp 
        WHERE p.seccion = '{sec_escaped}' AND bm.geom IS NOT NULL
    """
    try:
        gdf_bm = gpd.read_postgis(query_bm, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception as e:
        gdf_bm = gpd.GeoDataFrame()

    # 7. Cargar Línea de Fondo (LDF) de la sección
    query_ldf = f"""
        SELECT ldf.geom, ldf.smp 
        FROM mdr_ldf_parc ldf 
        INNER JOIN cur_parcelas_ok p ON ldf.smp = p.smp 
        WHERE p.seccion = '{sec_escaped}' AND ldf.geom IS NOT NULL
    """
    try:
        gdf_ldf = gpd.read_postgis(query_ldf, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception as e:
        gdf_ldf = gpd.GeoDataFrame()

    # 8. Cargar Tejido de la sección (sec en tejido es VARCHAR, normalizado con LPAD)
    query_tejido = f"SELECT geom, smp, LPAD(sec, 3, '0') AS seccion, man AS manzana, altura FROM tejido WHERE LPAD(sec, 3, '0') = '{sec_escaped}' AND geom IS NOT NULL"
    try:
        gdf_tejido = gpd.read_postgis(query_tejido, con=engine, geom_col="geom", crs="EPSG:3857")
        if not gdf_tejido.empty:
            gdf_tejido = gdf_tejido.to_crs("EPSG:22186")
    except Exception as e:
        gdf_tejido = gpd.GeoDataFrame()

    # 9. Cargar Tejido Consolidado de la sección
    query_tc = f"""
        SELECT tc.geometry AS geom, tc.smp 
        FROM mdr_tejidoconsolidado tc 
        INNER JOIN cur_parcelas_ok p ON tc.smp = p.smp 
        WHERE p.seccion = '{sec_escaped}' AND tc.geometry IS NOT NULL
    """
    try:
        gdf_consolidado = gpd.read_postgis(query_tc, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception as e:
        gdf_consolidado = gpd.GeoDataFrame()

    # 10. Cargar Tejido Para Irregular de la sección
    query_tpi = f"""
        SELECT tpi.geometry AS geom, tpi.smp 
        FROM mdr_tejidoparairregular tpi 
        INNER JOIN cur_parcelas_ok p ON tpi.smp = p.smp 
        WHERE p.seccion = '{sec_escaped}' AND tpi.geometry IS NOT NULL
    """
    try:
        gdf_tejido_irreg = gpd.read_postgis(query_tpi, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception as e:
        gdf_tejido_irreg = gpd.GeoDataFrame()

    # Configurar directorio de la sección
    seccion_dir = os.path.join(dxf_base_dir, sec_folder)
    os.makedirs(seccion_dir, exist_ok=True)
    
    # Agrupar manzanas por manzana catastral
    grouped_manzanas = gdf_manzanas.groupby('manzana')
    
    for m_val, group_manzana in grouped_manzanas:
        if not m_val:
            continue
            
        m_layers = {}
        
        # Manzana (convertida a contorno de líneas)
        m_boundary = group_manzana.copy()
        m_boundary['geometry'] = m_boundary.geometry.apply(polygon_to_boundary)
        m_layers['manzanas'] = m_boundary
        
        # Parcelas (convertidas a contorno de líneas) y recolección de etiquetas de parcelas
        m_parcelas_data = []
        if not gdf_parcelas.empty:
            m_parcelas = gdf_parcelas[gdf_parcelas['manzana'] == m_val].copy()
            if not m_parcelas.empty:
                for idx, row in m_parcelas.iterrows():
                    geom = row['geom']
                    if geom and not geom.is_empty:
                        centroid = geom.centroid
                        cur = row.get('cur_1')
                        unis = [row.get(f'uni_edif_{i}') for i in range(1, 5)]
                        unis_clean = [float(u) for u in unis if u is not None and str(u) != 'nan' and float(u) > 0]
                        
                        labels = []
                        if cur and str(cur) != 'nan':
                            labels.append(str(cur))
                        if unis_clean:
                            labels.append(" / ".join(f"{u:.1f}m" for u in unis_clean))
                        
                        if labels:
                            m_parcelas_data.append(((centroid.x, centroid.y), labels))
                            
                m_parcelas['geometry'] = m_parcelas.geometry.apply(polygon_to_boundary)
                m_layers['parcelas'] = m_parcelas

        # Calles circundantes (posicionadas exactamente frente a la manzana con su ángulo de orientación)
        m_calles_data = []
        if not gdf_calles.empty and not group_manzana.empty:
            mza_geom = group_manzana.geometry.iloc[0]
            calles_bbox = gdf_calles[gdf_calles.intersects(mza_geom.buffer(100))].copy()
            if not calles_bbox.empty:
                calles_bbox['dist'] = calles_bbox.geometry.apply(lambda g: g.distance(mza_geom))
                calles_frentistas = calles_bbox[calles_bbox['dist'] <= 60]
                if not calles_frentistas.empty:
                    grouped = calles_frentistas.groupby('nomoficial')
                    for nom, group in grouped:
                        if not nom or str(nom) == 'nan':
                            continue
                        group_sorted = group.sort_values(by='dist')
                        best_segment = group_sorted.iloc[0]['geom']
                        if best_segment and not best_segment.is_empty:
                            nearest_pt = best_segment.interpolate(best_segment.project(mza_geom.centroid))
                            proj_d = best_segment.project(nearest_pt)
                            p1 = best_segment.interpolate(max(0, proj_d - 1.0))
                            p2 = best_segment.interpolate(min(best_segment.length, proj_d + 1.0))
                            angle = math.degrees(math.atan2(p2.y - p1.y, p2.x - p1.x))
                            if angle > 90:
                                angle -= 180
                            elif angle < -90:
                                angle += 180
                            m_calles_data.append(((nearest_pt.x, nearest_pt.y), str(nom).strip().upper(), angle))
                
        # LFI
        if not gdf_lfi.empty:
            m_lfi = gdf_lfi[gdf_lfi['manzana'] == m_val]
            if not m_lfi.empty:
                m_layers['lfi'] = m_lfi
                
        # LIB
        if not gdf_lib.empty:
            m_lib = gdf_lib[gdf_lib['manzana'] == m_val]
            if not m_lib.empty:
                m_layers['lib'] = m_lib
                
        # Troneras
        if not gdf_troneras.empty:
            m_troneras = gdf_troneras[gdf_troneras['manzana'] == m_val]
            if not m_troneras.empty:
                m_troneras_si = m_troneras[m_troneras['irregular'] == 'NO'].copy()
                if not m_troneras_si.empty:
                    m_troneras_si['geometry'] = m_troneras_si.geometry.apply(polygon_to_boundary)
                    m_layers['Tronera SI'] = m_troneras_si
                    
                m_irregular = m_troneras[m_troneras['irregular'] == 'SI'].copy()
                if not m_irregular.empty:
                    m_irregular['geometry'] = m_irregular.geometry.apply(polygon_to_boundary)
                    m_layers['Irregular'] = m_irregular
                
        # Banda Mínima
        if not gdf_bm.empty and not gdf_parcelas.empty:
            m_smps = gdf_parcelas[gdf_parcelas['manzana'] == m_val]['smp'].dropna().unique().tolist()
            if m_smps:
                m_bm = gdf_bm[gdf_bm['smp'].isin(m_smps)].copy()
                if not m_bm.empty:
                    m_bm['geometry'] = m_bm.geometry.apply(polygon_to_boundary)
                    m_layers['banda_minima'] = m_bm

        # Línea de Fondo (LDF)
        if not gdf_ldf.empty and not gdf_parcelas.empty:
            m_smps = gdf_parcelas[gdf_parcelas['manzana'] == m_val]['smp'].dropna().unique().tolist()
            if m_smps:
                m_ldf = gdf_ldf[gdf_ldf['smp'].isin(m_smps)]
                if not m_ldf.empty:
                    m_layers['ldf'] = m_ldf

        # Tejido
        m_tejido_data = []
        if not gdf_tejido.empty:
            m_tejido = gdf_tejido[gdf_tejido['manzana'] == m_val].copy()
            if not m_tejido.empty:
                for idx, row in m_tejido.iterrows():
                    geom = row['geom']
                    alt = row.get('altura', None)
                    if geom and not geom.is_empty and alt is not None:
                        centroid = geom.centroid
                        m_tejido_data.append(((centroid.x, centroid.y), alt))
                
                m_tejido['geometry'] = m_tejido.geometry.apply(polygon_to_boundary)
                m_layers['tejido'] = m_tejido
                
        # Tejido Consolidado
        if not gdf_consolidado.empty and not gdf_parcelas.empty:
            m_smps = gdf_parcelas[gdf_parcelas['manzana'] == m_val]['smp'].dropna().unique().tolist()
            if m_smps:
                m_consolidado = gdf_consolidado[gdf_consolidado['smp'].isin(m_smps)]
                if not m_consolidado.empty:
                    m_layers['mdr_tejidoconsolidado'] = m_consolidado
                    
        # Tejido Para Irregular
        if not gdf_tejido_irreg.empty and not gdf_parcelas.empty:
            m_smps = gdf_parcelas[gdf_parcelas['manzana'] == m_val]['smp'].dropna().unique().tolist()
            if m_smps:
                m_tpi = gdf_tejido_irreg[gdf_tejido_irreg['smp'].isin(m_smps)]
                if not m_tpi.empty:
                    m_layers['mdr_tejidoparairregular'] = m_tpi
                    
        # Combinar capas de la manzana
        gdfs_to_combine = []
        for layer_name, gdf in m_layers.items():
            gdf_clean = gpd.GeoDataFrame({'geometry': gdf.geometry}, crs="EPSG:22186")
            gdf_clean['Layer'] = layer_name
            
            # Asignar estilo de color OGR para DXF
            if layer_name == 'lib':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#ffd306)'
            elif layer_name == 'lfi':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#3579b1)'
            elif layer_name == 'banda_minima':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#e41a1c)'
            elif layer_name == 'tejido':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#808080)'
            elif layer_name == 'mdr_tejidoconsolidado':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#c0c0c0)'
            elif layer_name == 'mdr_tejidoparairregular':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#808080)'
            elif layer_name == 'manzanas':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#404040)'
            elif layer_name == 'parcelas':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#606060)'
            elif layer_name == 'Tronera SI':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#3579b1)'
            elif layer_name == 'Irregular':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#e41a1c)'
            else:
                gdf_clean['OGR_STYLE'] = 'PEN(c:#000000)'
                
            gdfs_to_combine.append(gdf_clean)
            
        if gdfs_to_combine:
            combined_gdf = pd.concat(gdfs_to_combine, ignore_index=True)
            combined_gdf = gpd.GeoDataFrame(combined_gdf, geometry='geometry', crs="EPSG:22186")
            combined_gdf = combined_gdf[~combined_gdf.geometry.is_empty].copy()
            
            if len(combined_gdf) > 0:
                filename = f"{sec_folder}-{m_val}.dxf"
                filepath = os.path.join(seccion_dir, filename)
                
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass
                        
                try:
                    with fiona.Env(DXF_WRITE_HATCH="FALSE"):
                        combined_gdf.to_file(filepath, driver="DXF", layer="entities")
                    
                    try:
                        doc = ezdxf.readfile(filepath)
                        
                        # Registrar tipo de línea DASHED para Banda Mínima
                        if 'DASHED' not in doc.linetypes:
                            try:
                                doc.linetypes.new('DASHED', dxfattribs={'description': 'Dashed line - - -', 'pattern': [10.0, 5.0, -5.0]})
                            except Exception:
                                pass
                                
                        msp = doc.modelspace()
                        
                        layer_colors = {
                            'lib': (2, (255, 211, 6)),          # ACI 2 (Amarillo), RGB #ffd306
                            'lfi': (141, (53, 121, 177)),       # ACI 141 (Azul Acero), RGB #3579b1
                            'banda_minima': (1, (228, 26, 28)), # ACI 1 (Rojo), RGB #e41a1c
                            'tejido': (8, (128, 128, 128)),     # ACI 8 (Gris Oscuro), RGB #808080
                            'mdr_tejidoconsolidado': (9, (192, 192, 192)), # ACI 9 (Gris Claro), RGB #c0c0c0
                            'mdr_tejidoparairregular': (8, (128, 128, 128)), # ACI 8 (Gris Oscuro), RGB #808080
                            'manzanas': (250, (64, 64, 64)),    # ACI 250 (Gris Muy Oscuro), RGB #404040
                            'parcelas': (252, (96, 96, 96)),    # ACI 252 (Gris Carbón), RGB #606060
                            'Tronera SI': (141, (53, 121, 177)), # ACI 141 (Azul LFI), RGB #3579b1
                            'Irregular': (1, (228, 26, 28))     # ACI 1 (Rojo), RGB #e41a1c
                        }
                        
                        # 1. Configurar propiedades de capa (color y transparencia)
                        for l_name, (aci, rgb) in layer_colors.items():
                            if l_name in doc.layers:
                                layer = doc.layers.get(l_name)
                                layer.color = aci
                                layer.rgb = rgb
                                if l_name in ('mdr_tejidoconsolidado', 'mdr_tejidoparairregular'):
                                    layer.transparency = 0.5
                                    
                        # Configurar tipo de línea DASHED en la capa banda_minima
                        if 'banda_minima' in doc.layers:
                            layer_bm = doc.layers.get('banda_minima')
                            layer_bm.linetype = 'DASHED'
                            layer_bm.color = 1
                            
                        for entity in msp:
                            if entity.dxf.layer == 'banda_minima':
                                entity.dxf.linetype = 'DASHED'
                                entity.dxf.ltscale = 5.0
                                entity.dxf.color = 1

                        # 2. Convertir las polilíneas de las capas de tejido a HATCH
                        hatch_layers = ('mdr_tejidoconsolidado', 'mdr_tejidoparairregular')
                        for l_name in hatch_layers:
                            if l_name in doc.layers:
                                polylines = [e for e in msp if e.dxf.layer == l_name and e.dxftype() in ('LWPOLYLINE', 'POLYLINE')]
                                for poly in polylines:
                                    if poly.dxftype() == 'LWPOLYLINE':
                                        pts = [(p[0], p[1]) for p in poly.get_points()]
                                    else:
                                        pts = [(v.dxf.location.x, v.dxf.location.y) for v in poly.vertices]
                                        
                                    if len(pts) >= 3:
                                        h_color = doc.layers.get(l_name).color
                                        hatch = msp.add_hatch(color=h_color, dxfattribs={'layer': l_name})
                                        hatch.set_pattern_fill('SOLID')
                                        hatch.paths.add_polyline_path(pts, is_closed=True)
                                        
                                    msp.delete_entity(poly)

                        # 3. Estilo de texto oficial
                        for s in doc.styles:
                            try:
                                s.dxf.font = 'arial.ttf'
                            except Exception:
                                pass

                        text_style = 'HELVETICA'
                        try:
                            if 'HELVETICA' not in doc.styles:
                                style = doc.styles.new('HELVETICA', dxfattribs={'font': 'arialbd.ttf'})
                                try:
                                    style.set_extended_font_data(family='Helvetica', italic=False, bold=True)
                                except Exception:
                                    pass
                            else:
                                doc.styles.get('HELVETICA').dxf.font = 'arialbd.ttf'
                        except Exception:
                            text_style = 'Standard'

                        # 4. Agregar etiquetas de altura (labels) para la capa 'tejido'
                        if m_tejido_data:
                            try:
                                h_color = doc.layers.get('tejido').color if 'tejido' in doc.layers else 8
                                for pos, alt in m_tejido_data:
                                    try:
                                        alt_val = float(alt)
                                        text_str = f"{alt_val:.1f}"
                                    except (ValueError, TypeError):
                                        text_str = str(alt)
                                        
                                    t = msp.add_text(text_str, dxfattribs={
                                        'layer': 'tejido',
                                        'color': h_color,
                                        'height': 0.375,
                                        'style': text_style
                                    })
                                    t.set_placement(pos, align=TextEntityAlignment.MIDDLE_CENTER)
                            except Exception as e_t:
                                print(f"Error procesando tejido texto: {e_t}")

                        # 5. Agregar etiquetas de parcelas (CUR y Unidades de Edificabilidad)
                        if m_parcelas_data:
                            try:
                                if 'parcelas_etiquetas' not in doc.layers:
                                    l_parc = doc.layers.new('parcelas_etiquetas')
                                    l_parc.color = 252
                                    l_parc.rgb = (96, 96, 96)
                                
                                p_color = doc.layers.get('parcelas_etiquetas').color
                                for (x, y), lines in m_parcelas_data:
                                    positions = [(x, y + 0.3), (x, y - 0.3)] if len(lines) == 2 else [(x, y)]
                                    for line_text, pos in zip(lines, positions):
                                        t = msp.add_text(line_text, dxfattribs={
                                            'layer': 'parcelas_etiquetas',
                                            'color': p_color,
                                            'height': 0.45,
                                            'style': text_style
                                        })
                                        t.set_placement(pos, align=TextEntityAlignment.MIDDLE_CENTER)
                            except Exception as e_p:
                                print(f"Error procesando parcelas texto: {e_p}")

                        # 6. Agregar etiquetas de calles (con las mismas propiedades de parcelas_etiquetas)
                        if m_calles_data:
                            try:
                                if 'calles_etiquetas' not in doc.layers:
                                    l_calles = doc.layers.new('calles_etiquetas')
                                    l_calles.color = 252
                                    l_calles.rgb = (96, 96, 96)
                                
                                c_color = doc.layers.get('calles_etiquetas').color
                                for pos, calle_name, rot_angle in m_calles_data:
                                    t = msp.add_text(str(calle_name).upper(), dxfattribs={
                                        'layer': 'calles_etiquetas',
                                        'color': c_color,
                                        'height': 0.45,
                                        'rotation': rot_angle,
                                        'style': text_style
                                    })
                                    t.set_placement(pos, align=TextEntityAlignment.MIDDLE_CENTER)
                            except Exception as e_c:
                                print(f"Error procesando calles texto: {e_c}")
                                    
                        doc.save()
                    except Exception as e_dxf:
                        print(f"  -> Manzana {m_val}: Advertencia al aplicar colores/hatches con ezdxf: {e_dxf}")
                        
                except Exception as e:
                    print(f"  -> Manzana {m_val}: Error al escribir: {e}")
                    
    print(f"Sección {sec_folder} finalizada en {time.time() - t_sec_start:.2f} segundos.")

def exportar_single_manzana_dxf(engine, seccion_val, manzana_val, output_path=None):
    """
    Genera on-demand el archivo DXF para una única manzana utilizando la misma lógica exacta
    de capas, colores, hatches y etiquetas de exportar_dwg.py.
    """
    sec_str = str(seccion_val).strip()
    m_str = str(manzana_val).strip()
    sec_escaped = sec_str.replace("'", "''")
    m_escaped = m_str.replace("'", "''")
    sec_lpad = sec_escaped.zfill(3)
    sec_unpad = sec_escaped.lstrip('0') or '0'
    m_lpad = m_escaped.zfill(3)
    m_unpad = m_escaped.lstrip('0') or '0'

    # 1. Cargar Manzanas con ST_Transform nativo en PostGIS
    query_manzanas = f"""
        SELECT ST_Transform(ST_SetSRID(geom, CASE WHEN ST_SRID(geom) = 0 THEN 3857 ELSE ST_SRID(geom) END), 22186) AS geom, seccion, manzana 
        FROM public.manzanas 
        WHERE (TRIM(seccion) = '{sec_escaped}' OR LPAD(TRIM(seccion), 3, '0') = '{sec_lpad}' OR TRIM(seccion) = '{sec_unpad}')
          AND (TRIM(manzana) = '{m_escaped}' OR LPAD(TRIM(manzana), 3, '0') = '{m_lpad}' OR TRIM(manzana) = '{m_unpad}')
          AND geom IS NOT NULL
    """
    try:
        gdf_manzanas = gpd.read_postgis(query_manzanas, con=engine, geom_col="geom", crs="EPSG:22186")
        if gdf_manzanas.empty:
            raise ValueError(f"No se encontró la manzana {m_str} en la sección {sec_str}.")
    except Exception as e:
        raise ValueError(f"Error al cargar manzana {sec_str}-{m_str}: {e}")

    # 2. Cargar Parcelas
    query_parcelas = f"""
        SELECT geom, smp, seccion, manzana, cur_1, uni_edif_1, uni_edif_2, uni_edif_3, uni_edif_4 
        FROM public.cur_parcelas_ok 
        WHERE (TRIM(seccion) = '{sec_escaped}' OR LPAD(TRIM(seccion), 3, '0') = '{sec_lpad}') 
          AND (TRIM(manzana) = '{m_escaped}' OR LPAD(TRIM(manzana), 3, '0') = '{m_lpad}') 
          AND geom IS NOT NULL
    """
    try:
        gdf_parcelas = gpd.read_postgis(query_parcelas, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception:
        gdf_parcelas = gpd.GeoDataFrame()

    # 2b. Cargar Calles cercanas (usando la envolvente bounding-box exacta con ST_Transform nativo en EPSG:22186)
    if not gdf_manzanas.empty:
        m_xmin, m_ymin, m_xmax, m_ymax = gdf_manzanas.total_bounds
        query_calles = f"""
            SELECT c.nomoficial, ST_Transform(ST_SetSRID(c.geom, CASE WHEN ST_SRID(c.geom) = 0 THEN 22186 ELSE ST_SRID(c.geom) END), 22186) AS geom 
            FROM public.calles c 
            WHERE c.geom IS NOT NULL 
              AND c.nomoficial IS NOT NULL 
              AND TRIM(c.nomoficial) <> ''
              AND ST_Transform(ST_SetSRID(c.geom, CASE WHEN ST_SRID(c.geom) = 0 THEN 22186 ELSE ST_SRID(c.geom) END), 22186) && ST_MakeEnvelope({m_xmin - 150}, {m_ymin - 150}, {m_xmax + 150}, {m_ymax + 150}, 22186)
        """
        try:
            gdf_calles = gpd.read_postgis(query_calles, con=engine, geom_col="geom", crs="EPSG:22186")
        except Exception as e_c1:
            try:
                fallback_q = f"""
                    SELECT c.nomoficial, ST_Transform(ST_SetSRID(c.geom, CASE WHEN ST_SRID(c.geom) = 0 THEN 22186 ELSE ST_SRID(c.geom) END), 22186) AS geom 
                    FROM calles c 
                    WHERE c.geom IS NOT NULL 
                      AND c.nomoficial IS NOT NULL 
                      AND TRIM(c.nomoficial) <> ''
                      AND ST_Transform(ST_SetSRID(c.geom, CASE WHEN ST_SRID(c.geom) = 0 THEN 22186 ELSE ST_SRID(c.geom) END), 22186) && ST_MakeEnvelope({m_xmin - 150}, {m_ymin - 150}, {m_xmax + 150}, {m_ymax + 150}, 22186)
                """
                gdf_calles = gpd.read_postgis(fallback_q, con=engine, geom_col="geom", crs="EPSG:22186")
            except Exception as e_c2:
                print(f"Error cargando calles: {e_c1} / {e_c2}")
                gdf_calles = gpd.GeoDataFrame()
    else:
        gdf_calles = gpd.GeoDataFrame()

    # 3. LFI
    query_lfi = f"SELECT geom, seccion, manzana FROM public.mdr_lineadefrenteinterno WHERE (TRIM(seccion) = '{sec_escaped}' OR LPAD(TRIM(seccion), 3, '0') = '{sec_lpad}') AND (TRIM(manzana) = '{m_escaped}' OR LPAD(TRIM(manzana), 3, '0') = '{m_lpad}') AND geom IS NOT NULL"
    try:
        gdf_lfi = gpd.read_postgis(query_lfi, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception:
        gdf_lfi = gpd.GeoDataFrame()

    # 4. LIB
    query_lib = f"SELECT geom, seccion, manzana FROM public.mdr_lineadebasamento WHERE (TRIM(seccion) = '{sec_escaped}' OR LPAD(TRIM(seccion), 3, '0') = '{sec_lpad}') AND (TRIM(manzana) = '{m_escaped}' OR LPAD(TRIM(manzana), 3, '0') = '{m_lpad}') AND geom IS NOT NULL"
    try:
        gdf_lib = gpd.read_postgis(query_lib, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception:
        gdf_lib = gpd.GeoDataFrame()

    # 5. Troneras
    query_troneras = f"SELECT geom, seccion, manzana, id_tronera, sm, comuna, irregular FROM public.mdr_troneras WHERE (TRIM(seccion) = '{sec_escaped}' OR LPAD(TRIM(seccion), 3, '0') = '{sec_lpad}') AND (TRIM(manzana) = '{m_escaped}' OR LPAD(TRIM(manzana), 3, '0') = '{m_lpad}') AND geom IS NOT NULL"
    try:
        gdf_troneras = gpd.read_postgis(query_troneras, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception:
        gdf_troneras = gpd.GeoDataFrame()

    # 6. Banda Mínima
    query_bm = f"""
        SELECT bm.geom, bm.smp 
        FROM public.mdr_banda_minima bm 
        INNER JOIN public.cur_parcelas_ok p ON bm.smp = p.smp 
        WHERE (TRIM(p.seccion) = '{sec_escaped}' OR LPAD(TRIM(p.seccion), 3, '0') = '{sec_lpad}') AND (TRIM(p.manzana) = '{m_escaped}' OR LPAD(TRIM(p.manzana), 3, '0') = '{m_lpad}') AND bm.geom IS NOT NULL
    """
    try:
        gdf_bm = gpd.read_postgis(query_bm, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception:
        gdf_bm = gpd.GeoDataFrame()

    # 7. LDF
    query_ldf = f"""
        SELECT ldf.geom, ldf.smp 
        FROM public.mdr_ldf_parc ldf 
        INNER JOIN public.cur_parcelas_ok p ON ldf.smp = p.smp 
        WHERE (TRIM(p.seccion) = '{sec_escaped}' OR LPAD(TRIM(p.seccion), 3, '0') = '{sec_lpad}') AND (TRIM(p.manzana) = '{m_escaped}' OR LPAD(TRIM(p.manzana), 3, '0') = '{m_lpad}') AND ldf.geom IS NOT NULL
    """
    try:
        gdf_ldf = gpd.read_postgis(query_ldf, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception:
        gdf_ldf = gpd.GeoDataFrame()

    # 8. Tejido
    query_tejido = f"SELECT geom, smp, LPAD(sec, 3, '0') AS seccion, man AS manzana, altura FROM public.tejido WHERE (LPAD(sec, 3, '0') = '{sec_lpad}' OR TRIM(sec) = '{sec_unpad}') AND (TRIM(man) = '{m_escaped}' OR LPAD(TRIM(man), 3, '0') = '{m_lpad}') AND geom IS NOT NULL"
    try:
        gdf_tejido = gpd.read_postgis(query_tejido, con=engine, geom_col="geom", crs="EPSG:3857")
        if not gdf_tejido.empty:
            gdf_tejido = gdf_tejido.to_crs("EPSG:22186")
    except Exception:
        gdf_tejido = gpd.GeoDataFrame()

    # 9. Tejido Consolidado
    query_tc = f"""
        SELECT tc.geometry AS geom, tc.smp 
        FROM public.mdr_tejidoconsolidado tc 
        INNER JOIN public.cur_parcelas_ok p ON tc.smp = p.smp 
        WHERE (TRIM(p.seccion) = '{sec_escaped}' OR LPAD(TRIM(p.seccion), 3, '0') = '{sec_lpad}') AND (TRIM(p.manzana) = '{m_escaped}' OR LPAD(TRIM(p.manzana), 3, '0') = '{m_lpad}') AND tc.geometry IS NOT NULL
    """
    try:
        gdf_consolidado = gpd.read_postgis(query_tc, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception:
        gdf_consolidado = gpd.GeoDataFrame()

    # 10. Tejido Para Irregular
    query_tpi = f"""
        SELECT tpi.geometry AS geom, tpi.smp 
        FROM public.mdr_tejidoparairregular tpi 
        INNER JOIN public.cur_parcelas_ok p ON tpi.smp = p.smp 
        WHERE (TRIM(p.seccion) = '{sec_escaped}' OR LPAD(TRIM(p.seccion), 3, '0') = '{sec_lpad}') AND (TRIM(p.manzana) = '{m_escaped}' OR LPAD(TRIM(p.manzana), 3, '0') = '{m_lpad}') AND tpi.geometry IS NOT NULL
    """
    try:
        gdf_tejido_irreg = gpd.read_postgis(query_tpi, con=engine, geom_col="geom", crs="EPSG:22186")
    except Exception:
        gdf_tejido_irreg = gpd.GeoDataFrame()

    m_layers = {}

    # Manzanas
    m_boundary = gdf_manzanas.copy()
    m_boundary['geometry'] = m_boundary.geometry.apply(polygon_to_boundary)
    m_layers['manzanas'] = m_boundary

    # Parcelas
    m_parcelas_data = []
    if not gdf_parcelas.empty:
        for idx, row in gdf_parcelas.iterrows():
            geom = row['geom']
            if geom and not geom.is_empty:
                centroid = geom.centroid
                cur = row.get('cur_1')
                unis = [row.get(f'uni_edif_{i}') for i in range(1, 5)]
                unis_clean = [float(u) for u in unis if u is not None and str(u) != 'nan' and float(u) > 0]
                labels = []
                if cur and str(cur) != 'nan':
                    labels.append(str(cur))
                if unis_clean:
                    labels.append(" / ".join(f"{u:.1f}m" for u in unis_clean))
                if labels:
                    m_parcelas_data.append(((centroid.x, centroid.y), labels))
        m_parcelas = gdf_parcelas.copy()
        m_parcelas['geometry'] = m_parcelas.geometry.apply(polygon_to_boundary)
        m_layers['parcelas'] = m_parcelas

    # Calles
    m_calles_data = []
    if not gdf_calles.empty and not gdf_manzanas.empty:
        mza_geom = gdf_manzanas.geometry.iloc[0]
        calles_bbox = gdf_calles[gdf_calles.intersects(mza_geom.buffer(100))].copy()
        if not calles_bbox.empty:
            calles_bbox['dist'] = calles_bbox.geometry.apply(lambda g: g.distance(mza_geom))
            calles_frentistas = calles_bbox[calles_bbox['dist'] <= 60]
            if not calles_frentistas.empty:
                grouped = calles_frentistas.groupby('nomoficial')
                for nom, group in grouped:
                    if not nom or str(nom) == 'nan':
                        continue
                    group_sorted = group.sort_values(by='dist')
                    best_segment = group_sorted.iloc[0]['geom']
                    if best_segment and not best_segment.is_empty:
                        nearest_pt = best_segment.interpolate(best_segment.project(mza_geom.centroid))
                        proj_d = best_segment.project(nearest_pt)
                        p1 = best_segment.interpolate(max(0, proj_d - 1.0))
                        p2 = best_segment.interpolate(min(best_segment.length, proj_d + 1.0))
                        angle = math.degrees(math.atan2(p2.y - p1.y, p2.x - p1.x))
                        if angle > 90:
                            angle -= 180
                        elif angle < -90:
                            angle += 180
                        m_calles_data.append(((nearest_pt.x, nearest_pt.y), str(nom).strip().upper(), angle))

    if not gdf_lfi.empty:
        m_layers['lfi'] = gdf_lfi
    if not gdf_lib.empty:
        m_layers['lib'] = gdf_lib
    if not gdf_troneras.empty:
        m_troneras_si = gdf_troneras[gdf_troneras['irregular'] == 'NO'].copy()
        if not m_troneras_si.empty:
            m_troneras_si['geometry'] = m_troneras_si.geometry.apply(polygon_to_boundary)
            m_layers['Tronera SI'] = m_troneras_si
        m_irregular = gdf_troneras[gdf_troneras['irregular'] == 'SI'].copy()
        if not m_irregular.empty:
            m_irregular['geometry'] = m_irregular.geometry.apply(polygon_to_boundary)
            m_layers['Irregular'] = m_irregular
    if not gdf_bm.empty:
        gdf_bm['geometry'] = gdf_bm.geometry.apply(polygon_to_boundary)
        m_layers['banda_minima'] = gdf_bm
    if not gdf_ldf.empty:
        m_layers['ldf'] = gdf_ldf

    m_tejido_data = []
    if not gdf_tejido.empty:
        for idx, row in gdf_tejido.iterrows():
            geom = row['geom']
            alt = row.get('altura', None)
            if geom and not geom.is_empty and alt is not None:
                centroid = geom.centroid
                m_tejido_data.append(((centroid.x, centroid.y), alt))
        gdf_tejido['geometry'] = gdf_tejido.geometry.apply(polygon_to_boundary)
        m_layers['tejido'] = gdf_tejido

    if not gdf_consolidado.empty:
        m_layers['mdr_tejidoconsolidado'] = gdf_consolidado
    if not gdf_tejido_irreg.empty:
        m_layers['mdr_tejidoparairregular'] = gdf_tejido_irreg

    gdfs_to_combine = []
    for layer_name, gdf in m_layers.items():
        gdf_clean = gpd.GeoDataFrame({'geometry': gdf.geometry}, crs="EPSG:22186")
        gdf_clean['Layer'] = layer_name
        if layer_name == 'lib': gdf_clean['OGR_STYLE'] = 'PEN(c:#ffd306)'
        elif layer_name == 'lfi': gdf_clean['OGR_STYLE'] = 'PEN(c:#3579b1)'
        elif layer_name == 'banda_minima': gdf_clean['OGR_STYLE'] = 'PEN(c:#e41a1c)'
        elif layer_name == 'tejido': gdf_clean['OGR_STYLE'] = 'PEN(c:#808080)'
        elif layer_name == 'mdr_tejidoconsolidado': gdf_clean['OGR_STYLE'] = 'PEN(c:#c0c0c0)'
        elif layer_name == 'mdr_tejidoparairregular': gdf_clean['OGR_STYLE'] = 'PEN(c:#808080)'
        elif layer_name == 'manzanas': gdf_clean['OGR_STYLE'] = 'PEN(c:#404040)'
        elif layer_name == 'parcelas': gdf_clean['OGR_STYLE'] = 'PEN(c:#606060)'
        elif layer_name == 'Tronera SI': gdf_clean['OGR_STYLE'] = 'PEN(c:#3579b1)'
        elif layer_name == 'Irregular': gdf_clean['OGR_STYLE'] = 'PEN(c:#e41a1c)'
        else: gdf_clean['OGR_STYLE'] = 'PEN(c:#000000)'
        gdfs_to_combine.append(gdf_clean)

    if not gdfs_to_combine:
        raise ValueError("No se encontraron geometrías vectoriales para esta manzana.")

    combined_gdf = pd.concat(gdfs_to_combine, ignore_index=True)
    combined_gdf = gpd.GeoDataFrame(combined_gdf, geometry='geometry', crs="EPSG:22186")
    combined_gdf = combined_gdf[~combined_gdf.geometry.is_empty].copy()

    if output_path is None:
        import tempfile
        temp_fd, filepath = tempfile.mkstemp(suffix=".dxf")
        os.close(temp_fd)
    else:
        filepath = output_path

    with fiona.Env(DXF_WRITE_HATCH="FALSE"):
        combined_gdf.to_file(filepath, driver="DXF", layer="entities")

    try:
        doc = ezdxf.readfile(filepath)
        if 'DASHED' not in doc.linetypes:
            try: doc.linetypes.new('DASHED', dxfattribs={'description': 'Dashed line - - -', 'pattern': [10.0, 5.0, -5.0]})
            except Exception: pass
        msp = doc.modelspace()
        layer_colors = {
            'lib': (2, (255, 211, 6)),
            'lfi': (141, (53, 121, 177)),
            'banda_minima': (1, (228, 26, 28)),
            'tejido': (8, (128, 128, 128)),
            'mdr_tejidoconsolidado': (9, (192, 192, 192)),
            'mdr_tejidoparairregular': (8, (128, 128, 128)),
            'manzanas': (250, (64, 64, 64)),
            'parcelas': (252, (96, 96, 96)),
            'Tronera SI': (141, (53, 121, 177)),
            'Irregular': (1, (228, 26, 28))
        }
        for l_name, (aci, rgb) in layer_colors.items():
            if l_name in doc.layers:
                layer = doc.layers.get(l_name)
                layer.color = aci
                layer.rgb = rgb
                if l_name in ('mdr_tejidoconsolidado', 'mdr_tejidoparairregular'):
                    layer.transparency = 0.40

        if 'banda_minima' in doc.layers:
            layer_bm = doc.layers.get('banda_minima')
            layer_bm.linetype = 'DASHED'
            layer_bm.color = 1
        for entity in msp:
            if entity.dxf.layer == 'banda_minima':
                entity.dxf.linetype = 'DASHED'
                entity.dxf.ltscale = 5.0
                entity.dxf.color = 1

        hatch_layers = ('mdr_tejidoconsolidado', 'mdr_tejidoparairregular')
        for l_name in hatch_layers:
            if l_name in doc.layers:
                polylines = [e for e in msp if e.dxf.layer == l_name and e.dxftype() in ('LWPOLYLINE', 'POLYLINE')]
                for poly in polylines:
                    pts = [(p[0], p[1]) for p in poly.get_points()] if poly.dxftype() == 'LWPOLYLINE' else [(v.dxf.location.x, v.dxf.location.y) for v in poly.vertices]
                    if len(pts) >= 3:
                        h_color = doc.layers.get(l_name).color
                        hatch = msp.add_hatch(color=h_color, dxfattribs={'layer': l_name})
                        hatch.set_pattern_fill('SOLID')
                        hatch.paths.add_polyline_path(pts, is_closed=True)
                        hatch.transparency = 0.40
                    msp.delete_entity(poly)

        # Actualizar todos los estilos del DXF (Standard, etc.) para forzar la fuente Arial
        for s in doc.styles:
            try:
                s.dxf.font = 'arial.ttf'
            except Exception:
                pass

        text_style = 'HELVETICA'
        try:
            if 'HELVETICA' not in doc.styles:
                style = doc.styles.new('HELVETICA', dxfattribs={'font': 'arialbd.ttf'})
                try:
                    style.set_extended_font_data(family='Helvetica', italic=False, bold=True)
                except Exception:
                    pass
            else:
                doc.styles.get('HELVETICA').dxf.font = 'arialbd.ttf'
        except Exception:
            text_style = 'Standard'

        if m_tejido_data:
            try:
                h_color = doc.layers.get('tejido').color if 'tejido' in doc.layers else 8
                for pos, alt in m_tejido_data:
                    try: alt_val = float(alt); text_str = f"{alt_val:.1f}"
                    except (ValueError, TypeError): text_str = str(alt)
                    t = msp.add_text(text_str, dxfattribs={'layer': 'tejido', 'color': h_color, 'height': 0.375, 'style': text_style})
                    t.set_placement(pos, align=TextEntityAlignment.MIDDLE_CENTER)
            except Exception as e_t:
                print(f"Error tejido texto: {e_t}")

        if m_parcelas_data:
            try:
                if 'parcelas_etiquetas' not in doc.layers:
                    l_parc = doc.layers.new('parcelas_etiquetas')
                    l_parc.color = 252; l_parc.rgb = (96, 96, 96)
                p_color = doc.layers.get('parcelas_etiquetas').color
                for (x, y), lines in m_parcelas_data:
                    positions = [(x, y + 0.3), (x, y - 0.3)] if len(lines) == 2 else [(x, y)]
                    for line_text, pos in zip(lines, positions):
                        t = msp.add_text(line_text, dxfattribs={'layer': 'parcelas_etiquetas', 'color': p_color, 'height': 0.45, 'style': text_style})
                        t.set_placement(pos, align=TextEntityAlignment.MIDDLE_CENTER)
            except Exception as e_p:
                print(f"Error parcelas texto: {e_p}")

        if m_calles_data:
            try:
                if 'calles_etiquetas' not in doc.layers:
                    l_calles = doc.layers.new('calles_etiquetas')
                    l_calles.color = 252; l_calles.rgb = (96, 96, 96)
                c_color = doc.layers.get('calles_etiquetas').color
                for pos, calle_name, rot_angle in m_calles_data:
                    t = msp.add_text(str(calle_name).upper(), dxfattribs={'layer': 'calles_etiquetas', 'color': c_color, 'height': 0.45, 'rotation': rot_angle, 'style': text_style})
                    t.set_placement(pos, align=TextEntityAlignment.MIDDLE_CENTER)
            except Exception as e_c:
                print(f"Error calles texto: {e_c}")

        doc.save()
    except Exception as e_dxf:
        print(f"Advertencia ezdxf: {e_dxf}")

    return filepath

def main():
    parser = argparse.ArgumentParser(description="Exportar capas vectoriales a DXF por manzana (Optimizado por Sección).")
    parser.add_argument("--seccion", type=str, help="Sección específica a procesar (ej. 009). Si no se define, procesa todas.")
    args = parser.parse_args()
    
    engine = get_engine()
    
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dxf_base_dir = os.path.join(root_dir, "dxf")
    os.makedirs(dxf_base_dir, exist_ok=True)
    
    if args.seccion:
        sections = [args.seccion.strip().zfill(3)]
    else:
        print("Obteniendo listado de secciones catastrales en la base de datos...")
        with engine.connect() as conn:
            res_sec = conn.execute(text("SELECT DISTINCT seccion FROM manzanas WHERE seccion IS NOT NULL ORDER BY seccion")).fetchall()
            sections = [r[0].strip().zfill(3) for r in res_sec if r[0]]
            
    print(f"Total de secciones a procesar: {len(sections)}")
    
    t_global_start = time.time()
    for idx, sec in enumerate(sections, 1):
        print(f"\n[{idx}/{len(sections)}]", end=" ")
        exportar_seccion(engine, sec, dxf_base_dir)
        
    print(f"\n==========================================")
    print(f"EXPORTACIÓN COMPLETADA en {time.time() - t_global_start:.2f} segundos.")
    print(f"==========================================")

if __name__ == "__main__":
    main()
