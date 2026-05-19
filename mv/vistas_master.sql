-- ============================================================
-- MEGA-SQL DE RECONSTRUCCIÓN DE CAPA ANALÍTICA MODULAR (SGDU)
-- GENERADO DE FORMA SEGURA Y SECUENCIAL SEGÚN DEPENDENCIAS
-- ============================================================

SET statement_timeout = 0;
SET work_mem = '256MB';
SET maintenance_work_mem = '512MB';

-- ============================================================
-- VISTAS MATERIALIZADAS BASE (CIMIENTOS TRANSACCIONALES)
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_primer_ingreso_buzon CASCADE;
CREATE MATERIALIZED VIEW mv_primer_ingreso_buzon AS
 SELECT id_expediente,
    destinatario AS buzon,
    min(fecha) AS fecha_primer_ingreso
   FROM mvw_ee_pases_secgdu
  GROUP BY id_expediente, destinatario;

CREATE UNIQUE INDEX idx_mvpib_exp_buzon ON mv_primer_ingreso_buzon(id_expediente, buzon);

DROP MATERIALIZED VIEW IF EXISTS mv_ultimo_pase CASCADE;
CREATE MATERIALIZED VIEW mv_ultimo_pase AS
 SELECT id_expediente,
    fecha AS fecha_ultimo_pase,
    usuario AS usuario_remitente,
    destinatario AS destinatario_actual,
    estado AS estado_en_pase
   FROM ( SELECT mvw_ee_pases_secgdu.id_expediente,
            mvw_ee_pases_secgdu.fecha,
            mvw_ee_pases_secgdu.usuario,
            mvw_ee_pases_secgdu.destinatario,
            mvw_ee_pases_secgdu.estado,
            row_number() OVER (PARTITION BY mvw_ee_pases_secgdu.id_expediente ORDER BY mvw_ee_pases_secgdu.fecha DESC) AS rn
           FROM mvw_ee_pases_secgdu) t
  WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvup_exp ON mv_ultimo_pase(id_expediente);

DROP MATERIALIZED VIEW IF EXISTS mv_ultima_actividad CASCADE;
CREATE MATERIALIZED VIEW mv_ultima_actividad AS
 SELECT id_expediente,
    usuario_alta,
    nombre_tipo_actividad,
    estado AS estado_actividad,
    fecha_alta,
    fecha_cierre,
    usuario_cierre
   FROM ( SELECT mvw_ee_actividades_secgdu.id_expediente,
            mvw_ee_actividades_secgdu.usuario_alta,
            mvw_ee_actividades_secgdu.nombre_tipo_actividad,
            mvw_ee_actividades_secgdu.estado,
            mvw_ee_actividades_secgdu.fecha_alta,
            mvw_ee_actividades_secgdu.fecha_cierre,
            mvw_ee_actividades_secgdu.usuario_cierre,
            row_number() OVER (PARTITION BY mvw_ee_actividades_secgdu.id_expediente ORDER BY mvw_ee_actividades_secgdu.fecha_alta DESC) AS rn
           FROM mvw_ee_actividades_secgdu) t
  WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvua_exp ON mv_ultima_actividad(id_expediente);


-- ============================================================
-- ETAPA DE COMPILACIÓN: 00
-- ============================================================

-- --- INICIO: catastro/00_catastro_alter_cfg.sql ---
-- ============================================================
-- ARCHIVO 00: ALTER de cfg_gestion_metas y carga config Catastro
-- ============================================================

-- Paso 1: Asegurar columnas
ALTER TABLE cfg_gestion_metas 
ADD COLUMN IF NOT EXISTS firmantes_egreso TEXT[];

ALTER TABLE cfg_gestion_metas
ADD COLUMN IF NOT EXISTS buzones_ingreso_intervenciones TEXT[];

-- Paso 2: Borrar fila previa si existe
DELETE FROM cfg_gestion_metas 
WHERE gerencia = 'catastro' AND trata_reporte = 'CATASTRO';

-- Paso 3: Cargar config
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
    'catastro',
    'CATASTRO',
    ARRAY[
        'MDUG0115C','MDUG1501L','MDUG0115G','MDUG1501H','MDUG0134C',
        'MDUG0134N','MDUG0146A','GENE0702C','MDUG0115F','MDUG0115B',
        'MDUG0132A','MDUG0131A','MDUG0131B','MDUG0115E','MDUG0134E','MDUG0135A'
    ]::TEXT[],
    ARRAY[
        'IFMMH','IFMAD','IF','IFDEX','CECNU','IFGPA','FIPAR','IFPCB',
        'PPINV','IFMOT','IFMSC','IFMHC'
    ]::TEXT[],
    NULL, -- Cualquier firmante cuenta como egreso
    ARRAY['DGROC-CIC','DGROC-COPIAPLANO','DGROC-DCATDES','DGROC-DCATPOL','DGROC-DCATTIT']::TEXT[],
    ARRAY[
        'ACOSTAPA','AFAHLER','AGUSMAZZONI','ALEALFONSIN','ALEGREM',
        'ARGENTOES','BARTROLIG','CABRERAM','CANALEAL','CARBONELLIM',
        'CHIANETTAR','CIOPKOG','CISTERNACA','COHENCAD','CONTIL',
        'CONVERTID','DELGADODE','DGROC-CIC','DGROC-COPIAPLANO','DGROC-DCATDES',
        'DGROC-DCATMEN','DGROC-DCATPOL','DGROC-DCATTIT','DIBIASEO','DIEZGASTON',
        'DIHARCEP','DURSIM','ECIJAN','FMARCHISELLA','FOLLONIERLE',
        'FREIXASC','GARCIASIL','GILESJP','GONZALEZAMA','GONZALEZHORAC',
        'GUZMANO','IGARZABALP','JTIRADO','LAGUNAMA','LBELLY',
        'LOISIG','LUCCIC','M.NAPOLI','MALATTOR','MANNOP',
        'MARCHETTIJ','MHOSBALIKCIYAN','MOSCOVICHA','NCITRANGOLO','NOGUERAH',
        'NPONZO','NQUINTERNO','PONZOS','ROLDANG','SALGUEROM',
        'SORIAANDREA','TARRUA','TAVELLAE','VEGAJ','VILLAGI',
        'WVIRGILIO'
    ]::TEXT[],
    ARRAY['DGROC-CIC','DGROC-COPIAPLANO','DGROC-DCATDES','DGROC-DCATPOL','DGROC-DCATTIT']::TEXT[]
);

-- --- FIN: catastro/00_catastro_alter_cfg.sql ---

-- --- INICIO: instalaciones/00_instalaciones_alter_cfg.sql ---
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

-- --- FIN: instalaciones/00_instalaciones_alter_cfg.sql ---

-- --- INICIO: regularizacion/00_regularizacion_alter_cfg.sql ---
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

-- --- FIN: regularizacion/00_regularizacion_alter_cfg.sql ---

-- --- INICIO: contable/00_contable_alter_cfg.sql ---
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

-- --- FIN: contable/00_contable_alter_cfg.sql ---

-- --- INICIO: etapa_proyecto/00_etapa_proyecto_alter_cfg.sql ---
-- ============================================================
-- ARCHIVO 00: ALTER de cfg_gestion_metas y carga config Etapa Proyecto
-- ============================================================

-- Paso 1: Asegurar columnas
ALTER TABLE cfg_gestion_metas 
ADD COLUMN IF NOT EXISTS firmantes_egreso TEXT[];

ALTER TABLE cfg_gestion_metas
ADD COLUMN IF NOT EXISTS buzones_ingreso_intervenciones TEXT[];

-- Paso 2: Borrar fila previa si existe
DELETE FROM cfg_gestion_metas 
WHERE gerencia = 'etapa_proyecto' AND trata_reporte = 'ETAPA PROYECTO';

-- Paso 3: Cargar config
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
    'etapa_proyecto',
    'ETAPA PROYECTO',
    ARRAY['MDUG3402A','MDUG1502A','MDUG4003A','MDUG0142A','MDUG3001A']::TEXT[],
    ARRAY['IFTPT','IFOCD','IFBRP']::TEXT[],
    NULL, -- Cualquier firmante cuenta como egreso
    ARRAY['DGROC-OBRASTECNICA']::TEXT[],
    ARRAY[
        'A.PEREZ','AGUSDEMARCO','ANTOVERA','BELOCURESJ','COIROL',
        'DBECERRACURITIMA','DGROC-OBRASTECNICA','DIMASOM','DNKAINSKY','FORGIONEA',
        'GAILLURJP','GARRIONDO','JOSEFINA.P','M.SANCHEZ','MARCE.TOSONI',
        'MARCETOSONI','MARCETOSONI1','MBRISA','MCANOGARAY','MCARLUCCIO',
        'MGALLARDOC','MSTIBERTI','NLOPEZQUIROGA','ROCABERTJ','SPUET',
        'TALAMOM','VERA'
    ]::TEXT[],
    ARRAY['DGROC-OBRASTECNICA']::TEXT[] -- Intervenciones entran por el mismo buzón
);

-- --- FIN: etapa_proyecto/00_etapa_proyecto_alter_cfg.sql ---

-- --- INICIO: aviso_obra/00_aviso_obra_alter_cfg.sql ---
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

-- --- FIN: aviso_obra/00_aviso_obra_alter_cfg.sql ---

-- --- INICIO: morfologia/00_morfologia_alter_cfg.sql ---
-- ============================================================
-- ARCHIVO 00: ALTER de cfg_gestion_metas y carga config Morfología
-- ============================================================
-- PROPÓSITO: 
--   1) Agregar columna firmantes_egreso (si no existe).
--   2) Cargar la fila MORFOLOGIA en cfg_gestion_metas.
-- ORDEN DE EJECUCIÓN: 1° (antes de todo lo demás).
-- ============================================================

-- Paso 1: Agregar columna firmantes_egreso si no existe
ALTER TABLE cfg_gestion_metas 
ADD COLUMN IF NOT EXISTS firmantes_egreso TEXT[];

COMMENT ON COLUMN cfg_gestion_metas.firmantes_egreso IS 
'Lista de usuarios cuyas firmas en GEDOs de la lista acronimos_egreso cuentan como egreso efectivo. NULL = cualquier firmante.';


-- Paso 2: Borrar fila previa de morfologia si existe (idempotente)
DELETE FROM cfg_gestion_metas 
WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA';


-- Paso 3: Cargar config de Morfología
INSERT INTO cfg_gestion_metas (
    gerencia,
    trata_reporte,
    tratas_incluidas,
    acronimos_egreso,
    firmantes_egreso,
    buzones_ingreso,
    analistas_oficiales
)
VALUES (
    'morfologia',
    'MORFOLOGIA',
    -- Tratas propias (10 tratas)
    ARRAY[
        'MDUG1801A','MDUG0107A','MDUG3501A','MDUG3601A','MDUG3901A',
        'MDUG1802A','MDUG1804A','MDUG1803A','MDUG1805A','MDUG1806A'
    ]::TEXT[],
    -- Acrónimos de egreso (DI, ANEXO, IF)
    ARRAY['DI','ANEXO','IF']::TEXT[],
    -- Firmantes oficiales para egreso efectivo
    ARRAY['ALANDAZURI']::TEXT[],
    -- Buzones de ingreso (1 buzón para tratas propias)
    ARRAY['DGIUR-03']::TEXT[],
    -- Analistas oficiales (lista completa)
    ARRAY[
        'A.GUZMAN','AGARTEAGA','ALANDAZURI','ALFONSOGA','CAROLINAPRADO',
        'CGAMARRA','CGENTILINI','DANCOLOMBO','DGIUR-03','DGIUR-ADMISIBILIDADMORFO',
        'DGIUR-CONSULTASESPECIFICAS','DGIUR-CURVERIFICACION','DGIUR-DGIUR-PERMISO TEMPRANO','DGIUR-VA II',
        'ECAYSSIALS','EVELYNTORRES','FORFANO','FOTTOGALLI','FRANGARAY',
        'GBERNASCONI','GCABADGIUR','IANELUSTONDO','IVALDES','LNSPERTINO',
        'M.SABATINO','MANUELALVELO','MILAGROSTOURON','MILENAAZULMORENO','MLOBIANCOCRIADO',
        'MPLANS1','MREIDMAN','MVOSKIAN','NASILANES','NCASALE',
        'OVERRINA','PTEIGA','ROCAM','SBONDOREVSKY','SCABANELLAS',
        'SDAVIDOVSKY','SVC_DGIURMORFO','SVCDGIUR3','TOSELLIR','VVINICIUS'
    ]::TEXT[]
);


-- Paso 4: Para intervenciones, agregamos también los buzones extra como puntos de ingreso
-- Esto es porque las intervenciones de morfología pueden entrar por más buzones que las propias.
-- Vamos a manejarlo creando una columna nueva o lo resolveremos en la MV del universo.
-- Por ahora, anotamos los 5 buzones adicionales de intervenciones en un campo nuevo.
ALTER TABLE cfg_gestion_metas
ADD COLUMN IF NOT EXISTS buzones_ingreso_intervenciones TEXT[];

COMMENT ON COLUMN cfg_gestion_metas.buzones_ingreso_intervenciones IS 
'Buzones adicionales por los que ingresan SOLO intervenciones (no aplica a tratas propias). NULL = usar buzones_ingreso.';

UPDATE cfg_gestion_metas 
SET buzones_ingreso_intervenciones = ARRAY[
    'DGIUR-03',
    'DGIUR-ADMISIBILIDADMORFO',
    'DGIUR-CONSULTASESPECIFICAS',
    'DGIUR-CURVERIFICACION',
    'DGIUR-DGIUR-PERMISO TEMPRANO',
    'DGIUR-VA II'
]::TEXT[]
WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA';


-- Paso 5: Verificación
SELECT 
    gerencia,
    trata_reporte,
    array_length(tratas_incluidas, 1)               AS n_tratas_propias,
    array_length(acronimos_egreso, 1)               AS n_acronimos,
    array_length(firmantes_egreso, 1)               AS n_firmantes,
    array_length(buzones_ingreso, 1)                AS n_buzones_propios,
    array_length(buzones_ingreso_intervenciones, 1) AS n_buzones_intervenciones,
    array_length(analistas_oficiales, 1)            AS n_analistas
FROM cfg_gestion_metas
WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA';

-- Esperado:
-- n_tratas_propias: 10
-- n_acronimos: 3
-- n_firmantes: 1
-- n_buzones_propios: 1
-- n_buzones_intervenciones: 6
-- n_analistas: 44

-- --- FIN: morfologia/00_morfologia_alter_cfg.sql ---

-- --- INICIO: aph/00_aph_alter_cfg.sql ---
-- ============================================================
-- ARCHIVO 00: ALTER de cfg_gestion_metas y carga config APH
-- ============================================================

DELETE FROM cfg_gestion_metas WHERE gerencia = 'aph' AND trata_reporte = 'APH';

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
    'aph',
    'APH',
    ARRAY['MDUG3701A','MDUG3801A']::TEXT[],
    ARRAY['DICTAMEN','ANEXO','INFORME']::TEXT[],
    ARRAY['VASTAM']::TEXT[],
    ARRAY['DGIUR-21']::TEXT[],
    ARRAY[
        'CHANTIRRO','CHEZOM','DAMATOG','DESANTISA','DGIUR-21',
        'DGIUR-ADMISIBILIDADAPH','DGIUR-ADMISIMIDIDADAPH','GALAMA',
        'GONZALEZNIETOR','HERENUFE','LSANTINMOLINA','MARIANALVAREZ',
        'NASALVATIERRA','PIOLON','SVC_DGIURADMAPH','VASTAM'
    ]::TEXT[],
    ARRAY['DGIUR-21']::TEXT[]
);

-- --- FIN: aph/00_aph_alter_cfg.sql ---

-- --- INICIO: usos/00_usos_alter_cfg.sql ---
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

-- --- FIN: usos/00_usos_alter_cfg.sql ---

-- ============================================================
-- ETAPA DE COMPILACIÓN: 01
-- ============================================================

-- --- INICIO: catastro/01_catastro_universo.sql ---
-- ============================================================
-- ARCHIVO 01: mv_catastro_universo
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_universo CASCADE;
DROP TYPE IF EXISTS mv_catastro_universo CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_universo AS
WITH cfg AS (
    SELECT 
        buzones_ingreso, 
        buzones_ingreso_intervenciones,
        tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'catastro' AND trata_reporte = 'CATASTRO'
),
ingresos_propios AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso)
    GROUP BY pib.id_expediente
),
ingresos_intervenciones AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso_intervenciones)
    GROUP BY pib.id_expediente
)
SELECT
    e.id_expediente,
    e.expediente,
    e.trata,
    e.descripcion_trata,
    e.descripcion,
    e.caratula,
    e.estado                                AS estado_expediente,
    e.fecha_creacion                        AS fecha_creacion_ee,
    CASE 
        WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.primer_buzon
        ELSE ii.primer_buzon
    END                                     AS primer_buzon_ingreso,
    CASE 
        WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.fecha_min
        ELSE ii.fecha_min
    END                                     AS fecha_primer_ingreso_gerencia,
    (e.trata = ANY(cfg.tratas_incluidas))   AS es_trata_propia
FROM mvw_expedientes_tratas_secgdu e
CROSS JOIN cfg
LEFT JOIN ingresos_propios       ip ON ip.id_expediente = e.id_expediente
LEFT JOIN ingresos_intervenciones ii ON ii.id_expediente = e.id_expediente
WHERE
    (e.trata = ANY(cfg.tratas_incluidas) AND ip.id_expediente IS NOT NULL)
    OR
    (NOT (e.trata = ANY(cfg.tratas_incluidas)) AND ii.id_expediente IS NOT NULL);

CREATE UNIQUE INDEX idx_mvct_univ_exp ON mv_catastro_universo(id_expediente);
CREATE INDEX idx_mvct_univ_trata ON mv_catastro_universo(trata);
CREATE INDEX idx_mvct_univ_propia ON mv_catastro_universo(es_trata_propia);
CREATE INDEX idx_mvct_univ_fecha ON mv_catastro_universo(fecha_primer_ingreso_gerencia);

-- --- FIN: catastro/01_catastro_universo.sql ---

-- --- INICIO: instalaciones/01_instalaciones_universo.sql ---
-- ============================================================
-- ARCHIVO 01: mv_instalaciones_universo
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_universo CASCADE;
DROP TYPE IF EXISTS mv_instalaciones_universo CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_universo AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones, tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'instalaciones' AND trata_reporte = 'INSTALACIONES'
),
ingresos_propios AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso)
    GROUP BY pib.id_expediente
),
ingresos_intervenciones AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso_intervenciones)
    GROUP BY pib.id_expediente
)
SELECT
    e.id_expediente, e.expediente, e.trata, e.descripcion_trata, e.descripcion, e.caratula,
    e.estado AS estado_expediente, e.fecha_creacion AS fecha_creacion_ee,
    CASE WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.primer_buzon ELSE ii.primer_buzon END AS primer_buzon_ingreso,
    CASE WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.fecha_min ELSE ii.fecha_min END AS fecha_primer_ingreso_gerencia,
    (e.trata = ANY(cfg.tratas_incluidas)) AS es_trata_propia
FROM mvw_expedientes_tratas_secgdu e
CROSS JOIN cfg
LEFT JOIN ingresos_propios ip ON ip.id_expediente = e.id_expediente
LEFT JOIN ingresos_intervenciones ii ON ii.id_expediente = e.id_expediente
WHERE
    (e.trata = ANY(cfg.tratas_incluidas) AND ip.id_expediente IS NOT NULL)
    OR
    (NOT (e.trata = ANY(cfg.tratas_incluidas)) AND ii.id_expediente IS NOT NULL);

CREATE UNIQUE INDEX idx_mvins_univ_exp ON mv_instalaciones_universo(id_expediente);
CREATE INDEX idx_mvins_univ_propia ON mv_instalaciones_universo(es_trata_propia);

-- --- FIN: instalaciones/01_instalaciones_universo.sql ---

