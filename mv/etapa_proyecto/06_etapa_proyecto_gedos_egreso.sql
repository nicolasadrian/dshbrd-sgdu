-- ============================================================
-- ARCHIVO 06: mv_etapa_proyecto_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_gedos_egreso AS
SELECT 
    id_expediente,
    expediente,
    trata,
    fecha_egreso
FROM mv_etapa_proyecto_egresos_efectivos;

CREATE INDEX idx_mvep_gedos_egr_fecha ON mv_etapa_proyecto_gedos_egreso(fecha_egreso);
