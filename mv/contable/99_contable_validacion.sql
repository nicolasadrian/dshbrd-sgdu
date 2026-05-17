-- ============================================================
-- CONTABLE 99: Validación completa
-- ============================================================
-- Ejecutar DESPUÉS de crear todas las MVs.
-- ============================================================

-- ===========================================
-- 1) Universo
-- ===========================================
SELECT es_trata_propia, COUNT(*) AS cant
FROM mv_contable_universo
GROUP BY es_trata_propia;

SELECT 
    es_trata_propia, trata, descripcion_trata, COUNT(*) AS cant
FROM mv_contable_universo
GROUP BY es_trata_propia, trata, descripcion_trata
ORDER BY es_trata_propia DESC, cant DESC;


-- ===========================================
-- 2) Categorías por trata propia
-- ===========================================
SELECT
    (SELECT COUNT(*) FROM mv_contable_stock_propio)            AS stock_propio,
    (SELECT COUNT(*) FROM mv_contable_subsanaciones)           AS subsanaciones,
    (SELECT COUNT(*) FROM mv_contable_egresos_efectivos)       AS egresos_efectivos,
    (SELECT COUNT(*) FROM mv_contable_egresos_no_efectivos)    AS egresos_no_efectivos;


-- ===========================================
-- 3) Coherencia
-- ===========================================
SELECT 
    (SELECT COUNT(*) FROM mv_contable_universo WHERE es_trata_propia)  AS total_universo_propio,
    COUNT(DISTINCT id_expediente)                                       AS expedientes_unicos_clasificados
FROM (
    SELECT id_expediente FROM mv_contable_stock_propio
    UNION ALL
    SELECT id_expediente FROM mv_contable_subsanaciones
    UNION ALL
    SELECT id_expediente FROM mv_contable_egresos_efectivos
    UNION ALL
    SELECT id_expediente FROM mv_contable_egresos_no_efectivos
) t;

-- Duplicados (no debería haber)
SELECT id_expediente, COUNT(*) AS apariciones
FROM (
    SELECT id_expediente FROM mv_contable_stock_propio
    UNION ALL
    SELECT id_expediente FROM mv_contable_subsanaciones
    UNION ALL
    SELECT id_expediente FROM mv_contable_egresos_efectivos
    UNION ALL
    SELECT id_expediente FROM mv_contable_egresos_no_efectivos
) t
GROUP BY id_expediente
HAVING COUNT(*) > 1
LIMIT 20;


-- ===========================================
-- 4) Validación crítica de firmantes para MDUG0901A
-- ===========================================
-- Solo deben aparecer FABIANSANTILLAN y LICETB
SELECT 
    usuario_egreso, 
    COUNT(*) AS cant
FROM mv_contable_egresos_efectivos
WHERE trata = 'MDUG0901A'
GROUP BY usuario_egreso
ORDER BY cant DESC;


-- ===========================================
-- 5) Intervenciones
-- ===========================================
SELECT
    (SELECT COUNT(*) FROM mv_contable_universo WHERE NOT es_trata_propia)   AS universo_intervenciones,
    (SELECT COUNT(*) FROM mv_contable_intervenciones_stock)                  AS interv_stock,
    (SELECT COUNT(*) FROM mv_contable_intervenciones_subs)                   AS interv_subs,
    (SELECT COUNT(*) FROM mv_contable_intervenciones_egresadas)              AS interv_egresadas,
    (SELECT COUNT(*) FROM mv_contable_interv_egresos_eventos)                AS eventos_egreso_interv;


-- ===========================================
-- 6) Reporte mensual MAYO de trámites propios
-- ===========================================
WITH 
parametros AS (SELECT DATE '2026-05-01' AS desde, DATE '2026-06-01' AS hasta),
tratas_reporte AS (
    SELECT DISTINCT trata, descripcion_trata
    FROM mv_contable_universo
    WHERE es_trata_propia = TRUE
),
ingresos_mes AS (
    SELECT trata, COUNT(*) AS cant
    FROM mv_contable_ingresos_eventos, parametros p
    WHERE es_trata_propia = TRUE
      AND fecha_ingreso >= p.desde AND fecha_ingreso < p.hasta
    GROUP BY trata
),
egresos_efec_mes AS (
    SELECT trata, COUNT(*) AS cant
    FROM mv_contable_gedos_egreso, parametros p
    WHERE fecha_egreso >= p.desde AND fecha_egreso < p.hasta
    GROUP BY trata
),
egresos_noef_mes AS (
    SELECT trata, COUNT(*) AS cant
    FROM mv_contable_egresos_no_efectivos, parametros p
    WHERE fecha_ultimo_movimiento >= p.desde AND fecha_ultimo_movimiento < p.hasta
    GROUP BY trata
),
stock_actual AS (
    SELECT trata, COUNT(*) AS cant FROM mv_contable_stock_propio GROUP BY trata
),
subs_actual AS (
    SELECT trata, COUNT(*) AS cant FROM mv_contable_subsanaciones GROUP BY trata
)
SELECT
    tr.trata, tr.descripcion_trata,
    COALESCE(im.cant, 0)    AS ingresos_mayo,
    COALESCE(ee.cant, 0)    AS egresos_efectivos_mayo,
    COALESCE(en.cant, 0)    AS egresos_no_efectivos_mayo,
    COALESCE(sa.cant, 0)    AS stock_propio_actual,
    COALESCE(sb.cant, 0)    AS subsanaciones_actual,
    COALESCE(sa.cant, 0) + COALESCE(sb.cant, 0) AS stock_total
FROM tratas_reporte tr
LEFT JOIN ingresos_mes       im ON im.trata = tr.trata
LEFT JOIN egresos_efec_mes   ee ON ee.trata = tr.trata
LEFT JOIN egresos_noef_mes   en ON en.trata = tr.trata
LEFT JOIN stock_actual       sa ON sa.trata = tr.trata
LEFT JOIN subs_actual        sb ON sb.trata = tr.trata
ORDER BY (COALESCE(im.cant,0) + COALESCE(ee.cant,0) + COALESCE(en.cant,0)) DESC;


-- ===========================================
-- 7) Stock histórico mensual (totales por mes)
-- ===========================================
SELECT 
    mes_label,
    SUM(CASE WHEN categoria = 'STOCK_PROPIO' AND es_trata_propia THEN cant_expedientes ELSE 0 END) AS stock_propios,
    SUM(CASE WHEN categoria = 'SUBSANACION'  AND es_trata_propia THEN cant_expedientes ELSE 0 END) AS subs_propios,
    SUM(CASE WHEN categoria = 'STOCK_PROPIO' AND NOT es_trata_propia THEN cant_expedientes ELSE 0 END) AS stock_interv,
    SUM(CASE WHEN categoria = 'SUBSANACION'  AND NOT es_trata_propia THEN cant_expedientes ELSE 0 END) AS subs_interv
FROM mv_contable_stock_historico
GROUP BY mes_label, mes_cierre
ORDER BY mes_cierre;
