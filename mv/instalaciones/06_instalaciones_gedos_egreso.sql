-- ============================================================
-- ARCHIVO 06: mv_instalaciones_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_gedos_egreso AS
SELECT 
    id_expediente, expediente, trata, fecha_egreso
FROM mv_instalaciones_egresos_efectivos;

CREATE INDEX idx_mvins_gedos_egr_fecha ON mv_instalaciones_gedos_egreso(fecha_egreso);
