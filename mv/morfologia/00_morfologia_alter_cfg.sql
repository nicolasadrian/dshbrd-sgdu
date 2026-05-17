-- ============================================================
-- ARCHIVO 00: ALTER de cfg_gestion_metas y carga config Morfología
-- ============================================================
-- PROPÓSITO: 
--   1) Agregar columna firmantes_egreso (si no existe).
--   2) Cargar la fila MORFOLOGIA en cfg_gestion_metas.
-- ORDEN DE EJECUCIÓN: 1° (antes de todo lo demás).
-- ============================================================

-- Paso 1: Agregar columna firmantes_egreso si no existe
ALTER TABLE cfg_gestion_metas 
ADD COLUMN IF NOT EXISTS firmantes_egreso TEXT[];

COMMENT ON COLUMN cfg_gestion_metas.firmantes_egreso IS 
'Lista de usuarios cuyas firmas en GEDOs de la lista acronimos_egreso cuentan como egreso efectivo. NULL = cualquier firmante.';


-- Paso 2: Borrar fila previa de morfologia si existe (idempotente)
DELETE FROM cfg_gestion_metas 
WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA';


-- Paso 3: Cargar config de Morfología
INSERT INTO cfg_gestion_metas (
    gerencia,
    trata_reporte,
    tratas_incluidas,
    acronimos_egreso,
    firmantes_egreso,
    buzones_ingreso,
    analistas_oficiales
)
VALUES (
    'morfologia',
    'MORFOLOGIA',
    -- Tratas propias (10 tratas)
    ARRAY[
        'MDUG1801A','MDUG0107A','MDUG3501A','MDUG3601A','MDUG3901A',
        'MDUG1802A','MDUG1804A','MDUG1803A','MDUG1805A','MDUG1806A'
    ]::TEXT[],
    -- Acrónimos de egreso (DI, ANEXO, IF)
    ARRAY['DI','ANEXO','IF']::TEXT[],
    -- Firmantes oficiales para egreso efectivo
    ARRAY['ALANDAZURI']::TEXT[],
    -- Buzones de ingreso (1 buzón para tratas propias)
    ARRAY['DGIUR-03']::TEXT[],
    -- Analistas oficiales (lista completa)
    ARRAY[
        'A.GUZMAN','AGARTEAGA','ALANDAZURI','ALFONSOGA','CAROLINAPRADO',
        'CGAMARRA','CGENTILINI','DANCOLOMBO','DGIUR-03','DGIUR-ADMISIBILIDADMORFO',
        'DGIUR-CONSULTASESPECIFICAS','DGIUR-CURVERIFICACION','DGIUR-DGIUR-PERMISO TEMPRANO','DGIUR-VA II',
        'ECAYSSIALS','EVELYNTORRES','FORFANO','FOTTOGALLI','FRANGARAY',
        'GBERNASCONI','GCABADGIUR','IANELUSTONDO','IVALDES','LNSPERTINO',
        'M.SABATINO','MANUELALVELO','MILAGROSTOURON','MILENAAZULMORENO','MLOBIANCOCRIADO',
        'MPLANS1','MREIDMAN','MVOSKIAN','NASILANES','NCASALE',
        'OVERRINA','PTEIGA','ROCAM','SBONDOREVSKY','SCABANELLAS',
        'SDAVIDOVSKY','SVC_DGIURMORFO','SVCDGIUR3','TOSELLIR','VVINICIUS'
    ]::TEXT[]
);


-- Paso 4: Para intervenciones, agregamos también los buzones extra como puntos de ingreso
-- Esto es porque las intervenciones de morfología pueden entrar por más buzones que las propias.
-- Vamos a manejarlo creando una columna nueva o lo resolveremos en la MV del universo.
-- Por ahora, anotamos los 5 buzones adicionales de intervenciones en un campo nuevo.
ALTER TABLE cfg_gestion_metas
ADD COLUMN IF NOT EXISTS buzones_ingreso_intervenciones TEXT[];

COMMENT ON COLUMN cfg_gestion_metas.buzones_ingreso_intervenciones IS 
'Buzones adicionales por los que ingresan SOLO intervenciones (no aplica a tratas propias). NULL = usar buzones_ingreso.';

UPDATE cfg_gestion_metas 
SET buzones_ingreso_intervenciones = ARRAY[
    'DGIUR-03',
    'DGIUR-ADMISIBILIDADMORFO',
    'DGIUR-CONSULTASESPECIFICAS',
    'DGIUR-CURVERIFICACION',
    'DGIUR-DGIUR-PERMISO TEMPRANO',
    'DGIUR-VA II'
]::TEXT[]
WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA';


-- Paso 5: Verificación
SELECT 
    gerencia,
    trata_reporte,
    array_length(tratas_incluidas, 1)               AS n_tratas_propias,
    array_length(acronimos_egreso, 1)               AS n_acronimos,
    array_length(firmantes_egreso, 1)               AS n_firmantes,
    array_length(buzones_ingreso, 1)                AS n_buzones_propios,
    array_length(buzones_ingreso_intervenciones, 1) AS n_buzones_intervenciones,
    array_length(analistas_oficiales, 1)            AS n_analistas
FROM cfg_gestion_metas
WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA';

-- Esperado:
-- n_tratas_propias: 10
-- n_acronimos: 3
-- n_firmantes: 1
-- n_buzones_propios: 1
-- n_buzones_intervenciones: 6
-- n_analistas: 44
