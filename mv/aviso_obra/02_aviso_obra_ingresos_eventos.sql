-- ============================================================
-- ARCHIVO 02: mv_aviso_obra_ingresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_ingresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_ingresos_eventos AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones
    FROM cfg_gestion_metas
    WHERE gerencia = 'aviso_obra' AND trata_reporte = 'AVISO DE OBRA'
)
SELECT 
    pib.id_expediente, univ.expediente, pib.fecha_primer_ingreso AS fecha_ingreso,
    pib.buzon, univ.trata, univ.es_trata_propia
FROM mv_primer_ingreso_buzon pib
JOIN mv_aviso_obra_universo univ ON univ.id_expediente = pib.id_expediente
CROSS JOIN cfg
WHERE 
    (univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso))
    OR
    (NOT univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso_intervenciones));

CREATE INDEX idx_mvao_ing_fecha ON mv_aviso_obra_ingresos_eventos(fecha_ingreso);
