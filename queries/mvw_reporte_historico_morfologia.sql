-- Vista Materializada: MORFOLOGIA
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_morfologia;

CREATE MATERIALIZED VIEW mvw_reporte_historico_morfologia AS
WITH tramites_metadata (gerencia, trata, nombre_trata, acronimos_list) AS (
    VALUES 
    ('morfologia', 'MDUG1801A', 'Informe urbanístico.', ARRAY['DI', 'ANEXO', 'IF']),
    ('morfologia', 'MDUG0107A', 'Fijación de Línea de Frente Interno.', ARRAY['DI', 'ANEXO', 'IF']),
    ('morfologia', 'MDUG3501A', 'Consulta Obligatoria General.', ARRAY['DI', 'ANEXO', 'IF']),
    ('morfologia', 'MDUG3601A', 'Interpretación Urbanística.', ARRAY['DI', 'ANEXO', 'IF']),
    ('morfologia', 'MDUG3901A', 'Solicitud De Certificado Urbanístico', ARRAY['DI', 'ANEXO', 'IF']),
    ('morfologia', 'MDUG1802A', 'Consulta No Obligatoria De Capacidad Constructiva Adicional Proyecto Emisor', ARRAY['DI', 'ANEXO', 'IF']),
    ('morfologia', 'MDUG1804A', 'Permiso De Ejecución De Obra Civil - Proyecto Emisor Zona Sur', ARRAY['DI', 'ANEXO', 'IF']),
    ('morfologia', 'MDUG1803A', 'Registro Etapa Proyecto - Emisor Zona Sur', ARRAY['DI', 'ANEXO', 'IF']),
    ('morfologia', 'MDUG1805A', 'Evaluación Vinculante De Capacidad Constructiva Adicional - Proyecto Emisor Zona Sur', ARRAY['DI', 'ANEXO', 'IF']),
    ('morfologia', 'MDUG1806A', 'Certificado De Capacidad Constructiva Adicional', ARRAY['DI', 'ANEXO', 'IF']),
    ('morfologia', 'INTERVENCIONES', 'Intervenciones', ARRAY['DI', 'ANEXO', 'IF'])
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
ingresos_raw AS (
    -- Ingresos para trámites puros (Buzón DGIUR-03)
    SELECT p.id_expediente, 'morfologia' as gerencia_buzon, ec.trata as trata_orig, MIN(p.fecha)::date as fecha_ing
    FROM pases_pre_filtrados p
    JOIN expedientes_target ec ON p.id_expediente = ec.id_expediente
    WHERE p.destinatario = 'DGIUR-03' 
      AND ec.trata IN ('MDUG1801A', 'MDUG0107A', 'MDUG3501A', 'MDUG3601A', 'MDUG3901A', 'MDUG1802A', 'MDUG1804A', 'MDUG1803A', 'MDUG1805A', 'MDUG1806A')
    GROUP BY 1, 2, 3
    
    UNION ALL
    
    -- Ingresos para Intervenciones (Buzones específicos, trata no pura)
    SELECT p.id_expediente, 'morfologia' as gerencia_buzon, ec.trata as trata_orig, MIN(p.fecha)::date as fecha_ing
    FROM pases_pre_filtrados p
    JOIN expedientes_target ec ON p.id_expediente = ec.id_expediente
    WHERE p.destinatario IN ('DGIUR-03', 'DGIUR-ADMISIBILIDADMORFO', 'DGIUR-CONSULTASESPECIFICAS', 'DGIUR-CURVERIFICACION', 'DGIUR-DGIUR-PERMISO TEMPRANO', 'DGIUR-VA II')
      AND ec.trata NOT IN ('MDUG1801A', 'MDUG0107A', 'MDUG3501A', 'MDUG3601A', 'MDUG3901A', 'MDUG1802A', 'MDUG1804A', 'MDUG1803A', 'MDUG1805A', 'MDUG1806A')
    GROUP BY 1, 2, 3
),
ingresos AS (
    -- Concepto: si un mismo expediente ingresa mas de una vez en un buzón, vamos a contabilidad el ingreso mas antiguo.
    SELECT ir.id_expediente, ir.gerencia_buzon as gerencia,
           CASE 
                WHEN EXISTS (SELECT 1 FROM tramites_metadata tm WHERE tm.trata = ir.trata_orig AND tm.trata != 'INTERVENCIONES') THEN ir.trata_orig
                ELSE 'INTERVENCIONES'
           END as trata,
           MIN(ir.fecha_ing) as fecha_ing
    FROM ingresos_raw ir
    GROUP BY 1, 2, 3
),
egresos_efectivos AS (
    -- Tanto para los tramites puros de Morfología como las intervenciones, el acto que se considera para el egreso es DICTAMEN/ANEXO/INFORME FIRMADO POR ALANDAZURI
    SELECT g.id_expediente, i.trata, i.gerencia, MIN(g.fecha_creacion)::date as fecha_egr
    FROM mvw_datos_gedo_secgdu g
    JOIN ingresos i ON g.id_expediente = i.id_expediente
    JOIN tramites_metadata tm ON i.trata = tm.trata
    WHERE (g.acronimo ILIKE 'DICTAMEN%' OR g.acronimo ILIKE 'ANEXO%' OR g.acronimo ILIKE 'INFORME%')
      AND g.fecha_creacion >= i.fecha_ing
      AND g.usuario_creador = 'ALANDAZURI'
    GROUP BY 1, 2, 3
),
egresos_no_efectivos AS (
    -- Para las subsanaciones (EGRESO NO EFECTIVO) Se toma los expedientes detectados como ingresados que tengan en la tabla de pases el movimiento de envío a Guarda Temporal y que no tenga acrónimo de registro previo al pase.
    -- EGRESOS NO EFECTIVOS en INTERVENCIONES no se computan.
    SELECT p.id_expediente, i.trata, i.gerencia, MIN(p.fecha)::date as fecha_egr
    FROM mvw_ee_pases_secgdu p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    WHERE (p.estado = 'Guarda Temporal' OR p.destinatario = 'GUARDA TEMPORAL') 
      AND p.fecha > i.fecha_ing 
      AND i.trata != 'INTERVENCIONES'
      -- No tenga acrónimo de registro previo (egreso efectivo)
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
    ) IN ('A.GUZMAN', 'AGARTEAGA', 'ALANDAZURI', 'ALFONSOGA', 'CAROLINAPRADO', 'CGAMARRA', 'CGENTILINI', 'DANCOLOMBO', 'DGIUR-03', 'DGIUR-ADMISIBILIDADMORFO', 'DGIUR-CONSULTASESPECIFICAS', 'DGIUR-CURVERIFICACION', 'DGIUR-DGIUR-PERMISO TEMPRANO', 'DGIUR-VA II', 'ECAYSSIALS', 'EVELYNTORRES', 'FORFANO', 'FOTTOGALLI', 'FRANGARAY', 'GBERNASCONI', 'GCABADGIUR', 'IANELUSTONDO', 'IVALDES', 'LNSPERTINO', 'M.SABATINO', 'MANUELALVELO', 'MILAGROSTOURON', 'MILENAAZULMORENO', 'MLOBIANCOCRIADO', 'MPLANS1', 'MREIDMAN', 'MVOSKIAN', 'NASILANES', 'NCASALE', 'OVERRINA', 'PTEIGA', 'ROCAM', 'SBONDOREVSKY', 'SCABANELLAS', 'SDAVIDOVSKY', 'SVC_DGIURMORFO', 'SVCDGIUR3', 'TOSELLIR', 'VVINICIUS')) as "STOCK_PROPIO",
    array_to_string(tm.acronimos_list, ', ') as acronimos
FROM tramites_metadata tm
CROSS JOIN periodos per
LEFT JOIN status_final s ON tm.trata = s.trata AND tm.gerencia = s.gerencia
GROUP BY 1, 2, 3, 4, 5, tm.acronimos_list
ORDER BY 1, 2, 4, 5;
