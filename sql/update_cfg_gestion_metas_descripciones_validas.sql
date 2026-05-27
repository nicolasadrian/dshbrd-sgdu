-- Actualiza cfg_gestion_metas para que MDUG3001A use el filtro de descripciones válido
-- Ejecutar con psql -f sql/update_cfg_gestion_metas_descripciones_validas.sql

ALTER TABLE cfg_gestion_metas
ADD COLUMN IF NOT EXISTS descripciones_validas text[];

COMMENT ON COLUMN cfg_gestion_metas.descripciones_validas IS
'Lista de descripciones del expediente que pertenecen al sector para esta trata. NULL = cualquier descripcion vale.';

-- MDUG3001A en regularizacion puede estar en la fila de INTERVENCIONES o en la fila de REGULARIZACIÓN Y CONFORME.
UPDATE cfg_gestion_metas
SET descripciones_validas = ARRAY[
    'Registro de plano conforme a obra civil',
    'Registro de plano de obra civil conforme de obra'
]::text[]
WHERE gerencia = 'regularizacion' AND trata_reporte IN ('MDUG3001A');

UPDATE cfg_gestion_metas
SET descripciones_validas = ARRAY[
    'Registro de plano de obra civil etapa proyecto'
]::text[]
WHERE gerencia = 'etapa_proyecto' AND trata_reporte IN ('MDUG3001A');
