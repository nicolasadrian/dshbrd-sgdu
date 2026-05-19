# Guía Funcional de Gerencias y Configuraciones - SGDU Analytics

Esta guía explica en términos sencillos y de negocio cómo está configurado cada sector (**gerencia**) dentro del sistema de analíticas de la SGDU. Está diseñada para que cualquier persona, sin importar su perfil técnico, pueda comprender exactamente de dónde proviene la información de cada tablero, quién procesa el trabajo y cuándo se considera que un trámite ha finalizado con éxito.

---

## 1. Conceptos Clave en Lenguaje Sencillo

Para entender las tablas de configuración de cada gerencia, es útil conocer estos cinco términos del día a día operativo:

1.  **Trámite o Trata (¿De qué se trata?):** Es el código que identifica el tipo de expediente que inicia el ciudadano (por ejemplo: un plano, un permiso de obra, una habilitación).
2.  **Buzón de Ingreso (¿Por dónde entra?):** Es la "mesa de entrada virtual" del sector. En el momento en que un expediente digital cae en este buzón, el reloj del sector empieza a correr.
3.  **Analistas Oficiales (¿Quién lo tiene?):** Es la lista (whitelist) de usuarios y sub-buzones del personal autorizado de cada área. Si el expediente está en poder de alguna de estas personas, se considera que está **"en Stock"** del área.
4.  **Acrónimo de Egreso (¿Cómo se termina?):** Es el tipo de documento digital (GEDO) oficial que aprueba o finaliza el trámite. Su generación marca un **"Egreso Efectivo"** (trabajo terminado con éxito).
5.  **Firmantes de Egreso (¿Quién da el gancho final?):** En algunos sectores, no cualquier firma vale. Solo los documentos firmados por los directores o jefes autorizados en esta lista marcan el fin del trámite. Si la lista está vacía, la firma de cualquier analista oficial es válida.

---

## 2. Detalle Sector por Sector (Las 9 Gerencias)

A continuación, se detalla la configuración exacta extraída del motor de base de datos para cada una de las gerencias:

---

### 📂 1. Catastro (DGROC - CATASTRO)
El sector encargado del registro y delimitación física, jurídica y económica de los inmuebles de la Ciudad.

*   **¿Qué trámites le corresponden (Tratas)?** (16 tipos de trámites)
    *   Planos de mensura, subdivisiones y catastros en general: `MDUG0115C`, `MDUG1501L`, `MDUG0115G`, `MDUG1501H`, `MDUG0134C`, `MDUG0134N`, `MDUG0146A`, `GENE0702C`, `MDUG0115F`, `MDUG0115B`, `MDUG0132A`, `MDUG0131A`, `MDUG0131B`, `MDUG0115E`, `MDUG0134E`, `MDUG0135A`.
*   **¿Por qué buzones entra el trabajo?**
    *   Buzones oficiales de catastro: `DGROC-CIC`, `DGROC-COPIAPLANO`, `DGROC-DCATDES`, `DGROC-DCATPOL`, `DGROC-DCATTIT`.
*   **¿Quiénes son sus analistas oficiales?**
    *   Un equipo de **61 analistas** y sub-buzones autorizados para tener stock activo.
    <details>
    <summary><b>Ver lista de usuarios autorizados ⬇️</b></summary>
    
    *   **Buzones del Sector:** `DGROC-CIC`, `DGROC-COPIAPLANO`, `DGROC-DCATDES`, `DGROC-DCATMEN`, `DGROC-DCATPOL`, `DGROC-DCATTIT`.
    *   **Usuarios:** `ACOSTAPA`, `AFAHLER`, `AGUSMAZZONI`, `ALEALFONSIN`, `ALEGREM`, `ARGENTOES`, `BARTROLIG`, `CABRERAM`, `CANALEAL`, `CARBONELLIM`, `CHIANETTAR`, `CIOPKOG`, `CISTERNACA`, `COHENCAD`, `CONTIL`, `CONVERTID`, `DELGADODE`, `DIBIASEO`, `DIEZGASTON`, `DIHARCEP`, `DURSIM`, `ECIJAN`, `FMARCHISELLA`, `FOLLONIERLE`, `FREIXASC`, `GARCIASIL`, `GILESJP`, `GONZALEZAMA`, `GONZALEZHORAC`, `GUZMANO`, `IGARZABALP`, `JTIRADO`, `LAGUNAMA`, `LBELLY`, `LOISIG`, `LUCCIC`, `M.NAPOLI`, `MALATTOR`, `MANNOP`, `MARCHETTIJ`, `MHOSBALIKCIYAN`, `MOSCOVICHA`, `NCITRANGOLO`, `NOGUERAH`, `NPONZO`, `NQUINTERNO`, `PONZOS`, `ROLDANG`, `SALGUEROM`, `SORIAANDREA`, `TARRUA`, `TAVELLAE`, `VEGAJ`, `VILLAGI`, `WVIRGILIO`.
    </details>
