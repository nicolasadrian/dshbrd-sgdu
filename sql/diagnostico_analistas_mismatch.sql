-- Diagnóstico profundo: ¿por qué no coinciden los analistas?

SELECT 'ANALISTAS OFICIALES CONFIGURADOS:' as info;

WITH cfg AS (
  SELECT analistas_oficiales
  FROM cfg_gestion_metas
  WHERE gerencia = 'instalaciones' AND trata_reporte = 'INTERVENCIONES'
)
SELECT UNNEST(cfg.analistas_oficiales) as analista
FROM cfg
ORDER BY analista;

SELECT '';
SELECT 'DESTINATARIOS ACTUALES EN MDUG2101A (primeros 20 únicos):' as info;

SELECT DISTINCT up.destinatario_actual, COUNT(*) as cantidad
FROM mv_instalaciones_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
WHERE u.trata = 'MDUG2101A' AND u.es_trata_propia = TRUE
GROUP BY up.destinatario_actual
ORDER BY cantidad DESC
LIMIT 20;

SELECT '';
SELECT 'ANÁLISIS DE CARACTERES (primeros destinatario encontrado):' as info;

SELECT 
  up.destinatario_actual,
  LENGTH(up.destinatario_actual) as largo,
  ASCII(up.destinatario_actual) as primer_ascii,
  up.destinatario_actual = 'AQUINOLUCAS' as es_aquinolucas
FROM mv_instalaciones_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
WHERE u.trata = 'MDUG2101A' AND u.es_trata_propia = TRUE
LIMIT 5;

SELECT '';
SELECT 'COINCIDENCIAS CON ARRAY:' as info;

WITH cfg AS (
  SELECT ARRAY['AQUINOLUCAS','ARENAJ','ARGUELLOJ','BATALLANJ','BENITOG','BRIANMARTINEZ','CORNAZM','FICARRAR','GAGLIARDIA','LOPARDOC','QUEIJASGUILLINP','ROBLEDOJO','ROLDANMI','RUDAC','SARIDISD','TOLESANOA','AURENA','BATALLANGE','BRITANP','GUARDADOB','JDECIMA','PEREZGA','RODRIGUEZESTEBAN','RODRIGUEZNE','SILESC','VILLAGAB'] AS analistas_oficiales
)
SELECT 
  COUNT(*) as total_mdug2101a,
  SUM(CASE WHEN up.destinatario_actual = ANY(cfg.analistas_oficiales) THEN 1 ELSE 0 END) as coinciden,
  SUM(CASE WHEN up.destinatario_actual NOT IN (SELECT UNNEST(cfg.analistas_oficiales)) THEN 1 ELSE 0 END) as no_coinciden
FROM mv_instalaciones_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.trata = 'MDUG2101A' AND u.es_trata_propia = TRUE;

SELECT '';
SELECT 'TOP 10 DESTINATARIOS NO COINCIDENTES:' as info;

WITH cfg AS (
  SELECT ARRAY['AQUINOLUCAS','ARENAJ','ARGUELLOJ','BATALLANJ','BENITOG','BRIANMARTINEZ','CORNAZM','FICARRAR','GAGLIARDIA','LOPARDOC','QUEIJASGUILLINP','ROBLEDOJO','ROLDANMI','RUDAC','SARIDISD','TOLESANOA','AURENA','BATALLANGE','BRITANP','GUARDADOB','JDECIMA','PEREZGA','RODRIGUEZESTEBAN','RODRIGUEZNE','SILESC','VILLAGAB'] AS analistas_oficiales
)
SELECT 
  up.destinatario_actual,
  COUNT(*) as cantidad
FROM mv_instalaciones_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.trata = 'MDUG2101A' 
  AND u.es_trata_propia = TRUE
  AND up.destinatario_actual NOT IN (SELECT UNNEST(cfg.analistas_oficiales))
GROUP BY up.destinatario_actual
ORDER BY cantidad DESC
LIMIT 10;
