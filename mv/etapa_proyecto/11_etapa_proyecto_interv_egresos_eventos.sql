-- ============================================================
-- ARCHIVO 11: mv_etapa_proyecto_interv_egresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_interv_egresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_interv_egresos_eventos AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'etapa_proyecto' AND trata_reporte = 'ETAPA PROYECTO'
),
pases_externos AS (
    SELECT 
        u.id_expediente,
        u.expediente,
        u.trata,
        u.descripcion_trata,
        p.fecha          AS fecha_egreso,
        p.usuario        AS usuario_que_envia,
        p.destinatario   AS destino_externo,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY p.fecha DESC) AS rn
    FROM mv_etapa_proyecto_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente
    WHERE u.es_trata_propia = FALSE
      AND NOT (p.destinatario = ANY(cfg.analistas_oficiales))
)
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

CREATE UNIQUE INDEX idx_mvep_iev_exp ON mv_etapa_proyecto_interv_egresos_eventos(id_expediente);
CREATE INDEX idx_mvep_iev_fecha ON mv_etapa_proyecto_interv_egresos_eventos(fecha_egreso);