*   **¿Cómo se aprueba el trámite (Documentos de salida)?**
    *   Cualquiera de los siguientes **12 informes o planos de catastro aprobados**: `IFMMH`, `IFMAD`, `IF`, `IFDEX`, `CECNU`, `IFGPA`, `FIPAR`, `IFPCB`, `PPINV`, `IFMOT`, `IFMSC`, `IFMHC`.
*   **¿Quién debe firmar?**
    *   **Cualquier usuario** que genere y firme uno de los documentos de egreso anteriores finaliza válidamente el trámite.

---

### ⚙️ 2. Instalaciones (DGROC - INSTALACIONES)
El área encargada de la fiscalización y registro de instalaciones mecánicas, eléctricas, sanitarias, térmicas, elevadores y sistemas contra incendios en obras.

*   **¿Qué trámites le corresponden (Tratas)?** (15 tipos de trámites)
    *   Permisos y registros de conservación de elevadores, térmicas, incendio, etc.: `MDUG2101A`, `MDUG2901A`, `MDUG2501A`, `MDUG2201A`, `MDUG2701A`, `MDUG2401A`, `MDUG2601A`, `MDUG2301A`, `MDUG3301A`, `MDUG0904A`, `MDUG0120A`, `MJGG1601A`, `MDUG0101D`, `MDUG0101G`, `MJGG1701A`.
*   **¿Por qué buzones entra el trabajo?**
    *   Los 8 buzones especializados por especialidad técnica: `DGROC-ELECTRICAS`, `DGROC-ELEVADORES`, `DGROC-INCENDIO`, `DGROC-SANITARIAS`, `DGROC-TERMICAS`, `DGROC-DCIMYE`, `DGROC-DCIELEV`, `DGROC-DCIDITI`.
*   **¿Quiénes son sus analistas oficiales?**
    *   Un equipo técnico de **58 analistas** registrados.
    <details>
    <summary><b>Ver lista de usuarios autorizados ⬇️</b></summary>
    
    *   **Buzones del Sector:** `DGROC-ELECTRICAS`, `DGROC-ELEVADORES`, `DGROC-INCENDIO`, `DGROC-SANITARIAS`, `DGROC-TERMICAS`, `DGROC-DCIMYE`, `DGROC-DCIELEV`, `DGROC-DCIDITI`.
    *   **Usuarios:** `AQUINOLUCAS`, `ARENAJ`, `ARGUELLOJ`, `BATALLANJ`, `BENITOG`, `BRIANMARTINEZ`, `CORNAZM`, `FICARRAR`, `GAGLIARDIA`, `LOPARDOC`, `QUEIJASGUILLINP`, `ROBLEDOJO`, `ROLDANMI`, `RUDAC`, `SARIDISD`, `TOLESANOA`, `AURENA`, `BATALLANGE`, `BRITANP`, `GUARDADOB`, `JDECIMA`, `PEREZGA`, `RODRIGUEZESTEBAN`, `RODRIGUEZNE`, `SILESC`, `VILLAGAB`, `ABCRAGNO`, `AGARCIAFIGUEROA`, `CABRERAARI`, `CAFELICE`, `CAPOZZOG`, `CSALGUERO`, `DARANGURI`, `DMOFFA`, `FUHRY`, `GONMAR`, `J.OLIVERA`, `LOPEZFE`, `MARIANELAROCARO`, `MBALDOME`, `MLMAMONE`, `MTRENQUE`, `NIEVAL`, `PCHERBENCO`, `RADAA`, `RIOSFE`, `ROMANOFLA`, `SANTACRUZ`, `CANTARELLTORRES`, `CIRIAE`, `LOIACONOANA`, `MCDIAMANTI`, `POUSAF`, `ARGUELLOSOL`, `COSSM`, `EIERACI`, `HAMALAG`, `RUIZMA`, `BRITANG`, `ENCISOROMERO`, `PITTERIE`, `WIERZBICKIIGOR`.
    </details>