-- --- INICIO: regularizacion/01_regularizacion_universo.sql ---
-- ============================================================
-- ARCHIVO 01: mv_regularizacion_universo
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_universo CASCADE;
DROP TYPE IF EXISTS mv_regularizacion_universo CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_universo AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones, tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME'
),
ingresos_propios AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso)
    GROUP BY pib.id_expediente
),
ingresos_intervenciones AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso_intervenciones)
    GROUP BY pib.id_expediente
)
SELECT
    e.id_expediente, e.expediente, e.trata, e.descripcion_trata, e.descripcion, e.caratula,
    e.estado AS estado_expediente, e.fecha_creacion AS fecha_creacion_ee,
    CASE WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.primer_buzon ELSE ii.primer_buzon END AS primer_buzon_ingreso,
    CASE WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.fecha_min ELSE ii.fecha_min END AS fecha_primer_ingreso_gerencia,
    (e.trata = ANY(cfg.tratas_incluidas)) AS es_trata_propia
FROM mvw_expedientes_tratas_secgdu e
CROSS JOIN cfg
LEFT JOIN ingresos_propios ip ON ip.id_expediente = e.id_expediente
LEFT JOIN ingresos_intervenciones ii ON ii.id_expediente = e.id_expediente
WHERE
    (e.trata = ANY(cfg.tratas_incluidas) AND ip.id_expediente IS NOT NULL)
    OR
    (NOT (e.trata = ANY(cfg.tratas_incluidas)) AND ii.id_expediente IS NOT NULL);

CREATE UNIQUE INDEX idx_mvreg_univ_exp ON mv_regularizacion_universo(id_expediente);
CREATE INDEX idx_mvreg_univ_propia ON mv_regularizacion_universo(es_trata_propia);

-- --- FIN: regularizacion/01_regularizacion_universo.sql ---

-- --- INICIO: contable/01_contable_universo.sql ---
-- ============================================================
-- CONTABLE 01: mv_contable_universo
-- ============================================================
-- Trámites propios: trata propia + entró por DGROC-CONTABLE o DGROC-OBRASADMIN.
-- Intervenciones: trata ajena + entró por los mismos buzones.
-- ORDEN DE EJECUCIÓN: 2°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_universo CASCADE;
DROP TYPE IF EXISTS mv_contable_universo CASCADE;

CREATE MATERIALIZED VIEW mv_contable_universo AS
WITH cfg AS (
    SELECT 
        buzones_ingreso, 
        buzones_ingreso_intervenciones,
        tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'contable' AND trata_reporte = 'CONTABLE'
),
ingresos_propios AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso)
    GROUP BY pib.id_expediente
),
ingresos_intervenciones AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso_intervenciones)
    GROUP BY pib.id_expediente
)
SELECT
    e.id_expediente,
    e.expediente,
    e.trata,
    e.descripcion_trata,
    e.descripcion,
    e.caratula,
    e.estado                                AS estado_expediente,
    e.fecha_creacion                        AS fecha_creacion_ee,
    CASE 
        WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.primer_buzon
        ELSE ii.primer_buzon
    END                                     AS primer_buzon_ingreso,
    CASE 
        WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.fecha_min
        ELSE ii.fecha_min
    END                                     AS fecha_primer_ingreso_gerencia,
    (e.trata = ANY(cfg.tratas_incluidas))   AS es_trata_propia
FROM mvw_expedientes_tratas_secgdu e
CROSS JOIN cfg
LEFT JOIN ingresos_propios        ip ON ip.id_expediente = e.id_expediente
LEFT JOIN ingresos_intervenciones ii ON ii.id_expediente = e.id_expediente
WHERE
    (e.trata = ANY(cfg.tratas_incluidas) AND ip.id_expediente IS NOT NULL)
    OR
    (NOT (e.trata = ANY(cfg.tratas_incluidas)) AND ii.id_expediente IS NOT NULL);

CREATE UNIQUE INDEX idx_mvc_univ_exp ON mv_contable_universo(id_expediente);
CREATE INDEX idx_mvc_univ_trata ON mv_contable_universo(trata);
CREATE INDEX idx_mvc_univ_propia ON mv_contable_universo(es_trata_propia);
CREATE INDEX idx_mvc_univ_fecha ON mv_contable_universo(fecha_primer_ingreso_gerencia);


-- Validación
SELECT es_trata_propia, COUNT(*) AS cant
FROM mv_contable_universo
GROUP BY es_trata_propia;

-- --- FIN: contable/01_contable_universo.sql ---

-- --- INICIO: etapa_proyecto/01_etapa_proyecto_universo.sql ---
-- ============================================================
-- ARCHIVO 01: mv_etapa_proyecto_universo
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_universo CASCADE;
DROP TYPE IF EXISTS mv_etapa_proyecto_universo CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_universo AS
WITH cfg AS (
    SELECT 
        buzones_ingreso, 
        buzones_ingreso_intervenciones,
        tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'etapa_proyecto' AND trata_reporte = 'ETAPA PROYECTO'
),
ingresos_propios AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso)
    GROUP BY pib.id_expediente
),
ingresos_intervenciones AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso_intervenciones)
    GROUP BY pib.id_expediente
)
SELECT
    e.id_expediente,
    e.expediente,
    e.trata,
    e.descripcion_trata,
    e.descripcion,
    e.caratula,
    e.estado                                AS estado_expediente,
    e.fecha_creacion                        AS fecha_creacion_ee,
    CASE 
        WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.primer_buzon
        ELSE ii.primer_buzon
    END                                     AS primer_buzon_ingreso,
    CASE 
        WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.fecha_min
        ELSE ii.fecha_min
    END                                     AS fecha_primer_ingreso_gerencia,
    (e.trata = ANY(cfg.tratas_incluidas))   AS es_trata_propia
FROM mvw_expedientes_tratas_secgdu e
CROSS JOIN cfg
LEFT JOIN ingresos_propios       ip ON ip.id_expediente = e.id_expediente
LEFT JOIN ingresos_intervenciones ii ON ii.id_expediente = e.id_expediente
WHERE
    (e.trata = ANY(cfg.tratas_incluidas) AND ip.id_expediente IS NOT NULL)
    OR
    (NOT (e.trata = ANY(cfg.tratas_incluidas)) AND ii.id_expediente IS NOT NULL);

CREATE UNIQUE INDEX idx_mvep_univ_exp ON mv_etapa_proyecto_universo(id_expediente);
CREATE INDEX idx_mvep_univ_trata ON mv_etapa_proyecto_universo(trata);
CREATE INDEX idx_mvep_univ_propia ON mv_etapa_proyecto_universo(es_trata_propia);
CREATE INDEX idx_mvep_univ_fecha ON mv_etapa_proyecto_universo(fecha_primer_ingreso_gerencia);

-- --- FIN: etapa_proyecto/01_etapa_proyecto_universo.sql ---

-- --- INICIO: aviso_obra/01_aviso_obra_universo.sql ---
-- ============================================================
-- ARCHIVO 01: mv_aviso_obra_universo
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_universo CASCADE;
DROP TYPE IF EXISTS mv_aviso_obra_universo CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_universo AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones, tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'aviso_obra' AND trata_reporte = 'AVISO DE OBRA'
),
ingresos_propios AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso)
    GROUP BY pib.id_expediente
),
ingresos_intervenciones AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso_intervenciones)
    GROUP BY pib.id_expediente
)
SELECT
    e.id_expediente, e.expediente, e.trata, e.descripcion_trata, e.descripcion, e.caratula,
    e.estado AS estado_expediente, e.fecha_creacion AS fecha_creacion_ee,
    CASE WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.primer_buzon ELSE ii.primer_buzon END AS primer_buzon_ingreso,
    CASE WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.fecha_min ELSE ii.fecha_min END AS fecha_primer_ingreso_gerencia,
    (e.trata = ANY(cfg.tratas_incluidas)) AS es_trata_propia
FROM mvw_expedientes_tratas_secgdu e
CROSS JOIN cfg
LEFT JOIN ingresos_propios ip ON ip.id_expediente = e.id_expediente
LEFT JOIN ingresos_intervenciones ii ON ii.id_expediente = e.id_expediente
WHERE
    (e.trata = ANY(cfg.tratas_incluidas) AND ip.id_expediente IS NOT NULL)
    OR
    (NOT (e.trata = ANY(cfg.tratas_incluidas)) AND ii.id_expediente IS NOT NULL);

CREATE UNIQUE INDEX idx_mvao_univ_exp ON mv_aviso_obra_universo(id_expediente);
CREATE INDEX idx_mvao_univ_propia ON mv_aviso_obra_universo(es_trata_propia);

-- --- FIN: aviso_obra/01_aviso_obra_universo.sql ---

-- --- INICIO: morfologia/01_morfologia_universo.sql ---
-- ============================================================
-- ARCHIVO 01: mv_morfologia_universo
-- ============================================================
-- PROPÓSITO: Universo de expedientes que entraron al sector.
-- Trámites propios: entraron por DGIUR-03 con trata propia.
-- Intervenciones: entraron por cualquiera de los 6 buzones con trata ajena.
-- ORDEN DE EJECUCIÓN: 2°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_universo CASCADE;
DROP TYPE IF EXISTS mv_morfologia_universo CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_universo AS
WITH cfg AS (
    SELECT 
        buzones_ingreso, 
        buzones_ingreso_intervenciones,
        tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
),
-- Primer ingreso a buzón de propios (DGIUR-03) - válido para propios y eventualmente intervenciones
ingresos_propios AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso)
    GROUP BY pib.id_expediente
),
-- Primer ingreso a CUALQUIER buzón de intervenciones (los 6)
ingresos_intervenciones AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso_intervenciones)
    GROUP BY pib.id_expediente
)
SELECT
    e.id_expediente,
    e.expediente,
    e.trata,
    e.descripcion_trata,
    e.descripcion,
    e.caratula,
    e.estado                                AS estado_expediente,
    e.fecha_creacion                        AS fecha_creacion_ee,
    -- Para propios: el buzón es DGIUR-03. Para intervenciones: cualquiera de los 6.
    CASE 
        WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.primer_buzon
        ELSE ii.primer_buzon
    END                                     AS primer_buzon_ingreso,
    -- Fecha del primer ingreso correspondiente
    CASE 
        WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.fecha_min
        ELSE ii.fecha_min
    END                                     AS fecha_primer_ingreso_gerencia,
    (e.trata = ANY(cfg.tratas_incluidas))   AS es_trata_propia
FROM mvw_expedientes_tratas_secgdu e
CROSS JOIN cfg
LEFT JOIN ingresos_propios       ip ON ip.id_expediente = e.id_expediente
LEFT JOIN ingresos_intervenciones ii ON ii.id_expediente = e.id_expediente
WHERE
    -- Propios: deben haber entrado por DGIUR-03
    (e.trata = ANY(cfg.tratas_incluidas) AND ip.id_expediente IS NOT NULL)
    OR
    -- Intervenciones: trata ajena + entró por alguno de los 6 buzones
    (NOT (e.trata = ANY(cfg.tratas_incluidas)) AND ii.id_expediente IS NOT NULL);

CREATE UNIQUE INDEX idx_mvm_univ_exp ON mv_morfologia_universo(id_expediente);
CREATE INDEX idx_mvm_univ_trata ON mv_morfologia_universo(trata);
CREATE INDEX idx_mvm_univ_propia ON mv_morfologia_universo(es_trata_propia);
CREATE INDEX idx_mvm_univ_fecha ON mv_morfologia_universo(fecha_primer_ingreso_gerencia);


-- Validación rápida
SELECT 
    es_trata_propia,
    COUNT(*) AS cant
FROM mv_morfologia_universo
GROUP BY es_trata_propia;

-- --- FIN: morfologia/01_morfologia_universo.sql ---

-- --- INICIO: aph/01_aph_universo.sql ---
-- ============================================================
-- ARCHIVO 01: mv_aph_universo
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_universo CASCADE;
DROP TYPE IF EXISTS mv_aph_universo CASCADE;

CREATE MATERIALIZED VIEW mv_aph_universo AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones, tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'aph' AND trata_reporte = 'APH'
),
ingresos_propios AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso)
    GROUP BY pib.id_expediente
),
ingresos_intervenciones AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso_intervenciones)
    GROUP BY pib.id_expediente
)
SELECT
    e.id_expediente, e.expediente, e.trata, e.descripcion_trata, e.descripcion, e.caratula,
    e.estado AS estado_expediente, e.fecha_creacion AS fecha_creacion_ee,
    CASE WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.primer_buzon ELSE ii.primer_buzon END AS primer_buzon_ingreso,
    CASE WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.fecha_min ELSE ii.fecha_min END AS fecha_primer_ingreso_gerencia,
    (e.trata = ANY(cfg.tratas_incluidas)) AS es_trata_propia
FROM mvw_expedientes_tratas_secgdu e
CROSS JOIN cfg
LEFT JOIN ingresos_propios ip ON ip.id_expediente = e.id_expediente
LEFT JOIN ingresos_intervenciones ii ON ii.id_expediente = e.id_expediente
WHERE
    (e.trata = ANY(cfg.tratas_incluidas) AND ip.id_expediente IS NOT NULL)
    OR
    (NOT (e.trata = ANY(cfg.tratas_incluidas)) AND ii.id_expediente IS NOT NULL);

CREATE UNIQUE INDEX idx_mvaph_univ_exp ON mv_aph_universo(id_expediente);
CREATE INDEX idx_mvaph_univ_propia ON mv_aph_universo(es_trata_propia);

-- --- FIN: aph/01_aph_universo.sql ---

-- --- INICIO: usos/01_usos_universo.sql ---
-- ============================================================
-- ARCHIVO 01: mv_usos_universo
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_universo CASCADE;
DROP TYPE IF EXISTS mv_usos_universo CASCADE;

CREATE MATERIALIZED VIEW mv_usos_universo AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones, tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos' AND trata_reporte = 'USOS'
),
ingresos_propios AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso)
    GROUP BY pib.id_expediente
),
ingresos_intervenciones AS (
    SELECT 
        pib.id_expediente,
        MIN(pib.fecha_primer_ingreso) AS fecha_min,
        (ARRAY_AGG(pib.buzon ORDER BY pib.fecha_primer_ingreso ASC))[1] AS primer_buzon
    FROM mv_primer_ingreso_buzon pib
    CROSS JOIN cfg
    WHERE pib.buzon = ANY(cfg.buzones_ingreso_intervenciones)
    GROUP BY pib.id_expediente
)
SELECT
    e.id_expediente, e.expediente, e.trata, e.descripcion_trata, e.descripcion, e.caratula,
    e.estado AS estado_expediente, e.fecha_creacion AS fecha_creacion_ee,
    CASE WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.primer_buzon ELSE ii.primer_buzon END AS primer_buzon_ingreso,
    CASE WHEN e.trata = ANY(cfg.tratas_incluidas) THEN ip.fecha_min ELSE ii.fecha_min END AS fecha_primer_ingreso_gerencia,
    (e.trata = ANY(cfg.tratas_incluidas)) AS es_trata_propia
FROM mvw_expedientes_tratas_secgdu e
CROSS JOIN cfg
LEFT JOIN ingresos_propios ip ON ip.id_expediente = e.id_expediente
LEFT JOIN ingresos_intervenciones ii ON ii.id_expediente = e.id_expediente
WHERE
    (e.trata = ANY(cfg.tratas_incluidas) AND ip.id_expediente IS NOT NULL)
    OR
    (NOT (e.trata = ANY(cfg.tratas_incluidas)) AND ii.id_expediente IS NOT NULL);

CREATE UNIQUE INDEX idx_mvusos_univ_exp ON mv_usos_universo(id_expediente);
CREATE INDEX idx_mvusos_univ_propia ON mv_usos_universo(es_trata_propia);

-- --- FIN: usos/01_usos_universo.sql ---

-- ============================================================
-- ETAPA DE COMPILACIÓN: 02
-- ============================================================

-- --- INICIO: catastro/02_catastro_ingresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 02: mv_catastro_ingresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_ingresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_catastro_ingresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_ingresos_eventos AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones, tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'catastro' AND trata_reporte = 'CATASTRO'
)
SELECT 
    pib.id_expediente,
    univ.expediente,
    pib.fecha_primer_ingreso AS fecha_ingreso,
    pib.buzon,
    univ.trata,
    univ.es_trata_propia
FROM mv_primer_ingreso_buzon pib
JOIN mv_catastro_universo univ ON univ.id_expediente = pib.id_expediente
CROSS JOIN cfg
WHERE 
    (univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso))
    OR
    (NOT univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso_intervenciones));

CREATE INDEX idx_mvct_ing_fecha ON mv_catastro_ingresos_eventos(fecha_ingreso);
CREATE INDEX idx_mvct_ing_trata ON mv_catastro_ingresos_eventos(trata);

-- --- FIN: catastro/02_catastro_ingresos_eventos.sql ---

-- --- INICIO: instalaciones/02_instalaciones_ingresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 02: mv_instalaciones_ingresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_ingresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_instalaciones_ingresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_ingresos_eventos AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones
    FROM cfg_gestion_metas
    WHERE gerencia = 'instalaciones' AND trata_reporte = 'INSTALACIONES'
)
SELECT 
    pib.id_expediente, univ.expediente, pib.fecha_primer_ingreso AS fecha_ingreso,
    pib.buzon, univ.trata, univ.es_trata_propia
FROM mv_primer_ingreso_buzon pib
JOIN mv_instalaciones_universo univ ON univ.id_expediente = pib.id_expediente
CROSS JOIN cfg
WHERE 
    (univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso))
    OR
    (NOT univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso_intervenciones));

CREATE INDEX idx_mvins_ing_fecha ON mv_instalaciones_ingresos_eventos(fecha_ingreso);

-- --- FIN: instalaciones/02_instalaciones_ingresos_eventos.sql ---

-- --- INICIO: regularizacion/02_regularizacion_ingresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 02: mv_regularizacion_ingresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_ingresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_regularizacion_ingresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_ingresos_eventos AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME'
)
SELECT 
    pib.id_expediente, univ.expediente, pib.fecha_primer_ingreso AS fecha_ingreso,
    pib.buzon, univ.trata, univ.es_trata_propia
FROM mv_primer_ingreso_buzon pib
JOIN mv_regularizacion_universo univ ON univ.id_expediente = pib.id_expediente
CROSS JOIN cfg
WHERE 
    (univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso))
    OR
    (NOT univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso_intervenciones));

CREATE INDEX idx_mvreg_ing_fecha ON mv_regularizacion_ingresos_eventos(fecha_ingreso);

-- --- FIN: regularizacion/02_regularizacion_ingresos_eventos.sql ---

-- --- INICIO: contable/02_contable_ingresos_eventos.sql ---
-- ============================================================
-- CONTABLE 02: mv_contable_ingresos_eventos
-- ============================================================
-- PROPÓSITO: Eventos de ingreso (UNO por expediente, el más antiguo).
-- ORDEN DE EJECUCIÓN: 3°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_ingresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_contable_ingresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_contable_ingresos_eventos AS
WITH cfg AS (
    SELECT 
        buzones_ingreso,
        buzones_ingreso_intervenciones,
        tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'contable' AND trata_reporte = 'CONTABLE'
),
expedientes_clasificados AS (
    SELECT 
        e.id_expediente, e.expediente, e.trata, e.descripcion_trata,
        (e.trata = ANY(cfg.tratas_incluidas)) AS es_trata_propia
    FROM mvw_expedientes_tratas_secgdu e
    CROSS JOIN cfg
),
primer_pase AS (
    SELECT 
        ec.id_expediente, ec.expediente, ec.trata, ec.descripcion_trata, ec.es_trata_propia,
        p.fecha, p.usuario, p.destinatario,
        ROW_NUMBER() OVER (PARTITION BY ec.id_expediente ORDER BY p.fecha ASC) AS rn
    FROM expedientes_clasificados ec
    CROSS JOIN cfg
    INNER JOIN mvw_ee_pases_secgdu p ON p.id_expediente = ec.id_expediente
    WHERE 
        (ec.es_trata_propia = TRUE  AND p.destinatario = ANY(cfg.buzones_ingreso))
        OR
        (ec.es_trata_propia = FALSE AND p.destinatario = ANY(cfg.buzones_ingreso_intervenciones))
)
SELECT
    id_expediente, expediente, trata, descripcion_trata,
    fecha           AS fecha_ingreso,
    usuario         AS usuario_remitente,
    destinatario    AS buzon_ingreso,
    es_trata_propia
