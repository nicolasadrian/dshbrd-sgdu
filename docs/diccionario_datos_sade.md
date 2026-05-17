# Diccionario de Datos Maestro - SADE SGDU

Este documento detalla la estructura de las tablas crudas sincronizadas desde Oracle hacia la base de datos local `sade_db`. Estas tablas son la fuente de verdad para toda la analítica del sistema.

---

## 1. mvw_expedientes_tratas_secgdu (Metadatos del Expediente)
Contiene la información general y el estado actual de cada trámite.

| Columna | Descripción |
| :--- | :--- |
| `id_expediente` | ID numérico interno (FK para cruces). |
| `expediente` | Número de expediente oficial (Ej: EX-2025-...). |
| `descripcion` | Descripción/Asunto del expediente. |
| `trata` | Código de trata (Ej: MDUG2101A). |
| `estado` | Estado actual en SADE (Tramitación, Pendiente, Subsanación, Archivo). |
| `usuario_modificador` | Último usuario que modificó el expediente. |
| `fecha_modificacion` | Fecha de la última actualización de estado o metadato. |

---

## 2. mvw_ee_pases_secgdu (Historial de Movimientos)
Registra cada pase del expediente entre usuarios y sectores. Es fundamental para el cálculo de **Stock**.

| Columna | Descripción |
| :--- | :--- |
| `id_expediente` | ID del expediente relacionado. |
| `fecha` | Fecha y hora exacta del pase. |
| `usuario` | Usuario o sistema que realiza el envío (Remitente). |
| `destinatario` | Usuario o buzón que recibe el expediente (Poseedor actual). |
| `estado` | Estado del expediente al momento del pase. |

---

## 3. mvw_datos_gedo_secgdu (Documentos Generados)
Contiene el registro de todos los documentos firmados y asociados al expediente. Se usa para detectar **Egresos Efectivos**.

| Columna | Descripción |
| :--- | :--- |
| `id_expediente` | ID del expediente relacionado. |
| `acronimo` | Tipo de documento (Ej: PROIN, PLINE, IF, PV). |
| `documento` | Número GDE del documento generado. |
| `usuario_creador` | Usuario que generó el documento. |
| `fecha_creacion` | Fecha de firma/generación. |

---

## 4. mvw_ee_actividades_secgdu (Actividades Internas y TAD)
Registra actividades específicas como subsanaciones, pases internos y tareas de TAD.

| Columna | Descripción |
| :--- | :--- |
| `id_expediente` | ID del expediente relacionado. |
| `nombre_tipo_actividad`| Tipo de tarea (Ej: SUBSANACION, SOLICITUD_SUBSANACION_TAD). |
| `estado` | **CLAVE**: Si es 'PENDIENTE', el expediente está esperando acción del vecino. |
| `fecha_alta` | Fecha de inicio de la actividad. |
| `fecha_cierre` | Fecha en que se completó la tarea. |

---

## 5. cfg_gestion_metas (Configuración de Negocio)
Tabla local para definir las reglas de cada gerencia.

| Columna | Descripción |
| :--- | :--- |
| `gerencia` | Nombre identificador de la gerencia (Ej: instalaciones). |
| `trata_reporte` | Nombre que aparecerá en el Dashboard. |
| `buzones_ingreso` | Lista (Array) de buzones que inician el conteo. |
| `analistas_oficiales`| Lista (Array) de usuarios que conforman el Stock Propio. |
| `tratas_incluidas` | Lista (Array) de códigos de trata a monitorear. |
| `acronimos_egreso` | Lista (Array) de GEDOs que marcan el fin del trámite. |

---

## 🔗 Relaciones Sugeridas para Consultas

*   **Para Stock Real**: 
    1. Buscar el máximo `fecha` en `mvw_ee_pases_secgdu` por `id_expediente`.
    2. Verificar si el `destinatario` está en tu lista de analistas.
*   **Para Subsanación**:
    1. Cruzar el Stock con `mvw_ee_actividades_secgdu` donde `estado = 'PENDIENTE'`.
*   **Para Egresos**:
    1. Buscar en `mvw_datos_gedo_secgdu` registros posteriores a la fecha de ingreso al área.
