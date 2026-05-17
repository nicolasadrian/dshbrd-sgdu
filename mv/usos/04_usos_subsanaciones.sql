-- ============================================================
-- ARCHIVO 04: mv_usos_subsanaciones
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_subsanaciones CASCADE;

CREATE MATERIALIZED VIEW mv_usos_subsanaciones AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos' AND trata_reporte = 'USOS'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_usos_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvusos_subs_exp ON mv_usos_subsanaciones(id_expediente);