FROM primer_pase
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvc_ing_ev_exp ON mv_contable_ingresos_eventos(id_expediente);
CREATE INDEX idx_mvc_ing_ev_fecha ON mv_contable_ingresos_eventos(fecha_ingreso);
CREATE INDEX idx_mvc_ing_ev_trata ON mv_contable_ingresos_eventos(trata);
CREATE INDEX idx_mvc_ing_ev_propia ON mv_contable_ingresos_eventos(es_trata_propia);


-- Validación
SELECT es_trata_propia, COUNT(*) AS cant
FROM mv_contable_ingresos_eventos
GROUP BY es_trata_propia;

-- --- FIN: contable/02_contable_ingresos_eventos.sql ---

-- --- INICIO: etapa_proyecto/02_etapa_proyecto_ingresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 02: mv_etapa_proyecto_ingresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_ingresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_etapa_proyecto_ingresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_ingresos_eventos AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones, tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'etapa_proyecto' AND trata_reporte = 'ETAPA PROYECTO'
)
SELECT 
    pib.id_expediente,
    univ.expediente,
    pib.fecha_primer_ingreso AS fecha_ingreso,
    pib.buzon,
    univ.trata,
    univ.es_trata_propia
FROM mv_primer_ingreso_buzon pib
JOIN mv_etapa_proyecto_universo univ ON univ.id_expediente = pib.id_expediente
CROSS JOIN cfg
WHERE 
    (univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso))
    OR
    (NOT univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso_intervenciones));

CREATE INDEX idx_mvep_ing_fecha ON mv_etapa_proyecto_ingresos_eventos(fecha_ingreso);
CREATE INDEX idx_mvep_ing_trata ON mv_etapa_proyecto_ingresos_eventos(trata);

-- --- FIN: etapa_proyecto/02_etapa_proyecto_ingresos_eventos.sql ---

-- --- INICIO: aviso_obra/02_aviso_obra_ingresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 02: mv_aviso_obra_ingresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_ingresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_aviso_obra_ingresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_ingresos_eventos AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones
    FROM cfg_gestion_metas
    WHERE gerencia = 'aviso_obra' AND trata_reporte = 'AVISO DE OBRA'
)
SELECT 
    pib.id_expediente, univ.expediente, pib.fecha_primer_ingreso AS fecha_ingreso,
    pib.buzon, univ.trata, univ.es_trata_propia
FROM mv_primer_ingreso_buzon pib
JOIN mv_aviso_obra_universo univ ON univ.id_expediente = pib.id_expediente
CROSS JOIN cfg
WHERE 
    (univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso))
    OR
    (NOT univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso_intervenciones));

CREATE INDEX idx_mvao_ing_fecha ON mv_aviso_obra_ingresos_eventos(fecha_ingreso);

-- --- FIN: aviso_obra/02_aviso_obra_ingresos_eventos.sql ---

-- --- INICIO: morfologia/02_morfologia_ingresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 02: mv_morfologia_ingresos_eventos
-- ============================================================
-- PROPÓSITO: Eventos de ingreso al sector (UNO por expediente).
-- Regla: si un expediente entra más de una vez al mismo buzón,
-- solo se cuenta el primero (fecha más antigua).
-- Para propios: ingreso a DGIUR-03.
-- Para intervenciones: ingreso a cualquiera de los 6 buzones.
-- ORDEN DE EJECUCIÓN: 3°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_ingresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_morfologia_ingresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_ingresos_eventos AS
WITH cfg AS (
    SELECT 
        buzones_ingreso,
        buzones_ingreso_intervenciones,
        tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
),
-- Para cada expediente, identificar si es propio o intervención
-- y buscar primer pase al buzón correspondiente
expedientes_clasificados AS (
    SELECT 
        e.id_expediente,
        e.expediente,
        e.trata,
        e.descripcion_trata,
        (e.trata = ANY(cfg.tratas_incluidas)) AS es_trata_propia
    FROM mvw_expedientes_tratas_secgdu e
    CROSS JOIN cfg
),
-- Pase más antiguo al buzón correspondiente para cada expediente
primer_pase AS (
    SELECT 
        ec.id_expediente,
        ec.expediente,
        ec.trata,
        ec.descripcion_trata,
        ec.es_trata_propia,
        p.fecha,
        p.usuario,
        p.destinatario,
        ROW_NUMBER() OVER (PARTITION BY ec.id_expediente ORDER BY p.fecha ASC) AS rn
    FROM expedientes_clasificados ec
    CROSS JOIN cfg
    INNER JOIN mvw_ee_pases_secgdu p ON p.id_expediente = ec.id_expediente
    WHERE 
        -- Propios: solo cuentan pases a DGIUR-03
        (ec.es_trata_propia = TRUE  AND p.destinatario = ANY(cfg.buzones_ingreso))
        OR
        -- Intervenciones: pases a cualquiera de los 6 buzones
        (ec.es_trata_propia = FALSE AND p.destinatario = ANY(cfg.buzones_ingreso_intervenciones))
)
SELECT
    id_expediente,
    expediente,
    trata,
    descripcion_trata,
    fecha           AS fecha_ingreso,
    usuario         AS usuario_remitente,
    destinatario    AS buzon_ingreso,
    es_trata_propia
FROM primer_pase
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvm_ing_ev_exp ON mv_morfologia_ingresos_eventos(id_expediente);
CREATE INDEX idx_mvm_ing_ev_fecha ON mv_morfologia_ingresos_eventos(fecha_ingreso);
CREATE INDEX idx_mvm_ing_ev_trata ON mv_morfologia_ingresos_eventos(trata);
CREATE INDEX idx_mvm_ing_ev_propia ON mv_morfologia_ingresos_eventos(es_trata_propia);


-- Validación
SELECT 
    es_trata_propia,
    COUNT(*) AS cant
FROM mv_morfologia_ingresos_eventos
GROUP BY es_trata_propia;

-- --- FIN: morfologia/02_morfologia_ingresos_eventos.sql ---

-- --- INICIO: aph/02_aph_ingresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 02: mv_aph_ingresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_ingresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_aph_ingresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_aph_ingresos_eventos AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones
    FROM cfg_gestion_metas
    WHERE gerencia = 'aph' AND trata_reporte = 'APH'
)
SELECT 
    pib.id_expediente, univ.expediente, pib.fecha_primer_ingreso AS fecha_ingreso,
    pib.buzon, univ.trata, univ.es_trata_propia
FROM mv_primer_ingreso_buzon pib
JOIN mv_aph_universo univ ON univ.id_expediente = pib.id_expediente
CROSS JOIN cfg
WHERE 
    (univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso))
    OR
    (NOT univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso_intervenciones));

CREATE INDEX idx_mvaph_ing_fecha ON mv_aph_ingresos_eventos(fecha_ingreso);

-- --- FIN: aph/02_aph_ingresos_eventos.sql ---

-- --- INICIO: usos/02_usos_ingresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 02: mv_usos_ingresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_ingresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_usos_ingresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_usos_ingresos_eventos AS
WITH cfg AS (
    SELECT buzones_ingreso, buzones_ingreso_intervenciones
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos' AND trata_reporte = 'USOS'
)
SELECT 
    pib.id_expediente, univ.expediente, pib.fecha_primer_ingreso AS fecha_ingreso,
    pib.buzon, univ.trata, univ.es_trata_propia
FROM mv_primer_ingreso_buzon pib
JOIN mv_usos_universo univ ON univ.id_expediente = pib.id_expediente
CROSS JOIN cfg
WHERE 
    (univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso))
    OR
    (NOT univ.es_trata_propia AND pib.buzon = ANY(cfg.buzones_ingreso_intervenciones));

CREATE INDEX idx_mvusos_ing_fecha ON mv_usos_ingresos_eventos(fecha_ingreso);

-- --- FIN: usos/02_usos_ingresos_eventos.sql ---

-- ============================================================
-- ETAPA DE COMPILACIÓN: 03
-- ============================================================

-- --- INICIO: catastro/03_catastro_stock_propio.sql ---
-- ============================================================
-- ARCHIVO 03: mv_catastro_stock_propio
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_stock_propio CASCADE;
DROP TYPE IF EXISTS mv_catastro_stock_propio CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_stock_propio AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'catastro' AND trata_reporte = 'CATASTRO'
)
SELECT
    u.id_expediente,
    u.expediente,
    u.trata,
    u.descripcion_trata,
    u.descripcion,
    u.caratula,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_catastro_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvct_stk_exp ON mv_catastro_stock_propio(id_expediente);

-- --- FIN: catastro/03_catastro_stock_propio.sql ---

-- --- INICIO: instalaciones/03_instalaciones_stock_propio.sql ---
-- ============================================================
-- ARCHIVO 03: mv_instalaciones_stock_propio
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_stock_propio CASCADE;
DROP TYPE IF EXISTS mv_instalaciones_stock_propio CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_stock_propio AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'instalaciones' AND trata_reporte = 'INSTALACIONES'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_instalaciones_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvins_stk_exp ON mv_instalaciones_stock_propio(id_expediente);

-- --- FIN: instalaciones/03_instalaciones_stock_propio.sql ---

-- --- INICIO: regularizacion/03_regularizacion_stock_propio.sql ---
-- ============================================================
-- ARCHIVO 03: mv_regularizacion_stock_propio
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_stock_propio CASCADE;
DROP TYPE IF EXISTS mv_regularizacion_stock_propio CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_stock_propio AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_regularizacion_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvreg_stk_exp ON mv_regularizacion_stock_propio(id_expediente);

-- --- FIN: regularizacion/03_regularizacion_stock_propio.sql ---

-- --- INICIO: contable/03_contable_stock_propio.sql ---
-- ============================================================
-- CONTABLE 03: mv_contable_stock_propio
-- ============================================================
-- ORDEN DE EJECUCIÓN: 4°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_stock_propio CASCADE;
DROP TYPE IF EXISTS mv_contable_stock_propio CASCADE;

CREATE MATERIALIZED VIEW mv_contable_stock_propio AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'contable' AND trata_reporte = 'CONTABLE'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.descripcion, u.caratula, u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_contable_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvc_stk_exp ON mv_contable_stock_propio(id_expediente);
CREATE INDEX idx_mvc_stk_analista ON mv_contable_stock_propio(analista);
CREATE INDEX idx_mvc_stk_trata ON mv_contable_stock_propio(trata);


SELECT COUNT(*) AS total_stock_propio FROM mv_contable_stock_propio;

-- --- FIN: contable/03_contable_stock_propio.sql ---

-- --- INICIO: etapa_proyecto/03_etapa_proyecto_stock_propio.sql ---
-- ============================================================
-- ARCHIVO 03: mv_etapa_proyecto_stock_propio
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_stock_propio CASCADE;
DROP TYPE IF EXISTS mv_etapa_proyecto_stock_propio CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_stock_propio AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'etapa_proyecto' AND trata_reporte = 'ETAPA PROYECTO'
)
SELECT
    u.id_expediente,
    u.expediente,
    u.trata,
    u.descripcion_trata,
    u.descripcion,
    u.caratula,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_etapa_proyecto_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvep_stk_exp ON mv_etapa_proyecto_stock_propio(id_expediente);

-- --- FIN: etapa_proyecto/03_etapa_proyecto_stock_propio.sql ---

-- --- INICIO: aviso_obra/03_aviso_obra_stock_propio.sql ---
-- ============================================================
-- ARCHIVO 03: mv_aviso_obra_stock_propio
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_stock_propio CASCADE;
DROP TYPE IF EXISTS mv_aviso_obra_stock_propio CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_stock_propio AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aviso_obra' AND trata_reporte = 'AVISO DE OBRA'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_aviso_obra_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvao_stk_exp ON mv_aviso_obra_stock_propio(id_expediente);

-- --- FIN: aviso_obra/03_aviso_obra_stock_propio.sql ---

-- --- INICIO: morfologia/03_morfologia_stock_propio.sql ---
-- ============================================================
-- ARCHIVO 03: mv_morfologia_stock_propio
-- ============================================================
-- PROPÓSITO: Expedientes propios actualmente en mano de analista,
-- SIN actividad SOLICITUD_SUBSANACION_TAD abierta de ese mismo analista.
-- ORDEN DE EJECUCIÓN: 4°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_stock_propio CASCADE;
DROP TYPE IF EXISTS mv_morfologia_stock_propio CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_stock_propio AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
)
SELECT
    u.id_expediente,
    u.expediente,
    u.trata,
    u.descripcion_trata,
    u.descripcion,
    u.caratula,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_morfologia_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvm_stk_exp ON mv_morfologia_stock_propio(id_expediente);
CREATE INDEX idx_mvm_stk_analista ON mv_morfologia_stock_propio(analista);
CREATE INDEX idx_mvm_stk_trata ON mv_morfologia_stock_propio(trata);


-- Validación
SELECT COUNT(*) AS total_stock_propio FROM mv_morfologia_stock_propio;

-- --- FIN: morfologia/03_morfologia_stock_propio.sql ---

-- --- INICIO: aph/03_aph_stock_propio.sql ---
-- ============================================================
-- ARCHIVO 03: mv_aph_stock_propio
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_stock_propio CASCADE;
DROP TYPE IF EXISTS mv_aph_stock_propio CASCADE;

CREATE MATERIALIZED VIEW mv_aph_stock_propio AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aph' AND trata_reporte = 'APH'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_aph_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvaph_stk_exp ON mv_aph_stock_propio(id_expediente);

-- --- FIN: aph/03_aph_stock_propio.sql ---

-- --- INICIO: usos/03_usos_stock_propio.sql ---
-- ============================================================
-- ARCHIVO 03: mv_usos_stock_propio
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_stock_propio CASCADE;
DROP TYPE IF EXISTS mv_usos_stock_propio CASCADE;

CREATE MATERIALIZED VIEW mv_usos_stock_propio AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos' AND trata_reporte = 'USOS'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_usos_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvusos_stk_exp ON mv_usos_stock_propio(id_expediente);

-- --- FIN: usos/03_usos_stock_propio.sql ---

-- ============================================================
-- ETAPA DE COMPILACIÓN: 04
-- ============================================================

-- --- INICIO: catastro/04_catastro_subsanaciones.sql ---
-- ============================================================
-- ARCHIVO 04: mv_catastro_subsanaciones
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_subsanaciones CASCADE;
DROP TYPE IF EXISTS mv_catastro_subsanaciones CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_subsanaciones AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'catastro' AND trata_reporte = 'CATASTRO'
)
SELECT
    u.id_expediente,
    u.expediente,
    u.trata,
    u.descripcion_trata,
    u.descripcion,
    u.caratula,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_catastro_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvct_subs_exp ON mv_catastro_subsanaciones(id_expediente);

-- --- FIN: catastro/04_catastro_subsanaciones.sql ---

-- --- INICIO: instalaciones/04_instalaciones_subsanaciones.sql ---
-- ============================================================
-- ARCHIVO 04: mv_instalaciones_subsanaciones
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_subsanaciones CASCADE;
DROP TYPE IF EXISTS mv_instalaciones_subsanaciones CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_subsanaciones AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'instalaciones' AND trata_reporte = 'INSTALACIONES'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_instalaciones_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvins_subs_exp ON mv_instalaciones_subsanaciones(id_expediente);

-- --- FIN: instalaciones/04_instalaciones_subsanaciones.sql ---

-- --- INICIO: regularizacion/04_regularizacion_subsanaciones.sql ---
-- ============================================================
-- ARCHIVO 04: mv_regularizacion_subsanaciones
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_subsanaciones CASCADE;
DROP TYPE IF EXISTS mv_regularizacion_subsanaciones CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_subsanaciones AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_regularizacion_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvreg_subs_exp ON mv_regularizacion_subsanaciones(id_expediente);

-- --- FIN: regularizacion/04_regularizacion_subsanaciones.sql ---

-- --- INICIO: contable/04_contable_subsanaciones.sql ---
-- ============================================================
-- CONTABLE 04: mv_contable_subsanaciones
-- ============================================================
-- ORDEN DE EJECUCIÓN: 5°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_subsanaciones CASCADE;
DROP TYPE IF EXISTS mv_contable_subsanaciones CASCADE;

CREATE MATERIALIZED VIEW mv_contable_subsanaciones AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'contable' AND trata_reporte = 'CONTABLE'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.descripcion, u.caratula, u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    a.nombre_tipo_actividad           AS tipo_subsanacion,
    a.fecha_alta                      AS fecha_apertura_subsanacion,
    (CURRENT_DATE - a.fecha_alta::date)                       AS dias_subsanacion_abierta,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_contable_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvc_sub_exp ON mv_contable_subsanaciones(id_expediente);
CREATE INDEX idx_mvc_sub_analista ON mv_contable_subsanaciones(analista);
CREATE INDEX idx_mvc_sub_trata ON mv_contable_subsanaciones(trata);


SELECT COUNT(*) AS total_subsanaciones FROM mv_contable_subsanaciones;

-- --- FIN: contable/04_contable_subsanaciones.sql ---

-- --- INICIO: etapa_proyecto/04_etapa_proyecto_subsanaciones.sql ---
-- ============================================================
-- ARCHIVO 04: mv_etapa_proyecto_subsanaciones
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_subsanaciones CASCADE;
DROP TYPE IF EXISTS mv_etapa_proyecto_subsanaciones CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_subsanaciones AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'etapa_proyecto' AND trata_reporte = 'ETAPA PROYECTO'
)
SELECT
    u.id_expediente,
    u.expediente,
    u.trata,
    u.descripcion_trata,
    u.descripcion,
    u.caratula,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_etapa_proyecto_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvep_subs_exp ON mv_etapa_proyecto_subsanaciones(id_expediente);

-- --- FIN: etapa_proyecto/04_etapa_proyecto_subsanaciones.sql ---

-- --- INICIO: aviso_obra/04_aviso_obra_subsanaciones.sql ---
-- ============================================================
-- ARCHIVO 04: mv_aviso_obra_subsanaciones
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_subsanaciones CASCADE;
DROP TYPE IF EXISTS mv_aviso_obra_subsanaciones CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_subsanaciones AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aviso_obra' AND trata_reporte = 'AVISO DE OBRA'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_aviso_obra_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvao_subs_exp ON mv_aviso_obra_subsanaciones(id_expediente);

-- --- FIN: aviso_obra/04_aviso_obra_subsanaciones.sql ---

-- --- INICIO: morfologia/04_morfologia_subsanaciones.sql ---
-- ============================================================
-- ARCHIVO 04: mv_morfologia_subsanaciones
-- ============================================================
-- PROPÓSITO: Expedientes propios actualmente en mano de analista,
-- CON actividad SOLICITUD_SUBSANACION_TAD abierta de ese mismo analista.
-- ORDEN DE EJECUCIÓN: 5°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_subsanaciones CASCADE;
DROP TYPE IF EXISTS mv_morfologia_subsanaciones CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_subsanaciones AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
)
SELECT
    u.id_expediente,
    u.expediente,
    u.trata,
    u.descripcion_trata,
    u.descripcion,
    u.caratula,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    a.nombre_tipo_actividad           AS tipo_subsanacion,
    a.fecha_alta                      AS fecha_apertura_subsanacion,
    (CURRENT_DATE - a.fecha_alta::date)                       AS dias_subsanacion_abierta,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_morfologia_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvm_sub_exp ON mv_morfologia_subsanaciones(id_expediente);
CREATE INDEX idx_mvm_sub_analista ON mv_morfologia_subsanaciones(analista);
CREATE INDEX idx_mvm_sub_trata ON mv_morfologia_subsanaciones(trata);


-- Validación
SELECT COUNT(*) AS total_subsanaciones FROM mv_morfologia_subsanaciones;

-- --- FIN: morfologia/04_morfologia_subsanaciones.sql ---

-- --- INICIO: aph/04_aph_subsanaciones.sql ---
-- ============================================================
-- ARCHIVO 04: mv_aph_subsanaciones
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_subsanaciones CASCADE;
DROP TYPE IF EXISTS mv_aph_subsanaciones CASCADE;

CREATE MATERIALIZED VIEW mv_aph_subsanaciones AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aph' AND trata_reporte = 'APH'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_aph_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvaph_subs_exp ON mv_aph_subsanaciones(id_expediente);

-- --- FIN: aph/04_aph_subsanaciones.sql ---

