-- ============================================================
-- ARCHIVO 00: ALTER de cfg_gestion_metas y carga config APH
-- ============================================================

DELETE FROM cfg_gestion_metas WHERE gerencia = 'aph' AND trata_reporte = 'APH';

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
    'aph',
    'APH',
    ARRAY['MDUG3701A','MDUG3801A']::TEXT[],
    ARRAY['DICTAMEN','ANEXO','INFORME']::TEXT[],
    ARRAY['VASTAM']::TEXT[],
    ARRAY['DGIUR-21']::TEXT[],
    ARRAY[
        'CHANTIRRO','CHEZOM','DAMATOG','DESANTISA','DGIUR-21',
        'DGIUR-ADMISIBILIDADAPH','DGIUR-ADMISIMIDIDADAPH','GALAMA',
        'GONZALEZNIETOR','HERENUFE','LSANTINMOLINA','MARIANALVAREZ',
        'NASALVATIERRA','PIOLON','SVC_DGIURADMAPH','VASTAM'
    ]::TEXT[],
    ARRAY['DGIUR-21']::TEXT[]
);
