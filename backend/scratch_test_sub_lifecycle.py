import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== EVALUANDO LOGICA REAL DE SUBSANACIONES ACTIVAS ===")

    # 1. Qué actividades existen en un expediente cuando se pide subsanación y cuando se responde:
    # Caso 28612115:
    #  - 2026-06-26 11:50: SOLICITUD_SUBSANACION_TAD (PENDIENTE) por DIBIASEO
    #  - 2026-07-10 09:38: SUBSANACION (CERRADA) por SUBSANACION_TAD (el ciudadano subsanó!)
    #  - 2026-07-10 09:38: APROBACION_DOC (APROBADA) por SUBSANACION_TAD
    #  - 2026-07-16 13:16: Documento de egreso IFGPA emitido.

    # 2. Si buscamos la ÚLTIMA actividad del expediente entre ('SOLICITUD_SUBSANACION_TAD', 'SUBSANACION'):
    # Si la última es SOLICITUD_SUBSANACION_TAD y estado = 'PENDIENTE', entonces sigue esperando al ciudadano.
    # Si hubo una actividad SUBSANACION posterior, el ciudadano ya respondió (subsanó).
    
    # 3. Y además, si el expediente ya tiene un EGRESO EFECTIVO (o fecha_egreso), ¡ya egresó de la gerencia!

    test_sql = """
        WITH cfg AS (
            SELECT analistas_oficiales FROM cfg_gestion_metas 
            WHERE gerencia = 'catastro' AND trata_reporte = 'INTERVENCIONES'
        ),
        ultima_act_sub AS (
            SELECT DISTINCT ON (id_expediente) 
                id_expediente, 
                nombre_tipo_actividad, 
                estado, 
                fecha_alta
            FROM mvw_ee_actividades_secgdu
            WHERE nombre_tipo_actividad IN ('SOLICITUD_SUBSANACION_TAD', 'SUBSANACION')
            ORDER BY id_expediente, fecha_alta DESC
        )
        SELECT 
            count(*) as total_candidatos,
            count(CASE WHEN u.trata = 'MDUG0134N' THEN 1 END) as mdug0134n_candidatos,
            count(CASE WHEN ee.id_expediente IS NOT NULL THEN 1 END) as con_egreso_efectivo,
            count(CASE WHEN ee.id_expediente IS NULL THEN 1 END) as sin_egreso_efectivo
        FROM mv_catastro_universo u
        JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
        JOIN ultima_act_sub uas ON uas.id_expediente = u.id_expediente
        LEFT JOIN mv_catastro_egresos_efectivos ee ON ee.id_expediente = u.id_expediente
        CROSS JOIN cfg
        WHERE u.es_trata_propia = true 
          AND (up.destinatario_actual = ANY(cfg.analistas_oficiales))
          AND uas.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
          AND uas.estado = 'PENDIENTE'
    """
    res = conn.execute(text(test_sql)).mappings().first()
    print("Conteo considerando ultima actividad del ciclo de subsanacion (SOLICITUD vs SUBSANACION):", dict(res))

    # Y qué pasa con el expediente 28612115 bajo este criterio?
    check_286 = conn.execute(text("""
        WITH ultima_act_sub AS (
            SELECT DISTINCT ON (id_expediente) 
                id_expediente, nombre_tipo_actividad, estado, fecha_alta
            FROM mvw_ee_actividades_secgdu
            WHERE nombre_tipo_actividad IN ('SOLICITUD_SUBSANACION_TAD', 'SUBSANACION')
            ORDER BY id_expediente, fecha_alta DESC
        )
        SELECT * FROM ultima_act_sub WHERE id_expediente = 32017770
    """)).mappings().first()
    print("Estado para expediente 28612115 (32017770):", dict(check_286))
