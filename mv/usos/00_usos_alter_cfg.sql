-- ============================================================
-- ARCHIVO 00: ALTER de cfg_gestion_metas y carga config USOS
-- ============================================================

DELETE FROM cfg_gestion_metas WHERE gerencia = 'usos' AND trata_reporte = 'USOS';

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
    'usos',
    'USOS',
    ARRAY['MDUG0136B','MDUG4102A','MDUG4001A','MDUG4002A','MJGG0302A','MJGG0303A']::TEXT[],
    ARRAY['DICTAMEN','ANEXO','INFORME']::TEXT[],
    ARRAY['FOVERDAGUER','MIZONCA','DALUNNI']::TEXT[],
    ARRAY['DGIUR-12']::TEXT[],
    ARRAY[
        'ALEPABLOCASTRO','ARVASR','AUZONMJ','BBORGIA','BILLAUDL',
        'CLAUDIAVARELA','DALUNNI','DGIUR-12','DGIUR-ADMISIBILIDADUSOS',
        'DGIUR-EGOUS','DIMEGLIOA','EDUARDODIAZ','ELIANACABRERA',
        'FOVERDAGUER','JBMENDY','JLSCIA','JLSCIARROTTA','LASALAMI',
        'LTROLDAN','MAYASTUY','MERCADOEA','MFALAPPA','MIZONCA',
        'MOCANA','MOURER','MPSIMONI','MYASTUY','PGLEISS','PORTAC',
        'ROCCOR','SOFIAZANI','SVC_DGIURUSOS','VKAUFMAN'
    ]::TEXT[],
    ARRAY['DGIUR-12']::TEXT[]
);
