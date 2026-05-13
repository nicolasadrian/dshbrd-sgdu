-- Vista de Ciclo de Vida (ESPEJO LOCAL - VISTA LÓGICA)
CREATE OR REPLACE VIEW v_expedientes_lifecycle AS
WITH pases_base AS (
    SELECT 
        id_expediente, 
        fecha, 
        destinatario, 
        usuario as remitente, -- Ajustado al nombre real en local
        estado,
        LEAD(fecha) OVER (PARTITION BY id_expediente ORDER BY fecha) as fecha_fin
    FROM mvw_ee_pases_secgdu
),
ingresos AS (
    SELECT 
        p.id_expediente, 
        cfg.gerencia, 
        cfg.trata_reporte,
        MIN(p.fecha)::date as fecha_ing
    FROM pases_base p
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
        g.id_expediente, i.gerencia, i.trata_reporte,
        MIN(g.fecha_creacion)::date as fecha_egr,
        'EFECTIVO'::text as tipo_egr
    FROM mvw_datos_gedo_secgdu g
    JOIN ingresos i ON g.id_expediente = i.id_expediente
    JOIN cfg_gestion_metas cfg ON (cfg.gerencia = i.gerencia AND cfg.trata_reporte = i.trata_reporte)
    WHERE g.acronimo = ANY(cfg.acronimos_egreso) AND g.fecha_creacion >= i.fecha_ing
    GROUP BY 1, 2, 3
),
egresos_pases AS (
    SELECT 
        p.id_expediente, i.gerencia, i.trata_reporte,
        CASE WHEN i.trata_reporte = 'INTERVENCIONES' THEN MAX(p.fecha)::date ELSE MIN(p.fecha)::date END as fecha_egr,
        'NO_EFECTIVO'::text as tipo_egr
    FROM pases_base p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    JOIN cfg_gestion_metas cfg ON (cfg.gerencia = i.gerencia AND cfg.trata_reporte = i.trata_reporte)
    WHERE p.fecha > i.fecha_ing 
      AND p.remitente = ANY(cfg.analistas_oficiales)
      AND p.destinatario != ANY(cfg.analistas_oficiales)
      AND p.destinatario != ANY(cfg.buzones_ingreso)
    GROUP BY 1, 2, 3
),
egresos_final AS (
    SELECT id_expediente, gerencia, trata_reporte, MIN(fecha_egr) as fecha_egr, tipo_egr
    FROM (
        SELECT * FROM egresos_gedo
        UNION ALL
        SELECT * FROM egresos_pases
    ) sub
    GROUP BY 1, 2, 3, 5
)
SELECT 
    i.id_expediente, i.gerencia, i.trata_reporte,
    i.fecha_ing, e.fecha_egr, e.tipo_egr,
    CASE WHEN e.fecha_egr IS NULL THEN 'ACTIVO' ELSE 'CERRADO' END as status_gestion
FROM ingresos i
LEFT JOIN egresos_final e ON (i.id_expediente = e.id_expediente AND i.gerencia = e.gerencia AND i.trata_reporte = e.trata_reporte);
