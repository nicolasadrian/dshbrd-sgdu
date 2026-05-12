-- Refactor de la Vista de Lifecycle (Versión Robusta)
CREATE OR REPLACE VIEW v_expedientes_lifecycle AS
WITH pases_filtrados AS (
    SELECT p.id_expediente, p.fecha, p.destinatario, p.usuario as remitente, p.estado
    FROM mvw_ee_pases_secgdu p
),
ingresos AS (
    SELECT 
        p.id_expediente, 
        cfg.gerencia as l_gerencia, 
        cfg.trata_reporte as l_trata_reporte,
        MIN(p.fecha)::date as fecha_ing
    FROM pases_filtrados p
    JOIN mvw_expedientes_tratas_secgdu et ON p.id_expediente = et.id_expediente
    JOIN cfg_gestion_metas cfg ON (
        (cfg.trata_reporte != 'INTERVENCIONES' AND et.trata = ANY(cfg.tratas_incluidas))
        OR 
        (cfg.trata_reporte = 'INTERVENCIONES' AND et.trata != ALL(cfg.tratas_incluidas))
    )
    WHERE p.destinatario = ANY(cfg.buzones_ingreso)
    GROUP BY 1, 2, 3
),
egresos_gedo AS (
    SELECT 
        g.id_expediente, 
        i.l_gerencia,
        i.l_trata_reporte,
        MIN(g.fecha_creacion)::date as fecha_egr,
        'EFECTIVO'::text as tipo_egr
    FROM mvw_datos_gedo_secgdu g
    JOIN ingresos i ON g.id_expediente = i.id_expediente
    JOIN cfg_gestion_metas cfg ON (cfg.gerencia = i.l_gerencia AND cfg.trata_reporte = i.l_trata_reporte)
    WHERE g.acronimo = ANY(cfg.acronimos_egreso) AND g.fecha_creacion >= i.fecha_ing
    GROUP BY 1, 2, 3
),
egresos_pases AS (
    SELECT 
        p.id_expediente,
        i.l_gerencia,
        i.l_trata_reporte,
        CASE 
            WHEN i.l_trata_reporte = 'INTERVENCIONES' THEN MAX(p.fecha)::date 
            ELSE MIN(p.fecha)::date 
        END as fecha_egr,
        'NO_EFECTIVO'::text as tipo_egr
    FROM pases_filtrados p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    JOIN cfg_gestion_metas cfg ON (cfg.gerencia = i.l_gerencia AND cfg.trata_reporte = i.l_trata_reporte)
    WHERE p.fecha > i.fecha_ing 
      AND p.remitente = ANY(cfg.analistas_oficiales)
      AND p.destinatario != ANY(cfg.analistas_oficiales)
      AND p.destinatario != ANY(cfg.buzones_ingreso)
      AND (
          i.l_trata_reporte != 'INTERVENCIONES' AND p.estado NOT ILIKE 'Subsanaci%'
          OR 
          i.l_trata_reporte = 'INTERVENCIONES'
      )
    GROUP BY 1, 2, 3
),
egresos_unificados AS (
    SELECT id_expediente, l_gerencia, l_trata_reporte, fecha_egr, tipo_egr FROM egresos_gedo
    UNION ALL
    SELECT id_expediente, l_gerencia, l_trata_reporte, fecha_egr, tipo_egr FROM egresos_pases
),
egresos_final AS (
    SELECT 
        id_expediente, 
        l_gerencia, 
        l_trata_reporte, 
        CASE 
            WHEN l_trata_reporte = 'INTERVENCIONES' THEN MAX(fecha_egr)
            ELSE MIN(fecha_egr)
        END as fecha_egr, 
        tipo_egr
    FROM egresos_unificados
    GROUP BY 1, 2, 3, 5
)
SELECT 
    i.id_expediente,
    i.l_gerencia as gerencia,
    i.l_trata_reporte as trata_reporte,
    i.fecha_ing,
    e.fecha_egr,
    e.tipo_egr,
    CASE 
        WHEN e.fecha_egr IS NULL THEN 'ACTIVO'
        ELSE 'CERRADO'
    END as status_gestion
FROM ingresos i
LEFT JOIN egresos_final e ON (
    i.id_expediente = e.id_expediente 
    AND i.l_gerencia = e.l_gerencia 
    AND i.l_trata_reporte = e.l_trata_reporte
);