-- --- INICIO: usos/04_usos_subsanaciones.sql ---
-- ============================================================
-- ARCHIVO 04: mv_usos_subsanaciones
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_subsanaciones CASCADE;
DROP TYPE IF EXISTS mv_usos_subsanaciones CASCADE;

CREATE MATERIALIZED VIEW mv_usos_subsanaciones AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos' AND trata_reporte = 'USOS'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual,
    (CURRENT_DATE - u.fecha_primer_ingreso_gerencia::date)    AS dias_en_gerencia
FROM mv_usos_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = TRUE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvusos_subs_exp ON mv_usos_subsanaciones(id_expediente);

-- --- FIN: usos/04_usos_subsanaciones.sql ---

-- ============================================================
-- ETAPA DE COMPILACIÓN: 05
-- ============================================================

-- --- INICIO: catastro/05_catastro_egresos_efectivos.sql ---
-- ============================================================
-- ARCHIVO 05: mv_catastro_egresos_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_egresos_efectivos CASCADE;
DROP TYPE IF EXISTS mv_catastro_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_egresos_efectivos AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'catastro' AND trata_reporte = 'CATASTRO'
),
egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_catastro_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo = ANY(cfg.acronimos_egreso)
    WHERE u.es_trata_propia = TRUE
      AND (cfg.firmantes_egreso IS NULL OR d.usuario_creador = ANY(cfg.firmantes_egreso))
)
SELECT 
    id_expediente, expediente, trata,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvct_eef_exp ON mv_catastro_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvct_egref_fecha ON mv_catastro_egresos_efectivos(fecha_egreso);

-- --- FIN: catastro/05_catastro_egresos_efectivos.sql ---

-- --- INICIO: instalaciones/05_instalaciones_egresos_efectivos.sql ---
-- ============================================================
-- ARCHIVO 05: mv_instalaciones_egresos_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_egresos_efectivos CASCADE;
DROP TYPE IF EXISTS mv_instalaciones_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_egresos_efectivos AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'instalaciones' AND trata_reporte = 'INSTALACIONES'
),
egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_instalaciones_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo = ANY(cfg.acronimos_egreso)
    WHERE u.es_trata_propia = TRUE
      AND (cfg.firmantes_egreso IS NULL OR d.usuario_creador = ANY(cfg.firmantes_egreso))
)
SELECT 
    id_expediente, expediente, trata,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvins_eef_exp ON mv_instalaciones_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvins_egref_fecha ON mv_instalaciones_egresos_efectivos(fecha_egreso);

-- --- FIN: instalaciones/05_instalaciones_egresos_efectivos.sql ---

-- --- INICIO: regularizacion/05_regularizacion_egresos_efectivos.sql ---
-- ============================================================
-- ARCHIVO 05: mv_regularizacion_egresos_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_egresos_efectivos CASCADE;
DROP TYPE IF EXISTS mv_regularizacion_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_egresos_efectivos AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME'
),
egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_regularizacion_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo = ANY(cfg.acronimos_egreso)
    WHERE u.es_trata_propia = TRUE
      -- Filtro especial para MDUG3001A: Solo IFPCO y expedientes anteriores al 2026
      AND (
          (u.trata = 'MDUG3001A' AND d.acronimo = 'IFPCO' AND EXTRACT(YEAR FROM u.fecha_creacion_ee) < 2026)
          OR
          (u.trata = 'MDUG0104A' AND d.acronimo = 'IFROC')
          OR
          (u.trata = 'MDUG0141A' AND d.acronimo IN ('IFPCO', 'IFSMI'))
          OR
          (u.trata = 'MDUG1501K' AND d.acronimo = 'IFPDO')
      )
      AND (cfg.firmantes_egreso IS NULL OR d.usuario_creador = ANY(cfg.firmantes_egreso))
)
SELECT 
    id_expediente, expediente, trata,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvreg_eef_exp ON mv_regularizacion_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvreg_egref_fecha ON mv_regularizacion_egresos_efectivos(fecha_egreso);

-- --- FIN: regularizacion/05_regularizacion_egresos_efectivos.sql ---

-- --- INICIO: contable/05_contable_egresos_efectivos.sql ---
-- ============================================================
-- CONTABLE 05: mv_contable_egresos_efectivos
-- ============================================================
-- PROPÓSITO: Un GEDO de egreso por expediente (el más antiguo válido).
-- Usa cfg_egresos_por_trata para reglas por (trata, acrónimo, firmante).
--
-- Reglas particulares de Contable:
--   - MDUG0901A: IF firmado SOLO por FABIANSANTILLAN o LICETB.
--   - MDUG1501J: IFPDO.
--   - MDUG3001A: IFPDO.
--   - MDUG3402A: IFPEO o IFPDO.
--
-- ORDEN DE EJECUCIÓN: 6°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_egresos_efectivos CASCADE;
DROP TYPE IF EXISTS mv_contable_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_contable_egresos_efectivos AS
WITH egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
        u.descripcion, u.caratula, u.fecha_primer_ingreso_gerencia,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_contable_universo u
    INNER JOIN cfg_egresos_por_trata cep 
        ON cep.gerencia = 'contable'
       AND cep.trata    = u.trata
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo      = cep.acronimo
       AND (cep.firmantes IS NULL OR d.usuario_creador = ANY(cep.firmantes))
       AND (cep.fecha_desde IS NULL OR d.fecha_creacion::date >= cep.fecha_desde)
       AND (cep.fecha_hasta IS NULL OR d.fecha_creacion::date <= cep.fecha_hasta)
    WHERE u.es_trata_propia = TRUE
)
SELECT 
    id_expediente, expediente, trata, descripcion_trata, descripcion, caratula,
    fecha_primer_ingreso_gerencia,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso,
    (fecha_egreso::date - fecha_primer_ingreso_gerencia::date) AS dias_tramitacion
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvc_eef_exp ON mv_contable_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvc_eef_fecha ON mv_contable_egresos_efectivos(fecha_egreso);
CREATE INDEX idx_mvc_eef_trata ON mv_contable_egresos_efectivos(trata);
CREATE INDEX idx_mvc_eef_acro ON mv_contable_egresos_efectivos(acronimo_egreso);


SELECT 
    trata,
    COUNT(*) AS cant
FROM mv_contable_egresos_efectivos
GROUP BY trata
ORDER BY cant DESC;

-- --- FIN: contable/05_contable_egresos_efectivos.sql ---

-- --- INICIO: etapa_proyecto/05_etapa_proyecto_egresos_efectivos.sql ---
-- ============================================================
-- ARCHIVO 05: mv_etapa_proyecto_egresos_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_egresos_efectivos CASCADE;
DROP TYPE IF EXISTS mv_etapa_proyecto_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_egresos_efectivos AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'etapa_proyecto' AND trata_reporte = 'ETAPA PROYECTO'
),
egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_etapa_proyecto_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo = ANY(cfg.acronimos_egreso)
    WHERE u.es_trata_propia = TRUE
      AND (cfg.firmantes_egreso IS NULL OR d.usuario_creador = ANY(cfg.firmantes_egreso))
)
SELECT 
    id_expediente, expediente, trata,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvep_eef_exp ON mv_etapa_proyecto_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvep_egref_fecha ON mv_etapa_proyecto_egresos_efectivos(fecha_egreso);

-- --- FIN: etapa_proyecto/05_etapa_proyecto_egresos_efectivos.sql ---

-- --- INICIO: aviso_obra/05_aviso_obra_egresos_efectivos.sql ---
-- ============================================================
-- ARCHIVO 05: mv_aviso_obra_egresos_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_egresos_efectivos CASCADE;
DROP TYPE IF EXISTS mv_aviso_obra_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_egresos_efectivos AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'aviso_obra' AND trata_reporte = 'AVISO DE OBRA'
),
egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_aviso_obra_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo = ANY(cfg.acronimos_egreso)
    WHERE u.es_trata_propia = TRUE
      AND (cfg.firmantes_egreso IS NULL OR d.usuario_creador = ANY(cfg.firmantes_egreso))
)
SELECT 
    id_expediente, expediente, trata,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvao_eef_exp ON mv_aviso_obra_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvao_egref_fecha ON mv_aviso_obra_egresos_efectivos(fecha_egreso);

-- --- FIN: aviso_obra/05_aviso_obra_egresos_efectivos.sql ---

-- --- INICIO: morfologia/05_morfologia_egresos_efectivos.sql ---
-- ============================================================
-- ARCHIVO 05: mv_morfologia_egresos_efectivos
-- ============================================================
-- PROPÓSITO: Un GEDO de egreso por expediente (el más antiguo).
-- Lógica: DI, ANEXO o IF firmado por ALANDAZURI.
-- DIFERENCIA vs Instalaciones: filtra por firmante (no solo por acrónimo).
-- ORDEN DE EJECUCIÓN: 6°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_egresos_efectivos CASCADE;
DROP TYPE IF EXISTS mv_morfologia_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_egresos_efectivos AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
),
egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
        u.descripcion, u.caratula, u.fecha_primer_ingreso_gerencia,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_morfologia_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo = ANY(cfg.acronimos_egreso)
       AND d.usuario_creador = ANY(cfg.firmantes_egreso)
    WHERE u.es_trata_propia = TRUE
)
SELECT 
    id_expediente, expediente, trata, descripcion_trata, descripcion, caratula,
    fecha_primer_ingreso_gerencia,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso,
    (fecha_egreso::date - fecha_primer_ingreso_gerencia::date) AS dias_tramitacion
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvm_eef_exp ON mv_morfologia_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvm_eef_fecha ON mv_morfologia_egresos_efectivos(fecha_egreso);
CREATE INDEX idx_mvm_eef_trata ON mv_morfologia_egresos_efectivos(trata);
CREATE INDEX idx_mvm_eef_acro ON mv_morfologia_egresos_efectivos(acronimo_egreso);


-- Validación
SELECT COUNT(*) AS total_egresos_efectivos FROM mv_morfologia_egresos_efectivos;

-- --- FIN: morfologia/05_morfologia_egresos_efectivos.sql ---

-- --- INICIO: aph/05_aph_egresos_efectivos.sql ---
-- ============================================================
-- ARCHIVO 05: mv_aph_egresos_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_egresos_efectivos CASCADE;
DROP TYPE IF EXISTS mv_aph_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_aph_egresos_efectivos AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'aph' AND trata_reporte = 'APH'
),
egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_aph_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo = ANY(cfg.acronimos_egreso)
    WHERE u.es_trata_propia = TRUE
      AND (cfg.firmantes_egreso IS NULL OR d.usuario_creador = ANY(cfg.firmantes_egreso))
)
SELECT 
    id_expediente, expediente, trata,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvaph_eef_exp ON mv_aph_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvaph_egref_fecha ON mv_aph_egresos_efectivos(fecha_egreso);

-- --- FIN: aph/05_aph_egresos_efectivos.sql ---

-- --- INICIO: usos/05_usos_egresos_efectivos.sql ---
-- ============================================================
-- ARCHIVO 05: mv_usos_egresos_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_egresos_efectivos CASCADE;
DROP TYPE IF EXISTS mv_usos_egresos_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_usos_egresos_efectivos AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos' AND trata_reporte = 'USOS'
),
egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_usos_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo = ANY(cfg.acronimos_egreso)
    WHERE u.es_trata_propia = TRUE
      AND (cfg.firmantes_egreso IS NULL OR d.usuario_creador = ANY(cfg.firmantes_egreso))
)
SELECT 
    id_expediente, expediente, trata,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvusos_eef_exp ON mv_usos_egresos_efectivos(id_expediente);
CREATE INDEX idx_mvusos_egref_fecha ON mv_usos_egresos_efectivos(fecha_egreso);

-- --- FIN: usos/05_usos_egresos_efectivos.sql ---

-- ============================================================
-- ETAPA DE COMPILACIÓN: 06
-- ============================================================

-- --- INICIO: catastro/06_catastro_gedos_egreso.sql ---
-- ============================================================
-- ARCHIVO 06: mv_catastro_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_gedos_egreso CASCADE;
DROP TYPE IF EXISTS mv_catastro_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_gedos_egreso AS
SELECT 
    id_expediente,
    expediente,
    trata,
    fecha_egreso
FROM mv_catastro_egresos_efectivos;

CREATE INDEX idx_mvct_gedos_egr_fecha ON mv_catastro_gedos_egreso(fecha_egreso);

-- --- FIN: catastro/06_catastro_gedos_egreso.sql ---

-- --- INICIO: instalaciones/06_instalaciones_gedos_egreso.sql ---
-- ============================================================
-- ARCHIVO 06: mv_instalaciones_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_gedos_egreso CASCADE;
DROP TYPE IF EXISTS mv_instalaciones_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_gedos_egreso AS
SELECT 
    id_expediente, expediente, trata, fecha_egreso
FROM mv_instalaciones_egresos_efectivos;

CREATE INDEX idx_mvins_gedos_egr_fecha ON mv_instalaciones_gedos_egreso(fecha_egreso);

-- --- FIN: instalaciones/06_instalaciones_gedos_egreso.sql ---

-- --- INICIO: regularizacion/06_regularizacion_gedos_egreso.sql ---
-- ============================================================
-- ARCHIVO 06: mv_regularizacion_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_gedos_egreso CASCADE;
DROP TYPE IF EXISTS mv_regularizacion_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_gedos_egreso AS
SELECT 
    id_expediente, expediente, trata, fecha_egreso
FROM mv_regularizacion_egresos_efectivos;

CREATE INDEX idx_mvreg_gedos_egr_fecha ON mv_regularizacion_gedos_egreso(fecha_egreso);

-- --- FIN: regularizacion/06_regularizacion_gedos_egreso.sql ---

-- --- INICIO: contable/06_contable_gedos_egreso.sql ---
-- ============================================================
-- CONTABLE 06: mv_contable_gedos_egreso
-- ============================================================
-- PROPÓSITO: Todos los GEDOs de egreso válidos (cada evento).
-- Útil para reportes mensuales.
-- ORDEN DE EJECUCIÓN: 7°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_gedos_egreso CASCADE;
DROP TYPE IF EXISTS mv_contable_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_contable_gedos_egreso AS
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    d.documento           AS documento_egreso,
    d.acronimo            AS acronimo_egreso,
    d.fecha_creacion      AS fecha_egreso,
    d.usuario_creador     AS usuario_egreso
FROM mv_contable_universo u
INNER JOIN cfg_egresos_por_trata cep 
    ON cep.gerencia = 'contable'
   AND cep.trata    = u.trata
INNER JOIN mvw_datos_gedo_secgdu d 
    ON d.id_expediente = u.id_expediente
   AND d.acronimo      = cep.acronimo
   AND (cep.firmantes IS NULL OR d.usuario_creador = ANY(cep.firmantes))
   AND (cep.fecha_desde IS NULL OR d.fecha_creacion::date >= cep.fecha_desde)
   AND (cep.fecha_hasta IS NULL OR d.fecha_creacion::date <= cep.fecha_hasta)
WHERE u.es_trata_propia = TRUE;

CREATE INDEX idx_mvc_geg_exp ON mv_contable_gedos_egreso(id_expediente);
CREATE INDEX idx_mvc_geg_fecha ON mv_contable_gedos_egreso(fecha_egreso);
CREATE INDEX idx_mvc_geg_trata ON mv_contable_gedos_egreso(trata);
CREATE INDEX idx_mvc_geg_acro ON mv_contable_gedos_egreso(acronimo_egreso);


-- Validación: distribución por acrónimo y firmante
SELECT 
    trata,
    acronimo_egreso,
    usuario_egreso,
    COUNT(*) AS cant
FROM mv_contable_gedos_egreso
GROUP BY trata, acronimo_egreso, usuario_egreso
ORDER BY cant DESC
LIMIT 30;

-- Verificación importante: para MDUG0901A, solo deben aparecer FABIANSANTILLAN y LICETB
SELECT 
    usuario_egreso,
    COUNT(*) AS cant
FROM mv_contable_gedos_egreso
WHERE trata = 'MDUG0901A'
GROUP BY usuario_egreso
ORDER BY cant DESC;

-- --- FIN: contable/06_contable_gedos_egreso.sql ---

-- --- INICIO: etapa_proyecto/06_etapa_proyecto_gedos_egreso.sql ---
-- ============================================================
-- ARCHIVO 06: mv_etapa_proyecto_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_gedos_egreso CASCADE;
DROP TYPE IF EXISTS mv_etapa_proyecto_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_gedos_egreso AS
SELECT 
    id_expediente,
    expediente,
    trata,
    fecha_egreso
FROM mv_etapa_proyecto_egresos_efectivos;

CREATE INDEX idx_mvep_gedos_egr_fecha ON mv_etapa_proyecto_gedos_egreso(fecha_egreso);

-- --- FIN: etapa_proyecto/06_etapa_proyecto_gedos_egreso.sql ---

-- --- INICIO: aviso_obra/06_aviso_obra_gedos_egreso.sql ---
-- ============================================================
-- ARCHIVO 06: mv_aviso_obra_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_gedos_egreso CASCADE;
DROP TYPE IF EXISTS mv_aviso_obra_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_gedos_egreso AS
SELECT 
    id_expediente, expediente, trata, fecha_egreso
FROM mv_aviso_obra_egresos_efectivos;

CREATE INDEX idx_mvao_gedos_egr_fecha ON mv_aviso_obra_gedos_egreso(fecha_egreso);

-- --- FIN: aviso_obra/06_aviso_obra_gedos_egreso.sql ---

-- --- INICIO: morfologia/06_morfologia_gedos_egreso.sql ---
-- ============================================================
-- ARCHIVO 06: mv_morfologia_gedos_egreso
-- ============================================================
-- PROPÓSITO: Listar TODOS los GEDOs de egreso firmados (cada evento).
-- Útil para reportes mensuales de flujo.
-- ORDEN DE EJECUCIÓN: 7°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_gedos_egreso CASCADE;
DROP TYPE IF EXISTS mv_morfologia_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_gedos_egreso AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    d.documento           AS documento_egreso,
    d.acronimo            AS acronimo_egreso,
    d.fecha_creacion      AS fecha_egreso,
    d.usuario_creador     AS usuario_egreso
FROM mv_morfologia_universo u
CROSS JOIN cfg
INNER JOIN mvw_datos_gedo_secgdu d 
    ON d.id_expediente = u.id_expediente
   AND d.acronimo = ANY(cfg.acronimos_egreso)
   AND d.usuario_creador = ANY(cfg.firmantes_egreso)
WHERE u.es_trata_propia = TRUE;

CREATE INDEX idx_mvm_geg_exp ON mv_morfologia_gedos_egreso(id_expediente);
CREATE INDEX idx_mvm_geg_fecha ON mv_morfologia_gedos_egreso(fecha_egreso);
CREATE INDEX idx_mvm_geg_trata ON mv_morfologia_gedos_egreso(trata);
CREATE INDEX idx_mvm_geg_acro ON mv_morfologia_gedos_egreso(acronimo_egreso);


-- Validación
SELECT 
    acronimo_egreso,
    COUNT(*) AS cant
FROM mv_morfologia_gedos_egreso
GROUP BY acronimo_egreso
ORDER BY cant DESC;

-- --- FIN: morfologia/06_morfologia_gedos_egreso.sql ---

-- --- INICIO: aph/06_aph_gedos_egreso.sql ---
-- ============================================================
-- ARCHIVO 06: mv_aph_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_gedos_egreso CASCADE;
DROP TYPE IF EXISTS mv_aph_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_aph_gedos_egreso AS
SELECT 
    id_expediente, expediente, trata, fecha_egreso
FROM mv_aph_egresos_efectivos;

CREATE INDEX idx_mvaph_gedos_egr_fecha ON mv_aph_gedos_egreso(fecha_egreso);

-- --- FIN: aph/06_aph_gedos_egreso.sql ---

-- --- INICIO: usos/06_usos_gedos_egreso.sql ---
-- ============================================================
-- ARCHIVO 06: mv_usos_gedos_egreso
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_gedos_egreso CASCADE;
DROP TYPE IF EXISTS mv_usos_gedos_egreso CASCADE;

CREATE MATERIALIZED VIEW mv_usos_gedos_egreso AS
SELECT 
    id_expediente, expediente, trata, fecha_egreso
FROM mv_usos_egresos_efectivos;

CREATE INDEX idx_mvusos_gedos_egr_fecha ON mv_usos_gedos_egreso(fecha_egreso);

