import os
import io
import logging
from datetime import datetime
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

logger = logging.getLogger("pdf_generator")

# Dimensiones A3 Landscape en puntos (1 mm = 2.83464567 pt)
# A3 Landscape: Ancho = 1190.55 pt (420 mm), Alto = 841.89 pt (297 mm)
PAGE_WIDTH, PAGE_HEIGHT = landscape(A3)
MARGIN_CM = 0.5
MARGIN_PT = MARGIN_CM * 28.3465  # 0.5 cm = 14.17 pt

# Ruta al logo oficial del Gobierno de la Ciudad
ESCUDO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "img", "Nuevo_escudo_de_la_Ciudad_de_Buenos_Aires.png"))

def extract_lines_from_geom(geom):
    """Extrae líneas de polígonos o multipolígonos de Shapely."""
    if geom is None or geom.is_empty:
        return []
    gtype = geom.geom_type
    lines = []
    if gtype == 'Polygon':
        lines.append(geom.exterior.xy)
        for hole in geom.interiors:
            lines.append(hole.xy)
    elif gtype == 'MultiPolygon':
        for poly in geom.geoms:
            lines.extend(extract_lines_from_geom(poly))
    elif gtype in ('LineString', 'MultiLineString'):
        if gtype == 'LineString':
            lines.append(geom.xy)
        else:
            for ls in geom.geoms:
                lines.append(ls.xy)
    return lines

