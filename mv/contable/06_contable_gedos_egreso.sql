-- ============================================================
-- CONTABLE 06: mv_contable_gedos_egreso
-- ============================================================
-- PROPÓSITO: Todos los GEDOs de egreso válidos (cada evento).
-- Útil para reportes mensuales.
-- ORDEN DE EJECUCIÓN: 7°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_contable_gedos_egreso AS
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    d.documento           AS documento_egreso,
    d.acronimo            AS acronimo_egreso,
    d.fecha_creacion      AS fecha_egreso,
    d.usuario_creador     AS usuario_egreso
FROM mv_contable_universo u
INNER JOIN cfg_egresos_por_trata cep 
    ON cep.gerencia = 'contable'
   AND cep.trata    = u.trata
INNER JOIN mvw_datos_gedo_secgdu d 
    ON d.id_expediente = u.id_expediente
   AND d.acronimo      = cep.acronimo
   AND (cep.firmantes IS NULL OR d.usuario_creador = ANY(cep.firmantes))
   AND (cep.fecha_desde IS NULL OR d.fecha_creacion::date >= cep.fecha_desde)
   AND (cep.fecha_hasta IS NULL OR d.fecha_creacion::date <= cep.fecha_hasta)
WHERE u.es_trata_propia = TRUE;

CREATE INDEX idx_mvc_geg_exp ON mv_contable_gedos_egreso(id_expediente);
CREATE INDEX idx_mvc_geg_fecha ON mv_contable_gedos_egreso(fecha_egreso);
CREATE INDEX idx_mvc_geg_trata ON mv_contable_gedos_egreso(trata);
CREATE INDEX idx_mvc_geg_acro ON mv_contable_gedos_egreso(acronimo_egreso);


-- Validación: distribución por acrónimo y firmante
SELECT 
    trata,
    acronimo_egreso,
    usuario_egreso,
    COUNT(*) AS cant
FROM mv_contable_gedos_egreso
GROUP BY trata, acronimo_egreso, usuario_egreso
ORDER BY cant DESC
LIMIT 30;

-- Verificación importante: para MDUG0901A, solo deben aparecer FABIANSANTILLAN y LICETB
SELECT 
    usuario_egreso,
    COUNT(*) AS cant
FROM mv_contable_gedos_egreso
WHERE trata = 'MDUG0901A'
GROUP BY usuario_egreso
ORDER BY cant DESC;
