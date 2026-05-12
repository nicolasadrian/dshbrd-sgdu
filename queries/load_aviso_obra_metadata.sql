-- Carga de Metadatos: Aviso de Obra
INSERT INTO cfg_gestion_metas (gerencia, trata_reporte, tratas_incluidas, buzones_ingreso, analistas_oficiales, acronimos_egreso)
VALUES (
    'aviso_obra', 
    'MDUG0102B', 
    ARRAY['MDUG0102B'], 
    ARRAY['DGROC-AUTOMAT'], 
    ARRAY['DGROC-AUTOMAT'], 
    ARRAY['IFCAO', 'IFCFP', 'IFCAC']
),
(
    'aviso_obra', 
    'INTERVENCIONES', 
    ARRAY['MDUG0102B'], 
    ARRAY['DGROC-AUTOMAT'], 
    ARRAY['DGROC-AUTOMAT'], 
    ARRAY[]::text[]
)
ON CONFLICT (gerencia, trata_reporte) DO UPDATE SET
    tratas_incluidas = EXCLUDED.tratas_incluidas,
    buzones_ingreso = EXCLUDED.buzones_ingreso,
    analistas_oficiales = EXCLUDED.analistas_oficiales,
    acronimos_egreso = EXCLUDED.acronimos_egreso;
