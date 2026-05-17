-- ============================================================
-- CONTABLE 00: Cargar configuración del sector
-- ============================================================
-- PROPÓSITO:
--   1) Cargar fila CONTABLE en cfg_gestion_metas.
--   2) Cargar reglas de egreso en cfg_egresos_por_trata.
--
-- IMPORTANTE: Las tratas de Contable tienen reglas distintas:
--   - MDUG0901A: IF firmado SOLO por FABIANSANTILLAN o LICETB.
--   - MDUG1501J: IFPDO (cualquier firmante).
--   - MDUG3001A: IFPDO (cualquier firmante - se distingue de Etapa Proyecto por el buzón).
--   - MDUG3402A: IFPEO o IFPDO (cualquier firmante).
--
-- ORDEN DE EJECUCIÓN: 1°.
-- ============================================================

-- ============================================================
-- Paso 1: Limpiar registros previos (idempotente)
-- ============================================================
DELETE FROM cfg_gestion_metas 
WHERE gerencia = 'contable' AND trata_reporte = 'CONTABLE';

DELETE FROM cfg_egresos_por_trata 
WHERE gerencia = 'contable';


-- ============================================================
-- Paso 2: cfg_gestion_metas
-- ============================================================
INSERT INTO cfg_gestion_metas (
    gerencia,
    trata_reporte,
    tratas_incluidas,
    acronimos_egreso,         -- DEPRECATED: ahora se usa cfg_egresos_por_trata
    firmantes_egreso,         -- DEPRECATED: idem
    buzones_ingreso,
    buzones_ingreso_intervenciones,
    analistas_oficiales
)
VALUES (
    'contable',
    'CONTABLE',
    -- 4 tratas propias
    ARRAY['MDUG0901A','MDUG1501J','MDUG3001A','MDUG3402A']::TEXT[],
    -- Acrónimos (referencial, no se usan en la nueva lógica)
    ARRAY['IF','IFPDO','IFPEO']::TEXT[],
    -- Firmantes (referencial)
    NULL::TEXT[],
    -- Buzones de ingreso (2)
    ARRAY['DGROC-CONTABLE','DGROC-OBRASADMIN']::TEXT[],
    -- Para intervenciones, mismos buzones que los de propios
    ARRAY['DGROC-CONTABLE','DGROC-OBRASADMIN']::TEXT[],
    -- Analistas oficiales y buzones del sector
    ARRAY[
        'AMONTEVERDE','AMORINC','CARLOSDUARTE','CAROJAS','COLOTTAP',
        'CPENDON','DAS','DASTUGUEO','DEGODOY',
        'DGROC-AUTOMAT','DGROC-CONTABLE','DGROC-DCG','DGROC-DESCARGOS',
        'DGROC-DTACONT','DGROC-DTARPS','DGROC-LEGAJOS','DGROC-OBRASADMIN',
        'DGROC-PENDIENTESDEPAGO','DGROC-REVISIONCONTABLE',
        'DIAZBAR','DKRENZ','EDEFEO','FABIANSANTILLAN','FMHERRERA','FSPANTI',
        'GARCIASEBA','HRICCIARDI','JOSEMARIAORTIZ','JPOMAR','JULILOPARDO',
        'LAMORGIAKA','LBARRIENTOS','LICETB','M.ROSSO','MARQUEZMAR','MARTINEZCLA',
        'MLAURITO','MMALACALZA','NMONTEVERDE','NMORENO','POVIEDO','PRESAF',
        'PVACEVEDO','RIVERAMA','ROBLEDOE','RODRIGUEZLEA','RODRIGUEZMAGD',
        'ROSARIODECRIS','SCHULERG','SENING','SMERMOZ','SORIAD','SPOSAROAL',
        'TATOJ','TIRENDIC','TOMIPITES','VICSOLMORE','VILLACRI'
    ]::TEXT[]
);


-- ============================================================
-- Paso 3: cfg_egresos_por_trata (reglas granulares por trata)
-- ============================================================
INSERT INTO cfg_egresos_por_trata (gerencia, trata, acronimo, firmantes) VALUES
-- MDUG0901A: IF SOLO firmado por FABIANSANTILLAN o LICETB
('contable','MDUG0901A','IF', ARRAY['FABIANSANTILLAN','LICETB']::TEXT[]),

-- MDUG1501J: IFPDO (cualquier firmante)
('contable','MDUG1501J','IFPDO', NULL),

-- MDUG3001A: IFPDO (cualquier firmante; se distingue de Etapa Proyecto por el buzón de ingreso)
('contable','MDUG3001A','IFPDO', NULL),

-- MDUG3402A: IFPEO o IFPDO (cualquier firmante)
('contable','MDUG3402A','IFPEO', NULL),
('contable','MDUG3402A','IFPDO', NULL);


-- ============================================================
-- VALIDACIÓN
-- ============================================================

-- cfg_gestion_metas
SELECT 
    gerencia,
    trata_reporte,
    array_length(tratas_incluidas, 1)               AS n_tratas,
    array_length(buzones_ingreso, 1)                AS n_buzones,
    array_length(analistas_oficiales, 1)            AS n_analistas
FROM cfg_gestion_metas
WHERE gerencia = 'contable';

-- cfg_egresos_por_trata
SELECT 
    trata,
    acronimo,
    firmantes,
    fecha_desde,
    fecha_hasta
FROM cfg_egresos_por_trata
WHERE gerencia = 'contable'
ORDER BY trata, acronimo;

-- Esperado:
-- 4 tratas, 2 buzones, ~57 analistas
-- 5 reglas de egreso (4 tratas, una con 2 acrónimos)
