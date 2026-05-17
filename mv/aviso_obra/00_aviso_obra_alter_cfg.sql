-- ============================================================
-- ARCHIVO 00: ALTER de cfg_gestion_metas y carga config Aviso de Obra
-- ============================================================

DELETE FROM cfg_gestion_metas WHERE gerencia = 'aviso_obra' AND trata_reporte = 'AVISO DE OBRA';

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
    'aviso_obra',
    'AVISO DE OBRA',
    ARRAY['MDUG0102B']::TEXT[],
    ARRAY['IFCAO','IFCFP','IFCAC']::TEXT[],
    NULL, -- Cualquier firmante
    ARRAY['DGROC-AUTOMAT']::TEXT[],
    ARRAY['DGROC-AUTOMAT']::TEXT[],
    ARRAY['DGROC-AUTOMAT']::TEXT[]
);