*   **¿Cómo se aprueba el trámite (Documentos de salida)?**
    *   Cualquiera de los siguientes **5 tipos de registro o informes**: `PROIN` (Proyecto Instalación), `PLINE` (Plano Instalación), `IFCIS` (Informe Técnico Cisterna), `IFSMC` (Informe Semestral Conservación), `IFRSP` (Informe Registro Obra).
*   **¿Quién debe firmar?**
    *   **Cualquier usuario** autorizado.

---

### ⚖️ 3. Regularización y Conforme (DGROC - REGULARIZACIÓN)
El sector encargado de regularizar obras existentes realizadas sin permiso previo, y de otorgar los conformes finales de obra.

*   **¿Qué trámites le corresponden (Tratas)?** (4 tipos de trámites)
    *   Ajuste de obras, demoliciones y registros técnicos de regularización: `MDUG0104A`, `MDUG0141A`, `MDUG3001A`, `MDUG1501K`.
*   **¿Por qué buzones entra el trabajo?**
    *   Buzones de obras demoliciones y técnica: `DGROC-OBRASDEMO`, `DGROC-OBRASTECNICA`.
*   **¿Quiénes son sus analistas oficiales?**
    *   Un equipo de **17 analistas** oficiales (incluye el buzón temporal `DGROC-ESPERAINSTALACIONES`).
    <details>
    <summary><b>Ver lista de usuarios autorizados ⬇️</b></summary>
    
    *   **Buzones del Sector:** `DGROC-ESPERAINSTALACIONES`, `DGROC-OBRASDEMO`.
    *   **Usuarios:** `AGUEROJO`, `AKRACOFF`, `ALVAREZ.M`, `ARAOZLUIS`, `ATENCIOAL`, `DALBORAF`, `ENCISOA`, `EPARLATO`, `ERDOCIAINA`, `JBARRACO`, `JLGARMENDIA`, `JTERRILE`, `MYUSHU`, `S.SANCHEZPAZ`, `SCAVALLARO`.
    </details>
*   **¿Cómo se aprueba el trámite (Documentos de salida)?**
    *   Cualquiera de los siguientes **4 documentos de conforme o regularización**: `IFROC`, `IFPCO`, `IFSMI`, `IFPDO`.
*   **¿Quién debe firmar?**
    *   **Cualquier usuario** que genere el documento.

---

### 📊 4. Contable (DGROC - CONTABLE)
El sector encargado del control de pagos de derechos de construcción, liquidaciones de tasas fiscales y multas contables de las obras.

*   **¿Qué trámites le corresponden (Tratas)?** (4 tipos de trámites propios)
    *   Liquidaciones y trámites de pago: `MDUG0901A`, `MDUG1501J`, `MDUG3001A`, `MDUG3402A`.
*   **¿Por qué buzones entra el trabajo?**
    *   Buzones contables y administrativos: `DGROC-CONTABLE`, `DGROC-OBRASADMIN`.
