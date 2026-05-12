-- Vista Histórica de AVISO DE OBRA (Versión Ultra Explícita)
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_aviso_obra CASCADE;

CREATE MATERIALIZED VIEW mvw_reporte_historico_aviso_obra AS
WITH periodos AS (
    SELECT 
        EXTRACT(YEAR FROM s.d)::int as anio, 
        EXTRACT(MONTH FROM s.d)::int as mes,
        (s.d + interval '1 month' - interval '1 day')::date as fin_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
),
lifecycle_ao AS (
    SELECT 
        id_expediente, 
        gerencia as l_gerencia, 
        trata_reporte as l_trata_reporte, 
        fecha_ing, 
        fecha_egr, 
        tipo_egr 
    FROM v_expedientes_lifecycle 
    WHERE gerencia = 'aviso_obra'
)
SELECT 
    cfg.gerencia as "GERENCIA",
    cfg.trata_reporte as "COD TRATA",
    CASE 
        WHEN cfg.trata_reporte = 'INTERVENCIONES' THEN 'INTERVENCIONES'
        ELSE (SELECT descripcion FROM mvw_expedientes_tratas_secgdu WHERE trata = cfg.tratas_incluidas[1] LIMIT 1) 
    END as "DETALLE TRATA",
    per.anio,
    per.mes,
    COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= date_trunc('month', per.fin_mes) AND l.fecha_ing <= per.fin_mes) as "ING",
    COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_egr >= date_trunc('month', per.fin_mes) AND l.fecha_egr <= per.fin_mes AND l.tipo_egr = 'EFECTIVO') as "EGR_EF",
    COUNT(DISTINCT l.id_expediente) FILTER (
        WHERE l.fecha_egr >= date_trunc('month', per.fin_mes) 
          AND l.fecha_egr <= per.fin_mes 
          AND l.tipo_egr = 'NO_EFECTIVO'
          AND l.l_trata_reporte != 'INTERVENCIONES'
    ) as "EGR_NE",
    0 as "STOCK_SUBS",
    COUNT(DISTINCT l.id_expediente) FILTER (
        WHERE l.fecha_ing <= per.fin_mes 
          AND (l.fecha_egr IS NULL OR l.fecha_egr > per.fin_mes)
    ) as "STOCK_PROPIO",
    array_to_string(cfg.acronimos_egreso, ', ') as acronimos
FROM cfg_gestion_metas cfg
CROSS JOIN periodos per
LEFT JOIN lifecycle_ao l ON cfg.trata_reporte = l.l_trata_reporte
WHERE cfg.gerencia = 'aviso_obra'
GROUP BY cfg.gerencia, cfg.trata_reporte, cfg.tratas_incluidas, per.anio, per.mes, cfg.acronimos_egreso
ORDER BY 1, 2, 4, 5;

CREATE INDEX idx_hist_ao_trata ON mvw_reporte_historico_aviso_obra ("COD TRATA");
CREATE INDEX idx_hist_ao_periodo ON mvw_reporte_historico_aviso_obra (anio, mes);
