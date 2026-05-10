-- Tablero Integral - CATASTRO
-- Trámite: Certificado de Determinación de Cinturón Digital (MDUG0115G)
-- Formato Horizontal (Pivot) - Año 2026 (Hasta Mayo) - OPTIMIZADO

WITH ingresos_todos AS (
    SELECT p.id_expediente, MIN(p.fecha) as fecha_ingreso
    FROM mvw_ee_pases_secgdu p
    JOIN mvw_expedientes_tratas_secgdu e ON p.id_expediente = e.id_expediente
    WHERE p.destinatario IN ('DGROC-CIC', 'DGROC-COPIAPLANO', 'DGROC-DCATDES', 'DGROC-DCATPOL', 'DGROC-DCATTIT')
      AND e.trata = 'MDUG0115G'
    GROUP BY p.id_expediente
),
egresos_efectivos AS (
    SELECT i.id_expediente, MIN(g.fecha_creacion) as fecha_egreso
    FROM ingresos_todos i
    JOIN mvw_datos_gedo_secgdu g ON i.id_expediente = g.id_expediente
    WHERE g.acronimo IN ('IF')
    GROUP BY i.id_expediente
),
egresos_no_efectivos AS (
    SELECT i.id_expediente, MIN(p.fecha) as fecha_egreso
    FROM ingresos_todos i
    JOIN mvw_ee_pases_secgdu p ON i.id_expediente = p.id_expediente
    LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente
    WHERE (p.estado = 'Guarda Temporal' OR p.destinatario = 'GUARDA TEMPORAL')
      AND ee.id_expediente IS NULL
    GROUP BY i.id_expediente
),
consolidado_mensual AS (
    SELECT id_expediente, fecha_ingreso as fecha, 'ING' as tipo FROM ingresos_todos
    UNION ALL
    SELECT id_expediente, fecha_egreso as fecha, 'EGR_EF' as tipo FROM egresos_efectivos
    UNION ALL
    SELECT id_expediente, fecha_egreso as fecha, 'EGR_NE' as tipo FROM egresos_no_efectivos
)
SELECT 
    'CATASTRO' as "GERENCIA",
    'MDUG0115G' as "COD TRATA",
    'Certificado de Determinación de Cinturón Digital' as "DETALLE TRATA",
    
    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'ING' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 1) as "ING_01",
    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'ING' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 2) as "ING_02",
    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'ING' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 3) as "ING_03",
    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'ING' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 4) as "ING_04",
    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'ING' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 5) as "ING_05",

    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_EF' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 1) as "EGR_EF_01",
    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_EF' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 2) as "EGR_EF_02",
    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_EF' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 3) as "EGR_EF_03",
    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_EF' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 4) as "EGR_EF_04",
    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_EF' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 5) as "EGR_EF_05",

    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_NE' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 1) as "EGR_NE_01",
    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_NE' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 2) as "EGR_NE_02",
    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_NE' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 3) as "EGR_NE_03",
    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_NE' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 4) as "EGR_NE_04",
    COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_NE' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 5) as "EGR_NE_05",

    (COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_EF' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 1) + 
     COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_NE' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 1)) as "EGR_TOT_01",
    (COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_EF' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 2) + 
     COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_NE' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 2)) as "EGR_TOT_02",
    (COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_EF' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 3) + 
     COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_NE' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 3)) as "EGR_TOT_03",
    (COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_EF' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 4) + 
     COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_NE' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 4)) as "EGR_TOT_04",
    (COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_EF' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 5) + 
     COUNT(DISTINCT id_expediente) FILTER (WHERE tipo = 'EGR_NE' AND EXTRACT(YEAR FROM fecha) = 2026 AND EXTRACT(MONTH FROM fecha) = 5)) as "EGR_TOT_05",

    (SELECT COUNT(DISTINCT i.id_expediente) FROM ingresos_todos i LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente LEFT JOIN egresos_no_efectivos ene ON i.id_expediente = ene.id_expediente JOIN mvw_expedientes_tratas_secgdu e ON i.id_expediente = e.id_expediente WHERE ee.id_expediente IS NULL AND ene.id_expediente IS NULL AND e.estado NOT ILIKE 'Subsanaci%%n') as "STOCK",
    (SELECT COUNT(DISTINCT i.id_expediente) FROM ingresos_todos i LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente LEFT JOIN egresos_no_efectivos ene ON i.id_expediente = ene.id_expediente JOIN mvw_expedientes_tratas_secgdu e ON i.id_expediente = e.id_expediente WHERE ee.id_expediente IS NULL AND ene.id_expediente IS NULL AND e.estado ILIKE 'Subsanaci%%n') as "SUBSANACIONES ABIERTAS",
    (SELECT COUNT(DISTINCT i.id_expediente) FROM ingresos_todos i LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente LEFT JOIN egresos_no_efectivos ene ON i.id_expediente = ene.id_expediente WHERE ee.id_expediente IS NULL AND ene.id_expediente IS NULL) as "STOCK TOTAL"
FROM consolidado_mensual;