*   **¿Quiénes son sus analistas oficiales?**
    *   Un equipo amplio de **59 analistas** y sub-buzones específicos de cobros (ej. `DGROC-PENDIENTESDEPAGO`, `DGROC-REVISIONCONTABLE`).
    <details>
    <summary><b>Ver lista de usuarios autorizados ⬇️</b></summary>
    
    *   **Buzones del Sector:** `DGROC-AUTOMAT`, `DGROC-CONTABLE`, `DGROC-DCG`, `DGROC-DESCARGOS`, `DGROC-DTACONT`, `DGROC-DTARPS`, `DGROC-LEGAJOS`, `DGROC-OBRASADMIN`, `DGROC-PENDIENTESDEPAGO`, `DGROC-REVISIONCONTABLE`.
    *   **Usuarios:** `AMONTEVERDE`, `AMORINC`, `CARLOSDUARTE`, `CAROJAS`, `COLOTTAP`, `CPENDON`, `DAS`, `DASTUGUEO`, `DEGODOY`, `DIAZBAR`, `DKRENZ`, `EDEFEO`, `FABIANSANTILLAN`, `FMHERRERA`, `FSPANTI`, `GARCIASEBA`, `HRICCIARDI`, `JOSEMARIAORTIZ`, `JPOMAR`, `JULILOPARDO`, `LAMORGIAKA`, `LBARRIENTOS`, `LICETB`, `M.ROSSO`, `MARQUEZMAR`, `MARTINEZCLA`, `MLAURITO`, `MMALACALZA`, `NMONTEVERDE`, `NMORENO`, `POVIEDO`, `PRESAF`, `PVACEVEDO`, `RIVERAMA`, `ROBLEDOE`, `RODRIGUEZLEA`, `RODRIGUEZMAGD`, `ROSARIODECRIS`, `SCHULERG`, `SENING`, `SMERMOZ`, `SORIAD`, `SPOSAROAL`, `TATOJ`, `TIRENDIC`, `TOMIPITES`, `VICSOLMORE`, `VILLACRI`.
    </details>
*   **¿Cómo se aprueba el trámite (Documentos de salida)?**
    > [!IMPORTANT]
    > **Regla Especial de Contable:** Este sector no tiene una lista genérica. Cada trámite tiene su propio "documento de egreso" y su firmante específico:
    *   **Para el trámite `MDUG0901A`:** Se requiere un informe tipo **`IF`** firmado **únicamente** por los responsables contables `FABIANSANTILLAN` o `LICETB`. La firma de cualquier otro usuario no finaliza el trámite para las estadísticas.
    *   **Para el trámite `MDUG1501J`:** Se requiere un documento de liquidación de pago **`IFPDO`** firmado por cualquier analista.
    *   **Para el trámite `MDUG3001A`:** Se requiere un documento de liquidación **`IFPDO`** firmado por cualquier analista. (Se distingue de Etapa Proyecto por el buzón de entrada).
    *   **Para el trámite `MDUG3402A`:** Se requiere un documento contable **`IFPEO`** o **`IFPDO`** firmado por cualquier analista.

---

### 📐 5. Etapa Proyecto (DGROC - ETAPA PROYECTO)
El sector enfocado en la revisión inicial de planos de arquitectura, volumetría y edificabilidad antes de otorgar el permiso de obra definitivo.

*   **¿Qué trámites le corresponden (Tratas)?** (5 tipos de trámites)
    *   Proyectos de obras civiles y edificabilidad básica: `MDUG3402A`, `MDUG1502A`, `MDUG4003A`, `MDUG0142A`, `MDUG3001A`.
*   **¿Por qué buzones entra el trabajo?**
    *   Buzón único de técnica: `DGROC-OBRASTECNICA`.
*   **¿Quiénes son sus analistas oficiales?**
    *   Un equipo de **27 analistas** oficiales.
    <details>
    <summary><b>Ver lista de usuarios autorizados ⬇️</b></summary>
    
    *   **Buzones del Sector:** `DGROC-OBRASTECNICA`.
    *   **Usuarios:** `A.PEREZ`, `AGUSDEMARCO`, `ANTOVERA`, `BELOCURESJ`, `COIROL`, `DBECERRACURITIMA`, `DIMASOM`, `DNKAINSKY`, `FORGIONEA`, `GAILLURJP`, `GARRIONDO`, `JOSEFINA.P`, `M.SANCHEZ`, `MARCE.TOSONI`, `MARCETOSONI`, `MARCETOSONI1`, `MBRISA`, `MCANOGARAY`, `MCARLUCCIO`, `MGALLARDOC`, `MSTIBERTI`, `NLOPEZQUIROGA`, `ROCABERTJ`, `SPUET`, `TALAMOM`, `VERA`.
    </details>
