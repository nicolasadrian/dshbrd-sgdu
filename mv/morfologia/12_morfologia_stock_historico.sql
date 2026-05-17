-- ============================================================
-- ARCHIVO 12: mv_morfologia_stock_historico
-- ============================================================
-- PROPÓSITO: Stock histórico mensual rolling 12 meses.
-- Replica la lógica corregida de Instalaciones:
--   - Detecta subsanaciones por FECHAS (no por estado actual).
--   - Filtra por nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'.
-- ORDEN DE EJECUCIÓN: 13° (último, es el más pesado).
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_stock_historico CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_stock_historico AS
WITH cfg AS (
    SELECT analistas_oficiales, tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
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
        u.es_trata_propia,
        fc.fecha_corte,
        p.destinatario AS destinatario_cierre
    FROM mv_morfologia_universo u
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
    CROSS JOIN cfg
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente
       AND a.usuario_alta = ANY(cfg.analistas_oficiales)
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
)
SELECT
    dpc.fecha_corte                                AS mes_cierre,
    TO_CHAR(dpc.fecha_corte, 'YYYY-MM')            AS mes_label,
    dpc.trata,
    dpc.es_trata_propia,
    CASE 
        WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION'
        ELSE 'STOCK_PROPIO'
    END AS categoria,
    COUNT(*) AS cant_expedientes
FROM destinatario_por_corte dpc
LEFT JOIN subsanacion_abierta_al_cierre sac 
    ON sac.id_expediente = dpc.id_expediente
   AND sac.fecha_corte = dpc.fecha_corte
CROSS JOIN cfg
WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
GROUP BY dpc.fecha_corte, dpc.trata, dpc.es_trata_propia,
         CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION' ELSE 'STOCK_PROPIO' END;

CREATE INDEX idx_mvm_sh_mes ON mv_morfologia_stock_historico(mes_cierre);
CREATE INDEX idx_mvm_sh_trata ON mv_morfologia_stock_historico(trata);
CREATE INDEX idx_mvm_sh_categoria ON mv_morfologia_stock_historico(categoria);
CREATE INDEX idx_mvm_sh_propia ON mv_morfologia_stock_historico(es_trata_propia);


-- Validación
SELECT 
    mes_label,
    es_trata_propia,
    categoria,
    SUM(cant_expedientes) AS total
FROM mv_morfologia_stock_historico
GROUP BY mes_label, mes_cierre, es_trata_propia, categoria
ORDER BY mes_cierre, es_trata_propia DESC, categoria;
