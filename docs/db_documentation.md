# Documentación de Base de Datos - SGDU Analytics

Esta documentación detalla la estructura, lógica y flujo de datos de la base de datos `sade_db`, utilizada para el sistema de reportes de la Secretaría de Gestión y Desarrollo Urbano (SGDU).

## 1. Arquitectura General

El sistema utiliza una arquitectura de **ETL (Extract, Transform, Load)** simplificada basada en vistas de PostgreSQL:
1.  **Origen de Datos (SADE Sync)**: Vistas materializadas que se sincronizan con la base de datos central de SADE.
2.  **Capa de Configuración**: Tablas que definen el comportamiento de cada gerencia y trámite.
3.  **Capa de Lógica (Ciclo de Vida)**: Vistas que procesan los "pases" y documentos para determinar ingresos, egresos y stock.
4.  **Capa de Presentación**: Vistas materializadas optimizadas para el consumo del Dashboard (Backend/Frontend).

---

## 2. Capa de Configuración y Seguridad

### `auth_users`
Tabla para la gestión de acceso al Dashboard.
- **Campos**: `id`, `username`, `password_hash` (bcrypt), `role` (admin/user), `created_at`.
- **Propósito**: Control de autenticación para la API de FastAPI.

### `cfg_gestion_metas`
El "cerebro" del sistema. Define cómo se miden los trámites por gerencia.
- **Campos**:
    - `gerencia`: Identificador de la gerencia (ej: `catastro`, `instalaciones`).
    - `trata_reporte`: Nombre del trámite en el reporte (ej: `MDUG0115C`).
    - `tratas_incluidas`: Array de códigos SADE que componen este reporte.
    - `buzones_ingreso`: Array de reparticiones/sectores que marcan el ingreso al área.
    - `analistas_oficiales`: Whitelist de usuarios que poseen el "Stock Propio".
    - `acronimos_egreso`: Códigos de documentos (GEDO) que cierran el trámite.
    - `metas_mensuales`: JSONB para definir objetivos por periodo.

---

## 3. Capa de Datos (SADE Source)

Estas vistas son réplicas (ReadOnly) de los datos operativos de SADE:
- **`mvw_ee_pases_secgdu`**: Historial completo de movimientos de expedientes.
- **`mvw_expedientes_tratas_secgdu`**: Información general del expediente (trata, estado, carátula).
- **`mvw_datos_gedo_secgdu`**: Listado de todos los documentos generados en los expedientes.

---

## 4. Vistas de Lógica y Procesamiento

### `v_expedientes_lifecycle`
Procesa el ciclo de vida de cada expediente basado en `cfg_gestion_metas`.
- **Lógica de Ingreso**: Se registra cuando un expediente llega a uno de los `buzones_ingreso`.
- **Lógica de Egreso Efectivo**: Cuando se genera un documento del tipo `acronimos_egreso`.
- **Lógica de Egreso No Efectivo**: Cuando el expediente sale de la whitelist de analistas sin un documento conclusivo (ej: pase a otra área o guarda temporal).

### `mvw_reporte_historico_{gerencia}`
Vistas materializadas por gerencia (ej: `mvw_reporte_historico_catastro`).
- **Columnas**: `anio`, `mes`, `COD TRATA`, `DETALLE TRATA`, `ING` (Ingresos), `EGR_EF` (Egresos Efectivos), `EGR_NE` (Egresos No Efectivos), `STOCK_SUBS` (Subsanaciones), `STOCK_TOTAL`.
- **Frecuencia de Actualización**: Se refrescan mediante el script `run_etl_full.py`.

### `mvw_stock_actual_detalle`
Vista optimizada para el desglose del stock actual.
- **Propósito**: Permite al usuario ver exactamente qué expedientes componen el stock, cuántos días llevan en el área y quién es el analista actual.

---

## 5. Flujos de Actualización (Cron)

1.  **Sync**: El script `sync_public.py` trae los datos frescos de SADE a las vistas `mvw_..._secgdu`.
2.  **Transform**: El script `update_views_public.py` refresca las vistas materializadas de reportes históricos.
3.  **Run**: `run_etl_full.py` es el orquestador principal que ejecuta ambos pasos de forma secuencial.

---

## 6. Diccionario de Términos

- **Stock Propio**: Expedientes que están en poder de un usuario incluido en la whitelist de la gerencia y no están en estado "Subsanación".
- **Subsanación**: Expedientes que el profesional/usuario externo debe corregir. Se miden por separado ya que el área no tiene control sobre su tiempo de respuesta.
- **Egreso Efectivo**: Trámite finalizado con la firma de un acto administrativo (GEDO) previsto.
- **Intervenciones**: Trámites que pasan por el área pero cuya resolución final no corresponde a la misma (no tienen un GEDO conclusivo propio).
