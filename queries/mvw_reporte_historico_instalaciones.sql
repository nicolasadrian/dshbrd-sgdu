-- REFACTOR FINAL: Reporte Histórico INSTALACIONES (Súper Optimizado)
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_instalaciones CASCADE;

CREATE MATERIALIZED VIEW mvw_reporte_historico_instalaciones AS
WITH tramites_metadata (gerencia, trata, nombre_trata, acronimos_list) AS (
    VALUES 
    ('instalaciones', 'MDUG2101A', 'Registro de Plano de Prevención contra Incendios.', ARRAY['PROIN', 'PLINE', 'IFCIS', 'IFSMC', 'IFRSP']),
    ('instalaciones', 'MDUG2901A', 'Registro de Plano de Elementos Guiados de Transporte.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2501A', 'Registro de Plano de Instalación de Inflamables.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2201A', 'Registro de Plano de Instalación de Ventilación Mecánica.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2701A', 'Registro de Plano de Instalación Eléctrica.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2401A', 'Registro de Plano de Instalación Electromecánica.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2601A', 'Registro de Plano de Instalación Sanitaria.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2301A', 'Registro de Plano de Instalación Térmica.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG3301A', 'Registro de Plano de Sala de Máquinas.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG0904A', 'Ascenso de Categoría de Foguistas.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG0120A', 'Solicitud Examen de Foguista.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MJGG1601A', 'Registro de planos de prototipo de equipos.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG0101D', 'Ajuste De Instalacion Elementos Guiados De Transporte.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG0101G', 'Ajuste De Instalacion Termica.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MJGG1701A', 'Transferencia de Titularidad de Instalación.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'INTERVENCIONES', 'Intervenciones', ARRAY['PROIN', 'PLINE', 'IFCIS', 'IFSMC', 'IFRSP'])
),
periodos AS (
    SELECT 
        EXTRACT(YEAR FROM s.d)::int as anio, 
        EXTRACT(MONTH FROM s.d)::int as mes,
        (s.d + interval '1 month' - interval '1 day')::date as fin_mes,
        date_trunc('month', s.d)::date as inicio_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
),
lifecycle AS (
    SELECT * FROM v_expedientes_lifecycle WHERE gerencia = 'instalaciones'
),
stats_base AS (
    SELECT 
        l.trata_reporte,
        p.anio,
        p.mes,
        COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= p.inicio_mes AND l.fecha_ing <= p.fin_mes) as ing,
        COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_egr >= p.inicio_mes AND l.fecha_egr <= p.fin_mes AND l.tipo_egr = 'EFECTIVO') as egr_ef,
        COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_egr >= p.inicio_mes AND l.fecha_egr <= p.fin_mes AND l.tipo_egr = 'NO_EFECTIVO') as egr_ne,
        COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing <= p.fin_mes AND (l.fecha_egr IS NULL OR l.fecha_egr > p.fin_mes)) as stock_bruto
    FROM lifecycle l
    CROSS JOIN periodos p
    GROUP BY 1, 2, 3
),
subs_mensuales AS (
    SELECT 
        l.trata_reporte,
        p.anio,
        p.mes,
        COUNT(DISTINCT t.id_expediente) as stock_subs
    FROM mvw_pases_timeline t
    JOIN lifecycle l ON t.id_expediente = l.id_expediente
    CROSS JOIN periodos p
    WHERE t.is_subs = 1 
      AND t.fecha_inicio <= p.fin_mes 
      AND (t.fecha_fin IS NULL OR t.fecha_fin > p.fin_mes)
    GROUP BY 1, 2, 3
)
SELECT 
    tm.gerencia as "GERENCIA",
    tm.trata as "COD TRATA",
    tm.nombre_trata as "DETALLE TRATA",
    p.anio,
    p.mes,
    COALESCE(s.ing, 0) as "ING",
    COALESCE(s.egr_ef, 0) as "EGR_EF",
    COALESCE(s.egr_ne, 0) as "EGR_NE",
    COALESCE(sm.stock_subs, 0) as "STOCK_SUBS",
    (COALESCE(s.stock_bruto, 0) - COALESCE(sm.stock_subs, 0)) as "STOCK_PROPIO"
FROM tramites_metadata tm
CROSS JOIN periodos p
LEFT JOIN stats_base s ON tm.trata = s.trata_reporte AND p.anio = s.anio AND p.mes = s.mes
LEFT JOIN subs_mensuales sm ON tm.trata = sm.trata_reporte AND p.anio = sm.anio AND p.mes = sm.mes
ORDER BY 1, 2, 4, 5;
