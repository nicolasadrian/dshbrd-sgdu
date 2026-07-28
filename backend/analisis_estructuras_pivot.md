# Informe de Análisis de Estructuras Pivote por Acrónimo

Este informe detalla los campos del formulario (`input_name`) detectados para cada uno de los acrónimos (GEDO) rastreados, el tipo de dato predominante (`TEXT`, `INT`, `DATE`, `BOOL`, etc.) y la frecuencia con la que aparecen en la tabla `df_form_comp_value`.

## Resumen General de Campos Únicos por Acrónimo

| Acrónimo | Cantidad de Campos Detectados | Estado / Observación |
|---|---|---|
| **CECNU** | 291 | Listo para pivote |
| **FIPAR** | 13 | Listo para pivote |
| **IFCAC** | 0 | Sin datos o ya absorbido por otras transacciones |
| **IFCAO** | 0 | Sin datos o ya absorbido por otras transacciones |
| **IFCFP** | 0 | Sin datos o ya absorbido por otras transacciones |
| **IFCIS** | 78 | Listo para pivote |
| **IFDEX** | 7 | Listo para pivote |
| **IFGPA** | 11 | Listo para pivote |
| **IFMAD** | 0 | Sin datos o ya absorbido por otras transacciones |
| **IFMHC** | 0 | Sin datos o ya absorbido por otras transacciones |
| **IFMMH** | 0 | Sin datos o ya absorbido por otras transacciones |
| **IFMOT** | 0 | Sin datos o ya absorbido por otras transacciones |
| **IFMSC** | 0 | Sin datos o ya absorbido por otras transacciones |
| **IFOCD** | 375 | Listo para pivote |
| **IFPCB** | 9 | Listo para pivote |
| **IFPCO** | 310 | Listo para pivote |
| **IFPDO** | 258 | Listo para pivote |
| **IFPEO** | 128 | Listo para pivote |
| **IFROC** | 167 | Listo para pivote |
| **IFRSP** | 101 | Listo para pivote |
| **IFSMC** | 324 | Listo para pivote |
| **IFSMI** | 141 | Listo para pivote |
| **IFTPT** | 132 | Listo para pivote |
| **PLINE** | 590 | Listo para pivote |
| **PROIN** | 480 | Listo para pivote |

---

## Detalle de Campos por Acrónimo

### 📄 Acrónimo: CECNU
Se detectaron **291** campos únicos para CECNU. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `dom_est_calle` | `TEXT` | 5,592 |
| `dom_caba_numero` | `TEXT` | 5,592 |
| `separator_inm_num` | `INT` | 5,581 |
| `Sseparator_aclaracion` | `INT` | 5,580 |
| `Sseparator_dom_est` | `INT` | 5,580 |
| `dom_est_calle_dgparcela` | `TEXT` | 5,576 |
| `dom_est_calle_dgbarrio` | `TEXT` | 5,576 |
| `dom_est_calle_dgseccion` | `TEXT` | 5,576 |
| `dom_est_calle_dgmanzana` | `TEXT` | 5,576 |
| `dom_est_calle_dgcomuna` | `TEXT` | 5,576 |
| `dom_caba_calle` | `TEXT` | 5,558 |
| `dom_caba_calle_dgcomuna` | `TEXT` | 5,558 |
| `dom_caba_calle_dgbarrio` | `TEXT` | 5,558 |
| `dom_caba_calle_dgparcela` | `TEXT` | 5,558 |
| `dom_caba_calle_dgseccion` | `TEXT` | 5,558 |
| *... y 276 campos adicionales* | | |


