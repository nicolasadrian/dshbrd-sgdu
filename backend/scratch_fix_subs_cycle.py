import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

def recreate_subsanaciones_and_stock():
    with engine.connect() as conn:
        print("Recreando mv_catastro_subsanaciones y mv_catastro_stock_propio con ciclo completo de subsanación...")

        # 1. mv_catastro_subsanaciones
        conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS mv_catastro_subsanaciones CASCADE;"))
        conn.execute(text("""
            CREATE MATERIALIZED VIEW mv_catastro_subsanaciones AS
            WITH cfg AS (
                SELECT cfg_gestion_metas.analistas_oficiales
                FROM cfg_gestion_metas
                WHERE cfg_gestion_metas.gerencia = 'catastro'::text AND cfg_gestion_metas.trata_reporte = 'INTERVENCIONES'::text
            ), subs_ciclo AS (
                SELECT DISTINCT ON (a.id_expediente) 
                    a.id_expediente,
                    a.usuario_alta,
                    a.nombre_tipo_actividad,
                    a.estado,
                    a.fecha_alta
                FROM mvw_ee_actividades_secgdu a
                WHERE a.nombre_tipo_actividad IN ('SOLICITUD_SUBSANACION_TAD', 'SUBSANACION')
                ORDER BY a.id_expediente, a.fecha_alta DESC
            )
            SELECT u.id_expediente,
                   u.expediente,
                   u.trata,
                   u.descripcion_trata,
                   u.descripcion,
                   u.caratula,
                   u.estado_expediente,
                   u.fecha_primer_ingreso_gerencia,
                   up.destinatario_actual AS analista,
                   up.fecha_ultimo_pase AS fecha_recepcion_analista,
                   CURRENT_DATE - up.fecha_ultimo_pase::date AS dias_en_poder_actual,
                   sc.nombre_tipo_actividad AS tipo_subsanacion,
                   sc.fecha_alta AS fecha_apertura_subsanacion,
                   CURRENT_DATE - sc.fecha_alta::date AS dias_subsanacion_abierta,
                   CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date AS dias_en_gerencia
            FROM mv_catastro_universo u
            JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
            CROSS JOIN cfg
            JOIN subs_ciclo sc ON sc.id_expediente = u.id_expediente
            LEFT JOIN mv_catastro_egresos_efectivos ee ON ee.id_expediente = u.id_expediente
            WHERE u.es_trata_propia = true 
              AND (up.destinatario_actual = ANY (cfg.analistas_oficiales))
              AND sc.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'::text
              AND sc.estado = 'PENDIENTE'::text
              AND ee.id_expediente IS NULL;
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_subs_id ON mv_catastro_subsanaciones(id_expediente);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_subs_trata ON mv_catastro_subsanaciones(trata);"))

        # 2. mv_catastro_stock_propio
        conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS mv_catastro_stock_propio CASCADE;"))
        conn.execute(text("""
            CREATE MATERIALIZED VIEW mv_catastro_stock_propio AS
            WITH cfg AS (
                SELECT cfg_gestion_metas.analistas_oficiales
                FROM cfg_gestion_metas
                WHERE cfg_gestion_metas.gerencia = 'catastro'::text AND cfg_gestion_metas.trata_reporte = 'INTERVENCIONES'::text
            ), subs_ciclo AS (
                SELECT DISTINCT ON (a.id_expediente) 
                    a.id_expediente,
                    a.nombre_tipo_actividad,
                    a.estado
                FROM mvw_ee_actividades_secgdu a
                WHERE a.nombre_tipo_actividad IN ('SOLICITUD_SUBSANACION_TAD', 'SUBSANACION')
                ORDER BY a.id_expediente, a.fecha_alta DESC
            )
            SELECT u.id_expediente,
                   u.expediente,
                   u.trata,
                   u.descripcion_trata,
                   u.descripcion,
                   u.caratula,
                   u.estado_expediente,
                   u.fecha_primer_ingreso_gerencia,
                   up.destinatario_actual AS analista,
                   up.fecha_ultimo_pase AS fecha_recepcion_analista,
                   CURRENT_DATE - up.fecha_ultimo_pase::date AS dias_en_poder_actual,
                   CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date AS dias_en_gerencia
            FROM mv_catastro_universo u
            JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
            LEFT JOIN subs_ciclo sc ON sc.id_expediente = u.id_expediente
            LEFT JOIN mv_catastro_egresos_efectivos ee ON ee.id_expediente = u.id_expediente
            CROSS JOIN cfg
            WHERE u.es_trata_propia = true 
              AND (up.destinatario_actual = ANY (cfg.analistas_oficiales))
              AND ee.id_expediente IS NULL
              AND NOT (sc.id_expediente IS NOT NULL 
                       AND sc.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'::text 
                       AND sc.estado = 'PENDIENTE'::text);
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_sp_id ON mv_catastro_stock_propio(id_expediente);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_sp_trata ON mv_catastro_stock_propio(trata);"))

        conn.commit()
        print("Subsanaciones y Stock Propio de Catastro actualizados exitosamente!")

if __name__ == '__main__':
    recreate_subsanaciones_and_stock()
