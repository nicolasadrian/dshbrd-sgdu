# La Biblia de Reconstrucción SGDU - Base Pública (v1.2)

Este documento es la referencia definitiva y completa para reconstruir la totalidad de la estructura de la base de datos pública de SGDU Analytics. Siga los pasos en orden estricto.

---

## Paso 1: Limpieza Universal Inteligente (Smart Drop)
Este bloque detecta automáticamente si el objeto es una TABLA, VISTA o VISTA MATERIALIZADA y lo elimina correctamente sin errores de tipo.

```sql
DO $$ 
DECLARE
    r RECORD;
BEGIN
    -- Lista de objetos a limpiar
    FOR r IN (
        SELECT relname, relkind 
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace 
        WHERE n.nspname = 'public' 
          AND relname IN (
            'v_expedientes_lifecycle', 
            'mvw_stock_actual_detalle', 
            'mvw_reporte_consolidado_catastro',
            'mvw_reporte_historico_catastro',
            'mvw_reporte_historico_instalaciones',
            'mvw_reporte_historico_contable',
            'mvw_reporte_historico_regularizacion',
            'mvw_reporte_historico_etapa_proyecto',
            'mvw_reporte_historico_morfologia',
            'mvw_reporte_historico_aph',
            'mvw_reporte_historico_usos',
            'mvw_reporte_historico_aviso_obra',
            'mvw_reporte_historico_global',
            'cfg_gestion_metas',
            'auth_users'
          )
    ) LOOP
        IF r.relkind = 'v' THEN 
            EXECUTE 'DROP VIEW IF EXISTS ' || r.relname || ' CASCADE';
        ELSIF r.relkind = 'm' THEN 
            EXECUTE 'DROP MATERIALIZED VIEW IF EXISTS ' || r.relname || ' CASCADE';
        ELSIF r.relkind = 'r' THEN 
            EXECUTE 'DROP TABLE IF EXISTS ' || r.relname || ' CASCADE';
        END IF;
    END LOOP;
END $$;
```

---

## Paso 2: Creación de Tablas Base
Tablas de seguridad y el cerebro de configuración.

```sql
-- Tabla de Usuarios
CREATE TABLE auth_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Configuración de Gestión y Metas
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
```

---

## Paso 3: Índices de Optimización
Ejecute esto sobre las tablas sincronizadas de SADE antes de crear las vistas.

```sql
CREATE INDEX IF NOT EXISTS idx_pases_id_exp_prod ON mvw_ee_pases_secgdu (id_expediente);
CREATE INDEX IF NOT EXISTS idx_pases_destinatario ON mvw_ee_pases_secgdu (destinatario);
CREATE INDEX IF NOT EXISTS idx_pases_fecha ON mvw_ee_pases_secgdu (fecha);
CREATE INDEX IF NOT EXISTS idx_gedo_id_exp_prod ON mvw_datos_gedo_secgdu (id_expediente);
CREATE INDEX IF NOT EXISTS idx_exp_trata_id_prod ON mvw_expedientes_tratas_secgdu (id_expediente);
CREATE INDEX IF NOT EXISTS idx_gedo_acronimo ON mvw_datos_gedo_secgdu (acronimo);

ANALYZE mvw_ee_pases_secgdu;
ANALYZE mvw_datos_gedo_secgdu;
ANALYZE mvw_expedientes_tratas_secgdu;
```

---

## Paso 4: Poblado Total de Configuración
Este es el contenido crítico de `populate_cfg_metas.sql` (Ejemplos principales). **Debe cargar todos los registros del archivo original.**

