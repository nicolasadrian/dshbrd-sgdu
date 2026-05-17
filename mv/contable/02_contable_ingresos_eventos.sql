-- ============================================================
-- CONTABLE 02: mv_contable_ingresos_eventos
-- ============================================================
-- PROPÓSITO: Eventos de ingreso (UNO por expediente, el más antiguo).
-- ORDEN DE EJECUCIÓN: 3°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_ingresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_contable_ingresos_eventos AS
WITH cfg AS (
    SELECT 
        buzones_ingreso,
        buzones_ingreso_intervenciones,
        tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'contable' AND trata_reporte = 'CONTABLE'
),
expedientes_clasificados AS (
    SELECT 
        e.id_expediente, e.expediente, e.trata, e.descripcion_trata,
        (e.trata = ANY(cfg.tratas_incluidas)) AS es_trata_propia
    FROM mvw_expedientes_tratas_secgdu e
    CROSS JOIN cfg
),
primer_pase AS (
    SELECT 
        ec.id_expediente, ec.expediente, ec.trata, ec.descripcion_trata, ec.es_trata_propia,
        p.fecha, p.usuario, p.destinatario,
        ROW_NUMBER() OVER (PARTITION BY ec.id_expediente ORDER BY p.fecha ASC) AS rn
    FROM expedientes_clasificados ec
    CROSS JOIN cfg
    INNER JOIN mvw_ee_pases_secgdu p ON p.id_expediente = ec.id_expediente
    WHERE 
        (ec.es_trata_propia = TRUE  AND p.destinatario = ANY(cfg.buzones_ingreso))
        OR
        (ec.es_trata_propia = FALSE AND p.destinatario = ANY(cfg.buzones_ingreso_intervenciones))
)
SELECT
    id_expediente, expediente, trata, descripcion_trata,
    fecha           AS fecha_ingreso,
    usuario         AS usuario_remitente,
    destinatario    AS buzon_ingreso,
    es_trata_propia
FROM primer_pase
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvc_ing_ev_exp ON mv_contable_ingresos_eventos(id_expediente);
CREATE INDEX idx_mvc_ing_ev_fecha ON mv_contable_ingresos_eventos(fecha_ingreso);
CREATE INDEX idx_mvc_ing_ev_trata ON mv_contable_ingresos_eventos(trata);
CREATE INDEX idx_mvc_ing_ev_propia ON mv_contable_ingresos_eventos(es_trata_propia);


-- Validación
SELECT es_trata_propia, COUNT(*) AS cant
FROM mv_contable_ingresos_eventos
GROUP BY es_trata_propia;
