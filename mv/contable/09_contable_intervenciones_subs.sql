-- ============================================================
-- CONTABLE 09: mv_contable_intervenciones_subs
-- ============================================================
-- ORDEN DE EJECUCIÓN: 10°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_intervenciones_subs CASCADE;

CREATE MATERIALIZED VIEW mv_contable_intervenciones_subs AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'contable' AND trata_reporte = 'CONTABLE'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    a.nombre_tipo_actividad           AS tipo_subsanacion,
    a.fecha_alta                      AS fecha_apertura_subsanacion,
    (CURRENT_DATE - a.fecha_alta::date) AS dias_subsanacion_abierta
FROM mv_contable_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvc_isb_exp ON mv_contable_intervenciones_subs(id_expediente);
CREATE INDEX idx_mvc_isb_analista ON mv_contable_intervenciones_subs(analista);
CREATE INDEX idx_mvc_isb_trata ON mv_contable_intervenciones_subs(trata);


SELECT COUNT(*) AS total_intervenciones_subs FROM mv_contable_intervenciones_subs;
