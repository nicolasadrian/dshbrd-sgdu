-- ============================================================
-- ARCHIVO 06: mv_catastro_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_gedos_egreso AS
SELECT 
    id_expediente,
    expediente,
    trata,
    fecha_egreso
FROM mv_catastro_egresos_efectivos;

CREATE INDEX idx_mvct_gedos_egr_fecha ON mv_catastro_gedos_egreso(fecha_egreso);
