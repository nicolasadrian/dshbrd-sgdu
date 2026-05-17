-- ============================================================
-- ARCHIVO 10: mv_usos_intervenciones_egresadas
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_intervenciones_egresadas CASCADE;

CREATE MATERIALIZED VIEW mv_usos_intervenciones_egresadas AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos' AND trata_reporte = 'USOS'
)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual           AS destino_actual,
    up.fecha_ultimo_pase             AS fecha_egreso,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_afuera
FROM mv_usos_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.es_trata_propia = FALSE
  AND NOT (up.destinatario_actual = ANY(cfg.analistas_oficiales));

CREATE UNIQUE INDEX idx_mvusos_ine_exp ON mv_usos_intervenciones_egresadas(id_expediente);
