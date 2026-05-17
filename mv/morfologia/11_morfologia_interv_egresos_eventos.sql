-- ============================================================
-- ARCHIVO 11: mv_morfologia_interv_egresos_eventos
-- ============================================================
-- PROPÓSITO: Eventos de egreso de intervenciones (pases a destinos externos).
-- REGLA NUEVA (a partir de Morfología): si un mismo expediente entró
-- varias veces para intervención, se cuenta SOLO el ÚLTIMO egreso.
-- No es "todos los pases externos", es "la fecha más reciente de salida".
-- ORDEN DE EJECUCIÓN: 12°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_interv_egresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_interv_egresos_eventos AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
),
pases_externos AS (
    -- Todos los pases a destinos externos (destinatario NO está en analistas_oficiales)
    SELECT 
        u.id_expediente,
        u.expediente,
        u.trata,
        u.descripcion_trata,
        p.fecha          AS fecha_egreso,
        p.usuario        AS usuario_que_envia,
        p.destinatario   AS destino_externo,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY p.fecha DESC) AS rn
    FROM mv_morfologia_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente
    WHERE u.es_trata_propia = FALSE
      AND NOT (p.destinatario = ANY(cfg.analistas_oficiales))
)
-- Tomamos solo el último egreso de cada expediente (rn = 1 con ORDER BY DESC)
SELECT 
    id_expediente,
    expediente,
    trata,
    descripcion_trata,
    fecha_egreso,
    usuario_que_envia,
    destino_externo
FROM pases_externos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvm_iev_exp ON mv_morfologia_interv_egresos_eventos(id_expediente);
CREATE INDEX idx_mvm_iev_fecha ON mv_morfologia_interv_egresos_eventos(fecha_egreso);
CREATE INDEX idx_mvm_iev_trata ON mv_morfologia_interv_egresos_eventos(trata);


-- Validación
SELECT COUNT(*) AS total_egresos_intervenciones FROM mv_morfologia_interv_egresos_eventos;
