# Configuración de Consultas SQL y Metadatos de Trámites por Gerencia

# Configuración de Trámites por Gerencia (ORDENADOS según requerimiento del usuario)
TRAMITES_CONFIG = {
    "catastro": {
        "MDUG0115C": {"nombre": "Anulación de Propiedad Horizontal.", "acronimos": "'IFMMH'"},
        "MDUG1501L": {"nombre": "Certificado de cota de parcela nivel cero", "acronimos": "'IFMAD'"},
        "MDUG0115G": {"nombre": "Certificado de Determinación de Cinturón Digital", "acronimos": "'IF'"},
        "MDUG1501H": {"nombre": "Certificado de información catastral.", "acronimos": "'IFDEX'"},
        "MDUG0134C": {"nombre": "Certificado de numeración domiciliaria.", "acronimos": "'CECNU'"},
        "MDUG0134N": {"nombre": "Constitución de Estado Parcelario", "acronimos": "'IFGPA', 'FIPAR'"},
        "MDUG0146A": {"nombre": "Copia de plano", "acronimos": "'IFPCB', 'IFDEX'"},
        "GENE0702C": {"nombre": "Mensura Regularización Urbana Dominial", "acronimos": "'PPINV'"},
        "MDUG0115F": {"nombre": "Plano de mensura de objeto territorial.", "acronimos": "'IFMOT'"},
        "MDUG0115B": {"nombre": "Plano de Mensura Particular.", "acronimos": "'IFMSC'"},
        "MDUG0132A": {"nombre": "Plano de prehorizontalidad nuevo", "acronimos": "'IFMHC'"},
        "MDUG0131A": {"nombre": "Plano de Propiedad Horizontal modificatorio/complementario.", "acronimos": "'IFMHC'"},
        "MDUG0131B": {"nombre": "Plano de propiedad horizontal nuevo.", "acronimos": "'IFMHC'"},
        "MDUG0115E": {"nombre": "Rectificación de Plano de Mensura.", "acronimos": "'IFMSC', 'IFMHC'"},
        "MDUG0134E": {"nombre": "Solicitud de Certificado de fijación de línea", "acronimos": "'IFMAD'"},
        "MDUG0135A": {"nombre": "Solicitud de consideración a la Dirección General Registros de Obra y Catastro", "acronimos": "'IFMHC', 'IFMMH', 'IFMAD', 'IFMSC', 'IFMOT', 'IFPCB', 'FIPAR'"},
        "INTERVENCIONES": {"nombre": "Intervenciones", "acronimos": ""}
    },
    "instalaciones": {
        "MDUG2101A": {"nombre": "Registro de Plano de Prevención contra Incendios.", "acronimos": "'PROIN', 'PLINE', 'IFCIS', 'IFSMC', 'IFRSP'"},
        "MDUG2901A": {"nombre": "Registro de Plano de Elementos Guiados de Transporte.", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "MDUG2501A": {"nombre": "Registro de Plano de Instalación de Inflamables.", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "MDUG2201A": {"nombre": "Registro de Plano de Instalación de Ventilación Mecánica.", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "MDUG2701A": {"nombre": "Registro de Plano de Instalación Eléctrica.", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "MDUG2401A": {"nombre": "Registro de Plano de Instalación Electromecánica.", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "MDUG2601A": {"nombre": "Registro de Plano de Instalación Sanitaria.", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "MDUG2301A": {"nombre": "Registro de Plano de Instalación Térmica.", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "MDUG3301A": {"nombre": "Registro de Plano de Sala de Máquinas.", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "MDUG0904A": {"nombre": "Ascenso de Categoría de Foguistas.", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "MDUG0120A": {"nombre": "Solicitud Examen de Foguista.", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "MJGG1601A": {"nombre": "Registro de planos de prototipo de equipos", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "MDUG0101D": {"nombre": "Ajuste De Instalacion Elementos Guiados De Transporte", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "MDUG0101G": {"nombre": "Ajuste De Instalacion Termica", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "MJGG1701A": {"nombre": "Transferencia de Titularidad de Instalación.", "acronimos": "'PROIN', 'PLINE', 'IFSMC'"},
        "INTERVENCIONES": {"nombre": "Intervenciones", "acronimos": ""}
    },
    "regularizacion": {
        "MDUG0104A": {"nombre": "Regularización de Plano de Obra Civil", "acronimos": "'IFROC'"},
        "MDUG0141A": {"nombre": "Registro de plano Conforme.", "acronimos": "'IFPCO', 'IFSMI'"},
        "MDUG3001A": {"nombre": "Registro de Plano de Obra Civil: Registro en Etapa Proyecto (EXPEDIENTES VIEJOS)", "acronimos": "'IFPCO'"},
        "MDUG1501K": {"nombre": "Permiso de Demolición.", "acronimos": "'IFPDO'"},
        "INTERVENCIONES": {"nombre": "Intervenciones", "acronimos": ""}
    },
    "contable": {
        "MDUG0901A": {"nombre": "Registro de Profesionales de Obras y Catastro", "acronimos": "'IF'"},
        "MDUG1501J": {"nombre": "Permiso de Ejecución de Obra Civil.", "acronimos": "'IFPDO'"},
        "MDUG3001A": {"nombre": "Registro de Plano de Obra Civil: Registro en Etapa Proyecto (CONTINUAN A PERMISOS)", "acronimos": "'IFPDO'"},
        "MDUG3402A": {"nombre": "Permiso Temprano de Ejecución de Obra Civil.", "acronimos": "'IFPEO', 'IFPDO'"},
        "INTERVENCIONES": {"nombre": "Intervenciones", "acronimos": ""}
    },
    "etapa_proyecto": {
        "MDUG3402A": {"nombre": "Permiso Temprano de Ejecución de Obra Civil.", "acronimos": "'IFTPT'"},
        "MDUG1502A": {"nombre": "Inicio de Micro Obra bajo Responsabilidad Profesional.", "acronimos": "'IFOCD', 'IFBRP'"},
        "MDUG4003A": {"nombre": "MODEL BA", "acronimos": "'IFOCD'"},
        "MDUG0142A": {"nombre": "Modificación de obra en curso bajo responsabilidad profesional", "acronimos": "'IFOCD'"},
        "MDUG3001A": {"nombre": "Registro de Plano de Obra Civil: Registro en Etapa Proyecto.", "acronimos": "'IFOCD'"},
        "INTERVENCIONES": {"nombre": "Intervenciones", "acronimos": ""}
    },
    "morfologia": {
        "MDUG1801A": {"nombre": "Informe urbanístico.", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MDUG0107A": {"nombre": "Fijación de Línea de Frente Interno.", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MDUG3501A": {"nombre": "Consulta Obligatoria General.", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MDUG3601A": {"nombre": "Interpretación Urbanística.", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MDUG3901A": {"nombre": "Solicitud De Certificado Urbanístico", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MDUG1802A": {"nombre": "Consulta No Obligatoria De Capacidad Constructiva Adicional Proyecto Emisor", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MDUG1804A": {"nombre": "Permiso De Ejecución De Obra Civil - Proyecto Emisor Zona Sur", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MDUG1803A": {"nombre": "Registro Etapa Proyecto - Emisor Zona Sur", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MDUG1805A": {"nombre": "Evaluación Vinculante De Capacidad Constructiva Adicional - Proyecto Emisor Zona Sur", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MDUG1806A": {"nombre": "Certificado De Capacidad Constructiva Adicional", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "INTERVENCIONES": {"nombre": "Intervenciones", "acronimos": ""}
    },
    "aph": {
        "MDUG3701A": {"nombre": "Consulta Obligatoria para Inmuebles en APH o Catalogados.", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MDUG3801A": {"nombre": "Solicitudes Especiales para Inmuebles en APH o Catalogados.", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "INTERVENCIONES": {"nombre": "Intervenciones", "acronimos": ""}
    },
    "usos": {
        "MDUG0136B": {"nombre": "Consulta de emplazamiento de estructuras soportes de antenas.", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MDUG4102A": {"nombre": "Consulta de usos - visado de anuncio publicitario (frontal, saliente) marquesina y/o toldos.", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MDUG4001A": {"nombre": "Consulta de usos", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MDUG4002A": {"nombre": "Consulta de usos B", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MJGG0302A": {"nombre": "Consulta de Usos No conforme", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "MJGG0303A": {"nombre": "Consulta de Usos con Intervención del consejo", "acronimos": "'DI', 'ANEXO', 'IF'"},
        "INTERVENCIONES": {"nombre": "Intervenciones", "acronimos": ""}
    },
    "aviso_obra": {
        "MDUG0102B": {"nombre": "Aviso de obra.", "acronimos": "'IFCAO', 'IFCFP', 'IFCAC'"},
        "INTERVENCIONES": {"nombre": "Intervenciones", "acronimos": ""}
    }
}
# Whitelists de Analistas Oficiales por Gerencia
WHITELISTS = {
    "catastro": [
        'ACOSTAPA', 'AFAHLER', 'AGUSMAZZONI', 'ALEALFONSIN', 'ALEGREM', 'ARGENTOES', 'BARTROLIG', 'CABRERAM', 'CANALEAL', 'CARBONELLIM', 'CHIANETTAR', 'CIOPKOG', 'CISTERNACA', 'COHENCAD', 'CONTIL', 'CONVERTID', 'DELGADODE', 'DIBIASEO', 'DIEZGASTON', 'DIHARCEP', 'DURSIM', 'ECIJAN', 'FMARCHISELLA', 'FOLLONIERLE', 'FREIXASC', 'GARCIASIL', 'GILESJP', 'GONZALEZAMA', 'GONZALEZHORAC', 'GUZMANO', 'IGARZABALP', 'JTIRADO', 'LAGUNAMA', 'LBELLY', 'LOISIG', 'LUCCIC', 'M.NAPOLI', 'MALATTOR', 'MANNOP', 'MARCHETTIJ', 'MHOSBALIKCIYAN', 'MOSCOVICHA', 'NCITRANGOLO', 'NOGUERAH', 'NPONZO', 'NQUINTERNO', 'PONZOS', 'ROLDANG', 'SALGUEROM', 'SORIAANDREA', 'TARRUA', 'TAVELLAE', 'VEGAJ', 'VILLAGI', 'WVIRGILIO'
    ],
    "instalaciones": [
        'AQUINOLUCAS', 'ARENAJ', 'ARGUELLOJ', 'BATALLANJ', 'BENITOG', 'BRIANMARTINEZ', 'CORNAZM', 'FICARRAR', 'GAGLIARDIA', 'LOPARDOC', 'QUEIJASGUILLINP', 'ROBLEDOJO', 'ROLDANMI', 'RUDAC', 'SARIDISD', 'TOLESANOA', 'AURENA', 'BATALLANGE', 'BRITANP', 'GUARDADOB', 'JDECIMA', 'PEREZGA', 'RODRIGUEZESTEBAN', 'RODRIGUEZNE', 'SILESC', 'VILLAGAB', 'ABCRAGNO', 'AGARCIAFIGUEROA', 'CABRERAARI', 'CAFELICE', 'CAPOZZOG', 'CSALGUERO', 'DARANGURI', 'DMOFFA', 'FUHRY', 'GONMAR', 'J.OLIVERA', 'LOPEZFE', 'MARIANELAROCARO', 'MBALDOME', 'MLMAMONE', 'MTRENQUE', 'NIEVAL', 'PCHERBENCO', 'RADAA', 'RIOSFE', 'ROMANOFLA', 'SANTACRUZ', 'CANTARELLTORRES', 'CIRIAE', 'LOIACONOANA', 'MCDIAMANTI', 'POUSAF', 'ARGUELLOSOL', 'COSSM', 'EIERACI', 'HAMALAG', 'RUIZMA', 'BRITANG', 'ENCISOROMERO', 'PITTERIE', 'WIERZBICKIIGOR'
    ],
    "regularizacion": [
        'AGUEROJO', 'AKRACOFF', 'ALVAREZ.M', 'ARAOZLUIS', 'ATENCIOAL', 'DALBORAF', 'ENCISOA', 'EPARLATO', 'ERDOCIAINA', 'JBARRACO', 'JLGARMENDIA', 'JTERRILE', 'MYUSHU', 'S.SANCHEZPAZ', 'SCAVALLARO'
    ],
    "contable": [
        'AMONTEVERDE', 'AMORINC', 'CARLOSDUARTE', 'CAROJAS', 'COLOTTAP', 'CPENDON', 'DAS', 'DASTUGUEO', 'DEGODOY', 'DIAZBAR', 'DKRENZ', 'EDEFEO', 'FABIANSANTILLAN', 'FMHERRERA', 'FSPANTI', 'GARCIASEBA', 'HRICCIARDI', 'JOSEMARIAORTIZ', 'JPOMAR', 'JULILOPARDO', 'LAMORGIAKA', 'LBARRIENTOS', 'LICETB', 'M.ROSSO', 'MARQUEZMAR', 'MARTINEZCLA', 'MLAURITO', 'MMALACALZA', 'NMONTEVERDE', 'NMORENO', 'POVIEDO', 'PRESAF', 'PVACEVEDO', 'RIVERAMA', 'ROBLEDOE', 'RODRIGUEZLEA', 'RODRIGUEZMAGD', 'ROSARIODECRIS', 'SCHULERG', 'SENING', 'SMERMOZ', 'SORIAD', 'SPOSAROAL', 'TATOJ', 'TIRENDIC', 'TOMIPITES', 'VICSOLMORE', 'VILLACRI'
    ],
    "etapa_proyecto": [
        'A.PEREZ', 'AGUSDEMARCO', 'ANTOVERA', 'BELOCURESJ', 'COIROL', 'DBECERRACURITIMA', 'DIMASOM', 'DNKAINSKY', 'FORGIONEA', 'GAILLURJP', 'GARRIONDO', 'JOSEFINA.P', 'M.SANCHEZ', 'MARCE.TOSONI', 'MARCETOSONI', 'MARCETOSONI1', 'MBRISA', 'MCANOGARAY', 'MCARLUCCIO', 'MGALLARDOC', 'MSTIBERTI', 'NLOPEZQUIROGA', 'ROCABERTJ', 'SPUET', 'TALAMOM', 'VERA'
    ],
    "morfologia": [
        'A.GUZMAN', 'AGARTEAGA', 'ALANDAZURI', 'ALFONSOGA', 'CAROLINAPRADO', 'CGAMARRA', 'CGENTILINI', 'DANCOLOMBO', 'ECAYSSIALS', 'EVELYNTORRES', 'FORFANO', 'FOTTOGALLI', 'FRANGARAY', 'GBERNASCONI', 'GCABADGIUR', 'IANELUSTONDO', 'IVALDES', 'LNSPERTINO', 'M.SABATINO', 'MANUELALVELO', 'MILAGROSTOURON', 'MILENAAZULMORENO', 'MLOBIANCOCRIADO', 'MPLANS1', 'MREIDMAN', 'MVOSKIAN', 'NASILANES', 'NCASALE', 'OVERRINA', 'PTEIGA', 'ROCAM', 'SBONDOREVSKY', 'SCABANELLAS', 'SDAVIDOVSKY', 'SVC_DGIURMORFO', 'SVCDGIUR3', 'TOSELLIR', 'VVINICIUS'
    ],
    "aph": [
        'CHANTIRRO', 'CHEZOM', 'DAMATOG', 'DESANTISA', 'GALAMA', 'GONZALEZNIETOR', 'HERENUFE', 'LSANTINMOLINA', 'MARIANALVAREZ', 'NASALVATIERRA', 'PIOLON', 'SVC_DGIURADMAPH', 'VASTAM'
    ],
    "usos": [
        'ALEPABLOCASTRO', 'ARVASR', 'AUZONMJ', 'BBORGIA', 'BILLAUDL', 'CLAUDIAVARELA', 'DALUNNI', 'DIMEGLIOA', 'EDUARDODIAZ', 'ELIANACABRERA', 'FOVERDAGUER', 'JBMENDY', 'JLSCIA', 'JLSCIARROTTA', 'LASALAMI', 'LTROLDAN', 'MAYASTUY', 'MERCADOEA', 'MFALAPPA', 'MIZONCA', 'MOCANA', 'MOURER', 'MPSIMONI', 'MYASTUY', 'PGLEISS', 'PORTAC', 'ROCCOR', 'SOFIAZANI', 'SVC_DGIURUSOS', 'VKAUFMAN'
    ],
    "aviso_obra": [
        'DGROC-AUTOMAT'
    ]
}

# Buzones de entrada por Gerencia
BUZZERS_MAP = {
    "catastro": ['DGROC-CIC', 'DGROC-COPIAPLANO', 'DGROC-DCATDES', 'DGROC-DCATMEN', 'DGROC-DCATPOL', 'DGROC-DCATTIT'],
    "instalaciones": ['DGROC-ELECTRICAS', 'DGROC-ELEVADORES', 'DGROC-INCENDIO', 'DGROC-SANITARIAS', 'DGROC-TERMICAS', 'DGROC-DCIMYE', 'DGROC-DCIELEV', 'DGROC-DCIDITI'],
    "regularizacion": ['DGROC-OBRASDEMO', 'DGROC-ESPERAINSTALACIONES'],
    "contable": ['DGROC-CONTABLE', 'DGROC-OBRASADMIN', 'DGROC-DCG', 'DGROC-DESCARGOS', 'DGROC-DTACONT', 'DGROC-DTARPS', 'DGROC-LEGAJOS', 'DGROC-REVISIONCONTABLE', 'DGROC-AUTOMAT', 'DGROC-PENDIENTESDEPAGO'],
    "etapa_proyecto": ['DGROC-OBRASTECNICA'],
    "morfologia": ['DGIUR-03', 'DGIUR-ADMISIBILIDADMORFO', 'DGIUR-CONSULTASESPECIFICAS', 'DGIUR-CURVERIFICACION', 'DGIUR-DGIUR-PERMISO TEMPRANO', 'DGIUR-VA II'],
    "aph": ['DGIUR-21', 'DGIUR-ADMISIBILIDADAPH', 'DGIUR-ADMISIMIDIDADAPH'],
    "usos": ['DGIUR-12', 'DGIUR-ADMISIBILIDADUSOS', 'DGIUR-EGOUS'],
    "aviso_obra": ['DGROC-AUTOMAT']
}
