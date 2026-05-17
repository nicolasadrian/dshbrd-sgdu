-- ============================================================
-- ARCHIVO 00: ALTER de cfg_gestion_metas y carga config Catastro
-- ============================================================

-- Paso 1: Asegurar columnas
ALTER TABLE cfg_gestion_metas 
ADD COLUMN IF NOT EXISTS firmantes_egreso TEXT[];

ALTER TABLE cfg_gestion_metas
ADD COLUMN IF NOT EXISTS buzones_ingreso_intervenciones TEXT[];

-- Paso 2: Borrar fila previa si existe
DELETE FROM cfg_gestion_metas 
WHERE gerencia = 'catastro' AND trata_reporte = 'CATASTRO';

-- Paso 3: Cargar config
INSERT INTO cfg_gestion_metas (
    gerencia,
    trata_reporte,
    tratas_incluidas,
    acronimos_egreso,
    firmantes_egreso,
    buzones_ingreso,
    analistas_oficiales,
    buzones_ingreso_intervenciones
)
VALUES (
    'catastro',
    'CATASTRO',
    ARRAY[
        'MDUG0115C','MDUG1501L','MDUG0115G','MDUG1501H','MDUG0134C',
        'MDUG0134N','MDUG0146A','GENE0702C','MDUG0115F','MDUG0115B',
        'MDUG0132A','MDUG0131A','MDUG0131B','MDUG0115E','MDUG0134E','MDUG0135A'
    ]::TEXT[],
    ARRAY[
        'IFMMH','IFMAD','IF','IFDEX','CECNU','IFGPA','FIPAR','IFPCB',
        'PPINV','IFMOT','IFMSC','IFMHC'
    ]::TEXT[],
    NULL, -- Cualquier firmante cuenta como egreso
    ARRAY['DGROC-CIC','DGROC-COPIAPLANO','DGROC-DCATDES','DGROC-DCATPOL','DGROC-DCATTIT']::TEXT[],
    ARRAY[
        'ACOSTAPA','AFAHLER','AGUSMAZZONI','ALEALFONSIN','ALEGREM',
        'ARGENTOES','BARTROLIG','CABRERAM','CANALEAL','CARBONELLIM',
        'CHIANETTAR','CIOPKOG','CISTERNACA','COHENCAD','CONTIL',
        'CONVERTID','DELGADODE','DGROC-CIC','DGROC-COPIAPLANO','DGROC-DCATDES',
        'DGROC-DCATMEN','DGROC-DCATPOL','DGROC-DCATTIT','DIBIASEO','DIEZGASTON',
        'DIHARCEP','DURSIM','ECIJAN','FMARCHISELLA','FOLLONIERLE',
        'FREIXASC','GARCIASIL','GILESJP','GONZALEZAMA','GONZALEZHORAC',
        'GUZMANO','IGARZABALP','JTIRADO','LAGUNAMA','LBELLY',
        'LOISIG','LUCCIC','M.NAPOLI','MALATTOR','MANNOP',
        'MARCHETTIJ','MHOSBALIKCIYAN','MOSCOVICHA','NCITRANGOLO','NOGUERAH',
        'NPONZO','NQUINTERNO','PONZOS','ROLDANG','SALGUEROM',
        'SORIAANDREA','TARRUA','TAVELLAE','VEGAJ','VILLAGI',
        'WVIRGILIO'
    ]::TEXT[],
    ARRAY['DGROC-CIC','DGROC-COPIAPLANO','DGROC-DCATDES','DGROC-DCATPOL','DGROC-DCATTIT']::TEXT[]
);
