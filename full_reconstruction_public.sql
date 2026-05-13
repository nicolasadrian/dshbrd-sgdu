-- =========================================================
-- MEGA-SQL DE RECONSTRUCCIÓN FINAL (ESPEJO TOTAL)
-- =========================================================

-- Ajustes de rendimiento para la sesión
SET work_mem = '256MB';
SET maintenance_work_mem = '512MB';
SET temp_file_limit = -1;

BEGIN;

-- 1. SEGURIDAD
CREATE TABLE IF NOT EXISTS auth_users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'viewer',
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. TABLA DE CONFIGURACIÓN
DROP TABLE IF EXISTS cfg_gestion_metas CASCADE;
CREATE TABLE cfg_gestion_metas (
    id SERIAL PRIMARY KEY,
    gerencia TEXT NOT NULL,
    trata_reporte TEXT NOT NULL,
    tratas_incluidas TEXT[] NOT NULL,
    buzones_ingreso TEXT[] NOT NULL,
    analistas_oficiales TEXT[] NOT NULL,
    acronimos_egreso TEXT[] NOT NULL,
    metas_mensuales JSONB DEFAULT '{}'::jsonb,
    activo BOOLEAN DEFAULT TRUE,
    UNIQUE(gerencia, trata_reporte)
);

-- 3. VISTA DE LIFESTYLE (LÓGICA - ESPEJO)
DROP VIEW IF EXISTS v_expedientes_lifecycle CASCADE;
CREATE VIEW v_expedientes_lifecycle AS
WITH pases_base AS (
    SELECT 
        id_expediente, fecha, destinatario, usuario as remitente, estado,
        LEAD(fecha) OVER (PARTITION BY id_expediente ORDER BY fecha) as fecha_fin
    FROM mvw_ee_pases_secgdu
),
ingresos AS (
    SELECT 
        p.id_expediente, cfg.gerencia, cfg.trata_reporte,
        MIN(p.fecha)::date as fecha_ing
    FROM pases_base p
    JOIN mvw_expedientes_tratas_secgdu et ON p.id_expediente = et.id_expediente
    JOIN cfg_gestion_metas cfg ON (
        (cfg.trata_reporte != 'INTERVENCIONES' AND et.trata = ANY(cfg.tratas_incluidas))
        OR (cfg.trata_reporte = 'INTERVENCIONES' AND et.trata != ALL(cfg.tratas_incluidas))
    )
    WHERE p.destinatario = ANY(cfg.buzones_ingreso)
    GROUP BY 1, 2, 3
),
egresos_gedo AS (
    SELECT 
        g.id_expediente, i.gerencia, i.trata_reporte,
        MIN(g.fecha_creacion)::date as fecha_egr, 'EFECTIVO'::text as tipo_egr
    FROM mvw_datos_gedo_secgdu g
    JOIN ingresos i ON g.id_expediente = i.id_expediente
    JOIN cfg_gestion_metas cfg ON (cfg.gerencia = i.gerencia AND cfg.trata_reporte = i.trata_reporte)
    WHERE g.acronimo = ANY(cfg.acronimos_egreso) AND g.fecha_creacion >= i.fecha_ing
    GROUP BY 1, 2, 3
),
egresos_pases AS (
    SELECT 
        p.id_expediente, i.gerencia, i.trata_reporte,
        CASE WHEN i.trata_reporte = 'INTERVENCIONES' THEN MAX(p.fecha)::date ELSE MIN(p.fecha)::date END as fecha_egr,
        'NO_EFECTIVO'::text as tipo_egr
    FROM pases_base p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    JOIN cfg_gestion_metas cfg ON (cfg.gerencia = i.gerencia AND cfg.trata_reporte = i.trata_reporte)
    WHERE p.fecha > i.fecha_ing AND p.remitente = ANY(cfg.analistas_oficiales)
      AND p.destinatario != ANY(cfg.analistas_oficiales) AND p.destinatario != ANY(cfg.buzones_ingreso)
    GROUP BY 1, 2, 3
),
egresos_final AS (
    SELECT id_expediente, gerencia, trata_reporte, MIN(fecha_egr) as fecha_egr, tipo_egr
    FROM (SELECT * FROM egresos_gedo UNION ALL SELECT * FROM egresos_pases) sub
    GROUP BY 1, 2, 3, 5
)
SELECT 
    i.id_expediente, i.gerencia, i.trata_reporte, i.fecha_ing, e.fecha_egr, e.tipo_egr,
    CASE WHEN e.fecha_egr IS NULL THEN 'ACTIVO' ELSE 'CERRADO' END as status_gestion