-- --- FIN: usos/06_usos_gedos_egreso.sql ---

-- ============================================================
-- ETAPA DE COMPILACIÓN: 07
-- ============================================================

-- --- INICIO: catastro/07_catastro_egresos_no_efectivos.sql ---
-- ============================================================
-- ARCHIVO 07: mv_catastro_egresos_no_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_egresos_no_efectivos CASCADE;
DROP TYPE IF EXISTS mv_catastro_egresos_no_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_egresos_no_efectivos AS
SELECT
    u.id_expediente, u.expediente, u.trata,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.fecha_ultimo_pase                                                AS fecha_ultimo_movimiento,
    up.destinatario_actual                                              AS poseedor_actual
FROM mv_catastro_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
LEFT JOIN mv_catastro_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
WHERE u.es_trata_propia = TRUE
  AND u.estado_expediente = 'Guarda Temporal'
  AND eef.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvct_ene_exp ON mv_catastro_egresos_no_efectivos(id_expediente);
CREATE INDEX idx_mvct_egrne_fecha ON mv_catastro_egresos_no_efectivos(fecha_ultimo_movimiento);

-- --- FIN: catastro/07_catastro_egresos_no_efectivos.sql ---

-- --- INICIO: instalaciones/07_instalaciones_egresos_no_efectivos.sql ---
-- ============================================================
-- ARCHIVO 07: mv_instalaciones_egresos_no_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_egresos_no_efectivos CASCADE;
DROP TYPE IF EXISTS mv_instalaciones_egresos_no_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_egresos_no_efectivos AS
SELECT
    u.id_expediente, u.expediente, u.trata, u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.fecha_ultimo_pase AS fecha_ultimo_movimiento,
    up.destinatario_actual AS poseedor_actual
FROM mv_instalaciones_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
LEFT JOIN mv_instalaciones_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
WHERE u.es_trata_propia = TRUE
  AND u.estado_expediente = 'Guarda Temporal'
  AND eef.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvins_ene_exp ON mv_instalaciones_egresos_no_efectivos(id_expediente);
CREATE INDEX idx_mvins_egrne_fecha ON mv_instalaciones_egresos_no_efectivos(fecha_ultimo_movimiento);

-- --- FIN: instalaciones/07_instalaciones_egresos_no_efectivos.sql ---

-- --- INICIO: regularizacion/07_regularizacion_egresos_no_efectivos.sql ---
-- ============================================================
-- ARCHIVO 07: mv_regularizacion_egresos_no_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_egresos_no_efectivos CASCADE;
DROP TYPE IF EXISTS mv_regularizacion_egresos_no_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_egresos_no_efectivos AS
SELECT
    u.id_expediente, u.expediente, u.trata, u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.fecha_ultimo_pase AS fecha_ultimo_movimiento,
    up.destinatario_actual AS poseedor_actual
FROM mv_regularizacion_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
LEFT JOIN mv_regularizacion_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
WHERE u.es_trata_propia = TRUE
  AND u.estado_expediente = 'Guarda Temporal'
  AND eef.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvreg_ene_exp ON mv_regularizacion_egresos_no_efectivos(id_expediente);
CREATE INDEX idx_mvreg_egrne_fecha ON mv_regularizacion_egresos_no_efectivos(fecha_ultimo_movimiento);

-- --- FIN: regularizacion/07_regularizacion_egresos_no_efectivos.sql ---

-- --- INICIO: contable/07_contable_egresos_no_efectivos.sql ---
-- ============================================================
-- CONTABLE 07: mv_contable_egresos_no_efectivos
-- ============================================================
-- ORDEN DE EJECUCIÓN: 8°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_egresos_no_efectivos CASCADE;
DROP TYPE IF EXISTS mv_contable_egresos_no_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_contable_egresos_no_efectivos AS
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.descripcion, u.caratula, u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.fecha_ultimo_pase                                                AS fecha_ultimo_movimiento,
    up.destinatario_actual                                              AS poseedor_actual,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)                         AS dias_desde_guarda,
    (up.fecha_ultimo_pase::date - u.fecha_primer_ingreso_gerencia::date) AS dias_tramitacion_aprox
FROM mv_contable_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
LEFT JOIN mv_contable_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
WHERE u.es_trata_propia = TRUE
  AND u.estado_expediente = 'Guarda Temporal'
  AND eef.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvc_ene_exp ON mv_contable_egresos_no_efectivos(id_expediente);
CREATE INDEX idx_mvc_ene_trata ON mv_contable_egresos_no_efectivos(trata);
CREATE INDEX idx_mvc_ene_fecha ON mv_contable_egresos_no_efectivos(fecha_ultimo_movimiento);


SELECT COUNT(*) AS total_egresos_no_efectivos FROM mv_contable_egresos_no_efectivos;

-- --- FIN: contable/07_contable_egresos_no_efectivos.sql ---

-- --- INICIO: etapa_proyecto/07_etapa_proyecto_egresos_no_efectivos.sql ---
-- ============================================================
-- ARCHIVO 07: mv_etapa_proyecto_egresos_no_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_egresos_no_efectivos CASCADE;
DROP TYPE IF EXISTS mv_etapa_proyecto_egresos_no_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_egresos_no_efectivos AS
SELECT
    u.id_expediente, u.expediente, u.trata,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.fecha_ultimo_pase                                                AS fecha_ultimo_movimiento,
    up.destinatario_actual                                              AS poseedor_actual
FROM mv_etapa_proyecto_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
LEFT JOIN mv_etapa_proyecto_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
WHERE u.es_trata_propia = TRUE
  AND u.estado_expediente = 'Guarda Temporal'
  AND eef.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvep_ene_exp ON mv_etapa_proyecto_egresos_no_efectivos(id_expediente);
CREATE INDEX idx_mvep_egrne_fecha ON mv_etapa_proyecto_egresos_no_efectivos(fecha_ultimo_movimiento);

-- --- FIN: etapa_proyecto/07_etapa_proyecto_egresos_no_efectivos.sql ---

-- --- INICIO: aviso_obra/07_aviso_obra_egresos_no_efectivos.sql ---
-- ============================================================
-- ARCHIVO 07: mv_aviso_obra_egresos_no_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_egresos_no_efectivos CASCADE;
DROP TYPE IF EXISTS mv_aviso_obra_egresos_no_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_egresos_no_efectivos AS
SELECT
    u.id_expediente, u.expediente, u.trata, u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.fecha_ultimo_pase AS fecha_ultimo_movimiento,
    up.destinatario_actual AS poseedor_actual
FROM mv_aviso_obra_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
LEFT JOIN mv_aviso_obra_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
WHERE u.es_trata_propia = TRUE
  AND u.estado_expediente = 'Guarda Temporal'
  AND eef.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvao_ene_exp ON mv_aviso_obra_egresos_no_efectivos(id_expediente);
CREATE INDEX idx_mvao_egrne_fecha ON mv_aviso_obra_egresos_no_efectivos(fecha_ultimo_movimiento);

-- --- FIN: aviso_obra/07_aviso_obra_egresos_no_efectivos.sql ---

-- --- INICIO: morfologia/07_morfologia_egresos_no_efectivos.sql ---
-- ============================================================
-- ARCHIVO 07: mv_morfologia_egresos_no_efectivos
-- ============================================================
-- PROPÓSITO: Expedientes propios en Guarda Temporal sin egreso efectivo.
-- ORDEN DE EJECUCIÓN: 8°.
-- DEPENDE de mv_morfologia_egresos_efectivos.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_egresos_no_efectivos CASCADE;
DROP TYPE IF EXISTS mv_morfologia_egresos_no_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_egresos_no_efectivos AS
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.descripcion, u.caratula, u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.fecha_ultimo_pase                                                AS fecha_ultimo_movimiento,
    up.destinatario_actual                                              AS poseedor_actual,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)                         AS dias_desde_guarda,
    (up.fecha_ultimo_pase::date - u.fecha_primer_ingreso_gerencia::date) AS dias_tramitacion_aprox
FROM mv_morfologia_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
LEFT JOIN mv_morfologia_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
WHERE u.es_trata_propia = TRUE
  AND u.estado_expediente = 'Guarda Temporal'
  AND eef.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvm_ene_exp ON mv_morfologia_egresos_no_efectivos(id_expediente);
CREATE INDEX idx_mvm_ene_trata ON mv_morfologia_egresos_no_efectivos(trata);
CREATE INDEX idx_mvm_ene_fecha ON mv_morfologia_egresos_no_efectivos(fecha_ultimo_movimiento);


-- Validación
SELECT COUNT(*) AS total_egresos_no_efectivos FROM mv_morfologia_egresos_no_efectivos;

-- --- FIN: morfologia/07_morfologia_egresos_no_efectivos.sql ---

-- --- INICIO: aph/07_aph_egresos_no_efectivos.sql ---
-- ============================================================
-- ARCHIVO 07: mv_aph_egresos_no_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_egresos_no_efectivos CASCADE;
DROP TYPE IF EXISTS mv_aph_egresos_no_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_aph_egresos_no_efectivos AS
SELECT
    u.id_expediente, u.expediente, u.trata, u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.fecha_ultimo_pase AS fecha_ultimo_movimiento,
    up.destinatario_actual AS poseedor_actual
FROM mv_aph_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
LEFT JOIN mv_aph_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
WHERE u.es_trata_propia = TRUE
  AND u.estado_expediente = 'Guarda Temporal'
  AND eef.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvaph_ene_exp ON mv_aph_egresos_no_efectivos(id_expediente);
CREATE INDEX idx_mvaph_egrne_fecha ON mv_aph_egresos_no_efectivos(fecha_ultimo_movimiento);

-- --- FIN: aph/07_aph_egresos_no_efectivos.sql ---

-- --- INICIO: usos/07_usos_egresos_no_efectivos.sql ---
-- ============================================================
-- ARCHIVO 07: mv_usos_egresos_no_efectivos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_egresos_no_efectivos CASCADE;
DROP TYPE IF EXISTS mv_usos_egresos_no_efectivos CASCADE;

CREATE MATERIALIZED VIEW mv_usos_egresos_no_efectivos AS
SELECT
    u.id_expediente, u.expediente, u.trata, u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.fecha_ultimo_pase AS fecha_ultimo_movimiento,
    up.destinatario_actual AS poseedor_actual
FROM mv_usos_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
LEFT JOIN mv_usos_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
WHERE u.es_trata_propia = TRUE
  AND u.estado_expediente = 'Guarda Temporal'
  AND eef.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvusos_ene_exp ON mv_usos_egresos_no_efectivos(id_expediente);
CREATE INDEX idx_mvusos_egrne_fecha ON mv_usos_egresos_no_efectivos(fecha_ultimo_movimiento);

-- --- FIN: usos/07_usos_egresos_no_efectivos.sql ---

-- ============================================================
-- ETAPA DE COMPILACIÓN: 08
-- ============================================================

-- --- INICIO: catastro/08_catastro_intervenciones_stock.sql ---
-- ============================================================
-- ARCHIVO 08: mv_catastro_intervenciones_stock
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_intervenciones_stock CASCADE;
DROP TYPE IF EXISTS mv_catastro_intervenciones_stock CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_intervenciones_stock AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'catastro' AND trata_reporte = 'CATASTRO'
)
SELECT
    u.id_expediente,
    u.expediente,
    u.trata,
    u.descripcion_trata,
    u.descripcion,
    u.caratula,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_catastro_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvct_interv_stock_exp ON mv_catastro_intervenciones_stock(id_expediente);

-- --- FIN: catastro/08_catastro_intervenciones_stock.sql ---

-- --- INICIO: instalaciones/08_instalaciones_intervenciones_stock.sql ---
-- ============================================================
-- ARCHIVO 08: mv_instalaciones_intervenciones_stock
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_intervenciones_stock CASCADE;
DROP TYPE IF EXISTS mv_instalaciones_intervenciones_stock CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_intervenciones_stock AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'instalaciones' AND trata_reporte = 'INSTALACIONES'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_instalaciones_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvins_interv_stock_exp ON mv_instalaciones_intervenciones_stock(id_expediente);

-- --- FIN: instalaciones/08_instalaciones_intervenciones_stock.sql ---

-- --- INICIO: regularizacion/08_regularizacion_intervenciones_stock.sql ---
-- ============================================================
-- ARCHIVO 08: mv_regularizacion_intervenciones_stock
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_intervenciones_stock CASCADE;
DROP TYPE IF EXISTS mv_regularizacion_intervenciones_stock CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_intervenciones_stock AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_regularizacion_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvreg_interv_stock_exp ON mv_regularizacion_intervenciones_stock(id_expediente);

-- --- FIN: regularizacion/08_regularizacion_intervenciones_stock.sql ---

-- --- INICIO: contable/08_contable_intervenciones_stock.sql ---
-- ============================================================
-- CONTABLE 08: mv_contable_intervenciones_stock
-- ============================================================
-- ORDEN DE EJECUCIÓN: 9°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_intervenciones_stock CASCADE;
DROP TYPE IF EXISTS mv_contable_intervenciones_stock CASCADE;

CREATE MATERIALIZED VIEW mv_contable_intervenciones_stock AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'contable' AND trata_reporte = 'CONTABLE'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_en_poder_actual
FROM mv_contable_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvc_ist_exp ON mv_contable_intervenciones_stock(id_expediente);
CREATE INDEX idx_mvc_ist_analista ON mv_contable_intervenciones_stock(analista);
CREATE INDEX idx_mvc_ist_trata ON mv_contable_intervenciones_stock(trata);


SELECT COUNT(*) AS total_intervenciones_stock FROM mv_contable_intervenciones_stock;

-- --- FIN: contable/08_contable_intervenciones_stock.sql ---

-- --- INICIO: etapa_proyecto/08_etapa_proyecto_intervenciones_stock.sql ---
-- ============================================================
-- ARCHIVO 08: mv_etapa_proyecto_intervenciones_stock
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_intervenciones_stock CASCADE;
DROP TYPE IF EXISTS mv_etapa_proyecto_intervenciones_stock CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_intervenciones_stock AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'etapa_proyecto' AND trata_reporte = 'ETAPA PROYECTO'
)
SELECT
    u.id_expediente,
    u.expediente,
    u.trata,
    u.descripcion_trata,
    u.descripcion,
    u.caratula,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_etapa_proyecto_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvep_interv_stock_exp ON mv_etapa_proyecto_intervenciones_stock(id_expediente);

-- --- FIN: etapa_proyecto/08_etapa_proyecto_intervenciones_stock.sql ---

-- --- INICIO: aviso_obra/08_aviso_obra_intervenciones_stock.sql ---
-- ============================================================
-- ARCHIVO 08: mv_aviso_obra_intervenciones_stock
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_intervenciones_stock CASCADE;
DROP TYPE IF EXISTS mv_aviso_obra_intervenciones_stock CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_intervenciones_stock AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aviso_obra' AND trata_reporte = 'AVISO DE OBRA'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_aviso_obra_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvao_interv_stock_exp ON mv_aviso_obra_intervenciones_stock(id_expediente);

-- --- FIN: aviso_obra/08_aviso_obra_intervenciones_stock.sql ---

-- --- INICIO: morfologia/08_morfologia_intervenciones_stock.sql ---
-- ============================================================
-- ARCHIVO 08: mv_morfologia_intervenciones_stock
-- ============================================================
-- PROPÓSITO: Intervenciones actualmente en mano de analista,
-- sin actividad SOLICITUD_SUBSANACION_TAD abierta.
-- ORDEN DE EJECUCIÓN: 9°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_intervenciones_stock CASCADE;
DROP TYPE IF EXISTS mv_morfologia_intervenciones_stock CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_intervenciones_stock AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_en_poder_actual
FROM mv_morfologia_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvm_ist_exp ON mv_morfologia_intervenciones_stock(id_expediente);
CREATE INDEX idx_mvm_ist_analista ON mv_morfologia_intervenciones_stock(analista);
CREATE INDEX idx_mvm_ist_trata ON mv_morfologia_intervenciones_stock(trata);


-- Validación
SELECT COUNT(*) AS total_intervenciones_stock FROM mv_morfologia_intervenciones_stock;

-- --- FIN: morfologia/08_morfologia_intervenciones_stock.sql ---

-- --- INICIO: aph/08_aph_intervenciones_stock.sql ---
-- ============================================================
-- ARCHIVO 08: mv_aph_intervenciones_stock
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_intervenciones_stock CASCADE;
DROP TYPE IF EXISTS mv_aph_intervenciones_stock CASCADE;

CREATE MATERIALIZED VIEW mv_aph_intervenciones_stock AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aph' AND trata_reporte = 'APH'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_aph_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvaph_interv_stock_exp ON mv_aph_intervenciones_stock(id_expediente);

-- --- FIN: aph/08_aph_intervenciones_stock.sql ---

-- --- INICIO: usos/08_usos_intervenciones_stock.sql ---
-- ============================================================
-- ARCHIVO 08: mv_usos_intervenciones_stock
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_intervenciones_stock CASCADE;
DROP TYPE IF EXISTS mv_usos_intervenciones_stock CASCADE;

CREATE MATERIALIZED VIEW mv_usos_intervenciones_stock AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos' AND trata_reporte = 'USOS'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_usos_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
LEFT JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
  AND a.id_expediente IS NULL;

CREATE UNIQUE INDEX idx_mvusos_interv_stock_exp ON mv_usos_intervenciones_stock(id_expediente);

-- --- FIN: usos/08_usos_intervenciones_stock.sql ---

-- ============================================================
-- ETAPA DE COMPILACIÓN: 09
-- ============================================================

-- --- INICIO: catastro/09_catastro_intervenciones_subs.sql ---
-- ============================================================
-- ARCHIVO 09: mv_catastro_intervenciones_subs
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_intervenciones_subs CASCADE;
DROP TYPE IF EXISTS mv_catastro_intervenciones_subs CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_intervenciones_subs AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'catastro' AND trata_reporte = 'CATASTRO'
)
SELECT
    u.id_expediente,
    u.expediente,
    u.trata,
    u.descripcion_trata,
    u.descripcion,
    u.caratula,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_catastro_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvct_interv_subs_exp ON mv_catastro_intervenciones_subs(id_expediente);

-- --- FIN: catastro/09_catastro_intervenciones_subs.sql ---

-- --- INICIO: instalaciones/09_instalaciones_intervenciones_subs.sql ---
-- ============================================================
-- ARCHIVO 09: mv_instalaciones_intervenciones_subs
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_intervenciones_subs CASCADE;
DROP TYPE IF EXISTS mv_instalaciones_intervenciones_subs CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_intervenciones_subs AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'instalaciones' AND trata_reporte = 'INSTALACIONES'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_instalaciones_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvins_interv_subs_exp ON mv_instalaciones_intervenciones_subs(id_expediente);

-- --- FIN: instalaciones/09_instalaciones_intervenciones_subs.sql ---

-- --- INICIO: regularizacion/09_regularizacion_intervenciones_subs.sql ---
-- ============================================================
-- ARCHIVO 09: mv_regularizacion_intervenciones_subs
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_intervenciones_subs CASCADE;
DROP TYPE IF EXISTS mv_regularizacion_intervenciones_subs CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_intervenciones_subs AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_regularizacion_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvreg_interv_subs_exp ON mv_regularizacion_intervenciones_subs(id_expediente);

-- --- FIN: regularizacion/09_regularizacion_intervenciones_subs.sql ---

-- --- INICIO: contable/09_contable_intervenciones_subs.sql ---
-- ============================================================
-- CONTABLE 09: mv_contable_intervenciones_subs
-- ============================================================
-- ORDEN DE EJECUCIÓN: 10°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_intervenciones_subs CASCADE;
DROP TYPE IF EXISTS mv_contable_intervenciones_subs CASCADE;

CREATE MATERIALIZED VIEW mv_contable_intervenciones_subs AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'contable' AND trata_reporte = 'CONTABLE'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    a.nombre_tipo_actividad           AS tipo_subsanacion,
    a.fecha_alta                      AS fecha_apertura_subsanacion,
    (CURRENT_DATE - a.fecha_alta::date) AS dias_subsanacion_abierta
FROM mv_contable_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvc_isb_exp ON mv_contable_intervenciones_subs(id_expediente);
CREATE INDEX idx_mvc_isb_analista ON mv_contable_intervenciones_subs(analista);
CREATE INDEX idx_mvc_isb_trata ON mv_contable_intervenciones_subs(trata);


