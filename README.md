# Tablero de Gestión SGDU

Tablero institucional de gestión para la Secretaría de Gestión y Desarrollo Urbano (SGDU) enfocado en el monitoreo en tiempo real de trámites de Catastro y Obra (DGROC).

## 🚀 Inicio Rápido (Local)

Para iniciar de forma automatizada tanto el Backend como el Frontend, ejecuta el siguiente archivo por lotes en tu terminal:

```cmd
restart.bat
```

* **Acceso del Sistema:** [http://localhost:3000](http://localhost:3000)

---

## 🛠️ Scripts Operativos Clave

Si prefieres ejecutar los procesos de forma manual o necesitas correr las tareas de integración y sincronización de datos:

* **Iniciar Backend:** `python backend/main.py`
* **Iniciar Frontend:** `python -m http.server 3000 --directory frontend`
* **ETL Masivo (Oracle -> Local):** `python deploy/etl_sade.py`
* **Sincronización Delta (Local -> Producción):** `python deploy/sync_sade_tables.py`
