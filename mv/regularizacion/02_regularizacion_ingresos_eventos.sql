-- ============================================================
-- ARCHIVO 02: mv_regularizacion_ingresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_ingresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_ingresos_eventos AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME'
)
SELECT 
    pib.id_expediente, univ.expediente, pib.fecha_primer_ingreso AS fecha_ingreso,
    pib.buzon, univ.trata, univ.es_trata_propia
FROM mv_primer_ingreso_buzon pib
JOIN mv_regularizacion_universo univ ON univ.id_expediente = pib.id_expediente
CROSS JOIN cfg
WHERE 
    (univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso))
    OR
    (NOT univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso_intervenciones));

CREATE INDEX idx_mvreg_ing_fecha ON mv_regularizacion_ingresos_eventos(fecha_ingreso);