*   **¿Cómo se aprueba el trámite (Documentos de salida)?**
    *   Cualquiera de los siguientes **3 informes técnicos de proyecto aprobados**: `IFTPT`, `IFOCD`, `IFBRP`.
*   **¿Quién debe firmar?**
    *   **Cualquier usuario** que genere el documento aprobado.

---

### ⚡ 6. Aviso de Obra (DGROC - AVISO DE OBRA)
El canal rápido y automatizado de la DGROC para obras de bajísimo impacto (ej. pintura, refacciones menores) que no requieren una revisión exhaustiva presencial.

*   **¿Qué trámites le corresponden (Tratas)?** (1 tipo de trámite)
    *   Trámite único de aviso ágil: `MDUG0102B`.
*   **¿Por qué buzones entra el trabajo?**
    *   Buzón automatizado del sistema: `DGROC-AUTOMAT`.
*   **¿Quiénes son sus analistas oficiales?**
    *   El buzón robot: `DGROC-AUTOMAT` (Todo se procesa digitalmente en segundos de forma automática).
    <details>
    <summary><b>Ver lista de usuarios autorizados ⬇️</b></summary>
    
    *   **Buzones del Sector:** `DGROC-AUTOMAT`.
    </details>
*   **¿Cómo se aprueba el trámite (Documentos de salida)?**
    *   Cualquiera de los **3 tipos de aviso aprobados**: `IFCAO`, `IFCFP`, `IFCAC`.
*   **¿Quién debe firmar?**
    *   El sistema o cualquier usuario autorizado en `DGROC-AUTOMAT`.

---

### 🎨 7. Morfología Urbana (DGIUR - MORFOLOGIA)
El área de la Dirección General de Interpretación Urbanística (DGIUR) que evalúa el perfil urbano, alturas de fachadas y la volumetría de las parcelas de la Ciudad.

*   **¿Qué trámites le corresponden (Tratas)?** (10 tipos de trámites propios)
    *   Visados urbanísticos, consultas de volumetrías y morfología: `MDUG1801A`, `MDUG0107A`, `MDUG3501A`, `MDUG3601A`, `MDUG3901A`, `MDUG1802A`, `MDUG1804A`, `MDUG1803A`, `MDUG1805A`, `MDUG1806A`.
*   **¿Por qué buzones entra el trabajo propio?**
    *   Buzón central de la DGIUR: `DGIUR-03`.
*   **¿Por qué buzones entran las "Intervenciones"?** (6 buzones)
    *   Morfología puede intervenir en trámites de otras áreas que entren por: `DGIUR-03`, `DGIUR-ADMISIBILIDADMORFO`, `DGIUR-CONSULTASESPECIFICAS`, `DGIUR-CURVERIFICACION`, `DGIUR-DGIUR-PERMISO TEMPRANO`, `DGIUR-VA II`.
*   **¿Quiénes son sus analistas oficiales?**
    *   Un equipo altamente especializado de **44 analistas** y sub-buzones de mesa sectorial.
    <details>
    <summary><b>Ver lista de usuarios autorizados ⬇️</b></summary>
    
    *   **Buzones del Sector:** `DGIUR-03`, `DGIUR-ADMISIBILIDADMORFO`, `DGIUR-CONSULTASESPECIFICAS`, `DGIUR-CURVERIFICACION`, `DGIUR-DGIUR-PERMISO TEMPRANO`, `DGIUR-VA II`.
    *   **Usuarios:** `A.GUZMAN`, `AGARTEAGA`, `ALANDAZURI`, `ALFONSOGA`, `CAROLINAPRADO`, `CGAMARRA`, `CGENTILINI`, `DANCOLOMBO`, `ECAYSSIALS`, `EVELYNTORRES`, `FORFANO`, `FOTTOGALLI`, `FRANGARAY`, `GBERNASCONI`, `GCABADGIUR`, `IANELUSTONDO`, `IVALDES`, `LNSPERTINO`, `M.SABATINO`, `MANUELALVELO`, `MILAGROSTOURON`, `MILENAAZULMORENO`, `MLOBIANCOCRIADO`, `MPLANS1`, `MREIDMAN`, `MVOSKIAN`, `NASILANES`, `NCASALE`, `OVERRINA`, `PTEIGA`, `ROCAM`, `SBONDOREVSKY`, `SCABANELLAS`, `SDAVIDOVSKY`, `SVC_DGIURMORFO`, `SVCDGIUR3`, `TOSELLIR`, `VVINICIUS`.
    </details>
