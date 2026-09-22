import os
import sys
import logging
import ezdxf
from shapely.geometry import LineString, MultiLineString
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
                # Normalizar nombre de capa visualmente
                capa_label = "LFI" if layer_norm == "lfi" else ("Tronera SI" if layer_norm == "tronera si" else "Irregular")
                extracted.append({
                    "capa": capa_label,
                    "geom_wkt": geom.wkt
                })

    return extracted

def run_extraction_lfi_troneras(only_approved=True):
    """
    Ejecuta el proceso completo de extracción:
    1. Asegura la existencia de public.lfi_troneras en geo-mdr.
    2. Obtiene manzanas aprobadas con analista asignado desde sade_db.
    3. Obtiene los metadatos de las manzanas (mz_tipo, sm, etc.) desde geo-mdr.
    4. Para cada manzana aprobada, busca su último DXF cargado.
    5. Extrae los vectores de LFI, Tronera SI e Irregular.
    6. Inserta los datos en geo-mdr.public.lfi_troneras con disposicio = 'A designar'.
    """
    report = {
        "status": "ok",
        "total_manzanas_encontradas": 0,
        "manzanas_procesadas": 0,
        "vectores_totales_insertados": 0,
        "detalles": [],
        "errores": []
    }

    # 1. Asegurar tabla en geo-mdr
    with geo_engine.begin() as geo_conn:
        ensure_lfi_troneras_table(geo_conn)

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

    # 2. Obtener metadata de manzanas desde geo-mdr
    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads", "trazados_lfi"))
    
    with geo_engine.begin() as geo_conn:
        ensure_lfi_troneras_table(geo_conn)

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

        # 3. Procesar cada manzana
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
                # Si no está en BD, buscar en la carpeta de uploads por patrón
                if os.path.exists(upload_dir):
                    matched = [
                        f for f in os.listdir(upload_dir)
                        if f.startswith(f"lfi-{sec}-") or f.startswith(f"lfi-{sec_padded}-")
                        and f"-{man}-" in f or f"-{man_padded}-" in f
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

            # Limpiar vectores previos de esta manzana en public.lfi_troneras
            geo_conn.execute(text("""
                DELETE FROM public.lfi_troneras WHERE sm = :sm
            """), {"sm": meta["sm"]})

            # Insertar los nuevos vectores
            capas_counts = {}
            for v in vectors:
                c_name = v["capa"]
                capas_counts[c_name] = capas_counts.get(c_name, 0) + 1
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

            report["manzanas_procesadas"] += 1
            report["vectores_totales_insertados"] += len(vectors)
            report["detalles"].append({
                "seccion": meta["seccion"],
                "manzana": meta["manzana"],
                "sm": meta["sm"],
                "analista": analista,
                "archivo": chosen_file,
                "vectores": len(vectors),
                "desglose": capas_counts
            })

    return report

if __name__ == '__main__':
    print("=== INICIANDO EXTRACCIÓN DE VECTORES DXF A public.lfi_troneras ===")
    res = run_extraction_lfi_troneras()
    print(f"Manzanas encontradas: {res['total_manzanas_encontradas']}")
    print(f"Manzanas procesadas: {res['manzanas_procesadas']}")
    print(f"Vectores totales insertados: {res['vectores_totales_insertados']}")
    if res['detalles']:
        print("\nDetalle por manzana:")
        for d in res['detalles']:
            print(f"  - SM: {d['sm']} (Secc {d['seccion']}, Mz {d['manzana']}): {d['vectores']} vectores {d['desglose']} [Archivo: {d['archivo']}]")
    if res['errores']:
        print("\nAvisos / Errores:")
        for e in res['errores']:
            print(f"  ! {e}")
