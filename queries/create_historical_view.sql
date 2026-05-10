-- Borrar vistas previas
DROP MATERIALIZED VIEW IF EXISTS mvw_reporte_historico_dgroc;

CREATE MATERIALIZED VIEW mvw_reporte_historico_dgroc AS
WITH tramites_metadata (gerencia, trata, nombre_trata, acronimos_list) AS (
    VALUES 
    -- CATASTRO
    ('catastro', 'MDUG0115C', 'Anulación de Propiedad Horizontal', ARRAY['IFMMH']),
    ('catastro', 'MDUG1501L', 'Certificado de cota de parcela nivel cero', ARRAY['IFMAD']),
    ('catastro', 'MDUG0115G', 'Certificado de Determinación de Cinturón Digital', ARRAY['IF']),
    ('catastro', 'MDUG1501H', 'Certificado de información catastral', ARRAY['IFDEX']),
    ('catastro', 'MDUG0134C', 'Certificado de numeración domiciliaria', ARRAY['CECNU']),
    ('catastro', 'MDUG0134N', 'Constitución de Estado Parcelario', ARRAY['IFGPA', 'FIPAR']),
    ('catastro', 'MDUG0146A', 'Copia de plano', ARRAY['IFPCB', 'IFDEX']),
    ('catastro', 'GENE0702C', 'Mensura Regularización Urbana Dominial', ARRAY['PPINV']),
    ('catastro', 'MDUG0115F', 'Plano de mensura de objeto territorial', ARRAY['IFMOT']),
    ('catastro', 'MDUG0115B', 'Plano de Mensura Particular', ARRAY['IFMSC']),
    ('catastro', 'MDUG0132A', 'Plano de prehorizontalidad nuevo', ARRAY['IFMHC']),
    ('catastro', 'MDUG0131A', 'Plano de Propiedad Horizontal modif/compl', ARRAY['IFMHC']),
    ('catastro', 'MDUG0131B', 'Plano de propiedad horizontal nuevo', ARRAY['IFMHC']),
    ('catastro', 'MDUG0115E', 'Rectificación de Plano de Mensura', ARRAY['IFMSC', 'IFMHC']),
    ('catastro', 'MDUG0134E', 'Solicitud de Certificado de fijación de línea', ARRAY['IFMAD']),
    ('catastro', 'MDUG0135A', 'Solicitud de consideración a la DGROC', ARRAY['IFMHC', 'IFMMH', 'IFMAD', 'IFMSC', 'IFMOT', 'IFPCB', 'FIPAR']),
    
    -- INSTALACIONES
    ('instalaciones', 'MDUG2101A', 'Registro de Plano de Prevención contra Incendios', ARRAY['PROIN', 'PLINE', 'IFCIS', 'IFSMC', 'IFRSP']),
    ('instalaciones', 'MDUG2901A', 'Registro de Plano de Elementos Guiados de Transporte', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2501A', 'Registro de Plano de Instalación de Inflamables', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2201A', 'Registro de Plano de Instalación de Ventilación Mecánica', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2701A', 'Registro de Plano de Instalación Eléctrica', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2401A', 'Registro de Plano de Instalación Electromecánica', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2601A', 'Registro de Plano de Instalación Sanitaria', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG2301A', 'Registro de Plano de Instalación Térmica', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG3301A', 'Registro de Plano de Sala de Máquinas', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG0904A', 'Ascenso de Categoría de Foguistas', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG0120A', 'Solicitud Examen de Foguista', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MJGG1601A', 'Registro de planos de prototipo de equipos', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG0101D', 'Ajuste De Instalacion Elementos Guiados De Transporte', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MDUG0101G', 'Ajuste De Instalacion Termica', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    ('instalaciones', 'MJGG1701A', 'Transferencia de Titularidad de Instalación', ARRAY['PROIN', 'PLINE', 'IFSMC']),
    
    -- REGULARIZACION Y CONFORME
    ('regularizacion', 'MDUG0104A', 'Regularización de Plano de Obra Civil', ARRAY['IFROC']),
    ('regularizacion', 'MDUG0141A', 'Registro de plano Conforme', ARRAY['IFPCO', 'IFSMI']),
    ('regularizacion', 'MDUG3001A', 'Registro de Plano de Obra Civil: Registro en Etapa Proyecto (EXPEDIENTES VIEJOS)', ARRAY['IFPCO']),
    ('regularizacion', 'MDUG1501K', 'Permiso de Demolición', ARRAY['IFPDO']),
    
    -- CONTABLE
    ('contable', 'MDUG0901A', 'Registro de Profesionales de Obras y Catastro', ARRAY['IF']),
    ('contable', 'MDUG1501J', 'Permiso de Ejecución de Obra Civil', ARRAY['IFPDO']),
    ('contable', 'MDUG3001A', 'Registro de Plano de Obra Civil: Registro en Etapa Proyecto (EXPEDIENTES QUE CONTINUAN A PERMISOS)', ARRAY['IFPDO']),
    ('contable', 'MDUG3402A', 'Permiso Temprano de Ejecución de Obra Civil', ARRAY['IFPEO', 'IFPDO']),
    
    -- ETAPA PROYECTO
    ('etapa_proyecto', 'MDUG3402A', 'Permiso Temprano de Ejecución de Obra Civil', ARRAY['IFTPT']),
    ('etapa_proyecto', 'MDUG1502A', 'Inico de Micro Obra bajo Responsabilidad Profesional', ARRAY['IFOCD', 'IFBRP']),
    ('etapa_proyecto', 'MDUG4003A', 'MODEL BA', ARRAY['IFOCD']),
    ('etapa_proyecto', 'MDUG0142A', 'Modificación de obra en curso bajo responsabilidad profesional', ARRAY['IFOCD']),
    ('etapa_proyecto', 'MDUG3001A', 'Registro de Plano de Obra Civil: Registro en Etapa Proyecto', ARRAY['IFOCD']),
    
    -- INTERVENCIONES (Catch-all para tratas no contempladas en cada área)
    -- Se eliminan IF y PV para evitar considerar cualquier documento interno como egreso final
    ('catastro', 'INTERVENCIONES', 'Intervenciones', ARRAY['IFMMH', 'IFMAD', 'IFDEX', 'CECNU', 'IFGPA', 'FIPAR', 'IFPCB', 'PPINV', 'IFMOT', 'IFMSC', 'IFMHC', 'PLAN', 'MIXTA', 'CONOT']),
    ('instalaciones', 'INTERVENCIONES', 'Intervenciones', ARRAY['PROIN', 'PLINE', 'IFCIS', 'IFSMC', 'IFRSP']),
    ('regularizacion', 'INTERVENCIONES', 'Intervenciones', ARRAY['IFROC', 'IFPCO', 'IFSMI', 'IFPDO']),
    ('contable', 'INTERVENCIONES', 'Intervenciones', ARRAY['IFPDO', 'IFPEO']),
    ('etapa_proyecto', 'INTERVENCIONES', 'Intervenciones', ARRAY['IFTPT', 'IFOCD', 'IFBRP']),

    -- AVISO DE OBRA
    ('aviso_obra', 'MDUG0102B_AUTO', 'Aviso de Obra (Automático)', ARRAY['IFCAO', 'IFCAC']),
    ('aviso_obra', 'MDUG0102B_DGIUR', 'Aviso de Obra (DGIUR)', ARRAY['IF'])
),
periodos AS (
    SELECT 
        EXTRACT(YEAR FROM s.d)::int as anio, 
        EXTRACT(MONTH FROM s.d)::int as mes,
        (s.d + interval '1 month' - interval '1 day')::date as fin_mes
    FROM generate_series('2024-01-01'::date, '2026-12-01'::date, '1 month'::interval) s(d)
),
expedientes_target AS (
    SELECT id_expediente, trata, CASE WHEN estado ILIKE 'Subsanaci%' OR estado ILIKE 'Subsanación%' THEN 1 ELSE 0 END as is_subs
    FROM mvw_expedientes_tratas_secgdu
),
pases_pre_filtrados AS (
    SELECT p.id_expediente, p.fecha, p.destinatario, 
           LAG(p.destinatario) OVER (PARTITION BY p.id_expediente ORDER BY p.fecha) as remitente
    FROM mvw_ee_pases_secgdu p
),
ingresos_raw AS (
    -- Ingresos Estándar (Basados en Destinatario)
    SELECT p.id_expediente, 
           CASE 
                WHEN p.destinatario IN ('DGROC-CIC', 'DGROC-COPIAPLANO', 'DGROC-DCATDES', 'DGROC-DCATMEN', 'DGROC-DCATPOL', 'DGROC-DCATTIT') THEN 'catastro'
                WHEN p.destinatario IN ('DGROC-ELECTRICAS', 'DGROC-ELEVADORES', 'DGROC-INCENDIO', 'DGROC-SANITARIAS', 'DGROC-TERMICAS', 'DGROC-DCIMYE', 'DGROC-DCIELEV', 'DGROC-DCIDITI') THEN 'instalaciones'
                WHEN p.destinatario IN ('DGROC-OBRASDEMO', 'DGROC-ESPERAINSTALACIONES') THEN 'regularizacion'
                WHEN p.destinatario IN ('DGROC-CONTABLE', 'DGROC-OBRASADMIN', 'DGROC-DCG', 'DGROC-DESCARGOS', 'DGROC-DTACONT', 'DGROC-DTARPS', 'DGROC-LEGAJOS', 'DGROC-REVISIONCONTABLE') THEN 'contable'
                WHEN p.destinatario = 'DGROC-OBRASTECNICA' THEN 'etapa_proyecto'
                WHEN p.destinatario = 'DGROC-AUTOMAT' THEN 'aviso_obra'
           END as gerencia_buzon,
           CASE 
                WHEN p.destinatario = 'DGROC-AUTOMAT' THEN 'MDUG0102B_AUTO'
                ELSE ec.trata 
           END as trata_orig,
           MIN(p.fecha)::date as fecha_ing
    FROM pases_pre_filtrados p
    JOIN expedientes_target ec ON p.id_expediente = ec.id_expediente
    WHERE p.destinatario IN (
        -- SOLAMENTE BUZONES PARA INGRESO (Evita duplicados por pases a analistas)
        'DGROC-CIC', 'DGROC-COPIAPLANO', 'DGROC-DCATDES', 'DGROC-DCATMEN', 'DGROC-DCATPOL', 'DGROC-DCATTIT',
        'DGROC-ELECTRICAS', 'DGROC-ELEVADORES', 'DGROC-INCENDIO', 'DGROC-SANITARIAS', 'DGROC-TERMICAS', 'DGROC-DCIMYE', 'DGROC-DCIELEV', 'DGROC-DCIDITI',
        'DGROC-OBRASDEMO', 'DGROC-ESPERAINSTALACIONES',
        'DGROC-CONTABLE', 'DGROC-OBRASADMIN', 'DGROC-DCG', 'DGROC-DESCARGOS', 'DGROC-DTACONT', 'DGROC-DTARPS', 'DGROC-LEGAJOS', 'DGROC-REVISIONCONTABLE',
        'DGROC-OBRASTECNICA', 'DGROC-AUTOMAT'
    )
    GROUP BY 1, 2, 3
    
    UNION ALL
    
    -- Ingresos DGIUR (Regla Específica: DGROC-AUTOMAT -> DGIUR-21)
    SELECT p.id_expediente, 'aviso_obra' as gerencia_buzon, 'MDUG0102B_DGIUR' as trata_orig,
           MIN(p.fecha)::date as fecha_ing
    FROM pases_pre_filtrados p
    JOIN expedientes_target ec ON p.id_expediente = ec.id_expediente
    WHERE ec.trata = 'MDUG0102B' 
      AND p.destinatario = 'DGIUR-21' 
      AND p.remitente = 'DGROC-AUTOMAT'
    GROUP BY 1, 2, 3
),
ingresos AS (
    SELECT ir.id_expediente, 
           ir.gerencia_buzon as gerencia,
           CASE 
                WHEN ir.trata_orig IN ('MDUG0102B_AUTO', 'MDUG0102B_DGIUR') THEN ir.trata_orig
                WHEN EXISTS (SELECT 1 FROM tramites_metadata tm WHERE tm.gerencia = ir.gerencia_buzon AND tm.trata = ir.trata_orig) THEN ir.trata_orig
                ELSE 'INTERVENCIONES'
           END as trata,
           MIN(ir.fecha_ing) as fecha_ing
    FROM ingresos_raw ir
    GROUP BY 1, 2, 3
),
egresos_efectivos AS (
    SELECT g.id_expediente, i.trata, i.gerencia, MIN(g.fecha_creacion)::date as fecha_egr
    FROM mvw_datos_gedo_secgdu g
    JOIN ingresos i ON g.id_expediente = i.id_expediente
    JOIN tramites_metadata tm ON i.trata = tm.trata AND i.gerencia = tm.gerencia
    WHERE g.acronimo = ANY(tm.acronimos_list)
      AND g.fecha_creacion >= i.fecha_ing
      -- Filtro especial para DGIUR: Firmantes específicos
      AND (i.trata != 'MDUG0102B_DGIUR' OR g.usuario_creador IN ('VASTAM', 'ALANDAZURI', 'FVERDAGUER', 'VGAYTAN', 'ZONCA', 'CGIRAUD'))
      -- Filtro especial para Profesionales
      AND (tm.trata != 'MDUG0901A' OR g.usuario_creador IN ('FABIANSANTILLAN', 'LICETB'))
    GROUP BY g.id_expediente, i.trata, i.gerencia
    
    UNION ALL
    
    -- EGRESO EFECTIVO PARA INTERVENCIONES: Pase de salida del área REALIZADO POR UN ANALISTA
    -- Según requerimiento: El egreso es efectivo cuando el analista lo termina y lo manda a otra área.
    -- Se restringe el remitente a solo los analistas de la Whitelist (evitando egresos desde buzones).
    SELECT p.id_expediente, 'INTERVENCIONES' as trata, i.gerencia, MIN(p.fecha)::date as fecha_egr
    FROM pases_pre_filtrados p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    WHERE i.trata = 'INTERVENCIONES'
      AND p.fecha > i.fecha_ing
      AND (
          (i.gerencia = 'catastro' AND p.remitente IN ('ACOSTAPA', 'AFAHLER', 'AGUSMAZZONI', 'ALEALFONSIN', 'ALEGREM', 'ARGENTOES', 'BARTROLIG', 'CABRERAM', 'CANALEAL', 'CARBONELLIM', 'CHIANETTAR', 'CIOPKOG', 'CISTERNACA', 'COHENCAD', 'CONTIL', 'CONVERTID', 'DELGADODE', 'DIBIASEO', 'DIEZGASTON', 'DIHARCEP', 'DURSIM', 'ECIJAN', 'FMARCHISELLA', 'FOLLONIERLE', 'FREIXASC', 'GARCIASIL', 'GILESJP', 'GONZALEZAMA', 'GONZALEZHORAC', 'GUZMANO', 'IGARZABALP', 'JTIRADO', 'LAGUNAMA', 'LBELLY', 'LOISIG', 'LUCCIC', 'M.NAPOLI', 'MALATTOR', 'MANNOP', 'MARCHETTIJ', 'MHOSBALIKCIYAN', 'MOSCOVICHA', 'NCITRANGOLO', 'NOGUERAH', 'NPONZO', 'NQUINTERNO', 'PONZOS', 'ROLDANG', 'SALGUEROM', 'SORIAANDREA', 'TARRUA', 'TAVELLAE', 'VEGAJ', 'VILLAGI', 'WVIRGILIO') AND p.destinatario NOT IN ('ACOSTAPA', 'AFAHLER', 'AGUSMAZZONI', 'ALEALFONSIN', 'ALEGREM', 'ARGENTOES', 'BARTROLIG', 'CABRERAM', 'CANALEAL', 'CARBONELLIM', 'CHIANETTAR', 'CIOPKOG', 'CISTERNACA', 'COHENCAD', 'CONTIL', 'CONVERTID', 'DELGADODE', 'DGROC-CIC', 'DGROC-COPIAPLANO', 'DGROC-DCATDES', 'DGROC-DCATMEN', 'DGROC-DCATPOL', 'DGROC-DCATTIT', 'DIBIASEO', 'DIEZGASTON', 'DIHARCEP', 'DURSIM', 'ECIJAN', 'FMARCHISELLA', 'FOLLONIERLE', 'FREIXASC', 'GARCIASIL', 'GILESJP', 'GONZALEZAMA', 'GONZALEZHORAC', 'GUZMANO', 'IGARZABALP', 'JTIRADO', 'LAGUNAMA', 'LBELLY', 'LOISIG', 'LUCCIC', 'M.NAPOLI', 'MALATTOR', 'MANNOP', 'MARCHETTIJ', 'MHOSBALIKCIYAN', 'MOSCOVICHA', 'NCITRANGOLO', 'NOGUERAH', 'NPONZO', 'NQUINTERNO', 'PONZOS', 'ROLDANG', 'SALGUEROM', 'SORIAANDREA', 'TARRUA', 'TAVELLAE', 'VEGAJ', 'VILLAGI', 'WVIRGILIO'))
          OR
          (i.gerencia = 'instalaciones' AND p.remitente IN ('AQUINOLUCAS', 'ARENAJ', 'ARGUELLOJ', 'BATALLANJ', 'BENITOG', 'BRIANMARTINEZ', 'CORNAZM', 'FICARRAR', 'GAGLIARDIA', 'LOPARDOC', 'QUEIJASGUILLINP', 'ROBLEDOJO', 'ROLDANMI', 'RUDAC', 'SARIDISD', 'TOLESANOA', 'AURENA', 'BATALLANGE', 'BRITANP', 'GUARDADOB', 'JDECIMA', 'PEREZGA', 'RODRIGUEZESTEBAN', 'RODRIGUEZNE', 'SILESC', 'VILLAGAB', 'ABCRAGNO', 'AGARCIAFIGUEROA', 'CABRERAARI', 'CAFELICE', 'CAPOZZOG', 'CSALGUERO', 'DARANGURI', 'DMOFFA', 'FUHRY', 'GONMAR', 'J.OLIVERA', 'LOPEZFE', 'MARIANELAROCARO', 'MBALDOME', 'MLMAMONE', 'MTRENQUE', 'NIEVAL', 'PCHERBENCO', 'RADAA', 'RIOSFE', 'ROMANOFLA', 'SANTACRUZ', 'CANTARELLTORRES', 'CIRIAE', 'LOIACONOANA', 'MCDIAMANTI', 'POUSAF', 'ARGUELLOSOL', 'COSSM', 'EIERACI', 'HAMALAG', 'RUIZMA', 'BRITANG', 'ENCISOROMERO', 'PITTERIE', 'WIERZBICKIIGOR') AND p.destinatario NOT IN ('AQUINOLUCAS', 'ARENAJ', 'ARGUELLOJ', 'BATALLANJ', 'BENITOG', 'BRIANMARTINEZ', 'CORNAZM', 'DGROC-DCIMYE', 'DGROC-ELECTRICAS', 'FICARRAR', 'GAGLIARDIA', 'LOPARDOC', 'QUEIJASGUILLINP', 'ROBLEDOJO', 'ROLDANMI', 'RUDAC', 'SARIDISD', 'TOLESANOA', 'AURENA', 'BATALLANGE', 'BRITANP', 'DGROC-DCIELEV', 'DGROC-ELEVADORES', 'DGROC-OBSDCIELEV', 'GUARDADOB', 'JDECIMA', 'PEREZGA', 'RODRIGUEZESTEBAN', 'RODRIGUEZNE', 'SILESC', 'VILLAGAB', 'ABCRAGNO', 'AGARCIAFIGUEROA', 'CABRERAARI', 'CAFELICE', 'CAPOZZOG', 'CSALGUERO', 'DARANGURI', 'DGROC-DCIDITI', 'DGROC-ESPERAAGCINCENDIO', 'DGROC-INCENDIO', 'DMOFFA', 'FUHRY', 'GONMAR', 'J.OLIVERA', 'LOPEZFE', 'MARIANELAROCARO', 'MBALDOME', 'MLMAMONE', 'MTRENQUE', 'NIEVAL', 'PCHERBENCO', 'RADAA', 'RIOSFE', 'ROMANOFLA', 'SANTACRUZ', 'CANTARELLTORRES', 'CIRIAE', 'LOIACONOANA', 'MCDIAMANTI', 'POUSAF', 'ARGUELLOSOL', 'COSSM', 'DGROC-SANITARIAS', 'EIERACI', 'HAMALAG', 'RUIZMA', 'BRITANG', 'DGROC-TERMICAS', 'ENCISOROMERO', 'PITTERIE', 'WIERZBICKIIGOR'))
          OR
          (i.gerencia = 'regularizacion' AND p.remitente IN ('AGUEROJO', 'AKRACOFF', 'ALVAREZ.M', 'ARAOZLUIS', 'ATENCIOAL', 'DALBORAF', 'ENCISOA', 'EPARLATO', 'ERDOCIAINA', 'JBARRACO', 'JLGARMENDIA', 'JTERRILE', 'MYUSHU', 'S.SANCHEZPAZ', 'SCAVALLARO') AND p.destinatario NOT IN ('AGUEROJO', 'AKRACOFF', 'ALVAREZ.M', 'ARAOZLUIS', 'ATENCIOAL', 'DALBORAF', 'DGROC-ESPERAINSTALACIONES', 'DGROC-OBRASDEMO', 'ENCISOA', 'EPARLATO', 'ERDOCIAINA', 'JBARRACO', 'JLGARMENDIA', 'JTERRILE', 'MYUSHU', 'S.SANCHEZPAZ', 'SCAVALLARO'))
          OR
          (i.gerencia = 'contable' AND p.remitente IN ('AMONTEVERDE', 'AMORINC', 'CARLOSDUARTE', 'CAROJAS', 'COLOTTAP', 'CPENDON', 'DAS', 'DASTUGUEO', 'DEGODOY', 'DIAZBAR', 'DKRENZ', 'EDEFEO', 'FABIANSANTILLAN', 'FMHERRERA', 'FSPANTI', 'GARCIASEBA', 'HRICCIARDI', 'JOSEMARIAORTIZ', 'JPOMAR', 'JULILOPARDO', 'LAMORGIAKA', 'LBARRIENTOS', 'LICETB', 'M.ROSSO', 'MARQUEZMAR', 'MARTINEZCLA', 'MLAURITO', 'MMALACALZA', 'NMONTEVERDE', 'NMORENO', 'POVIEDO', 'PRESAF', 'PVACEVEDO', 'RIVERAMA', 'ROBLEDOE', 'RODRIGUEZLEA', 'RODRIGUEZMAGD', 'ROSARIODECRIS', 'SCHULERG', 'SENING', 'SMERMOZ', 'SORIAD', 'SPOSAROAL', 'TATOJ', 'TIRENDIC', 'TOMIPITES', 'VICSOLMORE', 'VILLACRI') AND p.destinatario NOT IN ('AMONTEVERDE', 'AMORINC', 'CARLOSDUARTE', 'CAROJAS', 'COLOTTAP', 'CPENDON', 'DAS', 'DASTUGUEO', 'DEGODOY', 'DGROC-AUTOMAT', 'DGROC-CONTABLE', 'DGROC-DCG', 'DGROC-DESCARGOS', 'DGROC-DTACONT', 'DGROC-DTARPS', 'DGROC-LEGAJOS', 'DGROC-OBRASADMIN', 'DGROC-PENDIENTESDEPAGO', 'DGROC-REVISIONCONTABLE', 'DIAZBAR', 'DKRENZ', 'EDEFEO', 'FABIANSANTILLAN', 'FMHERRERA', 'FSPANTI', 'GARCIASEBA', 'HRICCIARDI', 'JOSEMARIAORTIZ', 'JPOMAR', 'JULILOPARDO', 'LAMORGIAKA', 'LBARRIENTOS', 'LICETB', 'M.ROSSO', 'MARQUEZMAR', 'MARTINEZCLA', 'MLAURITO', 'MMALACALZA', 'NMONTEVERDE', 'NMORENO', 'POVIEDO', 'PRESAF', 'PVACEVEDO', 'RIVERAMA', 'ROBLEDOE', 'RODRIGUEZLEA', 'RODRIGUEZMAGD', 'ROSARIODECRIS', 'SCHULERG', 'SENING', 'SMERMOZ', 'SORIAD', 'SPOSAROAL', 'TATOJ', 'TIRENDIC', 'TOMIPITES', 'VICSOLMORE', 'VILLACRI'))
          OR
          (i.gerencia = 'etapa_proyecto' AND p.remitente IN ('A.PEREZ', 'AGUSDEMARCO', 'ANTOVERA', 'BELOCURESJ', 'COIROL', 'DBECERRACURITIMA', 'DIMASOM', 'DNKAINSKY', 'FORGIONEA', 'GAILLURJP', 'GARRIONDO', 'JOSEFINA.P', 'M.SANCHEZ', 'MARCE.TOSONI', 'MARCETOSONI', 'MARCETOSONI1', 'MBRISA', 'MCANOGARAY', 'MCARLUCCIO', 'MGALLARDOC', 'MSTIBERTI', 'NLOPEZQUIROGA', 'ROCABERTJ', 'SPUET', 'TALAMOM', 'VERA') AND p.destinatario NOT IN ('A.PEREZ', 'AGUSDEMARCO', 'ANTOVERA', 'BELOCURESJ', 'COIROL', 'DBECERRACURITIMA', 'DGROC-OBRASTECNICA', 'DIMASOM', 'DNKAINSKY', 'FORGIONEA', 'GAILLURJP', 'GARRIONDO', 'JOSEFINA.P', 'M.SANCHEZ', 'MARCE.TOSONI', 'MARCETOSONI', 'MARCETOSONI1', 'MBRISA', 'MCANOGARAY', 'MCARLUCCIO', 'MGALLARDOC', 'MSTIBERTI', 'NLOPEZQUIROGA', 'ROCABERTJ', 'SPUET', 'TALAMOM', 'VERA'))
      )
    GROUP BY p.id_expediente, i.trata, i.gerencia
),
egresos_no_efectivos_raw AS (
    -- Pases a Guarda Temporal
    SELECT p.id_expediente, i.trata, i.gerencia, MIN(p.fecha)::date as fecha_egr
    FROM mvw_ee_pases_secgdu p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    WHERE (p.estado = 'Guarda Temporal' OR p.destinatario = 'GUARDA TEMPORAL')
      AND p.fecha > i.fecha_ing
    GROUP BY p.id_expediente, i.trata, i.gerencia
    
    UNION ALL
    
    -- IFCFP como Egreso No Efectivo para Aviso de Obra
    SELECT g.id_expediente, i.trata, i.gerencia, MIN(g.fecha_creacion)::date as fecha_egr
    FROM mvw_datos_gedo_secgdu g
    JOIN ingresos i ON g.id_expediente = i.id_expediente
    WHERE i.trata IN ('MDUG0102B_AUTO', 'MDUG0102B_DGIUR')
      AND g.acronimo = 'IFCFP'
      AND g.fecha_creacion >= i.fecha_ing
    GROUP BY g.id_expediente, i.trata, i.gerencia
    
    UNION ALL
    
    -- TRANSFERENCIA: AUTO -> DGIUR (Egreso para AUTO)
    SELECT p.id_expediente, 'MDUG0102B_AUTO' as trata, 'aviso_obra' as gerencia, MIN(p.fecha)::date as fecha_egr
    FROM pases_pre_filtrados p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    WHERE i.trata = 'MDUG0102B_AUTO'
      AND p.destinatario = 'DGIUR-21'
      AND p.remitente = 'DGROC-AUTOMAT'
      AND p.fecha > i.fecha_ing
    GROUP BY p.id_expediente
),
egresos_no_efectivos AS (
    SELECT id_expediente, trata, gerencia, MIN(fecha_egr) as fecha_egr
    FROM egresos_no_efectivos_raw
    WHERE trata != 'INTERVENCIONES' -- Por requerimiento: No hay Guarda Temporal para Intervenciones
    GROUP BY id_expediente, trata, gerencia
),
status_final AS (
    SELECT 
        i.id_expediente, i.trata, i.gerencia, i.fecha_ing,
        COALESCE(ee.fecha_egr, en.fecha_egr) as fecha_egr,
        CASE 
            WHEN ee.id_expediente IS NOT NULL THEN 'EF' 
            WHEN en.id_expediente IS NOT NULL THEN 'NE' 
            ELSE NULL 
        END as tipo_egr,
        ec.is_subs
    FROM ingresos i
    JOIN expedientes_target ec ON i.id_expediente = ec.id_expediente
    LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente AND i.trata = ee.trata
    LEFT JOIN egresos_no_efectivos en ON i.id_expediente = en.id_expediente AND i.trata = en.trata AND ee.id_expediente IS NULL
)
SELECT 
    tm.gerencia as "GERENCIA",
    tm.trata as "COD TRATA",
    tm.nombre_trata as "DETALLE TRATA",
    per.anio,
    per.mes,
    COUNT(*) FILTER (WHERE s.fecha_ing >= date_trunc('month', per.fin_mes) AND s.fecha_ing <= per.fin_mes) as "ING",
    COUNT(*) FILTER (WHERE s.fecha_egr >= date_trunc('month', per.fin_mes) AND s.fecha_egr <= per.fin_mes AND s.tipo_egr = 'EF') as "EGR_EF",
    COUNT(*) FILTER (WHERE s.fecha_egr >= date_trunc('month', per.fin_mes) AND s.fecha_egr <= per.fin_mes AND s.tipo_egr = 'NE') as "EGR_NE",
    
    -- STOCK SUBSANACIONES (Sin cambios, es lo que está en estado Subsanación)
    COUNT(*) FILTER (WHERE s.fecha_ing <= per.fin_mes AND (s.fecha_egr IS NULL OR s.fecha_egr > per.fin_mes) AND s.is_subs = 1) as "STOCK_SUBS",
    
    -- STOCK TOTAL REDEFINIDO: Suma de Propio (Whitelist) + Subsanaciones
    (
        COUNT(*) FILTER (
            WHERE s.fecha_ing <= per.fin_mes 
              AND (s.fecha_egr IS NULL OR s.fecha_egr > per.fin_mes)
              AND s.is_subs = 0
              AND (
                  (tm.gerencia = 'catastro' AND (
                      SELECT p.destinatario 
                      FROM mvw_ee_pases_secgdu p 
                      WHERE p.id_expediente = s.id_expediente AND p.fecha <= per.fin_mes 
                      ORDER BY p.fecha DESC LIMIT 1
                  ) IN (
                      'ACOSTAPA', 'AFAHLER', 'AGUSMAZZONI', 'ALEALFONSIN', 'ALEGREM', 'ARGENTOES',
                      'BARTROLIG', 'CABRERAM', 'CANALEAL', 'CARBONELLIM', 'CHIANETTAR', 'CIOPKOG',
                      'CISTERNACA', 'COHENCAD', 'CONTIL', 'CONVERTID', 'DELGADODE', 'DGROC-CIC',
                      'DGROC-COPIAPLANO', 'DGROC-DCATDES', 'DGROC-DCATMEN', 'DGROC-DCATPOL',
                      'DGROC-DCATTIT', 'DIBIASEO', 'DIEZGASTON', 'DIHARCEP', 'DURSIM', 'ECIJAN',
                      'FMARCHISELLA', 'FOLLONIERLE', 'FREIXASC', 'GARCIASIL', 'GILESJP', 'GONZALEZAMA',
                      'GONZALEZHORAC', 'GUZMANO', 'IGARZABALP', 'JTIRADO', 'LAGUNAMA', 'LBELLY',
                      'LOISIG', 'LUCCIC', 'M.NAPOLI', 'MALATTOR', 'MANNOP', 'MARCHETTIJ',
                      'MHOSBALIKCIYAN', 'MOSCOVICHA', 'NCITRANGOLO', 'NOGUERAH', 'NPONZO',
                      'NQUINTERNO', 'PONZOS', 'ROLDANG', 'SALGUEROM', 'SORIAANDREA', 'TARRUA',
                      'TAVELLAE', 'VEGAJ', 'VILLAGI', 'WVIRGILIO'
                  ))
                  OR
                  (tm.gerencia = 'regularizacion' AND (
                      SELECT p.destinatario 
                      FROM mvw_ee_pases_secgdu p 
                      WHERE p.id_expediente = s.id_expediente AND p.fecha <= per.fin_mes 
                      ORDER BY p.fecha DESC LIMIT 1
                  ) IN (
                      'AGUEROJO', 'AKRACOFF', 'ALVAREZ.M', 'ARAOZLUIS', 'ATENCIOAL', 'DALBORAF',
                      'DGROC-ESPERAINSTALACIONES', 'DGROC-OBRASDEMO', 'ENCISOA', 'EPARLATO',
                      'ERDOCIAINA', 'JBARRACO', 'JLGARMENDIA', 'JTERRILE', 'MYUSHU', 'S.SANCHEZPAZ',
                      'SCAVALLARO'
                  ))
                  OR
                  (tm.gerencia = 'instalaciones' AND (
                      SELECT p.destinatario 
                      FROM mvw_ee_pases_secgdu p 
                      WHERE p.id_expediente = s.id_expediente AND p.fecha <= per.fin_mes 
                      ORDER BY p.fecha DESC LIMIT 1
                  ) IN (
                      'AQUINOLUCAS', 'ARENAJ', 'ARGUELLOJ', 'BATALLANJ', 'BENITOG', 'BRIANMARTINEZ',
                      'CORNAZM', 'DGROC-DCIMYE', 'DGROC-ELECTRICAS', 'FICARRAR', 'GAGLIARDIA',
                      'LOPARDOC', 'QUEIJASGUILLINP', 'ROBLEDOJO', 'ROLDANMI', 'RUDAC', 'SARIDISD',
                      'TOLESANOA', 'AURENA', 'BATALLANGE', 'BRITANP', 'DGROC-DCIELEV', 'DGROC-ELEVADORES',
                      'DGROC-OBSDCIELEV', 'GUARDADOB', 'JDECIMA', 'PEREZGA', 'RODRIGUEZESTEBAN',
                      'RODRIGUEZNE', 'SILESC', 'VILLAGAB', 'ABCRAGNO', 'AGARCIAFIGUEROA', 'CABRERAARI',
                      'CAFELICE', 'CAPOZZOG', 'CSALGUERO', 'DARANGURI', 'DGROC-DCIDITI',
                      'DGROC-ESPERAAGCINCENDIO', 'DGROC-INCENDIO', 'DMOFFA', 'FUHRY', 'GONMAR',
                      'J.OLIVERA', 'LOPEZFE', 'MARIANELAROCARO', 'MBALDOME', 'MLMAMONE', 'MTRENQUE',
                      'NIEVAL', 'PCHERBENCO', 'RADAA', 'RIOSFE', 'ROMANOFLA', 'SANTACRUZ',
                      'CANTARELLTORRES', 'CIRIAE', 'LOIACONOANA', 'MCDIAMANTI', 'POUSAF', 'ARGUELLOSOL',
                      'COSSM', 'DGROC-SANITARIAS', 'EIERACI', 'HAMALAG', 'RUIZMA', 'BRITANG',
                      'DGROC-TERMICAS', 'ENCISOROMERO', 'PITTERIE', 'WIERZBICKIIGOR'
                  ))
                  OR
                  (tm.gerencia = 'contable' AND (
                      SELECT p.destinatario 
                      FROM mvw_ee_pases_secgdu p 
                      WHERE p.id_expediente = s.id_expediente AND p.fecha <= per.fin_mes 
                      ORDER BY p.fecha DESC LIMIT 1
                  ) IN (
                      'AMONTEVERDE', 'AMORINC', 'CARLOSDUARTE', 'CAROJAS', 'COLOTTAP', 'CPENDON',
                      'DAS', 'DASTUGUEO', 'DEGODOY', 'DGROC-AUTOMAT', 'DGROC-CONTABLE', 'DGROC-DCG',
                      'DGROC-DESCARGOS', 'DGROC-DTACONT', 'DGROC-DTARPS', 'DGROC-LEGAJOS',
                      'DGROC-OBRASADMIN', 'DGROC-PENDIENTESDEPAGO', 'DGROC-REVISIONCONTABLE',
                      'DIAZBAR', 'DKRENZ', 'EDEFEO', 'FABIANSANTILLAN', 'FMHERRERA', 'FSPANTI',
                      'GARCIASEBA', 'HRICCIARDI', 'JOSEMARIAORTIZ', 'JPOMAR', 'JULILOPARDO',
                      'LAMORGIAKA', 'LBARRIENTOS', 'LICETB', 'M.ROSSO', 'MARQUEZMAR', 'MARTINEZCLA',
                      'MLAURITO', 'MMALACALZA', 'NMONTEVERDE', 'NMORENO', 'POVIEDO', 'PRESAF',
                      'PVACEVEDO', 'RIVERAMA', 'ROBLEDOE', 'RODRIGUEZLEA', 'RODRIGUEZMAGD',
                      'ROSARIODECRIS', 'SCHULERG', 'SENING', 'SMERMOZ', 'SORIAD', 'SPOSAROAL',
                      'TATOJ', 'TIRENDIC', 'TOMIPITES', 'VICSOLMORE', 'VILLACRI'
                  ))
                  OR
                  (tm.gerencia = 'etapa_proyecto' AND (
                      SELECT p.destinatario 
                      FROM mvw_ee_pases_secgdu p 
                      WHERE p.id_expediente = s.id_expediente AND p.fecha <= per.fin_mes 
                      ORDER BY p.fecha DESC LIMIT 1
                  ) IN (
                      'A.PEREZ', 'AGUSDEMARCO', 'ANTOVERA', 'BELOCURESJ', 'COIROL',
                      'DBECERRACURITIMA', 'DGROC-OBRASTECNICA', 'DIMASOM', 'DNKAINSKY',
                      'FORGIONEA', 'GAILLURJP', 'GARRIONDO', 'JOSEFINA.P', 'M.SANCHEZ',
                      'MARCE.TOSONI', 'MARCETOSONI', 'MARCETOSONI1', 'MBRISA', 'MCANOGARAY',
                      'MCARLUCCIO', 'MGALLARDOC', 'MSTIBERTI', 'NLOPEZQUIROGA', 'ROCABERTJ',
                      'SPUET', 'TALAMOM', 'VERA'
                  ))
                  OR
                  (tm.gerencia NOT IN ('catastro', 'regularizacion', 'instalaciones', 'contable', 'etapa_proyecto'))
              )
        ) 
        + 
        COUNT(*) FILTER (WHERE s.fecha_ing <= per.fin_mes AND (s.fecha_egr IS NULL OR s.fecha_egr > per.fin_mes) AND s.is_subs = 1)
    ) as "STOCK_TOTAL",
    (COUNT(*) FILTER (WHERE s.fecha_ing <= per.fin_mes AND (s.fecha_egr IS NULL OR s.fecha_egr > per.fin_mes)) - 
     COUNT(*) FILTER (WHERE s.fecha_ing <= per.fin_mes AND (s.fecha_egr IS NULL OR s.fecha_egr > per.fin_mes) AND s.is_subs = 1)) as "STOCK_PROPIO_OLD",
    
    -- NUEVA LOGICA: STOCK PROPIO FILTRADO POR WHITELIST (CATASTRO, REGULARIZACION, INSTALACIONES, CONTABLE Y ETAPA_PROYECTO)
    COUNT(*) FILTER (
        WHERE s.fecha_ing <= per.fin_mes 
          AND (s.fecha_egr IS NULL OR s.fecha_egr > per.fin_mes)
          AND s.is_subs = 0
          AND (
              (tm.gerencia = 'catastro' AND (
                  SELECT p.destinatario 
                  FROM mvw_ee_pases_secgdu p 
                  WHERE p.id_expediente = s.id_expediente AND p.fecha <= per.fin_mes 
                  ORDER BY p.fecha DESC LIMIT 1
              ) IN (
                  'ACOSTAPA', 'AFAHLER', 'AGUSMAZZONI', 'ALEALFONSIN', 'ALEGREM', 'ARGENTOES',
                  'BARTROLIG', 'CABRERAM', 'CANALEAL', 'CARBONELLIM', 'CHIANETTAR', 'CIOPKOG',
                  'CISTERNACA', 'COHENCAD', 'CONTIL', 'CONVERTID', 'DELGADODE', 'DGROC-CIC',
                  'DGROC-COPIAPLANO', 'DGROC-DCATDES', 'DGROC-DCATMEN', 'DGROC-DCATPOL',
                  'DGROC-DCATTIT', 'DIBIASEO', 'DIEZGASTON', 'DIHARCEP', 'DURSIM', 'ECIJAN',
                  'FMARCHISELLA', 'FOLLONIERLE', 'FREIXASC', 'GARCIASIL', 'GILESJP', 'GONZALEZAMA',
                  'GONZALEZHORAC', 'GUZMANO', 'IGARZABALP', 'JTIRADO', 'LAGUNAMA', 'LBELLY',
                  'LOISIG', 'LUCCIC', 'M.NAPOLI', 'MALATTOR', 'MANNOP', 'MARCHETTIJ',
                  'MHOSBALIKCIYAN', 'MOSCOVICHA', 'NCITRANGOLO', 'NOGUERAH', 'NPONZO',
                  'NQUINTERNO', 'PONZOS', 'ROLDANG', 'SALGUEROM', 'SORIAANDREA', 'TARRUA',
                  'TAVELLAE', 'VEGAJ', 'VILLAGI', 'WVIRGILIO'
              ))
              OR
              (tm.gerencia = 'regularizacion' AND (
                  SELECT p.destinatario 
                  FROM mvw_ee_pases_secgdu p 
                  WHERE p.id_expediente = s.id_expediente AND p.fecha <= per.fin_mes 
                  ORDER BY p.fecha DESC LIMIT 1
              ) IN (
                  'AGUEROJO', 'AKRACOFF', 'ALVAREZ.M', 'ARAOZLUIS', 'ATENCIOAL', 'DALBORAF',
                  'DGROC-ESPERAINSTALACIONES', 'DGROC-OBRASDEMO', 'ENCISOA', 'EPARLATO',
                  'ERDOCIAINA', 'JBARRACO', 'JLGARMENDIA', 'JTERRILE', 'MYUSHU', 'S.SANCHEZPAZ',
                  'SCAVALLARO'
              ))
              OR
              (tm.gerencia = 'instalaciones' AND (
                  SELECT p.destinatario 
                  FROM mvw_ee_pases_secgdu p 
                  WHERE p.id_expediente = s.id_expediente AND p.fecha <= per.fin_mes 
                  ORDER BY p.fecha DESC LIMIT 1
              ) IN (
                  'AQUINOLUCAS', 'ARENAJ', 'ARGUELLOJ', 'BATALLANJ', 'BENITOG', 'BRIANMARTINEZ',
                  'CORNAZM', 'DGROC-DCIMYE', 'DGROC-ELECTRICAS', 'FICARRAR', 'GAGLIARDIA',
                  'LOPARDOC', 'QUEIJASGUILLINP', 'ROBLEDOJO', 'ROLDANMI', 'RUDAC', 'SARIDISD',
                  'TOLESANOA', 'AURENA', 'BATALLANGE', 'BRITANP', 'DGROC-DCIELEV', 'DGROC-ELEVADORES',
                  'DGROC-OBSDCIELEV', 'GUARDADOB', 'JDECIMA', 'PEREZGA', 'RODRIGUEZESTEBAN',
                  'RODRIGUEZNE', 'SILESC', 'VILLAGAB', 'ABCRAGNO', 'AGARCIAFIGUEROA', 'CABRERAARI',
                  'CAFELICE', 'CAPOZZOG', 'CSALGUERO', 'DARANGURI', 'DGROC-DCIDITI',
                  'DGROC-ESPERAAGCINCENDIO', 'DGROC-INCENDIO', 'DMOFFA', 'FUHRY', 'GONMAR',
                  'J.OLIVERA', 'LOPEZFE', 'MARIANELAROCARO', 'MBALDOME', 'MLMAMONE', 'MTRENQUE',
                  'NIEVAL', 'PCHERBENCO', 'RADAA', 'RIOSFE', 'ROMANOFLA', 'SANTACRUZ',
                  'CANTARELLTORRES', 'CIRIAE', 'LOIACONOANA', 'MCDIAMANTI', 'POUSAF', 'ARGUELLOSOL',
                  'COSSM', 'DGROC-SANITARIAS', 'EIERACI', 'HAMALAG', 'RUIZMA', 'BRITANG',
                  'DGROC-TERMICAS', 'ENCISOROMERO', 'PITTERIE', 'WIERZBICKIIGOR'
              ))
              OR
              (tm.gerencia = 'contable' AND (
                  SELECT p.destinatario 
                  FROM mvw_ee_pases_secgdu p 
                  WHERE p.id_expediente = s.id_expediente AND p.fecha <= per.fin_mes 
                  ORDER BY p.fecha DESC LIMIT 1
              ) IN (
                  'AMONTEVERDE', 'AMORINC', 'CARLOSDUARTE', 'CAROJAS', 'COLOTTAP', 'CPENDON',
                  'DAS', 'DASTUGUEO', 'DEGODOY', 'DGROC-AUTOMAT', 'DGROC-CONTABLE', 'DGROC-DCG',
                  'DGROC-DESCARGOS', 'DGROC-DTACONT', 'DGROC-DTARPS', 'DGROC-LEGAJOS',
                  'DGROC-OBRASADMIN', 'DGROC-PENDIENTESDEPAGO', 'DGROC-REVISIONCONTABLE',
                  'DIAZBAR', 'DKRENZ', 'EDEFEO', 'FABIANSANTILLAN', 'FMHERRERA', 'FSPANTI',
                  'GARCIASEBA', 'HRICCIARDI', 'JOSEMARIAORTIZ', 'JPOMAR', 'JULILOPARDO',
                  'LAMORGIAKA', 'LBARRIENTOS', 'LICETB', 'M.ROSSO', 'MARQUEZMAR', 'MARTINEZCLA',
                  'MLAURITO', 'MMALACALZA', 'NMONTEVERDE', 'NMORENO', 'POVIEDO', 'PRESAF',
                  'PVACEVEDO', 'RIVERAMA', 'ROBLEDOE', 'RODRIGUEZLEA', 'RODRIGUEZMAGD',
                  'ROSARIODECRIS', 'SCHULERG', 'SENING', 'SMERMOZ', 'SORIAD', 'SPOSAROAL',
                  'TATOJ', 'TIRENDIC', 'TOMIPITES', 'VICSOLMORE', 'VILLACRI'
              ))
              OR
              (tm.gerencia = 'etapa_proyecto' AND (
                  SELECT p.destinatario 
                  FROM mvw_ee_pases_secgdu p 
                  WHERE p.id_expediente = s.id_expediente AND p.fecha <= per.fin_mes 
                  ORDER BY p.fecha DESC LIMIT 1
              ) IN (
                  'A.PEREZ', 'AGUSDEMARCO', 'ANTOVERA', 'BELOCURESJ', 'COIROL',
                  'DBECERRACURITIMA', 'DGROC-OBRASTECNICA', 'DIMASOM', 'DNKAINSKY',
                  'FORGIONEA', 'GAILLURJP', 'GARRIONDO', 'JOSEFINA.P', 'M.SANCHEZ',
                  'MARCE.TOSONI', 'MARCETOSONI', 'MARCETOSONI1', 'MBRISA', 'MCANOGARAY',
                  'MCARLUCCIO', 'MGALLARDOC', 'MSTIBERTI', 'NLOPEZQUIROGA', 'ROCABERTJ',
                  'SPUET', 'TALAMOM', 'VERA'
              ))
              OR
              (tm.gerencia NOT IN ('catastro', 'regularizacion', 'instalaciones', 'contable', 'etapa_proyecto'))
          )
    ) as "STOCK_PROPIO",
    array_to_string(tm.acronimos_list, ', ') as acronimos
FROM tramites_metadata tm
CROSS JOIN periodos per
LEFT JOIN status_final s ON tm.trata = s.trata AND tm.gerencia = s.gerencia
WHERE per.anio >= 2025
GROUP BY tm.gerencia, tm.trata, tm.nombre_trata, tm.acronimos_list, per.anio, per.mes
ORDER BY tm.gerencia, tm.trata, per.anio, per.mes;