def render_dxf_or_geometry_to_image(seccion, manzana, file_path=None):
    """
    Renderiza el dibujo morfológico a PNG de Alta Resolución (300 DPI) para el plano A3.
    - Carga de capas vectoriales oficiales desde PostGIS (cur_parcelas_ok, mdr_banda_minima, mdr_lineadefrenteinterno, mdr_lineadebasamento, mdr_troneras, calles).
    - Banda Mínima renderizada como LÍNEA CORTADA (DASHED) en rojo (#e41a1c).
    - Nombres de Calles y Números de Parcela etiquetados en COLOR NEGRO ABSOLUTO (#000000) en negrita (Font Arial).
    - Exclusión total de capas de tejido urbano.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import json
    from shapely.geometry import shape
    
    img_buf = io.BytesIO()
    
    # 1. Si existe archivo DXF subido, procesar y renderizar con ezdxf a 300 DPI
    if file_path and os.path.exists(file_path) and file_path.lower().endswith('.dxf'):
        try:
            import ezdxf
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
            
            doc = ezdxf.readfile(file_path)
            
            # Recrear patrón DASHED compacto para la Banda Mínima
            if 'DASHED' in doc.linetypes:
                try:
                    doc.linetypes.remove('DASHED')
                except Exception:
                    pass
            try:
                doc.linetypes.new('DASHED', dxfattribs={'description': 'Compact dashed line', 'pattern': [0.6, 0.4, -0.2]})
            except Exception:
                pass
            
            def apply_entity_rules(entities):
                for entity in entities:
                    layer_name = (entity.dxf.layer or "").lower()
                    
                    # Ocultar únicamente capas de edificabilidad/volumetria 3D genérica
                    if any(k in layer_name for k in ['edificab', 'volumetria']) and not any(k in layer_name for k in ['cota', 'cotas', 'consolidad', 'cons', 'hatch']):
                        entity.dxf.invisible = 1
                        continue
                        
                    # Capas de Consolidados / Tejido Consolidado: Forzar visibilidad y color Gris uniforme (ACI 8 / #808080)
                    is_consolidado = any(k in layer_name for k in ['consolidad', 'cons', 'tejido', 'tej'])
                    if is_consolidado and not any(k in layer_name for k in ['cota', 'cotas', 'lfi', 'banda', 'irr', 'tronera']):
                        entity.dxf.invisible = 0
                        if entity.dxf.hasattr('color'):
                            entity.dxf.color = 8  # Gris uniforme
                        try:
                            entity.rgb = (128, 128, 128)
                        except Exception:
                            pass

                    # Cotas / Dimensiones / Textos / Flechas: Forzar visibilidad, línea CONTINUA y color negro
                    is_cotas = any(k in layer_name for k in ['cota', 'cotas', 'dim', 'dimension']) or entity.dxftype() in ('DIMENSION', 'LEADER')
                    
                    if is_cotas:
                        entity.dxf.invisible = 0
                        if entity.dxf.hasattr('linetype'):
                            entity.dxf.linetype = 'CONTINUOUS'
                        if entity.dxf.hasattr('color'):
                            entity.dxf.color = 7  # Negro en CAD
                    # Extensión Irregular / Tronera / LFI: Mismo color Azul (#3579b1 / ACI 5 / RGB 53, 121, 177) y línea CONTINUA
                    elif any(k in layer_name for k in ['irr', 'tronera', 'lfi', 'frente']):
                        if entity.dxf.hasattr('color'):
                            entity.dxf.color = 5  # Azul LFI
                        if entity.dxf.hasattr('linetype'):
                            entity.dxf.linetype = 'CONTINUOUS'
                        try:
                            entity.rgb = (53, 121, 177)
                        except Exception:
                            pass
                    # Banda Mínima: LÍNEA CORTADA (DASHED) en Violeta (#8a2be2)
                    elif any(k in layer_name for k in ['banda', 'bm', 'afec']):
                        if entity.dxf.hasattr('linetype'):
                            entity.dxf.linetype = 'DASHED'
                        if entity.dxf.hasattr('color'):
                            entity.dxf.color = 6  # Violeta / Magenta
                        
                    # Textos / MText / Etiquetas / Cotas: COLOR NEGRO (#000000)
                    if entity.dxftype() in ('TEXT', 'MTEXT') or any(k in layer_name for k in ['texto', 'text', 'calle', 'parc', 'nom', 'smp', 'etiqueta']):
                        if not is_consolidado and entity.dxf.hasattr('color'):
                            entity.dxf.color = 7
                        try:
                            if not is_consolidado:
                                entity.rgb = (0, 0, 0)
                        except Exception:
                            pass

            # Aplicar reglas tanto a ModelSpace como a todos los Bloques definidos (ej. bloques de DIMENSION *D...)
            msp = doc.modelspace()
            apply_entity_rules(msp)
            for blk in doc.blocks:
                apply_entity_rules(blk)
            
            # Orden de dibujado (Z-Order estricto): Consolidados/HATCH al fondo (0), Líneas/Polígonos al medio (1), Cotas/Textos al frente (2)
            def entity_sort_key(e):
                layer_name = (e.dxf.layer or "").lower()
                is_consolidado = any(k in layer_name for k in ['consolidad', 'cons', 'tejido', 'tej'])
                t = e.dxftype()
                if is_consolidado or t == 'HATCH':
                    return 0
                elif t in ('LINE', 'LWPOLYLINE', 'POLYLINE', 'ARC', 'CIRCLE', 'SOLID'):
                    return 1
                elif t in ('TEXT', 'MTEXT', 'DIMENSION', 'LEADER'):
                    return 2
                return 1

            sorted_entities = sorted(msp, key=entity_sort_key)

            fig = plt.figure(figsize=(16, 13), dpi=600)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.set_axis_off()
            
            ctx = RenderContext(doc)
            out = MatplotlibBackend(ax)
            frontend = Frontend(ctx, out)
            
            # Forzar contexto de layout y dibujar entidades respetando la lista ordenada
            frontend.ctx.set_current_layout(msp)
            frontend.set_background(frontend.ctx.current_layout_properties.background_color)
            frontend.draw_entities(sorted_entities)
            frontend.pipeline.finalize()
            
            # Forzar todas las etiquetas de texto de matplotlib a COLOR NEGRO ABSOLUTO (#000000)
            for txt in ax.texts:
                txt.set_color('#000000')
                txt.set_fontweight('bold')
                txt.set_fontsize(9.5)
                txt.set_bbox(dict(boxstyle='square,pad=0.15', facecolor='white', edgecolor='none', alpha=0.9))
                
            fig.savefig(img_buf, format='png', bbox_inches='tight', pad_inches=0.02, facecolor='white')
            plt.close(fig)
            img_buf.seek(0)
            return img_buf
        except Exception as e:
            logger.warning(f"No se pudo renderizar DXF con ezdxf ({e}). Generando plano desde base de datos...")

    # 2. Render vectorial estructurado en ALTA RESOLUCIÓN (300 DPI) desde PostGIS (geo_engine)
    try:
        from database import get_geo_mdr_engine
        from sqlalchemy import text
        
        geo_engine = get_geo_mdr_engine()
        with geo_engine.connect() as conn:
            s_clean = seccion.strip().zfill(3)
            m_clean = manzana.strip()
            
            # A. Manzana (Contorno principal)
            q_mza = "SELECT ST_AsGeoJSON(geom) FROM public.manzanas WHERE (TRIM(seccion) = :s OR LPAD(TRIM(seccion), 3, '0') = :s) AND TRIM(manzana) = :m LIMIT 1"
            mza_json = conn.execute(text(q_mza), {"s": s_clean, "m": m_clean}).scalar()
            
            # B. Parcelas de la manzana con número y centroide
            q_parc = """
                SELECT parcela, smp, ST_AsGeoJSON(geom), ST_X(ST_Centroid(geom)), ST_Y(ST_Centroid(geom))
                FROM public.cur_parcelas_ok 
                WHERE (TRIM(seccion) = :s OR LPAD(TRIM(seccion), 3, '0') = :s) AND TRIM(manzana) = :m
            """
            parc_rows = conn.execute(text(q_parc), {"s": s_clean, "m": m_clean}).fetchall()
            
            # C. LFI
            q_lfi = "SELECT ST_AsGeoJSON(geom) FROM public.mdr_lineadefrenteinterno WHERE (TRIM(seccion) = :s OR LPAD(TRIM(seccion), 3, '0') = :s) AND TRIM(manzana) = :m"
            lfi_rows = [r[0] for r in conn.execute(text(q_lfi), {"s": s_clean, "m": m_clean}).fetchall() if r[0]]
            
            # D. LIB (Basamento)
            q_lib = "SELECT ST_AsGeoJSON(geom) FROM public.mdr_lineadebasamento WHERE (TRIM(seccion) = :s OR LPAD(TRIM(seccion), 3, '0') = :s) AND TRIM(manzana) = :m"
            lib_rows = [r[0] for r in conn.execute(text(q_lib), {"s": s_clean, "m": m_clean}).fetchall() if r[0]]
            
            # E. Troneras
            q_tron = "SELECT irregular, ST_AsGeoJSON(geom) FROM public.mdr_troneras WHERE (TRIM(seccion) = :s OR LPAD(TRIM(seccion), 3, '0') = :s) AND TRIM(manzana) = :m"
            tron_rows = conn.execute(text(q_tron), {"s": s_clean, "m": m_clean}).fetchall()
            
            # F. Banda Mínima (LÍNEA CORTADA)
            q_bm = """
                SELECT ST_AsGeoJSON(bm.geom) 
                FROM public.mdr_banda_minima bm 
                INNER JOIN public.cur_parcelas_ok p ON bm.smp = p.smp 
                WHERE (TRIM(p.seccion) = :s OR LPAD(TRIM(p.seccion), 3, '0') = :s) AND TRIM(p.manzana) = :m AND bm.geom IS NOT NULL
            """
            bm_rows = [r[0] for r in conn.execute(text(q_bm), {"s": s_clean, "m": m_clean}).fetchall() if r[0]]
            
            calles_rows = []
            if mza_json:
                try:
                    import geopandas as gpd
                    mza_shape = shape(json.loads(mza_json))
                    query_calles = "SELECT nomoficial, geom FROM public.calles WHERE geom IS NOT NULL AND nomoficial IS NOT NULL AND TRIM(nomoficial) <> ''"
                    gdf_calles = gpd.read_postgis(query_calles, con=conn, geom_col="geom", crs="EPSG:22186")
                    if not gdf_calles.empty:
                        calles_bbox = gdf_calles[gdf_calles.intersects(mza_shape.buffer(80))]
                        seen_calles = set()
                        for idx, r_calle in calles_bbox.iterrows():
                            nom = r_calle.get('nomoficial')
                            if not nom or nom in seen_calles or str(nom) == 'nan':
                                continue
                            c_geom = r_calle['geom']
                            if c_geom and not c_geom.is_empty:
                                nearest_pt = c_geom.interpolate(c_geom.project(mza_shape.centroid))
                                dist = nearest_pt.distance(mza_shape)
                                if dist <= 60:
                                    seen_calles.add(nom)
                                    calles_rows.append((str(nom).strip().upper(), nearest_pt.x, nearest_pt.y))
                except Exception as e_c:
                    logger.warning(f"No se pudieron consultar calles: {e_c}")
            
            fig, ax = plt.subplots(figsize=(16, 13), dpi=300)
            ax.set_facecolor("white")
            
            # 1. Dibujar Contorno de Manzana
            if mza_json:
                m_geom = shape(json.loads(mza_json))
                for x, y in extract_lines_from_geom(m_geom):
                    ax.plot(x, y, color='#404040', linewidth=2.2, zorder=2)
                    
            # 2. Dibujar Parcelas y ETIQUETAS DE PARCELA EN COLOR NEGRO (#000000)
            if parc_rows:
                for p_num, smp, p_json, cx, cy in parc_rows:
                    if p_json:
                        p_geom = shape(json.loads(p_json))
                        for x, y in extract_lines_from_geom(p_geom):
                            ax.plot(x, y, color='#606060', linewidth=1.2, zorder=3)
                        
                        # ETIQUETA DE PARCELA (COLOR NEGRO ABSOLUTO #000000, ARIAL BOLD)
                        if p_num and cx and cy:
                            p_clean = str(p_num).strip()
                            ax.text(cx, cy, p_clean, color='#000000', fontsize=8.5, fontweight='bold',
                                    fontfamily='sans-serif', ha='center', va='center', zorder=20,
                                    bbox=dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor='none', alpha=0.85))

            # 3. Dibujar Basamento (LIB) - Amarillo #ffd306
            for l_json in lib_rows:
                l_geom = shape(json.loads(l_json))
                for x, y in extract_lines_from_geom(l_geom):
                    ax.plot(x, y, color='#ffd306', linewidth=2.2, zorder=5)

            # 4. Dibujar LFI - Azul #3579b1
            for l_json in lfi_rows:
                l_geom = shape(json.loads(l_json))
                for x, y in extract_lines_from_geom(l_geom):
                    ax.plot(x, y, color='#3579b1', linewidth=2.5, zorder=6)

            # 5. Dibujar Troneras / Extensiones Irregulares - Mismo color Azul #3579b1 que LFI
            for irr_val, t_json in tron_rows:
                if t_json:
                    t_geom = shape(json.loads(t_json))
                    t_color = '#3579b1'  # Azul unificado con LFI
                    t_lw = 2.8 if str(irr_val).upper() == 'SI' else 2.2
                    for x, y in extract_lines_from_geom(t_geom):
                        ax.plot(x, y, color=t_color, linewidth=t_lw, zorder=7)

            # 6. DIBUJAR BANDA MÍNIMA COMO LÍNEA CORTADA COMPACTA EN VIOLETA (#8a2be2)
            for bm_j in bm_rows:
                bm_geom = shape(json.loads(bm_j))
                for x, y in extract_lines_from_geom(bm_geom):
                    ax.plot(x, y, color='#8a2be2', linestyle='--', linewidth=2.5, dashes=(1.5, 1.0), zorder=12)

            # 7. DIBUJAR ETIQUETAS DE NOMBRES DE CALLES EN COLOR NEGRO ABSOLUTO (#000000)
            if calles_rows:
                for c_nom, cx, cy in calles_rows:
                    if c_nom and cx and cy:
                        c_clean = str(c_nom).strip().upper()
                        ax.text(cx, cy, c_clean, color='#000000', fontsize=9.5, fontweight='bold',
                                fontfamily='sans-serif', ha='center', va='center', zorder=25,
                                bbox=dict(boxstyle='square,pad=0.25', facecolor='#ffffff', edgecolor='#cbd5e1', linewidth=0.8, alpha=0.95))
                        
            ax.set_aspect('equal')
            ax.grid(False)
            ax.set_axis_off()
            
            fig.savefig(img_buf, format='png', bbox_inches='tight', pad_inches=0.04, facecolor='white')
            plt.close(fig)
            img_buf.seek(0)
            return img_buf

    except Exception as e:
        logger.error(f"Error generando gráfico matplotlib de respaldo: {e}")
        fig, ax = plt.subplots(figsize=(12, 10), dpi=300)
        ax.text(0.5, 0.5, f"Trazado Sección {seccion} - Manzana {manzana}", ha='center', va='center', fontsize=18, color='#000000')
        ax.axis('off')
        fig.savefig(img_buf, format='png', bbox_inches='tight')
        plt.close(fig)
        img_buf.seek(0)
        return img_buf

def generate_lfi_a3_pdf(seccion, manzana, barrio="", comuna="", disposicion="", estado="En curso", analista="", file_path=None):
    """
    Genera un archivo PDF formato A3 Horizontal con márgenes de 0.5 cm (5 mm) y fuente Arial (Helvetica).
    - Banda Mínima renderizada como LÍNEA CORTADA / DASHED RED LINE (#e41a1c).
    - Nombres de calles y parcelas visibles en COLOR NEGRO ABSOLUTO (#000000) con cajas de realce.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A3))
    
    x_min = MARGIN_PT
    y_min = MARGIN_PT
    x_max = PAGE_WIDTH - MARGIN_PT
    y_max = PAGE_HEIGHT - MARGIN_PT
    
    width_bounded = x_max - x_min
    height_bounded = y_max - y_min
    
    # 1. Dibujar Marco Exterior General (Márgenes de 0.5 cm)
    c.setLineWidth(1.5)
    c.setStrokeColor(colors.HexColor("#000000"))
    c.rect(x_min, y_min, width_bounded, height_bounded)
    
    # Panel lateral derecho (ancho 183.31 pt / ~65 mm)
    panel_width = 183.31
    drawing_width = width_bounded - panel_width
    x_split = x_max - panel_width
    
    # Línea divisoria vertical principal
    c.setLineWidth(1.5)
    c.line(x_split, y_min, x_split, y_max)
    
    # --- RECUADRO PRINCIPAL (DIBUJO CAD / PLANO) ---
    img_buf = render_dxf_or_geometry_to_image(seccion, manzana, file_path)
    if img_buf:
        img_reader = ImageReader(img_buf)
        pad = 2.0
        img_x = x_min + pad
        img_y = y_min + pad
        img_w = drawing_width - (pad * 2.0)
        img_h = height_bounded - (pad * 2.0)
        
        c.drawImage(img_reader, img_x, img_y, width=img_w, height=img_h, preserveAspectRatio=True, anchor='c')
    
    # --- PANEL LATERAL DERECHO ---
    h_r1 = 210.0
    h_r2 = 95.0
    h_r3 = 105.0
    
    y_r1_bottom = y_max - h_r1
    y_r2_bottom = y_r1_bottom - h_r2
    y_r3_bottom = y_r2_bottom - h_r3
    y_r4_bottom = y_min
    
    # Dibujar líneas horizontales divisoras
    c.setLineWidth(1.2)
    c.line(x_split, y_r1_bottom, x_max, y_r1_bottom)
    c.line(x_split, y_r2_bottom, x_max, y_r2_bottom)
    c.line(x_split, y_r3_bottom, x_max, y_r3_bottom)
    
    x_center = x_split + (panel_width / 2.0)
    
    # RECUADRO 1: ESCUDO + TEXTO INSTITUCIONAL CENTRADOS VERTICAL Y HORIZONTALMENTE
    y_r1_center = y_max - (h_r1 / 2.0)
    escudo_w = 75.0
    escudo_h = 75.0
    gap = 14.0
    
    escudo_top = y_r1_center + 65.0
    escudo_y = escudo_top - escudo_h
    escudo_x = x_center - (escudo_w / 2.0)
    
    if os.path.exists(ESCUDO_PATH):
        try:
            escudo_img = ImageReader(ESCUDO_PATH)
            c.drawImage(escudo_img, escudo_x, escudo_y, width=escudo_w, height=escudo_h, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            logger.error(f"Error al cargar imagen del escudo: {e}")

    c.setFillColor(colors.HexColor("#000000"))
    c.setFont("Helvetica-Bold", 9.5)
    
    text_start_y = escudo_y - gap
    c.drawCentredString(x_center, text_start_y, "GOBIERNO DE LA CIUDAD")
    c.drawCentredString(x_center, text_start_y - 13.0, "AUTÓNOMA DE BUENOS AIRES")
    
    c.setFont("Helvetica-Bold", 8.0)
    c.drawCentredString(x_center, text_start_y - 29.0, "SECRETARÍA DE GESTIÓN Y")
    c.drawCentredString(x_center, text_start_y - 40.0, "DESARROLLO URBANO")

    # RECUADRO 2: TÍTULO DEL TIPO DE PLANO (CENTRADO)
    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(colors.HexColor("#000000"))
    y_r2_center = y_r1_bottom - (h_r2 / 2.0) + 7.0
    c.drawCentredString(x_center, y_r2_center, "EXTENSIÓN DE ESPACIO")
    c.drawCentredString(x_center, y_r2_center - 15.0, "LIBRE DE MANZANA")

    # RECUADRO 3: VALOR DE SM
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawCentredString(x_center, y_r2_bottom - 20.0, "SECCIÓN - MANZANA (SM)")
    
    sec_str = str(seccion).strip().zfill(3)
    mza_str = str(manzana).strip().zfill(3)
    sm_value = f"{sec_str}-{mza_str}"
    
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(colors.HexColor("#000000"))
    c.drawCentredString(x_center, y_r2_bottom - 60.0, sm_value)

    # RECUADRO 4: REFERENCIAS GRÁFICAS DEL PLANO (ESTILOS Y VECTORES UNIFICADOS)
    c.setFont("Helvetica-Bold", 9.5)
    c.setFillColor(colors.HexColor("#000000"))
    c.drawString(x_split + 12.0, y_r3_bottom - 22.0, "REFERENCIAS GRÁFICAS")
    
    c.setLineWidth(0.8)
    c.setStrokeColor(colors.HexColor("#000000"))
    c.line(x_split + 12.0, y_r3_bottom - 27.0, x_max - 12.0, y_r3_bottom - 27.0)
    
    y_ref = y_r3_bottom - 45.0
    ref_items = [
        ("line", "#3579b1", [], 2.0, "Línea de Frente Interno"),
        ("line", "#3579b1", [], 2.0, "Extensión Irregular"),
        ("line", "#ffd306", [], 2.0, "Línea de Basamento"),
        ("line", "#8a2be2", [3, 2], 2.0, "Banda Mínima Afec."),
        ("rect", "#808080", [], 0, "Tejido Consolidado"),
        ("line", "#606060", [], 1.0, "Límite Parcelario")
    ]
    
    for item_type, color_hex, dash_pat, line_w, label in ref_items:
        if item_type == "line":
            c.setStrokeColor(colors.HexColor(color_hex))
            c.setLineWidth(line_w)
            if dash_pat:
                c.setDash(dash_pat, 0)
            else:
                c.setDash([], 0)
            c.line(x_split + 14.0, y_ref + 3.0, x_split + 44.0, y_ref + 3.0)
            c.setDash([], 0)
        elif item_type == "rect":
            c.setFillColor(colors.HexColor(color_hex))
            c.setStrokeColor(colors.HexColor(color_hex))
            c.rect(x_split + 14.0, y_ref - 1.0, 30.0, 8.0, fill=1, stroke=0)
            
        c.setFont("Helvetica", 8.0)
        c.setFillColor(colors.HexColor("#1e293b"))
        c.drawString(x_split + 52.0, y_ref, label)
        y_ref -= 16.0
        
    c.showPage()
    c.save()
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