SELECT COUNT(*) AS total_intervenciones_subs FROM mv_contable_intervenciones_subs;

-- --- FIN: contable/09_contable_intervenciones_subs.sql ---

-- --- INICIO: etapa_proyecto/09_etapa_proyecto_intervenciones_subs.sql ---
-- ============================================================
-- ARCHIVO 09: mv_etapa_proyecto_intervenciones_subs
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_intervenciones_subs CASCADE;
DROP TYPE IF EXISTS mv_etapa_proyecto_intervenciones_subs CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_intervenciones_subs AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'etapa_proyecto' AND trata_reporte = 'ETAPA PROYECTO'
)
SELECT
    u.id_expediente,
    u.expediente,
    u.trata,
    u.descripcion_trata,
    u.descripcion,
    u.caratula,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_etapa_proyecto_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvep_interv_subs_exp ON mv_etapa_proyecto_intervenciones_subs(id_expediente);

-- --- FIN: etapa_proyecto/09_etapa_proyecto_intervenciones_subs.sql ---

-- --- INICIO: aviso_obra/09_aviso_obra_intervenciones_subs.sql ---
-- ============================================================
-- ARCHIVO 09: mv_aviso_obra_intervenciones_subs
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_intervenciones_subs CASCADE;
DROP TYPE IF EXISTS mv_aviso_obra_intervenciones_subs CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_intervenciones_subs AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aviso_obra' AND trata_reporte = 'AVISO DE OBRA'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_aviso_obra_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvao_interv_subs_exp ON mv_aviso_obra_intervenciones_subs(id_expediente);

-- --- FIN: aviso_obra/09_aviso_obra_intervenciones_subs.sql ---

-- --- INICIO: morfologia/09_morfologia_intervenciones_subs.sql ---
-- ============================================================
-- ARCHIVO 09: mv_morfologia_intervenciones_subs
-- ============================================================
-- PROPÓSITO: Intervenciones actualmente en mano de analista,
-- CON actividad SOLICITUD_SUBSANACION_TAD abierta.
-- ORDEN DE EJECUCIÓN: 10°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_intervenciones_subs CASCADE;
DROP TYPE IF EXISTS mv_morfologia_intervenciones_subs CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_intervenciones_subs AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    a.nombre_tipo_actividad           AS tipo_subsanacion,
    a.fecha_alta                      AS fecha_apertura_subsanacion,
    (CURRENT_DATE - a.fecha_alta::date) AS dias_subsanacion_abierta
FROM mv_morfologia_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvm_isb_exp ON mv_morfologia_intervenciones_subs(id_expediente);
CREATE INDEX idx_mvm_isb_analista ON mv_morfologia_intervenciones_subs(analista);
CREATE INDEX idx_mvm_isb_trata ON mv_morfologia_intervenciones_subs(trata);


-- Validación
SELECT COUNT(*) AS total_intervenciones_subs FROM mv_morfologia_intervenciones_subs;

-- --- FIN: morfologia/09_morfologia_intervenciones_subs.sql ---

-- --- INICIO: aph/09_aph_intervenciones_subs.sql ---
-- ============================================================
-- ARCHIVO 09: mv_aph_intervenciones_subs
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_intervenciones_subs CASCADE;
DROP TYPE IF EXISTS mv_aph_intervenciones_subs CASCADE;

CREATE MATERIALIZED VIEW mv_aph_intervenciones_subs AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aph' AND trata_reporte = 'APH'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_aph_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvaph_interv_subs_exp ON mv_aph_intervenciones_subs(id_expediente);

-- --- FIN: aph/09_aph_intervenciones_subs.sql ---

-- --- INICIO: usos/09_usos_intervenciones_subs.sql ---
-- ============================================================
-- ARCHIVO 09: mv_usos_intervenciones_subs
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_intervenciones_subs CASCADE;
DROP TYPE IF EXISTS mv_usos_intervenciones_subs CASCADE;

CREATE MATERIALIZED VIEW mv_usos_intervenciones_subs AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos' AND trata_reporte = 'USOS'
)
SELECT
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata, u.descripcion, u.caratula,
    u.estado_expediente, u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual            AS analista,
    up.fecha_ultimo_pase              AS fecha_recepcion_analista,
    (CURRENT_DATE - up.fecha_ultimo_pase::date)               AS dias_en_poder_actual
FROM mv_usos_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
INNER JOIN mv_ultima_actividad a 
    ON a.id_expediente = u.id_expediente
   AND a.usuario_alta = up.destinatario_actual
   AND a.estado_actividad = 'PENDIENTE'
   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
WHERE u.es_trata_propia = FALSE
  AND up.destinatario_actual = ANY(cfg.analistas_oficiales);

CREATE UNIQUE INDEX idx_mvusos_interv_subs_exp ON mv_usos_intervenciones_subs(id_expediente);

-- --- FIN: usos/09_usos_intervenciones_subs.sql ---

-- ============================================================
-- ETAPA DE COMPILACIÓN: 10
-- ============================================================

-- --- INICIO: catastro/10_catastro_intervenciones_egresadas.sql ---
-- ============================================================
-- ARCHIVO 10: mv_catastro_intervenciones_egresadas
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_intervenciones_egresadas CASCADE;
DROP TYPE IF EXISTS mv_catastro_intervenciones_egresadas CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_intervenciones_egresadas AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'catastro' AND trata_reporte = 'CATASTRO'
)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual           AS destino_actual,
    up.fecha_ultimo_pase             AS fecha_egreso,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_afuera
FROM mv_catastro_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.es_trata_propia = FALSE
  AND NOT (up.destinatario_actual = ANY(cfg.analistas_oficiales));

CREATE UNIQUE INDEX idx_mvct_ine_exp ON mv_catastro_intervenciones_egresadas(id_expediente);

-- --- FIN: catastro/10_catastro_intervenciones_egresadas.sql ---

-- --- INICIO: instalaciones/10_instalaciones_intervenciones_egresadas.sql ---
-- ============================================================
-- ARCHIVO 10: mv_instalaciones_intervenciones_egresadas
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_intervenciones_egresadas CASCADE;
DROP TYPE IF EXISTS mv_instalaciones_intervenciones_egresadas CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_intervenciones_egresadas AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'instalaciones' AND trata_reporte = 'INSTALACIONES'
)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual           AS destino_actual,
    up.fecha_ultimo_pase             AS fecha_egreso,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_afuera
FROM mv_instalaciones_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.es_trata_propia = FALSE
  AND NOT (up.destinatario_actual = ANY(cfg.analistas_oficiales));

CREATE UNIQUE INDEX idx_mvins_ine_exp ON mv_instalaciones_intervenciones_egresadas(id_expediente);

-- --- FIN: instalaciones/10_instalaciones_intervenciones_egresadas.sql ---

-- --- INICIO: regularizacion/10_regularizacion_intervenciones_egresadas.sql ---
-- ============================================================
-- ARCHIVO 10: mv_regularizacion_intervenciones_egresadas
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_intervenciones_egresadas CASCADE;
DROP TYPE IF EXISTS mv_regularizacion_intervenciones_egresadas CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_intervenciones_egresadas AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME'
)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual           AS destino_actual,
    up.fecha_ultimo_pase             AS fecha_egreso,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_afuera
FROM mv_regularizacion_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.es_trata_propia = FALSE
  AND NOT (up.destinatario_actual = ANY(cfg.analistas_oficiales));

CREATE UNIQUE INDEX idx_mvreg_ine_exp ON mv_regularizacion_intervenciones_egresadas(id_expediente);

-- --- FIN: regularizacion/10_regularizacion_intervenciones_egresadas.sql ---

-- --- INICIO: contable/10_contable_intervenciones_egresadas.sql ---
-- ============================================================
-- CONTABLE 10: mv_contable_intervenciones_egresadas
-- ============================================================
-- ORDEN DE EJECUCIÓN: 11°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_intervenciones_egresadas CASCADE;
DROP TYPE IF EXISTS mv_contable_intervenciones_egresadas CASCADE;

CREATE MATERIALIZED VIEW mv_contable_intervenciones_egresadas AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'contable' AND trata_reporte = 'CONTABLE'
)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual           AS destino_actual,
    up.fecha_ultimo_pase             AS fecha_egreso,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_afuera
FROM mv_contable_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.es_trata_propia = FALSE
  AND NOT (up.destinatario_actual = ANY(cfg.analistas_oficiales));

CREATE UNIQUE INDEX idx_mvc_ine_exp ON mv_contable_intervenciones_egresadas(id_expediente);
CREATE INDEX idx_mvc_ine_trata ON mv_contable_intervenciones_egresadas(trata);


SELECT COUNT(*) AS total_intervenciones_egresadas FROM mv_contable_intervenciones_egresadas;

-- --- FIN: contable/10_contable_intervenciones_egresadas.sql ---

-- --- INICIO: etapa_proyecto/10_etapa_proyecto_intervenciones_egresadas.sql ---
-- ============================================================
-- ARCHIVO 10: mv_etapa_proyecto_intervenciones_egresadas
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_intervenciones_egresadas CASCADE;
DROP TYPE IF EXISTS mv_etapa_proyecto_intervenciones_egresadas CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_intervenciones_egresadas AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'etapa_proyecto' AND trata_reporte = 'ETAPA PROYECTO'
)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual           AS destino_actual,
    up.fecha_ultimo_pase             AS fecha_egreso,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_afuera
FROM mv_etapa_proyecto_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.es_trata_propia = FALSE
  AND NOT (up.destinatario_actual = ANY(cfg.analistas_oficiales));

CREATE UNIQUE INDEX idx_mvep_ine_exp ON mv_etapa_proyecto_intervenciones_egresadas(id_expediente);

-- --- FIN: etapa_proyecto/10_etapa_proyecto_intervenciones_egresadas.sql ---

-- --- INICIO: aviso_obra/10_aviso_obra_intervenciones_egresadas.sql ---
-- ============================================================
-- ARCHIVO 10: mv_aviso_obra_intervenciones_egresadas
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_intervenciones_egresadas CASCADE;
DROP TYPE IF EXISTS mv_aviso_obra_intervenciones_egresadas CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_intervenciones_egresadas AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aviso_obra' AND trata_reporte = 'AVISO DE OBRA'
)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual           AS destino_actual,
    up.fecha_ultimo_pase             AS fecha_egreso,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_afuera
FROM mv_aviso_obra_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.es_trata_propia = FALSE
  AND NOT (up.destinatario_actual = ANY(cfg.analistas_oficiales));

CREATE UNIQUE INDEX idx_mvao_ine_exp ON mv_aviso_obra_intervenciones_egresadas(id_expediente);

-- --- FIN: aviso_obra/10_aviso_obra_intervenciones_egresadas.sql ---

-- --- INICIO: morfologia/10_morfologia_intervenciones_egresadas.sql ---
-- ============================================================
-- ARCHIVO 10: mv_morfologia_intervenciones_egresadas
-- ============================================================
-- PROPÓSITO: Intervenciones actualmente fuera del sector.
-- (destinatario actual no es analista ni buzón de la gerencia)
-- ORDEN DE EJECUCIÓN: 11°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_intervenciones_egresadas CASCADE;
DROP TYPE IF EXISTS mv_morfologia_intervenciones_egresadas CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_intervenciones_egresadas AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
)
-- Para intervenciones, los "internos" son TODOS los buzones/usuarios de Stock Propio
-- (que ya están en analistas_oficiales - la lista incluye buzones del sector)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual           AS destino_actual,
    up.fecha_ultimo_pase             AS fecha_egreso,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_afuera
FROM mv_morfologia_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.es_trata_propia = FALSE
  AND NOT (up.destinatario_actual = ANY(cfg.analistas_oficiales));

CREATE UNIQUE INDEX idx_mvm_ine_exp ON mv_morfologia_intervenciones_egresadas(id_expediente);
CREATE INDEX idx_mvm_ine_trata ON mv_morfologia_intervenciones_egresadas(trata);


-- Validación
SELECT COUNT(*) AS total_intervenciones_egresadas FROM mv_morfologia_intervenciones_egresadas;

-- --- FIN: morfologia/10_morfologia_intervenciones_egresadas.sql ---

-- --- INICIO: aph/10_aph_intervenciones_egresadas.sql ---
-- ============================================================
-- ARCHIVO 10: mv_aph_intervenciones_egresadas
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_intervenciones_egresadas CASCADE;
DROP TYPE IF EXISTS mv_aph_intervenciones_egresadas CASCADE;

CREATE MATERIALIZED VIEW mv_aph_intervenciones_egresadas AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aph' AND trata_reporte = 'APH'
)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual           AS destino_actual,
    up.fecha_ultimo_pase             AS fecha_egreso,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_afuera
FROM mv_aph_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.es_trata_propia = FALSE
  AND NOT (up.destinatario_actual = ANY(cfg.analistas_oficiales));

CREATE UNIQUE INDEX idx_mvaph_ine_exp ON mv_aph_intervenciones_egresadas(id_expediente);

-- --- FIN: aph/10_aph_intervenciones_egresadas.sql ---

-- --- INICIO: usos/10_usos_intervenciones_egresadas.sql ---
-- ============================================================
-- ARCHIVO 10: mv_usos_intervenciones_egresadas
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_intervenciones_egresadas CASCADE;
DROP TYPE IF EXISTS mv_usos_intervenciones_egresadas CASCADE;

CREATE MATERIALIZED VIEW mv_usos_intervenciones_egresadas AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos' AND trata_reporte = 'USOS'
)
SELECT 
    u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
    u.fecha_primer_ingreso_gerencia,
    up.destinatario_actual           AS destino_actual,
    up.fecha_ultimo_pase             AS fecha_egreso,
    (CURRENT_DATE - up.fecha_ultimo_pase::date) AS dias_afuera
FROM mv_usos_universo u
INNER JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
CROSS JOIN cfg
WHERE u.es_trata_propia = FALSE
  AND NOT (up.destinatario_actual = ANY(cfg.analistas_oficiales));

CREATE UNIQUE INDEX idx_mvusos_ine_exp ON mv_usos_intervenciones_egresadas(id_expediente);

-- --- FIN: usos/10_usos_intervenciones_egresadas.sql ---

-- ============================================================
-- ETAPA DE COMPILACIÓN: 11
-- ============================================================

-- --- INICIO: catastro/11_catastro_interv_egresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 11: mv_catastro_interv_egresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_interv_egresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_catastro_interv_egresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_interv_egresos_eventos AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'catastro' AND trata_reporte = 'CATASTRO'
),
pases_externos AS (
    SELECT 
        u.id_expediente,
        u.expediente,
        u.trata,
        u.descripcion_trata,
        p.fecha          AS fecha_egreso,
        p.usuario        AS usuario_que_envia,
        p.destinatario   AS destino_externo,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY p.fecha DESC) AS rn
    FROM mv_catastro_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente
    WHERE u.es_trata_propia = FALSE
      AND NOT (p.destinatario = ANY(cfg.analistas_oficiales))
)
SELECT 
    id_expediente,
    expediente,
    trata,
    descripcion_trata,
    fecha_egreso,
    usuario_que_envia,
    destino_externo
FROM pases_externos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvct_iev_exp ON mv_catastro_interv_egresos_eventos(id_expediente);
CREATE INDEX idx_mvct_iev_fecha ON mv_catastro_interv_egresos_eventos(fecha_egreso);

-- --- FIN: catastro/11_catastro_interv_egresos_eventos.sql ---

-- --- INICIO: instalaciones/11_instalaciones_interv_egresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 11: mv_instalaciones_interv_egresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_interv_egresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_instalaciones_interv_egresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_interv_egresos_eventos AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'instalaciones' AND trata_reporte = 'INSTALACIONES'
),
pases_externos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
        p.fecha          AS fecha_egreso,
        p.usuario        AS usuario_que_envia,
        p.destinatario   AS destino_externo,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY p.fecha DESC) AS rn
    FROM mv_instalaciones_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente
    WHERE u.es_trata_propia = FALSE
      AND NOT (p.destinatario = ANY(cfg.analistas_oficiales))
)
SELECT id_expediente, expediente, trata, descripcion_trata, fecha_egreso, usuario_que_envia, destino_externo
FROM pases_externos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvins_iev_exp ON mv_instalaciones_interv_egresos_eventos(id_expediente);
CREATE INDEX idx_mvins_iev_fecha ON mv_instalaciones_interv_egresos_eventos(fecha_egreso);

-- --- FIN: instalaciones/11_instalaciones_interv_egresos_eventos.sql ---

-- --- INICIO: regularizacion/11_regularizacion_interv_egresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 11: mv_regularizacion_interv_egresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_interv_egresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_regularizacion_interv_egresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_interv_egresos_eventos AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME'
),
pases_externos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
        p.fecha          AS fecha_egreso,
        p.usuario        AS usuario_que_envia,
        p.destinatario   AS destino_externo,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY p.fecha DESC) AS rn
    FROM mv_regularizacion_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente
    WHERE u.es_trata_propia = FALSE
      AND NOT (p.destinatario = ANY(cfg.analistas_oficiales))
)
SELECT id_expediente, expediente, trata, descripcion_trata, fecha_egreso, usuario_que_envia, destino_externo
FROM pases_externos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvreg_iev_exp ON mv_regularizacion_interv_egresos_eventos(id_expediente);
CREATE INDEX idx_mvreg_iev_fecha ON mv_regularizacion_interv_egresos_eventos(fecha_egreso);

-- --- FIN: regularizacion/11_regularizacion_interv_egresos_eventos.sql ---

-- --- INICIO: contable/11_contable_interv_egresos_eventos.sql ---
-- ============================================================
-- CONTABLE 11: mv_contable_interv_egresos_eventos
-- ============================================================
-- PROPÓSITO: Último egreso de cada intervención (regla: la fecha más reciente).
-- ORDEN DE EJECUCIÓN: 12°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_interv_egresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_contable_interv_egresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_contable_interv_egresos_eventos AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'contable' AND trata_reporte = 'CONTABLE'
),
pases_externos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
        p.fecha          AS fecha_egreso,
        p.usuario        AS usuario_que_envia,
        p.destinatario   AS destino_externo,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY p.fecha DESC) AS rn
    FROM mv_contable_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente
    WHERE u.es_trata_propia = FALSE
      AND NOT (p.destinatario = ANY(cfg.analistas_oficiales))
)
SELECT 
    id_expediente, expediente, trata, descripcion_trata,
    fecha_egreso, usuario_que_envia, destino_externo
FROM pases_externos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvc_iev_exp ON mv_contable_interv_egresos_eventos(id_expediente);
CREATE INDEX idx_mvc_iev_fecha ON mv_contable_interv_egresos_eventos(fecha_egreso);
CREATE INDEX idx_mvc_iev_trata ON mv_contable_interv_egresos_eventos(trata);


SELECT COUNT(*) AS total_egresos_intervenciones FROM mv_contable_interv_egresos_eventos;

-- --- FIN: contable/11_contable_interv_egresos_eventos.sql ---

-- --- INICIO: etapa_proyecto/11_etapa_proyecto_interv_egresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 11: mv_etapa_proyecto_interv_egresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_interv_egresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_etapa_proyecto_interv_egresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_interv_egresos_eventos AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'etapa_proyecto' AND trata_reporte = 'ETAPA PROYECTO'
),
pases_externos AS (
    SELECT 
        u.id_expediente,
        u.expediente,
        u.trata,
        u.descripcion_trata,
        p.fecha          AS fecha_egreso,
        p.usuario        AS usuario_que_envia,
        p.destinatario   AS destino_externo,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY p.fecha DESC) AS rn
    FROM mv_etapa_proyecto_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente
    WHERE u.es_trata_propia = FALSE
      AND NOT (p.destinatario = ANY(cfg.analistas_oficiales))
)
SELECT 
    id_expediente,
    expediente,
    trata,
    descripcion_trata,
    fecha_egreso,
    usuario_que_envia,
    destino_externo
FROM pases_externos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvep_iev_exp ON mv_etapa_proyecto_interv_egresos_eventos(id_expediente);
CREATE INDEX idx_mvep_iev_fecha ON mv_etapa_proyecto_interv_egresos_eventos(fecha_egreso);

-- --- FIN: etapa_proyecto/11_etapa_proyecto_interv_egresos_eventos.sql ---

