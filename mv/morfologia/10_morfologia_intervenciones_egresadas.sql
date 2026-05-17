-- ============================================================
-- ARCHIVO 10: mv_morfologia_intervenciones_egresadas
-- ============================================================
-- PROPÓSITO: Intervenciones actualmente fuera del sector.
-- (destinatario actual no es analista ni buzón de la gerencia)
-- ORDEN DE EJECUCIÓN: 11°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_intervenciones_egresadas CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_intervenciones_egresadas AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
)
-- Para intervenciones, los "internos" son TODOS los buzones/usuarios de Stock Propio
-- (que ya están en analistas_oficiales - la lista incluye buzones del sector)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual           AS destino_actual,
    up.fecha_ultimo_pase             AS fecha_egreso,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_afuera
FROM mv_morfologia_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.es_trata_propia = FALSE
  AND NOT (up.destinatario_actual = ANY(cfg.analistas_oficiales));

CREATE UNIQUE INDEX idx_mvm_ine_exp ON mv_morfologia_intervenciones_egresadas(id_expediente);
CREATE INDEX idx_mvm_ine_trata ON mv_morfologia_intervenciones_egresadas(trata);


-- Validación
SELECT COUNT(*) AS total_intervenciones_egresadas FROM mv_morfologia_intervenciones_egresadas;
