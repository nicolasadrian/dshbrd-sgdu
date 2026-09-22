import os
import sys
import math
import logging
import ezdxf
from shapely.geometry import LineString, MultiLineString, Polygon, MultiPolygon, Point
from shapely.ops import unary_union, polygonize, snap
import shapely
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Asegurar import de database
try:
    from database import engine, geo_engine
except ImportError:
    try:
        from backend.database import engine, geo_engine
    except ImportError:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        from database import engine, geo_engine

TARGET_LAYERS = {'lfi', 'tronera si', 'irregular'}

def ensure_lfi_troneras_table(geo_conn):
    """
    Crea la tabla public.lfi_troneras en geo-mdr si no existe.
    Campos solicitados: gid | seccion | manzana | mz_tipo | sm | disposicio | geom
    """
    geo_conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.lfi_troneras (
            gid BIGSERIAL PRIMARY KEY,
            seccion VARCHAR(10) NOT NULL,
            manzana VARCHAR(10) NOT NULL,
            mz_tipo VARCHAR(50),
            sm VARCHAR(20) NOT NULL,
            disposicio VARCHAR(100) DEFAULT 'A designar',
            geom geometry(Geometry, 22186)
        );
        ALTER TABLE public.lfi_troneras DROP COLUMN IF EXISTS capa;
        CREATE INDEX IF NOT EXISTS idx_lfi_troneras_sm ON public.lfi_troneras(sm);
        CREATE INDEX IF NOT EXISTS idx_lfi_troneras_geom ON public.lfi_troneras USING GIST(geom);
    """))

def ensure_contorno_table(geo_conn):
    """
    Crea la tabla public.lfi_troneras_contorno en geo-mdr si no existe.
    Campos solicitados: gid | seccion | manzana | mz_tipo | sm | disposicio | geom
    """
    geo_conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.lfi_troneras_contorno (
            gid BIGSERIAL PRIMARY KEY,
            seccion VARCHAR(10) NOT NULL,
            manzana VARCHAR(10) NOT NULL,
            mz_tipo VARCHAR(50),
            sm VARCHAR(20) NOT NULL,
            disposicio VARCHAR(100) DEFAULT 'A designar',
            geom geometry(Geometry, 22186)
        );
        CREATE INDEX IF NOT EXISTS idx_lfi_troneras_contorno_sm ON public.lfi_troneras_contorno(sm);
        CREATE INDEX IF NOT EXISTS idx_lfi_troneras_contorno_geom ON public.lfi_troneras_contorno USING GIST(geom);
    """))

def extract_vectors_from_dxf(fpath):
    """
    Lee un archivo DXF y extrae todas las entidades de las capas objetivo:
    LFI, Tronera SI, Irregular
    """
    if not os.path.exists(fpath):
        return []

    try:
        doc = ezdxf.readfile(fpath)
    except Exception as e:
        logger.error(f"Error abriendo archivo DXF {fpath}: {e}")
        return []

    msp = doc.modelspace()
    extracted = []

    for e in msp:
        layer_raw = (e.dxf.layer or "").strip()
        layer_norm = layer_raw.lower()
        if layer_norm in TARGET_LAYERS:
            geom = None
            dxftype = e.dxftype()
            
            if dxftype == 'LINE':
                p1 = (float(e.dxf.start.x), float(e.dxf.start.y))
                p2 = (float(e.dxf.end.x), float(e.dxf.end.y))
                if p1 != p2:
                    geom = LineString([p1, p2])
            elif dxftype == 'LWPOLYLINE':
                pts = [(float(p[0]), float(p[1])) for p in e.get_points('xy')]
                if e.is_closed and len(pts) >= 2 and pts[0] != pts[-1]:
                    pts.append(pts[0])
                if len(pts) >= 2:
                    geom = LineString(pts)
            elif dxftype == 'POLYLINE':
                pts = [(float(v.dxf.location.x), float(v.dxf.location.y)) for v in e.vertices]
                if e.is_closed and len(pts) >= 2 and pts[0] != pts[-1]:
                    pts.append(pts[0])
                if len(pts) >= 2:
                    geom = LineString(pts)
            elif dxftype == 'SPLINE':
                try:
                    ctrl_pts = [(float(p[0]), float(p[1])) for p in e.control_points]
                    if len(ctrl_pts) >= 2:
                        geom = LineString(ctrl_pts)
                except Exception:
                    pass

            if geom and not geom.is_empty:
                capa_label = "LFI" if layer_norm == "lfi" else ("Tronera SI" if layer_norm == "tronera si" else "Irregular")
                extracted.append({
                    "capa": capa_label,
                    "geom": geom,
                    "geom_wkt": geom.wkt
                })

    return extracted