-- --- INICIO: aviso_obra/11_aviso_obra_interv_egresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 11: mv_aviso_obra_interv_egresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_interv_egresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_aviso_obra_interv_egresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_interv_egresos_eventos AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aviso_obra' AND trata_reporte = 'AVISO DE OBRA'
),
pases_externos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata, u.descripcion_trata,
        p.fecha          AS fecha_egreso,
        p.usuario        AS usuario_que_envia,
        p.destinatario   AS destino_externo,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY p.fecha DESC) AS rn
    FROM mv_aviso_obra_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente
    WHERE u.es_trata_propia = FALSE
      AND NOT (p.destinatario = ANY(cfg.analistas_oficiales))
)
SELECT id_expediente, expediente, trata, descripcion_trata, fecha_egreso, usuario_que_envia, destino_externo
FROM pases_externos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvao_iev_exp ON mv_aviso_obra_interv_egresos_eventos(id_expediente);
CREATE INDEX idx_mvao_iev_fecha ON mv_aviso_obra_interv_egresos_eventos(fecha_egreso);

-- --- FIN: aviso_obra/11_aviso_obra_interv_egresos_eventos.sql ---

-- --- INICIO: morfologia/11_morfologia_interv_egresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 11: mv_morfologia_interv_egresos_eventos
-- ============================================================
-- PROPÓSITO: Eventos de egreso de intervenciones (pases a destinos externos).
-- REGLA NUEVA (a partir de Morfología): si un mismo expediente entró
-- varias veces para intervención, se cuenta SOLO el ÚLTIMO egreso.
-- No es "todos los pases externos", es "la fecha más reciente de salida".
-- ORDEN DE EJECUCIÓN: 12°.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_interv_egresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_morfologia_interv_egresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_interv_egresos_eventos AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
),
pases_externos AS (
    -- Todos los pases a destinos externos (destinatario NO está en analistas_oficiales)
    SELECT 
        u.id_expediente,
        u.expediente,
        u.trata,
        u.descripcion_trata,
        p.fecha          AS fecha_egreso,
        p.usuario        AS usuario_que_envia,
        p.destinatario   AS destino_externo,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY p.fecha DESC) AS rn
    FROM mv_morfologia_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente
    WHERE u.es_trata_propia = FALSE
      AND NOT (p.destinatario = ANY(cfg.analistas_oficiales))
)
-- Tomamos solo el último egreso de cada expediente (rn = 1 con ORDER BY DESC)
SELECT 
    id_expediente,
    expediente,
    trata,
    descripcion_trata,
    fecha_egreso,
    usuario_que_envia,
    destino_externo
FROM pases_externos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvm_iev_exp ON mv_morfologia_interv_egresos_eventos(id_expediente);
CREATE INDEX idx_mvm_iev_fecha ON mv_morfologia_interv_egresos_eventos(fecha_egreso);
CREATE INDEX idx_mvm_iev_trata ON mv_morfologia_interv_egresos_eventos(trata);


-- Validación
SELECT COUNT(*) AS total_egresos_intervenciones FROM mv_morfologia_interv_egresos_eventos;

-- --- FIN: morfologia/11_morfologia_interv_egresos_eventos.sql ---

-- --- INICIO: aph/11_aph_interv_egresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 11: mv_aph_interv_egresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_interv_egresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_aph_interv_egresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_aph_interv_egresos_eventos AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'aph' AND trata_reporte = 'APH'
),
egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_aph_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo = ANY(cfg.acronimos_egreso)
    WHERE u.es_trata_propia = FALSE
      AND (cfg.firmantes_egreso IS NULL OR d.usuario_creador = ANY(cfg.firmantes_egreso))
)
SELECT 
    id_expediente, expediente, trata,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvaph_iev_exp ON mv_aph_interv_egresos_eventos(id_expediente);
CREATE INDEX idx_mvaph_iev_fecha ON mv_aph_interv_egresos_eventos(fecha_egreso);

-- --- FIN: aph/11_aph_interv_egresos_eventos.sql ---

-- --- INICIO: usos/11_usos_interv_egresos_eventos.sql ---
-- ============================================================
-- ARCHIVO 11: mv_usos_interv_egresos_eventos
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_interv_egresos_eventos CASCADE;
DROP TYPE IF EXISTS mv_usos_interv_egresos_eventos CASCADE;

CREATE MATERIALIZED VIEW mv_usos_interv_egresos_eventos AS
WITH cfg AS (
    SELECT acronimos_egreso, firmantes_egreso
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos' AND trata_reporte = 'USOS'
),
egresos_validos AS (
    SELECT 
        u.id_expediente, u.expediente, u.trata,
        d.documento           AS documento_egreso,
        d.acronimo            AS acronimo_egreso,
        d.fecha_creacion      AS fecha_egreso,
        d.usuario_creador     AS usuario_egreso,
        ROW_NUMBER() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_creacion ASC) AS rn
    FROM mv_usos_universo u
    CROSS JOIN cfg
    INNER JOIN mvw_datos_gedo_secgdu d 
        ON d.id_expediente = u.id_expediente
       AND d.acronimo = ANY(cfg.acronimos_egreso)
    WHERE u.es_trata_propia = FALSE
      AND (cfg.firmantes_egreso IS NULL OR d.usuario_creador = ANY(cfg.firmantes_egreso))
)
SELECT 
    id_expediente, expediente, trata,
    documento_egreso, acronimo_egreso, fecha_egreso, usuario_egreso
FROM egresos_validos
WHERE rn = 1;

CREATE UNIQUE INDEX idx_mvusos_iev_exp ON mv_usos_interv_egresos_eventos(id_expediente);
CREATE INDEX idx_mvusos_iev_fecha ON mv_usos_interv_egresos_eventos(fecha_egreso);

-- --- FIN: usos/11_usos_interv_egresos_eventos.sql ---

-- ============================================================
-- ETAPA DE COMPILACIÓN: 12
-- ============================================================

-- --- INICIO: catastro/12_catastro_stock_historico.sql ---
-- ============================================================
-- ARCHIVO 12: mv_catastro_stock_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_stock_historico CASCADE;
DROP TYPE IF EXISTS mv_catastro_stock_historico CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_stock_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'catastro' AND trata_reporte = 'CATASTRO'
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        u.es_trata_propia,
        fc.fecha_corte,
        p.destinatario AS destinatario_cierre
    FROM mv_catastro_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente
       AND a.usuario_alta = ANY(cfg.analistas_oficiales)
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
)
SELECT
    dpc.fecha_corte                                AS mes_cierre,
    TO_CHAR(dpc.fecha_corte, 'YYYY-MM')            AS mes_label,
    dpc.trata,
    dpc.es_trata_propia,
    CASE 
        WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION'
        ELSE 'STOCK_PROPIO'
    END AS categoria,
    COUNT(*) AS cant_expedientes
FROM destinatario_por_corte dpc
LEFT JOIN subsanacion_abierta_al_cierre sac 
    ON sac.id_expediente = dpc.id_expediente
   AND sac.fecha_corte = dpc.fecha_corte
CROSS JOIN cfg
WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
GROUP BY dpc.fecha_corte, dpc.trata, dpc.es_trata_propia,
         CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION' ELSE 'STOCK_PROPIO' END;

CREATE INDEX idx_mvct_sh_mes ON mv_catastro_stock_historico(mes_cierre);
CREATE INDEX idx_mvct_sh_trata ON mv_catastro_stock_historico(trata);
CREATE INDEX idx_mvct_sh_categoria ON mv_catastro_stock_historico(categoria);

-- --- FIN: catastro/12_catastro_stock_historico.sql ---

-- --- INICIO: instalaciones/12_instalaciones_stock_historico.sql ---
-- ============================================================
-- ARCHIVO 12: mv_instalaciones_stock_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_stock_historico CASCADE;
DROP TYPE IF EXISTS mv_instalaciones_stock_historico CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_stock_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'instalaciones' AND trata_reporte = 'INSTALACIONES'
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        u.es_trata_propia,
        fc.fecha_corte,
        p.destinatario AS destinatario_cierre
    FROM mv_instalaciones_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente
       AND a.usuario_alta = ANY(cfg.analistas_oficiales)
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
)
SELECT
    dpc.fecha_corte                                AS mes_cierre,
    TO_CHAR(dpc.fecha_corte, 'YYYY-MM')            AS mes_label,
    dpc.trata,
    dpc.es_trata_propia,
    CASE 
        WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION'
        ELSE 'STOCK_PROPIO'
    END AS categoria,
    COUNT(*) AS cant_expedientes
FROM destinatario_por_corte dpc
LEFT JOIN subsanacion_abierta_al_cierre sac 
    ON sac.id_expediente = dpc.id_expediente
   AND sac.fecha_corte = dpc.fecha_corte
CROSS JOIN cfg
WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
GROUP BY dpc.fecha_corte, dpc.trata, dpc.es_trata_propia,
         CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION' ELSE 'STOCK_PROPIO' END;

CREATE INDEX idx_mvins_sh_mes ON mv_instalaciones_stock_historico(mes_cierre);
CREATE INDEX idx_mvins_sh_trata ON mv_instalaciones_stock_historico(trata);
CREATE INDEX idx_mvins_sh_categoria ON mv_instalaciones_stock_historico(categoria);

-- --- FIN: instalaciones/12_instalaciones_stock_historico.sql ---

-- --- INICIO: regularizacion/12_regularizacion_stock_historico.sql ---
-- ============================================================
-- ARCHIVO 12: mv_regularizacion_stock_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_stock_historico CASCADE;
DROP TYPE IF EXISTS mv_regularizacion_stock_historico CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_stock_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion' AND trata_reporte = 'REGULARIZACIÓN Y CONFORME'
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        u.es_trata_propia,
        fc.fecha_corte,
        p.destinatario AS destinatario_cierre
    FROM mv_regularizacion_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente
       AND a.usuario_alta = ANY(cfg.analistas_oficiales)
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
)
SELECT
    dpc.fecha_corte                                AS mes_cierre,
    TO_CHAR(dpc.fecha_corte, 'YYYY-MM')            AS mes_label,
    dpc.trata,
    dpc.es_trata_propia,
    CASE 
        WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION'
        ELSE 'STOCK_PROPIO'
    END AS categoria,
    COUNT(*) AS cant_expedientes
FROM destinatario_por_corte dpc
LEFT JOIN subsanacion_abierta_al_cierre sac 
    ON sac.id_expediente = dpc.id_expediente
   AND sac.fecha_corte = dpc.fecha_corte
CROSS JOIN cfg
WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
GROUP BY dpc.fecha_corte, dpc.trata, dpc.es_trata_propia,
         CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION' ELSE 'STOCK_PROPIO' END;

CREATE INDEX idx_mvreg_sh_mes ON mv_regularizacion_stock_historico(mes_cierre);
CREATE INDEX idx_mvreg_sh_trata ON mv_regularizacion_stock_historico(trata);
CREATE INDEX idx_mvreg_sh_categoria ON mv_regularizacion_stock_historico(categoria);

-- --- FIN: regularizacion/12_regularizacion_stock_historico.sql ---

-- --- INICIO: contable/12_contable_stock_historico.sql ---
-- ============================================================
-- CONTABLE 12: mv_contable_stock_historico
-- ============================================================
-- PROPÓSITO: Stock histórico rolling 12 meses.
-- Replica la lógica corregida de Instalaciones/Morfología.
-- ORDEN DE EJECUCIÓN: 13°.
-- ⚠️ Tarda varios minutos en crearse la primera vez.
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_stock_historico CASCADE;
DROP TYPE IF EXISTS mv_contable_stock_historico CASCADE;

CREATE MATERIALIZED VIEW mv_contable_stock_historico AS
WITH cfg AS (
    SELECT analistas_oficiales, tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'contable' AND trata_reporte = 'CONTABLE'
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        u.es_trata_propia,
        fc.fecha_corte,
        p.destinatario AS destinatario_cierre
    FROM mv_contable_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente
       AND a.usuario_alta = dpc.destinatario_cierre
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
)
SELECT
    dpc.fecha_corte                                AS mes_cierre,
    TO_CHAR(dpc.fecha_corte, 'YYYY-MM')            AS mes_label,
    dpc.trata,
    dpc.es_trata_propia,
    CASE 
        WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION'
        ELSE 'STOCK_PROPIO'
    END AS categoria,
    COUNT(*) AS cant_expedientes
FROM destinatario_por_corte dpc
LEFT JOIN subsanacion_abierta_al_cierre sac 
    ON sac.id_expediente = dpc.id_expediente
   AND sac.fecha_corte = dpc.fecha_corte
CROSS JOIN cfg
WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
GROUP BY dpc.fecha_corte, dpc.trata, dpc.es_trata_propia,
         CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION' ELSE 'STOCK_PROPIO' END;

CREATE INDEX idx_mvc_sh_mes ON mv_contable_stock_historico(mes_cierre);
CREATE INDEX idx_mvc_sh_trata ON mv_contable_stock_historico(trata);
CREATE INDEX idx_mvc_sh_categoria ON mv_contable_stock_historico(categoria);
CREATE INDEX idx_mvc_sh_propia ON mv_contable_stock_historico(es_trata_propia);


SELECT 
    mes_label,
    es_trata_propia,
    categoria,
    SUM(cant_expedientes) AS total
FROM mv_contable_stock_historico
GROUP BY mes_label, mes_cierre, es_trata_propia, categoria
ORDER BY mes_cierre, es_trata_propia DESC, categoria;

-- --- FIN: contable/12_contable_stock_historico.sql ---

-- --- INICIO: etapa_proyecto/12_etapa_proyecto_stock_historico.sql ---
-- ============================================================
-- ARCHIVO 12: mv_etapa_proyecto_stock_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_stock_historico CASCADE;
DROP TYPE IF EXISTS mv_etapa_proyecto_stock_historico CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_stock_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'etapa_proyecto' AND trata_reporte = 'ETAPA PROYECTO'
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        u.es_trata_propia,
        fc.fecha_corte,
        p.destinatario AS destinatario_cierre
    FROM mv_etapa_proyecto_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente
       AND a.usuario_alta = ANY(cfg.analistas_oficiales)
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
)
SELECT
    dpc.fecha_corte                                AS mes_cierre,
    TO_CHAR(dpc.fecha_corte, 'YYYY-MM')            AS mes_label,
    dpc.trata,
    dpc.es_trata_propia,
    CASE 
        WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION'
        ELSE 'STOCK_PROPIO'
    END AS categoria,
    COUNT(*) AS cant_expedientes
FROM destinatario_por_corte dpc
LEFT JOIN subsanacion_abierta_al_cierre sac 
    ON sac.id_expediente = dpc.id_expediente
   AND sac.fecha_corte = dpc.fecha_corte
CROSS JOIN cfg
WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
GROUP BY dpc.fecha_corte, dpc.trata, dpc.es_trata_propia,
         CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION' ELSE 'STOCK_PROPIO' END;

CREATE INDEX idx_mvep_sh_mes ON mv_etapa_proyecto_stock_historico(mes_cierre);
CREATE INDEX idx_mvep_sh_trata ON mv_etapa_proyecto_stock_historico(trata);
CREATE INDEX idx_mvep_sh_categoria ON mv_etapa_proyecto_stock_historico(categoria);

-- --- FIN: etapa_proyecto/12_etapa_proyecto_stock_historico.sql ---

-- --- INICIO: aviso_obra/12_aviso_obra_stock_historico.sql ---
-- ============================================================
-- ARCHIVO 12: mv_aviso_obra_stock_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_stock_historico CASCADE;
DROP TYPE IF EXISTS mv_aviso_obra_stock_historico CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_stock_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aviso_obra' AND trata_reporte = 'AVISO DE OBRA'
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        u.es_trata_propia,
        fc.fecha_corte,
        p.destinatario AS destinatario_cierre
    FROM mv_aviso_obra_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente
       AND a.usuario_alta = ANY(cfg.analistas_oficiales)
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
)
SELECT
    dpc.fecha_corte                                AS mes_cierre,
    TO_CHAR(dpc.fecha_corte, 'YYYY-MM')            AS mes_label,
    dpc.trata,
    dpc.es_trata_propia,
    CASE 
        WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION'
        ELSE 'STOCK_PROPIO'
    END AS categoria,
    COUNT(*) AS cant_expedientes
FROM destinatario_por_corte dpc
LEFT JOIN subsanacion_abierta_al_cierre sac 
    ON sac.id_expediente = dpc.id_expediente
   AND sac.fecha_corte = dpc.fecha_corte
CROSS JOIN cfg
WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
GROUP BY dpc.fecha_corte, dpc.trata, dpc.es_trata_propia,
         CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION' ELSE 'STOCK_PROPIO' END;

CREATE INDEX idx_mvao_sh_mes ON mv_aviso_obra_stock_historico(mes_cierre);
CREATE INDEX idx_mvao_sh_trata ON mv_aviso_obra_stock_historico(trata);
CREATE INDEX idx_mvao_sh_categoria ON mv_aviso_obra_stock_historico(categoria);

-- --- FIN: aviso_obra/12_aviso_obra_stock_historico.sql ---

-- --- INICIO: morfologia/12_morfologia_stock_historico.sql ---
-- ============================================================
-- ARCHIVO 12: mv_morfologia_stock_historico
-- ============================================================
-- PROPÓSITO: Stock histórico mensual rolling 12 meses.
-- Replica la lógica corregida de Instalaciones:
--   - Detecta subsanaciones por FECHAS (no por estado actual).
--   - Filtra por nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'.
-- ORDEN DE EJECUCIÓN: 13° (último, es el más pesado).
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_stock_historico CASCADE;
DROP TYPE IF EXISTS mv_morfologia_stock_historico CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_stock_historico AS
WITH cfg AS (
    SELECT analistas_oficiales, tratas_incluidas
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia' AND trata_reporte = 'MORFOLOGIA'
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        u.es_trata_propia,
        fc.fecha_corte,
        p.destinatario AS destinatario_cierre
    FROM mv_morfologia_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente
       AND a.usuario_alta = ANY(cfg.analistas_oficiales)
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
)
SELECT
    dpc.fecha_corte                                AS mes_cierre,
    TO_CHAR(dpc.fecha_corte, 'YYYY-MM')            AS mes_label,
    dpc.trata,
    dpc.es_trata_propia,
    CASE 
        WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION'
        ELSE 'STOCK_PROPIO'
    END AS categoria,
    COUNT(*) AS cant_expedientes
FROM destinatario_por_corte dpc
LEFT JOIN subsanacion_abierta_al_cierre sac 
    ON sac.id_expediente = dpc.id_expediente
   AND sac.fecha_corte = dpc.fecha_corte
CROSS JOIN cfg
WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
GROUP BY dpc.fecha_corte, dpc.trata, dpc.es_trata_propia,
         CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION' ELSE 'STOCK_PROPIO' END;

CREATE INDEX idx_mvm_sh_mes ON mv_morfologia_stock_historico(mes_cierre);
CREATE INDEX idx_mvm_sh_trata ON mv_morfologia_stock_historico(trata);
CREATE INDEX idx_mvm_sh_categoria ON mv_morfologia_stock_historico(categoria);
CREATE INDEX idx_mvm_sh_propia ON mv_morfologia_stock_historico(es_trata_propia);


-- Validación
SELECT 
    mes_label,
    es_trata_propia,
    categoria,
    SUM(cant_expedientes) AS total
FROM mv_morfologia_stock_historico
GROUP BY mes_label, mes_cierre, es_trata_propia, categoria
ORDER BY mes_cierre, es_trata_propia DESC, categoria;

-- --- FIN: morfologia/12_morfologia_stock_historico.sql ---

-- --- INICIO: aph/12_aph_stock_historico.sql ---
-- ============================================================
-- ARCHIVO 12: mv_aph_stock_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_stock_historico CASCADE;
DROP TYPE IF EXISTS mv_aph_stock_historico CASCADE;

