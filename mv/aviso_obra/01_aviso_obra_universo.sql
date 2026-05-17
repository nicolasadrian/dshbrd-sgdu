-- ============================================================
-- ARCHIVO 01: mv_aviso_obra_universo
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_universo CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_universo AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones, tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'aviso_obra' AND trata_reporte = 'AVISO DE OBRA'
),
ingresos_propios AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso)
    GROUP BY pib.id_expediente
),
ingresos_intervenciones AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso_intervenciones)
    GROUP BY pib.id_expediente
)
SELECT
    e.id_expediente, e.expediente, e.trata, e.descripcion_trata, e.descripcion, e.caratula,
    e.estado AS estado_expediente, e.fecha_creacion AS fecha_creacion_ee,
    CASE WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.primer_buzon ELSE ii.primer_buzon END AS primer_buzon_ingreso,
    CASE WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.fecha_min ELSE ii.fecha_min END AS fecha_primer_ingreso_gerencia,
    (e.trata = ANY(cfg.tratas_incluidas)) AS es_trata_propia
FROM mvw_expedientes_tratas_secgdu e
CROSS JOIN cfg
LEFT JOIN ingresos_propios ip ON ip.id_expediente = e.id_expediente
LEFT JOIN ingresos_intervenciones ii ON ii.id_expediente = e.id_expediente
WHERE
    (e.trata = ANY(cfg.tratas_incluidas) AND ip.id_expediente IS NOT NULL)
    OR
    (NOT (e.trata = ANY(cfg.tratas_incluidas)) AND ii.id_expediente IS NOT NULL);

CREATE UNIQUE INDEX idx_mvao_univ_exp ON mv_aviso_obra_universo(id_expediente);
CREATE INDEX idx_mvao_univ_propia ON mv_aviso_obra_universo(es_trata_propia);