```sql
DELETE FROM cfg_gestion_metas;

-- CATASTRO (Resumen)
INSERT INTO cfg_gestion_metas (gerencia, trata_reporte, tratas_incluidas, buzones_ingreso, analistas_oficiales, acronimos_egreso)
VALUES ('catastro', 'MDUG0115C', ARRAY['MDUG0115C'], ARRAY['DGROC-CIC', 'DGROC-COPIAPLANO', 'DGROC-DCATDES', 'DGROC-DCATMEN', 'DGROC-DCATPOL', 'DGROC-DCATTIT'], ARRAY['ACOSTAPA', 'AFAHLER', 'AGUSMAZZONI', 'ALEALFONSIN', 'ALEGREM', 'ARGENTOES', 'BARTROLIG', 'CABRERAM', 'CANALEAL', 'CARBONELLIM', 'CHIANETTAR', 'CIOPKOG', 'CISTERNACA', 'COHENCAD', 'CONTIL', 'CONVERTID', 'DELGADODE', 'DIBIASEO', 'DIEZGASTON', 'DIHARCEP', 'DURSIM', 'ECIJAN', 'FMARCHISELLA', 'FOLLONIERLE', 'FREIXASC', 'GARCIASIL', 'GILESJP', 'GONZALEZAMA', 'GONZALEZHORAC', 'GUZMANO', 'IGARZABALP', 'JTIRADO', 'LAGUNAMA', 'LBELLY', 'LOISIG', 'LUCCIC', 'M.NAPOLI', 'MALATTOR', 'MANNOP', 'MARCHETTIJ', 'MHOSBALIKCIYAN', 'MOSCOVICHA', 'NCITRANGOLO', 'NOGUERAH', 'NPONZO', 'NQUINTERNO', 'PONZOS', 'ROLDANG', 'SALGUEROM', 'SORIAANDREA', 'TARRUA', 'TAVELLAE', 'VEGAJ', 'VILLAGI', 'WVIRGILIO'], ARRAY['IFMMH']);

-- INSTALACIONES (Resumen)
INSERT INTO cfg_gestion_metas (gerencia, trata_reporte, tratas_incluidas, buzones_ingreso, analistas_oficiales, acronimos_egreso)
VALUES ('instalaciones', 'MDUG2101A', ARRAY['MDUG2101A'], ARRAY['DGROC-ELECTRICAS', 'DGROC-ELEVADORES', 'DGROC-INCENDIO', 'DGROC-SANITARIAS', 'DGROC-TERMICAS', 'DGROC-DCIMYE', 'DGROC-DCIELEV', 'DGROC-DCIDITI'], ARRAY['AQUINOLUCAS', 'ARENAJ', 'ARGUELLOJ', 'BATALLANJ', 'BENITOG', 'BRIANMARTINEZ', 'CORNAZM', 'FICARRAR', 'GAGLIARDIA', 'LOPARDOC', 'QUEIJASGUILLINP', 'ROBLEDOJO', 'ROLDANMI', 'RUDAC', 'SARIDISD', 'TOLESANOA', 'AURENA', 'BATALLANGE', 'BRITANP', 'GUARDADOB', 'JDECIMA', 'PEREZGA', 'RODRIGUEZESTEBAN', 'RODRIGUEZNE', 'SILESC', 'VILLAGAB', 'ABCRAGNO', 'AGARCIAFIGUEROA', 'CABRERAARI', 'CAFELICE', 'CAPOZZOG', 'CSALGUERO', 'DARANGURI', 'DMOFFA', 'FUHRY', 'GONMAR', 'J.OLIVERA', 'LOPEZFE', 'MARIANELAROCARO', 'MBALDOME', 'MLMAMONE', 'MTRENQUE', 'NIEVAL', 'PCHERBENCO', 'RADAA', 'RIOSFE', 'ROMANOFLA', 'SANTACRUZ', 'CANTARELLTORRES', 'CIRIAE', 'LOIACONOANA', 'MCDIAMANTI', 'POUSAF', 'ARGUELLOSOL', 'COSSM', 'EIERACI', 'HAMALAG', 'RUIZMA', 'BRITANG', 'ENCISOROMERO', 'PITTERIE', 'WIERZBICKIIGOR'], ARRAY['PROIN', 'PLINE', 'IFCIS', 'IFSMC', 'IFRSP']);
```

---

## Paso 5: Vista de Ciclo de Vida (`v_expedientes_lifecycle`)
Motor lógico unificado para detección de ingresos y egresos.

