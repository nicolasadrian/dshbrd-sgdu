-- Vista Materializada: GLOBAL (Unificada)
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_dgroc;

CREATE MATERIALIZED VIEW mvw_reporte_historico_dgroc AS
SELECT * FROM mvw_reporte_historico_catastro
UNION ALL
SELECT * FROM mvw_reporte_historico_instalaciones
UNION ALL
SELECT * FROM mvw_reporte_historico_regularizacion
UNION ALL
SELECT * FROM mvw_reporte_historico_contable
UNION ALL
SELECT * FROM mvw_reporte_historico_etapa_proyecto
UNION ALL
SELECT * FROM mvw_reporte_historico_aviso_obra;
