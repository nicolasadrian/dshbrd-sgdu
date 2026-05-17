-- ============================================================
-- ARCHIVO 05: mv_usos_egresos_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_usos_egresos_efectivos AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos' AND trata_reporte = 'USOS'
),
egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_usos_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo = ANY(cfg.acronimos_egreso)
    WHERE u.es_trata_propia = TRUE
      AND (cfg.firmantes_egreso IS NULL OR d.usuario_creador = ANY(cfg.firmantes_egreso))
)
SELECT 
    id_expediente, expediente, trata,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvusos_eef_exp ON mv_usos_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvusos_egref_fecha ON mv_usos_egresos_efectivos(fecha_egreso);