def remove_spikes_and_collinear_from_coords(coords, spike_gap_tol=0.05, cos_thresh=-0.999):
    """
    Elimina ÚNICAMENTE espículas/astillas verdaderas (donde la línea va y regresa exactamente
    sobre la misma trayectoria con espesor cero), preservando escalones y entrantes reales.
    """
    if len(coords) < 3:
        return coords
        
    pts = list(coords)
    is_closed = (pts[0] == pts[-1])
    if is_closed:
        pts.pop()
        
    changed = True
    iterations = 0
    max_iter = 50
    
    while changed and len(pts) >= 3 and iterations < max_iter:
        changed = False
        iterations += 1
        new_pts = []
        n = len(pts)
        
        i = 0
        while i < n:
            p_prev = pts[(i - 1) % n]
            p_curr = pts[i]
            p_next = pts[(i + 1) % n]
            
            d_ends = math.hypot(p_next[0] - p_prev[0], p_next[1] - p_prev[1])
            len1 = math.hypot(p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
            len2 = math.hypot(p_next[0] - p_curr[0], p_next[1] - p_curr[1])
            
            if len1 < 0.001:
                changed = True
                i += 1
                continue
                
            v1 = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
            v2 = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])
            if len1 > 0.001 and len2 > 0.001:
                cos_a = (v1[0]*v2[0] + v1[1]*v2[1]) / (len1 * len2)
                if cos_a > 0.99999:
                    changed = True
                    i += 1
                    continue
                    
                if cos_a < cos_thresh and d_ends < spike_gap_tol and len1 > 0.01:
                    changed = True
                    i += 1
                    continue
                    
            new_pts.append(p_curr)
            i += 1
            
        pts = new_pts
        
    if is_closed and len(pts) >= 3:
        pts.append(pts[0])
        
    return pts

def clean_boundary_geom(geom):
    """
    Limpia polilíneas de un LineString o MultiLineString eliminando astillas de espesor cero.
    """
    if geom is None or geom.is_empty:
        return None
        
    if geom.geom_type == 'LineString':
        cleaned_pts = remove_spikes_and_collinear_from_coords(list(geom.coords))
        if len(cleaned_pts) >= 2:
            return LineString(cleaned_pts)
        return None
        
    elif geom.geom_type == 'MultiLineString':
        cleaned_lines = []
        for l in geom.geoms:
            c_pts = remove_spikes_and_collinear_from_coords(list(l.coords))
            if len(c_pts) >= 2:
                cleaned_lines.append(LineString(c_pts))
        if len(cleaned_lines) == 1:
            return cleaned_lines[0]
        elif len(cleaned_lines) > 1:
            return MultiLineString(cleaned_lines)
        return None
        
    return geom