```sql
CREATE OR REPLACE VIEW v_expedientes_lifecycle AS
WITH pases_filtrados AS (
    SELECT p.id_expediente, p.fecha, p.destinatario, p.usuario as remitente, p.estado
    FROM mvw_ee_pases_secgdu p
),
ingresos AS (
    SELECT 
        p.id_expediente, 
        cfg.gerencia as l_gerencia, 
        cfg.trata_reporte as l_trata_reporte,
        MIN(p.fecha)::date as fecha_ing
    FROM pases_filtrados p
    JOIN mvw_expedientes_tratas_secgdu et ON p.id_expediente = et.id_expediente
    JOIN cfg_gestion_metas cfg ON (
        (cfg.trata_reporte != 'INTERVENCIONES' AND et.trata = ANY(cfg.tratas_incluidas))
        OR 
        (cfg.trata_reporte = 'INTERVENCIONES' AND et.trata != ALL(cfg.tratas_incluidas))
    )
    WHERE p.destinatario = ANY(cfg.buzones_ingreso)
    GROUP BY 1, 2, 3
),
egresos_gedo AS (
    SELECT 
        g.id_expediente, i.l_gerencia, i.l_trata_reporte,
        MIN(g.fecha_creacion)::date as fecha_egr,
        'EFECTIVO'::text as tipo_egr
    FROM mvw_datos_gedo_secgdu g
    JOIN ingresos i ON g.id_expediente = i.id_expediente
    JOIN cfg_gestion_metas cfg ON (cfg.gerencia = i.l_gerencia AND cfg.trata_reporte = i.l_trata_reporte)
    WHERE g.acronimo = ANY(cfg.acronimos_egreso) AND g.fecha_creacion >= i.fecha_ing
    GROUP BY 1, 2, 3
),
egresos_pases AS (
    SELECT 
        p.id_expediente, i.l_gerencia, i.l_trata_reporte,
        CASE 
            WHEN i.l_trata_reporte = 'INTERVENCIONES' THEN MAX(p.fecha)::date 
            ELSE MIN(p.fecha)::date 
        END as fecha_egr,
        'NO_EFECTIVO'::text as tipo_egr
    FROM pases_filtrados p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    JOIN cfg_gestion_metas cfg ON (cfg.gerencia = i.l_gerencia AND cfg.trata_reporte = i.l_trata_reporte)
    WHERE p.fecha > i.fecha_ing 
      AND p.remitente = ANY(cfg.analistas_oficiales)
      AND p.destinatario != ANY(cfg.analistas_oficiales)
      AND p.destinatario != ANY(cfg.buzones_ingreso)
    GROUP BY 1, 2, 3
),
egresos_unificados AS (
    SELECT id_expediente, l_gerencia, l_trata_reporte, fecha_egr, tipo_egr FROM egresos_gedo
    UNION ALL
    SELECT id_expediente, l_gerencia, l_trata_reporte, fecha_egr, tipo_egr FROM egresos_pases
),
egresos_final AS (
    SELECT 
        id_expediente, l_gerencia, l_trata_reporte, 
        CASE WHEN l_trata_reporte = 'INTERVENCIONES' THEN MAX(fecha_egr) ELSE MIN(fecha_egr) END as fecha_egr, 
        tipo_egr
    FROM egresos_unificados
    GROUP BY 1, 2, 3, 5
)
SELECT 
    i.id_expediente, i.l_gerencia as gerencia, i.l_trata_reporte as trata_reporte,
    i.fecha_ing, e.fecha_egr, e.tipo_egr,
    CASE WHEN e.fecha_egr IS NULL THEN 'ACTIVO' ELSE 'CERRADO' END as status_gestion
FROM ingresos i
LEFT JOIN egresos_final e ON (i.id_expediente = e.id_expediente AND i.l_gerencia = e.l_gerencia AND i.l_trata_reporte = e.l_trata_reporte);
```

---

