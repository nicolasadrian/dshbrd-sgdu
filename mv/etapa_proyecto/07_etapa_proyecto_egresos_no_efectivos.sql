-- ============================================================
-- ARCHIVO 07: mv_etapa_proyecto_egresos_no_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_egresos_no_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_egresos_no_efectivos AS
SELECT
    u.id_expediente, u.expediente, u.trata,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.fecha_ultimo_pase                                                AS fecha_ultimo_movimiento,
    up.destinatario_actual                                              AS poseedor_actual
FROM mv_etapa_proyecto_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
LEFT JOIN mv_etapa_proyecto_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
WHERE u.es_trata_propia = TRUE
  AND u.estado_expediente = 'Guarda Temporal'
  AND eef.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvep_ene_exp ON mv_etapa_proyecto_egresos_no_efectivos(id_expediente);
CREATE INDEX idx_mvep_egrne_fecha ON mv_etapa_proyecto_egresos_no_efectivos(fecha_ultimo_movimiento);
