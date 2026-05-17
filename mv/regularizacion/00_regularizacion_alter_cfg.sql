-- ============================================================
-- ARCHIVO 00: ALTER de cfg_gestion_metas y carga config Regularización
-- ============================================================

DELETE FROM cfg_gestion_metas WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME';

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
    'regularizacion',
    'REGULARIZACIÓN Y CONFORME',
    ARRAY['MDUG0104A','MDUG0141A','MDUG3001A','MDUG1501K']::TEXT[],
    ARRAY['IFROC','IFPCO','IFSMI','IFPDO']::TEXT[],
    NULL, -- Cualquier firmante
    ARRAY['DGROC-OBRASDEMO','DGROC-OBRASTECNICA']::TEXT[],
    ARRAY[
        'AGUEROJO','AKRACOFF','ALVAREZ.M','ARAOZLUIS','ATENCIOAL','DALBORAF',
        'DGROC-ESPERAINSTALACIONES','DGROC-OBRASDEMO','ENCISOA','EPARLATO',
        'ERDOCIAINA','JBARRACO','JLGARMENDIA','JTERRILE','MYUSHU',
        'S.SANCHEZPAZ','SCAVALLARO'
    ]::TEXT[],
    ARRAY['DGROC-OBRASDEMO','DGROC-OBRASTECNICA']::TEXT[]
);