### 📄 Acrónimo: FIPAR
Se detectaron **13** campos únicos para FIPAR. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `num_ex` | `TEXT` | 96,243 |
| `dom_caba_calle` | `TEXT` | 96,243 |
| `dom_caba_calle_seccion` | `TEXT` | 89,422 |
| `dom_caba_calle_manzana` | `TEXT` | 89,418 |
| `dom_caba_calle_parcela` | `TEXT` | 89,409 |
| `dom_caba_calle_comuna` | `TEXT` | 64,830 |
| `dom_caba_calle_barrio` | `TEXT` | 64,624 |
| `dom_caba_calle_cpu` | `TEXT` | 51,314 |
| `dom_caba_calle_dgseccion` | `TEXT` | 5,228 |
| `dom_caba_calle_dgbarrio` | `TEXT` | 5,228 |
| `dom_caba_calle_dgcomuna` | `TEXT` | 5,228 |
| `dom_caba_calle_dgparcela` | `TEXT` | 5,228 |
| `dom_caba_calle_dgmanzana` | `TEXT` | 5,228 |


### 📄 Acrónimo: IFCIS
Se detectaron **78** campos únicos para IFCIS. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `encomienda_profesional_rep` | `TEXT` | 244 |
| `acredi_inter_legi_anio` | `INT` | 244 |
| `acredi_inter_legi_nro` | `INT` | 244 |
| `acredi_inter_legi_rep` | `TEXT` | 244 |
| `apellido_profesional` | `TEXT` | 244 |
| `comprobante_pago_act` | `TEXT` | 244 |
| `comprobante_pago_anio` | `INT` | 244 |
| `comprobante_pago_nro` | `INT` | 244 |
| `comprobante_pago_rep` | `TEXT` | 244 |
| `encomienda_profesional_act` | `TEXT` | 244 |
| `encomienda_profesional_anio` | `INT` | 244 |
| `encomienda_profesional_nro` | `INT` | 244 |
| `acredi_inter_legi_act` | `TEXT` | 244 |
| `hay_observaciones` | `BOOL` | 244 |
| `hay_uf` | `BOOL` | 244 |
| *... y 63 campos adicionales* | | |


### 📄 Acrónimo: IFDEX
Se detectaron **7** campos únicos para IFDEX. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `tipo_documento` | `TEXT` | 48,250 |
| `Sseparator_ubicacion` | `INT` | 48,250 |
| `seccion` | `TEXT` | 48,248 |
| `manzana` | `TEXT` | 48,248 |
| `parcela` | `TEXT` | 42,142 |
| `expediente` | `TEXT` | 41,990 |
| `observaciones` | `TEXT` | 11,282 |


### 📄 Acrónimo: IFGPA
Se detectaron **11** campos únicos para IFGPA. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `componente_domicilio` | `TEXT` | 11,138 |
| `componente_domicilio_dgbarrio` | `TEXT` | 11,138 |
| `componente_domicilio_dgcomuna` | `TEXT` | 11,138 |
| `componente_domicilio_dgmanzana` | `TEXT` | 11,138 |
| `componente_domicilio_dgparcela` | `TEXT` | 11,138 |
| `componente_domicilio_dgseccion` | `TEXT` | 11,138 |
| `expediente_sade_act` | `TEXT` | 11,138 |
| `expediente_sade_anio` | `INT` | 11,138 |
| `expediente_sade_nro` | `INT` | 11,138 |
| `expediente_sade_rep` | `TEXT` | 11,138 |
| `motivo` | `TEXT` | 11,138 |


### 📄 Acrónimo: IFOCD
Se detectaron **375** campos únicos para IFOCD. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `sup_demoler` | `DOUBLE` | 19,137 |
| `sup_construir` | `DOUBLE` | 19,137 |
| `pisos` | `INT` | 19,137 |
| `pago_derechos_rep` | `TEXT` | 19,137 |
| `pago_derechos_nro` | `INT` | 19,137 |
| `pago_derechos_anio` | `INT` | 19,137 |
| `pago_derechos_act` | `TEXT` | 19,137 |
| `separator_datos_profesional` | `INT` | 19,137 |
| `separator_otra_documentacion` | `INT` | 19,137 |
| `separator_ubicacion` | `INT` | 19,137 |
| `nombre_profesional` | `TEXT` | 19,137 |
| `matricula_profesional` | `TEXT` | 19,137 |
| `ubicacion_dgseccion` | `TEXT` | 19,137 |
| `informe_dominio_rep` | `TEXT` | 19,137 |
| `encomienda_profesional_act` | `TEXT` | 19,137 |
| *... y 360 campos adicionales* | | |


