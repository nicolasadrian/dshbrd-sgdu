-- ============================================================
-- ARCHIVO 00: ALTER de cfg_gestion_metas y carga config Etapa Proyecto
-- ============================================================

-- Paso 1: Asegurar columnas
ALTER TABLE cfg_gestion_metas 
ADD COLUMN IF NOT EXISTS firmantes_egreso TEXT[];

ALTER TABLE cfg_gestion_metas
ADD COLUMN IF NOT EXISTS buzones_ingreso_intervenciones TEXT[];

-- Paso 2: Borrar fila previa si existe
DELETE FROM cfg_gestion_metas 
WHERE gerencia = 'etapa_proyecto' AND trata_reporte = 'ETAPA PROYECTO';

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
    'etapa_proyecto',
    'ETAPA PROYECTO',
    ARRAY['MDUG3402A','MDUG1502A','MDUG4003A','MDUG0142A','MDUG3001A']::TEXT[],
    ARRAY['IFTPT','IFOCD','IFBRP']::TEXT[],
    NULL, -- Cualquier firmante cuenta como egreso
    ARRAY['DGROC-OBRASTECNICA']::TEXT[],
    ARRAY[
        'A.PEREZ','AGUSDEMARCO','ANTOVERA','BELOCURESJ','COIROL',
        'DBECERRACURITIMA','DGROC-OBRASTECNICA','DIMASOM','DNKAINSKY','FORGIONEA',
        'GAILLURJP','GARRIONDO','JOSEFINA.P','M.SANCHEZ','MARCE.TOSONI',
        'MARCETOSONI','MARCETOSONI1','MBRISA','MCANOGARAY','MCARLUCCIO',
        'MGALLARDOC','MSTIBERTI','NLOPEZQUIROGA','ROCABERTJ','SPUET',
        'TALAMOM','VERA'
    ]::TEXT[],
    ARRAY['DGROC-OBRASTECNICA']::TEXT[] -- Intervenciones entran por el mismo buzón
);
