-- ============================================================
-- ARCHIVO 02: mv_morfologia_ingresos_eventos
-- ============================================================
-- PROPÓSITO: Eventos de ingreso al sector (UNO por expediente).
-- Regla: si un expediente entra más de una vez al mismo buzón,
-- solo se cuenta el primero (fecha más antigua).
-- Para propios: ingreso a DGIUR-03.
-- Para intervenciones: ingreso a cualquiera de los 6 buzones.
-- ORDEN DE EJECUCIÓN: 3°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_ingresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_ingresos_eventos AS
WITH cfg AS (
    SELECT 
        buzones_ingreso,
        buzones_ingreso_intervenciones,
        tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
),
-- Para cada expediente, identificar si es propio o intervención
-- y buscar primer pase al buzón correspondiente
expedientes_clasificados AS (
    SELECT 
        e.id_expediente,
        e.expediente,
        e.trata,
        e.descripcion_trata,
        (e.trata = ANY(cfg.tratas_incluidas)) AS es_trata_propia
    FROM mvw_expedientes_tratas_secgdu e
    CROSS JOIN cfg
),
-- Pase más antiguo al buzón correspondiente para cada expediente
primer_pase AS (
    SELECT 
        ec.id_expediente,
        ec.expediente,
        ec.trata,
        ec.descripcion_trata,
        ec.es_trata_propia,
        p.fecha,
        p.usuario,
        p.destinatario,
        ROW_NUMBER() OVER (PARTITION BY ec.id_expediente ORDER BY p.fecha ASC) AS rn
    FROM expedientes_clasificados ec
    CROSS JOIN cfg
    INNER JOIN mvw_ee_pases_secgdu p ON p.id_expediente = ec.id_expediente
    WHERE 
        -- Propios: solo cuentan pases a DGIUR-03
        (ec.es_trata_propia = TRUE  AND p.destinatario = ANY(cfg.buzones_ingreso))
        OR
        -- Intervenciones: pases a cualquiera de los 6 buzones
        (ec.es_trata_propia = FALSE AND p.destinatario = ANY(cfg.buzones_ingreso_intervenciones))
)
SELECT
    id_expediente,
    expediente,
    trata,
    descripcion_trata,
    fecha           AS fecha_ingreso,
    usuario         AS usuario_remitente,
    destinatario    AS buzon_ingreso,
    es_trata_propia
FROM primer_pase
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvm_ing_ev_exp ON mv_morfologia_ingresos_eventos(id_expediente);
CREATE INDEX idx_mvm_ing_ev_fecha ON mv_morfologia_ingresos_eventos(fecha_ingreso);
CREATE INDEX idx_mvm_ing_ev_trata ON mv_morfologia_ingresos_eventos(trata);
CREATE INDEX idx_mvm_ing_ev_propia ON mv_morfologia_ingresos_eventos(es_trata_propia);


-- Validación
SELECT 
    es_trata_propia,
    COUNT(*) AS cant
FROM mv_morfologia_ingresos_eventos
GROUP BY es_trata_propia;
