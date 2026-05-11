-- Vista Materializada: AVISO DE OBRA
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_aviso_obra;

CREATE MATERIALIZED VIEW mvw_reporte_historico_aviso_obra AS
WITH tramites_metadata (gerencia, trata, nombre_trata, acronimos_list) AS (
    VALUES 
    ('aviso_obra', 'MDUG0102B_AUTO', 'Aviso de Obra (Automático)', ARRAY['IFCAO', 'IFCAC']),
    ('aviso_obra', 'MDUG0102B_DGIUR', 'Aviso de Obra (DGIUR)', ARRAY['IF'])
),
periodos AS (
    SELECT 
        EXTRACT(YEAR FROM s.d)::int as anio, 
        EXTRACT(MONTH FROM s.d)::int as mes,
        (s.d + interval '1 month' - interval '1 day')::date as fin_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
),
expedientes_target AS (
    SELECT id_expediente, trata, 0 as is_subs FROM mvw_expedientes_tratas_secgdu WHERE trata = 'MDUG0102B'
),
pases_pre_filtrados AS (
    SELECT p.id_expediente, p.fecha, p.destinatario, 
           LAG(p.destinatario) OVER (PARTITION BY p.id_expediente ORDER BY p.fecha) as remitente
    FROM mvw_ee_pases_secgdu p
),
ingresos_raw AS (
    -- AUTO
    SELECT p.id_expediente, 'aviso_obra' as gerencia_buzon, 'MDUG0102B_AUTO' as trata_orig, MIN(p.fecha)::date as fecha_ing
    FROM pases_pre_filtrados p WHERE p.destinatario = 'DGROC-AUTOMAT' GROUP BY 1
    UNION ALL
    -- DGIUR
    SELECT p.id_expediente, 'aviso_obra' as gerencia_buzon, 'MDUG0102B_DGIUR' as trata_orig, MIN(p.fecha)::date as fecha_ing
    FROM pases_pre_filtrados p WHERE p.destinatario = 'DGIUR-21' AND p.remitente = 'DGROC-AUTOMAT' GROUP BY 1
),
ingresos AS (
    SELECT id_expediente, gerencia_buzon as gerencia, trata_orig as trata, MIN(fecha_ing) as fecha_ing FROM ingresos_raw GROUP BY 1, 2, 3
),
egresos_efectivos AS (
    SELECT g.id_expediente, i.trata, i.gerencia, MIN(g.fecha_creacion)::date as fecha_egr
    FROM mvw_datos_gedo_secgdu g
    JOIN ingresos i ON g.id_expediente = i.id_expediente
    JOIN tramites_metadata tm ON i.trata = tm.trata
    WHERE g.acronimo = ANY(tm.acronimos_list) AND g.fecha_creacion >= i.fecha_ing
      AND (i.trata != 'MDUG0102B_DGIUR' OR g.usuario_creador IN ('VASTAM', 'ALANDAZURI', 'FVERDAGUER', 'VGAYTAN', 'ZONCA', 'CGIRAUD'))
    GROUP BY 1, 2, 3
),
egresos_no_efectivos AS (
    -- Guarda Temporal
    SELECT p.id_expediente, i.trata, i.gerencia, MIN(p.fecha)::date as fecha_egr
    FROM mvw_ee_pases_secgdu p JOIN ingresos i ON p.id_expediente = i.id_expediente
    WHERE (p.estado = 'Guarda Temporal' OR p.destinatario = 'GUARDA TEMPORAL') AND p.fecha > i.fecha_ing GROUP BY 1, 2, 3
    UNION ALL
    -- IFCFP
    SELECT g.id_expediente, i.trata, i.gerencia, MIN(g.fecha_creacion)::date as fecha_egr
    FROM mvw_datos_gedo_secgdu g JOIN ingresos i ON g.id_expediente = i.id_expediente
    WHERE g.acronimo = 'IFCFP' AND g.fecha_creacion >= i.fecha_ing GROUP BY 1, 2, 3
    UNION ALL
    -- Transferencia AUTO -> DGIUR
    SELECT p.id_expediente, 'MDUG0102B_AUTO' as trata, 'aviso_obra' as gerencia, MIN(p.fecha)::date as fecha_egr
    FROM pases_pre_filtrados p JOIN ingresos i ON p.id_expediente = i.id_expediente
    WHERE i.trata = 'MDUG0102B_AUTO' AND p.destinatario = 'DGIUR-21' AND p.remitente = 'DGROC-AUTOMAT' AND p.fecha > i.fecha_ing GROUP BY 1
),
status_final AS (
    SELECT i.id_expediente, i.trata, i.gerencia, i.fecha_ing, COALESCE(ee.fecha_egr, (SELECT MIN(fecha_egr) FROM egresos_no_efectivos en WHERE en.id_expediente = i.id_expediente AND en.trata = i.trata)) as fecha_egr,
           CASE WHEN ee.id_expediente IS NOT NULL THEN 'EF' WHEN EXISTS (SELECT 1 FROM egresos_no_efectivos en WHERE en.id_expediente = i.id_expediente AND en.trata = i.trata) THEN 'NE' ELSE NULL END as tipo_egr,
           0 as is_subs
    FROM ingresos i
    LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente AND i.trata = ee.trata
)
SELECT 
    tm.gerencia as "GERENCIA", tm.trata as "COD TRATA", tm.nombre_trata as "DETALLE TRATA", per.anio, per.mes,
    COUNT(*) FILTER (WHERE s.fecha_ing >= date_trunc('month', per.fin_mes) AND s.fecha_ing <= per.fin_mes) as "ING",
    COUNT(*) FILTER (WHERE s.fecha_egr >= date_trunc('month', per.fin_mes) AND s.fecha_egr <= per.fin_mes AND s.tipo_egr = 'EF') as "EGR_EF",
    COUNT(*) FILTER (WHERE s.fecha_egr >= date_trunc('month', per.fin_mes) AND s.fecha_egr <= per.fin_mes AND s.tipo_egr = 'NE') as "EGR_NE",
    0 as "STOCK_SUBS",
    COUNT(*) FILTER (WHERE s.fecha_ing <= per.fin_mes AND (s.fecha_egr IS NULL OR s.fecha_egr > per.fin_mes)) as "STOCK_PROPIO",
    array_to_string(tm.acronimos_list, ', ') as acronimos
FROM tramites_metadata tm
CROSS JOIN periodos per
LEFT JOIN status_final s ON tm.trata = s.trata AND tm.gerencia = s.gerencia
GROUP BY 1, 2, 3, 4, 5, tm.acronimos_list
ORDER BY 1, 2, 4, 5;
