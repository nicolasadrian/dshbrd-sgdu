-- ============================================================
-- ARCHIVO 06: mv_regularizacion_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_gedos_egreso AS
SELECT 
    id_expediente, expediente, trata, fecha_egreso
FROM mv_regularizacion_egresos_efectivos;

CREATE INDEX idx_mvreg_gedos_egr_fecha ON mv_regularizacion_gedos_egreso(fecha_egreso);
