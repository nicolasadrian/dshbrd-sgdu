# 🏗️ Documentación de Arquitectura y Pipeline de Datos (Tablero SGDU)

Este documento detalla la estructura, flujo y responsabilidad de cada uno de los scripts de actualización de datos del Tablero SGDU, organizados en fases secuenciales.

---

## 🔄 Flujo General del Pipeline

```
[Oracle / SADE] 
      │
      ▼  (Fase 1: deploy/etl_sade.py)
[PostgreSQL Local: sgdu_local]
      │
      ├─► (Fase 2: backend/run_all_imports.py y scripts import_df_form_comp_value_*.py)
      │      └─► Generación de Tablas GEDO Pivotadas en Local
      │
      ├─► (Fase 3: backend/populate_coordinates.py & backend/recreate_local_m2_view.py)
      │      └─► Georeferenciación e Índices Vistas Materializadas
      │
      └─► (Fase 4: Sincronización a Producción)
             ├─► deploy/sync_sade_tables.py  (Tablas SADE)
             ├─► backend/upload_gedo_tables_to_production.py  (Tablas GEDO Pivotadas)
             └─► backend/create_prod_m2_view.py  (Vistas Materializadas Remotas)
```

---

## 📚 Detalle de Scripts por Fase

### Fase 1: Extracción y Carga Base (SADE)

#### `deploy/etl_sade.py`
* **Descripción**: Extrae incrementalmente la información oficial de trámites, pases, actividades, usuarios y documentos GEDO desde la base de datos Oracle (SADE) hacia la base de datos PostgreSQL local (`sgdu_local`).
* **Frecuencia sugerida**: Diaria o previa a generación de reportes.
* **Tablas que alimenta (Local)**:
  * `mvw_expedientes_tratas_secgdu`
  * `mvw_ee_ssgu`
  * `mvw_datos_gedo_secgdu`
  * `mvw_ee_pases_secgdu`
  * `mvw_ee_gedo_secgdu`
  * `mvw_ee_actividades_secgdu`
  * `datos_usuario`

---

### Fase 2: Extracción y Pivotado de Formularios GEDO (`df_form_comp_value`)

Estos scripts extraen los campos formulario específicos (parámetros clave/valor) guardados en SADE en formato XML/JSON dentro del repositorio GEDO y generan las tablas analíticas pivotadas por acrónimo.

#### `backend/run_all_imports.py` (Orquestador Lote)
* **Descripción**: Ejecuta secuencialmente la lista completa de scripts de importación de acrónimos GEDO.

#### Scripts Individuales por Acrónimo / Gerencia:

| Script | Acrónimo / Dominio | Tabla Destino Generada | Descripción de Campos Extraídos |
| :--- | :--- | :--- | :--- |
| `backend/import_df_form_comp_value_ifroc.py` | `IFROC` (Obras) | `public.gedo_ifroc_datos` | Dirección (`calle_altura`), superficie, tipo de obra, destino, profesional. |
| `backend/import_df_form_comp_value_ifcao.py` | `IFCAO` (Avisos de Obra) | `public.gedo_ifcao_datos` | Datos de aviso de obra, propietario, ubicación. |
| `backend/import_df_form_comp_value_ifcfp.py` | `IFCFP` (Avisos de Obra) | `public.gedo_ifcfp_datos` | Datos de clausuras/permisos de obra por fachada/frente. |
| `backend/import_df_form_comp_value_ifcac.py` | `IFCAC` (Avisos de Obra) | `public.gedo_ifcac_datos` | Certificados de avisos de obra y demolición. |
| `backend/import_df_form_comp_value_morfologia.py` | Morfología / LFI | `public.gedo_morfologia_datos` | Datos morfométricos, altura, basamentos y LFI. |
| `backend/import_df_form_comp_value_usos.py` | Usos Urbanos | `public.gedo_usos_datos` | Rubros, actividades comerciales y superficies habilitadas. |
| `backend/import_df_form_comp_value_aph.py` | APH (Patrimonio) | `public.gedo_aph_datos` | Nivel de protección patrimonial y dictámenes. |
| `backend/import_df_form_comp_value_cecnu.py` | CECNU | `public.gedo_cecnu_datos` | Certificados de conformidad normativa urbana. |
| `backend/import_df_form_comp_value_fipar.py` | FIPAR | `public.gedo_fipar_datos` | Formularios de intervenciones en parcelas. |
| `backend/import_df_form_comp_value_ifcis.py` | IFCIS (Instalaciones) | `public.gedo_ifcis_datos` | Instalaciones térmicas, inflamables y electromecánicas. |
| `backend/import_df_form_comp_value_ifdex.py` | IFDEX (Demoliciones) | `public.gedo_ifdex_datos` | Permisos y planos de demolición previa. |
| `backend/import_df_form_comp_value_ifgpa.py` | IFGPA | `public.gedo_ifgpa_datos` | Formularios de empadronamiento y patrimonio. |
| `backend/import_df_form_comp_value_ifmad.py` | IFMAD | `public.gedo_ifmad_datos` | Modificaciones de obras y planos registrados. |
| `backend/import_df_form_comp_value_ifmhc.py` | IFMHC | `public.gedo_ifmhc_datos` | Modificaciones históricas y de conservación. |
| `backend/import_df_form_comp_value_ifmmh.py` | IFMMH | `public.gedo_ifmmh_datos` | Modificaciones menores y mantenimientos. |
| `backend/import_df_form_comp_value_ifmot.py` | IFMOT | `public.gedo_ifmot_datos` | Formularios técnicos de obras particulares. |
| `backend/import_df_form_comp_value_ifmsc.py` | IFMSC | `public.gedo_ifmsc_datos` | Superficies comunes y subdivisiones. |
| `backend/import_df_form_comp_value_ifpcb.py` | IFPCB | `public.gedo_ifpcb_datos` | Permisos de conservación de basamento. |
| `backend/import_df_form_comp_value_ifpco.py` | IFPCO | `public.gedo_ifpco_datos` | Permisos de construcciones en vía pública. |
| `backend/import_df_form_comp_value_ifpdo.py` | IFPDO (Permisos) | `public.gedo_ifpdo_datos` | Permisos de obra nueva, registro y m² a edificar. |
| `backend/import_df_form_comp_value_ifpeo.py` | IFPEO | `public.gedo_ifpeo_datos` | Permisos de ejecución de obras. |
| `backend/import_df_form_comp_value_ifrsp.py` | IFRSP | `public.gedo_ifrsp_datos` | Registros de superficies permisadas. |
| `backend/import_df_form_comp_value_ifsmc.py` | IFSMC | `public.gedo_ifsmc_datos` | Solicitudes de modificación de uso o código. |
| `backend/import_df_form_comp_value_ifsmi.py` | IFSMI | `public.gedo_ifsmi_datos` | Solicitudes de modificación en instalaciones. |
| `backend/import_df_form_comp_value_iftpt.py` | IFTPT | `public.gedo_iftpt_datos` | Tareas de protección temporal. |
| `backend/import_df_form_comp_value_pline.py` | PLINE | `public.gedo_pline_datos` | Planos de edificación e instalaciones en línea. |
| `backend/import_df_form_comp_value_proin.py` | PROIN | `public.gedo_proin_datos` | Proyectos de instalaciones aprobados. |

---

### Fase 3: Georeferenciación y Vistas Materializadas Locales

#### `backend/populate_coordinates.py`
* **Descripción**: Lee las direcciones y nomenclaturas de las tablas pivotadas GEDO (ej: `gedo_ifroc_datos`, `gedo_ifpdo_datos`) y asigna coordenadas cartográficas $(X, Y)$, Comuna y Barrio utilizando la base espacial GIS (`geo_engine`).

#### `backend/recreate_local_m2_view.py`
* **Descripción**: Regenera la Vista Materializada `public.mvw_m2_permisados` en el entorno local con sus respectivos índices (`smp`, `expediente`, `matricula_profesional`, `id_expediente`).

---

### Fase 4: Sincronización a Producción (Servidor Remoto)

#### `deploy/sync_sade_tables.py`
* **Descripción**: Sincroniza incrementalmente las tablas SADE desde PostgreSQL local hacia la base de datos remota de producción.

#### `backend/upload_gedo_tables_to_production.py`
* **Descripción**: Migra y sube las tablas pivotadas GEDO generadas localmente hacia el servidor PostgreSQL en Producción.

#### `backend/create_prod_m2_view.py`
* **Descripción**: Ejecuta el refresco de las Vistas Materializadas analíticas (`mvw_m2_permisados` y sus índices) directamente en el servidor remoto de producción.

---

### Otros Componentes Relacionados

* `backend/routers/exportar_dwg.py`: Motor cartográfico CAD para la generación de archivos DXF on-demand (capas parcelarias, LFI, LIB, tejido con 40% transparencia y etiquetas frentistas en tangente).
* `backend/pdf_generator.py`: Generador de reportes PDF A3 para trámites de LFI y morfología.
