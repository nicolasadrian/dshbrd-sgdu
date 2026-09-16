import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

def recreate_catastro_views():
    with engine.connect() as conn:
        print("Recreando vistas materializadas de Catastro...")

        # 1. mv_catastro_egresos_efectivos
        print("1. mv_catastro_egresos_efectivos...")
        conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS mv_catastro_egresos_efectivos CASCADE;"))
        conn.execute(text("""
            CREATE MATERIALIZED VIEW mv_catastro_egresos_efectivos AS
            WITH reglas_por_trata AS (
                SELECT cfg.trata_reporte AS trata,
                       unnest(cfg.acronimos_egreso) AS acronimo,
                       cfg.firmantes_egreso
                FROM cfg_gestion_metas cfg
                WHERE cfg.gerencia = 'catastro'::text AND cfg.trata_reporte <> 'INTERVENCIONES'::text
            ), egresos_validos AS (
                SELECT u.id_expediente,
                       u.expediente,
                       u.trata,
                       u.descripcion_trata,
                       u.descripcion,
                       u.caratula,
                       u.fecha_primer_ingreso_gerencia,
                       d.documento AS documento_egreso,
                       d.acronimo AS acronimo_egreso,
                       d.fecha_asociacion AS fecha_egreso,
                       d.usuario_creador AS usuario_egreso,
                       row_number() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_asociacion) AS rn
                FROM mv_catastro_universo u
                JOIN reglas_por_trata r ON r.trata = u.trata
                JOIN mvw_datos_gedo_secgdu d ON d.id_expediente = u.id_expediente 
                     AND d.acronimo = r.acronimo 
                     AND (r.firmantes_egreso IS NULL OR (d.usuario_creador = ANY (r.firmantes_egreso))) 
                     AND d.fecha_asociacion >= u.fecha_primer_ingreso_gerencia
                WHERE u.es_trata_propia = true
                  AND EXISTS (
                      SELECT 1 FROM mvw_ee_pases_secgdu p
                      WHERE p.id_expediente = u.id_expediente
                        AND p.motivo ~* 'constituc|certific'
                  )
            )
            SELECT id_expediente,
                   expediente,
                   trata,
                   descripcion_trata,
                   descripcion,
                   caratula,
                   fecha_primer_ingreso_gerencia,
                   documento_egreso,
                   acronimo_egreso,
                   fecha_egreso,
                   usuario_egreso,
                   fecha_egreso::date - fecha_primer_ingreso_gerencia::date AS dias_tramitacion
            FROM egresos_validos
            WHERE rn = 1;
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_ee_id ON mv_catastro_egresos_efectivos(id_expediente);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_ee_trata ON mv_catastro_egresos_efectivos(trata);"))

        # 2. mv_catastro_gedos_egreso
        print("2. mv_catastro_gedos_egreso...")
        conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS mv_catastro_gedos_egreso CASCADE;"))
        conn.execute(text("""
            CREATE MATERIALIZED VIEW mv_catastro_gedos_egreso AS
            WITH reglas_por_trata AS (
                SELECT cfg.trata_reporte AS trata,
                       unnest(cfg.acronimos_egreso) AS acronimo,
                       cfg.firmantes_egreso
                FROM cfg_gestion_metas cfg
                WHERE cfg.gerencia = 'catastro'::text AND cfg.trata_reporte <> 'INTERVENCIONES'::text
            ), raw_gedos AS (
                SELECT u.id_expediente,
                       u.expediente,
                       u.trata,
                       u.descripcion_trata,
                       d.documento AS documento_egreso,
                       d.acronimo AS acronimo_egreso,
                       d.fecha_asociacion AS fecha_egreso,
                       d.usuario_creador AS usuario_egreso,
                       row_number() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_asociacion DESC, d.documento DESC) AS rn
                FROM mv_catastro_universo u
                JOIN reglas_por_trata r ON r.trata = u.trata
                JOIN mvw_datos_gedo_secgdu d ON d.id_expediente = u.id_expediente 
                     AND d.acronimo = r.acronimo 
                     AND (r.firmantes_egreso IS NULL OR (d.usuario_creador = ANY (r.firmantes_egreso))) 
                     AND d.fecha_asociacion >= u.fecha_primer_ingreso_gerencia
                WHERE u.es_trata_propia = true
                  AND EXISTS (
                      SELECT 1 FROM mvw_ee_pases_secgdu p
                      WHERE p.id_expediente = u.id_expediente
                        AND p.motivo ~* 'constituc|certific'
                  )
            )
            SELECT id_expediente,
                   expediente,
                   trata,
                   descripcion_trata,
                   documento_egreso,
                   acronimo_egreso,
                   fecha_egreso,
                   usuario_egreso
            FROM raw_gedos
            WHERE rn = 1;
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_ge_id ON mv_catastro_gedos_egreso(id_expediente);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_ge_trata ON mv_catastro_gedos_egreso(trata);"))

        # 3. mv_catastro_egresos_no_efectivos
        print("3. mv_catastro_egresos_no_efectivos...")
        conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS mv_catastro_egresos_no_efectivos CASCADE;"))
        conn.execute(text("""
            CREATE MATERIALIZED VIEW mv_catastro_egresos_no_efectivos AS
            SELECT u.id_expediente,
                   u.expediente,
                   u.trata,
                   u.descripcion_trata,
                   u.descripcion,
                   u.caratula,
                   u.estado_expediente,
                   u.fecha_primer_ingreso_gerencia,
                   up.fecha_ultimo_pase AS fecha_ultimo_movimiento,
                   up.destinatario_actual AS poseedor_actual,
                   CURRENT_DATE - up.fecha_ultimo_pase::date AS dias_desde_guarda,
                   up.fecha_ultimo_pase::date - u.fecha_primer_ingreso_gerencia::date AS dias_tramitacion_aprox
            FROM mv_catastro_universo u
            JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
            LEFT JOIN mv_catastro_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
            WHERE u.es_trata_propia = true AND u.estado_expediente = 'Guarda Temporal'::text AND eef.id_expediente IS NULL;
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_ene_id ON mv_catastro_egresos_no_efectivos(id_expediente);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_ene_trata ON mv_catastro_egresos_no_efectivos(trata);"))

        # 4. mv_catastro_subsanaciones
        print("4. mv_catastro_subsanaciones...")
        conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS mv_catastro_subsanaciones CASCADE;"))
        conn.execute(text("""
            CREATE MATERIALIZED VIEW mv_catastro_subsanaciones AS
            WITH cfg AS (
                SELECT cfg_gestion_metas.analistas_oficiales
                FROM cfg_gestion_metas
                WHERE cfg_gestion_metas.gerencia = 'catastro'::text AND cfg_gestion_metas.trata_reporte = 'INTERVENCIONES'::text
            ), subs_abiertas AS (
                SELECT DISTINCT ON (a.id_expediente) 
                    a.id_expediente,
                    a.usuario_alta,
                    a.nombre_tipo_actividad,
                    a.estado,
                    a.fecha_alta
                FROM mvw_ee_actividades_secgdu a
                WHERE a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'::text
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
                   sa.nombre_tipo_actividad AS tipo_subsanacion,
                   sa.fecha_alta AS fecha_apertura_subsanacion,
                   CURRENT_DATE - sa.fecha_alta::date AS dias_subsanacion_abierta,
                   CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date AS dias_en_gerencia
            FROM mv_catastro_universo u
            JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
            CROSS JOIN cfg
            JOIN subs_abiertas sa ON sa.id_expediente = u.id_expediente
            WHERE u.es_trata_propia = true 
              AND (up.destinatario_actual = ANY (cfg.analistas_oficiales))
              AND sa.estado = 'PENDIENTE'::text;
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_subs_id ON mv_catastro_subsanaciones(id_expediente);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_subs_trata ON mv_catastro_subsanaciones(trata);"))

        # 5. mv_catastro_stock_propio
        print("5. mv_catastro_stock_propio...")
        conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS mv_catastro_stock_propio CASCADE;"))
        conn.execute(text("""
            CREATE MATERIALIZED VIEW mv_catastro_stock_propio AS
            WITH cfg AS (
                SELECT cfg_gestion_metas.analistas_oficiales
                FROM cfg_gestion_metas
                WHERE cfg_gestion_metas.gerencia = 'catastro'::text AND cfg_gestion_metas.trata_reporte = 'INTERVENCIONES'::text
            ), subs_abiertas AS (
                SELECT DISTINCT ON (a.id_expediente) 
                    a.id_expediente,
                    a.estado
                FROM mvw_ee_actividades_secgdu a
                WHERE a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'::text
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
            LEFT JOIN subs_abiertas sa ON sa.id_expediente = u.id_expediente
            CROSS JOIN cfg
            WHERE u.es_trata_propia = true 
              AND (up.destinatario_actual = ANY (cfg.analistas_oficiales))
              AND (sa.id_expediente IS NULL OR sa.estado <> 'PENDIENTE'::text);
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_sp_id ON mv_catastro_stock_propio(id_expediente);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_catastro_sp_trata ON mv_catastro_stock_propio(trata);"))

        conn.commit()
        print("¡Todas las vistas de Catastro fueron recreadas exitosamente!")

if __name__ == '__main__':
    recreate_catastro_views()
