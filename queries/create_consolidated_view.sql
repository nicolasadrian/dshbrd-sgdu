-- Refactor de Vista Consolidada SIN PRODUCTO CARTESIANO (Ultra Liviana)
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_consolidado_catastro CASCADE;

CREATE MATERIALIZED VIEW mvw_reporte_consolidado_catastro AS
WITH tramites_metadata (trata, nombre_trata) AS (
    VALUES 
    ('MDUG0115C', 'Anulación de Propiedad Horizontal'),
    ('MDUG1501L', 'Certificado de cota de parcela nivel cero'),
    ('MDUG0115G', 'Certificado de Determinación de Cinturón Digital'),
    ('MDUG1501H', 'Certificado de información catastral'),
    ('MDUG0134C', 'Certificado de numeración domiciliaria'),
    ('MDUG0134N', 'Constitución de Estado Parcelario'),
    ('MDUG0146A', 'Copia de plano'),
    ('GENE0702C', 'Mensura Regularización Urbana Dominial'),
    ('MDUG0115F', 'Plano de mensura de objeto territorial'),
    ('MDUG0115B', 'Plano de Mensura Particular'),
    ('MDUG0132A', 'Plano de prehorizontalidad nuevo'),
    ('MDUG0131A', 'Plano de Propiedad Horizontal modif/compl'),
    ('MDUG0131B', 'Plano de propiedad horizontal nuevo'),
    ('MDUG0115E', 'Rectificación de Plano de Mensura'),
    ('MDUG0134E', 'Solicitud de Certificado de fijación de línea'),
    ('MDUG0135A', 'Solicitud de consideración a la DGROC')
),
stats_mensuales AS (
    SELECT 
        trata_reporte as trata,
        COUNT(DISTINCT id_expediente) FILTER (WHERE fecha_ing >= '2026-01-01' AND fecha_ing <= '2026-01-31') as ing_01,
        COUNT(DISTINCT id_expediente) FILTER (WHERE fecha_ing >= '2026-02-01' AND fecha_ing <= '2026-02-28') as ing_02,
        COUNT(DISTINCT id_expediente) FILTER (WHERE fecha_ing >= '2026-03-01' AND fecha_ing <= '2026-03-31') as ing_03,
        COUNT(DISTINCT id_expediente) FILTER (WHERE fecha_ing >= '2026-04-01' AND fecha_ing <= '2026-04-30') as ing_04,
        COUNT(DISTINCT id_expediente) FILTER (WHERE fecha_ing >= '2026-05-01' AND fecha_ing <= '2026-05-31') as ing_05,
        
        COUNT(DISTINCT id_expediente) FILTER (WHERE fecha_egr >= '2026-01-01' AND fecha_egr <= '2026-01-31') as egr_01,
        COUNT(DISTINCT id_expediente) FILTER (WHERE fecha_egr >= '2026-02-01' AND fecha_egr <= '2026-02-28') as egr_02,
        COUNT(DISTINCT id_expediente) FILTER (WHERE fecha_egr >= '2026-03-01' AND fecha_egr <= '2026-03-31') as egr_03,
        COUNT(DISTINCT id_expediente) FILTER (WHERE fecha_egr >= '2026-04-01' AND fecha_egr <= '2026-04-30') as egr_04,
        COUNT(DISTINCT id_expediente) FILTER (WHERE fecha_egr >= '2026-05-01' AND fecha_egr <= '2026-05-31') as egr_05,
        
        COUNT(DISTINCT id_expediente) FILTER (WHERE status_gestion = 'ACTIVO') as stock_total
    FROM v_expedientes_lifecycle
    WHERE gerencia = 'catastro'
    GROUP BY 1
)
SELECT 
    tm.trata as "COD TRATA",
    tm.nombre_trata as "DETALLE TRATA",
    COALESCE(s.ing_01, 0) as "ING_01",
    COALESCE(s.ing_02, 0) as "ING_02",
    COALESCE(s.ing_03, 0) as "ING_03",
    COALESCE(s.ing_04, 0) as "ING_04",
    COALESCE(s.ing_05, 0) as "ING_05",
    COALESCE(s.egr_01, 0) as "EGR_TOT_01",
    COALESCE(s.egr_02, 0) as "EGR_TOT_02",
    COALESCE(s.egr_03, 0) as "EGR_TOT_03",
    COALESCE(s.egr_04, 0) as "EGR_TOT_04",
    COALESCE(s.egr_05, 0) as "EGR_TOT_05",
    COALESCE(s.stock_total, 0) as "STOCK TOTAL"
FROM tramites_metadata tm
LEFT JOIN stats_mensuales s ON tm.trata = s.trata
ORDER BY tm.nombre_trata;
