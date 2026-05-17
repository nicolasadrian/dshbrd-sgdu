-- ============================================================
-- MIGRACIÓN 03: Recrear MVs de egresos de Morfología
-- ============================================================
-- PROPÓSITO: Usar cfg_egresos_por_trata en lugar de los arrays de cfg_gestion_metas.
-- ORDEN DE EJECUCIÓN: 3° del paquete de migración.
-- DEPENDE de: 01 y 02 ejecutados.
-- ============================================================

-- ============================================================
-- mv_morfologia_egresos_efectivos
-- ============================================================
DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_egresos_efectivos AS
WITH egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
        u.descripcion, u.caratula, u.fecha_primer_ingreso_gerencia,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_morfologia_universo u
    INNER JOIN cfg_egresos_por_trata cep 
        ON cep.gerencia = 'morfologia'
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

CREATE UNIQUE INDEX idx_mvm_eef_exp ON mv_morfologia_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvm_eef_fecha ON mv_morfologia_egresos_efectivos(fecha_egreso);
CREATE INDEX idx_mvm_eef_trata ON mv_morfologia_egresos_efectivos(trata);
CREATE INDEX idx_mvm_eef_acro ON mv_morfologia_egresos_efectivos(acronimo_egreso);


-- ============================================================
-- mv_morfologia_gedos_egreso
-- ============================================================
DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_gedos_egreso AS
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    d.documento           AS documento_egreso,
    d.acronimo            AS acronimo_egreso,
    d.fecha_creacion      AS fecha_egreso,
    d.usuario_creador     AS usuario_egreso
FROM mv_morfologia_universo u
INNER JOIN cfg_egresos_por_trata cep 
    ON cep.gerencia = 'morfologia'
   AND cep.trata    = u.trata
INNER JOIN mvw_datos_gedo_secgdu d 
    ON d.id_expediente = u.id_expediente
   AND d.acronimo      = cep.acronimo
   AND (cep.firmantes IS NULL OR d.usuario_creador = ANY(cep.firmantes))
   AND (cep.fecha_desde IS NULL OR d.fecha_creacion::date >= cep.fecha_desde)
   AND (cep.fecha_hasta IS NULL OR d.fecha_creacion::date <= cep.fecha_hasta)
WHERE u.es_trata_propia = TRUE;

CREATE INDEX idx_mvm_geg_exp ON mv_morfologia_gedos_egreso(id_expediente);
CREATE INDEX idx_mvm_geg_fecha ON mv_morfologia_gedos_egreso(fecha_egreso);
CREATE INDEX idx_mvm_geg_trata ON mv_morfologia_gedos_egreso(trata);
CREATE INDEX idx_mvm_geg_acro ON mv_morfologia_gedos_egreso(acronimo_egreso);


-- ============================================================
-- mv_morfologia_egresos_no_efectivos (recreada por CASCADE)
-- ============================================================
DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_egresos_no_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_egresos_no_efectivos AS
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.descripcion, u.caratula, u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.fecha_ultimo_pase                                                AS fecha_ultimo_movimiento,
    up.destinatario_actual                                              AS poseedor_actual,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)                         AS dias_desde_guarda,
    (up.fecha_ultimo_pase::date - u.fecha_primer_ingreso_gerencia::date) AS dias_tramitacion_aprox
FROM mv_morfologia_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
LEFT JOIN mv_morfologia_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
WHERE u.es_trata_propia = TRUE
  AND u.estado_expediente = 'Guarda Temporal'
  AND eef.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvm_ene_exp ON mv_morfologia_egresos_no_efectivos(id_expediente);
CREATE INDEX idx_mvm_ene_trata ON mv_morfologia_egresos_no_efectivos(trata);
CREATE INDEX idx_mvm_ene_fecha ON mv_morfologia_egresos_no_efectivos(fecha_ultimo_movimiento);


-- ============================================================
-- VALIDACIÓN
-- ============================================================
SELECT
    (SELECT COUNT(*) FROM mv_morfologia_egresos_efectivos)        AS egresos_efectivos,
    (SELECT COUNT(*) FROM mv_morfologia_gedos_egreso)             AS gedos_totales,
    (SELECT COUNT(*) FROM mv_morfologia_egresos_no_efectivos)     AS egresos_no_efectivos;

-- Validar que los GEDOs son SOLO firmados por ALANDAZURI
SELECT 
    usuario_egreso, 
    acronimo_egreso, 
    COUNT(*) AS cant
FROM mv_morfologia_gedos_egreso
GROUP BY usuario_egreso, acronimo_egreso
ORDER BY cant DESC
LIMIT 10;
-- Esperado: solo aparece ALANDAZURI como usuario_egreso
