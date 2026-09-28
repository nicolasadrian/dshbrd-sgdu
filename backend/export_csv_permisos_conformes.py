import os
import sys
import pandas as pd
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import engine

def export_permisos_ifpdo():
    print("[*] Exportando Permisos de Obra (IFPDO)...")
    query = """
    SELECT 
        p.id_expediente,
        p.expediente,
        p.documento,
        p.fecha_creacion,
        COALESCE(NULLIF(p.ubicacion, ''), NULLIF(m2.direccion, ''), '') AS ubicacion,
        COALESCE(NULLIF(p.ubicacion, ''), NULLIF(m2.direccion, ''), '') AS direccion,
        COALESCE(NULLIF(p.ubicacion_dgseccion, ''), NULLIF(m2.seccion, ''), '') AS seccion,
        COALESCE(NULLIF(p.ubicacion_dgmanzana, ''), NULLIF(m2.manzana, ''), '') AS manzana,
        COALESCE(NULLIF(p.ubicacion_dgparcela, ''), NULLIF(m2.parcela, ''), '') AS parcela,
        CASE 
            WHEN COALESCE(NULLIF(p.ubicacion_dgseccion, ''), NULLIF(m2.seccion, '')) IS NOT NULL 
             AND COALESCE(NULLIF(p.ubicacion_dgmanzana, ''), NULLIF(m2.manzana, '')) IS NOT NULL 
             AND COALESCE(NULLIF(p.ubicacion_dgparcela, ''), NULLIF(m2.parcela, '')) IS NOT NULL 
            THEN COALESCE(NULLIF(p.ubicacion_dgseccion, ''), NULLIF(m2.seccion, '')) || '-' || 
                 COALESCE(NULLIF(p.ubicacion_dgmanzana, ''), NULLIF(m2.manzana, '')) || '-' || 
                 COALESCE(NULLIF(p.ubicacion_dgparcela, ''), NULLIF(m2.parcela, ''))
            ELSE ''
        END AS smp,
        COALESCE(NULLIF(p.ubicacion_dgbarrio, ''), NULLIF(m2.barrio, ''), '') AS barrio,
        COALESCE(NULLIF(p.ubicacion_dgcomuna, ''), NULLIF(m2.comuna, ''), '') AS comuna,
        COALESCE(NULLIF(p.tipo_permiso, ''), NULLIF(m2.tipo_obra, ''), NULLIF(o.tipo_obra, ''), 'Permiso de Obra') AS tipo_obra,
        COALESCE(NULLIF(o.tipo_tarea, ''), NULLIF(m2.tipo_tarea, ''), '') AS tipo_tarea,
        (
            CASE 
                WHEN (COALESCE(o.sup_construir, 0) + COALESCE(o.sup_ampliar, 0) + COALESCE(o.sup_modificar, 0)) > 0 
                THEN (COALESCE(o.sup_construir, 0) + COALESCE(o.sup_ampliar, 0) + COALESCE(o.sup_modificar, 0))
                WHEN (COALESCE(m2.sup_construir, 0) + COALESCE(m2.sup_ampliar, 0) + COALESCE(m2.sup_modificar, 0)) > 0 
                THEN (COALESCE(m2.sup_construir, 0) + COALESCE(m2.sup_ampliar, 0) + COALESCE(m2.sup_modificar, 0))
                ELSE COALESCE(p.sup_demoler, 0)
            END
        ) AS metros_cuadrados,
        COALESCE(o.sup_construir, m2.sup_construir) AS metros_construir,
        COALESCE(o.sup_ampliar, m2.sup_ampliar) AS metros_ampliar,
        COALESCE(o.sup_modificar, m2.sup_modificar) AS metros_modificar,
        COALESCE(p.sup_terreno, m2.sup_terreno) AS sup_terreno,
        COALESCE(p.sup_existente, m2.sup_existente) AS sup_existente,
        COALESCE(p.sup_demoler, m2.sup_demoler) AS sup_demoler,
        COALESCE(p.sup_libre, m2.sup_libre) AS sup_libre,
        COALESCE(p.x, m2.x) AS longitud,
        COALESCE(p.y, m2.y) AS latitud,
        CASE 
            WHEN COALESCE(p.x, m2.x) IS NOT NULL AND COALESCE(p.y, m2.y) IS NOT NULL 
            THEN COALESCE(p.y, m2.y)::text || ', ' || COALESCE(p.x, m2.x)::text
            ELSE ''
        END AS coordenadas
    FROM public.gedo_ifpdo_datos p
    LEFT JOIN (
        SELECT DISTINCT ON (id_expediente)
            id_expediente,
            tipo_obra,
            tipo_tarea,
            sup_construir,
            sup_ampliar,
            sup_modificar
        FROM public.gedo_ifocd_datos
        ORDER BY id_expediente, fecha_creacion DESC NULLS LAST
    ) o ON p.id_expediente = o.id_expediente
    LEFT JOIN (
        SELECT DISTINCT ON (id_expediente) *
        FROM public.mvw_m2_permisados
        ORDER BY id_expediente
    ) m2 ON p.id_expediente = m2.id_expediente
    ORDER BY p.fecha_creacion DESC NULLS LAST, p.id_expediente DESC;
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "permisos_obra_ifpdo.csv"))
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[+] Permisos de Obra exportados exitosamente: {out_path} ({len(df):,} filas)")
    return out_path, len(df)

def export_conformes_ifpco():
    print("[*] Exportando Conformes de Obra (IFPCO)...")
    query = """
    SELECT 
        c.id_expediente,
        c.expediente,
        c.documento,
        c.fecha_creacion,
        COALESCE(NULLIF(c.ubicacion, ''), NULLIF(c.ubicacion_r1, ''), NULLIF(m.direccion, ''), '') AS ubicacion,
        COALESCE(NULLIF(c.ubicacion, ''), NULLIF(c.ubicacion_r1, ''), NULLIF(m.direccion, ''), '') AS direccion,
        COALESCE(NULLIF(c.ubicacion_dgseccion, ''), NULLIF(c.ubicacion_seccion, ''), NULLIF(c.ubicacion_dgseccion_r1, ''), NULLIF(m.seccion, ''), '') AS seccion,
        COALESCE(NULLIF(c.ubicacion_dgmanzana, ''), NULLIF(c.ubicacion_manzana, ''), NULLIF(c.ubicacion_dgmanzana_r1, ''), NULLIF(m.manzana, ''), '') AS manzana,
        COALESCE(NULLIF(c.ubicacion_dgparcela, ''), NULLIF(c.ubicacion_parcela, ''), NULLIF(c.ubicacion_dgparcela_r1, ''), NULLIF(m.parcela, ''), '') AS parcela,
        CASE 
            WHEN COALESCE(NULLIF(c.ubicacion_dgseccion, ''), NULLIF(c.ubicacion_seccion, ''), NULLIF(c.ubicacion_dgseccion_r1, ''), NULLIF(m.seccion, '')) IS NOT NULL 
             AND COALESCE(NULLIF(c.ubicacion_dgmanzana, ''), NULLIF(c.ubicacion_manzana, ''), NULLIF(c.ubicacion_dgmanzana_r1, ''), NULLIF(m.manzana, '')) IS NOT NULL 
             AND COALESCE(NULLIF(c.ubicacion_dgparcela, ''), NULLIF(c.ubicacion_parcela, ''), NULLIF(c.ubicacion_dgparcela_r1, ''), NULLIF(m.parcela, '')) IS NOT NULL 
            THEN COALESCE(NULLIF(c.ubicacion_dgseccion, ''), NULLIF(c.ubicacion_seccion, ''), NULLIF(c.ubicacion_dgseccion_r1, ''), NULLIF(m.seccion, '')) || '-' || 
                 COALESCE(NULLIF(c.ubicacion_dgmanzana, ''), NULLIF(c.ubicacion_manzana, ''), NULLIF(c.ubicacion_dgmanzana_r1, ''), NULLIF(m.manzana, '')) || '-' || 
                 COALESCE(NULLIF(c.ubicacion_dgparcela, ''), NULLIF(c.ubicacion_parcela, ''), NULLIF(c.ubicacion_dgparcela_r1, ''), NULLIF(m.parcela, ''))
            ELSE ''
        END AS smp,
        COALESCE(NULLIF(c.ubicacion_dgbarrio, ''), NULLIF(c.ubicacion_barrio, ''), NULLIF(c.ubicacion_dgbarrio_r1, ''), NULLIF(m.barrio, ''), '') AS barrio,
        COALESCE(NULLIF(c.ubicacion_dgcomuna, ''), NULLIF(c.ubicacion_comuna, ''), NULLIF(c.ubicacion_dgcomuna_r1, ''), NULLIF(m.comuna, ''), '') AS comuna,
        COALESCE(NULLIF(c.tipo_obra, ''), NULLIF(m.tipo_obra, ''), 'Conforme de Obra') AS tipo_obra,
        COALESCE(NULLIF(c.tipo_tarea, ''), NULLIF(m.tipo_tarea, ''), '') AS tipo_tarea,
        (
            CASE 
                WHEN (
                    COALESCE(c.construida, 0) + 
                    COALESCE(c.modificada, 0) + 
                    COALESCE(c.sup_contrav_reg, 0) + 
                    COALESCE(c.sup_contrav_antirr, 0) + 
                    COALESCE(c.reglamentaria, 0) + 
                    COALESCE(c.antireglamentaria, 0) + 
                    COALESCE(c.modif_sup_reglam, 0) + 
                    COALESCE(c.modif_sup_antirr, 0) + 
                    COALESCE(c.super_ampliada_contravencion, 0) + 
                    COALESCE(c.supe_contra_reglamen_cur, 0) + 
                    COALESCE(c.supe_contra_no_reglam_cur, 0) + 
                    COALESCE(c.supe_contra_no_reglam_cpu, 0)
                ) > 0 THEN (
                    COALESCE(c.construida, 0) + 
                    COALESCE(c.modificada, 0) + 
                    COALESCE(c.sup_contrav_reg, 0) + 
                    COALESCE(c.sup_contrav_antirr, 0) + 
                    COALESCE(c.reglamentaria, 0) + 
                    COALESCE(c.antireglamentaria, 0) + 
                    COALESCE(c.modif_sup_reglam, 0) + 
                    COALESCE(c.modif_sup_antirr, 0) + 
                    COALESCE(c.super_ampliada_contravencion, 0) + 
                    COALESCE(c.supe_contra_reglamen_cur, 0) + 
                    COALESCE(c.supe_contra_no_reglam_cur, 0) + 
                    COALESCE(c.supe_contra_no_reglam_cpu, 0)
                )
                WHEN COALESCE(m.sup_total_afectada, 0) > 0 THEN m.sup_total_afectada
                ELSE COALESCE(c.sup_permiso_previo, 0)
            END
        ) AS metros_cuadrados,
        COALESCE(c.construida, m.sup_construida) AS metros_construida,
        COALESCE(c.modificada, m.sup_modificada) AS metros_modificada,
        COALESCE(c.sup_permiso_previo, m.sup_permiso_previo) AS metros_permiso_previo,
        COALESCE(c.sup_terreno, m.sup_terreno) AS sup_terreno,
        COALESCE(c.sup_existente, m.sup_existente) AS sup_existente,
        COALESCE(c.sup_libre, 0) AS sup_libre,
        COALESCE(c.x, m.x) AS longitud,
        COALESCE(c.y, m.y) AS latitud,
        CASE 
            WHEN COALESCE(c.x, m.x) IS NOT NULL AND COALESCE(c.y, m.y) IS NOT NULL 
            THEN COALESCE(c.y, m.y)::text || ', ' || COALESCE(c.x, m.x)::text
            ELSE ''
        END AS coordenadas
    FROM public.gedo_ifpco_datos c
    LEFT JOIN (
        SELECT DISTINCT ON (documento) *
        FROM public.mvw_conformes_obra
        ORDER BY documento
    ) m ON c.documento = m.documento
    ORDER BY c.fecha_creacion DESC NULLS LAST, c.id_expediente DESC;
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "conformes_obra_ifpco.csv"))
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[+] Conformes de Obra exportados exitosamente: {out_path} ({len(df):,} filas)")
    return out_path, len(df)

if __name__ == "__main__":
    pdo_file, pdo_count = export_permisos_ifpdo()
    pco_file, pco_count = export_conformes_ifpco()
    print("\n[V] Ambos archivos generados correctamente.")
