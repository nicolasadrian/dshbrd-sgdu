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

-- 3. Vista de Lifecycle Unificada
-- Esta vista procesa el ciclo de vida de cada expediente basado en la configuración
DROP VIEW IF EXISTS v_expedientes_lifecycle CASCADE;

CREATE VIEW v_expedientes_lifecycle AS
WITH pases_filtrados AS (
    SELECT p.id_expediente, p.fecha, p.destinatario, p.estado,
           LAG(p.destinatario) OVER (PARTITION BY p.id_expediente ORDER BY p.fecha) as remitente
    FROM mvw_ee_pases_secgdu p
),
ingresos AS (
    SELECT 
        p.id_expediente, 
        cfg.gerencia, 
        cfg.trata_reporte,
        MIN(p.fecha)::date as fecha_ing
    FROM pases_filtrados p
    JOIN mvw_expedientes_tratas_secgdu et ON p.id_expediente = et.id_expediente
    JOIN cfg_gestion_metas cfg ON et.trata = ANY(cfg.tratas_incluidas)
    WHERE p.destinatario = ANY(cfg.buzones_ingreso)
    GROUP BY 1, 2, 3
),
egresos_gedo AS (
    SELECT 
        g.id_expediente, 
        i.gerencia,
        i.trata_reporte,
        MIN(g.fecha_creacion)::date as fecha_egr,
        'EFECTIVO' as tipo_egr
    FROM mvw_datos_gedo_secgdu g
    JOIN ingresos i ON g.id_expediente = i.id_expediente
    JOIN cfg_gestion_metas cfg ON i.gerencia = cfg.gerencia AND i.trata_reporte = cfg.trata_reporte
    WHERE g.acronimo = ANY(cfg.acronimos_egreso) AND g.fecha_creacion >= i.fecha_ing
    GROUP BY 1, 2, 3
),
egresos_pases AS (
    -- Un egreso por pase ocurre cuando el expediente sale del área y NO vuelve en el mismo movimiento
    -- Para simplificar, consideramos egreso no efectivo cuando sale de los analistas oficiales y no tiene GEDO
    SELECT 
        p.id_expediente,
        i.gerencia,
        i.trata_reporte,
        MIN(p.fecha)::date as fecha_egr,
        'NO_EFECTIVO' as tipo_egr
    FROM pases_filtrados p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    JOIN cfg_gestion_metas cfg ON i.gerencia = cfg.gerencia AND i.trata_reporte = cfg.trata_reporte
    WHERE p.fecha > i.fecha_ing 
      AND p.remitente = ANY(cfg.analistas_oficiales)
      AND p.destinatario != ANY(cfg.analistas_oficiales)
      AND p.destinatario != ANY(cfg.buzones_ingreso)
      AND p.estado NOT ILIKE 'Subsanaci%'
    GROUP BY 1, 2, 3
),
egresos_final AS (
    SELECT id_expediente, gerencia, trata_reporte, MIN(fecha_egr) as fecha_egr, tipo_egr
    FROM (
        SELECT * FROM egresos_gedo
        UNION ALL
        SELECT * FROM egresos_pases
    ) sub
    GROUP BY 1, 2, 3, 5
)
SELECT 
    i.id_expediente,
    i.gerencia,
    i.trata_reporte,
    i.fecha_ing,
    e.fecha_egr,
    e.tipo_egr,
    CASE 
        WHEN e.fecha_egr IS NULL THEN 'ACTIVO'
        ELSE 'CERRADO'
    END as status_gestion
FROM ingresos i
LEFT JOIN egresos_final e ON i.id_expediente = e.id_expediente AND i.gerencia = e.gerencia AND i.trata_reporte = e.trata_reporte;
