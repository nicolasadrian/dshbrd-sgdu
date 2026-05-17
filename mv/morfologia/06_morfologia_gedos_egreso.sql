-- ============================================================
-- ARCHIVO 06: mv_morfologia_gedos_egreso
-- ============================================================
-- PROPÓSITO: Listar TODOS los GEDOs de egreso firmados (cada evento).
-- Útil para reportes mensuales de flujo.
-- ORDEN DE EJECUCIÓN: 7°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_gedos_egreso AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    d.documento           AS documento_egreso,
    d.acronimo            AS acronimo_egreso,
    d.fecha_creacion      AS fecha_egreso,
    d.usuario_creador     AS usuario_egreso
FROM mv_morfologia_universo u
CROSS JOIN cfg
INNER JOIN mvw_datos_gedo_secgdu d 
    ON d.id_expediente = u.id_expediente
   AND d.acronimo = ANY(cfg.acronimos_egreso)
   AND d.usuario_creador = ANY(cfg.firmantes_egreso)
WHERE u.es_trata_propia = TRUE;

CREATE INDEX idx_mvm_geg_exp ON mv_morfologia_gedos_egreso(id_expediente);
CREATE INDEX idx_mvm_geg_fecha ON mv_morfologia_gedos_egreso(fecha_egreso);
CREATE INDEX idx_mvm_geg_trata ON mv_morfologia_gedos_egreso(trata);
CREATE INDEX idx_mvm_geg_acro ON mv_morfologia_gedos_egreso(acronimo_egreso);


-- Validación
SELECT 
    acronimo_egreso,
    COUNT(*) AS cant
FROM mv_morfologia_gedos_egreso
GROUP BY acronimo_egreso
ORDER BY cant DESC;
