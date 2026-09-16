import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== INSPECCIONANDO LOS 11 EXPEDIENTES CON EGRESO EFECTIVO Y SOLICITUD PENDIENTE ===")
    sample_egresados = conn.execute(text("""
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
        SELECT u.id_expediente, u.expediente, u.trata, uas.fecha_alta as fecha_solicitud, 
               ee.fecha_egreso, ee.documento_egreso, ee.acronimo_egreso, up.destinatario_actual
        FROM mv_catastro_universo u
        JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
        JOIN ultima_act_sub uas ON uas.id_expediente = u.id_expediente
        JOIN mv_catastro_egresos_efectivos ee ON ee.id_expediente = u.id_expediente
        CROSS JOIN cfg
        WHERE u.es_trata_propia = true 
          AND (up.destinatario_actual = ANY(cfg.analistas_oficiales))
          AND uas.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
          AND uas.estado = 'PENDIENTE'
    """)).mappings().fetchall()

    for s in sample_egresados:
        print(dict(s))
