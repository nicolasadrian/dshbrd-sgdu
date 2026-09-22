import os
import sys
import math
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from shapely import wkt
import shapely
from shapely.geometry import LineString, MultiLineString, Polygon, MultiPolygon, Point
from shapely.ops import unary_union, polygonize, snap

load_dotenv()
logger = logging.getLogger(__name__)

# Base de datos local geo-mdr
local_sade = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
if local_sade.startswith("postgres://"):
    local_sade = local_sade.replace("postgres://", "postgresql://", 1)
local_geo = f"{local_sade.rsplit('/', 1)[0]}/geo-mdr"

def ensure_contorno_table(conn):
    """
    Crea la tabla public.lfi_troneras_contorno en geo-mdr.
    Campos: gid | seccion | manzana | mz_tipo | sm | disposicio | geom
    """
    conn.execute(text("""
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

def remove_spikes_and_collinear_from_coords(coords, spike_gap_tol=0.05, cos_thresh=-0.999):
    """
    Recorre los vértices de una polilínea y elimina ÚNICAMENTE espículas/astillas verdaderas
    (donde la línea va y regresa exactamente sobre la misma trayectoria con espesor cero).
    Preserva intactos todos los escalones, retranqueos y quiebres reales del trazado.
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
            
            # 1. Puntos duplicados / longitud prácticamente cero
            if len1 < 0.001:
                changed = True
                i += 1
                continue
                
            # 2. Vértice colineal redundante
            v1 = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
            v2 = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])
            if len1 > 0.001 and len2 > 0.001:
                cos_a = (v1[0]*v2[0] + v1[1]*v2[1]) / (len1 * len2)
                if cos_a > 0.99999:
                    changed = True
                    i += 1
                    continue
                    
                # 3. Astilla verdadera (va y regresa sobre la misma línea con espesor cero)
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
    Limpia todas las polilíneas de un LineString o MultiLineString eliminando astillas.
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
    5. Disuelve las áreas interiores con unary_union.
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
            # Si tiene al menos 3 vértices y los extremos están a menos de close_tol (ej. 75cm)
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
    all_polys = polys + [p for p in direct_polys if p.is_valid and p.area > 0.001]
    
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


def run_dissolve_lfi_troneras():
    eng = create_engine(local_geo)
    
    with eng.begin() as conn:
        ensure_contorno_table(conn)
        conn.execute(text("TRUNCATE TABLE public.lfi_troneras_contorno RESTART IDENTITY;"))
        
        # Obtener todas las manzanas agrupadas
        mzs = conn.execute(text("""
            SELECT sm, seccion, manzana, mz_tipo, disposicio
            FROM public.lfi_troneras
            GROUP BY sm, seccion, manzana, mz_tipo, disposicio
            ORDER BY seccion, manzana
        """)).fetchall()
        
        print(f"Iniciando disolución de contornos para {len(mzs)} manzanas...")
        
        processed = 0
        errors = 0
        
        for mz in mzs:
            sm, sec, man, mz_tipo, disp = mz
            
            # Obtener todas las líneas de la manzana
            rows = conn.execute(text("""
                SELECT ST_AsText(geom) FROM public.lfi_troneras WHERE sm = :sm
            """), {"sm": sm}).fetchall()
            
            lines = [wkt.loads(r[0]) for r in rows if r[0]]
            
            try:
                boundary_geom = dissolve_manzana_vectors(lines)
                if boundary_geom and not boundary_geom.is_empty:
                    conn.execute(text("""
                        INSERT INTO public.lfi_troneras_contorno (seccion, manzana, mz_tipo, sm, disposicio, geom)
                        VALUES (:sec, :man, :tipo, :sm, :disp, ST_SetSRID(ST_GeomFromText(:wkt), 22186))
                    """), {
                        "sec": sec,
                        "man": man,
                        "tipo": mz_tipo or "TIPICA",
                        "sm": sm,
                        "disp": disp or "A designar",
                        "wkt": boundary_geom.wkt
                    })
                    processed += 1
                else:
                    print(f"  [AVISO] Manzana {sm} no generó geometría de contorno.")
                    errors += 1
            except Exception as e:
                print(f"  [ERROR] Error procesando manzana {sm}: {e}")
                errors += 1

        print(f"\nProceso finalizado:")
        print(f"  - Manzanas totales: {len(mzs)}")
        print(f"  - Contornos disueltos insertados: {processed}")
        print(f"  - Errores / Avisos: {errors}")

    # Verificar datos resultantes
    with eng.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM public.lfi_troneras_contorno")).scalar()
        print(f"\nTotal registros en public.lfi_troneras_contorno: {count}")
        
        sample = conn.execute(text("""
            SELECT gid, seccion, manzana, mz_tipo, sm, disposicio, ST_GeometryType(geom), ST_NPoints(geom)
            FROM public.lfi_troneras_contorno
            LIMIT 5
        """)).fetchall()
        print("\nMuestra de registros:")
        for s in sample:
            print(" ", s)

if __name__ == '__main__':
    run_dissolve_lfi_troneras()
