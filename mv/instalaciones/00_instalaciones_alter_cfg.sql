-- ============================================================
-- ARCHIVO 00: ALTER de cfg_gestion_metas y carga config Instalaciones
-- ============================================================

DELETE FROM cfg_gestion_metas WHERE gerencia = 'instalaciones' AND trata_reporte = 'INSTALACIONES';

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
    'instalaciones',
    'INSTALACIONES',
    ARRAY[
        'MDUG2101A','MDUG2901A','MDUG2501A','MDUG2201A','MDUG2701A',
        'MDUG2401A','MDUG2601A','MDUG2301A','MDUG3301A','MDUG0904A',
        'MDUG0120A','MJGG1601A','MDUG0101D','MDUG0101G','MJGG1701A'
    ]::TEXT[],
    ARRAY['PROIN','PLINE','IFCIS','IFSMC','IFRSP']::TEXT[],
    NULL, -- Cualquier firmante
    ARRAY[
        'DGROC-ELECTRICAS','DGROC-ELEVADORES','DGROC-INCENDIO',
        'DGROC-SANITARIAS','DGROC-TERMICAS','DGROC-DCIMYE',
        'DGROC-DCIELEV','DGROC-DCIDITI'
    ]::TEXT[],
    ARRAY[
        'AQUINOLUCAS','ARENAJ','ARGUELLOJ','BATALLANJ','BENITOG','BRIANMARTINEZ',
        'CORNAZM','FICARRAR','GAGLIARDIA','LOPARDOC','QUEIJASGUILLINP','ROBLEDOJO',
        'ROLDANMI','RUDAC','SARIDISD','TOLESANOA','AURENA','BATALLANGE','BRITANP',
        'GUARDADOB','JDECIMA','PEREZGA','RODRIGUEZESTEBAN','RODRIGUEZNE','SILESC',
        'VILLAGAB','ABCRAGNO','AGARCIAFIGUEROA','CABRERAARI','CAFELICE','CAPOZZOG',
        'CSALGUERO','DARANGURI','DMOFFA','FUHRY','GONMAR','J.OLIVERA','LOPEZFE',
        'MARIANELAROCARO','MBALDOME','MLMAMONE','MTRENQUE','NIEVAL','PCHERBENCO',
        'RADAA','RIOSFE','ROMANOFLA','SANTACRUZ','CANTARELLTORRES','CIRIAE',
        'LOIACONOANA','MCDIAMANTI','POUSAF','ARGUELLOSOL','COSSM','EIERACI',
        'HAMALAG','RUIZMA','BRITANG','ENCISOROMERO','PITTERIE','WIERZBICKIIGOR'
    ]::TEXT[],
    ARRAY[
        'DGROC-ELECTRICAS','DGROC-ELEVADORES','DGROC-INCENDIO',
        'DGROC-SANITARIAS','DGROC-TERMICAS','DGROC-DCIMYE',
        'DGROC-DCIELEV','DGROC-DCIDITI'
    ]::TEXT[]
);
