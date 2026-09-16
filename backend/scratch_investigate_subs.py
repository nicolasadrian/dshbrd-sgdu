import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== EXPEDIENTES EN SUBSANACION QUE YA EGRESARON O CUYA ULTIMA ACTIVIDAD NO ES PENDIENTE ===")
    
    # 1. Cuántos están en mv_catastro_subsanaciones Y además en mv_catastro_egresos_efectivos
    r1 = conn.execute(text("""
        SELECT count(*) 
        FROM mv_catastro_subsanaciones s
        JOIN mv_catastro_egresos_efectivos e ON e.id_expediente = s.id_expediente
    """)).scalar()
    print("Expedientes en Subsanaciones Y Egresos Efectivos:", r1)

    # 2. Cuántos están en mv_catastro_subsanaciones Y en mv_catastro_egresos_no_efectivos (Guarda Temporal)
    r2 = conn.execute(text("""
        SELECT count(*) 
        FROM mv_catastro_subsanaciones s
        JOIN mv_catastro_egresos_no_efectivos e ON e.id_expediente = s.id_expediente
    """)).scalar()
    print("Expedientes en Subsanaciones Y Egresos No Efectivos:", r2)

    # 3. Analizando la última actividad de CUALQUIER tipo vs solo SOLICITUD_SUBSANACION_TAD
    # Si la persona subsana, el sistema crea SUBSANACION (CERRADA) y APROBACION_DOC (APROBADA), pero SADE NO cambia el estado de la SOLICITUD_SUBSANACION_TAD original a CERRADA
    sample_acts = conn.execute(text("""
        WITH ultimas_actividades AS (
            SELECT DISTINCT ON (id_expediente) id_expediente, nombre_tipo_actividad, estado, fecha_alta, fecha_cierre
            FROM mvw_ee_actividades_secgdu
            ORDER BY id_expediente, fecha_alta DESC
        )
        SELECT s.id_expediente, s.trata, s.analista, ua.nombre_tipo_actividad, ua.estado, ua.fecha_alta,
               CASE WHEN ee.id_expediente IS NOT NULL THEN 'EGRESADO' ELSE 'NO_EGRESADO' END as egreso_status
        FROM mv_catastro_subsanaciones s
        JOIN ultimas_actividades ua ON ua.id_expediente = s.id_expediente
        LEFT JOIN mv_catastro_egresos_efectivos ee ON ee.id_expediente = s.id_expediente
        LIMIT 20
    """)).mappings().fetchall()
    
    print("\nSample de expedientes en subsanaciones:")
    for sa in sample_acts:
        print(dict(sa))

    # 4. Distribución de la última actividad general para los expedientes hoy en subsanaciones
    dist = conn.execute(text("""
        WITH ultimas_actividades AS (
            SELECT DISTINCT ON (id_expediente) id_expediente, nombre_tipo_actividad, estado, fecha_alta
            FROM mvw_ee_actividades_secgdu
            ORDER BY id_expediente, fecha_alta DESC
        )
        SELECT ua.nombre_tipo_actividad, ua.estado, count(*)
        FROM mv_catastro_subsanaciones s
        JOIN ultimas_actividades ua ON ua.id_expediente = s.id_expediente
        GROUP BY ua.nombre_tipo_actividad, ua.estado
    """)).mappings().fetchall()
    print("\nDistribución de la última actividad general para los en subsanación:")
    for d in dist:
        print(dict(d))
