-- ============================================================
-- ARCHIVO 06: mv_aph_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_aph_gedos_egreso AS
SELECT 
    id_expediente, expediente, trata, fecha_egreso
FROM mv_aph_egresos_efectivos;

CREATE INDEX idx_mvaph_gedos_egr_fecha ON mv_aph_gedos_egreso(fecha_egreso);
