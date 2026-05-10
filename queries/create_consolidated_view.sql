-- Borrar si ya existe
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_consolidado_catastro;

CREATE MATERIALIZED VIEW mvw_reporte_consolidado_catastro AS
WITH tramites_metadata (trata, nombre_trata, acronimos_list) AS (
    VALUES 
    ('MDUG0115C', 'Anulación de Propiedad Horizontal', ARRAY['IFMMH']),
    ('MDUG1501L', 'Certificado de cota de parcela nivel cero', ARRAY['IFMAD']),
    ('MDUG0115G', 'Certificado de Determinación de Cinturón Digital', ARRAY['IF']),
    ('MDUG1501H', 'Certificado de información catastral', ARRAY['IFDEX']),
    ('MDUG0134C', 'Certificado de numeración domiciliaria', ARRAY['CECNU']),
    ('MDUG0134N', 'Constitución de Estado Parcelario', ARRAY['IFGPA', 'FIPAR']),
    ('MDUG0146A', 'Copia de plano', ARRAY['IFPCB', 'IFDEX']),
    ('GENE0702C', 'Mensura Regularización Urbana Dominial', ARRAY['PPINV']),
    ('MDUG0115F', 'Plano de mensura de objeto territorial', ARRAY['IFMOT']),
    ('MDUG0115B', 'Plano de Mensura Particular', ARRAY['IFMSC']),
    ('MDUG0132A', 'Plano de prehorizontalidad nuevo', ARRAY['IFMHC']),
    ('MDUG0131A', 'Plano de Propiedad Horizontal modif/compl', ARRAY['IFMHC']),
    ('MDUG0131B', 'Plano de propiedad horizontal nuevo', ARRAY['IFMHC']),
    ('MDUG0115E', 'Rectificación de Plano de Mensura', ARRAY['IFMSC', 'IFMHC']),
    ('MDUG0134E', 'Solicitud de Certificado de fijación de línea', ARRAY['IFMAD']),
    ('MDUG0135A', 'Solicitud de consideración a la DGROC', ARRAY['IFMHC', 'IFMMH', 'IFMAD', 'IFMSC', 'IFMOT', 'IFPCB', 'FIPAR'])
),
ingresos_todos AS (
    SELECT p.id_expediente, e.trata, MIN(p.fecha) as fecha_ingreso
    FROM mvw_ee_pases_secgdu p
    JOIN mvw_expedientes_tratas_secgdu e ON p.id_expediente = e.id_expediente
    WHERE p.destinatario IN ('DGROC-CIC', 'DGROC-COPIAPLANO', 'DGROC-DCATDES', 'DGROC-DCATPOL', 'DGROC-DCATTIT')
      AND e.trata IN (SELECT trata FROM tramites_metadata)
    GROUP BY p.id_expediente, e.trata
),
egresos_efectivos AS (
    SELECT i.id_expediente, i.trata, MIN(g.fecha_creacion) as fecha_egreso
    FROM ingresos_todos i
    JOIN mvw_datos_gedo_secgdu g ON i.id_expediente = g.id_expediente
    JOIN tramites_metadata tm ON i.trata = tm.trata
    WHERE g.acronimo = ANY(tm.acronimos_list)
    GROUP BY i.id_expediente, i.trata
),
egresos_no_efectivos AS (
    SELECT i.id_expediente, i.trata, MIN(p.fecha) as fecha_egreso
    FROM ingresos_todos i
    JOIN mvw_ee_pases_secgdu p ON i.id_expediente = p.id_expediente
    LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente
    WHERE (p.estado = 'Guarda Temporal' OR p.destinatario = 'GUARDA TEMPORAL')
      AND ee.id_expediente IS NULL
    GROUP BY i.id_expediente, i.trata
),
consolidado_mensual AS (
    SELECT id_expediente, trata, fecha_ingreso as fecha, 'ING' as tipo FROM ingresos_todos
    UNION ALL
    SELECT id_expediente, trata, fecha_egreso as fecha, 'EGR_EF' as tipo FROM egresos_efectivos
    UNION ALL
    SELECT id_expediente, trata, fecha_egreso as fecha, 'EGR_NE' as tipo FROM egresos_no_efectivos
)
SELECT 
    tm.trata as "COD TRATA",
    tm.nombre_trata as "DETALLE TRATA",
    
    COUNT(DISTINCT c.id_expediente) FILTER (WHERE c.tipo = 'ING' AND EXTRACT(YEAR FROM c.fecha) = 2026 AND EXTRACT(MONTH FROM c.fecha) = 1) as "ING_01",
    COUNT(DISTINCT c.id_expediente) FILTER (WHERE c.tipo = 'ING' AND EXTRACT(YEAR FROM c.fecha) = 2026 AND EXTRACT(MONTH FROM c.fecha) = 2) as "ING_02",
    COUNT(DISTINCT c.id_expediente) FILTER (WHERE c.tipo = 'ING' AND EXTRACT(YEAR FROM c.fecha) = 2026 AND EXTRACT(MONTH FROM c.fecha) = 3) as "ING_03",
    COUNT(DISTINCT c.id_expediente) FILTER (WHERE c.tipo = 'ING' AND EXTRACT(YEAR FROM c.fecha) = 2026 AND EXTRACT(MONTH FROM c.fecha) = 4) as "ING_04",
    COUNT(DISTINCT c.id_expediente) FILTER (WHERE c.tipo = 'ING' AND EXTRACT(YEAR FROM c.fecha) = 2026 AND EXTRACT(MONTH FROM c.fecha) = 5) as "ING_05",

    (COUNT(DISTINCT c.id_expediente) FILTER (WHERE (c.tipo = 'EGR_EF' OR c.tipo = 'EGR_NE') AND EXTRACT(YEAR FROM c.fecha) = 2026 AND EXTRACT(MONTH FROM c.fecha) = 1)) as "EGR_TOT_01",
    (COUNT(DISTINCT c.id_expediente) FILTER (WHERE (c.tipo = 'EGR_EF' OR c.tipo = 'EGR_NE') AND EXTRACT(YEAR FROM c.fecha) = 2026 AND EXTRACT(MONTH FROM c.fecha) = 2)) as "EGR_TOT_02",
    (COUNT(DISTINCT c.id_expediente) FILTER (WHERE (c.tipo = 'EGR_EF' OR c.tipo = 'EGR_NE') AND EXTRACT(YEAR FROM c.fecha) = 2026 AND EXTRACT(MONTH FROM c.fecha) = 3)) as "EGR_TOT_03",
    (COUNT(DISTINCT c.id_expediente) FILTER (WHERE (c.tipo = 'EGR_EF' OR c.tipo = 'EGR_NE') AND EXTRACT(YEAR FROM c.fecha) = 2026 AND EXTRACT(MONTH FROM c.fecha) = 4)) as "EGR_TOT_04",
    (COUNT(DISTINCT c.id_expediente) FILTER (WHERE (c.tipo = 'EGR_EF' OR c.tipo = 'EGR_NE') AND EXTRACT(YEAR FROM c.fecha) = 2026 AND EXTRACT(MONTH FROM c.fecha) = 5)) as "EGR_TOT_05",

    (SELECT COUNT(DISTINCT i.id_expediente) 
     FROM ingresos_todos i 
     LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente 
     LEFT JOIN egresos_no_efectivos ene ON i.id_expediente = ene.id_expediente 
     JOIN mvw_expedientes_tratas_secgdu e ON i.id_expediente = e.id_expediente 
     WHERE i.trata = tm.trata AND ee.id_expediente IS NULL AND ene.id_expediente IS NULL AND e.estado NOT ILIKE 'Subsanación') as "STOCK",
     
    (SELECT COUNT(DISTINCT i.id_expediente) 
     FROM ingresos_todos i 
     LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente 
     LEFT JOIN egresos_no_efectivos ene ON i.id_expediente = ene.id_expediente 
     JOIN mvw_expedientes_tratas_secgdu e ON i.id_expediente = e.id_expediente 
     WHERE i.trata = tm.trata AND ee.id_expediente IS NULL AND ene.id_expediente IS NULL AND e.estado ILIKE 'Subsanación') as "SUBSANACIONES ABIERTAS",
     
    (SELECT COUNT(DISTINCT i.id_expediente) 
     FROM ingresos_todos i 
     LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente 
     LEFT JOIN egresos_no_efectivos ene ON i.id_expediente = ene.id_expediente 
     WHERE i.trata = tm.trata AND ee.id_expediente IS NULL AND ene.id_expediente IS NULL) as "STOCK TOTAL"

FROM tramites_metadata tm
LEFT JOIN consolidado_mensual c ON tm.trata = c.trata
GROUP BY tm.trata, tm.nombre_trata
ORDER BY tm.nombre_trata;