*   **¿Cómo se aprueba el trámite (Documentos de salida)?**
    *   Cualquiera de los siguientes **3 documentos**: `DI` (Disposición Urbanística), `ANEXO` (Anexo Gráfico / Volumétrico), `IF` (Informe Técnico de Morfología).
*   **¿Quién debe firmar?**
    > [!IMPORTANT]
    > **Regla de Firma Directiva:** Para que el egreso sea contabilizado como válido, el documento **debe estar firmado obligatoriamente por `ALANDAZURI`** (Director General o firma autorizada del área). Ninguna otra firma de analista cierra estadísticamente el trámite propio.

---

### 🏛️ 8. Área de Protección Histórica - APH (DGIUR - APH)
El área de la DGIUR dedicada a la preservación del patrimonio construido de la Ciudad. Evalúa obras ubicadas en edificios protegidos históricamente o distritos catalogados.

*   **¿Qué trámites le corresponden (Tratas)?** (2 tipos de trámites)
    *   Trámites específicos de catalogación e intervenciones en patrimonio: `MDUG3701A`, `MDUG3801A`.
*   **¿Por qué buzones entra el trabajo?**
    *   Buzón central de protección histórica: `DGIUR-21`.
*   **¿Quiénes son sus analistas oficiales?**
    *   Un equipo de **16 arquitectos y especialistas patrimoniales** (incluye los buzones sectoriales `DGIUR-ADMISIBILIDADAPH`, `SVC_DGIURADMAPH`).
    <details>
    <summary><b>Ver lista de usuarios autorizados ⬇️</b></summary>
    
    *   **Buzones del Sector:** `DGIUR-21`, `DGIUR-ADMISIBILIDADAPH`, `DGIUR-ADMISIMIDIDADAPH`, `SVC_DGIURADMAPH`.
    *   **Usuarios:** `CHANTIRRO`, `CHEZOM`, `DAMATOG`, `DESANTISA`, `GALAMA`, `GONZALEZNIETOR`, `HERENUFE`, `LSANTINMOLINA`, `MARIANALVAREZ`, `NASALVATIERRA`, `PIOLON`, `VASTAM`.
    </details>
*   **¿Cómo se aprueba el trámite (Documentos de salida)?**
    *   Cualquiera de los **3 tipos de resoluciones**: `DICTAMEN` (Dictamen APH), `ANEXO` (Anexo Técnico de Edificio Protegido), `INFORME` (Informe Técnico de Viabilidad).
*   **¿Quién debe firmar?**
    > [!IMPORTANT]
    > **Regla de Firma Directiva:** Para que el trámite cuente como cerrado, el documento de egreso **debe estar firmado únicamente por `VASTAM`** (Jefe/Director del área de Protección Histórica).

---

### 🏬 9. Usos del Suelo (DGIUR - USOS)
El área de la DGIUR que dictamina sobre la factibilidad de actividades comerciales, industriales o de servicios de una parcela en base a la zonificación del Código Urbanístico de la Ciudad.

*   **¿Qué trámites le corresponden (Tratas)?** (6 tipos de trámites)
    *   Consultas de uso de suelo, habilitaciones de actividades comerciales especiales y mixtura de usos: `MDUG0136B`, `MDUG4102A`, `MDUG4001A`, `MDUG4002A`, `MJGG0302A`, `MJGG0303A`.
