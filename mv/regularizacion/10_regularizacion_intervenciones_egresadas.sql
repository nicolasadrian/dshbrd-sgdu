-- ============================================================
-- ARCHIVO 10: mv_regularizacion_intervenciones_egresadas
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_intervenciones_egresadas CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_intervenciones_egresadas AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME'
)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual           AS destino_actual,
    up.fecha_ultimo_pase             AS fecha_egreso,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_afuera
FROM mv_regularizacion_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.es_trata_propia = FALSE
  AND NOT (up.destinatario_actual = ANY(cfg.analistas_oficiales));

CREATE UNIQUE INDEX idx_mvreg_ine_exp ON mv_regularizacion_intervenciones_egresadas(id_expediente);
