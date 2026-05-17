-- ============================================================
-- ARCHIVO 06: mv_aviso_obra_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_gedos_egreso AS
SELECT 
    id_expediente, expediente, trata, fecha_egreso
FROM mv_aviso_obra_egresos_efectivos;

CREATE INDEX idx_mvao_gedos_egr_fecha ON mv_aviso_obra_gedos_egreso(fecha_egreso);
