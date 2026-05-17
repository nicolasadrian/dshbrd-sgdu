-- ============================================================
-- ARCHIVO 05: mv_regularizacion_egresos_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_egresos_efectivos AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME'
),
egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_regularizacion_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo = ANY(cfg.acronimos_egreso)
    WHERE u.es_trata_propia = TRUE
      -- Filtro especial para MDUG3001A: Solo IFPCO y expedientes anteriores al 2026
      AND (
          (u.trata = 'MDUG3001A' AND d.acronimo = 'IFPCO' AND EXTRACT(YEAR FROM u.fecha_creacion_ee) < 2026)
          OR
          (u.trata = 'MDUG0104A' AND d.acronimo = 'IFROC')
          OR
          (u.trata = 'MDUG0141A' AND d.acronimo IN ('IFPCO', 'IFSMI'))
          OR
          (u.trata = 'MDUG1501K' AND d.acronimo = 'IFPDO')
      )
      AND (cfg.firmantes_egreso IS NULL OR d.usuario_creador = ANY(cfg.firmantes_egreso))
)
SELECT 
    id_expediente, expediente, trata,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvreg_eef_exp ON mv_regularizacion_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvreg_egref_fecha ON mv_regularizacion_egresos_efectivos(fecha_egreso);
