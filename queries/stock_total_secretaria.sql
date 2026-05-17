-- ============================================================
-- CONSULTA DE STOCK PROPIO TOTAL (REAL-TIME) - SECRETARÍA
-- Consolida Stock Propio e Intervenciones de todas las áreas
-- ============================================================

WITH stock_consolidado AS (
    -- CATASTRO
    SELECT 'catastro' as gerencia, id_expediente, trata, 'OFICIAL' as tipo_trata, 'STOCK_PROPIO' as categoria, dias_en_gerencia FROM mv_catastro_stock_propio
    UNION ALL SELECT 'catastro', id_expediente, trata, 'OFICIAL', 'SUBSANACION', dias_en_gerencia FROM mv_catastro_subsanaciones
    UNION ALL SELECT 'catastro', id_expediente, trata, 'INTERVENCION', 'STOCK_PROPIO', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_catastro_intervenciones_stock
    UNION ALL SELECT 'catastro', id_expediente, trata, 'INTERVENCION', 'SUBSANACION', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_catastro_intervenciones_subs

    -- INSTALACIONES
    UNION ALL SELECT 'instalaciones', id_expediente, trata, 'OFICIAL', 'STOCK_PROPIO', dias_en_gerencia FROM mv_instalaciones_stock_propio
    UNION ALL SELECT 'instalaciones', id_expediente, trata, 'OFICIAL', 'SUBSANACION', dias_en_gerencia FROM mv_instalaciones_subsanaciones
    UNION ALL SELECT 'instalaciones', id_expediente, trata, 'INTERVENCION', 'STOCK_PROPIO', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_instalaciones_intervenciones_stock
    UNION ALL SELECT 'instalaciones', id_expediente, trata, 'INTERVENCION', 'SUBSANACION', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_instalaciones_intervenciones_subs

    -- ETAPA PROYECTO
    UNION ALL SELECT 'etapa_proyecto', id_expediente, trata, 'OFICIAL', 'STOCK_PROPIO', dias_en_gerencia FROM mv_etapa_proyecto_stock_propio
    UNION ALL SELECT 'etapa_proyecto', id_expediente, trata, 'OFICIAL', 'SUBSANACION', dias_en_gerencia FROM mv_etapa_proyecto_subsanaciones
    UNION ALL SELECT 'etapa_proyecto', id_expediente, trata, 'INTERVENCION', 'STOCK_PROPIO', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_etapa_proyecto_intervenciones_stock
    UNION ALL SELECT 'etapa_proyecto', id_expediente, trata, 'INTERVENCION', 'SUBSANACION', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_etapa_proyecto_intervenciones_subs

    -- MORFOLOGIA
    UNION ALL SELECT 'morfologia', id_expediente, trata, 'OFICIAL', 'STOCK_PROPIO', dias_en_gerencia FROM mv_morfologia_stock_propio
    UNION ALL SELECT 'morfologia', id_expediente, trata, 'OFICIAL', 'SUBSANACION', dias_en_gerencia FROM mv_morfologia_subsanaciones
    UNION ALL SELECT 'morfologia', id_expediente, trata, 'INTERVENCION', 'STOCK_PROPIO', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_morfologia_intervenciones_stock
    UNION ALL SELECT 'morfologia', id_expediente, trata, 'INTERVENCION', 'SUBSANACION', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_morfologia_intervenciones_subs

    -- APH
    UNION ALL SELECT 'aph', id_expediente, trata, 'OFICIAL', 'STOCK_PROPIO', dias_en_gerencia FROM mv_aph_stock_propio
    UNION ALL SELECT 'aph', id_expediente, trata, 'OFICIAL', 'SUBSANACION', dias_en_gerencia FROM mv_aph_subsanaciones
    UNION ALL SELECT 'aph', id_expediente, trata, 'INTERVENCION', 'STOCK_PROPIO', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_aph_intervenciones_stock
    UNION ALL SELECT 'aph', id_expediente, trata, 'INTERVENCION', 'SUBSANACION', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_aph_intervenciones_subs

    -- USOS
    UNION ALL SELECT 'usos', id_expediente, trata, 'OFICIAL', 'STOCK_PROPIO', dias_en_gerencia FROM mv_usos_stock_propio
    UNION ALL SELECT 'usos', id_expediente, trata, 'OFICIAL', 'SUBSANACION', dias_en_gerencia FROM mv_usos_subsanaciones
    UNION ALL SELECT 'usos', id_expediente, trata, 'INTERVENCION', 'STOCK_PROPIO', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_usos_intervenciones_stock
    UNION ALL SELECT 'usos', id_expediente, trata, 'INTERVENCION', 'SUBSANACION', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_usos_intervenciones_subs

    -- AVISO DE OBRA
    UNION ALL SELECT 'aviso_obra', id_expediente, trata, 'OFICIAL', 'STOCK_PROPIO', dias_en_gerencia FROM mv_aviso_obra_stock_propio
    UNION ALL SELECT 'aviso_obra', id_expediente, trata, 'OFICIAL', 'SUBSANACION', dias_en_gerencia FROM mv_aviso_obra_subsanaciones
    UNION ALL SELECT 'aviso_obra', id_expediente, trata, 'INTERVENCION', 'STOCK_PROPIO', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_aviso_obra_intervenciones_stock
    UNION ALL SELECT 'aviso_obra', id_expediente, trata, 'INTERVENCION', 'SUBSANACION', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_aviso_obra_intervenciones_subs

    -- REGULARIZACION
    UNION ALL SELECT 'regularizacion', id_expediente, trata, 'OFICIAL', 'STOCK_PROPIO', dias_en_gerencia FROM mv_regularizacion_stock_propio
    UNION ALL SELECT 'regularizacion', id_expediente, trata, 'OFICIAL', 'SUBSANACION', dias_en_gerencia FROM mv_regularizacion_subsanaciones
    UNION ALL SELECT 'regularizacion', id_expediente, trata, 'INTERVENCION', 'STOCK_PROPIO', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_regularizacion_intervenciones_stock
    UNION ALL SELECT 'regularizacion', id_expediente, trata, 'INTERVENCION', 'SUBSANACION', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_regularizacion_intervenciones_subs

    -- CONTABLE
    UNION ALL SELECT 'contable', id_expediente, trata, 'OFICIAL', 'STOCK_PROPIO', dias_en_gerencia FROM mv_contable_stock_propio
    UNION ALL SELECT 'contable', id_expediente, trata, 'OFICIAL', 'SUBSANACION', dias_en_gerencia FROM mv_contable_subsanaciones
    UNION ALL SELECT 'contable', id_expediente, trata, 'INTERVENCION', 'STOCK_PROPIO', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_contable_intervenciones_stock
    UNION ALL SELECT 'contable', id_expediente, trata, 'INTERVENCION', 'SUBSANACION', (CURRENT_DATE - fecha_primer_ingreso_gerencia::date) as dias_en_gerencia FROM mv_contable_intervenciones_subs
)
SELECT 
    UPPER(gerencia) as "Área",
    COUNT(*) FILTER (WHERE dias_en_gerencia <= 90) as "Stock Corriente (<= 3 meses)",
    COUNT(*) FILTER (WHERE dias_en_gerencia > 90) as "Stock Sector (> 3 meses)",
    COUNT(*) as "Total Stock Propio"
FROM stock_consolidado
GROUP BY gerencia
ORDER BY "Total Stock Propio" DESC;
