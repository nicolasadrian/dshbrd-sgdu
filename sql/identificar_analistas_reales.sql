-- Identificar analistas/buzones REALES en el sistema para instalaciones

SELECT 'TODOS LOS DESTINATARIOS ÚNICOS EN INSTALACIONES:' as info;

SELECT 
  up.destinatario_actual,
  COUNT(*) as cantidad,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as porcentaje,
  CASE 
    WHEN up.destinatario_actual LIKE 'DGROC-%' THEN 'BUZÓN'
    WHEN up.destinatario_actual LIKE 'MJGG%' THEN 'BUZÓN'
    WHEN LENGTH(up.destinatario_actual) <= 20 AND up.destinatario_actual NOT LIKE '%-%' THEN 'USUARIO'
    ELSE 'OTRO'
  END as tipo
FROM mv_instalaciones_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
WHERE u.es_trata_propia = TRUE
GROUP BY up.destinatario_actual
ORDER BY cantidad DESC;

SELECT '';
SELECT 'DESTINATARIOS QUE PARECEN USUARIOS (no contienen guiones):' as info;

SELECT 
  destinatario_actual,
  COUNT(*) as cantidad
FROM (
  SELECT up.destinatario_actual
  FROM mv_instalaciones_universo u
  INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
  WHERE u.es_trata_propia = TRUE
    AND up.destinatario_actual NOT LIKE 'DGROC-%'
    AND up.destinatario_actual NOT LIKE 'MJGG%'
) subq
GROUP BY destinatario_actual
ORDER BY cantidad DESC;
