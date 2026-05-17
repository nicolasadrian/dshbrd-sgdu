-- ============================================================
-- CONTABLE 05: mv_contable_egresos_efectivos
-- ============================================================
-- PROPÓSITO: Un GEDO de egreso por expediente (el más antiguo válido).
-- Usa cfg_egresos_por_trata para reglas por (trata, acrónimo, firmante).
--
-- Reglas particulares de Contable:
--   - MDUG0901A: IF firmado SOLO por FABIANSANTILLAN o LICETB.
--   - MDUG1501J: IFPDO.
--   - MDUG3001A: IFPDO.
--   - MDUG3402A: IFPEO o IFPDO.
--
-- ORDEN DE EJECUCIÓN: 6°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_contable_egresos_efectivos AS
WITH egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
        u.descripcion, u.caratula, u.fecha_primer_ingreso_gerencia,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
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
    WHERE u.es_trata_propia = TRUE
)
SELECT 
    id_expediente, expediente, trata, descripcion_trata, descripcion, caratula,
    fecha_primer_ingreso_gerencia,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso,
    (fecha_egreso::date - fecha_primer_ingreso_gerencia::date) AS dias_tramitacion
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvc_eef_exp ON mv_contable_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvc_eef_fecha ON mv_contable_egresos_efectivos(fecha_egreso);
CREATE INDEX idx_mvc_eef_trata ON mv_contable_egresos_efectivos(trata);
CREATE INDEX idx_mvc_eef_acro ON mv_contable_egresos_efectivos(acronimo_egreso);


SELECT 
    trata,
    COUNT(*) AS cant
FROM mv_contable_egresos_efectivos
GROUP BY trata
ORDER BY cant DESC;
