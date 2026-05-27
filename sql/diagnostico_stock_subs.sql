-- Diagnóstico: Tratas con stock y subsanaciones faltantes
-- Compara valores esperados vs. retornados por MVs

WITH cfg AS (
  SELECT analistas_oficiales
  FROM cfg_gestion_metas
  WHERE gerencia = 'instalaciones' AND trata_reporte = 'INTERVENCIONES'
),

tratas_instalaciones AS (
  SELECT UNNEST(ARRAY['MDUG2101A','MDUG2901A','MDUG2501A','MDUG2201A','MDUG2701A','MDUG2401A','MDUG2601A','MDUG2301A','MDUG3301A','MDUG0904A','MDUG0120A','MJGG1601A','MDUG0101D','MDUG0101G','MJGG1701A']) AS trata
),

-- Stock esperado: expedientes propios con destino en analistas_oficiales (NO en subsanación)
stock_raw AS (
  SELECT 
    u.trata,
    COUNT(*) as cnt_raw
  FROM mv_instalaciones_universo u
  INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
  CROSS JOIN cfg
  WHERE u.es_trata_propia = TRUE
    AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
    AND u.estado_expediente NOT ILIKE '%SUBSAN%'
  GROUP BY u.trata
),

-- Subsanaciones esperadas: expedientes propios en mano de analista CON subsanación pendiente
subs_raw AS (
  SELECT 
    u.trata,
    COUNT(*) as cnt_raw
  FROM mv_instalaciones_universo u
  INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
  CROSS JOIN cfg
  WHERE u.es_trata_propia = TRUE
    AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
    AND EXISTS (
      SELECT 1
      FROM mvw_ee_actividades_secgdu a
      WHERE a.id_expediente = u.id_expediente
        AND a.usuario_alta = up.destinatario_actual
        AND a.estado = 'PENDIENTE'
        AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
    )
  GROUP BY u.trata
),

-- Stock desde MV
stock_mv AS (
  SELECT 
    trata,
    COUNT(*) as cnt_mv
  FROM mv_instalaciones_stock_propio
  GROUP BY trata
),

-- Subsanaciones desde MV
subs_mv AS (
  SELECT 
    trata,
    COUNT(*) as cnt_mv
  FROM mv_instalaciones_subsanaciones
  GROUP BY trata
)

SELECT 
  t.trata,
  COALESCE(sr.cnt_raw, 0) as stock_esperado,
  COALESCE(sm.cnt_mv, 0) as stock_mv,
  CASE WHEN COALESCE(sr.cnt_raw, 0) = 0 AND COALESCE(sm.cnt_mv, 0) = 0 THEN 'OK (ceros esperados)'
       WHEN COALESCE(sr.cnt_raw, 0) = 0 AND COALESCE(sm.cnt_mv, 0) > 0 THEN '⚠️ MV retorna datos sin raw'
       WHEN COALESCE(sr.cnt_raw, 0) > 0 AND COALESCE(sm.cnt_mv, 0) = 0 THEN '❌ FALTA stock'
       WHEN COALESCE(sr.cnt_raw, 0) != COALESCE(sm.cnt_mv, 0) THEN '⚠️ Diferencia'
       ELSE 'OK'
  END as estado_stock,
  COALESCE(subr.cnt_raw, 0) as subs_esperadas,
  COALESCE(subm.cnt_mv, 0) as subs_mv,
  CASE WHEN COALESCE(subr.cnt_raw, 0) = 0 AND COALESCE(subm.cnt_mv, 0) = 0 THEN 'OK (ceros esperados)'
       WHEN COALESCE(subr.cnt_raw, 0) = 0 AND COALESCE(subm.cnt_mv, 0) > 0 THEN '⚠️ MV retorna datos sin raw'
       WHEN COALESCE(subr.cnt_raw, 0) > 0 AND COALESCE(subm.cnt_mv, 0) = 0 THEN '❌ FALTA subs'
       WHEN COALESCE(subr.cnt_raw, 0) != COALESCE(subm.cnt_mv, 0) THEN '⚠️ Diferencia'
       ELSE 'OK'
  END as estado_subs
FROM tratas_instalaciones t
LEFT JOIN stock_raw sr ON t.trata = sr.trata
LEFT JOIN stock_mv sm ON t.trata = sm.trata
LEFT JOIN subs_raw subr ON t.trata = subr.trata
LEFT JOIN subs_mv subm ON t.trata = subm.trata
ORDER BY t.trata;

-- Validar si cfg_gestion_metas tiene las tratas
SELECT 'Tratas en cfg_gestion_metas (instalaciones):' as verificacion;
SELECT gerencia, trata_reporte, ARRAY_LENGTH(tratas_incluidas, 1) as cant_tratas 
FROM cfg_gestion_metas 
WHERE gerencia = 'instalaciones'
ORDER BY trata_reporte;

-- Validar condiciones de filtrado para stock (ejemplo para MDUG2101A)
SELECT 'Diagnóstico detallado para MDUG2101A - Stock:' as diagnostico;
WITH cfg2 AS (
  SELECT analistas_oficiales
  FROM cfg_gestion_metas
  WHERE gerencia = 'instalaciones' AND trata_reporte = 'INTERVENCIONES'
)
SELECT 
  COUNT(*) as total_exp_mdug2101a,
  SUM(CASE WHEN up.destinatario_actual = ANY(cfg2.analistas_oficiales) THEN 1 ELSE 0 END) as con_destino_analista,
  SUM(CASE WHEN u.estado_expediente NOT ILIKE '%SUBSAN%' THEN 1 ELSE 0 END) as sin_subsanacion_estado
FROM mv_instalaciones_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg2
WHERE u.trata = 'MDUG2101A'
  AND u.es_trata_propia = TRUE;
