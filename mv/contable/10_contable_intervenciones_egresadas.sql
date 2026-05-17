-- ============================================================
-- CONTABLE 10: mv_contable_intervenciones_egresadas
-- ============================================================
-- ORDEN DE EJECUCIÓN: 11°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_intervenciones_egresadas CASCADE;

CREATE MATERIALIZED VIEW mv_contable_intervenciones_egresadas AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'contable' AND trata_reporte = 'CONTABLE'
)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual           AS destino_actual,
    up.fecha_ultimo_pase             AS fecha_egreso,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_afuera
FROM mv_contable_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.es_trata_propia = FALSE
  AND NOT (up.destinatario_actual = ANY(cfg.analistas_oficiales));

CREATE UNIQUE INDEX idx_mvc_ine_exp ON mv_contable_intervenciones_egresadas(id_expediente);
CREATE INDEX idx_mvc_ine_trata ON mv_contable_intervenciones_egresadas(trata);


SELECT COUNT(*) AS total_intervenciones_egresadas FROM mv_contable_intervenciones_egresadas;