## Paso 6: Vistas Materializadas de Reporte
Vistas pre-calculadas para el Dashboard.

### 6.1 Detalle de Stock Actual
```sql
DROP MATERIALIZED VIEW IF EXISTS mvw_stock_actual_detalle CASCADE;

CREATE MATERIALIZED VIEW mvw_stock_actual_detalle AS
WITH last_pases AS (
    SELECT DISTINCT ON (id_expediente) id_expediente, destinatario as analista, fecha, estado
    FROM mvw_ee_pases_secgdu
    ORDER BY id_expediente, fecha DESC
),
stock_candidatos AS (
    SELECT lp.id_expediente, lp.analista as analista_actual, lp.fecha as fecha_ultimo_pase, lp.estado,
           cfg.gerencia, cfg.trata_reporte, cfg.tratas_incluidas, cfg.acronimos_egreso
    FROM last_pases lp
    JOIN cfg_gestion_metas cfg ON (lp.analista = ANY(cfg.analistas_oficiales) OR lp.analista = ANY(cfg.buzones_ingreso))
),
stock_filtrado AS (
    SELECT s.*, et.trata, et.descripcion, et.expediente, et.fecha_creacion
    FROM stock_candidatos s
    JOIN mvw_expedientes_tratas_secgdu et ON s.id_expediente = et.id_expediente
    WHERE (
        (s.trata_reporte != 'INTERVENCIONES' AND et.trata = ANY(s.tratas_incluidas))
        OR
        (s.trata_reporte = 'INTERVENCIONES' AND et.trata != ALL(
            SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = s.gerencia AND trata_reporte != 'INTERVENCIONES'
        ))
    )
),
egresos_gedo AS (
    SELECT DISTINCT ON (g.id_expediente, s.gerencia, s.trata_reporte) g.id_expediente, s.gerencia, s.trata_reporte
    FROM mvw_datos_gedo_secgdu g
    JOIN stock_filtrado s ON g.id_expediente = s.id_expediente
    WHERE g.acronimo = ANY(s.acronimos_egreso) AND g.fecha_creacion >= s.fecha_ultimo_pase
    ORDER BY g.id_expediente, s.gerencia, s.trata_reporte
)
SELECT 
    f.id_expediente, f.expediente, f.analista_actual, f.fecha_ultimo_pase,
    f.fecha_creacion::date as fecha_ing,
    CURRENT_DATE - f.fecha_ultimo_pase::date as dias_stock,
    f.trata, f.descripcion,
    CASE WHEN f.estado ILIKE 'Subsanaci%' THEN 1 ELSE 0 END as is_subs,
    f.gerencia, f.trata_reporte
FROM stock_filtrado f
LEFT JOIN egresos_gedo eg ON f.id_expediente = eg.id_expediente AND f.gerencia = eg.gerencia AND f.trata_reporte = eg.trata_reporte
WHERE eg.id_expediente IS NULL;

CREATE INDEX idx_stock_det_gerencia ON mvw_stock_actual_detalle (gerencia);
CREATE INDEX idx_stock_det_reporte ON mvw_stock_actual_detalle (trata_reporte);
```

