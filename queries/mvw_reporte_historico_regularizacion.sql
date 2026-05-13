-- REFACTOR FINAL: Reporte Histórico REGULARIZACIÓN (Súper Optimizado)
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_regularizacion CASCADE;

CREATE MATERIALIZED VIEW mvw_reporte_historico_regularizacion AS
WITH periodos AS (
    SELECT 
        EXTRACT(YEAR FROM s.d)::int as anio, EXTRACT(MONTH FROM s.d)::int as mes,
        (s.d + interval '1 month' - interval '1 day')::date as fin_mes,
        date_trunc('month', s.d)::date as inicio_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
),
lifecycle AS (
    SELECT * FROM v_expedientes_lifecycle WHERE gerencia = 'regularizacion'
),
stats_base AS (
    SELECT 
        l.trata_reporte, p.anio, p.mes,
        COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= p.inicio_mes AND l.fecha_ing <= p.fin_mes) as ing,
        COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_egr >= p.inicio_mes AND l.fecha_egr <= p.fin_mes AND l.tipo_egr = 'EFECTIVO') as egr_ef,
        COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_egr >= p.inicio_mes AND l.fecha_egr <= p.fin_mes AND l.tipo_egr = 'NO_EFECTIVO') as egr_ne,
        COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing <= p.fin_mes AND (l.fecha_egr IS NULL OR l.fecha_egr > p.fin_mes)) as stock_bruto
    FROM lifecycle l
    CROSS JOIN periodos p
    GROUP BY 1, 2, 3
),
subs_mensuales AS (
    SELECT 
        l.trata_reporte, p.anio, p.mes,
        COUNT(DISTINCT t.id_expediente) as stock_subs
    FROM mvw_pases_timeline t
    JOIN lifecycle l ON t.id_expediente = l.id_expediente
    CROSS JOIN periodos p
    WHERE t.is_subs = 1 AND t.fecha_inicio <= p.fin_mes AND (t.fecha_fin IS NULL OR t.fecha_fin > p.fin_mes)
    GROUP BY 1, 2, 3
)
SELECT 
    cfg.gerencia as "GERENCIA", cfg.trata_reporte as "COD TRATA", p.anio, p.mes,
    COALESCE(s.ing, 0) as "ING", COALESCE(s.egr_ef, 0) as "EGR_EF", COALESCE(s.egr_ne, 0) as "EGR_NE",
    COALESCE(sm.stock_subs, 0) as "STOCK_SUBS", (COALESCE(s.stock_bruto, 0) - COALESCE(sm.stock_subs, 0)) as "STOCK_PROPIO"
FROM cfg_gestion_metas cfg
CROSS JOIN periodos p
LEFT JOIN stats_base s ON cfg.trata_reporte = s.trata_reporte AND p.anio = s.anio AND p.mes = s.mes
LEFT JOIN subs_mensuales sm ON cfg.trata_reporte = sm.trata_reporte AND p.anio = sm.anio AND p.mes = sm.mes
WHERE cfg.gerencia = 'regularizacion'
ORDER BY 1, 2, 3, 4;