def dissolve_manzana_vectors(lines, snap_tol=0.25, close_tol=0.75):
    """
    Toma una lista de geometrías LineString de una manzana,
    1. Cierra bucles casi-cerrados (extremos a menos de close_tol).
    2. Aplica snapping bidireccional entre todas las líneas con tolerancia snap_tol.
    3. Nodea todas las intersecciones y cruces.
    4. Poligoniza todas las caras cerradas y extrae también polígonos directos.
    5. Disuelve las áreas interiores con unary_union y micro-buffer bridge.
    6. Extrae la polilínea del contorno exterior disuelto (exterior rings).
    7. Limpia astillas, espículas interiores y vértices redundantes.
    """
    if not lines:
        return None

    # 1. Normalizar y forzar cierre de polilíneas casi cerradas
    closed_lines = []
    direct_polys = []
    for l in lines:
        pts = list(l.coords)
        if len(pts) >= 2:
            p_start = Point(pts[0])
            p_end = Point(pts[-1])
            if len(pts) >= 3 and (p_start.distance(p_end) <= close_tol or pts[0] == pts[-1]):
                pts[-1] = pts[0]
                try:
                    poly = Polygon(pts)
                    if poly.is_valid and poly.area > 0.001:
                        direct_polys.append(poly)
                except Exception:
                    pass
            closed_lines.append(LineString(pts))

    # 2. Unir y aplicar snapping bidireccional
    u_lines = unary_union(closed_lines)
    if snap_tol > 0:
        u_lines = snap(u_lines, u_lines, tolerance=snap_tol)

    # 3. Nodear cruces
    noded = shapely.node(u_lines) if hasattr(shapely, 'node') else u_lines

    # 4. Poligonizar caras
    polys = list(polygonize(noded))
    
    # Combinar polígonos de la poligonización y polígonos directos
    all_polys = [p for p in (polys + direct_polys) if p.is_valid and p.area > 0.001]
    
    if not all_polys:
        return clean_boundary_geom(u_lines)

    # 5. Micro-buffer bridge para disolver aristas compartidas con micro-offsets flotantes
    buffered = [p.buffer(0.01, join_style='mitre') for p in all_polys]
    u_buff = unary_union(buffered)
    dissolved_poly = u_buff.buffer(-0.01, join_style='mitre')

    # 6. Extraer contorno exterior exclusivamente (evita bucles y agujeros internos)
    if dissolved_poly.geom_type == 'Polygon':
        boundary = LineString(dissolved_poly.exterior.coords)
    elif dissolved_poly.geom_type == 'MultiPolygon':
        boundary = MultiLineString([LineString(p.exterior.coords) for p in dissolved_poly.geoms])
    else:
        boundary = dissolved_poly.boundary

    # 7. Limpiar astillas / espículas interiores
    cleaned_boundary = clean_boundary_geom(boundary)
    return cleaned_boundary