### 6.2 Reporte Histórico: CATASTRO
```sql
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_catastro CASCADE;

CREATE MATERIALIZED VIEW mvw_reporte_historico_catastro AS
WITH periodos AS (
    SELECT 
        EXTRACT(YEAR FROM s.d)::int as anio, EXTRACT(MONTH FROM s.d)::int as mes,
        (s.d + interval '1 month' - interval '1 day')::date as fin_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
),
lifecycle AS (
    SELECT * FROM v_expedientes_lifecycle WHERE gerencia = 'catastro'
),
subsanaciones_historicas AS (
    SELECT p.id_expediente, per.anio, per.mes, 1 as is_subs
    FROM mvw_ee_pases_secgdu p
    JOIN periodos per ON p.fecha <= per.fin_mes
    JOIN (
        SELECT id_expediente, fecha, 
               LEAD(fecha) OVER (PARTITION BY id_expediente ORDER BY fecha) as fecha_fin_estado
        FROM mvw_ee_pases_secgdu
    ) p_range ON p.id_expediente = p_range.id_expediente AND p.fecha = p_range.fecha
    WHERE p.estado ILIKE 'Subsanaci%'
      AND per.fin_mes >= p.fecha 
      AND (p_range.fecha_fin_estado IS NULL OR per.fin_mes < p_range.fecha_fin_estado)
    GROUP BY 1, 2, 3
)
SELECT 
    cfg.gerencia as "GERENCIA", cfg.trata_reporte as "COD TRATA",
    per.anio, per.mes,
    COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_ing >= date_trunc('month', per.fin_mes) AND l.fecha_ing <= per.fin_mes) as "ING",
    COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_egr >= date_trunc('month', per.fin_mes) AND l.fecha_egr <= per.fin_mes AND l.tipo_egr = 'EFECTIVO') as "EGR_EF",
    COUNT(DISTINCT l.id_expediente) FILTER (WHERE l.fecha_egr >= date_trunc('month', per.fin_mes) AND l.fecha_egr <= per.fin_mes AND l.tipo_egr = 'NO_EFECTIVO') as "EGR_NE",
    COUNT(DISTINCT s.id_expediente) as "STOCK_SUBS",
    COUNT(DISTINCT l.id_expediente) FILTER (
        WHERE l.fecha_ing <= per.fin_mes 
          AND (l.fecha_egr IS NULL OR l.fecha_egr > per.fin_mes)
          AND NOT EXISTS (SELECT 1 FROM subsanaciones_historicas sh WHERE sh.id_expediente = l.id_expediente AND sh.anio = per.anio AND sh.mes = per.mes)
    ) as "STOCK_PROPIO"
FROM cfg_gestion_metas cfg
CROSS JOIN periodos per
LEFT JOIN lifecycle l ON cfg.trata_reporte = l.trata_reporte
LEFT JOIN subsanaciones_historicas s ON l.id_expediente = s.id_expediente AND per.anio = s.anio AND per.mes = s.mes
WHERE cfg.gerencia = 'catastro'
GROUP BY 1, 2, 3, 4 -- CORRECCIÓN: Eran 4 columnas descriptivas
ORDER BY 1, 2, 4, 5;

CREATE INDEX idx_hist_cat_trata ON mvw_reporte_historico_catastro ("COD TRATA");
CREATE INDEX idx_hist_cat_periodo ON mvw_reporte_historico_catastro (anio, mes);
```