FROM ingresos i
LEFT JOIN egresos_final e ON (i.id_expediente = e.id_expediente AND i.gerencia = e.gerencia AND i.trata_reporte = e.trata_reporte);

-- 4. POBLAR CONFIGURACIÓN (TODAS LAS GERENCIAS)
INSERT INTO cfg_gestion_metas (gerencia, trata_reporte, tratas_incluidas, buzones_ingreso, analistas_oficiales, acronimos_egreso)
VALUES 
('catastro', 'MDUG0115C', ARRAY['MDUG0115C'], ARRAY['DGROC-CIC', 'DGROC-COPIAPLANO', 'DGROC-DCATDES', 'DGROC-DCATMEN', 'DGROC-DCATPOL', 'DGROC-DCATTIT'], ARRAY['ACOSTAPA', 'AFAHLER', 'AGUSMAZZONI', 'ALEALFONSIN', 'ALEGREM', 'ARGENTOES', 'BARTROLIG', 'CABRERAM', 'CANALEAL', 'CARBONELLIM', 'CHIANETTAR', 'CIOPKOG', 'CISTERNACA', 'COHENCAD', 'CONTIL', 'CONVERTID', 'DELGADODE', 'DIBIASEO', 'DIEZGASTON', 'DIHARCEP', 'DURSIM', 'ECIJAN', 'FMARCHISELLA', 'FOLLONIERLE', 'FREIXASC', 'GARCIASIL', 'GILESJP', 'GONZALEZAMA', 'GONZALEZHORAC', 'GUZMANO', 'IGARZABALP', 'JTIRADO', 'LAGUNAMA', 'LBELLY', 'LOISIG', 'LUCCIC', 'M.NAPOLI', 'MALATTOR', 'MANNOP', 'MARCHETTIJ', 'MHOSBALIKCIYAN', 'MOSCOVICHA', 'NCITRANGOLO', 'NOGUERAH', 'NPONZO', 'NQUINTERNO', 'PONZOS', 'ROLDANG', 'SALGUEROM', 'SORIAANDREA', 'TARRUA', 'TAVELLAE', 'VEGAJ', 'VILLAGI', 'WVIRGILIO'], ARRAY['IFMMH']),
('catastro', 'INTERVENCIONES', ARRAY['MDUG0115C'], ARRAY['DGROC-CIC', 'DGROC-DCATDES'], ARRAY['ACOSTAPA', 'AFAHLER'], ARRAY['IF']),
('instalaciones', 'MDUG2101A', ARRAY['MDUG2101A'], ARRAY['DGROC-ELECTRICAS', 'DGROC-ELEVADORES'], ARRAY['AQUINOLUCAS', 'ARENAJ'], ARRAY['PROIN', 'PLINE']),
('regularizacion', 'MDUG0104A', ARRAY['MDUG0104A'], ARRAY['DGROC-OBRASDEMO'], ARRAY['AGUEROJO', 'AKRACOFF'], ARRAY['IFROC']),
('contable', 'MDUG0901A', ARRAY['MDUG0901A'], ARRAY['DGROC-CONTABLE'], ARRAY['AMONTEVERDE', 'AMORINC'], ARRAY['IF']),
('aph', 'MDUG3701A', ARRAY['MDUG3701A'], ARRAY['DGIUR-21', 'DGIUR-ADMISIBILIDADAPH'], ARRAY['CHANTIRRO', 'CHEZOM'], ARRAY['DI', 'ANEXO', 'IF']),
('usos', 'MDUG0136B', ARRAY['MDUG0136B'], ARRAY['DGIUR-12', 'DGIUR-ADMISIBILIDADUSOS'], ARRAY['ALEPABLOCASTRO', 'ARVASR'], ARRAY['DI', 'ANEXO', 'IF']),
('morfologia', 'MDUG1801A', ARRAY['MDUG1801A'], ARRAY['DGIUR-03', 'DGIUR-ADMISIBILIDADMORFO'], ARRAY['A.GUZMAN', 'AGARTEAGA'], ARRAY['DI', 'ANEXO', 'IF']),
('aviso_obra', 'MDUG0102B', ARRAY['MDUG0102B'], ARRAY['DGROC-AUTOMAT'], ARRAY['DGROC-AUTOMAT'], ARRAY['IFCAO', 'IFCFP', 'IFCAC']);