CREATE MATERIALIZED VIEW mv_aph_stock_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aph' AND trata_reporte = 'APH'
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        u.es_trata_propia,
        fc.fecha_corte,
        p.destinatario AS destinatario_cierre
    FROM mv_aph_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente
       AND a.usuario_alta = ANY(cfg.analistas_oficiales)
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
)
SELECT
    dpc.fecha_corte                                AS mes_cierre,
    TO_CHAR(dpc.fecha_corte, 'YYYY-MM')            AS mes_label,
    dpc.trata,
    dpc.es_trata_propia,
    CASE 
        WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION'
        ELSE 'STOCK_PROPIO'
    END AS categoria,
    COUNT(*) AS cant_expedientes
FROM destinatario_por_corte dpc
LEFT JOIN subsanacion_abierta_al_cierre sac 
    ON sac.id_expediente = dpc.id_expediente
   AND sac.fecha_corte = dpc.fecha_corte
CROSS JOIN cfg
WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
GROUP BY dpc.fecha_corte, dpc.trata, dpc.es_trata_propia,
         CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION' ELSE 'STOCK_PROPIO' END;

CREATE INDEX idx_mvaph_sh_mes ON mv_aph_stock_historico(mes_cierre);
CREATE INDEX idx_mvaph_sh_trata ON mv_aph_stock_historico(trata);
CREATE INDEX idx_mvaph_sh_categoria ON mv_aph_stock_historico(categoria);

-- --- FIN: aph/12_aph_stock_historico.sql ---

-- --- INICIO: usos/12_usos_stock_historico.sql ---
-- ============================================================
-- ARCHIVO 12: mv_usos_stock_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_stock_historico CASCADE;
DROP TYPE IF EXISTS mv_usos_stock_historico CASCADE;

CREATE MATERIALIZED VIEW mv_usos_stock_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos' AND trata_reporte = 'USOS'
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        u.es_trata_propia,
        fc.fecha_corte,
        p.destinatario AS destinatario_cierre
    FROM mv_usos_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente
       AND a.usuario_alta = ANY(cfg.analistas_oficiales)
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
)
SELECT
    dpc.fecha_corte                                AS mes_cierre,
    TO_CHAR(dpc.fecha_corte, 'YYYY-MM')            AS mes_label,
    dpc.trata,
    dpc.es_trata_propia,
    CASE 
        WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION'
        ELSE 'STOCK_PROPIO'
    END AS categoria,
    COUNT(*) AS cant_expedientes
FROM destinatario_por_corte dpc
LEFT JOIN subsanacion_abierta_al_cierre sac 
    ON sac.id_expediente = dpc.id_expediente
   AND sac.fecha_corte = dpc.fecha_corte
CROSS JOIN cfg
WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
GROUP BY dpc.fecha_corte, dpc.trata, dpc.es_trata_propia,
         CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, FALSE) THEN 'SUBSANACION' ELSE 'STOCK_PROPIO' END;

CREATE INDEX idx_mvusos_sh_mes ON mv_usos_stock_historico(mes_cierre);
CREATE INDEX idx_mvusos_sh_trata ON mv_usos_stock_historico(trata);
CREATE INDEX idx_mvusos_sh_categoria ON mv_usos_stock_historico(categoria);

-- --- FIN: usos/12_usos_stock_historico.sql ---

-- ============================================================
-- ETAPA DE COMPILACIÓN: 14
-- ============================================================

-- --- INICIO: catastro/14_catastro_metas_historico.sql ---
-- ============================================================
-- CATASTRO 14: mv_catastro_metas_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_catastro_metas_historico CASCADE;
DROP TYPE IF EXISTS mv_catastro_metas_historico CASCADE;

CREATE MATERIALIZED VIEW mv_catastro_metas_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'catastro'
    LIMIT 1
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        fc.fecha_corte,
        u.fecha_primer_ingreso_gerencia,
        p.destinatario AS destinatario_cierre
    FROM mv_catastro_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente 
       AND a.usuario_alta = dpc.destinatario_cierre 
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte 
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
),
stock_filtrado AS (
    SELECT 
        dpc.fecha_corte,
        dpc.trata,
        dpc.fecha_primer_ingreso_gerencia
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    LEFT JOIN subsanacion_abierta_al_cierre sac 
        ON sac.id_expediente = dpc.id_expediente 
       AND sac.fecha_corte = dpc.fecha_corte
    WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
      AND COALESCE(sac.tiene_subsanacion_abierta, FALSE) IS FALSE
)
SELECT 
    fecha_corte,
    to_char(fecha_corte, 'YYYY-MM') as mes_label,
    trata,
    COUNT(*) as total_stock,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) > 90 THEN 1 ELSE 0 END) as stock_sector,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) <= 90 THEN 1 ELSE 0 END) as stock_corriente
FROM stock_filtrado
GROUP BY 1, 2, 3;

CREATE INDEX idx_mv_catastro_mh_fecha ON mv_catastro_metas_historico(fecha_corte);
CREATE INDEX idx_mv_catastro_mh_trata ON mv_catastro_metas_historico(trata);

-- --- FIN: catastro/14_catastro_metas_historico.sql ---

-- --- INICIO: instalaciones/14_instalaciones_metas_historico.sql ---
-- ============================================================
-- INSTALACIONES 14: mv_instalaciones_metas_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_instalaciones_metas_historico CASCADE;
DROP TYPE IF EXISTS mv_instalaciones_metas_historico CASCADE;

CREATE MATERIALIZED VIEW mv_instalaciones_metas_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'instalaciones'
    LIMIT 1
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        fc.fecha_corte,
        u.fecha_primer_ingreso_gerencia,
        p.destinatario AS destinatario_cierre
    FROM mv_instalaciones_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente 
       AND a.usuario_alta = dpc.destinatario_cierre 
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte 
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
),
stock_filtrado AS (
    SELECT 
        dpc.fecha_corte,
        dpc.trata,
        dpc.fecha_primer_ingreso_gerencia
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    LEFT JOIN subsanacion_abierta_al_cierre sac 
        ON sac.id_expediente = dpc.id_expediente 
       AND sac.fecha_corte = dpc.fecha_corte
    WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
      AND COALESCE(sac.tiene_subsanacion_abierta, FALSE) IS FALSE
)
SELECT 
    fecha_corte,
    to_char(fecha_corte, 'YYYY-MM') as mes_label,
    trata,
    COUNT(*) as total_stock,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) > 90 THEN 1 ELSE 0 END) as stock_sector,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) <= 90 THEN 1 ELSE 0 END) as stock_corriente
FROM stock_filtrado
GROUP BY 1, 2, 3;

CREATE INDEX idx_mv_instalaciones_mh_fecha ON mv_instalaciones_metas_historico(fecha_corte);
CREATE INDEX idx_mv_instalaciones_mh_trata ON mv_instalaciones_metas_historico(trata);

-- --- FIN: instalaciones/14_instalaciones_metas_historico.sql ---

-- --- INICIO: regularizacion/14_regularizacion_metas_historico.sql ---
-- ============================================================
-- REGULARIZACION 14: mv_regularizacion_metas_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_regularizacion_metas_historico CASCADE;
DROP TYPE IF EXISTS mv_regularizacion_metas_historico CASCADE;

CREATE MATERIALIZED VIEW mv_regularizacion_metas_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'regularizacion'
    LIMIT 1
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        fc.fecha_corte,
        u.fecha_primer_ingreso_gerencia,
        p.destinatario AS destinatario_cierre
    FROM mv_regularizacion_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente 
       AND a.usuario_alta = dpc.destinatario_cierre 
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte 
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
),
stock_filtrado AS (
    SELECT 
        dpc.fecha_corte,
        dpc.trata,
        dpc.fecha_primer_ingreso_gerencia
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    LEFT JOIN subsanacion_abierta_al_cierre sac 
        ON sac.id_expediente = dpc.id_expediente 
       AND sac.fecha_corte = dpc.fecha_corte
    WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
      AND COALESCE(sac.tiene_subsanacion_abierta, FALSE) IS FALSE
)
SELECT 
    fecha_corte,
    to_char(fecha_corte, 'YYYY-MM') as mes_label,
    trata,
    COUNT(*) as total_stock,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) > 90 THEN 1 ELSE 0 END) as stock_sector,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) <= 90 THEN 1 ELSE 0 END) as stock_corriente
FROM stock_filtrado
GROUP BY 1, 2, 3;

CREATE INDEX idx_mv_regularizacion_mh_fecha ON mv_regularizacion_metas_historico(fecha_corte);
CREATE INDEX idx_mv_regularizacion_mh_trata ON mv_regularizacion_metas_historico(trata);

-- --- FIN: regularizacion/14_regularizacion_metas_historico.sql ---

-- --- INICIO: contable/14_contable_metas_historico.sql ---
-- ============================================================
-- CONTABLE 14: mv_contable_metas_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_contable_metas_historico CASCADE;
DROP TYPE IF EXISTS mv_contable_metas_historico CASCADE;

CREATE MATERIALIZED VIEW mv_contable_metas_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'contable'
    LIMIT 1
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        fc.fecha_corte,
        u.fecha_primer_ingreso_gerencia,
        p.destinatario AS destinatario_cierre
    FROM mv_contable_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente 
       AND a.usuario_alta = dpc.destinatario_cierre 
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte 
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
),
stock_filtrado AS (
    SELECT 
        dpc.fecha_corte,
        dpc.trata,
        dpc.fecha_primer_ingreso_gerencia
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    LEFT JOIN subsanacion_abierta_al_cierre sac 
        ON sac.id_expediente = dpc.id_expediente 
       AND sac.fecha_corte = dpc.fecha_corte
    WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
      AND COALESCE(sac.tiene_subsanacion_abierta, FALSE) IS FALSE
)
SELECT 
    fecha_corte,
    to_char(fecha_corte, 'YYYY-MM') as mes_label,
    trata,
    COUNT(*) as total_stock,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) > 90 THEN 1 ELSE 0 END) as stock_sector,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) <= 90 THEN 1 ELSE 0 END) as stock_corriente
FROM stock_filtrado
GROUP BY 1, 2, 3;

CREATE INDEX idx_mv_contable_mh_fecha ON mv_contable_metas_historico(fecha_corte);
CREATE INDEX idx_mv_contable_mh_trata ON mv_contable_metas_historico(trata);

-- --- FIN: contable/14_contable_metas_historico.sql ---

-- --- INICIO: etapa_proyecto/14_etapa_proyecto_metas_historico.sql ---
-- ============================================================
-- ETAPA_PROYECTO 14: mv_etapa_proyecto_metas_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_etapa_proyecto_metas_historico CASCADE;
DROP TYPE IF EXISTS mv_etapa_proyecto_metas_historico CASCADE;

CREATE MATERIALIZED VIEW mv_etapa_proyecto_metas_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'etapa_proyecto'
    LIMIT 1
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        fc.fecha_corte,
        u.fecha_primer_ingreso_gerencia,
        p.destinatario AS destinatario_cierre
    FROM mv_etapa_proyecto_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente 
       AND a.usuario_alta = dpc.destinatario_cierre 
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte 
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
),
stock_filtrado AS (
    SELECT 
        dpc.fecha_corte,
        dpc.trata,
        dpc.fecha_primer_ingreso_gerencia
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    LEFT JOIN subsanacion_abierta_al_cierre sac 
        ON sac.id_expediente = dpc.id_expediente 
       AND sac.fecha_corte = dpc.fecha_corte
    WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
      AND COALESCE(sac.tiene_subsanacion_abierta, FALSE) IS FALSE
)
SELECT 
    fecha_corte,
    to_char(fecha_corte, 'YYYY-MM') as mes_label,
    trata,
    COUNT(*) as total_stock,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) > 90 THEN 1 ELSE 0 END) as stock_sector,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) <= 90 THEN 1 ELSE 0 END) as stock_corriente
FROM stock_filtrado
GROUP BY 1, 2, 3;

CREATE INDEX idx_mv_etapa_proyecto_mh_fecha ON mv_etapa_proyecto_metas_historico(fecha_corte);
CREATE INDEX idx_mv_etapa_proyecto_mh_trata ON mv_etapa_proyecto_metas_historico(trata);

-- --- FIN: etapa_proyecto/14_etapa_proyecto_metas_historico.sql ---

-- --- INICIO: aviso_obra/14_aviso_obra_metas_historico.sql ---
-- ============================================================
-- AVISO_OBRA 14: mv_aviso_obra_metas_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aviso_obra_metas_historico CASCADE;
DROP TYPE IF EXISTS mv_aviso_obra_metas_historico CASCADE;

CREATE MATERIALIZED VIEW mv_aviso_obra_metas_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aviso_obra'
    LIMIT 1
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        fc.fecha_corte,
        u.fecha_primer_ingreso_gerencia,
        p.destinatario AS destinatario_cierre
    FROM mv_aviso_obra_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente 
       AND a.usuario_alta = dpc.destinatario_cierre 
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte 
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
),
stock_filtrado AS (
    SELECT 
        dpc.fecha_corte,
        dpc.trata,
        dpc.fecha_primer_ingreso_gerencia
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    LEFT JOIN subsanacion_abierta_al_cierre sac 
        ON sac.id_expediente = dpc.id_expediente 
       AND sac.fecha_corte = dpc.fecha_corte
    WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
      AND COALESCE(sac.tiene_subsanacion_abierta, FALSE) IS FALSE
)
SELECT 
    fecha_corte,
    to_char(fecha_corte, 'YYYY-MM') as mes_label,
    trata,
    COUNT(*) as total_stock,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) > 90 THEN 1 ELSE 0 END) as stock_sector,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) <= 90 THEN 1 ELSE 0 END) as stock_corriente
FROM stock_filtrado
GROUP BY 1, 2, 3;

CREATE INDEX idx_mv_aviso_obra_mh_fecha ON mv_aviso_obra_metas_historico(fecha_corte);
CREATE INDEX idx_mv_aviso_obra_mh_trata ON mv_aviso_obra_metas_historico(trata);

-- --- FIN: aviso_obra/14_aviso_obra_metas_historico.sql ---

-- --- INICIO: morfologia/14_morfologia_metas_historico.sql ---
-- ============================================================
-- MORFOLOGIA 14: mv_morfologia_metas_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_morfologia_metas_historico CASCADE;
DROP TYPE IF EXISTS mv_morfologia_metas_historico CASCADE;

CREATE MATERIALIZED VIEW mv_morfologia_metas_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'morfologia'
    LIMIT 1
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        fc.fecha_corte,
        u.fecha_primer_ingreso_gerencia,
        p.destinatario AS destinatario_cierre
    FROM mv_morfologia_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente 
       AND a.usuario_alta = dpc.destinatario_cierre 
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte 
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
),
stock_filtrado AS (
    SELECT 
        dpc.fecha_corte,
        dpc.trata,
        dpc.fecha_primer_ingreso_gerencia
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    LEFT JOIN subsanacion_abierta_al_cierre sac 
        ON sac.id_expediente = dpc.id_expediente 
       AND sac.fecha_corte = dpc.fecha_corte
    WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
      AND COALESCE(sac.tiene_subsanacion_abierta, FALSE) IS FALSE
)
SELECT 
    fecha_corte,
    to_char(fecha_corte, 'YYYY-MM') as mes_label,
    trata,
    COUNT(*) as total_stock,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) > 90 THEN 1 ELSE 0 END) as stock_sector,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) <= 90 THEN 1 ELSE 0 END) as stock_corriente
FROM stock_filtrado
GROUP BY 1, 2, 3;

CREATE INDEX idx_mv_morfologia_mh_fecha ON mv_morfologia_metas_historico(fecha_corte);
CREATE INDEX idx_mv_morfologia_mh_trata ON mv_morfologia_metas_historico(trata);

-- --- FIN: morfologia/14_morfologia_metas_historico.sql ---

-- --- INICIO: aph/14_aph_metas_historico.sql ---
-- ============================================================
-- APH 14: mv_aph_metas_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_aph_metas_historico CASCADE;
DROP TYPE IF EXISTS mv_aph_metas_historico CASCADE;

CREATE MATERIALIZED VIEW mv_aph_metas_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'aph'
    LIMIT 1
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        fc.fecha_corte,
        u.fecha_primer_ingreso_gerencia,
        p.destinatario AS destinatario_cierre
    FROM mv_aph_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente 
       AND a.usuario_alta = dpc.destinatario_cierre 
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte 
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
),
stock_filtrado AS (
    SELECT 
        dpc.fecha_corte,
        dpc.trata,
        dpc.fecha_primer_ingreso_gerencia
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    LEFT JOIN subsanacion_abierta_al_cierre sac 
        ON sac.id_expediente = dpc.id_expediente 
       AND sac.fecha_corte = dpc.fecha_corte
    WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
      AND COALESCE(sac.tiene_subsanacion_abierta, FALSE) IS FALSE
)
SELECT 
    fecha_corte,
    to_char(fecha_corte, 'YYYY-MM') as mes_label,
    trata,
    COUNT(*) as total_stock,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) > 90 THEN 1 ELSE 0 END) as stock_sector,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) <= 90 THEN 1 ELSE 0 END) as stock_corriente
FROM stock_filtrado
GROUP BY 1, 2, 3;

CREATE INDEX idx_mv_aph_mh_fecha ON mv_aph_metas_historico(fecha_corte);
CREATE INDEX idx_mv_aph_mh_trata ON mv_aph_metas_historico(trata);

-- --- FIN: aph/14_aph_metas_historico.sql ---

-- --- INICIO: usos/14_usos_metas_historico.sql ---
-- ============================================================
-- USOS 14: mv_usos_metas_historico
-- ============================================================

DROP MATERIALIZED VIEW IF EXISTS mv_usos_metas_historico CASCADE;
DROP TYPE IF EXISTS mv_usos_metas_historico CASCADE;

CREATE MATERIALIZED VIEW mv_usos_metas_historico AS
WITH cfg AS (
    SELECT analistas_oficiales
    FROM cfg_gestion_metas
    WHERE gerencia = 'usos'
    LIMIT 1
),
fechas_corte AS (
    SELECT 
        (date_trunc('month', mes) + INTERVAL '1 month - 1 day')::date AS fecha_corte
    FROM generate_series(
        date_trunc('month', CURRENT_DATE) - INTERVAL '11 months',
        date_trunc('month', CURRENT_DATE),
        INTERVAL '1 month'
    ) AS mes
),
destinatario_por_corte AS (
    SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte)
        u.id_expediente,
        u.trata,
        fc.fecha_corte,
        u.fecha_primer_ingreso_gerencia,
        p.destinatario AS destinatario_cierre
    FROM mv_usos_universo u
    CROSS JOIN fechas_corte fc
    INNER JOIN mvw_ee_pases_secgdu p 
        ON p.id_expediente = u.id_expediente
       AND p.fecha::date <= fc.fecha_corte
    ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
),
subsanacion_abierta_al_cierre AS (
    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
        dpc.id_expediente,
        dpc.fecha_corte,
        TRUE AS tiene_subsanacion_abierta
    FROM destinatario_por_corte dpc
    INNER JOIN mvw_ee_actividades_secgdu a 
        ON a.id_expediente = dpc.id_expediente 
       AND a.usuario_alta = dpc.destinatario_cierre 
       AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
       AND a.fecha_alta::date <= dpc.fecha_corte 
       AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
),
stock_filtrado AS (
    SELECT 
        dpc.fecha_corte,
        dpc.trata,
        dpc.fecha_primer_ingreso_gerencia
    FROM destinatario_por_corte dpc
    CROSS JOIN cfg
    LEFT JOIN subsanacion_abierta_al_cierre sac 
        ON sac.id_expediente = dpc.id_expediente 
       AND sac.fecha_corte = dpc.fecha_corte
    WHERE dpc.destinatario_cierre = ANY(cfg.analistas_oficiales)
      AND COALESCE(sac.tiene_subsanacion_abierta, FALSE) IS FALSE
)
SELECT 
    fecha_corte,
    to_char(fecha_corte, 'YYYY-MM') as mes_label,
    trata,
    COUNT(*) as total_stock,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) > 90 THEN 1 ELSE 0 END) as stock_sector,
    SUM(CASE WHEN (fecha_corte - fecha_primer_ingreso_gerencia::date) <= 90 THEN 1 ELSE 0 END) as stock_corriente
FROM stock_filtrado
GROUP BY 1, 2, 3;

CREATE INDEX idx_mv_usos_mh_fecha ON mv_usos_metas_historico(fecha_corte);
CREATE INDEX idx_mv_usos_mh_trata ON mv_usos_metas_historico(trata);

-- --- FIN: usos/14_usos_metas_historico.sql ---
