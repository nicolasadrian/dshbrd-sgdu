-- ============================================================
-- ARCHIVO 06: mv_usos_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_usos_gedos_egreso AS
SELECT 
    id_expediente, expediente, trata, fecha_egreso
FROM mv_usos_egresos_efectivos;

CREATE INDEX idx_mvusos_gedos_egr_fecha ON mv_usos_gedos_egreso(fecha_egreso);
