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
        "MDUG1502A": {"nombre": "Inico de Micro Obra bajo Responsabilidad Profesional.", "acronimos": "'IFOCD', 'IFBRP'"},
        "MDUG4003A": {"nombre": "MODEL BA", "acronimos": "'IFOCD'"},
        "MDUG0142A": {"nombre": "Modificación de obra en curso bajo responsabilidad profesional", "acronimos": "'IFOCD'"},
        "MDUG3001A": {"nombre": "Registro de Plano de Obra Civil: Registro en Etapa Proyecto.", "acronimos": "'IFOCD'"},
        "INTERVENCIONES": {"nombre": "Intervenciones", "acronimos": ""}
    },
    "aviso_obra": {
        "MDUG0102B_AUTO": {"nombre": "Aviso de Obra (Automático)", "acronimos": "'IFCAO', 'IFCAC'"},
        "MDUG0102B_DGIUR": {"nombre": "Aviso de Obra (DGIUR)", "acronimos": "'IF'"}
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
    "aviso_obra": []
}

# Buzones de entrada por Gerencia
BUZZERS_MAP = {
    "catastro": ['DGROC-CIC', 'DGROC-COPIAPLANO', 'DGROC-DCATDES', 'DGROC-DCATMEN', 'DGROC-DCATPOL', 'DGROC-DCATTIT'],
    "instalaciones": ['DGROC-ELECTRICAS', 'DGROC-ELEVADORES', 'DGROC-INCENDIO', 'DGROC-SANITARIAS', 'DGROC-TERMICAS', 'DGROC-DCIMYE', 'DGROC-DCIELEV', 'DGROC-DCIDITI'],
    "regularizacion": ['DGROC-OBRASDEMO', 'DGROC-ESPERAINSTALACIONES'],
    "contable": ['DGROC-CONTABLE', 'DGROC-OBRASADMIN', 'DGROC-DCG', 'DGROC-DESCARGOS', 'DGROC-DTACONT', 'DGROC-DTARPS', 'DGROC-LEGAJOS', 'DGROC-REVISIONCONTABLE'],
    "etapa_proyecto": ['DGROC-OBRASTECNICA'],
    "aviso_obra": ['DGROC-AUTOMAT']
}
