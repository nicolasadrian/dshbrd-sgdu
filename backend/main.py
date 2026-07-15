import os
import sys
import json
import time
import threading
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from sqlalchemy import text

# Ensure backend and root paths are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

load_dotenv()

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import config, database engines and routers
from config import TRAMITES_CONFIG
from database import engine, geo_engine
from schemas import User
from auth_utils import get_current_user, get_current_user_from_param_or_header

# Import APIRouters
from routers.auth import router as auth_router
from routers.rrhh import router as rrhh_router
from routers.landing import router as landing_router
from routers.reportes import router as reportes_router
from routers.ciudad3d import router as city3d_router

app = FastAPI(title="SGDU Analytics API")

app.add_middleware(GZipMiddleware, minimum_size=500)

_CORS_ORIGINS = [
    "https://dshbrd-sgdu.vercel.app",
    "https://api.geo-epesege.com.ar",
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5500",
    "http://127.0.0.1",
    "http://127.0.0.1:5500",
    "null",
]
_extra = os.getenv("CORS_ORIGINS", "")
if _extra:
    _CORS_ORIGINS += [o.strip() for o in _extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database Schema DDLs
try:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_favorite_folders (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, name)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_favorites (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                expediente VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, expediente)
            )
        """))
        conn.execute(text("""
            ALTER TABLE user_favorites ADD COLUMN IF NOT EXISTS folder_id INTEGER REFERENCES user_favorite_folders(id) ON DELETE SET NULL
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_favorites_user ON user_favorites (username)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_favorites_folder ON user_favorites (folder_id)
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_favorite_notes (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                expediente VARCHAR(100) NOT NULL,
                note_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_favorite_notes_exp ON user_favorite_notes (expediente)
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS expediente_fichas (
                expediente VARCHAR(100) PRIMARY KEY,
                direccion TEXT,
                notas_internas TEXT,
                responsable VARCHAR(100),
                estado VARCHAR(50),
                prioridad VARCHAR(20),
                proxima_reunion BOOLEAN DEFAULT FALSE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS expediente_ficha_internal_notes (
                id SERIAL PRIMARY KEY,
                expediente VARCHAR(100) NOT NULL,
                username VARCHAR(100) NOT NULL,
                note_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_exp_ficha_int_notes_exp ON expediente_ficha_internal_notes (expediente)
        """))
        conn.execute(text("ALTER TABLE cfg_gestion_metas ADD COLUMN IF NOT EXISTS descripcion_trata text"))
        conn.execute(text("ALTER TABLE cfg_gestion_metas ADD COLUMN IF NOT EXISTS direccion text"))
        
        conn.execute(text("""
            UPDATE cfg_gestion_metas
            SET direccion = 'DGROC'
            WHERE direccion IS NULL AND TRIM(LOWER(gerencia)) IN ('catastro', 'instalaciones', 'conforme', 'regularizacion', 'contable', 'etapa_proyecto', 'aviso_obra')
        """))
        conn.execute(text("""
            UPDATE cfg_gestion_metas
            SET direccion = 'DGIUR'
            WHERE direccion IS NULL AND TRIM(LOWER(gerencia)) IN ('morfologia', 'aph', 'usos')
        """))
        conn.execute(text("""
            UPDATE cfg_gestion_metas
            SET direccion = 'DGROC'
            WHERE direccion IS NULL
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.manzanas_atipicas_workflow (
                seccion VARCHAR(50) NOT NULL,
                manzana VARCHAR(50) NOT NULL,
                estado VARCHAR(50) NOT NULL DEFAULT 'Pendiente',
                analista_asignado VARCHAR(100),
                disposicion TEXT,
                archivo_trazado VARCHAR(255),
                archivo_finalizado VARCHAR(255),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (seccion, manzana)
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.manzanas_atipicas_notes (
                id SERIAL PRIMARY KEY,
                seccion VARCHAR(50) NOT NULL,
                manzana VARCHAR(50) NOT NULL,
                username VARCHAR(100) NOT NULL,
                nota TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.manzanas_lfi_workflow (
                seccion VARCHAR(50) NOT NULL,
                manzana VARCHAR(50) NOT NULL,
                estado VARCHAR(50) NOT NULL DEFAULT 'Pendiente',
                analista_asignado VARCHAR(100),
                disposicion TEXT,
                archivo_trazado VARCHAR(255),
                archivo_finalizado VARCHAR(255),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (seccion, manzana)
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.manzanas_lfi_notes (
                id SERIAL PRIMARY KEY,
                seccion VARCHAR(50) NOT NULL,
                manzana VARCHAR(50) NOT NULL,
                username VARCHAR(100) NOT NULL,
                nota TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS auth_roles (
                role_name VARCHAR(100) PRIMARY KEY,
                permissions JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.cfg_buzones_analisis_acceso (
                id SERIAL PRIMARY KEY,
                tipo_sujeto VARCHAR(50) NOT NULL,
                nombre_sujeto VARCHAR(100) NOT NULL UNIQUE,
                buzones TEXT[] NOT NULL
            )
        """))
        conn.execute(text("""
            ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS permissions JSONB DEFAULT NULL
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.cfg_tramites_familias (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) UNIQUE NOT NULL,
                tratas JSONB NOT NULL DEFAULT '[]'::jsonb
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.reportes_rrhh (
                cuil VARCHAR(255) NOT NULL,
                nombreyapellido VARCHAR(255) NOT NULL,
                fecha TIMESTAMP NOT NULL,
                feriado VARCHAR(255),
                convocado VARCHAR(255),
                hora_ingreso TIME,
                hora_salida TIME,
                cant_horas TIME,
                estado_incidencia VARCHAR(255),
                estado VARCHAR(255)
            )
        """))
        
        fam_count = conn.execute(text("SELECT COUNT(*) FROM public.cfg_tramites_familias")).scalar()
        if fam_count == 0:
            default_familias = {
                "Catastro": ["MDUG0134N", "MDUG0146A", "MDUG0131B", "MDUG0115B", "MDUG1501H", "MDUG0135A", "MDUG0131A", "MDUG0115F", "MDUG0134C", "MDUG0134E", "MDUG1501L", "MDUG0115E", "MDUG0115G", "MDUG0115C"],
                "Registros": ["MDUG3001A", "MDUG1502A", "MDUG0142A", "MDUG4003A"],
                "Incendio": ["MDUG2101A"],
                "Conforme": ["MDUG0141A", "MDUG0104A"],
                "Instalaciones": ["MDUG2901A", "MDUG2301A", "MDUG2201A", "MDUG3301A", "MDUG2601A", "MDUG2401A", "MDUG2501A", "MDUG2701A"],
                "Consultas de Usos": ["MDUG4001A", "MDUG4102A", "MJGG0302A", "MDUG0136B", "MJGG0303A"],
                "Permisos": ["MDUG1501J", "MDUG1501K", "MDUG3402A"],
                "Interpretaciones/Informe Urbanisitco": ["MDUG3601A", "MDUG1801A"],
                "Consultas Obligatorias": ["MDUG3701A", "MDUG3501A"],
                "Otros": ["MDUG0901A", "MDUG0120A", "MDUG0102B", "MDUG0107A", "MJGG1601A", "MDUG0904A", "MDUG3801A", "MJGG1701A", "MDUG1802A"]
            }
            for name, tratas in default_familias.items():
                conn.execute(
                    text("INSERT INTO public.cfg_tramites_familias (nombre, tratas) VALUES (:n, :t) ON CONFLICT DO NOTHING"),
                    {"n": name, "t": json.dumps(tratas)}
                )
        
        roles_count = conn.execute(text("SELECT COUNT(*) FROM auth_roles")).scalar()
        if roles_count == 0:
            default_roles = [
                ("administrador", json.dumps({"admin": True, "dgroc": True, "dgiur": True, "family": True, "seguimiento": True, "cierre": True, "slate": True, "subsanaciones": True, "buscador": True, "favoritos": True, "favoritos-seguimiento": True, "analytics_estadistica": True, "analytics_datasets": True, "asignados-mi": True, "buzones_analisis": True, "productividad_analistas": True, "secgdu": True, "ciudad_3d": True, "lfi_dibujar": True, "lfi_revisar": True})),
                ("admin", json.dumps({"admin": True, "dgroc": True, "dgiur": True, "family": True, "seguimiento": True, "cierre": True, "sla": True, "subsanaciones": True, "buscador": True, "favoritos": True, "favoritos-seguimiento": True, "analytics_estadistica": True, "analytics_datasets": True, "asignados-mi": True, "buzones_analisis": True, "productividad_analistas": True, "secgdu": True, "ciudad_3d": True, "lfi_dibujar": True, "lfi_revisar": True})),
                ("seguimiento", json.dumps({"admin": False, "dgroc": True, "dgiur": True, "family": True, "seguimiento": True, "cierre": True, "sla": True, "subsanaciones": True, "buscador": True, "favoritos": True, "favoritos-seguimiento": True, "analytics_estadistica": True, "analytics_datasets": True, "asignados-mi": True, "buzones_analisis": True, "productividad_analistas": False, "secgdu": True, "ciudad_3d": True, "lfi_dibujar": False, "lfi_revisar": False})),
                ("usuario", json.dumps({"admin": False, "dgroc": True, "dgiur": True, "family": True, "seguimiento": False, "cierre": False, "sla": False, "subsanaciones": False, "buscador": True, "favoritos": True, "favoritos-seguimiento": True, "analytics_estadistica": True, "analytics_datasets": True, "asignados-mi": True, "buzones_analisis": True, "productividad_analistas": False, "secgdu": False, "ciudad_3d": False, "lfi_dibujar": False, "lfi_revisar": False}))
            ]
            for r_name, r_perms in default_roles:
                conn.execute(text("INSERT INTO auth_roles (role_name, permissions) VALUES (:n, :p)"), {"n": r_name, "p": r_perms})
        else:
            conn.execute(text("""
                UPDATE auth_roles 
                SET permissions = permissions || '{"favoritos-seguimiento": true}'::jsonb
                WHERE NOT (permissions ? 'favoritos-seguimiento')
            """))
            conn.execute(text("""
                UPDATE auth_roles 
                SET permissions = permissions || '{"analytics_estadistica": true, "analytics_datasets": true}'::jsonb
                WHERE NOT (permissions ? 'analytics_estadistica')
            """))
            conn.execute(text("""
                UPDATE auth_roles 
                SET permissions = permissions || '{"asignados-mi": true}'::jsonb
                WHERE NOT (permissions ? 'asignados-mi')
            """))
            conn.execute(text("""
                UPDATE auth_roles 
                SET permissions = permissions || '{"buzones_analisis": true}'::jsonb
                WHERE NOT (permissions ? 'buzones_analisis')
            """))
            conn.execute(text("""
                UPDATE auth_roles 
                SET permissions = permissions || '{"productividad_analistas": false}'::jsonb
                WHERE NOT (permissions ? 'productividad_analistas')
            """))
            conn.execute(text("""
                UPDATE auth_roles 
                SET permissions = permissions || '{"secgdu": true}'::jsonb
                WHERE NOT (permissions ? 'secgdu')
            """))
            conn.execute(text("""
                UPDATE auth_roles 
                SET permissions = permissions || '{"ciudad_3d": true}'::jsonb
                WHERE NOT (permissions ? 'ciudad_3d') AND role_name IN ('administrador', 'admin', 'seguimiento')
            """))
            conn.execute(text("""
                UPDATE auth_roles 
                SET permissions = permissions || '{"ciudad_3d": false}'::jsonb
                WHERE NOT (permissions ? 'ciudad_3d')
            """))
            conn.execute(text("""
                UPDATE auth_roles 
                SET permissions = permissions || '{"lfi_dibujar": true}'::jsonb
                WHERE NOT (permissions ? 'lfi_dibujar') AND role_name IN ('administrador', 'admin', 'troneras')
            """))
            conn.execute(text("""
                UPDATE auth_roles 
                SET permissions = permissions || '{"lfi_dibujar": false}'::jsonb
                WHERE NOT (permissions ? 'lfi_dibujar')
            """))
            conn.execute(text("""
                UPDATE auth_roles 
                SET permissions = permissions || '{"lfi_revisar": true}'::jsonb
                WHERE NOT (permissions ? 'lfi_revisar') AND role_name IN ('administrador', 'admin', 'troneras-visor')
            """))
            conn.execute(text("""
                UPDATE auth_roles 
                SET permissions = permissions || '{"lfi_revisar": false}'::jsonb
                WHERE NOT (permissions ? 'lfi_revisar')
            """))
            conn.execute(text("""
                UPDATE auth_users 
                SET permissions = permissions || '{"ciudad_3d": true}'::jsonb
                WHERE permissions IS NOT NULL 
                  AND NOT (permissions ? 'ciudad_3d')
                  AND role IN ('administrador', 'admin', 'seguimiento')
            """))
            conn.execute(text("""
                UPDATE auth_users 
                SET permissions = permissions || '{"ciudad_3d": false}'::jsonb
                WHERE permissions IS NOT NULL 
                  AND NOT (permissions ? 'ciudad_3d')
            """))
            conn.execute(text("""
                UPDATE auth_users 
                SET permissions = permissions || '{"lfi_dibujar": true}'::jsonb
                WHERE permissions IS NOT NULL 
                  AND NOT (permissions ? 'lfi_dibujar')
                  AND role IN ('administrador', 'admin', 'troneras')
            """))
            conn.execute(text("""
                UPDATE auth_users 
                SET permissions = permissions || '{"lfi_dibujar": false}'::jsonb
                WHERE permissions IS NOT NULL 
                  AND NOT (permissions ? 'lfi_dibujar')
            """))
            conn.execute(text("""
                UPDATE auth_users 
                SET permissions = permissions || '{"lfi_revisar": true}'::jsonb
                WHERE permissions IS NOT NULL 
                  AND NOT (permissions ? 'lfi_revisar')
                  AND role IN ('administrador', 'admin', 'troneras-visor')
            """))
            conn.execute(text("""
                UPDATE auth_users 
                SET permissions = permissions || '{"lfi_revisar": false}'::jsonb
                WHERE permissions IS NOT NULL 
                  AND NOT (permissions ? 'lfi_revisar')
            """))
            
            roles_db = conn.execute(text("SELECT role_name, permissions FROM auth_roles")).fetchall()
            roles_map = {r[0]: r[1] for r in roles_db}
            users_db = conn.execute(text("SELECT username, role, permissions FROM auth_users WHERE permissions IS NOT NULL")).fetchall()
            for user in users_db:
                u_name = user[0]
                u_role = user[1]
                u_perms = user[2] or {}
                r_perms = roles_map.get(u_role, {})
                updated = False
                for k, v in r_perms.items():
                    if k not in u_perms:
                        u_perms[k] = v
                        updated = True
                if updated:
                    conn.execute(
                        text("UPDATE auth_users SET permissions = :p WHERE username = :u"),
                        {"p": json.dumps(u_perms), "u": u_name}
                    )
            # Migración: agregar permiso universo_tratas a roles que no lo tienen aún
            # Por defecto: false para todos (el admin lo configura vía backlog)
            conn.execute(text("""
                UPDATE auth_roles
                SET permissions = permissions || '{"universo_tratas": false}'::jsonb
                WHERE NOT (permissions ? 'universo_tratas')
            """))
            conn.execute(text("""
                UPDATE auth_users
                SET permissions = permissions || '{"universo_tratas": false}'::jsonb
                WHERE permissions IS NOT NULL
                  AND NOT (permissions ? 'universo_tratas')
            """))

        # Crear vista materializada mvw_universo_tratas si no existe
        try:
            conn.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS mvw_universo_tratas AS
                SELECT
                    TRIM(e.trata) AS trata,
                    MAX(e.descripcion_trata) AS descripcion_trata,
                    COUNT(DISTINCT e.id_expediente) AS cant_expedientes,
                    COUNT(DISTINCT CASE
                        WHEN UPPER(e.estado) NOT LIKE '%ARCHIVO%'
                         AND UPPER(e.estado) NOT LIKE '%GUARDA%'
                        THEN e.id_expediente END) AS cant_en_stock,
                    COUNT(DISTINCT CASE
                        WHEN UPPER(e.estado) LIKE '%ARCHIVO%'
                        THEN e.id_expediente END) AS cant_archivo,
                    COUNT(DISTINCT CASE
                        WHEN UPPER(e.estado) LIKE '%GUARDA%'
                        THEN e.id_expediente END) AS cant_guarda_temporal,
                    EXISTS(
                        SELECT 1 FROM cfg_gestion_metas cfg
                        WHERE TRIM(UPPER(cfg.trata_reporte)) = TRIM(UPPER(e.trata))
                           OR TRIM(UPPER(e.trata)) = ANY(
                                SELECT TRIM(UPPER(t)) FROM unnest(cfg.tratas_incluidas) t
                           )
                    ) AS alta_en_tablero
                FROM mvw_expedientes_tratas_secgdu e
                WHERE e.trata IS NOT NULL AND TRIM(e.trata) != ''
                GROUP BY TRIM(e.trata)
                WITH DATA
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_mvw_universo_tratas_trata
                ON mvw_universo_tratas (trata)
            """))
            logger.info("Vista materializada mvw_universo_tratas creada correctamente")
        except Exception as e_mv:
            logger.warning(f"mvw_universo_tratas ya existe o error al crear: {e_mv}")

except Exception as e:
    logger.error(f"Error executing database migrations/initialization DDLs: {e}")



# --- Core Global Endpoints ---

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": time.time()}


# --- Mount Routers ---
app.include_router(auth_router)
app.include_router(rrhh_router)
app.include_router(landing_router)
app.include_router(reportes_router)
app.include_router(city3d_router)


if __name__ == "__main__":
    import uvicorn
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
        
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
