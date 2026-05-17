-- ============================================================
-- ARCHIVO 09: mv_instalaciones_intervenciones_subs
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_intervenciones_subs CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_intervenciones_subs AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'instalaciones' AND trata_reporte = 'INSTALACIONES'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_instalaciones_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvins_interv_subs_exp ON mv_instalaciones_intervenciones_subs(id_expediente);
