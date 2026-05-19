-- ============================================================
-- VISTA MATERIALIZADA: mvw_sla_tramites
-- CONSOLIDA CASOS RESUELTOS Y CALCULA LOS DÍAS DE TRAMITACIÓN (SLA)
-- DÍA DE CARATULACIÓN HASTA EGRESO EFECTIVO DESCONTANDO DIAS DE SUBSANACIÓN
-- LIMITADO A EXPEDIENTES INGRESADOS EN EL ÚLTIMO AÑO
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mvw_sla_tramites CASCADE;

CREATE MATERIALIZED VIEW mvw_sla_tramites AS
WITH subs_dias AS (
    SELECT 
        id_expediente,
        COALESCE(SUM(
            CASE 
                WHEN fecha_cierre IS NOT NULL THEN (fecha_cierre::date - fecha_alta::date)
                ELSE (CURRENT_DATE - fecha_alta::date)
            END
        ), 0) AS dias_subs
    FROM mvw_ee_actividades_secgdu
    WHERE nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
    GROUP BY id_expediente
)
SELECT 
    'catastro'::text AS gerencia,
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_creacion_ee::timestamp AS fecha_caratula,
    e.fecha_egreso::timestamp AS fecha_egreso,
    GREATEST(0, (e.fecha_egreso::date - u.fecha_creacion_ee::date) - COALESCE(s.dias_subs, 0)) AS dias_resolucion
FROM mv_catastro_universo u
INNER JOIN mv_catastro_egresos_efectivos e ON u.id_expediente = e.id_expediente
LEFT JOIN subs_dias s ON u.id_expediente = s.id_expediente
WHERE u.fecha_creacion_ee >= CURRENT_DATE - INTERVAL '1 year'
UNION ALL
SELECT 
    'instalaciones'::text AS gerencia,
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_creacion_ee::timestamp AS fecha_caratula,
    e.fecha_egreso::timestamp AS fecha_egreso,
    GREATEST(0, (e.fecha_egreso::date - u.fecha_creacion_ee::date) - COALESCE(s.dias_subs, 0)) AS dias_resolucion
FROM mv_instalaciones_universo u
INNER JOIN mv_instalaciones_egresos_efectivos e ON u.id_expediente = e.id_expediente
LEFT JOIN subs_dias s ON u.id_expediente = s.id_expediente
WHERE u.fecha_creacion_ee >= CURRENT_DATE - INTERVAL '1 year'
UNION ALL
SELECT 
    'regularizacion'::text AS gerencia,
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_creacion_ee::timestamp AS fecha_caratula,
    e.fecha_egreso::timestamp AS fecha_egreso,
    GREATEST(0, (e.fecha_egreso::date - u.fecha_creacion_ee::date) - COALESCE(s.dias_subs, 0)) AS dias_resolucion
FROM mv_regularizacion_universo u
INNER JOIN mv_regularizacion_egresos_efectivos e ON u.id_expediente = e.id_expediente
LEFT JOIN subs_dias s ON u.id_expediente = s.id_expediente
WHERE u.fecha_creacion_ee >= CURRENT_DATE - INTERVAL '1 year'
UNION ALL
SELECT 
    'contable'::text AS gerencia,
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_creacion_ee::timestamp AS fecha_caratula,
    e.fecha_egreso::timestamp AS fecha_egreso,
    GREATEST(0, (e.fecha_egreso::date - u.fecha_creacion_ee::date) - COALESCE(s.dias_subs, 0)) AS dias_resolucion
FROM mv_contable_universo u
INNER JOIN mv_contable_egresos_efectivos e ON u.id_expediente = e.id_expediente
LEFT JOIN subs_dias s ON u.id_expediente = s.id_expediente
WHERE u.fecha_creacion_ee >= CURRENT_DATE - INTERVAL '1 year'
UNION ALL
SELECT 
    'etapa_proyecto'::text AS gerencia,
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_creacion_ee::timestamp AS fecha_caratula,
    e.fecha_egreso::timestamp AS fecha_egreso,
    GREATEST(0, (e.fecha_egreso::date - u.fecha_creacion_ee::date) - COALESCE(s.dias_subs, 0)) AS dias_resolucion
FROM mv_etapa_proyecto_universo u
INNER JOIN mv_etapa_proyecto_egresos_efectivos e ON u.id_expediente = e.id_expediente
LEFT JOIN subs_dias s ON u.id_expediente = s.id_expediente
WHERE u.fecha_creacion_ee >= CURRENT_DATE - INTERVAL '1 year'
UNION ALL
SELECT 
    'aviso_obra'::text AS gerencia,
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_creacion_ee::timestamp AS fecha_caratula,
    e.fecha_egreso::timestamp AS fecha_egreso,
    GREATEST(0, (e.fecha_egreso::date - u.fecha_creacion_ee::date) - COALESCE(s.dias_subs, 0)) AS dias_resolucion
FROM mv_aviso_obra_universo u
INNER JOIN mv_aviso_obra_egresos_efectivos e ON u.id_expediente = e.id_expediente
LEFT JOIN subs_dias s ON u.id_expediente = s.id_expediente
WHERE u.fecha_creacion_ee >= CURRENT_DATE - INTERVAL '1 year'
UNION ALL
SELECT 
    'morfologia'::text AS gerencia,
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_creacion_ee::timestamp AS fecha_caratula,
    e.fecha_egreso::timestamp AS fecha_egreso,
    GREATEST(0, (e.fecha_egreso::date - u.fecha_creacion_ee::date) - COALESCE(s.dias_subs, 0)) AS dias_resolucion
FROM mv_morfologia_universo u
INNER JOIN mv_morfologia_egresos_efectivos e ON u.id_expediente = e.id_expediente
LEFT JOIN subs_dias s ON u.id_expediente = s.id_expediente
WHERE u.fecha_creacion_ee >= CURRENT_DATE - INTERVAL '1 year'
UNION ALL
SELECT 
    'aph'::text AS gerencia,
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_creacion_ee::timestamp AS fecha_caratula,
    e.fecha_egreso::timestamp AS fecha_egreso,
    GREATEST(0, (e.fecha_egreso::date - u.fecha_creacion_ee::date) - COALESCE(s.dias_subs, 0)) AS dias_resolucion
FROM mv_aph_universo u
INNER JOIN mv_aph_egresos_efectivos e ON u.id_expediente = e.id_expediente
LEFT JOIN subs_dias s ON u.id_expediente = s.id_expediente
WHERE u.fecha_creacion_ee >= CURRENT_DATE - INTERVAL '1 year'
UNION ALL
SELECT 
    'usos'::text AS gerencia,
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_creacion_ee::timestamp AS fecha_caratula,
    e.fecha_egreso::timestamp AS fecha_egreso,
    GREATEST(0, (e.fecha_egreso::date - u.fecha_creacion_ee::date) - COALESCE(s.dias_subs, 0)) AS dias_resolucion
FROM mv_usos_universo u
INNER JOIN mv_usos_egresos_efectivos e ON u.id_expediente = e.id_expediente
LEFT JOIN subs_dias s ON u.id_expediente = s.id_expediente
WHERE u.fecha_creacion_ee >= CURRENT_DATE - INTERVAL '1 year';

CREATE UNIQUE INDEX idx_mvw_sla_ger_exp ON mvw_sla_tramites(gerencia, id_expediente);
CREATE INDEX idx_mvw_sla_trata ON mvw_sla_tramites(trata);
CREATE INDEX idx_mvw_sla_gerencia ON mvw_sla_tramites(gerencia);
CREATE INDEX idx_mvw_sla_egreso ON mvw_sla_tramites(fecha_egreso);