### 📄 Acrónimo: IFPCB
Se detectaron **9** campos únicos para IFPCB. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `dir` | `TEXT` | 11,222 |
| `expediente_act` | `TEXT` | 11,222 |
| `expediente_anio` | `INT` | 11,222 |
| `expediente_nro` | `INT` | 11,222 |
| `expediente_rep` | `TEXT` | 11,222 |
| `manzana` | `TEXT` | 11,222 |
| `parcela` | `TEXT` | 11,222 |
| `seccion` | `TEXT` | 11,222 |
| `Sseparator_datos` | `INT` | 11,222 |


### 📄 Acrónimo: IFPCO
Se detectaron **310** campos únicos para IFPCO. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `hay_observaciones` | `BOOL` | 7,411 |
| `num_sade_profesional_rep` | `TEXT` | 7,411 |
| `num_sade_profesional_nro` | `INT` | 7,411 |
| `num_sade_profesional_anio` | `INT` | 7,411 |
| `pisos` | `INT` | 7,411 |
| `num_sade_profesional_act` | `TEXT` | 7,411 |
| `ubicacion` | `TEXT` | 7,411 |
| `tipo_tarea` | `TEXT` | 7,411 |
| `corresponde_uso_particular` | `TEXT` | 7,411 |
| `nombre` | `TEXT` | 7,411 |
| `sup_terreno` | `DOUBLE` | 7,411 |
| `profundidad` | `DOUBLE` | 7,411 |
| `subsuelos` | `INT` | 7,411 |
| `Sseparator_tipo_tarea` | `INT` | 7,411 |
| `Sseparator_plano` | `INT` | 7,411 |
| *... y 295 campos adicionales* | | |


### 📄 Acrónimo: IFPDO
Se detectaron **258** campos únicos para IFPDO. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `ubicacion_dgbarrio` | `TEXT` | 25,538 |
| `dominio_documentacion_nro` | `INT` | 25,538 |
| `dominio_documentacion_rep` | `TEXT` | 25,538 |
| `Sseparator_documentacion` | `INT` | 25,538 |
| `Sseparator_datos_propietarios` | `INT` | 25,538 |
| `separator_planos` | `INT` | 25,538 |
| `separator_otra_documentacion` | `INT` | 25,538 |
| `certificado_documentacion_nro` | `INT` | 25,538 |
| `certificado_documentacion_anio` | `INT` | 25,538 |
| `certificado_documentacion_act` | `TEXT` | 25,538 |
| `ubicacion` | `TEXT` | 25,538 |
| `particularizado` | `TEXT` | 25,538 |
| `hay_observaciones` | `BOOL` | 25,538 |
| `gedo_planos_rep` | `TEXT` | 25,538 |
| `gedo_planos_nro` | `INT` | 25,538 |
| *... y 243 campos adicionales* | | |


### 📄 Acrónimo: IFPEO
Se detectaron **128** campos únicos para IFPEO. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `altura_metros` | `DOUBLE` | 286 |
| `apellido_profesional` | `TEXT` | 286 |
| `estudios_suelos_anio` | `INT` | 286 |
| `estudios_suelos_nro` | `INT` | 286 |
| `estudios_suelos_rep` | `TEXT` | 286 |
| `expediente_seismilcua_act` | `TEXT` | 286 |
| `expediente_seismilcua_anio` | `INT` | 286 |
| `expediente_seismilcua_nro` | `INT` | 286 |
| `expediente_seismilcua_rep` | `TEXT` | 286 |
| `hay_observaciones` | `BOOL` | 286 |
| `hay_uf` | `BOOL` | 286 |
| `id` | `TEXT` | 286 |
| `informe_dominio_act` | `TEXT` | 286 |
| `informe_dominio_anio` | `INT` | 286 |
| `informe_dominio_nro` | `INT` | 286 |
| *... y 113 campos adicionales* | | |


