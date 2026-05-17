-- ============================================================
-- CONTABLE 07: mv_contable_egresos_no_efectivos
-- ============================================================
-- ORDEN DE EJECUCIÓN: 8°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_egresos_no_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_contable_egresos_no_efectivos AS
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.descripcion, u.caratula, u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.fecha_ultimo_pase                                                AS fecha_ultimo_movimiento,
    up.destinatario_actual                                              AS poseedor_actual,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)                         AS dias_desde_guarda,
    (up.fecha_ultimo_pase::date - u.fecha_primer_ingreso_gerencia::date) AS dias_tramitacion_aprox
FROM mv_contable_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
LEFT JOIN mv_contable_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
WHERE u.es_trata_propia = TRUE
  AND u.estado_expediente = 'Guarda Temporal'
  AND eef.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvc_ene_exp ON mv_contable_egresos_no_efectivos(id_expediente);
CREATE INDEX idx_mvc_ene_trata ON mv_contable_egresos_no_efectivos(trata);
CREATE INDEX idx_mvc_ene_fecha ON mv_contable_egresos_no_efectivos(fecha_ultimo_movimiento);


SELECT COUNT(*) AS total_egresos_no_efectivos FROM mv_contable_egresos_no_efectivos;
