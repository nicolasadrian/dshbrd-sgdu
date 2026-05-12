-- Vista Materializada: REGULARIZACION
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_regularizacion;

CREATE MATERIALIZED VIEW mvw_reporte_historico_regularizacion AS
WITH tramites_metadata (gerencia, trata, nombre_trata, acronimos_list) AS (
    VALUES 
    ('regularizacion', 'MDUG0104A', 'Regularización de Plano de Obra Civil', ARRAY['IFROC']),
    ('regularizacion', 'MDUG0141A', 'Registro de plano Conforme.', ARRAY['IFPCO', 'IFSMI']),
    ('regularizacion', 'MDUG3001A', 'Registro de Plano de Obra Civil: Registro en Etapa Proyecto (EXPEDIENTES VIEJOS)', ARRAY['IFPCO']),
    ('regularizacion', 'MDUG1501K', 'Permiso de Demolición.', ARRAY['IFPDO']),
    ('regularizacion', 'INTERVENCIONES', 'Intervenciones', ARRAY['IFROC', 'IFPCO', 'IFSMI', 'IFPDO'])
),
periodos AS (
    SELECT 
        EXTRACT(YEAR FROM s.d)::int as anio, 
        EXTRACT(MONTH FROM s.d)::int as mes,
        (s.d + interval '1 month' - interval '1 day')::date as fin_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
),
expedientes_target AS (
    SELECT id_expediente, trata, CASE WHEN estado ILIKE 'Subsanaci%' OR estado ILIKE 'Subsanación%' THEN 1 ELSE 0 END as is_subs
    FROM mvw_expedientes_tratas_secgdu
),
pases_pre_filtrados AS (
    SELECT p.id_expediente, p.fecha, p.destinatario, 
           LAG(p.destinatario) OVER (PARTITION BY p.id_expediente ORDER BY p.fecha) as remitente
    FROM mvw_ee_pases_secgdu p
),
buzones_ingreso AS (
    SELECT unstack FROM unstack(ARRAY['DGROC-OBRASDEMO'])
),
analistas_area AS (
    SELECT unstack FROM unstack(ARRAY['AGUEROJO', 'AKRACOFF', 'ALVAREZ.M', 'ARAOZLUIS', 'ATENCIOAL', 'DALBORAF', 'DGROC-ESPERAINSTALACIONES', 'DGROC-OBRASDEMO', 'ENCISOA', 'EPARLATO', 'ERDOCIAINA', 'JBARRACO', 'JLGARMENDIA', 'JTERRILE', 'MYUSHU', 'S.SANCHEZPAZ', 'SCAVALLARO'])
),
ingresos_raw AS (
    SELECT p.id_expediente, 'regularizacion' as gerencia_buzon, ec.trata as trata_orig, MIN(p.fecha)::date as fecha_ing
    FROM pases_pre_filtrados p
    JOIN expedientes_target ec ON p.id_expediente = ec.id_expediente
    WHERE p.destinatario IN (SELECT * FROM buzones_ingreso)
    GROUP BY 1, 2, 3
),
ingresos AS (
    SELECT ir.id_expediente, ir.gerencia_buzon as gerencia,
           CASE 
                WHEN EXISTS (SELECT 1 FROM tramites_metadata tm WHERE tm.trata = ir.trata_orig AND tm.trata != 'INTERVENCIONES') THEN ir.trata_orig
                ELSE 'INTERVENCIONES'
           END as trata,
           MIN(ir.fecha_ing) as fecha_ing
    FROM ingresos_raw ir
    GROUP BY 1, 2, 3
),
egresos_efectivos_puros AS (
    SELECT g.id_expediente, i.trata, i.gerencia, MIN(g.fecha_creacion)::date as fecha_egr
    FROM mvw_datos_gedo_secgdu g
    JOIN ingresos i ON g.id_expediente = i.id_expediente
    JOIN tramites_metadata tm ON i.trata = tm.trata
    WHERE (
        (i.trata = 'MDUG3001A' AND EXTRACT(YEAR FROM i.fecha_ing) < 2026 AND g.acronimo = 'IFPCO') OR
        (i.trata = 'MDUG1501K' AND g.acronimo = 'IFPDO') OR
        (i.trata NOT IN ('MDUG3001A', 'MDUG1501K') AND g.acronimo = ANY(tm.acronimos_list))
    )
    AND g.fecha_creacion >= i.fecha_ing
    AND i.trata != 'INTERVENCIONES'
    GROUP BY 1, 2, 3
),
egresos_intervenciones AS (
    SELECT p.id_expediente, 'INTERVENCIONES' as trata, i.gerencia, MAX(p.fecha)::date as fecha_egr
    FROM pases_pre_filtrados p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    WHERE i.trata = 'INTERVENCIONES'
      AND p.fecha > i.fecha_ing
      AND p.remitente IN (SELECT * FROM analistas_area)
      AND p.destinatario NOT IN (SELECT * FROM analistas_area)
    GROUP BY 1, 2, 3
),
egresos_efectivos AS (
    SELECT * FROM egresos_efectivos_puros
    UNION ALL
    SELECT * FROM egresos_intervenciones
),
egresos_no_efectivos AS (
    SELECT p.id_expediente, i.trata, i.gerencia, MIN(p.fecha)::date as fecha_egr
    FROM mvw_ee_pases_secgdu p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    WHERE (p.estado = 'Guarda Temporal' OR p.destinatario = 'GUARDA TEMPORAL') 
      AND p.fecha > i.fecha_ing 
      AND i.trata != 'INTERVENCIONES'
      AND NOT EXISTS (
          SELECT 1 FROM egresos_efectivos ee 
          WHERE ee.id_expediente = i.id_expediente 
          AND ee.trata = i.trata
          AND ee.fecha_egr < p.fecha
      )
    GROUP BY 1, 2, 3
),
status_final AS (
    SELECT i.id_expediente, i.trata, i.gerencia, i.fecha_ing, COALESCE(ee.fecha_egr, en.fecha_egr) as fecha_egr,
           CASE WHEN ee.id_expediente IS NOT NULL THEN 'EF' WHEN en.id_expediente IS NOT NULL THEN 'NE' ELSE NULL END as tipo_egr,
           ec.is_subs
    FROM ingresos i
    JOIN expedientes_target ec ON i.id_expediente = ec.id_expediente
    LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente AND i.trata = ee.trata
    LEFT JOIN egresos_no_efectivos en ON i.id_expediente = en.id_expediente AND i.trata = en.trata AND ee.id_expediente IS NULL
)
SELECT 
    tm.gerencia as "GERENCIA", tm.trata as "COD TRATA", tm.nombre_trata as "DETALLE TRATA", per.anio, per.mes,
    COUNT(*) FILTER (WHERE s.fecha_ing >= date_trunc('month', per.fin_mes) AND s.fecha_ing <= per.fin_mes) as "ING",
    COUNT(*) FILTER (WHERE s.fecha_egr >= date_trunc('month', per.fin_mes) AND s.fecha_egr <= per.fin_mes AND s.tipo_egr = 'EF') as "EGR_EF",
    COUNT(*) FILTER (WHERE s.fecha_egr >= date_trunc('month', per.fin_mes) AND s.fecha_egr <= per.fin_mes AND s.tipo_egr = 'NE') as "EGR_NE",
    COUNT(*) FILTER (WHERE s.fecha_ing <= per.fin_mes AND (s.fecha_egr IS NULL OR s.fecha_egr > per.fin_mes) AND s.is_subs = 1) as "STOCK_SUBS",
    COUNT(*) FILTER (WHERE s.fecha_ing <= per.fin_mes AND (s.fecha_egr IS NULL OR s.fecha_egr > per.fin_mes) AND s.is_subs = 0 AND (
        SELECT p.destinatario FROM mvw_ee_pases_secgdu p WHERE p.id_expediente = s.id_expediente AND p.fecha <= per.fin_mes ORDER BY p.fecha DESC LIMIT 1
    ) IN (SELECT * FROM analistas_area)) as "STOCK_PROPIO",
    array_to_string(tm.acronimos_list, ', ') as acronimos
FROM tramites_metadata tm
CROSS JOIN periodos per
LEFT JOIN status_final s ON tm.trata = s.trata AND tm.gerencia = s.gerencia
GROUP BY 1, 2, 3, 4, 5, tm.acronimos_list
ORDER BY 1, 2, 4, 5;
