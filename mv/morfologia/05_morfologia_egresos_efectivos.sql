-- ============================================================
-- ARCHIVO 05: mv_morfologia_egresos_efectivos
-- ============================================================
-- PROPÓSITO: Un GEDO de egreso por expediente (el más antiguo).
-- Lógica: DI, ANEXO o IF firmado por ALANDAZURI.
-- DIFERENCIA vs Instalaciones: filtra por firmante (no solo por acrónimo).
-- ORDEN DE EJECUCIÓN: 6°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_egresos_efectivos AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
),
egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
        u.descripcion, u.caratula, u.fecha_primer_ingreso_gerencia,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_morfologia_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo = ANY(cfg.acronimos_egreso)
       AND d.usuario_creador = ANY(cfg.firmantes_egreso)
    WHERE u.es_trata_propia = TRUE
)
SELECT 
    id_expediente, expediente, trata, descripcion_trata, descripcion, caratula,
    fecha_primer_ingreso_gerencia,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso,
    (fecha_egreso::date - fecha_primer_ingreso_gerencia::date) AS dias_tramitacion
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvm_eef_exp ON mv_morfologia_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvm_eef_fecha ON mv_morfologia_egresos_efectivos(fecha_egreso);
CREATE INDEX idx_mvm_eef_trata ON mv_morfologia_egresos_efectivos(trata);
CREATE INDEX idx_mvm_eef_acro ON mv_morfologia_egresos_efectivos(acronimo_egreso);


-- Validación
SELECT COUNT(*) AS total_egresos_efectivos FROM mv_morfologia_egresos_efectivos;