### 📄 Acrónimo: IFROC
Se detectaron **167** campos únicos para IFROC. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `num_expediente_rep` | `TEXT` | 3,027 |
| `num_expediente_act` | `TEXT` | 3,027 |
| `num_expediente_anio` | `INT` | 3,027 |
| `registro_plano_rep` | `TEXT` | 3,027 |
| `registro_plano_nro` | `INT` | 3,027 |
| `registro_plano_anio` | `INT` | 3,027 |
| `registro_plano_act` | `TEXT` | 3,027 |
| `sup_permiso` | `DOUBLE` | 3,027 |
| `encomienda_prof_act` | `TEXT` | 3,027 |
| `encomienda_prof_anio` | `INT` | 3,027 |
| `encomienda_prof_nro` | `INT` | 3,027 |
| `encomienda_prof_rep` | `TEXT` | 3,027 |
| `hay_observaciones` | `BOOL` | 3,027 |
| `separator_usos_dos` | `INT` | 3,027 |
| `informe_dominio_act` | `TEXT` | 3,027 |
| *... y 152 campos adicionales* | | |


### 📄 Acrónimo: IFRSP
Se detectaron **101** campos únicos para IFRSP. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `apellido_profesional` | `TEXT` | 69 |
| `corresponde_control` | `TEXT` | 69 |
| `encomienda_profesional_act` | `TEXT` | 69 |
| `encomienda_profesional_anio` | `INT` | 69 |
| `encomienda_profesional_nro` | `INT` | 69 |
| `encomienda_profesional_rep` | `TEXT` | 69 |
| `hay_observaciones` | `TEXT` | 69 |
| `hay_uf` | `TEXT` | 69 |
| `interes_legitimmo_act` | `TEXT` | 69 |
| `interes_legitimmo_anio` | `INT` | 69 |
| `interes_legitimmo_nro` | `INT` | 69 |
| `interes_legitimmo_rep` | `TEXT` | 69 |
| `matricula_profesional` | `TEXT` | 69 |
| `nombre_profesional` | `TEXT` | 69 |
| `numero_sade_act` | `TEXT` | 69 |
| *... y 86 campos adicionales* | | |


### 📄 Acrónimo: IFSMC
Se detectaron **324** campos únicos para IFSMC. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `ubicacion_dgbarrio` | `TEXT` | 1,321 |
| `numero_sade_nro` | `INT` | 1,321 |
| `numero_sade_anio` | `INT` | 1,321 |
| `numero_sade_act` | `TEXT` | 1,321 |
| `acredi_inter_legi_nro` | `INT` | 1,321 |
| `Sseparator_hay_observaciones` | `INT` | 1,321 |
| `Sseparator_hay_uf` | `INT` | 1,321 |
| `Sseparator_observaciones` | `INT` | 1,321 |
| `ubicacion_dgparcela` | `TEXT` | 1,321 |
| `sup_afectada` | `DOUBLE` | 1,321 |
| `tipo_profesional` | `TEXT` | 1,321 |
| `ubicacion` | `TEXT` | 1,321 |
| `ubicacion_dgmanzana` | `TEXT` | 1,321 |
| `acredi_inter_legi_anio` | `INT` | 1,321 |
| `encomienda_profesional_act` | `TEXT` | 1,321 |
| *... y 309 campos adicionales* | | |


### 📄 Acrónimo: IFSMI
Se detectaron **141** campos únicos para IFSMI. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `hay_observaciones` | `BOOL` | 422 |
| `separatotor_acreditacion_inter` | `INT` | 422 |
| `separator_ubicacion` | `INT` | 422 |
| `numero_sade_act` | `TEXT` | 422 |
| `numero_sade_anio` | `INT` | 422 |
| `numero_sade_b_act` | `TEXT` | 422 |
| `separator_permiso_obra_otorgad` | `INT` | 422 |
| `numero_sade_b_anio` | `INT` | 422 |
| `ubicacion` | `TEXT` | 422 |
| `numero_sade_b_nro` | `INT` | 422 |
| `separator_pago` | `INT` | 422 |
| `numero_sade_b_rep` | `TEXT` | 422 |
| `separator_otra_doc` | `INT` | 422 |
| `numero_sade_c_act` | `TEXT` | 422 |
| `numero_sade_c_anio` | `INT` | 422 |
| *... y 126 campos adicionales* | | |