def run_extraction_lfi_troneras(only_approved=True):
    """
    Ejecuta el proceso completo de extracción y disolución:
    1. Asegura la existencia de public.lfi_troneras y public.lfi_troneras_contorno en geo-mdr.
    2. Obtiene manzanas aprobadas con analista asignado desde sade_db.
    3. Obtiene los metadatos de las manzanas (mz_tipo, sm, etc.) desde geo-mdr.
    4. Para cada manzana aprobada, busca su último DXF cargado.
    5. Extrae los vectores de LFI, Tronera SI e Irregular.
    6. Inserta los datos vectoriales en geo-mdr.public.lfi_troneras con disposicio = 'A designar'.
    7. Genera el contorno disuelto limpio y lo inserta en geo-mdr.public.lfi_troneras_contorno.
    """
    report = {
        "status": "ok",
        "total_manzanas_encontradas": 0,
        "manzanas_procesadas": 0,
        "vectores_totales_insertados": 0,
        "contornos_totales_insertados": 0,
        "detalles": [],
        "errores": []
    }

    # 1. Asegurar tablas en geo-mdr
    with geo_engine.begin() as geo_conn:
        ensure_lfi_troneras_table(geo_conn)
        ensure_contorno_table(geo_conn)

    # 2. Obtener manzanas con analista asignado
    estado_clause = """
        AND (
            estado IN ('Subir a Ciudad 3D', 'Aprobada', 'Aprobadas')
            OR estado ILIKE '%aprob%'
        )
    """ if only_approved else ""

    with engine.connect() as conn:
        wf_rows = conn.execute(text(f"""
            SELECT TRIM(seccion) as seccion, TRIM(manzana) as manzana, estado, analista_asignado, archivo_trazado, archivo_finalizado
            FROM public.manzanas_lfi_workflow
            WHERE analista_asignado IS NOT NULL 
              AND TRIM(analista_asignado) <> ''
              {estado_clause}
            ORDER BY seccion, manzana
        """)).fetchall()

    report["total_manzanas_encontradas"] = len(wf_rows)

    if not wf_rows:
        return report

    # 3. Obtener metadata de manzanas desde geo-mdr
    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads", "trazados_lfi"))
    
    with geo_engine.begin() as geo_conn:
        ensure_lfi_troneras_table(geo_conn)
        ensure_contorno_table(geo_conn)

        mz_dict = {}
        mz_res = geo_conn.execute(text("""
            SELECT TRIM(seccion) as seccion, TRIM(manzana) as manzana, mz_tipo, sm, disposicio
            FROM public.manzanas
        """)).fetchall()
        
        for m in mz_res:
            s_raw, m_raw = m[0], m[1]
            sec_clean = s_raw.lstrip('0') or '0'
            man_clean = m_raw.lstrip('0') or '0'
            sec_padded = s_raw.zfill(3)
            man_padded = m_raw.zfill(3)
            
            mz_data = {
                "seccion": s_raw,
                "manzana": m_raw,
                "mz_tipo": m[2] or "ATIPICA",
                "sm": m[3] or f"{sec_padded}-{man_padded}",
                "disposicio": m[4] or "A designar"
            }
            mz_dict[(s_raw, m_raw)] = mz_data
            mz_dict[(sec_clean, man_clean)] = mz_data
            mz_dict[(sec_padded, man_padded)] = mz_data

        # 4. Procesar cada manzana
        for row in wf_rows:
            sec = row[0]
            man = row[1]
            estado = row[2]
            analista = row[3]
            arch_trazado = row[4]
            arch_final = row[5]

            sec_clean = sec.lstrip('0') or '0'
            man_clean = man.lstrip('0') or '0'
            sec_padded = sec.zfill(3)
            man_padded = man.zfill(3)

            meta = (
                mz_dict.get((sec, man))
                or mz_dict.get((sec_clean, man_clean))
                or mz_dict.get((sec_padded, man_padded))
                or {
                    "seccion": sec_padded,
                    "manzana": man_padded,
                    "mz_tipo": "ATIPICA",
                    "sm": f"{sec_padded}-{man_padded}",
                    "disposicio": "A designar"
                }
            )

            # Buscar archivo DXF más reciente
            chosen_file = None
            if arch_final and arch_final.lower().endswith('.dxf'):
                chosen_file = arch_final
            elif arch_trazado and arch_trazado.lower().endswith('.dxf'):
                chosen_file = arch_trazado

            if not chosen_file:
                if os.path.exists(upload_dir):
                    matched = [
                        f for f in os.listdir(upload_dir)
                        if (f.startswith(f"lfi-{sec}-") or f.startswith(f"lfi-{sec_padded}-"))
                        and (f"-{man}-" in f or f"-{man_padded}-" in f)
                        and f.lower().endswith('.dxf')
                    ]
                    if matched:
                        matched.sort(reverse=True)
                        chosen_file = matched[0]

            if not chosen_file:
                report["errores"].append(f"No se encontró archivo DXF para Manzana {sec}-{man}")
                continue

            fpath = os.path.join(upload_dir, chosen_file)
            if not os.path.exists(fpath):
                report["errores"].append(f"Archivo no existe en disco: {chosen_file} (Mz {sec}-{man})")
                continue

            # Extraer vectores
            vectors = extract_vectors_from_dxf(fpath)
            if not vectors:
                report["errores"].append(f"No se encontraron vectores en capas LFI/Tronera SI/Irregular en {chosen_file}")
                continue

            # A. Limpiar y guardar en public.lfi_troneras
            geo_conn.execute(text("""
                DELETE FROM public.lfi_troneras WHERE sm = :sm
            """), {"sm": meta["sm"]})

            capas_counts = {}
            line_geoms = []
            for v in vectors:
                c_name = v["capa"]
                capas_counts[c_name] = capas_counts.get(c_name, 0) + 1
                line_geoms.append(v["geom"])
                geo_conn.execute(text("""
                    INSERT INTO public.lfi_troneras (seccion, manzana, mz_tipo, sm, disposicio, geom)
                    VALUES (:sec, :man, :tipo, :sm, :disp, ST_SetSRID(ST_GeomFromText(:wkt), 22186))
                """), {
                    "sec": meta["seccion"],
                    "man": meta["manzana"],
                    "tipo": meta["mz_tipo"],
                    "sm": meta["sm"],
                    "disp": "A designar",
                    "wkt": v["geom_wkt"]
                })

            # B. Generar contorno disuelto y guardar en public.lfi_troneras_contorno
            geo_conn.execute(text("""
                DELETE FROM public.lfi_troneras_contorno WHERE sm = :sm
            """), {"sm": meta["sm"]})

            contorno_ok = False
            try:
                boundary_geom = dissolve_manzana_vectors(line_geoms)
                if boundary_geom and not boundary_geom.is_empty:
                    geo_conn.execute(text("""
                        INSERT INTO public.lfi_troneras_contorno (seccion, manzana, mz_tipo, sm, disposicio, geom)
                        VALUES (:sec, :man, :tipo, :sm, :disp, ST_SetSRID(ST_GeomFromText(:wkt), 22186))
                    """), {
                        "sec": meta["seccion"],
                        "man": meta["manzana"],
                        "tipo": meta["mz_tipo"],
                        "sm": meta["sm"],
                        "disp": "A designar",
                        "wkt": boundary_geom.wkt
                    })
                    report["contornos_totales_insertados"] += 1
                    contorno_ok = True
            except Exception as b_err:
                logger.error(f"Error generando contorno para {meta['sm']}: {b_err}")
                report["errores"].append(f"Error generando contorno para {meta['sm']}: {b_err}")

            report["manzanas_procesadas"] += 1
            report["vectores_totales_insertados"] += len(vectors)
            report["detalles"].append({
                "seccion": meta["seccion"],
                "manzana": meta["manzana"],
                "sm": meta["sm"],
                "analista": analista,
                "archivo": chosen_file,
                "vectores": len(vectors),
                "contorno_generado": contorno_ok,
                "desglose": capas_counts
            })

    return report

if __name__ == '__main__':
    print("=== INICIANDO EXTRACCIÓN Y DISOLUCIÓN DE VECTORES DXF ===")
    res = run_extraction_lfi_troneras()
    print(f"Manzanas encontradas: {res['total_manzanas_encontradas']}")
    print(f"Manzanas procesadas: {res['manzanas_procesadas']}")
    print(f"Vectores insertados en lfi_troneras: {res['vectores_totales_insertados']}")
    print(f"Contornos insertados en lfi_troneras_contorno: {res['contornos_totales_insertados']}")
    if res['detalles']:
        print("\nDetalle por manzana:")
        for d in res['detalles']:
            print(f"  - SM: {d['sm']} (Secc {d['seccion']}, Mz {d['manzana']}): {d['vectores']} vectores {d['desglose']} [Contorno: {d['contorno_generado']}]")
    if res['errores']:
        print("\nAvisos / Errores:")
        for e in res['errores']:
            print(f"  ! {e}")
