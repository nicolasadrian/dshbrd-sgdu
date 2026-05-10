# Tablero de Gestión SGDU - Buenos Aires Ciudad

Este proyecto es un tablero integral de gestión para la Secretaría de Gestión y Desarrollo Urbano (SGDU), diseñado para el monitoreo en tiempo real de trámites de Catastro y Obra (DGROC).

## 🚀 Arquitectura del Sistema

El sistema ha sido refactorizado para eliminar la dependencia de archivos SQL externos y maximizar el rendimiento.

### Backend (FastAPI + PostgreSQL)
- **Motor Dinámico**: Utiliza una plantilla SQL centralizada (`backend/config.py`) para generar consultas consistentes.
- **Optimización de Rendimiento**: Implementación de **Vistas Materializadas** (`mvw_reporte_consolidado_catastro`) en PostgreSQL. Esto permite que el cálculo de los 16 trámites se realice una sola vez, ofreciendo una respuesta instantánea al usuario.
- **Compatibilidad con Vercel**: Configurado como Serverless Functions para despliegue en la nube.

### Frontend (Vanilla JS + GSAP)
- **Estética Institucional**: Diseño basado en el manual de marca del Gobierno de la Ciudad de Buenos Aires (Azul, Blanco y Amarillo GCBA).
- **Experiencia de Usuario (UX)**: Animaciones elásticas estilo "Swift/iOS" utilizando la librería GSAP para transiciones fluidas entre vistas.
- **Visualización Maestro-Detalle**: Los trámites se presentan en una tabla maestra consolidada con columnas fijas para facilitar el análisis de stock y movimientos mensuales.

## 🛠️ Instalación y Uso Local

1. **Requisitos**: Python 3.10+ y PostgreSQL.
2. **Backend**:
   ```powershell
   python backend/main.py
   ```
3. **Frontend**:
   ```powershell
   python -m http.server 3000 --directory frontend
   ```
4. **Acceso**: [http://localhost:3000](http://localhost:3000)

## 📊 Actualización de Datos

Dado que la base de datos se actualiza diariamente, es necesario refrescar la Vista Materializada para ver los cambios:

```powershell
python scratch/crear_mvw_consolidada.py
```

## ☁️ Despliegue en Vercel

El proyecto incluye un archivo `vercel.json` listo para ser subido. Recuerde configurar la variable de entorno `DATABASE_URL` en el panel de control de Vercel.