### 📄 Acrónimo: IFTPT
Se detectaron **132** campos únicos para IFTPT. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `altura` | `DOUBLE` | 191 |
| `apellido_profesional` | `TEXT` | 191 |
| `encomienda_profesional_act` | `TEXT` | 191 |
| `encomienda_profesional_anio` | `INT` | 191 |
| `encomienda_profesional_nro` | `INT` | 191 |
| `encomienda_profesional_rep` | `TEXT` | 191 |
| `expediente_seismilcua_act` | `TEXT` | 191 |
| `expediente_seismilcua_anio` | `INT` | 191 |
| `expediente_seismilcua_nro` | `INT` | 191 |
| `expediente_seismilcua_rep` | `TEXT` | 191 |
| `gedo_documento_act` | `TEXT` | 191 |
| `gedo_documento_anio` | `INT` | 191 |
| `gedo_documento_nro` | `INT` | 191 |
| `gedo_documento_rep` | `TEXT` | 191 |
| `hay_observaciones` | `BOOL` | 191 |
| *... y 117 campos adicionales* | | |


### 📄 Acrónimo: PLINE
Se detectaron **590** campos únicos para PLINE. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `numero_sade_rep` | `TEXT` | 19,297 |
| `plano_instalacion_ejecutada_rep` | `TEXT` | 19,297 |
| `separator_datos_profesional` | `INT` | 19,297 |
| `ubicacion_dgbarrio` | `TEXT` | 19,297 |
| `ubicacion` | `TEXT` | 19,297 |
| `tipo_profesional_dgroc` | `TEXT` | 19,297 |
| `apellido_profesional` | `TEXT` | 19,297 |
| `tipo_plano` | `TEXT` | 19,297 |
| `ubicacion_dgparcela` | `TEXT` | 19,297 |
| `plano_instalacion_ejecutada_nro` | `INT` | 19,297 |
| `numero_sade_nro` | `INT` | 19,297 |
| `numero_sade_anio` | `INT` | 19,297 |
| `numero_sade_act` | `TEXT` | 19,297 |
| `nombre_profesional` | `TEXT` | 19,297 |
| `matricula_profesional` | `TEXT` | 19,297 |
| *... y 575 campos adicionales* | | |


### 📄 Acrónimo: PROIN
Se detectaron **480** campos únicos para PROIN. A continuación se detallan los 15 más frecuentes:

| Campo (`input_name`) | Tipo Predominante | Registros Detectados |
|---|---|---|
| `tipo_instalacion` | `TEXT` | 22,370 |
| `comprobante_pago_act` | `TEXT` | 22,370 |
| `comprobante_pago_anio` | `INT` | 22,370 |
| `comprobante_pago_nro` | `INT` | 22,370 |
| `comprobante_pago_rep` | `TEXT` | 22,370 |
| `ubicacion_dgcomuna` | `TEXT` | 22,370 |
| `ubicacion_dgparcela` | `TEXT` | 22,370 |
| `ubicacion_dgbarrio` | `TEXT` | 22,370 |
| `ubicacion` | `TEXT` | 22,370 |
| `tipo_profesional` | `TEXT` | 22,370 |
| `encomienda_profesional_act` | `TEXT` | 22,370 |
| `encomienda_profesional_anio` | `INT` | 22,370 |
| `encomienda_profesional_nro` | `INT` | 22,370 |
| `apellido_profesional` | `TEXT` | 22,370 |
| `encomienda_profesional_rep` | `TEXT` | 22,370 |
| *... y 465 campos adicionales* | | |