*   **¿Por qué buzones entra el trabajo?**
    *   Buzón central de usos del suelo: `DGIUR-12`.
*   **¿Quiénes son sus analistas oficiales?**
    *   Un equipo de **33 analistas** de factibilidad (incluye los buzones internos `DGIUR-EGOUS`, `DGIUR-ADMISIBILIDADUSOS`, `SVC_DGIURUSOS`).
    <details>
    <summary><b>Ver lista de usuarios autorizados ⬇️</b></summary>
    
    *   **Buzones del Sector:** `DGIUR-12`, `DGIUR-ADMISIBILIDADUSOS`, `DGIUR-EGOUS`, `SVC_DGIURUSOS`.
    *   **Usuarios:** `ALEPABLOCASTRO`, `ARVASR`, `AUZONMJ`, `BBORGIA`, `BILLAUDL`, `CLAUDIAVARELA`, `DALUNNI`, `DIMEGLIOA`, `EDUARDODIAZ`, `ELIANACABRERA`, `FOVERDAGUER`, `JBMENDY`, `JLSCIA`, `JLSCIARROTTA`, `LASALAMI`, `LTROLDAN`, `MAYASTUY`, `MERCADOEA`, `MFALAPPA`, `MIZONCA`, `MOCANA`, `MOURER`, `MPSIMONI`, `MYASTUY`, `PGLEISS`, `PORTAC`, `ROCCOR`, `SOFIAZANI`, `VKAUFMAN`.
    </details>
*   **¿Cómo se aprueba el trámite (Documentos de salida)?**
    *   Cualquiera de los **3 tipos de resoluciones urbanísticas**: `DICTAMEN`, `ANEXO`, `INFORME`.
*   **¿Quién debe firmar?**
    > [!IMPORTANT]
    > **Regla de Firma Directiva:** El egreso solo se considera finalizado con éxito si el documento de salida es firmado digitalmente por al menos uno de los siguientes **3 directores autorizados**: `FOVERDAGUER`, `MIZONCA` o `DALUNNI`.

---

## 3. Resumen Rápido para No Especialistas

Si necesitas explicarle el modelo a alguien externo rápidamente, esta tabla resume visualmente las principales diferencias de reglas operativas:

| Gerencia | ¿De qué trata? (Ejemplo) | ¿Por dónde entra? | ¿Quién lo resuelve? | ¿Cómo termina formalmente? | ¿Quién firma el gancho final? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Catastro** | Planos y Mensuras | 5 buzones de Catastro | 61 analistas | Plano / Informe Aprobado | Cualquiera del equipo |
| **2. Instalaciones** | Ascensores, Incendio, Electricidad | 8 buzones de Instalaciones | 58 analistas | Proyecto / Plano Registrado | Cualquiera del equipo |
| **3. Regularización** | Conforme de Obra, Ajustes | 2 buzones de Obras | 17 analistas | Conforme / Plano Terminado | Cualquiera del equipo |
| **4. Contable** | Tasas y Derechos | Contable / Obras Adm. | 59 analistas | Liquidación (IFPDO/IFPEO) | **Regla por trámite** (Ej. MDUG0901A: Santillán o Licet) |
| **5. Etapa Proyecto** | Aprobación de Planos Técnicos | Técnica | 27 analistas | Informe Aprobado | Cualquiera del equipo |
| **6. Aviso de Obra** | Habilitación Exprés | Automatizado | Sistema Automatizado | Aviso Aprobado (IFCAO/CFP/CAC)| Cualquiera del equipo |
| **7. Morfología** | Perfil de Fachada y Alturas | DGIUR-03 | 44 analistas | Disposición / Anexo Gráfico | **Solo ALANDAZURI** |
| **8. APH** | Patrimonio Histórico | DGIUR-21 | 16 analistas | Dictamen / Anexo APH | **Solo VASTAM** |
| **9. Usos** | Comercio e Industrias | DGIUR-12 | 33 analistas | Dictamen / Informe de Usos | **Solo FOVERDAGUER, MIZONCA o DALUNNI** |
