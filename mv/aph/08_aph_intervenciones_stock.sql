-- ============================================================
-- ARCHIVO 08: mv_aph_intervenciones_stock
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_intervenciones_stock CASCADE;

CREATE MATERIALIZED VIEW mv_aph_intervenciones_stock AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aph' AND trata_reporte = 'APH'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_aph_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvaph_interv_stock_exp ON mv_aph_intervenciones_stock(id_expediente);
