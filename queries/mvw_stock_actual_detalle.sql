-- Refactor de Vista de detalle para el Stock Actual (Super Optimizado)
-- Esta versión busca DIRECTAMENTE quién tiene el expediente hoy,
-- garantizando que el total coincida con el Stock Propio Actual del área.

DROP MATERIALIZED VIEW IF EXISTS mvw_stock_actual_detalle CASCADE;

CREATE MATERIALIZED VIEW mvw_stock_actual_detalle AS
WITH last_pases AS (
    SELECT DISTINCT ON (id_expediente) id_expediente, destinatario as analista, fecha, estado
    FROM mvw_ee_pases_secgdu
    ORDER BY id_expediente, fecha DESC
),
-- Identificamos todos los expedientes que están en poder de un analista o buzón oficial
stock_candidatos AS (
    SELECT lp.id_expediente, lp.analista as analista_actual, lp.fecha as fecha_ultimo_pase, lp.estado,
           cfg.gerencia, cfg.trata_reporte, cfg.tratas_incluidas, cfg.acronimos_egreso
    FROM last_pases lp
    JOIN cfg_gestion_metas cfg ON (lp.analista = ANY(cfg.analistas_oficiales) OR lp.analista = ANY(cfg.buzones_ingreso))
),
-- Filtramos por el trámite correcto (Trámite específico o Intervenciones)
stock_filtrado AS (
    SELECT s.*, et.trata, et.descripcion, et.expediente, et.fecha_creacion
    FROM stock_candidatos s
    JOIN mvw_expedientes_tratas_secgdu et ON s.id_expediente = et.id_expediente
    WHERE (
        (s.trata_reporte != 'INTERVENCIONES' AND et.trata = ANY(s.tratas_incluidas))
        OR
        (s.trata_reporte = 'INTERVENCIONES' AND et.trata != ALL(
            SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = s.gerencia AND trata_reporte != 'INTERVENCIONES'
        ))
    )
),
-- Eliminamos los que ya tienen un egreso efectivo (GEDO) posterior al último pase
egresos_gedo AS (
    SELECT DISTINCT ON (g.id_expediente, s.gerencia, s.trata_reporte) g.id_expediente, s.gerencia, s.trata_reporte
    FROM mvw_datos_gedo_secgdu g
    JOIN stock_filtrado s ON g.id_expediente = s.id_expediente
    WHERE g.acronimo = ANY(s.acronimos_egreso) AND g.fecha_creacion >= s.fecha_ultimo_pase
    ORDER BY g.id_expediente, s.gerencia, s.trata_reporte
)
SELECT 
    f.id_expediente,
    f.expediente,
    f.analista_actual,
    f.fecha_ultimo_pase,
    f.fecha_creacion::date as fecha_ing, -- Fecha simplificada para velocidad
    CURRENT_DATE - f.fecha_ultimo_pase::date as dias_ultimo_movimiento,
    CURRENT_DATE - f.fecha_ultimo_pase::date as dias_stock, -- Alias para compatibilidad
    f.trata,
    f.descripcion,
    CASE WHEN f.estado ILIKE 'Subsanaci%' THEN 1 ELSE 0 END as is_subs,
    f.gerencia,
    f.trata_reporte
FROM stock_filtrado f
LEFT JOIN egresos_gedo eg ON f.id_expediente = eg.id_expediente AND f.gerencia = eg.gerencia AND f.trata_reporte = eg.trata_reporte
WHERE eg.id_expediente IS NULL;

-- Índices para performance
CREATE INDEX idx_stock_det_trata ON mvw_stock_actual_detalle (trata);
CREATE INDEX idx_stock_det_analista ON mvw_stock_actual_detalle (analista_actual);
CREATE INDEX idx_stock_det_gerencia ON mvw_stock_actual_detalle (gerencia);
CREATE INDEX idx_stock_det_reporte ON mvw_stock_actual_detalle (trata_reporte);
