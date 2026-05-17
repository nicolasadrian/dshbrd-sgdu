-- ============================================================
-- CONSULTAS DE METAS Y SEGMENTACIÓN DE STOCK
-- ============================================================

-- 1. PROMEDIOS DE INGRESOS Y EGRESOS (EJEMPLO PARA UNA GERENCIA)
-- Reemplazar {gerencia} por el nombre de la gerencia (ej. catastro, etapa_proyecto)

/*
WITH range AS (
    SELECT date_trunc('month', CURRENT_DATE - INTERVAL '6 months') as start_date
),
ing_m AS (
    SELECT trata, to_char(fecha_ingreso, 'YYYY-MM') as mes, COUNT(*) as cant
    FROM mv_{gerencia}_ingresos_eventos
    WHERE fecha_ingreso >= (SELECT start_date FROM range)
    GROUP BY 1, 2
),
eef_m AS (
    SELECT trata, to_char(fecha_egreso, 'YYYY-MM') as mes, COUNT(*) as cant
    FROM mv_{gerencia}_gedos_egreso
    WHERE fecha_egreso >= (SELECT start_date FROM range)
    GROUP BY 1, 2
),
ene_m AS (
    SELECT trata, to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes, COUNT(*) as cant
    FROM mv_{gerencia}_egresos_no_efectivos
    WHERE fecha_ultimo_movimiento >= (SELECT start_date FROM range)
    GROUP BY 1, 2
),
tratas AS (
    SELECT DISTINCT trata FROM (SELECT trata FROM ing_m UNION SELECT trata FROM eef_m UNION SELECT trata FROM ene_m) s
)
SELECT 
    t.trata,
    COALESCE(et.descripcion_trata, t.trata) as "Nombre Trámite",
    COALESCE(AVG(i.cant), 0)::float as "Promedio Ingresos",
    COALESCE(AVG(ef.cant), 0)::float as "Promedio Egresos Ef.",
    COALESCE(AVG(ne.cant), 0)::float as "Promedio Egresos NE"
FROM tratas t
LEFT JOIN mvw_expedientes_tratas_secgdu et ON et.trata = t.trata
LEFT JOIN ing_m i ON i.trata = t.trata
LEFT JOIN egr_ef ef ON ef.trata = t.trata AND ef.mes = i.mes
LEFT JOIN ene_m ne ON ne.trata = t.trata AND ne.mes = i.mes
GROUP BY 1, 2;
*/

-- 2. SEGMENTACIÓN DE STOCK: CORRIENTE vs SECTOR
-- Stock Corriente: <= 90 días (3 meses)
-- Stock Sector: > 90 días

/*
WITH full_stock AS (
    SELECT trata, dias_en_gerencia FROM mv_{gerencia}_stock_propio
    UNION ALL
    SELECT trata, dias_en_gerencia FROM mv_{gerencia}_subsanaciones
)
SELECT 
    trata,
    COUNT(*) FILTER (WHERE dias_en_gerencia <= 90) as "Stock Corriente (<= 3 meses)",
    COUNT(*) FILTER (WHERE dias_en_gerencia > 90) as "Stock Sector (> 3 meses)",
    COUNT(*) as "Total Stock Propio"
FROM full_stock
GROUP BY 1;
*/

-- 3. VISTA CONSOLIDADA (EJEMPLO PARA ETAPA PROYECTO)
WITH full_stock AS (
    SELECT trata, dias_en_gerencia FROM mv_etapa_proyecto_stock_propio
    UNION ALL
    SELECT trata, dias_en_gerencia FROM mv_etapa_proyecto_subsanaciones
)
SELECT 
    trata,
    COUNT(*) FILTER (WHERE dias_en_gerencia <= 90) as "Stock Corriente",
    COUNT(*) FILTER (WHERE dias_en_gerencia > 90) as "Stock Sector",
    ROUND(COUNT(*) FILTER (WHERE dias_en_gerencia > 90) * 100.0 / NULLIF(COUNT(*), 0), 2) as "% Envejecido"
FROM full_stock
GROUP BY 1;