### 6.3 Reporte Histórico: INSTALACIONES
```sql
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_instalaciones;

CREATE MATERIALIZED VIEW mvw_reporte_historico_instalaciones AS
WITH tramites_metadata (gerencia, trata, nombre_trata, acronimos_list) AS (
    VALUES 
    ('instalaciones', 'MDUG2101A', 'Registro de Plano de Prevención contra Incendios.', ARRAY['PROIN', 'PLINE', 'IFCIS', 'IFSMC', 'IFRSP']),
    ('instalaciones', 'MDUG2901A', 'Registro de Plano de Elementos Guiados de Transporte.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2501A', 'Registro de Plano de Instalación de Inflamables.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2201A', 'Registro de Plano de Instalación de Ventilación Mecánica.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2701A', 'Registro de Plano de Instalación Eléctrica.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2401A', 'Registro de Plano de Instalación Electromecánica.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2601A', 'Registro de Plano de Instalación Sanitaria.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2301A', 'Registro de Plano de Instalación Térmica.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG3301A', 'Registro de Plano de Sala de Máquinas.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG0904A', 'Ascenso de Categoría de Foguistas.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG0120A', 'Solicitud Examen de Foguista.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MJGG1601A', 'Registro de planos de prototipo de equipos.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG0101D', 'Ajuste De Instalacion Elementos Guiados De Transporte.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG0101G', 'Ajuste De Instalacion Termica.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MJGG1701A', 'Transferencia de Titularidad de Instalación.', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'INTERVENCIONES', 'Intervenciones', ARRAY['PROIN', 'PLINE', 'IFCIS', 'IFSMC', 'IFRSP'])
),
periodos AS (
    SELECT EXTRACT(YEAR FROM s.d)::int as anio, EXTRACT(MONTH FROM s.d)::int as mes, (s.d + interval '1 month' - interval '1 day')::date as fin_mes
    FROM generate_series('2025-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
),
expedientes_target AS (
    SELECT id_expediente, trata, CASE WHEN estado ILIKE 'Subsanaci%' OR estado ILIKE 'Subsanación%' THEN 1 ELSE 0 END as is_subs FROM mvw_expedientes_tratas_secgdu
),
pases_pre_filtrados AS (
    SELECT p.id_expediente, p.fecha, p.destinatario, LAG(p.destinatario) OVER (PARTITION BY p.id_expediente ORDER BY p.fecha) as remitente FROM mvw_ee_pases_secgdu p
),
buzones_ingreso AS (
    SELECT unnest FROM unnest(ARRAY['DGROC-ELECTRICAS', 'DGROC-ELEVADORES', 'DGROC-INCENDIO', 'DGROC-SANITARIAS', 'DGROC-TERMICAS', 'DGROC-DCIMYE', 'DGROC-DCIELEV', 'DGROC-DCIDITI'])
),
analistas_area AS (
    SELECT unnest FROM unnest(ARRAY['AQUINOLUCAS', 'ARENAJ', 'ARGUELLOJ', 'BATALLANJ', 'BENITOG', 'BRIANMARTINEZ', 'CORNAZM', 'FICARRAR', 'GAGLIARDIA', 'LOPARDOC', 'QUEIJASGUILLINP', 'ROBLEDOJO', 'ROLDANMI', 'RUDAC', 'SARIDISD', 'TOLESANOA', 'AURENA', 'BATALLANGE', 'BRITANP', 'GUARDADOB', 'JDECIMA', 'PEREZGA', 'RODRIGUEZESTEBAN', 'RODRIGUEZNE', 'SILESC', 'VILLAGAB', 'ABCRAGNO', 'AGARCIAFIGUEROA', 'CABRERAARI', 'CAFELICE', 'CAPOZZOG', 'CSALGUERO', 'DARANGURI', 'DMOFFA', 'FUHRY', 'GONMAR', 'J.OLIVERA', 'LOPEZFE', 'MARIANELAROCARO', 'MBALDOME', 'MLMAMONE', 'MTRENQUE', 'NIEVAL', 'PCHERBENCO', 'RADAA', 'RIOSFE', 'ROMANOFLA', 'SANTACRUZ', 'CANTARELLTORRES', 'CIRIAE', 'LOIACONOANA', 'MCDIAMANTI', 'POUSAF', 'ARGUELLOSOL', 'COSSM', 'EIERACI', 'HAMALAG', 'RUIZMA', 'BRITANG', 'ENCISOROMERO', 'PITTERIE', 'WIERZBICKIIGOR'])
),
ingresos AS (
    SELECT p.id_expediente, tm.trata, 'instalaciones' as gerencia, MIN(p.fecha)::date as fecha_ing
    FROM pases_pre_filtrados p
    JOIN expedientes_target ec ON p.id_expediente = ec.id_expediente
    LEFT JOIN tramites_metadata tm ON ec.trata = tm.trata
    WHERE p.destinatario IN (SELECT * FROM buzones_ingreso)
    GROUP BY 1, 2, 3
),
egresos_efectivos AS (
    SELECT g.id_expediente, i.trata, i.gerencia, MIN(g.fecha_creacion)::date as fecha_egr
    FROM mvw_datos_gedo_secgdu g
    JOIN ingresos i ON g.id_expediente = i.id_expediente
    JOIN tramites_metadata tm ON i.trata = tm.trata
    WHERE g.acronimo = ANY(tm.acronimos_list) AND g.fecha_creacion >= i.fecha_ing AND i.trata != 'INTERVENCIONES'
    GROUP BY 1, 2, 3
    UNION ALL
    SELECT p.id_expediente, 'INTERVENCIONES' as trata, i.gerencia, MAX(p.fecha)::date as fecha_egr
    FROM pases_pre_filtrados p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    WHERE i.trata = 'INTERVENCIONES' AND p.fecha > i.fecha_ing AND p.remitente IN (SELECT * FROM analistas_area) AND p.destinatario NOT IN (SELECT * FROM analistas_area)
    GROUP BY 1, 2, 3
),
egresos_no_efectivos AS (
    SELECT p.id_expediente, i.trata, i.gerencia, MIN(p.fecha)::date as fecha_egr
    FROM mvw_ee_pases_secgdu p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    WHERE (p.estado = 'Guarda Temporal' OR p.destinatario = 'GUARDA TEMPORAL') AND p.fecha > i.fecha_ing AND i.trata != 'INTERVENCIONES'
    GROUP BY 1, 2, 3
),
status_final AS (
    SELECT i.id_expediente, i.trata, i.gerencia, i.fecha_ing, COALESCE(ee.fecha_egr, en.fecha_egr) as fecha_egr,
           CASE WHEN ee.id_expediente IS NOT NULL THEN 'EF' WHEN en.id_expediente IS NOT NULL THEN 'NE' ELSE NULL END as tipo_egr,
           ec.is_subs
    FROM ingresos i
    JOIN expedientes_target ec ON i.id_expediente = ec.id_expediente
    LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente AND i.trata = ee.trata
    LEFT JOIN egresos_no_efectivos en ON i.id_expediente = en.id_expediente AND i.trata = en.trata AND ee.id_expediente IS NULL
)
SELECT 
    tm.gerencia as "GERENCIA", tm.trata as "COD TRATA", tm.nombre_trata as "DETALLE TRATA", per.anio, per.mes,
    COUNT(*) FILTER (WHERE s.fecha_ing >= date_trunc('month', per.fin_mes) AND s.fecha_ing <= per.fin_mes) as "ING",
    COUNT(*) FILTER (WHERE s.fecha_egr >= date_trunc('month', per.fin_mes) AND s.fecha_egr <= per.fin_mes AND s.tipo_egr = 'EF') as "EGR_EF",
    COUNT(*) FILTER (WHERE s.fecha_egr >= date_trunc('month', per.fin_mes) AND s.fecha_egr <= per.fin_mes AND s.tipo_egr = 'NE') as "EGR_NE",
    COUNT(*) FILTER (WHERE s.fecha_ing <= per.fin_mes AND (s.fecha_egr IS NULL OR s.fecha_egr > per.fin_mes) AND s.is_subs = 1) as "STOCK_SUBS",
    COUNT(*) FILTER (WHERE s.fecha_ing <= per.fin_mes AND (s.fecha_egr IS NULL OR s.fecha_egr > per.fin_mes) AND s.is_subs = 0 AND (
        SELECT p.destinatario FROM mvw_ee_pases_secgdu p WHERE p.id_expediente = s.id_expediente AND p.fecha <= per.fin_mes ORDER BY p.fecha DESC LIMIT 1
    ) IN (SELECT * FROM analistas_area)) as "STOCK_PROPIO",
    array_to_string(tm.acronimos_list, ', ') as acronimos
FROM tramites_metadata tm
CROSS JOIN periodos per
LEFT JOIN status_final s ON tm.trata = s.trata AND tm.gerencia = s.gerencia
GROUP BY 1, 2, 3, 4, 5
ORDER BY 1, 2, 4, 5;
```

---

## Paso 7: Resto de Reportes Históricos
Para las gerencias restantes, utilice los archivos `.sql` correspondientes en la carpeta `queries/`. Todos siguen la estructura del **Paso 6.2** o **6.3**.

---

## Alternativa Automática (Recomendada)
Para ejecutar todo esto sin copiar y pegar, utilice el script orquestador:

```bash
python sync_public.py
```