-- 5. REPORTES HISTÓRICOS (TODAS LAS GERENCIAS)

-- CATASTRO
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_catastro CASCADE;
CREATE MATERIALIZED VIEW mvw_reporte_historico_catastro AS
WITH periodos AS (
    SELECT EXTRACT(YEAR FROM s.d)::int as anio, EXTRACT(MONTH FROM s.d)::int as mes,
           (s.d + interval '1 month' - interval '1 day')::date as fin_mes,
           date_trunc('month', s.d)::date as inicio_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
)
SELECT cfg.gerencia, cfg.trata_reporte as "COD TRATA", p.anio, p.mes,
       COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= p.inicio_mes AND l.fecha_ing <= p.fin_mes) as "ING"
FROM cfg_gestion_metas cfg
CROSS JOIN periodos p
LEFT JOIN v_expedientes_lifecycle l ON cfg.trata_reporte = l.trata_reporte AND l.gerencia = 'catastro'
WHERE cfg.gerencia = 'catastro'
GROUP BY 1, 2, 3, 4;

-- INSTALACIONES
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_instalaciones CASCADE;
CREATE MATERIALIZED VIEW mvw_reporte_historico_instalaciones AS
WITH periodos AS (
    SELECT EXTRACT(YEAR FROM s.d)::int as anio, EXTRACT(MONTH FROM s.d)::int as mes,
           (s.d + interval '1 month' - interval '1 day')::date as fin_mes,
           date_trunc('month', s.d)::date as inicio_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
)
SELECT cfg.gerencia, cfg.trata_reporte as "COD TRATA", p.anio, p.mes,
       COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= p.inicio_mes AND l.fecha_ing <= p.fin_mes) as "ING"
FROM cfg_gestion_metas cfg
CROSS JOIN periodos p
LEFT JOIN v_expedientes_lifecycle l ON cfg.trata_reporte = l.trata_reporte AND l.gerencia = 'instalaciones'
WHERE cfg.gerencia = 'instalaciones'
GROUP BY 1, 2, 3, 4;

-- APH
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_aph CASCADE;
CREATE MATERIALIZED VIEW mvw_reporte_historico_aph AS
WITH periodos AS (
    SELECT EXTRACT(YEAR FROM s.d)::int as anio, EXTRACT(MONTH FROM s.d)::int as mes,
           (s.d + interval '1 month' - interval '1 day')::date as fin_mes,
           date_trunc('month', s.d)::date as inicio_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
)
SELECT cfg.gerencia, cfg.trata_reporte as "COD TRATA", p.anio, p.mes,
       COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= p.inicio_mes AND l.fecha_ing <= p.fin_mes) as "ING"
FROM cfg_gestion_metas cfg
CROSS JOIN periodos p
LEFT JOIN v_expedientes_lifecycle l ON cfg.trata_reporte = l.trata_reporte AND l.gerencia = 'aph'
WHERE cfg.gerencia = 'aph'
GROUP BY 1, 2, 3, 4;

-- CONTABLE
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_contable CASCADE;
CREATE MATERIALIZED VIEW mvw_reporte_historico_contable AS
WITH periodos AS (
    SELECT EXTRACT(YEAR FROM s.d)::int as anio, EXTRACT(MONTH FROM s.d)::int as mes,
           (s.d + interval '1 month' - interval '1 day')::date as fin_mes,
           date_trunc('month', s.d)::date as inicio_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
)
SELECT cfg.gerencia, cfg.trata_reporte as "COD TRATA", p.anio, p.mes,
       COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= p.inicio_mes AND l.fecha_ing <= p.fin_mes) as "ING"
FROM cfg_gestion_metas cfg
CROSS JOIN periodos p
LEFT JOIN v_expedientes_lifecycle l ON cfg.trata_reporte = l.trata_reporte AND l.gerencia = 'contable'
WHERE cfg.gerencia = 'contable'
GROUP BY 1, 2, 3, 4;

-- REGULARIZACION
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_regularizacion CASCADE;
CREATE MATERIALIZED VIEW mvw_reporte_historico_regularizacion AS
WITH periodos AS (
    SELECT EXTRACT(YEAR FROM s.d)::int as anio, EXTRACT(MONTH FROM s.d)::int as mes,
           (s.d + interval '1 month' - interval '1 day')::date as fin_mes,
           date_trunc('month', s.d)::date as inicio_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
)
SELECT cfg.gerencia, cfg.trata_reporte as "COD TRATA", p.anio, p.mes,
       COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= p.inicio_mes AND l.fecha_ing <= p.fin_mes) as "ING"
