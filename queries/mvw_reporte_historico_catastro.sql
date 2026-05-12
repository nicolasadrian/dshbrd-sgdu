-- Refactor de Vista Histórica de CATASTRO usando el modelo Unificado
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_catastro CASCADE;

CREATE MATERIALIZED VIEW mvw_reporte_historico_catastro AS
WITH periodos AS (
    SELECT 
        EXTRACT(YEAR FROM s.d)::int as anio, 
        EXTRACT(MONTH FROM s.d)::int as mes,
        (s.d + interval '1 month' - interval '1 day')::date as fin_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
),
lifecycle AS (
    SELECT * FROM v_expedientes_lifecycle WHERE gerencia = 'catastro'
),
subsanaciones_historicas AS (
    -- Identificar si un expediente estaba en subsanacion al final de cada mes
    -- Esto se hace cruzando los pases con los periodos
    SELECT 
        p.id_expediente,
        per.anio,
        per.mes,
        1 as is_subs
    FROM mvw_ee_pases_secgdu p
    JOIN periodos per ON p.fecha <= per.fin_mes
    JOIN (
        SELECT id_expediente, fecha, 
               LEAD(fecha) OVER (PARTITION BY id_expediente ORDER BY fecha) as fecha_fin_estado
        FROM mvw_ee_pases_secgdu
    ) p_range ON p.id_expediente = p_range.id_expediente AND p.fecha = p_range.fecha
    WHERE p.estado ILIKE 'Subsanaci%'
      AND per.fin_mes >= p.fecha 
      AND (p_range.fecha_fin_estado IS NULL OR per.fin_mes < p_range.fecha_fin_estado)
    GROUP BY 1, 2, 3
)
SELECT 
    cfg.gerencia as "GERENCIA",
    cfg.trata_reporte as "COD TRATA",
    (SELECT descripcion FROM mvw_expedientes_tratas_secgdu WHERE trata = cfg.tratas_incluidas[1] LIMIT 1) as "DETALLE TRATA",
    per.anio,
    per.mes,
    COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= date_trunc('month', per.fin_mes) AND l.fecha_ing <= per.fin_mes) as "ING",
    COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_egr >= date_trunc('month', per.fin_mes) AND l.fecha_egr <= per.fin_mes AND l.tipo_egr = 'EFECTIVO') as "EGR_EF",
    COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_egr >= date_trunc('month', per.fin_mes) AND l.fecha_egr <= per.fin_mes AND l.tipo_egr = 'NO_EFECTIVO') as "EGR_NE",
    COUNT(DISTINCT s.id_expediente) as "STOCK_SUBS",
    COUNT(DISTINCT l.id_expediente) FILTER (
        WHERE l.fecha_ing <= per.fin_mes 
          AND (l.fecha_egr IS NULL OR l.fecha_egr > per.fin_mes)
          AND NOT EXISTS (SELECT 1 FROM subsanaciones_historicas sh WHERE sh.id_expediente = l.id_expediente AND sh.anio = per.anio AND sh.mes = per.mes)
    ) as "STOCK_PROPIO",
    array_to_string(cfg.acronimos_egreso, ', ') as acronimos
FROM cfg_gestion_metas cfg
CROSS JOIN periodos per
LEFT JOIN lifecycle l ON cfg.trata_reporte = l.trata_reporte
LEFT JOIN subsanaciones_historicas s ON l.id_expediente = s.id_expediente AND per.anio = s.anio AND per.mes = s.mes
WHERE cfg.gerencia = 'catastro'
GROUP BY 1, 2, 3, 4, 5, cfg.acronimos_egreso
ORDER BY 1, 2, 4, 5;

CREATE INDEX idx_hist_cat_trata ON mvw_reporte_historico_catastro ("COD TRATA");
CREATE INDEX idx_hist_cat_periodo ON mvw_reporte_historico_catastro (anio, mes);
