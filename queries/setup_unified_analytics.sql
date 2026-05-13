-- 1. Creación de la Tabla de Configuración Centralizada
-- Esta tabla será el "Cerebro" de la gestión de stock y metas
DROP TABLE IF EXISTS cfg_gestion_metas CASCADE;

CREATE TABLE cfg_gestion_metas (
    id SERIAL PRIMARY KEY,
    gerencia TEXT NOT NULL,
    trata_reporte TEXT NOT NULL, -- El nombre del trámite en el reporte (ej: MDUG0115C o INTERVENCIONES)
    tratas_incluidas TEXT[] NOT NULL, -- Array de códigos SADE reales (ej: ['MDUG0115C'])
    buzones_ingreso TEXT[] NOT NULL, -- Buzones que marcan el ingreso al área
    analistas_oficiales TEXT[] NOT NULL, -- Usuarios cuyo poder es "Stock Propio"
    acronimos_egreso TEXT[] NOT NULL, -- GEDOs que cierran el trámite
    metas_mensuales JSONB DEFAULT '{}'::jsonb, -- Espacio para futuras metas por mes
    activo BOOLEAN DEFAULT TRUE,
    UNIQUE(gerencia, trata_reporte)
);

-- 2. Carga Inicial de Datos para CATASTRO (Modelo)
INSERT INTO cfg_gestion_metas (gerencia, trata_reporte, tratas_incluidas, buzones_ingreso, analistas_oficiales, acronimos_egreso)
VALUES (
    'catastro', 
    'MDUG0115C', 
    ARRAY['MDUG0115C'], 
    ARRAY['DGROC-DCATDES', 'DGROC-DCATMEN', 'DGROC-DCATPOL', 'DGROC-DCATTIT'], 
    ARRAY['ACOSTAPA', 'AFAHLER', 'AGUSMAZZONI', 'ALEALFONSIN', 'ALEGREM', 'ARGENTOES', 'BARTROLIG', 'CABRERAM', 'CANALEAL', 'CARBONELLIM', 'CHIANETTAR', 'CIOPKOG', 'CISTERNACA', 'COHENCAD', 'CONTIL', 'CONVERTID', 'DELGADODE', 'DIBIASEO', 'DIEZGASTON', 'DIHARCEP', 'DURSIM', 'ECIJAN', 'FMARCHISELLA', 'FOLLONIERLE', 'FREIXASC', 'GARCIASIL', 'GILESJP', 'GONZALEZAMA', 'GONZALEZHORAC', 'GUZMANO', 'IGARZABALP', 'JTIRADO', 'LAGUNAMA', 'LBELLY', 'LOISIG', 'LUCCIC', 'M.NAPOLI', 'MALATTOR', 'MANNOP', 'MARCHETTIJ', 'MHOSBALIKCIYAN', 'MOSCOVICHA', 'NCITRANGOLO', 'NOGUERAH', 'NPONZO', 'NQUINTERNO', 'PONZOS', 'ROLDANG', 'SALGUEROM', 'SORIAANDREA', 'TARRUA', 'TAVELLAE', 'VEGAJ', 'VILLAGI', 'WVIRGILIO'],
    ARRAY['IF', 'IFDEX', 'DI']
),
(
    'catastro', 
    'INTERVENCIONES', 
    ARRAY['MDUG0115C', 'MDUG1501L', 'MDUG0115G', 'MDUG1501H', 'MDUG0134C', 'MDUG0134N', 'MDUG0146A', 'GENE0702C', 'MDUG0115F', 'MDUG0115B', 'MDUG0132A', 'MDUG0131A', 'MDUG0131B', 'MDUG0115E', 'MDUG0134E', 'MDUG0135A'], 
    ARRAY['DGROC-DCATDES', 'DGROC-DCATMEN', 'DGROC-DCATPOL', 'DGROC-DCATTIT'], 
    ARRAY['ACOSTAPA', 'AFAHLER', 'AGUSMAZZONI', 'ALEALFONSIN', 'ALEGREM', 'ARGENTOES', 'BARTROLIG', 'CABRERAM', 'CANALEAL', 'CARBONELLIM', 'CHIANETTAR', 'CIOPKOG', 'CISTERNACA', 'COHENCAD', 'CONTIL', 'CONVERTID', 'DELGADODE', 'DIBIASEO', 'DIEZGASTON', 'DIHARCEP', 'DURSIM', 'ECIJAN', 'FMARCHISELLA', 'FOLLONIERLE', 'FREIXASC', 'GARCIASIL', 'GILESJP', 'GONZALEZAMA', 'GONZALEZHORAC', 'GUZMANO', 'IGARZABALP', 'JTIRADO', 'LAGUNAMA', 'LBELLY', 'LOISIG', 'LUCCIC', 'M.NAPOLI', 'MALATTOR', 'MANNOP', 'MARCHETTIJ', 'MHOSBALIKCIYAN', 'MOSCOVICHA', 'NCITRANGOLO', 'NOGUERAH', 'NPONZO', 'NQUINTERNO', 'PONZOS', 'ROLDANG', 'SALGUEROM', 'SORIAANDREA', 'TARRUA', 'TAVELLAE', 'VEGAJ', 'VILLAGI', 'WVIRGILIO'],
    ARRAY['IF', 'IFDEX', 'DI']
);

-- 3. La lógica de v_expedientes_lifecycle se maneja ahora en queries/v_expedientes_lifecycle.sql