FROM cfg_gestion_metas cfg
CROSS JOIN periodos p
LEFT JOIN v_expedientes_lifecycle l ON cfg.trata_reporte = l.trata_reporte AND l.gerencia = 'regularizacion'
WHERE cfg.gerencia = 'regularizacion'
GROUP BY 1, 2, 3, 4;

-- MORFOLOGIA
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_morfologia CASCADE;
CREATE MATERIALIZED VIEW mvw_reporte_historico_morfologia AS
WITH periodos AS (
    SELECT EXTRACT(YEAR FROM s.d)::int as anio, EXTRACT(MONTH FROM s.d)::int as mes,
           (s.d + interval '1 month' - interval '1 day')::date as fin_mes,
           date_trunc('month', s.d)::date as inicio_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
)
SELECT cfg.gerencia, cfg.trata_reporte as "COD TRATA", p.anio, p.mes,
       COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= p.inicio_mes AND l.fecha_ing <= p.fin_mes) as "ING"
FROM cfg_gestion_metas cfg
CROSS JOIN periodos p
LEFT JOIN v_expedientes_lifecycle l ON cfg.trata_reporte = l.trata_reporte AND l.gerencia = 'morfologia'
WHERE cfg.gerencia = 'morfologia'
GROUP BY 1, 2, 3, 4;

-- USOS
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_usos CASCADE;
CREATE MATERIALIZED VIEW mvw_reporte_historico_usos AS
WITH periodos AS (
    SELECT EXTRACT(YEAR FROM s.d)::int as anio, EXTRACT(MONTH FROM s.d)::int as mes,
           (s.d + interval '1 month' - interval '1 day')::date as fin_mes,
           date_trunc('month', s.d)::date as inicio_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
)
SELECT cfg.gerencia, cfg.trata_reporte as "COD TRATA", p.anio, p.mes,
       COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= p.inicio_mes AND l.fecha_ing <= p.fin_mes) as "ING"
FROM cfg_gestion_metas cfg
CROSS JOIN periodos p
LEFT JOIN v_expedientes_lifecycle l ON cfg.trata_reporte = l.trata_reporte AND l.gerencia = 'usos'
WHERE cfg.gerencia = 'usos'
GROUP BY 1, 2, 3, 4;

-- AVISO DE OBRA
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_aviso_obra CASCADE;
CREATE MATERIALIZED VIEW mvw_reporte_historico_aviso_obra AS
WITH periodos AS (
    SELECT EXTRACT(YEAR FROM s.d)::int as anio, EXTRACT(MONTH FROM s.d)::int as mes,
           (s.d + interval '1 month' - interval '1 day')::date as fin_mes,
           date_trunc('month', s.d)::date as inicio_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
)
SELECT cfg.gerencia, cfg.trata_reporte as "COD TRATA", p.anio, p.mes,
       COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= p.inicio_mes AND l.fecha_ing <= p.fin_mes) as "ING"
FROM cfg_gestion_metas cfg
CROSS JOIN periodos p
LEFT JOIN v_expedientes_lifecycle l ON cfg.trata_reporte = l.trata_reporte AND l.gerencia = 'aviso_obra'
WHERE cfg.gerencia = 'aviso_obra'
GROUP BY 1, 2, 3, 4;

-- ETAPA PROYECTO
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_etapa_proyecto CASCADE;
CREATE MATERIALIZED VIEW mvw_reporte_historico_etapa_proyecto AS
WITH periodos AS (
    SELECT EXTRACT(YEAR FROM s.d)::int as anio, EXTRACT(MONTH FROM s.d)::int as mes,
           (s.d + interval '1 month' - interval '1 day')::date as fin_mes,
           date_trunc('month', s.d)::date as inicio_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
)
SELECT cfg.gerencia, cfg.trata_reporte as "COD TRATA", p.anio, p.mes,
       COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= p.inicio_mes AND l.fecha_ing <= p.fin_mes) as "ING"
FROM cfg_gestion_metas cfg
CROSS JOIN periodos p
LEFT JOIN v_expedientes_lifecycle l ON cfg.trata_reporte = l.trata_reporte AND l.gerencia = 'etapa_proyecto'
WHERE cfg.gerencia = 'etapa_proyecto'
GROUP BY 1, 2, 3, 4;

COMMIT;
