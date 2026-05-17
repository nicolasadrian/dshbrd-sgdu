-- ============================================================
-- APH 14: mv_aph_metas_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_metas_historico CASCADE;

CREATE MATERIALIZED VIEW mv_aph_metas_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aph'
    LIMIT 1
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        fc.fecha_corte,
        u.fecha_primer_ingreso_gerencia,
        p.destinatario AS destinatario_cierre
    FROM mv_aph_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente 
       AND a.usuario_alta = dpc.destinatario_cierre 
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte 
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
),
stock_filtrado AS (
    SELECT 
        dpc.fecha_corte,
        dpc.trata,
        dpc.fecha_primer_ingreso_gerencia
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    LEFT JOIN subsanacion_abierta_al_cierre sac 
        ON sac.id_expediente = dpc.id_expediente 
       AND sac.fecha_corte = dpc.fecha_corte
    WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
      AND COALESCE(sac.tiene_subsanacion_abierta, FALSE) IS FALSE
)
SELECT 
    fecha_corte,
    to_char(fecha_corte, 'YYYY-MM') as mes_label,
    trata,
    COUNT(*) as total_stock,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) > 90 THEN 1 ELSE 0 END) as stock_sector,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) <= 90 THEN 1 ELSE 0 END) as stock_corriente
FROM stock_filtrado
GROUP BY 1, 2, 3;

CREATE INDEX idx_mv_aph_mh_fecha ON mv_aph_metas_historico(fecha_corte);
CREATE INDEX idx_mv_aph_mh_trata ON mv_aph_metas_historico(trata);
