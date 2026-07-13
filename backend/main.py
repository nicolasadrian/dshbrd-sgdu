import os
import sys
import json
from fastapi import FastAPI, HTTPException, Depends, status, Query, Header, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime, timedelta, date
import logging
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Ensure backend and root paths are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Cargar variables de entorno desde .env
load_dotenv()

try:
    from .config import TRAMITES_CONFIG, WHITELISTS, BUZZERS_MAP
except ImportError:
    from config import TRAMITES_CONFIG, WHITELISTS, BUZZERS_MAP

# Configuración de Seguridad
SECRET_KEY = os.getenv("SECRET_KEY", "7b6f8e9a2c4d5f1a3b5e7d9c0a2b4d6f8e0a2c4d")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 horas

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SGDU Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str
    full_name: str
    sector: str
    needs_password_change: bool
    permissions: Optional[Dict[str, bool]] = None

class User(BaseModel):
    username: str
    role: str
    full_name: Optional[str] = None
    sector: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None

class PasswordChange(BaseModel):
    new_password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    sector: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None

class RoleCreate(BaseModel):
    role_name: str

class RoleUpdate(BaseModel):
    permissions: Dict[str, bool]

class MetaUpdateRequest(BaseModel):
    direccion: Optional[str] = None
    gerencia: Optional[str] = None
    trata_reporte: Optional[str] = None
    tratas_incluidas: List[str]
    buzones_ingreso: List[str]
    analistas_oficiales: List[str]
    acronimos_egreso: List[str]
    activo: bool
    firmantes_egreso: Optional[List[str]] = None
    buzones_ingreso_intervenciones: Optional[List[str]] = None
    descripciones_validas: Optional[List[str]] = None
    descripcion_trata: Optional[str] = None

class MetaCreateRequest(BaseModel):
    direccion: str
    gerencia: str
    trata_reporte: str
    tratas_incluidas: List[str] = []
    buzones_ingreso: List[str] = []
    analistas_oficiales: List[str] = []
    acronimos_egreso: List[str] = []
    activo: bool = True
    firmantes_egreso: Optional[List[str]] = []
    buzones_ingreso_intervenciones: Optional[List[str]] = []
    descripciones_validas: Optional[List[str]] = []
    descripcion_trata: Optional[str] = ""

# Función para obtener el motor de DB de forma segura
def get_engine():
    # En localhost priorizamos la local, en Vercel se usará DATABASE_URL o PUBLIC
    db_url = os.getenv("DATABASE_URL_LOCAL") or os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_PUBLIC")
    if not db_url:
        db_url = "postgresql://postgres:lenovo@localhost:5432/sade_db"
    
    # Corregir prefijo para SQLAlchemy
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    return create_engine(db_url, pool_size=5, max_overflow=10)

engine = get_engine()

def get_geo_mdr_engine():
    db_url = os.getenv("DATABASE_URL_LOCAL") or os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_PUBLIC")
    if not db_url:
        db_url = "postgresql://postgres:lenovo@localhost:5432/sade_db"
    
    # Replace the database name at the end with "geo-mdr"
    base_url, _ = db_url.rsplit('/', 1)
    geo_url = f"{base_url}/geo-mdr"
    
    if geo_url.startswith("postgres://"):
        geo_url = geo_url.replace("postgres://", "postgresql://", 1)
        
    return create_engine(geo_url, pool_size=5, max_overflow=10)

geo_engine = get_geo_mdr_engine()


# Crear tabla de favoritos en el inicio
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
        # Populate defaults for existing rows if they are null
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
        
        # Manzanas Atípicas Workflow & Notas DDL
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
            CREATE TABLE IF NOT EXISTS public.manzanas_atipicas_notas (
                id SERIAL PRIMARY KEY,
                seccion VARCHAR(50) NOT NULL,
                manzana VARCHAR(50) NOT NULL,
                username VARCHAR(100) NOT NULL,
                nota TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Manzanas LFI Workflow & Notas DDL
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
        
        # dynamic roles DDL
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
        # dynamic families DDL
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.cfg_tramites_familias (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) UNIQUE NOT NULL,
                tratas JSONB NOT NULL DEFAULT '[]'::jsonb
            )
        """))
        # reportes_rrhh DDL
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.reporte_rrhh (
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
            import json
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
            import json
            default_roles = [
                ("administrador", json.dumps({"admin": True, "dgroc": True, "dgiur": True, "family": True, "seguimiento": True, "cierre": True, "sla": True, "subsanaciones": True, "buscador": True, "favoritos": True, "favoritos-seguimiento": True, "analytics_estadistica": True, "analytics_datasets": True, "asignados-mi": True, "buzones_analisis": True, "productividad_analistas": True, "secgdu": True, "ciudad_3d": True, "lfi_dibujar": True, "lfi_revisar": True})),
                ("admin", json.dumps({"admin": True, "dgroc": True, "dgiur": True, "family": True, "seguimiento": True, "cierre": True, "sla": True, "subsanaciones": True, "buscador": True, "favoritos": True, "favoritos-seguimiento": True, "analytics_estadistica": True, "analytics_datasets": True, "asignados-mi": True, "buzones_analisis": True, "productividad_analistas": True, "secgdu": True, "ciudad_3d": True, "lfi_dibujar": True, "lfi_revisar": True})),
                ("seguimiento", json.dumps({"admin": False, "dgroc": True, "dgiur": True, "family": True, "seguimiento": True, "cierre": True, "sla": True, "subsanaciones": True, "buscador": True, "favoritos": True, "favoritos-seguimiento": True, "analytics_estadistica": True, "analytics_datasets": True, "asignados-mi": True, "buzones_analisis": True, "productividad_analistas": False, "secgdu": True, "ciudad_3d": True, "lfi_dibujar": False, "lfi_revisar": False})),
                ("usuario", json.dumps({"admin": False, "dgroc": True, "dgiur": True, "family": True, "seguimiento": False, "cierre": False, "sla": False, "subsanaciones": False, "buscador": True, "favoritos": True, "favoritos-seguimiento": True, "analytics_estadistica": True, "analytics_datasets": True, "asignados-mi": True, "buzones_analisis": True, "productividad_analistas": False, "secgdu": False, "ciudad_3d": False, "lfi_dibujar": False, "lfi_revisar": False}))
            ]
            for r_name, r_perms in default_roles:
                conn.execute(text("INSERT INTO auth_roles (role_name, permissions) VALUES (:n, :p)"), {"n": r_name, "p": r_perms})
        else:
            # Upgrade existing DB roles if they don't have favoritos-seguimiento, analytics, or asignados-mi
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
            # Migrations for lfi_dibujar
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
            # Migrations for lfi_revisar
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
            # User overrides synchronization
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
            
            # Synchronize missing permission keys from roles to user overrides
            roles = conn.execute(text("SELECT role_name, permissions FROM auth_roles")).fetchall()
            roles_map = {r[0]: r[1] for r in roles}
            users = conn.execute(text("SELECT username, role, permissions FROM auth_users WHERE permissions IS NOT NULL")).fetchall()
            for user in users:
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
except Exception as e:
    print(f"Error creando tablas de favoritos/notas/roles: {e}")

# Utilidades de Seguridad
def verify_password(plain_password, password_hash):
    return bcrypt.checkpw(plain_password.encode('utf-8'), password_hash.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_resolved_permissions(conn, username: str, role_name: str) -> dict:
    # 1. Custom user permissions override
    user_perm = conn.execute(text("SELECT permissions FROM auth_users WHERE username = :u"), {"u": username}).scalar()
    
    r_lower = (role_name or "").lower()
    
    resolved = None
    if user_perm is not None:
        resolved = dict(user_perm)
    else:
        # 2. Role permissions
        if role_name:
            role_perm = conn.execute(text("SELECT permissions FROM auth_roles WHERE role_name = :r"), {"r": role_name}).scalar()
            if role_perm is not None:
                resolved = dict(role_perm)

    if resolved is None:
        # 3. Hardcoded Fallbacks
        if r_lower in ['admin', 'administrador']:
            resolved = {"admin": True, "dgroc": True, "dgiur": True, "family": True, "seguimiento": True, "cierre": True, "sla": True, "subsanaciones": True, "pendientes_asociacion": True, "buscador": True, "favoritos": True, "favoritos-seguimiento": True, "analytics_estadistica": True, "analytics_datasets": True, "asignados-mi": True, "productividad_analistas": True, "reportes_rrhh": True, "carga_reportes_rrhh": True}
        elif r_lower == 'seguimiento':
            resolved = {"admin": False, "dgroc": True, "dgiur": True, "family": True, "seguimiento": True, "cierre": True, "sla": True, "subsanaciones": True, "pendientes_asociacion": True, "buscador": True, "favoritos": True, "favoritos-seguimiento": True, "analytics_estadistica": True, "analytics_datasets": True, "asignados-mi": True, "productividad_analistas": False, "reportes_rrhh": False, "carga_reportes_rrhh": False}
        else:
            resolved = {"admin": False, "dgroc": True, "dgiur": True, "family": True, "seguimiento": False, "cierre": False, "sla": False, "subsanaciones": False, "pendientes_asociacion": False, "buscador": True, "favoritos": True, "favoritos-seguimiento": True, "analytics_estadistica": True, "analytics_datasets": True, "asignados-mi": True, "productividad_analistas": False, "reportes_rrhh": False, "carga_reportes_rrhh": False}
            
    # Add fallback defaults if not present
    if "analytics_estadistica" not in resolved:
        resolved["analytics_estadistica"] = True
    if "analytics_datasets" not in resolved:
        resolved["analytics_datasets"] = True
    if "asignados-mi" not in resolved:
        resolved["asignados-mi"] = True
    if "productividad_analistas" not in resolved:
        resolved["productividad_analistas"] = False
    if "reportes_rrhh" not in resolved:
        resolved["reportes_rrhh"] = False
    if "carga_reportes_rrhh" not in resolved:
        resolved["carga_reportes_rrhh"] = False

    # Force full admin permissions if they have the admin role
    if r_lower in ['admin', 'administrador']:
        resolved["admin"] = True
        resolved["pendientes_asociacion"] = True
        for k in ["dgroc", "dgiur", "family", "seguimiento", "cierre", "sla", "subsanaciones", "buscador", "favoritos", "favoritos-seguimiento", "analytics_estadistica", "analytics_datasets", "asignados-mi", "productividad_analistas", "reportes_rrhh", "carga_reportes_rrhh"]:
            resolved[k] = True
            
    return resolved

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el acceso",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        with engine.connect() as conn:
            user_row = conn.execute(text("""
                SELECT username, role, full_name, sector 
                FROM auth_users WHERE username = :u
            """), {"u": username}).fetchone()
            if not user_row:
                raise credentials_exception
            
            resolved_perms = get_resolved_permissions(conn, user_row[0], user_row[1])
            return User(
                username=user_row[0],
                role=user_row[1],
                full_name=user_row[2],
                sector=user_row[3],
                permissions=resolved_perms
            )
    except JWTError:
        raise credentials_exception

# --- Endpoints de Autenticación ---

@app.post("/api/auth/login", response_model=Token)
async def login(from_data: OAuth2PasswordRequestForm = Depends()):
    # Obtenemos la IP del cliente (simplificado para FastAPI)
    client_ip = "0.0.0.0" # En producción se puede obtener de request.client.host
    
    try:
        with engine.begin() as conn:
            query = text("""
                SELECT username, password_hash, role, full_name, sector, needs_password_change 
                FROM auth_users WHERE username = :u
            """)
            result = conn.execute(query, {"u": from_data.username}).fetchone()
            
            if not result or not verify_password(from_data.password, result[1]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario o contraseña incorrectos",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Registrar log de acceso
            conn.execute(
                text("INSERT INTO user_access_logs (username, ip_address) VALUES (:u, :ip)"),
                {"u": result[0], "ip": client_ip}
            )
            
            access_token = create_access_token(data={
                "sub": result[0], 
                "role": result[2],
                "name": result[3]
            })
            
            resolved_perms = get_resolved_permissions(conn, result[0], result[2])
            
            return {
                "access_token": access_token, 
                "token_type": "bearer", 
                "username": result[0], 
                "role": result[2],
                "full_name": result[3] or result[0],
                "sector": result[4] or "General",
                "needs_password_change": result[5],
                "permissions": resolved_perms
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.post("/api/auth/change-password")
async def change_password(data: PasswordChange, current_user: User = Depends(get_current_user)):
    try:
        hashed = bcrypt.hashpw(data.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE auth_users SET password_hash = :p, needs_password_change = FALSE WHERE username = :u"),
                {"p": hashed, "u": current_user.username}
            )
            return {"status": "ok", "message": "Contraseña actualizada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/api/health")
async def health_check():
    db_var = "None"
    if os.getenv("DATABASE_URL"): db_var = "DATABASE_URL"
    elif os.getenv("DATABASE_URL_PUBLIC"): db_var = "DATABASE_URL_PUBLIC"
    elif os.getenv("DATABASE_URL_LOCAL"): db_var = "DATABASE_URL_LOCAL"
    
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_url = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_PUBLIC") or os.getenv("DATABASE_URL_LOCAL") or "sade_db"
            return {
                "status": "online",
                "database": "connected",
                "detected_var": db_var,
                "db_name": db_url.split('/')[-1].split('?')[0]
            }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e),
            "detected_var": db_var
        }

@app.get("/api/admin/users")
async def list_users(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, username, role, full_name, sector, email, needs_password_change, created_at, permissions 
                FROM auth_users ORDER BY username
            """))
            return [dict(r._mapping) for r in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/admin/users/{username}")
async def update_user(username: str, data: UserUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        updates = []
        params = {"u": username}
        
        if data.full_name is not None:
            updates.append("full_name = :fn")
            params["fn"] = data.full_name
        if data.role is not None:
            updates.append("role = :r")
            params["r"] = data.role
        if data.sector is not None:
            updates.append("sector = :s")
            params["s"] = data.sector
        if data.email is not None:
            updates.append("email = :e")
            params["e"] = data.email
        if data.password:
            updates.append("password_hash = :p")
            params["p"] = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            updates.append("needs_password_change = TRUE")
            
        if "permissions" in data.model_fields_set:
            import json
            updates.append("permissions = :p_override")
            params["p_override"] = json.dumps(data.permissions) if data.permissions is not None else None

        if not updates:
            return {"status": "ok", "message": "Nada que actualizar"}

        sql = f"UPDATE auth_users SET {', '.join(updates)} WHERE username = :u"
        with engine.begin() as conn:
            conn.execute(text(sql), params)
            return {"status": "ok", "message": "Usuario actualizado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

@app.post("/api/admin/users")
async def create_user(user_data: UserCreate, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        hashed = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        with engine.connect() as conn:
            # Intentar insertar con el nombre nuevo, si falla probamos con el viejo
            try:
                conn.execute(
                    text("INSERT INTO auth_users (username, password_hash, role) VALUES (:u, :p, :r)"),
                    {"u": user_data.username, "p": hashed, "r": user_data.role}
                )
            except Exception:
                conn.execute(
                    text("INSERT INTO auth_users (username, password_hash, role) VALUES (:u, :p, :r)"),
                    {"u": user_data.username, "p": hashed, "r": user_data.role}
                )
            conn.commit()
            return {"status": "ok", "message": f"Usuario {user_data.username} creado"}
    except Exception as e:
        logger.error(f"Error creando usuario: {e}")
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@app.delete("/api/admin/users/{username}")
async def delete_user(username: str, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    if username == current_user.username:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM auth_users WHERE username = :u"), {"u": username})
            return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints de Roles (Admin) ---

@app.get("/api/admin/roles")
async def list_roles(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT role_name, permissions FROM auth_roles ORDER BY role_name"))
            return [dict(r._mapping) for r in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/roles")
async def create_role(role_data: RoleCreate, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    r_name = role_data.role_name.strip().lower()
    if not r_name:
        raise HTTPException(status_code=400, detail="El nombre del rol no puede estar vacío")
    try:
        import json
        default_perms = json.dumps({
            "admin": False,
            "dgroc": True,
            "dgiur": True,
            "family": True,
            "seguimiento": False,
            "cierre": False,
            "sla": False,
            "subsanaciones": False,
            "buscador": True,
            "favoritos": True
        })
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO auth_roles (role_name, permissions) VALUES (:n, :p) ON CONFLICT DO NOTHING"),
                {"n": r_name, "p": default_perms}
            )
            return {"status": "ok", "message": f"Rol {r_name} creado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/admin/roles/{role_name}")
async def update_role(role_name: str, role_update: RoleUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        import json
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE auth_roles SET permissions = :p WHERE role_name = :n"),
                {"p": json.dumps(role_update.permissions), "n": role_name}
            )
            return {"status": "ok", "message": "Permisos del rol actualizados"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/roles/{role_name}")
async def delete_role(role_name: str, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    if role_name.lower() in ['admin', 'administrador', 'seguimiento', 'usuario', 'user']:
        raise HTTPException(status_code=400, detail="No se pueden eliminar los roles integrados del sistema")
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM auth_roles WHERE role_name = :n"), {"n": role_name})
            return {"status": "ok", "message": f"Rol {role_name} eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints de Familias de Trámites (Admin) ---

class FamiliaUpdate(BaseModel):
    tratas: List[str]

class FamiliaCreate(BaseModel):
    nombre: str
    tratas: List[str]

@app.get("/api/admin/familias")
async def list_admin_familias(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, nombre, tratas FROM public.cfg_tramites_familias ORDER BY id"))
            return [dict(r._mapping) for r in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/familias")
async def create_admin_familia(data: FamiliaCreate, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    name_clean = data.nombre.strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="El nombre de la familia no puede estar vacío")
    try:
        import json
        clean_tratas = [t.strip().upper() for t in data.tratas if t.strip()]
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO public.cfg_tramites_familias (nombre, tratas) VALUES (:n, :t)"),
                {"n": name_clean, "t": json.dumps(clean_tratas)}
            )
            return {"status": "ok", "message": f"Familia {name_clean} creada con éxito"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al crear familia (tal vez ya existe): {str(e)}")

@app.put("/api/admin/familias/{nombre}")
async def update_admin_familia(nombre: str, data: FamiliaUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        import json
        clean_tratas = [t.strip().upper() for t in data.tratas if t.strip()]
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE public.cfg_tramites_familias SET tratas = :t WHERE nombre = :n"),
                {"t": json.dumps(clean_tratas), "n": nombre}
            )
            return {"status": "ok", "message": f"Familia {nombre} actualizada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/familias/{nombre}")
async def delete_admin_familia(nombre: str, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM public.cfg_tramites_familias WHERE nombre = :n"),
                {"n": nombre}
            )
            return {"status": "ok", "message": f"Familia {nombre} eliminada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/buzones-analisis/catalogo")
async def get_buzones_catalogo(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    requested_mailboxes = [
        'ARCHIVODGTAL', 'DGIUR-PREARCHIVO', 'DGIUR-SGUI', 'DGROC-ANTECEDENTESRLM', 'DGROC-APTOSGRYCO', 
        'DGROC-ARCHIVO', 'DGROC-ARI', 'DGROC-CIC', 'DGROC-CONTABLE', 'DGROC-COPIAPLANO', 
        'DGROC-DCATAT', 'DGROC-DCATDES', 'DGROC-DCATPOL', 'DGROC-DCATRUD', 'DGROC-DCATTIT', 
        'DGROC-DCG', 'DGROC-DCIDITI', 'DGROC-DCOBAAYFO', 'DGROC-DCOBLEG', 'DGROC-DCOBREG', 
        'DGROC-DCOBREGD', 'DGROC-DESCARGOS', 'DGROC-DGROCARI', 'DGROC-DGROCDES', 'DGROC-DGROCRRHH', 
        'DGROC-DTACONT', 'DGROC-DTADES', 'DGROC-DTARPS', 'DGROC-ELEVADORES', 'DGROC-ESPERAINSTALACIONES', 
        'DGROC-FICHA_PARCELARIA', 'DGROC-GO', 'DGROC-LEGAJOS', 'DGROC-LEGAJOSAUTOMAT', 'DGROC-LEY104', 
        'DGROC-MESADES', 'DGROC-MESAMIDI', 'DGROC-MESAMIDINST', 'DGROC-MESAMIDINSTINCENDIO', 
        'DGROC-MESAMIPVO', 'DGROC-OBRASADMIN', 'DGROC-OBRASENCURSO', 'DGROC-OBRASTECNICA', 'DGROC-OBSINCENDIO', 
        'DGROC-OBSOBRAPREARCHIVO', 'DGROC-OBSPREARCHAYFO', 'DGROC-OBSREGISTRO', 'DGROC-PENDIENTESDEPAGO', 
        'DGROC-RECHAZADOSLEGAJOS', 'DGROC-REVISIONCONTABLE', 'DGROC-SEDR', 'DGROC-SEDRI', 'DGROC-SGUI', 
        'DGROC-TERMICAS', 'DGSOCAI-ARCHIVO', 'MGEYA-ARCHIVO', 'MGEYA-DCG', 'PG-ARCHIVO', 
        'SECGDU-ARCHIVODESPACHO', 'SECLYT-ARCHIVO', 'SSGDU-ARCHIVODESPACHO', 'SSGU-ARCHIVODESPACHO'
    ]
    return sorted(requested_mailboxes)

@app.get("/api/admin/buzones-analisis/accesos")
async def list_buzones_accesos(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, tipo_sujeto, nombre_sujeto, buzones FROM public.cfg_buzones_analisis_acceso ORDER BY tipo_sujeto, nombre_sujeto"))
            return [dict(r._mapping) for r in result.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class BuzonAccesoUpdate(BaseModel):
    tipo_sujeto: str
    nombre_sujeto: str
    buzones: List[str]

@app.put("/api/admin/buzones-analisis/accesos")
async def save_buzon_acceso(data: BuzonAccesoUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM public.cfg_buzones_analisis_acceso WHERE nombre_sujeto = :name"), {"name": data.nombre_sujeto})
            conn.execute(text("""
                INSERT INTO public.cfg_buzones_analisis_acceso (tipo_sujeto, nombre_sujeto, buzones)
                VALUES (:t, :n, :b)
            """), {"t": data.tipo_sujeto, "n": data.nombre_sujeto, "b": data.buzones})
            return {"status": "ok", "message": "Acceso a buzones guardado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/buzones-analisis/accesos/{nombre_sujeto}")
async def delete_buzon_acceso(nombre_sujeto: str, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM public.cfg_buzones_analisis_acceso WHERE nombre_sujeto = :name"), {"name": nombre_sujeto})
            return {"status": "ok", "message": "Acceso personalizado eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def format_capital(val):
    if not val:
        return ""
    val = str(val).strip()
    if not val:
        return ""
    return val[0].upper() + val[1:].lower()

class AddAnalystRequest(BaseModel):
    usuario: str

@app.get("/api/admin/analistas")
async def list_admin_analistas(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                WITH unnested AS (
                    SELECT DISTINCT TRIM(gerencia) as gerencia, TRIM(unnest(analistas_oficiales)) as usuario_raw
                    FROM cfg_gestion_metas
                    WHERE analistas_oficiales IS NOT NULL
                )
                SELECT u.gerencia, u.usuario_raw,
                       du.usuario, du.apellido, du.nombre, du.mail, du.ocupacion, du.numero_cuit
                FROM unnested u
                LEFT JOIN public.datos_usuario du ON TRIM(UPPER(u.usuario_raw)) = TRIM(UPPER(du.usuario))
                ORDER BY u.gerencia, du.apellido, du.nombre
            """))
            
            # Get list of unique gerencias from the table to ensure we return even empty ones
            g_result = conn.execute(text("SELECT DISTINCT TRIM(gerencia) as gerencia FROM cfg_gestion_metas ORDER BY 1"))
            gerencias_map = {row[0]: [] for row in g_result}
            
            for row in result:
                g = row[0]
                raw_user = row[1]
                db_user = row[2]
                
                user_code = (db_user or raw_user).strip().upper()
                apellido = format_capital(row[3])
                nombre = format_capital(row[4])
                mail = format_capital(row[5])
                ocupacion = format_capital(row[6])
                cuit = format_capital(row[7])
                
                if g in gerencias_map:
                    gerencias_map[g].append({
                        "usuario": user_code,
                        "apellido": apellido,
                        "nombre": nombre,
                        "mail": mail,
                        "ocupacion": ocupacion,
                        "numero_cuit": cuit
                    })
            
            return [{"gerencia": k, "analistas": v} for k, v in gerencias_map.items()]
    except Exception as e:
        logger.error(f"Error listing admin analysts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/analistas/{gerencia}")
async def add_admin_analista(gerencia: str, req: AddAnalystRequest, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    
    usuario_to_add = req.usuario.strip().upper()
    if not usuario_to_add:
        raise HTTPException(status_code=400, detail="Debe ingresar un usuario válido.")
        
    try:
        with engine.begin() as conn:
            user_exists = conn.execute(text("SELECT 1 FROM public.datos_usuario WHERE TRIM(UPPER(usuario)) = :u"), {"u": usuario_to_add}).fetchone()
            if not user_exists:
                raise HTTPException(status_code=404, detail=f"El usuario '{usuario_to_add}' no existe en la base de datos.")
                
            rows = conn.execute(text("SELECT id, analistas_oficiales FROM cfg_gestion_metas WHERE TRIM(gerencia) = :g"), {"g": gerencia.strip()}).fetchall()
            for r in rows:
                current_analysts = r[1] or []
                current_analysts_upper = [a.strip().upper() for a in current_analysts if a]
                if usuario_to_add not in current_analysts_upper:
                    new_analysts = current_analysts + [usuario_to_add]
                    conn.execute(text("UPDATE cfg_gestion_metas SET analistas_oficiales = :a WHERE id = :id"), {"a": new_analysts, "id": r[0]})
            
            return {"status": "ok", "message": f"Usuario {usuario_to_add} agregado a {gerencia}."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding analyst: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/analistas/{gerencia}/{usuario}")
async def delete_admin_analista(gerencia: str, usuario: str, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    
    usuario_to_remove = usuario.strip().upper()
    try:
        with engine.begin() as conn:
            rows = conn.execute(text("SELECT id, analistas_oficiales FROM cfg_gestion_metas WHERE TRIM(gerencia) = :g"), {"g": gerencia.strip()}).fetchall()
            for r in rows:
                current_analysts = r[1] or []
                new_analysts = [a for a in current_analysts if a and a.strip().upper() != usuario_to_remove]
                conn.execute(text("UPDATE cfg_gestion_metas SET analistas_oficiales = :a WHERE id = :id"), {"a": new_analysts, "id": r[0]})
            
            return {"status": "ok", "message": f"Usuario {usuario_to_remove} eliminado de {gerencia}."}
    except Exception as e:
        logger.error(f"Error deleting analyst: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/metas")
async def list_metas(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT c.id, c.direccion, c.gerencia, c.trata_reporte, c.tratas_incluidas, c.buzones_ingreso, 
                       c.analistas_oficiales, c.acronimos_egreso, c.activo, c.firmantes_egreso, 
                       c.buzones_ingreso_intervenciones, c.descripciones_validas,
                       COALESCE(c.descripcion_trata, (SELECT descripcion_trata FROM vw_expedientes_maestro WHERE trata = c.trata_reporte LIMIT 1)) as descripcion_trata
                FROM cfg_gestion_metas c
                ORDER BY c.direccion, c.gerencia, c.trata_reporte
            """))
            metas = []
            for row in result:
                d = dict(row._mapping)
                if not d.get("direccion"):
                    d["direccion"] = "DGROC" # fallback
                for array_field in ['tratas_incluidas', 'buzones_ingreso', 'analistas_oficiales', 
                                    'acronimos_egreso', 'firmantes_egreso', 
                                    'buzones_ingreso_intervenciones', 'descripciones_validas']:
                    if d.get(array_field) is None:
                        d[array_field] = []
                metas.append(d)
            return metas
    except Exception as e:
        logger.error(f"Error listing metas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/metas")
async def create_meta(data: MetaCreateRequest, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.begin() as conn:
            exists = conn.execute(text("SELECT 1 FROM cfg_gestion_metas WHERE TRIM(UPPER(gerencia)) = :g AND TRIM(UPPER(trata_reporte)) = :t"), 
                                  {"g": data.gerencia.strip().upper(), "t": data.trata_reporte.strip().upper()}).fetchone()
            if exists:
                raise HTTPException(status_code=400, detail="Esta trata ya está configurada para esa gerencia.")
                
            conn.execute(
                text("""
                    INSERT INTO cfg_gestion_metas (
                        direccion, gerencia, trata_reporte, tratas_incluidas, buzones_ingreso,
                        analistas_oficiales, acronimos_egreso, activo, firmantes_egreso,
                        buzones_ingreso_intervenciones, descripciones_validas, descripcion_trata
                    ) VALUES (
                        :direccion, :gerencia, :trata_reporte, :tratas_incluidas, :buzones_ingreso,
                        :analistas_oficiales, :acronimos_egreso, :activo, :firmantes_egreso,
                        :buzones_ingreso_intervenciones, :descripciones_validas, :descripcion_trata
                    )
                """),
                {
                    "direccion": data.direccion.strip().upper(),
                    "gerencia": data.gerencia.strip().lower(),
                    "trata_reporte": data.trata_reporte.strip().upper(),
                    "tratas_incluidas": data.tratas_incluidas,
                    "buzones_ingreso": data.buzones_ingreso,
                    "analistas_oficiales": data.analistas_oficiales,
                    "acronimos_egreso": data.acronimos_egreso,
                    "activo": data.activo,
                    "firmantes_egreso": data.firmantes_egreso if data.firmantes_egreso else None,
                    "buzones_ingreso_intervenciones": data.buzones_ingreso_intervenciones if data.buzones_ingreso_intervenciones else None,
                    "descripciones_validas": data.descripciones_validas if data.descripciones_validas else None,
                    "descripcion_trata": data.descripcion_trata
                }
            )
            return {"status": "ok", "message": "Configuración de meta creada"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating meta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/admin/metas/{meta_id}")
async def update_meta(meta_id: int, data: MetaUpdateRequest, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE cfg_gestion_metas 
                    SET direccion = :direccion,
                        gerencia = :gerencia,
                        trata_reporte = :trata_reporte,
                        tratas_incluidas = :tratas_incluidas,
                        buzones_ingreso = :buzones_ingreso,
                        analistas_oficiales = :analistas_oficiales,
                        acronimos_egreso = :acronimos_egreso,
                        activo = :activo,
                        firmantes_egreso = :firmantes_egreso,
                        buzones_ingreso_intervenciones = :buzones_ingreso_intervenciones,
                        descripciones_validas = :descripciones_validas,
                        descripcion_trata = :descripcion_trata
                    WHERE id = :meta_id
                """),
                {
                    "direccion": data.direccion.strip().upper() if data.direccion else "DGROC",
                    "gerencia": data.gerencia.strip().lower() if data.gerencia else "catastro",
                    "trata_reporte": data.trata_reporte.strip().upper() if data.trata_reporte else "",
                    "tratas_incluidas": data.tratas_incluidas,
                    "buzones_ingreso": data.buzones_ingreso,
                    "analistas_oficiales": data.analistas_oficiales,
                    "acronimos_egreso": data.acronimos_egreso,
                    "activo": data.activo,
                    "firmantes_egreso": data.firmantes_egreso if data.firmantes_egreso else None,
                    "buzones_ingreso_intervenciones": data.buzones_ingreso_intervenciones if data.buzones_ingreso_intervenciones else None,
                    "descripciones_validas": data.descripciones_validas if data.descripciones_validas else None,
                    "descripcion_trata": data.descripcion_trata,
                    "meta_id": meta_id
                }
            )
            return {"status": "ok", "message": "Configuración de meta actualizada"}
    except Exception as e:
        logger.error(f"Error updating meta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/metas/{meta_id}")
async def delete_meta(meta_id: int, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM cfg_gestion_metas WHERE id = :id"), {"id": meta_id})
            return {"status": "ok", "message": "Configuración de meta eliminada"}
    except Exception as e:
        logger.error(f"Error deleting meta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints de RRHH (Protegidos por permisos) ---

@app.get("/api/rrhh/reporte")
async def get_rrhh_reporte(month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"), current_user: User = Depends(get_current_user)):
    if not (current_user.permissions.get("reportes_rrhh") or current_user.role.lower() in ['admin', 'administrador']):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        with engine.connect() as conn:
            # If month is not provided, find the max date in the table
            if not month:
                max_date = conn.execute(text("SELECT MAX(fecha) FROM public.reporte_rrhh")).scalar()
                if max_date:
                    month = max_date.strftime("%Y-%m-%d")[:7]
                else:
                    d = datetime.now()
                    month = f"{d.year}-{d.month:02d}"

            year_str, month_str = month.split("-")
            y_val = int(year_str)
            m_val = int(month_str)

            # Query all records for this month with SADE user matching
            sql = text("""
                SELECT r.cuil, r.nombreyapellido, r.fecha, r.feriado, r.convocado,
                       r.hora_ingreso, r.hora_salida, r.cant_horas, r.estado_incidencia, r.estado,
                       du.usuario, du.apellido, du.nombre,
                       COALESCE((SELECT MIN(c.gerencia) FROM cfg_gestion_metas c WHERE du.usuario = ANY(c.analistas_oficiales)), 'OTROS') as gerencia
                FROM public.reporte_rrhh r
                LEFT JOIN public.datos_usuario du ON REPLACE(du.numero_cuit, '-', '') = REPLACE(r.cuil, '-', '')
                WHERE EXTRACT(YEAR FROM r.fecha) = :year AND EXTRACT(MONTH FROM r.fecha) = :month
                ORDER BY r.fecha, r.nombreyapellido
            """)
            result = conn.execute(sql, {"year": y_val, "month": m_val}).fetchall()

            if not result:
                return {"month": month, "sectores": {}, "message": "No hay datos para este mes"}

            # Process records
            sectores = {}
            for r in result:
                sec = r[13].upper() # gerencia
                cuil = r[0]
                nombre_comp = r[1]
                fecha = r[2].strftime("%Y-%m-%d") if r[2] else None
                feriado = (r[3] or "").strip().upper() == "SI"
                convocado = (r[4] or "").strip().upper() == "SI"
                
                h_ingreso = r[5] # time object
                h_salida = r[6] # time object
                c_horas = r[7] # time object
                incidencia = r[8] or ""
                est = r[9] or ""

                if sec not in sectores:
                    sectores[sec] = {
                        "gerencia": sec,
                        "earliest_ingreso": None,
                        "latest_salida": None,
                        "dias_laborados": 0,
                        "dias_presentes_total": 0,
                        "dias_a_tiempo": 0,
                        "agentes": {},
                        "hourly_coverage": {f"{h:02d}:00": 0 for h in range(7, 20)}
                    }

                s_data = sectores[sec]

                # Analista key
                agente_key = cuil
                if agente_key not in s_data["agentes"]:
                    s_data["agentes"][agente_key] = {
                        "cuil": cuil,
                        "nombre": nombre_comp,
                        "usuario": r[10] or "N/A",
                        "presentes": 0,
                        "ausentes": 0,
                        "tardes": 0,
                        "total_convocado": 0,
                        "asistencia_pct": 0,
                        "puntualidad_pct": 0
                    }
                ag_data = s_data["agentes"][agente_key]

                # Presence / attendance check
                is_present = "PRESENTE" in est.upper() or h_ingreso is not None
                if convocado:
                    ag_data["total_convocado"] += 1
                    if is_present:
                        ag_data["presentes"] += 1
                        s_data["dias_presentes_total"] += 1
                    else:
                        ag_data["ausentes"] += 1

                # Daily check-in / check-out bounds
                if h_ingreso:
                    h_str = h_ingreso.strftime("%H:%M")
                    if not s_data["earliest_ingreso"] or h_str < s_data["earliest_ingreso"]:
                        s_data["earliest_ingreso"] = h_str
                    
                    # Hourly coverage matrix (determinar turnos)
                    # Check which hours this agent was present
                    start_h = h_ingreso.hour
                    end_h = h_salida.hour if h_salida else 18
                    for hour in range(start_h, min(end_h + 1, 20)):
                        h_key = f"{hour:02d}:00"
                        if h_key in s_data["hourly_coverage"]:
                            s_data["hourly_coverage"][h_key] += 1
                            
                    # Check punctual check-in (e.g. before 09:30 AM)
                    if h_ingreso.hour < 9 or (h_ingreso.hour == 9 and h_ingreso.minute <= 30):
                        s_data["dias_a_tiempo"] += 1
                        if convocado:
                            ag_data["tardes"] = ag_data.get("tardes", 0)
                    else:
                        if convocado:
                            ag_data["tardes"] = ag_data.get("tardes", 0) + 1

                if h_salida:
                    s_str = h_salida.strftime("%H:%M")
                    if not s_data["latest_salida"] or s_str > s_data["latest_salida"]:
                        s_data["latest_salida"] = s_str

            # Finalize averages & percents
            for sec, s_data in sectores.items():
                # Overall sector stats
                total_agentes = len(s_data["agentes"])
                for ag_key, ag_data in s_data["agentes"].items():
                    tot = ag_data["total_convocado"]
                    if tot > 0:
                        ag_data["asistencia_pct"] = round((ag_data["presentes"] / tot) * 100)
                        ag_data["puntualidad_pct"] = round(((ag_data["presentes"] - ag_data["tardes"]) / ag_data["presentes"]) * 100) if ag_data["presentes"] > 0 else 0
                    else:
                        ag_data["asistencia_pct"] = 100
                        ag_data["puntualidad_pct"] = 100

                # Convert agents dict to list
                s_data["agentes_list"] = list(s_data["agentes"].values())
                del s_data["agentes"]

            return {"sectores": sectores}
    except Exception as e:
        logger.error(f"Error fetching RRHH metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rrhh/reporte/detalle-agente")
async def get_rrhh_agente_detalle(cuil: str = Query(...), month: str = Query(..., regex=r"^\d{4}-\d{2}$"), current_user: User = Depends(get_current_user)):
    if not (current_user.permissions.get("reportes_rrhh") or current_user.role.lower() in ['admin', 'administrador']):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        year_str, month_str = month.split("-")
        y_val = int(year_str)
        m_val = int(month_str)

        with engine.connect() as conn:
            sql = text("""
                SELECT fecha, feriado, convocado, hora_ingreso, hora_salida, cant_horas, estado_incidencia, estado
                FROM public.reporte_rrhh
                WHERE REPLACE(cuil, '-', '') = REPLACE(:cuil, '-', '')
                  AND EXTRACT(YEAR FROM fecha) = :year
                  AND EXTRACT(MONTH FROM fecha) = :month
                ORDER BY fecha
            """)
            result = conn.execute(sql, {"cuil": cuil, "year": y_val, "month": m_val}).fetchall()
            
            rows = []
            for r in result:
                rows.append({
                    "fecha": r[0].strftime("%Y-%m-%d") if r[0] else "",
                    "feriado": r[1],
                    "convocado": r[2],
                    "hora_ingreso": r[3].strftime("%H:%M:%S") if r[3] else "",
                    "hora_salida": r[4].strftime("%H:%M:%S") if r[4] else "",
                    "cant_horas": r[5].strftime("%H:%M:%S") if r[5] else "",
                    "estado_incidencia": r[6] or "",
                    "estado": r[7] or ""
                })
            return rows
    except Exception as e:
        logger.error(f"Error fetching agent RRHH detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rrhh/upload")
async def upload_rrhh_excel(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if not (current_user.permissions.get("carga_reportes_rrhh") or current_user.role.lower() in ['admin', 'administrador']):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        # Read Excel using pandas
        df = pd.read_excel(file.file)
        
        # Check minimum columns count
        if len(df.columns) < 10:
            raise HTTPException(status_code=400, detail="El archivo Excel debe contener al menos 10 columnas correspondientes al formato requerido.")

        records_to_insert = []
        dates_present = set()

        for idx, row in df.iterrows():
            cuil_raw = str(row.iloc[0]).strip()
            # Skip header lookalikes or empty rows
            if not cuil_raw or cuil_raw.lower() in ['cuil', 'nan', 'none']:
                continue

            nombre = str(row.iloc[1]).strip()
            fecha_raw = row.iloc[2]
            feriado = str(row.iloc[3]).strip()
            convocado = str(row.iloc[4]).strip()
            
            h_ingreso_raw = row.iloc[5]
            h_salida_raw = row.iloc[6]
            c_horas_raw = row.iloc[7]
            
            incidencia = str(row.iloc[8]).strip() if pd.notna(row.iloc[8]) else ""
            estado = str(row.iloc[9]).strip() if pd.notna(row.iloc[9]) else ""

            # Parse date safely
            try:
                if isinstance(fecha_raw, str):
                    fecha = pd.to_datetime(fecha_raw).to_pydatetime()
                else:
                    fecha = pd.to_datetime(fecha_raw).to_pydatetime()
            except Exception:
                # Skip invalid date rows
                continue

            dates_present.add(fecha.date())

            # Parse times safely helper
            def parse_time(val):
                if pd.isna(val) or str(val).strip().lower() in ['nan', 'none', '']:
                    return None
                try:
                    if isinstance(val, datetime):
                        return val.time()
                    if isinstance(val, time):
                        return val
                    # String parse
                    t_str = str(val).strip()
                    # format H:M:S or H:M
                    parts = t_str.split(":")
                    if len(parts) >= 2:
                        h = int(parts[0])
                        m = int(parts[1])
                        s = int(parts[2]) if len(parts) > 2 else 0
                        return time(h, m, s)
                except Exception:
                    pass
                return None

            h_ingreso = parse_time(h_ingreso_raw)
            h_salida = parse_time(h_salida_raw)
            c_horas = parse_time(c_horas_raw)

            records_to_insert.append({
                "cuil": cuil_raw,
                "nombreyapellido": nombre,
                "fecha": fecha,
                "feriado": feriado,
                "convocado": convocado,
                "hora_ingreso": h_ingreso,
                "hora_salida": h_salida,
                "cant_horas": c_horas,
                "estado_incidencia": incidencia,
                "estado": estado
            })

        if not records_to_insert:
            raise HTTPException(status_code=400, detail="No se encontraron registros válidos para insertar.")

        # Clean and insert in database
        with engine.begin() as conn:
            # Delete existing data for the dates loaded in the file to avoid duplication
            min_date = min(dates_present)
            max_date = max(dates_present)
            conn.execute(
                text("DELETE FROM public.reporte_rrhh WHERE fecha >= :min_d AND fecha <= :max_d"),
                {"min_d": min_date, "max_d": max_date}
            )

            # Insert batch
            conn.execute(
                text("""
                    INSERT INTO public.reporte_rrhh (
                        cuil, nombreyapellido, fecha, feriado, convocado,
                        hora_ingreso, hora_salida, cant_horas, estado_incidencia, estado
                    ) VALUES (
                        :cuil, :nombreyapellido, :fecha, :feriado, :convocado,
                        :hora_ingreso, :hora_salida, :cant_horas, :estado_incidencia, :estado
                    )
                """),
                records_to_insert
            )

        return {
            "status": "ok", 
            "message": f"Se procesaron e ingresaron correctamente {len(records_to_insert)} registros correspondientes a las fechas {min_date} hasta {max_date}."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading RRHH excel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/sade_users/search")
async def search_sade_users(q: str = Query(..., min_length=2), current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        search_pattern = f"%{q}%"
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT DISTINCT usuario, apellido_nombre, codigo_sector_interno 
                    FROM datos_usuario 
                    WHERE usuario ILIKE :q OR apellido_nombre ILIKE :q 
                    ORDER BY apellido_nombre 
                    LIMIT 30
                """),
                {"q": search_pattern}
            )
            return [dict(r._mapping) for r in result]
    except Exception as e:
        logger.error(f"Error searching SADE users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints de Reportes (Protegidos) ---

def calculate_trata_expected_egresos(conn, gerencia_clean: str, trata: Optional[str] = None) -> int:
    try:
        interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"
        trata_filter = "TRUE"
        egr_trata_filter = "TRUE"
        if trata:
            trata_clean = trata.strip()
            if trata_clean == 'INTERVENCIONES':
                trata_filter = f"TRIM(trata) NOT IN (SELECT TRIM(unnest(tratas_incluidas)) FROM cfg_gestion_metas WHERE gerencia = '{gerencia_clean}')"
                egr_trata_filter = "TRIM(trata) = 'INTERVENCIONES'"
            else:
                trata_filter = f"TRIM(trata) = '{trata_clean}'"
                egr_trata_filter = f"TRIM(trata) = '{trata_clean}'"

        # Generate last 6 complete months in python
        now = datetime.now()
        curr_y, curr_m = now.year, now.month
        curr_m -= 1
        if curr_m == 0:
            curr_m = 12
            curr_y -= 1
            
        complete_months = []
        for _ in range(6):
            complete_months.append(f"{curr_y}-{str(curr_m).zfill(2)}")
            curr_m -= 1
            if curr_m == 0:
                curr_m = 12
                curr_y -= 1

        sql_hist = f"""
            WITH periodos(mes_label) AS (
                SELECT * FROM (VALUES {", ".join([f"('{m}')" for m in complete_months])}) as t(m)
            ),
            egr AS (
                SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                FROM (
                    SELECT fecha_egreso, trata FROM mv_{gerencia_clean}_gedos_egreso
                    UNION ALL
                    SELECT fecha_egreso, 'INTERVENCIONES' as trata FROM {interv_egr_table}
                ) t_egr
                WHERE {egr_trata_filter}
                GROUP BY 1
            ),
            egr_ne AS (
                SELECT to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_label, COUNT(*) as cant
                FROM mv_{gerencia_clean}_egresos_no_efectivos
                WHERE {trata_filter}
                GROUP BY 1
            )
            SELECT 
                p.mes_label,
                COALESCE(e.cant, 0) + COALESCE(ne.cant, 0) as egresos_totales
            FROM periodos p
            LEFT JOIN egr e ON e.mes_label = p.mes_label
            LEFT JOIN egr_ne ne ON ne.mes_label = p.mes_label
            ORDER BY p.mes_label ASC
        """
        result = conn.execute(text(sql_hist))
        hist_data = [dict(row._mapping) for row in result]
        if not hist_data:
            return 0
        sorted_vals = sorted([float(d['egresos_totales']) for d in hist_data])
        n = len(sorted_vals)
        mid = n // 2
        if n % 2 == 1:
            val = sorted_vals[mid]
        else:
            val = (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
        return round(val)
    except Exception as e:
        logger.error(f"Error calculate_trata_expected_egresos: {e}")
        return 0

@app.get("/api/reporte/{gerencia}/config/all")
async def get_gerencia_config(gerencia: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT trata_reporte, buzones_ingreso, analistas_oficiales, acronimos_egreso, buzones_ingreso_intervenciones
                FROM cfg_gestion_metas
                WHERE gerencia = :g
            """)
            result = conn.execute(query, {"g": gerencia_clean})
            config_data = {}
            for r in result.fetchall():
                config_data[r[0]] = {
                    "buzones_ingreso": r[1] or [],
                    "analistas_oficiales": r[2] or [],
                    "acronimos_egreso": r[3] or [],
                    "buzones_ingreso_intervenciones": r[4] or []
                }
            return config_data
    except Exception as e:
        logger.error(f"Error fetching gerencia config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/{gerencia}/consolidado")
def get_reporte_consolidado_gerencia(gerencia: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
        
    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
    
    trata_codes = list(TRAMITES_CONFIG[gerencia_clean].keys())
    
    # Obtener el último cuatrimestre completo + mes actual (5 meses total)
    now = datetime.now()
    months_list = []
    curr_y, curr_m = now.year, now.month
    
    for i in range(5):
        months_list.append(f"({curr_y}, {curr_m})")
        curr_m -= 1
        if curr_m == 0:
            curr_m = 12
            curr_y -= 1
            
    months_filter = ", ".join(months_list)
    
    try:
        with engine.connect() as conn:
            # Si la gerencia usa el nuevo esquema modular (vistas mv_gerencia_...)
            if gerencia_clean in ['instalaciones', 'morfologia', 'contable', 'etapa_proyecto', 'catastro', 'aph', 'usos', 'regularizacion', 'aviso_obra']:
                # Generamos los meses en formato 'YYYY-MM' para coincidir con mes_label
                modular_months = []
                m_y, m_m = now.year, now.month
                for _ in range(5):
                    modular_months.append(f"'{m_y}-{str(m_m).zfill(2)}'")
                    m_m -= 1
                    if m_m == 0: m_m = 12; m_y -= 1
                modular_filter = ", ".join(modular_months)

                # Definir tabla de egresos de intervenciones (Contable tiene nombre distinto)
                interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"

                sql = f"""
                    WITH periodos(mes_label) AS (
                        SELECT * FROM (VALUES {", ".join([f"({m})" for m in modular_months])}) as t(m)
                    ),
                    ing AS (
                        SELECT to_char(fecha_ingreso, 'YYYY-MM') as mes_label, 
                               CASE WHEN trata = ANY(:tratas_oficiales) THEN trata ELSE 'INTERVENCIONES' END as trata, 
                               COUNT(*) as cant
                        FROM mv_{gerencia_clean}_ingresos_eventos
                        GROUP BY 1, 2
                    ),
                    egr_ef AS (
                        -- Egresos Oficiales
                        SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, trata, COUNT(*) as cant
                        FROM mv_{gerencia_clean}_gedos_egreso
                        GROUP BY 1, 2
                        UNION ALL
                        -- Egresos Intervenciones
                        SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, 'INTERVENCIONES' as trata, COUNT(*) as cant
                        FROM {interv_egr_table}
                        GROUP BY 1, 2
                    ),
                    egr_ne AS (
                        SELECT to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_label, 
                               CASE WHEN trata = ANY(:tratas_oficiales) THEN trata ELSE 'INTERVENCIONES' END as trata, 
                               COUNT(*) as cant
                        FROM mv_{gerencia_clean}_egresos_no_efectivos
                        GROUP BY 1, 2
                    ),
                    stock_data AS (
                        -- Stock Histórico Oficial e Intervenciones
                        SELECT mes_label, 
                               CASE WHEN trata = ANY(:tratas_oficiales) THEN trata ELSE 'INTERVENCIONES' END as trata,
                               SUM(CASE WHEN categoria = 'STOCK_PROPIO' THEN cant_expedientes ELSE 0 END) as stock_propio,
                               SUM(CASE WHEN categoria = 'SUBSANACION' THEN cant_expedientes ELSE 0 END) as stock_subs
                        FROM mv_{gerencia_clean}_stock_historico
                        GROUP BY 1, 2
                    ),
                    config_order AS (
                        SELECT * FROM (VALUES {", ".join([f"('{c}', {i})" for i, c in enumerate(trata_codes)])}) as t(trata_code, ord)
                    ),
                    current_stock AS (
                        -- Foto de HOY para el mes actual
                        SELECT trata, COUNT(*) as cant FROM mv_{gerencia_clean}_stock_propio GROUP BY 1
                        UNION ALL
                        SELECT 'INTERVENCIONES' as trata, COUNT(*) as cant FROM mv_{gerencia_clean}_intervenciones_stock GROUP BY 1
                    ),
                    current_subs AS (
                        -- Foto de HOY para subsanaciones
                        SELECT trata, COUNT(*) as cant FROM mv_{gerencia_clean}_subsanaciones GROUP BY 1
                        UNION ALL
                        SELECT 'INTERVENCIONES' as trata, COUNT(*) as cant FROM mv_{gerencia_clean}_intervenciones_subs GROUP BY 1
                    )
                    SELECT 
                        et.trata as "COD TRATA", 
                        et.descripcion_trata as "DETALLE TRATA",
                        p.mes_label,
                        to_number(split_part(p.mes_label, '-', 1), '9999') as anio,
                        to_number(split_part(p.mes_label, '-', 2), '99') as mes,
                        COALESCE(i.cant, 0) as "ING",
                        COALESCE(ef.cant, 0) as "EGR_EF",
                        COALESCE(ne.cant, 0) as "EGR_NE",
                        -- Lógica de Stock Real Time
                        CASE 
                            WHEN p.mes_label = to_char(now(), 'YYYY-MM')
                            THEN COALESCE(MAX(cs.cant), 0) 
                            ELSE COALESCE(SUM(s.stock_propio), 0) 
                        END as "STOCK_PROPIO",
                        CASE 
                            WHEN p.mes_label = to_char(now(), 'YYYY-MM')
                            THEN COALESCE(MAX(csub.cant), 0) 
                            ELSE COALESCE(SUM(s.stock_subs), 0) 
                        END as "STOCK_SUBS"
                    FROM periodos p
                    CROSS JOIN (
                        SELECT DISTINCT 
                            t.trata, 
                            COALESCE(
                                (SELECT descripcion_trata FROM cfg_gestion_metas WHERE trata_reporte = t.trata AND gerencia = :g LIMIT 1),
                                (SELECT descripcion_trata FROM cfg_gestion_metas WHERE t.trata = ANY(tratas_incluidas) AND gerencia = :g LIMIT 1),
                                t.descripcion_trata
                            ) as descripcion_trata 
                        FROM vw_expedientes_maestro t
                        WHERE t.trata IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = :g)
                        UNION ALL
                        SELECT 'INTERVENCIONES', 'Intervenciones'
                    ) et
                    JOIN config_order o ON et.trata = o.trata_code
                    LEFT JOIN ing i ON i.mes_label = p.mes_label AND i.trata = et.trata
                    LEFT JOIN egr_ef ef ON ef.mes_label = p.mes_label AND ef.trata = et.trata
                    LEFT JOIN egr_ne ne ON ne.mes_label = p.mes_label AND ne.trata = et.trata
                    LEFT JOIN stock_data s ON s.mes_label = p.mes_label AND s.trata = et.trata
                    LEFT JOIN current_stock cs ON cs.trata = et.trata
                    LEFT JOIN current_subs csub ON csub.trata = et.trata
                    GROUP BY p.mes_label, 1, 2, 3, 4, o.ord, i.cant, ef.cant, ne.cant
                    ORDER BY o.ord, anio DESC, mes DESC
                """
                params = {"tratas_oficiales": trata_codes, "g": gerencia_clean}
            else:
                sql = f"""
                    WITH config_order AS (
                        SELECT * FROM (VALUES {", ".join([f"('{c}', {i})" for i, c in enumerate(trata_codes)])}) as t(trata_code, ord)
                    )
                    SELECT h.* FROM mvw_reporte_historico_{gerencia_clean} h
                    JOIN config_order o ON h."COD TRATA" = o.trata_code
                    WHERE (h.anio, h.mes) IN ({months_filter})
                    ORDER BY o.ord, h.anio DESC, h.mes DESC
                """
                params = {}

            result = conn.execute(text(sql), params)
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            # Precalcular meta_egr_prom para cada trata en la base de datos
            expected_targets = {}
            try:
                # Obtener el mes de metas más cercano a la fecha actual
                mes_cal = '2026-07-01'
                month_res = conn.execute(text(f"SELECT mes_calendario FROM mv_plan_metas_{gerencia_clean} ORDER BY abs(extract(epoch from (mes_calendario::timestamp - CURRENT_TIMESTAMP))) ASC LIMIT 1")).fetchone()
                if month_res:
                    mes_cal = month_res[0]

                metas_query = f"SELECT TRIM(trata) as trata, egresos_totales_plan as nueva_meta_produccion FROM mv_plan_metas_{gerencia_clean} WHERE mes_calendario = :mes"
                res_metas = conn.execute(text(metas_query), {"mes": mes_cal})
                for row in res_metas:
                    r_dict = row._mapping
                    if r_dict["trata"]:
                        expected_targets[str(r_dict["trata"]).strip().upper()] = round(r_dict["nueva_meta_produccion"] or 0)
            except Exception as e:
                import traceback
                try:
                    with open("c:\\Users\\Nicolas\\Documents\\dashboard_vscode\\dshbrd-sgdu\\backend_metas_error.txt", "w") as f_err:
                        traceback.print_exc(file=f_err)
                except Exception:
                    pass
                logger.warning(f"No se pudo consultar mv_metas_dinamicas_{gerencia_clean}, usando fallback: {e}")
                for t_code in trata_codes + ['INTERVENCIONES']:
                    expected_targets[t_code] = calculate_trata_expected_egresos(conn, gerencia_clean, t_code)

            # Enriquecer con acrónimos oficiales desde TRAMITES_CONFIG
            config_for_g = TRAMITES_CONFIG.get(gerencia_clean, {})
            df["acronimos"] = df["COD TRATA"].apply(lambda x: config_for_g.get(x, {}).get("acronimos", ""))
            df["meta_egr_prom"] = df["COD TRATA"].apply(lambda x: expected_targets.get(str(x).strip().upper(), 0))
            
            return df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error en consolidado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/{gerencia}/metas")
async def get_metas_proyeccion(gerencia: str, trata: Optional[str] = None, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
    try:
        with engine.connect() as conn:
            # 1. Obtener Histórico (12 meses) desde la nueva vista 14
            interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos"
            
            # Determinar filtros de trata
            trata_filter = "TRUE"
            egr_trata_filter = "TRUE"
            if trata:
                trata_clean = trata.strip()
                if trata_clean == 'INTERVENCIONES':
                    trata_filter = f"TRIM(trata) NOT IN (SELECT TRIM(unnest(tratas_incluidas)) FROM cfg_gestion_metas WHERE gerencia = '{gerencia_clean}')"
                    egr_trata_filter = "TRIM(trata) = 'INTERVENCIONES'"
                else:
                    trata_filter = f"TRIM(trata) = '{trata_clean}'"
                    egr_trata_filter = f"TRIM(trata) = '{trata_clean}'"

            sql_hist = f"""
                WITH ing AS (
                    SELECT to_char(fecha_ingreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                    FROM mv_{gerencia_clean}_ingresos_eventos
                    WHERE {trata_filter}
                    GROUP BY 1
                ),
                egr AS (
                    SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                    FROM (
                        SELECT fecha_egreso, trata FROM mv_{gerencia_clean}_gedos_egreso
                        UNION ALL
                        SELECT fecha_egreso, 'INTERVENCIONES' as trata FROM {interv_egr_table}
                    ) t_egr
                    WHERE {egr_trata_filter}
                    GROUP BY 1
                ),
                egr_ne AS (
                    SELECT to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_label, COUNT(*) as cant
                    FROM mv_{gerencia_clean}_egresos_no_efectivos
                    WHERE {trata_filter}
                    GROUP BY 1
                ),
                stock AS (
                    SELECT mes_label, 
                           SUM(CASE WHEN categoria = 'STOCK_PROPIO' THEN cant_expedientes ELSE 0 END) as sector, 
                           SUM(CASE WHEN categoria = 'SUBSANACION' THEN cant_expedientes ELSE 0 END) as corriente
                    FROM mv_{gerencia_clean}_stock_historico
                    WHERE {trata_filter}
                    GROUP BY 1
                )
                SELECT 
                    s.mes_label,
                    COALESCE(i.cant, 0) as ingresos,
                    COALESCE(e.cant, 0) + COALESCE(ne.cant, 0) as egresos_totales,
                    COALESCE(s.sector, 0) as stock_sector,
                    COALESCE(s.corriente, 0) as stock_corriente,
                    FALSE as es_proyeccion
                FROM stock s
                LEFT JOIN ing i ON i.mes_label = s.mes_label
                LEFT JOIN egr e ON e.mes_label = s.mes_label
                LEFT JOIN egr_ne ne ON ne.mes_label = s.mes_label
                ORDER BY s.mes_label ASC
            """
            
            result = conn.execute(text(sql_hist))
            hist_data = [dict(row._mapping) for row in result]
            
            if not hist_data:
                return {"history": [], "projection": [], "metas": {}}

            # 2. Calcular Mediana para Proyección (basado en últimos 6 meses completos, excluyendo el mes en curso)
            current_month_str = datetime.now().strftime('%Y-%m')
            complete_months = [d for d in hist_data if d['mes_label'] < current_month_str]
            recent = complete_months[-6:] if len(complete_months) >= 6 else complete_months
            
            def calculate_median(values):
                if not values:
                    return 0
                sorted_vals = sorted(values)
                n = len(sorted_vals)
                mid = n // 2
                if n % 2 == 1:
                    return sorted_vals[mid]
                else:
                    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0

            avg_ing = calculate_median([float(d['ingresos']) for d in recent])
            avg_egr = calculate_median([float(d['egresos_totales']) for d in recent])
            current_sector = float(hist_data[-1]['stock_sector'])
            current_corriente = float(hist_data[-1]['stock_corriente'])
            
            # Obtener la duración mediana (en días) para calcular la acumulación real del pipeline (WIP según Ley de Little)
            duracion_dias = 90.0  # Fallback de 3 meses (90 días)
            if trata and trata != 'INTERVENCIONES':
                try:
                    dur_res = conn.execute(text(f"SELECT COALESCE(duracion_total_mediana, 90) FROM mv_tiempos_resolucion_{gerencia_clean} WHERE trata = :t LIMIT 1"), {"t": trata}).fetchone()
                    if dur_res:
                        duracion_dias = float(dur_res[0])
                except Exception as dur_err:
                    logger.warning(f"Error obteniendo duracion de resolucion: {dur_err}")
            
            # WIP Saludable = Ingresos Promedio * (Mediana de Resolución en Meses)
            # Si ingresan 100/mes y tardan 110 días (3.66 meses), el stock en flujo acumulado debe ser 100 * 3.66 = 366 expedientes
            healthy_corriente_target = avg_ing * (duracion_dias / 30.0)
            excess_corriente = max(0.0, current_corriente - healthy_corriente_target)
            
            # Aplicamos la lógica de planificación de capacidad con esfuerzo 75% / 25%:
            # - El 75% de la capacidad objetivo (esfuerzo para ingresos) debe cubrir al menos el 100% del ingreso promedio: T >= avg_ing / 0.75
            # - El 25% de la capacidad objetivo (esfuerzo para stock) debe cubrir al menos la cuota de limpieza mensual requerida (Sector / 6 y Exceso Corriente / 3): T >= meta_limpieza_requerida / 0.25
            meta_maint = avg_ing
            meta_clean_required = (current_sector / 6.0) + (excess_corriente / 3.0)
            
            # Capacidad recomendada total (Egresos Totales Estimados): Leer directamente del plan de la tabla mv_plan_metas
            db_expected_target = None
            db_ingresos_promedio = None
            try:
                # Obtener el mes de metas más cercano a la fecha actual
                mes_cal = '2026-07-01'
                month_res = conn.execute(text(f"SELECT mes_calendario FROM mv_plan_metas_{gerencia_clean} ORDER BY abs(extract(epoch from (mes_calendario::timestamp - CURRENT_TIMESTAMP))) ASC LIMIT 1")).fetchone()
                if month_res:
                    mes_cal = month_res[0]

                if trata and trata != 'INTERVENCIONES':
                    meta_res = conn.execute(text(f"SELECT COALESCE(egresos_totales_plan, 0), COALESCE(ingresos_promedio, 0) FROM mv_plan_metas_{gerencia_clean} WHERE TRIM(UPPER(trata)) = :t AND mes_calendario = :mes LIMIT 1"), {"t": trata.strip().upper(), "mes": mes_cal}).fetchone()
                    if meta_res:
                        db_expected_target = float(meta_res[0])
                        db_ingresos_promedio = float(meta_res[1])
                else:
                    sum_res = conn.execute(text(f"SELECT SUM(COALESCE(egresos_totales_plan, 0)), SUM(COALESCE(ingresos_promedio, 0)) FROM mv_plan_metas_{gerencia_clean} WHERE mes_calendario = :mes"), {"mes": mes_cal}).fetchone()
                    if sum_res and sum_res[0] is not None:
                        db_expected_target = float(sum_res[0])
                        db_ingresos_promedio = float(sum_res[1])
            except Exception as meta_err:
                logger.warning(f"Error obteniendo egresos/ingresos de mv_plan_metas_{gerencia_clean}: {meta_err}")

            if db_ingresos_promedio is not None:
                avg_ing = db_ingresos_promedio
                meta_maint = avg_ing

            if db_expected_target is not None:
                meta_total_target = db_expected_target
            else:
                meta_total_target = max(meta_maint / 0.75, meta_clean_required / 0.25)
            
            # Distribución de la capacidad recomendada
            meta_maint_allocated = meta_total_target * 0.75
            meta_clean_allocated = meta_total_target * 0.25
            
            # 3. Generar Proyecciones (Escenario A: Actual, Escenario B: Objetivo)
            projection_current = []
            projection_target = []
            
            # El punto de partida de la proyección (stock inicial y fecha) se basa en el último día del último mes completo.
            # Esto evita que el mes incompleto en curso distorsione el punto inicial de la curva proyectada en el gráfico.
            if complete_months:
                projection_start_record = complete_months[-1]
            else:
                projection_start_record = hist_data[-1]

            proj_sector_start = float(projection_start_record['stock_sector'])
            proj_corriente_start = float(projection_start_record['stock_corriente'])
            excess_corriente_start = max(0.0, proj_corriente_start - healthy_corriente_target)

            try:
                last_date = datetime.strptime(projection_start_record['mes_label'], '%Y-%m')
            except:
                last_date = datetime.now()

            temp_sector_current = proj_sector_start
            temp_corriente_target = proj_corriente_start
            temp_sector_target = proj_sector_start
            
            for i in range(1, 8): # Proyectamos 7 meses (hasta dic 2026)
                next_month = last_date + timedelta(days=31*i)
                mes_label = next_month.strftime('%Y-%m')
                
                # Escenario Actual (Capacidad constante)
                # El stock sectorial cambia por la diferencia entre ingresos y egresos actuales
                delta_current = avg_ing - avg_egr
                temp_sector_current = max(0, temp_sector_current + delta_current)
                projection_current.append({
                    "mes_label": mes_label,
                    "ingresos": round(avg_ing),
                    "egresos_totales": round(avg_egr),
                    "stock_sector": round(temp_sector_current),
                    "stock_corriente": round(proj_corriente_start),
                    "es_proyeccion": True,
                    "escenario": "actual"
                })
                
                # Escenario Objetivo (Capacidad constante de la Nueva Meta de Producción)
                monthly_target = meta_total_target
                
                # Capacidad dedicada a la liquidación del stock sectorial acumulado
                if temp_sector_target > 0:
                    backlog_cleared = proj_sector_start / 6.0
                    temp_sector_target = max(0.0, temp_sector_target - backlog_cleared)
                else:
                    backlog_cleared = 0.0
                    temp_sector_target = 0.0
                
                # A medida que se egresa menos stock sector, volcamos más capacidad a procesar el stock corriente (flujo)
                flow_capacity = max(0.0, monthly_target - backlog_cleared)
                
                # Medida de ganancia de eficiencia basada en la liquidación del backlog sectorial
                if proj_sector_start > 0:
                    efficiency_gain = (proj_sector_start - temp_sector_target) / proj_sector_start
                else:
                    efficiency_gain = 1.0
                
                # El tiempo de tramitación efectivo disminuye (hasta un 40% de mejora o piso de 30 días) al erradicar el cuello de botella
                target_optimized_duration = max(30.0, duracion_dias * 0.6)
                effective_duration = duracion_dias - (duracion_dias - target_optimized_duration) * efficiency_gain
                
                # El piso saludable de stock corriente (WIP) disminuye dinámicamente con la reducción del tiempo de tramitación
                dynamic_healthy_corriente = avg_ing * (effective_duration / 30.0)
                
                # El stock corriente fluctúa dinámicamente según la Ley de Conservación de Flujo, acotado por el piso saludable decreciente
                temp_corriente_target = max(dynamic_healthy_corriente, temp_corriente_target + avg_ing - flow_capacity)
                
                projection_target.append({
                    "mes_label": mes_label,
                    "ingresos": round(avg_ing),
                    "egresos_totales": round(monthly_target),
                    "stock_sector": round(temp_sector_target),
                    "stock_corriente": round(temp_corriente_target),
                    "es_proyeccion": True,
                    "escenario": "objetivo"
                })

            # 3.5. Intentar cargar la planificación oficial desde la vista mv_plan_metas_{gerencia_clean}
            projection_target_db = []
            try:
                plan_trata_filter = f"TRIM(trata) = '{trata}'" if trata and trata != 'INTERVENCIONES' else "TRUE"
                plan_sql = f"""
                    SELECT nro_mes, to_char(mes_calendario, 'YYYY-MM') as mes_label,
                           SUM(COALESCE(ingresos_promedio, 0)) as ingresos,
                           SUM(COALESCE(egresos_totales_plan, 0)) as egresos_totales,
                           SUM(COALESCE(stock_sector_fin, 0)) as stock_sector,
                           SUM(COALESCE(stock_corriente, 0)) as stock_corriente
                    FROM mv_plan_metas_{gerencia_clean}
                    WHERE {plan_trata_filter} AND mes_calendario >= '2026-06-01'
                    GROUP BY 1, 2
                    ORDER BY 1 ASC
                """
                plan_res = conn.execute(text(plan_sql))
                for row in plan_res:
                    r_dict = row._mapping
                    projection_target_db.append({
                        "mes_label": r_dict["mes_label"],
                        "ingresos": round(float(r_dict["ingresos"])),
                        "egresos_totales": round(float(r_dict["egresos_totales"])),
                        "stock_sector": round(float(r_dict["stock_sector"])),
                        "stock_corriente": round(float(r_dict["stock_corriente"])),
                        "es_proyeccion": True,
                        "escenario": "objetivo"
                    })
            except Exception as plan_err:
                logger.warning(f"No se pudo consultar mv_plan_metas_{gerencia_clean}, usando fallback matemático: {plan_err}")

            if projection_target_db:
                projection_target = projection_target_db

            # 4. Metadatos para las tarjetas
            capacidad_limpieza_actual = avg_egr * 0.25
            meses_barrido_estimado = current_sector / capacidad_limpieza_actual if capacidad_limpieza_actual > 0 else 999

            return {
                "history": hist_data,
                "projection_current": projection_current,
                "projection_target": projection_target,
                "metas": {
                    "avg_ing": round(avg_ing),
                    "avg_egr_actual": round(avg_egr),
                    "meta_mantenimiento": round(meta_maint_allocated),
                    "meta_limpieza_objetivo": round(meta_clean_allocated),
                    "meta_total_recomendada": round(meta_total_target),
                    "meses_barrido_actual": round(meses_barrido_estimado),
                    "duracion_resolucion": round(duracion_dias)
                }
            }
    except Exception as e:
        logger.error(f"Error en metas proyección: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/familia")
async def get_reporte_familia(
    trata: List[str] = Query(...), 
    current_user: User = Depends(get_current_user)
):
    try:
        # Group tratas by gerencia
        trata_to_gerencia = {}
        for g, cfg in TRAMITES_CONFIG.items():
            for t in cfg.keys():
                if t != 'INTERVENCIONES':
                    trata_to_gerencia[t.upper()] = g.lower()

        # Overrides requested by the user for Family dashboard views
        trata_overrides = {
            "MDUG3001A": "etapa_proyecto",
            "MDUG0104A": "etapa_proyecto",
            "MDUG1501J": "etapa_proyecto",
            "MDUG0142A": "etapa_proyecto",
            "MDUG4003A": "etapa_proyecto"
        }

        aggregated_history = {}
        total_ingresos_promedio = 0
        total_egresos_totales_plan = 0

        with engine.connect() as conn:
            for t_code in trata:
                t_upper = t_code.strip().upper()
                gerencia_clean = trata_overrides.get(t_upper) or trata_to_gerencia.get(t_upper)
                if not gerencia_clean:
                    continue

                # 1. Fetch June 2026 plan metas for this trata
                try:
                    meta_res = conn.execute(text(f"""
                        SELECT COALESCE(egresos_totales_plan, 0), COALESCE(ingresos_promedio, 0) 
                        FROM mv_plan_metas_{gerencia_clean} 
                        WHERE TRIM(UPPER(trata)) = :t AND mes_calendario = '2026-06-01' LIMIT 1
                    """), {"t": t_upper}).fetchone()
                    if meta_res:
                        total_egresos_totales_plan += float(meta_res[0])
                        total_ingresos_promedio += float(meta_res[1])
                except Exception as meta_err:
                    logger.warning(f"Error fetching plan metas for {t_upper} in {gerencia_clean}: {meta_err}")

                # 2. Fetch 12-month history for this trata
                try:
                    sql_hist = f"""
                        WITH periodos AS (
                            SELECT DISTINCT mes_label FROM mv_{gerencia_clean}_stock_historico
                            ORDER BY mes_label DESC LIMIT 12
                        ),
                        ing AS (
                            SELECT to_char(fecha_ingreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                            FROM mv_{gerencia_clean}_ingresos_eventos WHERE TRIM(trata) = :t
                            GROUP BY 1
                        ),
                        egr_ef AS (
                            SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                            FROM mv_{gerencia_clean}_gedos_egreso WHERE TRIM(trata) = :t
                            GROUP BY 1
                        ),
                        egr_ne AS (
                            SELECT to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_label, COUNT(*) as cant
                            FROM mv_{gerencia_clean}_egresos_no_efectivos WHERE TRIM(trata) = :t
                            GROUP BY 1
                        ),
                        stock_data AS (
                            SELECT mes_label, 
                                   SUM(CASE WHEN categoria = 'STOCK_PROPIO' THEN cant_expedientes ELSE 0 END) as stock_propio,
                                   SUM(CASE WHEN categoria = 'SUBSANACION' THEN cant_expedientes ELSE 0 END) as stock_subs
                            FROM mv_{gerencia_clean}_stock_historico WHERE TRIM(trata) = :t
                            GROUP BY 1
                        )
                        SELECT 
                            p.mes_label,
                            COALESCE(i.cant, 0) as "ING",
                            COALESCE(ef.cant, 0) as "EGR_EF",
                            COALESCE(ne.cant, 0) as "EGR_NE",
                            COALESCE(s.stock_propio, 0) as "STOCK_PROPIO",
                            COALESCE(s.stock_subs, 0) as "STOCK_SUBS"
                        FROM periodos p
                        LEFT JOIN ing i ON i.mes_label = p.mes_label
                        LEFT JOIN egr_ef ef ON ef.mes_label = p.mes_label
                        LEFT JOIN egr_ne ne ON ne.mes_label = p.mes_label
                        LEFT JOIN stock_data s ON s.mes_label = p.mes_label
                        ORDER BY p.mes_label DESC
                    """
                    res_hist = conn.execute(text(sql_hist), {"t": t_upper})
                    for row in res_hist:
                        r_dict = row._mapping
                        mes_label = r_dict["mes_label"]
                        if mes_label not in aggregated_history:
                            aggregated_history[mes_label] = {
                                "mes_label": mes_label,
                                "ING": 0,
                                "EGR_EF": 0,
                                "EGR_NE": 0,
                                "STOCK_PROPIO": 0,
                                "STOCK_SUBS": 0
                            }
                        aggregated_history[mes_label]["ING"] += int(r_dict["ING"])
                        aggregated_history[mes_label]["EGR_EF"] += int(r_dict["EGR_EF"])
                        aggregated_history[mes_label]["EGR_NE"] += int(r_dict["EGR_NE"])
                        aggregated_history[mes_label]["STOCK_PROPIO"] += int(r_dict["STOCK_PROPIO"])
                        aggregated_history[mes_label]["STOCK_SUBS"] += int(r_dict["STOCK_SUBS"])
                except Exception as hist_err:
                    logger.warning(f"Error fetching history for {t_upper} in {gerencia_clean}: {hist_err}")

        # Format historical data sorted chronologically
        history_list = sorted(list(aggregated_history.values()), key=lambda x: x["mes_label"])
        
        # Format month names and years for UI consumption
        formatted_history = []
        for h in history_list:
            parts = h["mes_label"].split('-')
            formatted_history.append({
                "anio": int(parts[0]),
                "mes": int(parts[1]),
                "ING": h["ING"],
                "EGR_EF": h["EGR_EF"],
                "EGR_NE": h["EGR_NE"],
                "STOCK_PROPIO": h["STOCK_PROPIO"],
                "STOCK_SUBS": h["STOCK_SUBS"]
            })

        return {
            "history": formatted_history,
            "metas": {
                "ingresos_esperados": round(total_ingresos_promedio),
                "egresos_totales_plan": round(total_egresos_totales_plan)
            }
        }
    except Exception as e:
        logger.error(f"Error en reporte familia: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/familias_overview")
async def get_reporte_familias_overview(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            db_rows = conn.execute(text("SELECT nombre, tratas FROM public.cfg_tramites_familias ORDER BY id")).fetchall()
            FAMILIAS_CONFIG = {r[0]: r[1] for r in db_rows}
    except Exception as db_err:
        logger.error(f"Error reading families config from DB: {db_err}")
        FAMILIAS_CONFIG = {}
    
    trata_to_gerencia = {}
    for g, cfg in TRAMITES_CONFIG.items():
        for t in cfg.keys():
            if t != 'INTERVENCIONES':
                trata_to_gerencia[t.upper()] = g.lower()

    # Overrides requested by the user for Family dashboard views
    trata_overrides = {
        "MDUG3001A": "etapa_proyecto",
        "MDUG0104A": "etapa_proyecto",
        "MDUG1501J": "etapa_proyecto",
        "MDUG0142A": "etapa_proyecto",
        "MDUG4003A": "etapa_proyecto"
    }

    results = []
    
    try:
        with engine.connect() as conn:
            for family_name, tratas in FAMILIAS_CONFIG.items():
                total_target = 0
                total_actual = 0
                total_prev = 0
                
                for t_code in tratas:
                    t_upper = t_code.strip().upper()
                    gerencia_clean = trata_overrides.get(t_upper) or trata_to_gerencia.get(t_upper)
                    if not gerencia_clean:
                        continue
                        
                    try:
                        meta_res = conn.execute(text(f"""
                            SELECT COALESCE(egresos_totales_plan, 0)
                            FROM mv_plan_metas_{gerencia_clean} 
                            WHERE TRIM(UPPER(trata)) = :t AND mes_calendario = '2026-06-01' LIMIT 1
                        """), {"t": t_upper}).fetchone()
                        if meta_res:
                            total_target += float(meta_res[0])
                    except Exception:
                        pass
                        
                    try:
                        sql_months = f"""
                            SELECT DISTINCT mes_label FROM mv_{gerencia_clean}_stock_historico
                            ORDER BY mes_label DESC LIMIT 2
                        """
                        months_rows = conn.execute(text(sql_months)).fetchall()
                        if len(months_rows) >= 1:
                            mes_val = months_rows[0][0]
                            egr_ef_res = conn.execute(text(f"""
                                SELECT COUNT(*) FROM mv_{gerencia_clean}_gedos_egreso 
                                WHERE TRIM(trata) = :t AND to_char(fecha_egreso, 'YYYY-MM') = :m
                            """), {"t": t_upper, "m": mes_val}).fetchone()
                            
                            egr_ne_res = conn.execute(text(f"""
                                SELECT COUNT(*) FROM mv_{gerencia_clean}_egresos_no_efectivos
                                WHERE TRIM(trata) = :t AND to_char(fecha_ultimo_movimiento, 'YYYY-MM') = :m
                            """), {"t": t_upper, "m": mes_val}).fetchone()
                            
                            if egr_ef_res:
                                total_actual += int(egr_ef_res[0])
                            if egr_ne_res:
                                total_actual += int(egr_ne_res[0])
                                
                        if len(months_rows) >= 2:
                            mes_prev = months_rows[1][0]
                            egr_ef_prev = conn.execute(text(f"""
                                SELECT COUNT(*) FROM mv_{gerencia_clean}_gedos_egreso 
                                WHERE TRIM(trata) = :t AND to_char(fecha_egreso, 'YYYY-MM') = :m
                            """), {"t": t_upper, "m": mes_prev}).fetchone()
                            
                            egr_ne_prev = conn.execute(text(f"""
                                SELECT COUNT(*) FROM mv_{gerencia_clean}_egresos_no_efectivos
                                WHERE TRIM(trata) = :t AND to_char(fecha_ultimo_movimiento, 'YYYY-MM') = :m
                            """), {"t": t_upper, "m": mes_prev}).fetchone()
                            
                            if egr_ef_prev:
                                total_prev += int(egr_ef_prev[0])
                            if egr_ne_prev:
                                total_prev += int(egr_ne_prev[0])
                    except Exception:
                        pass
                
                progress_pct = round((total_actual / total_target) * 100) if total_target > 0 else 0
                
                variation_pct = 0.0
                if total_prev > 0:
                    variation_pct = round(((total_actual - total_prev) / total_prev) * 100, 1)
                
                descriptions = {
                    "Catastro": "14 trámites (Planos de mensura, PH, etc.)",
                    "Registros": "5 trámites (Inicio de obras, Model BA, etc.)",
                    "Incendio": "Prevención contra incendios",
                    "Conforme": "Conforme a obra civil",
                    "Instalaciones": "8 trámites (Sanitaria, Ventilación, Térmica, etc.)",
                    "Consultas de Usos": "5 trámites de localización y antenas",
                    "Permisos": "3 trámites (Permiso civil, Demoliciones, etc.)",
                    "Interpretaciones/Informe Urbanisitco": "Interpretación e informe urbanístico",
                    "Consultas Obligatorias": "APH y Catalogados / General",
                    "Otros": "9 trámites (Aviso de obra, Foguistas, etc.)"
                }
                
                results.append({
                    "family_name": family_name,
                    "actual_egr": round(total_actual),
                    "target_egr": round(total_target),
                    "progress_pct": progress_pct,
                    "variation_pct": variation_pct,
                    "trata_count": len(tratas),
                    "tratas": tratas,
                    "description": descriptions.get(family_name, f"{len(tratas)} trámites")
                })
                
        return results
    except Exception as e:
        logger.error(f"Error in families overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/{gerencia}/tramite/{trata}")
async def get_reporte_tramite_historico(gerencia: str, trata: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
    try:
        # Calcular los 12 meses: Actual + 11 anteriores
        now = datetime.now()
        months_list = []
        curr_y, curr_m = now.year, now.month
        for i in range(12):
            months_list.append(f"({curr_y}, {curr_m})")
            curr_m -= 1
            if curr_m == 0:
                curr_m = 12
                curr_y -= 1
        months_filter = ", ".join(months_list)

        with engine.connect() as conn:
            # Obtener el nombre descriptivo de la trata
            if trata == 'INTERVENCIONES':
                nombre_trata = "Intervenciones"
            else:
                trata_info = conn.execute(text("""
                    SELECT COALESCE(
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE trata_reporte = :t AND gerencia = :g LIMIT 1),
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE :t = ANY(tratas_incluidas) AND gerencia = :g LIMIT 1),
                        (SELECT descripcion_trata FROM vw_expedientes_maestro WHERE trata = :t LIMIT 1)
                    )
                """), {"t": trata, "g": gerencia_clean}).fetchone()
                nombre_trata = trata_info[0] if trata_info else trata

            # Seleccionamos directamente los valores de la vista histórica para asegurar consistencia total con la tabla
            if gerencia_clean in ['instalaciones', 'morfologia', 'contable', 'etapa_proyecto', 'catastro', 'aph', 'usos', 'regularizacion', 'aviso_obra']:
                # Usamos el ecosistema modular para el gráfico histórico de 12 meses
                # Filtro especial para agrupar intervenciones si es necesario
                trata_filter = f"trata = '{trata}'" if trata != 'INTERVENCIONES' else f"trata NOT IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = '{gerencia_clean}')"
                
                # Definir tabla de egresos de intervenciones (Contable tiene nombre distinto)
                interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"
                egr_trata_where = "trata = 'INTERVENCIONES'" if trata == 'INTERVENCIONES' else f"trata = '{trata}'"

                sql = f"""
                    WITH periodos AS (
                        SELECT DISTINCT mes_label FROM mv_{gerencia_clean}_stock_historico
                        ORDER BY mes_label DESC LIMIT 12
                    ),
                    ing AS (
                        SELECT to_char(fecha_ingreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                        FROM mv_{gerencia_clean}_ingresos_eventos WHERE {trata_filter}
                        GROUP BY 1
                    ),
                    egr_ef AS (
                        -- Egresos (Combinamos oficial e intervenciones si es el caso)
                        SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                        FROM (
                            SELECT fecha_egreso, trata FROM mv_{gerencia_clean}_gedos_egreso
                            UNION ALL
                            SELECT fecha_egreso, 'INTERVENCIONES' as trata FROM {interv_egr_table}
                        ) t_egr
                        WHERE {egr_trata_where}
                        GROUP BY 1
                    ),
                    egr_ne AS (
                        SELECT to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_label, COUNT(*) as cant
                        FROM mv_{gerencia_clean}_egresos_no_efectivos WHERE {trata_filter}
                        GROUP BY 1
                    ),
                    stock_data AS (
                        SELECT mes_label, 
                               SUM(CASE WHEN categoria = 'STOCK_PROPIO' THEN cant_expedientes ELSE 0 END) as stock_propio,
                               SUM(CASE WHEN categoria = 'SUBSANACION' THEN cant_expedientes ELSE 0 END) as stock_subs
                        FROM mv_{gerencia_clean}_stock_historico WHERE {trata_filter}
                        GROUP BY 1
                    ),
                    current_stock AS (
                        -- Foto de HOY para el mes actual
                        SELECT COUNT(*) as cant FROM mv_{gerencia_clean}_stock_propio WHERE {trata_filter}
                        UNION ALL
                        SELECT COUNT(*) as cant FROM mv_{gerencia_clean}_intervenciones_stock WHERE {'1=1' if trata == 'INTERVENCIONES' else 'FALSE'}
                    ),
                    current_subs AS (
                        -- Foto de HOY para subsanaciones
                        SELECT COUNT(*) as cant FROM mv_{gerencia_clean}_subsanaciones WHERE {trata_filter}
                        UNION ALL
                        SELECT COUNT(*) as cant FROM mv_{gerencia_clean}_intervenciones_subs WHERE {'1=1' if trata == 'INTERVENCIONES' else 'FALSE'}
                    )
                    SELECT 
                        split_part(p.mes_label, '-', 1)::int as anio,
                        split_part(p.mes_label, '-', 2)::int as mes,
                        '{nombre_trata}'::text as "DETALLE TRATA",
                        COALESCE(i.cant, 0) as "ING",
                        COALESCE(ef.cant, 0) as "EGR_EF",
                        COALESCE(ne.cant, 0) as "EGR_NE",
                        CASE 
                            WHEN p.mes_label = to_char(now(), 'YYYY-MM')
                            THEN COALESCE((SELECT SUM(cant) FROM current_stock), 0)
                            ELSE COALESCE(s.stock_propio, 0)
                        END as "STOCK_PROPIO",
                        CASE 
                            WHEN p.mes_label = to_char(now(), 'YYYY-MM')
                            THEN COALESCE((SELECT SUM(cant) FROM current_subs), 0)
                            ELSE COALESCE(s.stock_subs, 0)
                        END as "STOCK_SUBS"
                    FROM periodos p
                    LEFT JOIN ing i ON i.mes_label = p.mes_label
                    LEFT JOIN egr_ef ef ON ef.mes_label = p.mes_label
                    LEFT JOIN egr_ne ne ON ne.mes_label = p.mes_label
                    LEFT JOIN stock_data s ON s.mes_label = p.mes_label
                    ORDER BY anio DESC, mes DESC
                """
            elif trata == 'INTERVENCIONES':
                sql = f"""
                    SELECT anio, mes, "DETALLE TRATA", "ING", "EGR_EF", "EGR_NE", "STOCK_PROPIO", "STOCK_SUBS"
                    FROM mvw_reporte_historico_{gerencia_clean}
                    WHERE "COD TRATA" = 'INTERVENCIONES'
                      AND (anio, mes) IN ({months_filter})
                    ORDER BY anio DESC, mes DESC
                """
            else:
                sql = f"""
                    SELECT anio, mes, "DETALLE TRATA", "ING", "EGR_EF", "EGR_NE", "STOCK_PROPIO", "STOCK_SUBS"
                    FROM mvw_reporte_historico_{gerencia_clean}
                    WHERE "COD TRATA" = '{trata}'
                      AND (anio, mes) IN ({months_filter})
                    ORDER BY anio DESC, mes DESC
                """

            df_hist = pd.read_sql(sql, conn)
            
        if df_hist.empty: return []

        # Retornamos los datos tal cual vienen de la vista
        return df_hist.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error en histórico individual: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/{gerencia}/tramite/{trata}/stock_detail")
async def get_tramite_stock_detail(gerencia: str, trata: str, current_user: User = Depends(get_current_user)):
    """Detalle de Stock Propio Actual - usa la MISMA lógica que las vistas históricas."""
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
    if gerencia_clean not in TRAMITES_CONFIG: raise HTTPException(status_code=404, detail="Gerencia no encontrada.")

    try:
        with engine.connect() as conn:
            # Obtener el nombre descriptivo de la trata
            if trata == 'INTERVENCIONES':
                nombre_trata = "Intervenciones"
            else:
                trata_info = conn.execute(text("""
                    SELECT COALESCE(
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE trata_reporte = :t AND gerencia = :g LIMIT 1),
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE :t = ANY(tratas_incluidas) AND gerencia = :g LIMIT 1),
                        (SELECT descripcion_trata FROM vw_expedientes_maestro WHERE trata = :t LIMIT 1)
                    )
                """), {"t": trata, "g": gerencia_clean}).fetchone()
                nombre_trata = trata_info[0] if trata_info else trata

            # Usamos la vista materializada optimizada para el detalle si está disponible
            if gerencia_clean in ['instalaciones', 'morfologia', 'contable', 'etapa_proyecto', 'catastro', 'aph', 'usos', 'regularizacion', 'aviso_obra']:
                # Mapeamos los nombres de columnas de tu nueva vista a lo que espera el front
                # Si la trata no es de las "oficiales", es una intervención
                trata_codes = list(TRAMITES_CONFIG[gerencia_clean].keys())
                is_official = trata in [t for t in trata_codes if t != 'INTERVENCIONES']
                view_name = f"mv_{gerencia_clean}_stock_propio" if is_official else f"mv_{gerencia_clean}_intervenciones_stock"
                
                sql = f"""
                    SELECT {view_name}.id_expediente, {view_name}.expediente, {view_name}.fecha_primer_ingreso_gerencia as fecha_ing, 
                           {view_name}.fecha_recepcion_analista as fecha_ultimo_pase, 
                           {view_name}.dias_en_poder_actual as dias, {view_name}.analista, du.apellido_nombre as analista_nombre, {view_name}.trata, 
                           ext.fecha_creacion as caratula,
                           ext.descripcion_trata, ext.descripcion, ext.estado as estado_expediente,
                           (CURRENT_DATE - {view_name}.fecha_primer_ingreso_gerencia::date) as dias_en_gerencia
                    FROM {view_name}
                    LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = {view_name}.id_expediente
                    LEFT JOIN datos_usuario du ON {view_name}.analista = du.usuario
                    WHERE {f"{view_name}.trata = '{trata}'" if trata != 'INTERVENCIONES' else '1=1'}
                """
                result = conn.execute(text(sql))
                rows = [dict(r._mapping) for r in result.fetchall()]

                # --- PROCESAMIENTO DE RANGOS Y ANTIGÜEDAD PARA INSTALACIONES ---
                analyst_data = {}
                propio_month_counts = {}
                ranges = [(0, 15, "Menos de 15 dias"), (15, 30, "15 a 30 dias"), (30, 45, "30 a 45 dias"), (45, 60, "45 a 60 dias"), (60, 75, "60 a 75 dias"), (75, 90, "75 a 90 dias"), (90, 999999, "Mas de 90 dias")]
                
                for row in rows:
                    analista = row.get('analista') or 'SIN ASIGNAR'
                    analista_nombre = row.get('analista_nombre') or analista
                    dias = row.get('dias') or 0
                    f_pase = row.get('fecha_ultimo_pase')
                    
                    # Agrupación por mes (Antigüedad Real)
                    if f_pase and hasattr(f_pase, 'strftime'):
                        m_key = f_pase.strftime("%Y-%m")
                        propio_month_counts[m_key] = propio_month_counts.get(m_key, 0) + 1

                    # Agrupación por Analista y Rango
                    if analista not in analyst_data:
                        analyst_data[analista] = {"analista": analista, "analista_nombre": analista_nombre, "TOTAL": 0}
                        for _, _, r_name in ranges: analyst_data[analista][r_name] = 0
                    
                    analyst_data[analista]["TOTAL"] += 1
                    for r_min, r_max, r_name in ranges:
                        if r_min <= dias < r_max:
                            analyst_data[analista][r_name] += 1
                            break
                
                # Formatear month_dist para el gráfico
                month_dist = [{"periodo": m, "cantidad": propio_month_counts.get(m, 0)} for m in sorted(propio_month_counts.keys())]
            else:
                # Obtener configuración de analistas y buzones directamente de la DB para esta trata
                cfg_query = text("""
                    SELECT buzones_ingreso, analistas_oficiales 
                    FROM cfg_gestion_metas 
                    WHERE gerencia = :g AND trata_reporte = :t
                """)
                # Mapeo de lookup de configuración (Instalaciones y Contable tienen tablas propias de configuración)
                trata_cfg_lookup = gerencia_clean.upper() if gerencia_clean in ['instalaciones', 'contable'] else trata
                cfg_res = conn.execute(cfg_query, {"g": gerencia_clean, "t": trata_cfg_lookup}).fetchone()
                
                if not cfg_res:
                    return {"nombre_trata": nombre_trata, "stock_propio_count": 0, "month_distribution": [], "analyst_distribution": [], "expedientes": []}
                
                # Combinar buzones y analistas para el filtro de la vista
                sector_whitelist = (cfg_res[0] or []) + (cfg_res[1] or [])
                if not sector_whitelist:
                    return {"nombre_trata": nombre_trata, "stock_propio_count": 0, "month_distribution": [], "analyst_distribution": [], "expedientes": []}

                sql = f"""
                    SELECT id_expediente, expediente, fecha_ing, fecha_ultimo_pase, 
                           dias_stock as dias, analista_actual as analista, du.apellido_nombre as analista_nombre, trata,
                           fecha_creacion as caratula,
                           descripcion_trata,
                           descripcion,
                           estado as estado_expediente,
                           dias_stock as dias_en_gerencia
                    FROM mvw_stock_actual_detalle
                    LEFT JOIN datos_usuario du ON mvw_stock_actual_detalle.analista_actual = du.usuario
                    WHERE trata_reporte = :t 
                      AND gerencia = :g
                      AND is_subs = 0
                      AND analista_actual = ANY(:whitelist)
                """
                result = conn.execute(text(sql), {"t": trata, "g": gerencia_clean, "whitelist": sector_whitelist})
                rows = [dict(r._mapping) for r in result.fetchall()]

                # Distribución para otras gerencias
                query_month = text(f"SELECT anio || '-' || LPAD(mes::text, 2, '0') as periodo, COUNT(*) as cantidad FROM mvw_reporte_historico_{gerencia_clean} WHERE \"COD TRATA\" = :t GROUP BY 1 ORDER BY 1")
                res_month = conn.execute(query_month, {"t": trata})
                month_dist = [dict(row) for row in res_month.mappings()]
                
                # --- PROCESAMIENTO DE RANGOS Y ANALISTAS ---
                analyst_data = {}
                ranges = [(0, 15, "Menos de 15 dias"), (15, 30, "15 a 30 dias"), (30, 45, "30 a 45 dias"), (45, 60, "45 a 60 dias"), (60, 75, "60 a 75 dias"), (75, 90, "75 a 90 dias"), (90, 999999, "Mas de 90 dias")]
                
                for row in rows:
                    analista = row.get('analista') or 'SIN ASIGNAR'
                    analista_nombre = row.get('analista_nombre') or analista
                    dias = row.get('dias') or 0
                    
                    if analista not in analyst_data:
                        analyst_data[analista] = {"analista": analista, "analista_nombre": analista_nombre, "TOTAL": 0}
                        for _, _, r_name in ranges: analyst_data[analista][r_name] = 0
                    
                    analyst_data[analista]["TOTAL"] += 1
                    for r_min, r_max, r_name in ranges:
                        if r_min <= dias < r_max:
                            analyst_data[analista][r_name] += 1
                            break
            
            return {
                "nombre_trata": nombre_trata,
                "stock_propio_count": len(rows),
                "month_distribution": month_dist,
                "analyst_distribution": list(analyst_data.values()),
                "expedientes": [
                    {
                        "id_expediente": r.get("id_expediente"),
                        "expediente": r.get("expediente"),
                        "fecha_ing": r.get("fecha_ing").strftime("%Y-%m-%d %H:%M:%S") if r.get("fecha_ing") and hasattr(r.get("fecha_ing"), "strftime") else None,
                        "fecha_ultimo_pase": r.get("fecha_ultimo_pase").strftime("%Y-%m-%d %H:%M:%S") if r.get("fecha_ultimo_pase") and hasattr(r.get("fecha_ultimo_pase"), "strftime") else None,
                        "dias": r.get("dias") if r.get("dias") is not None else 0,
                        "analista": r.get("analista"),
                        "analista_nombre": r.get("analista_nombre") or r.get("analista"),
                        "trata": r.get("trata"),
                        "caratula": r.get("caratula").strftime("%Y-%m-%d %H:%M:%S") if r.get("caratula") and hasattr(r.get("caratula"), "strftime") else (str(r.get("caratula"))[:19] if r.get("caratula") else None),
                        "descripcion_trata": r.get("descripcion_trata"),
                        "descripcion": r.get("descripcion"),
                        "estado_expediente": r.get("estado_expediente"),
                        "dias_en_gerencia": r.get("dias_en_gerencia") if r.get("dias_en_gerencia") is not None else 0
                    } 
                    for r in rows[:1000]
                ]
            }
    except Exception as e:
        logger.error(f"Error en stock_detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/{gerencia}/buzones")
async def get_gerencia_buzones(gerencia: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
    
    if gerencia_clean == 'secgdu_todos':
        try:
            with engine.connect() as conn:
                sql = """
                    SELECT 
                        buzon as username,
                        buzon as name,
                        total_expedientes as count,
                        egresados_efectivos,
                        egresados_no_efectivos,
                        pendientes_actividad
                    FROM public.mv_secgdu_buzones_resumen
                    ORDER BY total_expedientes DESC
                """
                result = conn.execute(text(sql))
                rows = [dict(r._mapping) for r in result.fetchall()]
                for r in rows:
                    r["expedientes"] = []
                return rows
        except Exception as e:
            logger.error(f"Error en get_gerencia_buzones (secgdu_todos): {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    if gerencia_clean == 'analisis_archivo':
        try:
            with engine.connect() as conn:
                sql = """
                    SELECT 
                        up.id_expediente, 
                        ext.expediente, 
                        up.fecha_ultimo_pase as fecha_primer_ingreso_gerencia, 
                        up.fecha_ultimo_pase as fecha_recepcion_analista, 
                        (CURRENT_DATE - up.fecha_ultimo_pase::date) as dias_en_poder_actual, 
                        up.destinatario_actual as analista, 
                        up.destinatario_actual as analista_nombre, 
                        ext.trata, 
                        ext.fecha_creacion,
                        ext.descripcion_trata, 
                        ext.descripcion, 
                        ext.estado as estado_expediente,
                        (CURRENT_DATE - up.fecha_ultimo_pase::date) as dias_en_gerencia,
                        'EGRESADO' as ubicacion
                    FROM mv_ultimo_pase up
                    JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = up.id_expediente
                    WHERE up.destinatario_actual IN (
                        'ARCHIVODGTAL', 'DGIUR-PREARCHIVO', 'DGIUR-SGUI', 'DGROC-ANTECEDENTESRLM', 'DGROC-APTOSGRYCO', 
                        'DGROC-ARCHIVO', 'DGROC-ARI', 'DGROC-CIC', 'DGROC-CONTABLE', 'DGROC-COPIAPLANO', 
                        'DGROC-DCATAT', 'DGROC-DCATDES', 'DGROC-DCATPOL', 'DGROC-DCATRUD', 'DGROC-DCATTIT', 
                        'DGROC-DCG', 'DGROC-DCIDITI', 'DGROC-DCOBAAYFO', 'DGROC-DCOBLEG', 'DGROC-DCOBREG', 
                        'DGROC-DCOBREGD', 'DGROC-DESCARGOS', 'DGROC-DGROCARI', 'DGROC-DGROCDES', 'DGROC-DGROCRRHH', 
                        'DGROC-DTACONT', 'DGROC-DTADES', 'DGROC-DTARPS', 'DGROC-ELEVADORES', 'DGROC-ESPERAINSTALACIONES', 
                        'DGROC-FICHA_PARCELARIA', 'DGROC-GO', 'DGROC-LEGAJOS', 'DGROC-LEGAJOSAUTOMAT', 'DGROC-LEY104', 
                        'DGROC-MESADES', 'DGROC-MESAMIDI', 'DGROC-MESAMIDINST', 'DGROC-MESAMIDINSTINCENDIO', 
                        'DGROC-MESAMIPVO', 'DGROC-OBRASADMIN', 'DGROC-OBRASENCURSO', 'DGROC-OBRASTECNICA', 'DGROC-OBSINCENDIO', 
                        'DGROC-OBSOBRAPREARCHIVO', 'DGROC-OBSPREARCHAYFO', 'DGROC-OBSREGISTRO', 'DGROC-PENDIENTESDEPAGO', 
                        'DGROC-RECHAZADOSLEGAJOS', 'DGROC-REVISIONCONTABLE', 'DGROC-SEDR', 'DGROC-SEDRI', 'DGROC-SGUI', 
                        'DGROC-TERMICAS', 'DGSOCAI-ARCHIVO', 'MGEYA-ARCHIVO', 'MGEYA-DCG', 'PG-ARCHIVO', 
                        'SECGDU-ARCHIVODESPACHO', 'SECLYT-ARCHIVO', 'SSGDU-ARCHIVODESPACHO', 'SSGU-ARCHIVODESPACHO'
                    )
                """
                result = conn.execute(text(sql))
                rows = [dict(r._mapping) for r in result.fetchall()]
                
                # Group ids by gerencia to dynamically resolve their actual states
                from collections import defaultdict
                ids_by_gerencia = defaultdict(list)
                resolved_locations = {}
                trata_overrides = {
                    "MDUG3001A": "etapa_proyecto",
                    "MDUG0104A": "etapa_proyecto",
                    "MDUG1501J": "etapa_proyecto",
                    "MDUG0142A": "etapa_proyecto",
                    "MDUG4003A": "etapa_proyecto"
                }
                for r in rows:
                    id_exp = r["id_expediente"]
                    trata = r["trata"]
                    trata_upper = trata.strip().upper() if trata else ""
                    ger = None
                    if trata_upper in trata_overrides:
                        ger = trata_overrides[trata_upper]
                    else:
                        for g, config in TRAMITES_CONFIG.items():
                            if trata_upper in config:
                                ger = g
                                break
                    if ger:
                        ids_by_gerencia[ger].append(id_exp)
                    else:
                        resolved_locations[id_exp] = "FUERA DE TABLERO"

                for ger, ids in ids_by_gerencia.items():
                    if not ids:
                        continue
                    # 1. Stock Propio
                    try:
                        sp_res = conn.execute(text(f"SELECT id_expediente FROM mv_{ger}_stock_propio WHERE id_expediente IN :ids"), {"ids": tuple(ids)}).fetchall()
                        for s_row in sp_res:
                            resolved_locations[s_row[0]] = "STOCK PROPIO"
                    except Exception:
                        pass
                    # 2. Subsanación
                    try:
                        sub_res = conn.execute(text(f"SELECT id_expediente FROM mv_{ger}_subsanaciones WHERE id_expediente IN :ids"), {"ids": tuple(ids)}).fetchall()
                        for s_row in sub_res:
                            resolved_locations[s_row[0]] = "SUBSANACION"
                    except Exception:
                        pass
                    # 3. Intervencion Stock
                    try:
                        sp_int = conn.execute(text(f"SELECT id_expediente FROM mv_{ger}_intervenciones_stock WHERE id_expediente IN :ids"), {"ids": tuple(ids)}).fetchall()
                        for s_row in sp_int:
                            if s_row[0] not in resolved_locations:
                                resolved_locations[s_row[0]] = "STOCK PROPIO (INTERVENCION)"
                    except Exception:
                        pass
                    # 4. Intervencion Subsanacion
                    try:
                        sub_int = conn.execute(text(f"SELECT id_expediente FROM mv_{ger}_intervenciones_subs WHERE id_expediente IN :ids"), {"ids": tuple(ids)}).fetchall()
                        for s_row in sub_int:
                            if s_row[0] not in resolved_locations:
                                resolved_locations[s_row[0]] = "SUBSANACION (INTERVENCION)"
                    except Exception:
                        pass
                    # 5. Gedos Egreso
                    try:
                        egr_ef = conn.execute(text(f"SELECT id_expediente FROM mv_{ger}_gedos_egreso WHERE id_expediente IN :ids"), {"ids": tuple(ids)}).fetchall()
                        for s_row in egr_ef:
                            resolved_locations[s_row[0]] = "EGRESADO"
                    except Exception:
                        pass
                    # 6. Egresos No Efectivos
                    try:
                        egr_ne = conn.execute(text(f"SELECT id_expediente FROM mv_{ger}_egresos_no_efectivos WHERE id_expediente IN :ids"), {"ids": tuple(ids)}).fetchall()
                        for s_row in egr_ne:
                            resolved_locations[s_row[0]] = "EGRESADO (NO EFECTIVO)"
                    except Exception:
                        pass

                # Query last pase reason (motivo) in batch
                last_pase_motivos = {}
                try:
                    all_ids = [r["id_expediente"] for r in rows]
                    if all_ids:
                        motivos_res = conn.execute(text("""
                            SELECT DISTINCT ON (id_expediente) id_expediente, motivo
                            FROM mvw_ee_pases_secgdu
                            WHERE id_expediente IN :ids
                            ORDER BY id_expediente, fecha DESC
                        """), {"ids": tuple(all_ids)}).fetchall()
                        for m_row in motivos_res:
                            last_pase_motivos[m_row[0]] = m_row[1] or "Sin Motivo"
                except Exception as e:
                    logger.error(f"Error querying last pase motivos: {e}")

                archive_mailboxes = {
                    'ARCHIVODGTAL', 'DGSOCAI-ARCHIVO', 'MGEYA-ARCHIVO', 'PG-ARCHIVO',
                    'SECGDU-ARCHIVODESPACHO', 'SECLYT-ARCHIVO', 'SSGDU-ARCHIVODESPACHO', 'SSGU-ARCHIVODESPACHO',
                    'DGROC-ARCHIVO', 'DGROC-OBSOBRAPREARCHIVO'
                }
                
                # Chequear permisos de acceso específicos a buzones
                allowed_mailboxes = None
                try:
                    with engine.connect() as conn:
                        # 1. Por usuario
                        res_user = conn.execute(text("SELECT buzones FROM public.cfg_buzones_analisis_acceso WHERE tipo_sujeto = 'usuario' AND nombre_sujeto = :n"), {"n": current_user.username}).fetchone()
                        if res_user:
                            allowed_mailboxes = set(res_user[0])
                        else:
                            # 2. Por rol
                            res_role = conn.execute(text("SELECT buzones FROM public.cfg_buzones_analisis_acceso WHERE tipo_sujeto = 'rol' AND nombre_sujeto = :r"), {"r": current_user.role}).fetchone()
                            if res_role:
                                allowed_mailboxes = set(res_role[0])
                except Exception as db_err:
                    logger.error(f"Error checking allowed mailboxes: {db_err}")

                by_analyst = {}
                for r in rows:
                    username = r["analista"] or "SIN_ASIGNAR"
                    if allowed_mailboxes is not None and username not in allowed_mailboxes:
                        continue # Filtrar por permisos
                        
                    name = r["analista_nombre"] or "Sin Asignar"
                    
                    id_exp = r["id_expediente"]
                    if id_exp in resolved_locations:
                        ubic = resolved_locations[id_exp]
                    elif r["analista"] in archive_mailboxes:
                        ubic = "EGRESADO"
                    else:
                        ubic = "STOCK PROPIO"

                    fecha_ing = r["fecha_primer_ingreso_gerencia"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_primer_ingreso_gerencia"] and hasattr(r["fecha_primer_ingreso_gerencia"], "strftime") else (str(r["fecha_primer_ingreso_gerencia"])[:19] if r["fecha_primer_ingreso_gerencia"] else None)
                    fecha_pase = r["fecha_recepcion_analista"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_recepcion_analista"] and hasattr(r["fecha_recepcion_analista"], "strftime") else (str(r["fecha_recepcion_analista"])[:19] if r["fecha_recepcion_analista"] else None)
                    caratula = r["fecha_creacion"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_creacion"] and hasattr(r["fecha_creacion"], "strftime") else (str(r["fecha_creacion"])[:19] if r["fecha_creacion"] else None)
                    
                    exp_item = {
                        "id_expediente": r["id_expediente"],
                        "expediente": r["expediente"],
                        "fecha_ing": fecha_ing,
                        "fecha_ultimo_pase": fecha_pase,
                        "dias": r["dias_en_poder_actual"] if r["dias_en_poder_actual"] is not None else 0,
                        "trata": r["trata"],
                        "caratula": caratula,
                        "descripcion_trata": r["descripcion_trata"] or r["descripcion"] or "S/D",
                        "estado_expediente": r["estado_expediente"] or "S/D",
                        "dias_en_gerencia": r["dias_en_gerencia"] if r["dias_en_gerencia"] is not None else 0,
                        "estado_tablero": ubic,
                        "trata_en_tablero": (ubic != "FUERA DE TABLERO"),
                        "motivo_pase": last_pase_motivos.get(r["id_expediente"], "Sin Motivo")
                    }
                    
                    if username not in by_analyst:
                        by_analyst[username] = {
                            "username": username,
                            "name": name,
                            "count": 0,
                            "expedientes": []
                        }
                    by_analyst[username]["expedientes"].append(exp_item)
                    by_analyst[username]["count"] += 1
                
                requested_mailboxes = [
                    'ARCHIVODGTAL', 'DGIUR-PREARCHIVO', 'DGIUR-SGUI', 'DGROC-ANTECEDENTESRLM', 'DGROC-APTOSGRYCO', 
                    'DGROC-ARCHIVO', 'DGROC-ARI', 'DGROC-CIC', 'DGROC-CONTABLE', 'DGROC-COPIAPLANO', 
                    'DGROC-DCATAT', 'DGROC-DCATDES', 'DGROC-DCATPOL', 'DGROC-DCATRUD', 'DGROC-DCATTIT', 
                    'DGROC-DCG', 'DGROC-DCIDITI', 'DGROC-DCOBAAYFO', 'DGROC-DCOBLEG', 'DGROC-DCOBREG', 
                    'DGROC-DCOBREGD', 'DGROC-DESCARGOS', 'DGROC-DGROCARI', 'DGROC-DGROCDES', 'DGROC-DGROCRRHH', 
                    'DGROC-DTACONT', 'DGROC-DTADES', 'DGROC-DTARPS', 'DGROC-ELEVADORES', 'DGROC-ESPERAINSTALACIONES', 
                    'DGROC-FICHA_PARCELARIA', 'DGROC-GO', 'DGROC-LEGAJOS', 'DGROC-LEGAJOSAUTOMAT', 'DGROC-LEY104', 
                    'DGROC-MESADES', 'DGROC-MESAMIDI', 'DGROC-MESAMIDINST', 'DGROC-MESAMIDINSTINCENDIO', 
                    'DGROC-MESAMIPVO', 'DGROC-OBRASADMIN', 'DGROC-OBRASENCURSO', 'DGROC-OBRASTECNICA', 'DGROC-OBSINCENDIO', 
                    'DGROC-OBSOBRAPREARCHIVO', 'DGROC-OBSPREARCHAYFO', 'DGROC-OBSREGISTRO', 'DGROC-PENDIENTESDEPAGO', 
                    'DGROC-RECHAZADOSLEGAJOS', 'DGROC-REVISIONCONTABLE', 'DGROC-SEDR', 'DGROC-SEDRI', 'DGROC-SGUI', 
                    'DGROC-TERMICAS', 'DGSOCAI-ARCHIVO', 'MGEYA-ARCHIVO', 'MGEYA-DCG', 'PG-ARCHIVO', 
                    'SECGDU-ARCHIVODESPACHO', 'SECLYT-ARCHIVO', 'SSGDU-ARCHIVODESPACHO', 'SSGU-ARCHIVODESPACHO'
                ]
                for mb in requested_mailboxes:
                    if allowed_mailboxes is not None and mb not in allowed_mailboxes:
                        continue # Filtrar por permisos
                    if mb not in by_analyst:
                        by_analyst[mb] = {
                            "username": mb,
                            "name": mb,
                            "count": 0,
                            "expedientes": []
                        }
                return list(by_analyst.values())
        except Exception as e:
            logger.error(f"Error en get_gerencia_buzones (analisis_archivo): {e}")
            raise HTTPException(status_code=500, detail=str(e))

    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
        
    try:
        with engine.connect() as conn:
            sql = f"""
                SELECT 
                    s.id_expediente, 
                    s.expediente, 
                    s.fecha_primer_ingreso_gerencia, 
                    s.fecha_recepcion_analista, 
                    s.dias_en_poder_actual, 
                    s.analista, 
                    COALESCE(du.apellido_nombre, s.analista) as analista_nombre, 
                    s.trata, 
                    ext.fecha_creacion,
                    COALESCE(
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE trata_reporte = s.trata AND gerencia = :g LIMIT 1),
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE s.trata = ANY(tratas_incluidas) AND gerencia = :g LIMIT 1),
                        ext.descripcion_trata
                    ) as descripcion_trata, 
                    ext.descripcion, 
                    ext.estado as estado_expediente,
                    (CURRENT_DATE - s.fecha_primer_ingreso_gerencia::date) as dias_en_gerencia,
                    s.ubicacion
                FROM (
                    SELECT id_expediente, expediente, fecha_primer_ingreso_gerencia, fecha_recepcion_analista, dias_en_poder_actual, analista, trata, 'STOCK PROPIO' as ubicacion
                    FROM mv_{gerencia_clean}_stock_propio
                    UNION ALL
                    SELECT id_expediente, expediente, fecha_primer_ingreso_gerencia, fecha_recepcion_analista, dias_en_poder_actual, analista, trata, 'INTERVENCION' as ubicacion
                    FROM mv_{gerencia_clean}_intervenciones_stock
                ) s
                LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = s.id_expediente
                LEFT JOIN datos_usuario du ON s.analista = du.usuario
            """
            result = conn.execute(text(sql), {"g": gerencia_clean})
            rows = [dict(r._mapping) for r in result.fetchall()]
            
            by_analyst = {}
            for r in rows:
                username = r["analista"] or "SIN_ASIGNAR"
                name = r["analista_nombre"] or "Sin Asignar"
                
                fecha_ing = r["fecha_primer_ingreso_gerencia"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_primer_ingreso_gerencia"] and hasattr(r["fecha_primer_ingreso_gerencia"], "strftime") else (str(r["fecha_primer_ingreso_gerencia"])[:19] if r["fecha_primer_ingreso_gerencia"] else None)
                fecha_pase = r["fecha_recepcion_analista"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_recepcion_analista"] and hasattr(r["fecha_recepcion_analista"], "strftime") else (str(r["fecha_recepcion_analista"])[:19] if r["fecha_recepcion_analista"] else None)
                caratula = r["fecha_creacion"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_creacion"] and hasattr(r["fecha_creacion"], "strftime") else (str(r["fecha_creacion"])[:19] if r["fecha_creacion"] else None)
                
                exp_item = {
                    "id_expediente": r["id_expediente"],
                    "expediente": r["expediente"],
                    "fecha_ing": fecha_ing,
                    "fecha_ultimo_pase": fecha_pase,
                    "dias": r["dias_en_poder_actual"] if r["dias_en_poder_actual"] is not None else 0,
                    "trata": r["trata"],
                    "caratula": caratula,
                    "descripcion_trata": r["descripcion_trata"] or r["descripcion"] or "S/D",
                    "estado_expediente": r["estado_expediente"] or "S/D",
                    "dias_en_gerencia": r["dias_en_gerencia"] if r["dias_en_gerencia"] is not None else 0,
                    "estado_tablero": r["ubicacion"]
                }
                
                if username not in by_analyst:
                    by_analyst[username] = {
                        "username": username,
                        "name": name,
                        "count": 0,
                        "expedientes": []
                    }
                by_analyst[username]["expedientes"].append(exp_item)
                by_analyst[username]["count"] += 1
                
            return sorted(list(by_analyst.values()), key=lambda x: x["count"], reverse=True)
    except Exception as e:
        logger.error(f"Error fetching gerencia buzones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/secgdu/buzones/{username}/expedientes")
async def get_secgdu_buzon_expedientes(username: str, current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            sql = """
                SELECT 
                    up.id_expediente, 
                    ext.expediente, 
                    up.fecha_ultimo_pase as fecha_recepcion_analista,
                    up.fecha_ultimo_pase as fecha_primer_ingreso_gerencia, 
                    (CURRENT_DATE - up.fecha_ultimo_pase::date) as dias_en_poder_actual, 
                    ext.trata, 
                    ext.fecha_creacion,
                    ext.descripcion_trata, 
                    ext.descripcion, 
                    ext.estado as estado_expediente,
                    (CURRENT_DATE - up.fecha_ultimo_pase::date) as dias_en_gerencia
                FROM mv_ultimo_pase up
                JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = up.id_expediente
                WHERE up.destinatario_actual = :u
            """
            result = conn.execute(text(sql), {"u": username})
            rows = [dict(r._mapping) for r in result.fetchall()]
            
            rules_sql = """
                SELECT DISTINCT 
                    UNNEST(tratas_incluidas) AS trata,
                    UNNEST(acronimos_egreso) AS acronimo,
                    firmantes_egreso
                FROM public.cfg_gestion_metas
                WHERE trata_reporte <> 'INTERVENCIONES'
            """
            rules_res = conn.execute(text(rules_sql)).fetchall()
            rules_by_trata = {}
            for r_trata, r_acro, r_firm in rules_res:
                if r_trata not in rules_by_trata:
                    rules_by_trata[r_trata] = []
                rules_by_trata[r_trata].append((r_acro, r_firm))

            ids = [r["id_expediente"] for r in rows]
            gedos_by_exp = {}
            if ids:
                gedo_sql = """
                    SELECT id_expediente, acronimo, usuario_creador
                    FROM public.mvw_datos_gedo_secgdu
                    WHERE id_expediente IN :ids
                """
                gedo_res = conn.execute(text(gedo_sql), {"ids": tuple(ids)}).fetchall()
                for g_id, g_acro, g_user in gedo_res:
                    if g_id not in gedos_by_exp:
                        gedos_by_exp[g_id] = []
                    gedos_by_exp[g_id].append((g_acro, g_user))

            pending_activities = set()
            if ids:
                act_sql = """
                    SELECT DISTINCT ON (id_expediente) id_expediente, estado
                    FROM public.mvw_ee_actividades_secgdu
                    WHERE id_expediente IN :ids
                    ORDER BY id_expediente, fecha_alta DESC
                """
                act_res = conn.execute(text(act_sql), {"ids": tuple(ids)}).fetchall()
                for a_id, a_est in act_res:
                    if a_est == 'PENDIENTE':
                        pending_activities.add(a_id)

            last_pase_motivos = {}
            if ids:
                motivos_res = conn.execute(text("""
                    SELECT DISTINCT ON (id_expediente) id_expediente, motivo
                    FROM mvw_ee_pases_secgdu
                    WHERE id_expediente IN :ids
                    ORDER BY id_expediente, fecha DESC
                """), {"ids": tuple(ids)}).fetchall()
                for m_row in motivos_res:
                    last_pase_motivos[m_row[0]] = m_row[1] or "Sin Motivo"

            expedientes = []
            for r in rows:
                id_exp = r["id_expediente"]
                trata = r["trata"]
                
                is_efectivo = False
                if trata in rules_by_trata and id_exp in gedos_by_exp:
                    for r_acro, r_firm in rules_by_trata[trata]:
                        for g_acro, g_user in gedos_by_exp[id_exp]:
                            if g_acro == r_acro:
                                if not r_firm or g_user in r_firm:
                                    is_efectivo = True
                                    break
                        if is_efectivo:
                            break
                
                is_no_efectivo = (r["estado_expediente"] == 'Guarda Temporal' and not is_efectivo)
                
                if is_efectivo:
                    ubic = "EGRESADO"
                elif is_no_efectivo:
                    ubic = "EGRESADO (NO EFECTIVO)"
                elif id_exp in pending_activities:
                    ubic = "PENDIENTE DE ACTIVIDAD"
                else:
                    ubic = "EN STOCK"
                
                fecha_ing = r["fecha_primer_ingreso_gerencia"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_primer_ingreso_gerencia"] and hasattr(r["fecha_primer_ingreso_gerencia"], "strftime") else (str(r["fecha_primer_ingreso_gerencia"])[:19] if r["fecha_primer_ingreso_gerencia"] else None)
                fecha_pase = r["fecha_recepcion_analista"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_recepcion_analista"] and hasattr(r["fecha_recepcion_analista"], "strftime") else (str(r["fecha_recepcion_analista"])[:19] if r["fecha_recepcion_analista"] else None)
                caratula = r["fecha_creacion"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_creacion"] and hasattr(r["fecha_creacion"], "strftime") else (str(r["fecha_creacion"])[:19] if r["fecha_creacion"] else None)
                
                exp_item = {
                    "id_expediente": id_exp,
                    "expediente": r["expediente"],
                    "fecha_ing": fecha_ing,
                    "fecha_ultimo_pase": fecha_pase,
                    "dias": r["dias_en_poder_actual"] if r["dias_en_poder_actual"] is not None else 0,
                    "trata": trata,
                    "caratula": caratula,
                    "descripcion_trata": r["descripcion_trata"] or r["descripcion"] or "S/D",
                    "estado_expediente": r["estado_expediente"] or "S/D",
                    "dias_en_gerencia": r["dias_en_gerencia"] if r["dias_en_gerencia"] is not None else 0,
                    "estado_tablero": ubic,
                    "trata_en_tablero": True,
                    "motivo_pase": last_pase_motivos.get(id_exp, "Sin Motivo")
                }
                expedientes.append(exp_item)
                
            return expedientes
    except Exception as e:
        logger.error(f"Error en get_secgdu_buzon_expedientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/{gerencia}/intervenciones/detalle")
async def get_intervenciones_detalle(gerencia: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
    
    try:
        with engine.connect() as conn:
            if gerencia_clean in ['instalaciones', 'morfologia', 'contable', 'etapa_proyecto', 'catastro', 'aph', 'usos', 'regularizacion', 'aviso_obra']:
                # Consumimos de la nueva vista modular para intervenciones
                sql = f"""
                    SELECT trata, descripcion_trata as detalle, dias_en_poder_actual as dias_stock
                    FROM mv_{gerencia_clean}_intervenciones_stock
                """
                result = conn.execute(text(sql))
            else:
                # Consultamos directamente el stock actual usando la columna trata_reporte
                # Obtenemos primero la lista de analistas/buzones para esta gerencia (INTERVENCIONES)
                cfg_query = text("""
                    SELECT buzones_ingreso, analistas_oficiales 
                    FROM cfg_gestion_metas 
                    WHERE gerencia = :g AND trata_reporte = 'INTERVENCIONES'
                """)
                cfg_res = conn.execute(cfg_query, {"g": gerencia_clean}).fetchone()
                
                if not cfg_res: return []
                
                sector_whitelist = (cfg_res[0] or []) + (cfg_res[1] or [])
                if not sector_whitelist: return []

                sql = """
                    SELECT trata, descripcion as detalle, dias_ultimo_movimiento as dias_stock
                    FROM mvw_stock_actual_detalle
                    WHERE is_subs = 0 
                      AND gerencia = :g
                      AND trata_reporte = 'INTERVENCIONES'
                      AND analista_actual = ANY(:whitelist)
                """
                result = conn.execute(text(sql), {"g": gerencia_clean, "whitelist": sector_whitelist})
            
            rows = [dict(r._mapping) for r in result.fetchall()]
            if not rows: return []
            df = pd.DataFrame(rows)

            def get_range(d):
                if d < 15: return "Menos de 15 dias"
                if d <= 30: return "15 a 30 dias"
                if d <= 45: return "30 a 45 dias"
                if d <= 60: return "45 a 60 dias"
                if d <= 75: return "60 a 75 dias"
                if d <= 90: return "75 a 90 dias"
                return "Mas de 90 dias"

            df['rango'] = df['dias_stock'].apply(get_range)
            
            # Agrupar solo por trata para evitar duplicados por detalle
            # Primero obtenemos el mapeo de trata -> detalle (el primero que encuentre)
            trata_nombres = df.groupby('trata')['detalle'].first().to_dict()
            
            # Pivotear agrupando solo por trata y rango
            pivot = df.groupby(['trata', 'rango']).size().unstack(fill_value=0)
            
            ranges = ["Menos de 15 dias", "15 a 30 dias", "30 a 45 dias", "45 a 60 dias", "60 a 75 dias", "75 a 90 dias", "Mas de 90 dias"]
            for r in ranges:
                if r not in pivot.columns: pivot[r] = 0
            
            pivot['TOTAL'] = pivot.sum(axis=1)
            pivot = pivot.reset_index()
            
            # Reincorporar el nombre del detalle
            pivot['detalle'] = pivot['trata'].map(trata_nombres)
            
            return pivot.sort_values(by='TOTAL', ascending=False).to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error en intervenciones detalle: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/{gerencia}/tramite/{trata}/detalle_periodo")
async def get_tramite_detalle_periodo(
    gerencia: str, 
    trata: str, 
    periodo: str, 
    metrica: str, 
    current_user: User = Depends(get_current_user)
):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
        
    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
        
    # Normalizar periodo (por ejemplo, "2026-5" -> "2026-05")
    periodo_norm = periodo
    if '-' in periodo:
        parts = periodo.split('-')
        if len(parts) == 2:
            try:
                year = int(parts[0])
                month = int(parts[1])
                periodo_norm = f"{year:04d}-{month:02d}"
            except ValueError:
                pass
    try:
        with engine.connect() as conn:
            # 1. Obtener lista de tratas incluidas oficiales
            trata_codes = list(TRAMITES_CONFIG[gerencia_clean].keys())
            is_official = trata in [t for t in trata_codes if t != 'INTERVENCIONES']
            
            # 2. Definir la consulta según la métrica
            sql = ""
            params = {
                "periodo": periodo_norm,
                "trata": trata,
                "g": gerencia_clean
            }
            
            if trata == 'ALL':
                # Query all tratas for the gerencia
                if metrica == 'ING':
                    sql = f"""
                        SELECT 
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_ingreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            t.buzon AS "BUZON INGRESO",
                            e.usuario_modificador AS "ANALISTA",
                            e.descripcion_trata AS "DETALLE TRATA", 
                            e.descripcion AS "DESCRIPCION", 
                            e.estado AS "ESTADO"
                        FROM mv_{gerencia_clean}_ingresos_eventos t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        WHERE to_char(t.fecha_ingreso, 'YYYY-MM') = :periodo
                        ORDER BY t.fecha_ingreso DESC
                    """
                elif metrica == 'EGR_EF':
                    interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"
                    if gerencia_clean != 'contable':
                        sql = f"""
                            SELECT 
                                'OFICIAL' AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                t.documento_egreso AS "DOCUMENTO EGRESO/DESTINO", 
                                t.acronimo_egreso AS "ACRONIMO EGRESO", 
                                t.usuario_egreso AS "USUARIO EGRESO",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_gedos_egreso t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                            UNION ALL
                            SELECT 
                                'INTERVENCION' AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                t.destino_externo AS "DOCUMENTO EGRESO/DESTINO",
                                '' AS "ACRONIMO EGRESO",
                                t.usuario_que_envia AS "USUARIO EGRESO",
                                t.descripcion_trata AS "DETALLE TRATA",
                                e.estado AS "ESTADO"
                            FROM {interv_egr_table} t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                            ORDER BY 4 DESC
                        """
                    else:
                        sql = f"""
                            SELECT 
                                'OFICIAL' AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                t.documento_egreso AS "DOCUMENTO EGRESO/DESTINO", 
                                t.acronimo_egreso AS "ACRONIMO EGRESO", 
                                t.usuario_egreso AS "USUARIO EGRESO",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_gedos_egreso t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                            UNION ALL
                            SELECT 
                                'INTERVENCION' AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                t.destino_actual AS "DOCUMENTO EGRESO/DESTINO",
                                '' AS "ACRONIMO EGRESO",
                                '' AS "USUARIO EGRESO",
                                t.descripcion_trata AS "DETALLE TRATA",
                                e.estado AS "ESTADO"
                            FROM {interv_egr_table} t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                            ORDER BY 4 DESC
                        """
                elif metrica == 'EGR_NE':
                    sql = f"""
                        SELECT 
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_ultimo_movimiento, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA ULTIMO PASO",
                            t.poseedor_actual AS "DESTINATARIO/BUZON",
                            e.descripcion_trata AS "DETALLE TRATA", 
                            e.descripcion AS "DESCRIPCION", 
                            e.estado AS "ESTADO"
                        FROM mv_{gerencia_clean}_egresos_no_efectivos t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        WHERE to_char(t.fecha_ultimo_movimiento, 'YYYY-MM') = :periodo
                        ORDER BY t.fecha_ultimo_movimiento DESC
                    """
                elif metrica == 'EGR_TOT':
                    interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"
                    if gerencia_clean != 'contable':
                        sql = f"""
                            SELECT 
                                'EFECTIVO' AS "TIPO EGRESO",
                                'OFICIAL' AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                t.documento_egreso AS "DETALLE EGRESO (DOC/BUZON)",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_gedos_egreso t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                            UNION ALL
                            SELECT 
                                'EFECTIVO' AS "TIPO EGRESO",
                                'INTERVENCION' AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                t.destino_externo AS "DETALLE EGRESO (DOC/BUZON)",
                                t.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM {interv_egr_table} t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                            UNION ALL
                            SELECT 
                                'NO EFECTIVO' AS "TIPO EGRESO",
                                CASE WHEN t.trata = ANY(:tratas_oficiales) THEN 'OFICIAL' ELSE 'INTERVENCION' END AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_ultimo_movimiento, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                t.poseedor_actual AS "DETALLE EGRESO (DOC/BUZON)",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_egresos_no_efectivos t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_ultimo_movimiento, 'YYYY-MM') = :periodo
                            ORDER BY 5 DESC
                        """
                    else:
                        sql = f"""
                            SELECT 
                                'EFECTIVO' AS "TIPO EGRESO",
                                'OFICIAL' AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                t.documento_egreso AS "DETALLE EGRESO (DOC/BUZON)",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_gedos_egreso t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                            UNION ALL
                            SELECT 
                                'EFECTIVO' AS "TIPO EGRESO",
                                'INTERVENCION' AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                t.destino_actual AS "DETALLE EGRESO (DOC/BUZON)",
                                t.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM {interv_egr_table} t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                            UNION ALL
                            SELECT 
                                'NO EFECTIVO' AS "TIPO EGRESO",
                                CASE WHEN t.trata = ANY(:tratas_oficiales) THEN 'OFICIAL' ELSE 'INTERVENCION' END AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_ultimo_movimiento, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                t.poseedor_actual AS "DETALLE EGRESO (DOC/BUZON)",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_egresos_no_efectivos t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_ultimo_movimiento, 'YYYY-MM') = :periodo
                            ORDER BY 5 DESC
                        """
                    params["tratas_oficiales"] = trata_codes
                elif metrica == 'STOCK_PROPIO':
                    sql = f"""
                        SELECT 
                            'OFICIAL' AS "TIPO TRAMITE",
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                            t.dias_en_poder_actual AS "DIAS EN PODER", 
                            t.analista AS "ANALISTA",
                            e.descripcion_trata AS "DETALLE TRATA", 
                            e.descripcion AS "DESCRIPCION", 
                            e.estado AS "ESTADO"
                        FROM mv_{gerencia_clean}_stock_propio t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        UNION ALL
                        SELECT 
                            'INTERVENCION' AS "TIPO TRAMITE",
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                            t.dias_en_poder_actual AS "DIAS EN PODER", 
                            t.analista AS "ANALISTA",
                            t.descripcion_trata AS "DETALLE TRATA", 
                            e.descripcion AS "DESCRIPCION", 
                            e.estado AS "ESTADO"
                        FROM mv_{gerencia_clean}_intervenciones_stock t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        ORDER BY "DIAS EN PODER" DESC
                    """
                elif metrica == 'STOCK_SUBS':
                    sql = f"""
                        SELECT 
                            'OFICIAL' AS "TIPO TRAMITE",
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                            t.dias_en_poder_actual AS "DIAS EN PODER", 
                            t.analista AS "ANALISTA",
                            e.descripcion_trata AS "DETALLE TRATA", 
                            e.descripcion AS "DESCRIPCION", 
                            e.estado AS "ESTADO"
                        FROM mv_{gerencia_clean}_subsanaciones t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        UNION ALL
                        SELECT 
                            'INTERVENCION' AS "TIPO TRAMITE",
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                            t.dias_en_poder_actual AS "DIAS EN PODER", 
                            t.analista AS "ANALISTA",
                            t.descripcion_trata AS "DETALLE TRATA", 
                            e.descripcion AS "DESCRIPCION", 
                            e.estado AS "ESTADO"
                        FROM mv_{gerencia_clean}_intervenciones_subs t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        ORDER BY "DIAS EN PODER" DESC
                    """
                elif metrica == 'STOCK_TOTAL':
                    sql = f"""
                        SELECT 
                            'STOCK PROPIO' AS "TIPO STOCK",
                            'OFICIAL' AS "TIPO TRAMITE",
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                            t.dias_en_poder_actual AS "DIAS EN PODER", 
                            t.analista AS "ANALISTA",
                            e.descripcion_trata AS "DETALLE TRATA", 
                            e.estado AS "ESTADO"
                        FROM mv_{gerencia_clean}_stock_propio t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        UNION ALL
                        SELECT 
                            'STOCK PROPIO' AS "TIPO STOCK",
                            'INTERVENCION' AS "TIPO TRAMITE",
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                            t.dias_en_poder_actual AS "DIAS EN PODER", 
                            t.analista AS "ANALISTA",
                            t.descripcion_trata AS "DETALLE TRATA", 
                            e.estado AS "ESTADO"
                        FROM mv_{gerencia_clean}_intervenciones_stock t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        UNION ALL
                        SELECT 
                            'SUBSANACION' AS "TIPO STOCK",
                            'OFICIAL' AS "TIPO TRAMITE",
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                            t.dias_en_poder_actual AS "DIAS EN PODER", 
                            t.analista AS "ANALISTA",
                            e.descripcion_trata AS "DETALLE TRATA", 
                            e.estado AS "ESTADO"
                        FROM mv_{gerencia_clean}_subsanaciones t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        UNION ALL
                        SELECT 
                            'SUBSANACION' AS "TIPO STOCK",
                            'INTERVENCION' AS "TIPO TRAMITE",
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                            t.dias_en_poder_actual AS "DIAS EN PODER", 
                            t.analista AS "ANALISTA",
                            t.descripcion_trata AS "DETALLE TRATA", 
                            e.estado AS "ESTADO"
                        FROM mv_{gerencia_clean}_intervenciones_subs t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        ORDER BY 7 DESC
                    """
                else:
                    raise HTTPException(status_code=400, detail="Métrica no soportada.")
            else:
                if metrica == 'ING':
                    sql = f"""
                        SELECT 
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_ingreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            t.buzon AS "BUZON INGRESO",
                            e.usuario_modificador AS "ANALISTA",
                            e.descripcion_trata AS "DETALLE TRATA", 
                            e.descripcion AS "DESCRIPCION", 
                            e.estado AS "ESTADO"
                        FROM mv_{gerencia_clean}_ingresos_eventos t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        WHERE to_char(t.fecha_ingreso, 'YYYY-MM') = :periodo
                          AND (:trata = 'INTERVENCIONES' AND t.trata NOT IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = :g)
                               OR :trata != 'INTERVENCIONES' AND t.trata = :trata)
                        ORDER BY t.fecha_ingreso DESC
                    """
                    
                elif metrica == 'EGR_EF':
                    if is_official:
                        sql = f"""
                            SELECT 
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                t.documento_egreso AS "DOCUMENTO EGRESO", 
                                t.acronimo_egreso AS "ACRONIMO EGRESO", 
                                t.usuario_egreso AS "USUARIO EGRESO",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.descripcion AS "DESCRIPCION", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_gedos_egreso t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                              AND t.trata = :trata
                            ORDER BY t.fecha_egreso DESC
                        """
                    else:
                        # Intervenciones
                        interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"
                        
                        if gerencia_clean != 'contable':
                            sql = f"""
                                SELECT 
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.usuario_que_envia AS "USUARIO QUE ENVIA", 
                                    t.destino_externo AS "DESTINO EXTERNO",
                                    t.descripcion_trata AS "DETALLE TRATA",
                                    e.descripcion AS "DESCRIPCION", 
                                    e.estado AS "ESTADO"
                                FROM {interv_egr_table} t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                ORDER BY t.fecha_egreso DESC
                            """
                        else:
                            sql = f"""
                                SELECT 
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.destino_actual AS "DESTINO ACTUAL", 
                                    t.dias_afuera AS "DIAS AFUERA",
                                    t.descripcion_trata AS "DETALLE TRATA",
                                    e.descripcion AS "DESCRIPCION", 
                                    e.estado AS "ESTADO"
                                FROM {interv_egr_table} t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                ORDER BY t.fecha_egreso DESC
                            """
                            
                elif metrica == 'EGR_NE':
                    sql = f"""
                        SELECT 
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_ultimo_movimiento, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA ULTIMO PASO",
                            t.poseedor_actual AS "DESTINATARIO/BUZON",
                            e.descripcion_trata AS "DETALLE TRATA", 
                            e.descripcion AS "DESCRIPCION", 
                            e.estado AS "ESTADO"
                        FROM mv_{gerencia_clean}_egresos_no_efectivos t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        WHERE to_char(t.fecha_ultimo_movimiento, 'YYYY-MM') = :periodo
                          AND (:trata = 'INTERVENCIONES' AND t.trata NOT IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = :g)
                               OR :trata != 'INTERVENCIONES' AND t.trata = :trata)
                        ORDER BY t.fecha_ultimo_movimiento DESC
                    """
                    
                elif metrica == 'EGR_TOT':
                    if is_official:
                        sql = f"""
                            SELECT 
                                'EFECTIVO' AS "TIPO EGRESO",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                t.documento_egreso AS "DOCUMENTO EGRESO",
                                t.acronimo_egreso AS "ACRONIMO EGRESO",
                                t.documento_egreso AS "DETALLE EGRESO (DOC/BUZON)",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_gedos_egreso t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                              AND t.trata = :trata
                            UNION ALL
                            SELECT 
                                'NO EFECTIVO' AS "TIPO EGRESO",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_ultimo_movimiento, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                '' AS "DOCUMENTO EGRESO",
                                '' AS "ACRONIMO EGRESO",
                                t.poseedor_actual AS "DETALLE EGRESO (DOC/BUZON)",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_egresos_no_efectivos t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_ultimo_movimiento, 'YYYY-MM') = :periodo
                              AND t.trata = :trata
                            ORDER BY 4 DESC
                        """
                    else:
                        interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"
                        sql = f"""
                            SELECT 
                                'EFECTIVO' AS "TIPO EGRESO",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                t.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM {interv_egr_table} t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                            UNION ALL
                            SELECT 
                                'NO EFECTIVO' AS "TIPO EGRESO",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_ultimo_movimiento, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_egresos_no_efectivos t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_ultimo_movimiento, 'YYYY-MM') = :periodo
                              AND t.trata NOT IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = :g)
                            ORDER BY 4 DESC
                        """
                    
                elif metrica == 'STOCK_PROPIO':
                    stock_table = f"mv_{gerencia_clean}_stock_propio" if is_official else f"mv_{gerencia_clean}_intervenciones_stock"
                    sql = f"""
                        SELECT 
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                            t.dias_en_poder_actual AS "DIAS EN PODER", 
                            t.analista AS "ANALISTA",
                            e.descripcion_trata AS "DETALLE TRATA", 
                            e.descripcion AS "DESCRIPCION", 
                            e.estado AS "ESTADO"
                        FROM {stock_table} t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        WHERE (:trata = 'INTERVENCIONES' OR t.trata = :trata)
                        ORDER BY t.dias_en_poder_actual DESC
                    """
                    
                elif metrica == 'STOCK_SUBS':
                    stock_table = f"mv_{gerencia_clean}_subsanaciones" if is_official else f"mv_{gerencia_clean}_intervenciones_subs"
                    sql = f"""
                        SELECT 
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                            t.dias_en_poder_actual AS "DIAS EN PODER", 
                            t.analista AS "ANALISTA",
                            e.descripcion_trata AS "DETALLE TRATA", 
                            e.descripcion AS "DESCRIPCION", 
                            e.estado AS "ESTADO"
                        FROM {stock_table} t
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                        WHERE (:trata = 'INTERVENCIONES' OR t.trata = :trata)
                        ORDER BY t.dias_en_poder_actual DESC
                    """
                    
                elif metrica == 'STOCK_TOTAL':
                    stock_table = f"mv_{gerencia_clean}_stock_propio" if is_official else f"mv_{gerencia_clean}_intervenciones_stock"
                    subs_table = f"mv_{gerencia_clean}_subsanaciones" if is_official else f"mv_{gerencia_clean}_intervenciones_subs"
                    sql = f"""
                        SELECT 
                            'STOCK PROPIO' AS "TIPO STOCK",
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                            t.dias_en_poder_actual AS "DIAS EN PODER", 
                            t.analista AS "ANALISTA",
                            e.descripcion_trata AS "DETALLE TRATA", 
                            e.estado AS "ESTADO"
                        FROM {stock_table} t
                        LEFT JOIN vw_expedientes_maestro e ON e.id_expediente = t.id_expediente
                        WHERE (:trata = 'INTERVENCIONES' OR t.trata = :trata)
                        UNION ALL
                        SELECT 
                            'SUBSANACION' AS "TIPO STOCK",
                            t.expediente AS "EXPEDIENTE", 
                            t.trata AS "TRAMITE", 
                            to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                            to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                            t.dias_en_poder_actual AS "DIAS EN PODER", 
                            t.analista AS "ANALISTA",
                            e.descripcion_trata AS "DETALLE TRATA", 
                            e.estado AS "ESTADO"
                        FROM {subs_table} t
                        LEFT JOIN vw_expedientes_maestro e ON e.id_expediente = t.id_expediente
                        WHERE (:trata = 'INTERVENCIONES' OR t.trata = :trata)
                        ORDER BY 6 DESC
                    """
                else:
                    raise HTTPException(status_code=400, detail="Métrica no soportada.")
                    
            result = conn.execute(text(sql), params)
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error en detalle_periodo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/cierre_mes")
async def get_cierre_mes(mes: str, current_user: User = Depends(get_current_user)):
    try:
        # 1. Parsear el mes recibido (Ej: "2026-05") y calcular el anterior y el interanual
        try:
            parts = mes.split('-')
            year = int(parts[0])
            month = int(parts[1])
            dt_first = date(year, month, 1)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato de mes inválido. Usar YYYY-MM")

        if dt_first.month == 1:
            prev_dt = date(dt_first.year - 1, 12, 1)
        else:
            prev_dt = date(dt_first.year, dt_first.month - 1, 1)
            
        prev_mes = f"{prev_dt.year}-{str(prev_dt.month).zfill(2)}"
        
        # Mismo mes del año anterior (YoY)
        yoy_dt = date(dt_first.year - 1, dt_first.month, 1)
        yoy_mes = f"{yoy_dt.year}-{str(yoy_dt.month).zfill(2)}"
        
        target_date_str = f"{dt_first.year}-{str(dt_first.month).zfill(2)}-01"


        response_data = {
            "periodo": mes,
            "periodo_previo": prev_mes,
            "periodo_yoy": yoy_mes,
            "totales": {
                "ingresos": 0, "ingresos_prev": 0, "ingresos_yoy": 0,
                "egresos": 0, "egresos_prev": 0, "egresos_yoy": 0,
                "stock": 0, "stock_prev": 0, "stock_yoy": 0,
                "subsanaciones": 0, "subsanaciones_prev": 0, "subsanaciones_yoy": 0,
                "meta": 0, "cumplido": False
            },
            "gerencias": {}
        }

        with engine.connect() as conn:
            for g, config in TRAMITES_CONFIG.items():
                g_clean = g.lower()
                trata_codes = list(config.keys())
                tratas_oficiales = [t for t in trata_codes if t != 'INTERVENCIONES']
                interv_egr_table = f"mv_{g_clean}_interv_egresos_eventos" if g_clean != 'contable' else "mv_contable_intervenciones_egresadas"
                interv_stock_table = f"mv_{g_clean}_intervenciones_stock"
                interv_subs_table = f"mv_{g_clean}_intervenciones_subs"

                # A. Obtener Metas de la Planificación Oficial para el mes (solo desde Mayo 2026 en adelante)
                metas_plan = {}
                if mes >= '2026-05':
                    try:
                        meta_res = conn.execute(text(f"SELECT TRIM(trata) as trata, COALESCE(egresos_totales_plan, 0) FROM mv_plan_metas_{g_clean} WHERE mes_calendario = :target"), {"target": target_date_str}).fetchall()
                        for r in meta_res:
                            metas_plan[r[0].upper()] = float(r[1])
                    except Exception:
                        pass

                    # Fallback: si no hay metas de planificación unificadas para el mes seleccionado,
                    # calcular una meta estimada basada en la mediana de los últimos 6 meses
                    if not metas_plan:
                        for t_code in trata_codes:
                            metas_plan[t_code.upper()] = calculate_trata_expected_egresos(conn, g_clean, t_code)

                # B. Obtener Ingresos (Mes Objetivo vs Mes Previo vs Mes YoY)
                ingresos = {}
                ingresos_prev = {}
                ingresos_yoy = {}
                try:
                    ing_res = conn.execute(text(f"""
                        SELECT 
                            CASE WHEN TRIM(trata) = ANY(:tratas_oficiales) THEN TRIM(trata) ELSE 'INTERVENCIONES' END as trata, 
                            to_char(fecha_ingreso, 'YYYY-MM') as mes_lbl, 
                            COUNT(*) 
                        FROM mv_{g_clean}_ingresos_eventos 
                        WHERE to_char(fecha_ingreso, 'YYYY-MM') IN (:m, :pm, :yoy) 
                        GROUP BY 1, 2
                    """), {"m": mes, "pm": prev_mes, "yoy": yoy_mes, "tratas_oficiales": tratas_oficiales}).fetchall()
                    for r in ing_res:
                        t_code = r[0].upper()
                        if r[1] == mes:
                            ingresos[t_code] = r[2]
                        elif r[1] == prev_mes:
                            ingresos_prev[t_code] = r[2]
                        elif r[1] == yoy_mes:
                            ingresos_yoy[t_code] = r[2]
                except Exception:
                    pass
 
                # C. Obtener Egresos Efectivos (Mes Objetivo vs Mes Previo vs Mes YoY)
                egr_ef = {}
                egr_ef_prev = {}
                egr_ef_yoy = {}
                try:
                    # Oficiales
                    e_res = conn.execute(text(f"SELECT TRIM(trata) as trata, to_char(fecha_egreso, 'YYYY-MM') as mes_lbl, COUNT(*) FROM mv_{g_clean}_gedos_egreso WHERE to_char(fecha_egreso, 'YYYY-MM') IN (:m, :pm, :yoy) GROUP BY 1, 2"), {"m": mes, "pm": prev_mes, "yoy": yoy_mes}).fetchall()
                    for r in e_res:
                        t_code = r[0].upper()
                        if r[1] == mes:
                            egr_ef[t_code] = r[2]
                        elif r[1] == prev_mes:
                            egr_ef_prev[t_code] = r[2]
                        elif r[1] == yoy_mes:
                            egr_ef_yoy[t_code] = r[2]
                            
                    # Intervenciones
                    i_res = conn.execute(text(f"SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_lbl, COUNT(*) FROM {interv_egr_table} WHERE to_char(fecha_egreso, 'YYYY-MM') IN (:m, :pm, :yoy) GROUP BY 1"), {"m": mes, "pm": prev_mes, "yoy": yoy_mes}).fetchall()
                    for r in i_res:
                        if r[0] == mes:
                            egr_ef['INTERVENCIONES'] = r[1]
                        elif r[0] == prev_mes:
                            egr_ef_prev['INTERVENCIONES'] = r[1]
                        elif r[0] == yoy_mes:
                            egr_ef_yoy['INTERVENCIONES'] = r[1]
                except Exception:
                    pass
 
                # D. Obtener Egresos No Efectivos (Mes Objetivo vs Mes Previo vs Mes YoY)
                egr_ne = {}
                egr_ne_prev = {}
                egr_ne_yoy = {}
                try:
                    ne_res = conn.execute(text(f"""
                        SELECT 
                            CASE WHEN TRIM(trata) = ANY(:tratas_oficiales) THEN TRIM(trata) ELSE 'INTERVENCIONES' END as trata, 
                            to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_lbl, 
                            COUNT(*) 
                        FROM mv_{g_clean}_egresos_no_efectivos 
                        WHERE to_char(fecha_ultimo_movimiento, 'YYYY-MM') IN (:m, :pm, :yoy) 
                        GROUP BY 1, 2
                    """), {"m": mes, "pm": prev_mes, "yoy": yoy_mes, "tratas_oficiales": tratas_oficiales}).fetchall()
                    for r in ne_res:
                        t_code = r[0].upper()
                        if r[1] == mes:
                            egr_ne[t_code] = r[2]
                        elif r[1] == prev_mes:
                            egr_ne_prev[t_code] = r[2]
                        elif r[1] == yoy_mes:
                            egr_ne_yoy[t_code] = r[2]
                except Exception:
                    pass
 
                # E. Obtener Snapshots de Stock y Subsanación
                stock = {}
                stock_prev = {}
                stock_yoy = {}
                subs = {}
                subs_prev = {}
                subs_yoy = {}
                try:
                    st_res = conn.execute(text(f"""
                        SELECT 
                            CASE WHEN TRIM(trata) = ANY(:tratas_oficiales) THEN TRIM(trata) ELSE 'INTERVENCIONES' END as trata, 
                            categoria, 
                            mes_label, 
                            SUM(cant_expedientes) 
                        FROM mv_{g_clean}_stock_historico 
                        WHERE mes_label IN (:m, :pm, :yoy)
                        GROUP BY 1, 2, 3
                    """), {"m": mes, "pm": prev_mes, "yoy": yoy_mes, "tratas_oficiales": tratas_oficiales}).fetchall()
                    for r in st_res:
                        t_code = r[0].upper()
                        cat = r[1].upper() # 'STOCK_PROPIO' o 'SUBSANACION'
                        is_target = (r[2] == mes)
                        is_prev = (r[2] == prev_mes)
                        is_yoy = (r[2] == yoy_mes)
                        
                        if cat == 'STOCK_PROPIO':
                            if is_target: stock[t_code] = r[3]
                            elif is_prev: stock_prev[t_code] = r[3]
                            elif is_yoy: stock_yoy[t_code] = r[3]
                        elif cat == 'SUBSANACION':
                            if is_target: subs[t_code] = r[3]
                            elif is_prev: subs_prev[t_code] = r[3]
                            elif is_yoy: subs_yoy[t_code] = r[3]
                except Exception:
                    pass

                g_detalles = []
                g_tot_ing = 0; g_tot_ing_p = 0; g_tot_ing_y = 0
                g_tot_egr = 0; g_tot_egr_p = 0; g_tot_egr_y = 0
                g_tot_st = 0; g_tot_st_p = 0; g_tot_st_y = 0
                g_tot_sb = 0; g_tot_sb_p = 0; g_tot_sb_y = 0
                g_tot_meta = 0

                for t_id in trata_codes:
                    t_upper = t_id.upper()
                    
                    t_ing = ingresos.get(t_upper, 0)
                    t_ing_p = ingresos_prev.get(t_upper, 0)
                    t_ing_y = ingresos_yoy.get(t_upper, 0)
                    
                    t_egr = egr_ef.get(t_upper, 0) + egr_ne.get(t_upper, 0)
                    t_egr_p = egr_ef_prev.get(t_upper, 0) + egr_ne_prev.get(t_upper, 0)
                    t_egr_y = egr_ef_yoy.get(t_upper, 0) + egr_ne_yoy.get(t_upper, 0)
                    if t_upper == 'INTERVENCIONES':
                        t_egr = 0
                        t_egr_p = 0
                        t_egr_y = 0
                        
                    t_st = stock.get(t_upper, 0)
                    t_st_p = stock_prev.get(t_upper, 0)
                    t_st_y = stock_yoy.get(t_upper, 0)
                    
                    t_sb = subs.get(t_upper, 0)
                    t_sb_p = subs_prev.get(t_upper, 0)
                    t_sb_y = subs_yoy.get(t_upper, 0)
                    
                    t_meta = metas_plan.get(t_upper, 0)

                    # Acumular totales de gerencia
                    g_tot_ing += t_ing
                    g_tot_ing_p += t_ing_p
                    g_tot_ing_y += t_ing_y
                    
                    g_tot_egr += t_egr
                    g_tot_egr_p += t_egr_p
                    g_tot_egr_y += t_egr_y
                    
                    g_tot_st += t_st
                    g_tot_st_p += t_st_p
                    g_tot_st_y += t_st_y
                    
                    g_tot_sb += t_sb
                    g_tot_sb_p += t_sb_p
                    g_tot_sb_y += t_sb_y
                    
                    g_tot_meta += t_meta

                    g_detalles.append({
                        "trata": t_id,
                        "descripcion_trata": config[t_id]["nombre"] if t_id != 'INTERVENCIONES' else "Intervenciones Externas del Sector",
                        "ingresos": t_ing,
                        "ingresos_prev": t_ing_p,
                        "ingresos_yoy": t_ing_y,
                        "egresos": t_egr,
                        "egresos_prev": t_egr_p,
                        "egresos_yoy": t_egr_y,
                        "meta": t_meta,
                        "cumplio_meta": (t_egr >= t_meta) if t_meta > 0 else True,
                        "stock": t_st,
                        "stock_prev": t_st_p,
                        "stock_yoy": t_st_y,
                        "subsanaciones": t_sb,
                        "subsanaciones_prev": t_sb_p,
                        "subsanaciones_yoy": t_sb_y
                    })

                response_data["gerencias"][g_clean] = {
                    "totales": {
                        "ingresos": g_tot_ing, "ingresos_prev": g_tot_ing_p, "ingresos_yoy": g_tot_ing_y,
                        "egresos": g_tot_egr, "egresos_prev": g_tot_egr_p, "egresos_yoy": g_tot_egr_y,
                        "stock": g_tot_st, "stock_prev": g_tot_st_p, "stock_yoy": g_tot_st_y,
                        "subsanaciones": g_tot_sb, "subsanaciones_prev": g_tot_sb_p, "subsanaciones_yoy": g_tot_sb_y,
                        "meta": g_tot_meta,
                        "cumplido": (g_tot_egr >= g_tot_meta) if g_tot_meta > 0 else True
                    },
                    "detalles": g_detalles
                }

                # Acumular total general del tablero
                response_data["totales"]["ingresos"] += g_tot_ing
                response_data["totales"]["ingresos_prev"] += g_tot_ing_p
                response_data["totales"]["ingresos_yoy"] += g_tot_ing_y
                
                response_data["totales"]["egresos"] += g_tot_egr
                response_data["totales"]["egresos_prev"] += g_tot_egr_p
                response_data["totales"]["egresos_yoy"] += g_tot_egr_y
                
                response_data["totales"]["stock"] += g_tot_st
                response_data["totales"]["stock_prev"] += g_tot_st_p
                response_data["totales"]["stock_yoy"] += g_tot_st_y
                
                response_data["totales"]["subsanaciones"] += g_tot_sb
                response_data["totales"]["subsanaciones_prev"] += g_tot_sb_p
                response_data["totales"]["subsanaciones_yoy"] += g_tot_sb_y
                
                response_data["totales"]["meta"] += g_tot_meta

            # Evaluar cumplimiento general del tablero
            response_data["totales"]["cumplido"] = (response_data["totales"]["egresos"] >= response_data["totales"]["meta"]) if response_data["totales"]["meta"] > 0 else True

        return response_data
    except Exception as e:
        logger.error(f"Error en cierre_mes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/sla")
async def get_sla_report(gerencia: Optional[str] = 'ALL', current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            gerencias_to_query = []
            if gerencia and gerencia != 'ALL':
                g_clean = gerencia.lower()
                if g_clean == 'conforme':
                    g_clean = 'regularizacion'
                gerencias_to_query = [g_clean]
            else:
                gerencias_to_query = list(TRAMITES_CONFIG.keys())

            records = []
            for g_clean in gerencias_to_query:
                # Intentar leer de la nueva vista materializada
                try:
                    sql_tiempos = f"""
                        SELECT 
                            gerencia,
                            trata AS "COD TRATA",
                            tramite AS "DETALLE TRATA",
                            total_expedientes_egresados AS total_resueltos,
                            duracion_total_mediana AS duracion_total_mediana,
                            duracion_total_promedio AS duracion_total_promedio,
                            duracion_neta_mediana AS duracion_neta_mediana,
                            duracion_subsanaciones_mediana AS duracion_subsanaciones_mediana
                        FROM mv_tiempos_resolucion_{g_clean}
                    """
                    result = conn.execute(text(sql_tiempos))
                    for row in result:
                        row_dict = dict(row._mapping)
                        
                        # Mapear a los nombres esperados por el front antiguo como fallback
                        row_dict["mediana_dias"] = float(row_dict.get("duracion_total_mediana") or 0.0)
                        row_dict["promedio_dias"] = float(row_dict.get("duracion_total_mediana") or 0.0)
                        row_dict["total_resueltos"] = int(row_dict.get("total_resueltos") or 0)
                        
                        # Enriquecer con acrónimos
                        g_cfg = TRAMITES_CONFIG.get(g_clean, {})
                        t_code = row_dict["COD TRATA"]
                        t_cfg = g_cfg.get(t_code, {})
                        row_dict["acronimos"] = t_cfg.get("acronimos", "")
                        if t_cfg.get("nombre"):
                            row_dict["DETALLE TRATA"] = t_cfg.get("nombre")
                            
                        records.append(row_dict)
                except Exception as e:
                    logger.warning(f"No se pudo consultar mv_tiempos_resolucion_{g_clean}, usando fallback: {e}")
                    # Fallback a mvw_sla_tramites
                    sql_fallback = f"""
                        SELECT 
                            gerencia,
                            trata AS "COD TRATA",
                            descripcion_trata AS "DETALLE TRATA",
                            COUNT(*) AS total_resueltos,
                            ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dias_resolucion)::numeric, 1) AS mediana_dias,
                            ROUND(AVG(dias_resolucion)::numeric, 1) AS promedio_dias
                        FROM mvw_sla_tramites
                        WHERE gerencia = :g
                        GROUP BY gerencia, trata, descripcion_trata
                        ORDER BY trata
                    """
                    result = conn.execute(text(sql_fallback), {"g": g_clean})
                    for row in result:
                        row_dict = dict(row._mapping)
                        
                        # Asignar valores por defecto para los nuevos campos
                        row_dict["duracion_total_mediana"] = float(row_dict.get("mediana_dias") or 0.0)
                        row_dict["duracion_neta_mediana"] = float(row_dict.get("mediana_dias") or 0.0)
                        row_dict["duracion_subsanaciones_mediana"] = 0.0
                        row_dict["promedio_dias"] = float(row_dict.get("promedio_dias") or 0.0)
                        row_dict["total_resueltos"] = int(row_dict.get("total_resueltos") or 0)
                        
                        # Enriquecer acrónimos
                        g_cfg = TRAMITES_CONFIG.get(g_clean, {})
                        t_code = row_dict["COD TRATA"]
                        t_cfg = g_cfg.get(t_code, {})
                        row_dict["acronimos"] = t_cfg.get("acronimos", "")
                        if t_cfg.get("nombre"):
                            row_dict["DETALLE TRATA"] = t_cfg.get("nombre")
                            
                        records.append(row_dict)
            return records
    except Exception as e:
        logger.error(f"Error en reporte/sla: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/sla/expedientes")
async def get_sla_expedientes(
    gerencia: str,
    trata: str,
    current_user: User = Depends(get_current_user)
):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
        
    try:
        with engine.connect() as conn:
            sql = f"""
                WITH subs_dias AS (
                    SELECT 
                        id_expediente,
                        CASE 
                            WHEN COUNT(*) > 20 THEN 0
                            ELSE COALESCE(SUM(
                                CASE 
                                    WHEN fecha_alta IS NULL OR fecha_alta < '2015-01-01'::date THEN 0
                                    WHEN fecha_cierre IS NOT NULL THEN (fecha_cierre::date - fecha_alta::date)
                                    ELSE (CURRENT_DATE - fecha_alta::date)
                                END
                            ), 0)
                        END AS dias_subs
                    FROM (
                        SELECT DISTINCT id_expediente, fecha_alta, fecha_cierre
                        FROM mvw_ee_actividades_secgdu
                        WHERE nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                    ) t
                    GROUP BY id_expediente
                )
                SELECT 
                    '{gerencia_clean}'::text AS gerencia,
                    u.expediente AS "EXPEDIENTE",
                    u.trata AS "TRAMITE",
                    u.descripcion_trata AS "DETALLE TRATA",
                    to_char(u.fecha_creacion_ee, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA CARATULA",
                    to_char(e.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                    (e.fecha_egreso::date - u.fecha_creacion_ee::date) AS "DIAS BRUTOS",
                    COALESCE(s.dias_subs, 0) AS "DIAS SUBSANACION",
                    GREATEST(0, (e.fecha_egreso::date - u.fecha_creacion_ee::date) - COALESCE(s.dias_subs, 0)) AS "DIAS NETOS SLA"
                FROM mv_{gerencia_clean}_universo u
                INNER JOIN mv_{gerencia_clean}_egresos_efectivos e ON u.id_expediente = e.id_expediente
                LEFT JOIN subs_dias s ON u.id_expediente = s.id_expediente
                WHERE u.trata = :trata
                ORDER BY e.fecha_egreso DESC
            """
            result = conn.execute(text(sql), {"trata": trata})
            rows = [dict(row._mapping) for row in result.fetchall()]
            
            # Map for frontend expectations
            mapped_rows = []
            for r in rows:
                mapped_rows.append({
                    "gerencia": r["gerencia"],
                    "expediente": r["EXPEDIENTE"],
                    "trata": r["TRAMITE"],
                    "descripcion_trata": r["DETALLE TRATA"],
                    "fecha_caratula": r["FECHA CARATULA"],
                    "fecha_egreso": r["FECHA EGRESO"],
                    "dias_brutos": int(r["DIAS BRUTOS"] or 0),
                    "dias_subsanacion": int(r["DIAS SUBSANACION"] or 0),
                    "dias_netos_sla": int(r["DIAS NETOS SLA"] or 0)
                })
                
            return mapped_rows
    except Exception as e:
        logger.error(f"Error en reporte/sla/expedientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def normalize_expediente(exp_str: str) -> str:
    if not exp_str:
        return exp_str
    from urllib.parse import unquote
    clean_exp = unquote(exp_str).strip()
    parts = clean_exp.split('-')
    if len(parts) == 5:
        parts.insert(3, '   ')
    elif len(parts) >= 6:
        if parts[3].strip() == '':
            parts[3] = '   '
    return '-'.join(parts)

@app.get("/api/expediente/detalle")
async def get_expediente_detalle(
    expediente: str,
    current_user: User = Depends(get_current_user)
):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.connect() as conn:
            sql = """
                SELECT id_expediente, expediente, trata, descripcion_trata, estado, fecha_creacion,
                       COALESCE((
                           SELECT 
                               CASE 
                                   WHEN COUNT(*) > 20 THEN 0
                                   ELSE SUM(
                                       CASE 
                                           WHEN fecha_alta IS NULL OR fecha_alta < '2015-01-01'::date THEN 0
                                           WHEN fecha_cierre IS NOT NULL THEN (fecha_cierre::date - fecha_alta::date)
                                           ELSE (CURRENT_DATE - fecha_alta::date)
                                       END
                                   )
                               END
                           FROM (
                               SELECT DISTINCT fecha_alta, fecha_cierre
                               FROM mvw_ee_actividades_secgdu
                               WHERE id_expediente = vw_expedientes_maestro.id_expediente
                                 AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                           ) t
                       ), 0) AS dias_subsanacion,
                       COALESCE((
                           SELECT 
                               CASE 
                                   WHEN COUNT(*) > 20 THEN 0
                                   ELSE COUNT(*)
                               END
                           FROM (
                               SELECT DISTINCT fecha_alta, fecha_cierre
                               FROM mvw_ee_actividades_secgdu
                               WHERE id_expediente = vw_expedientes_maestro.id_expediente
                                 AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                           ) t
                       ), 0) AS cant_subsanaciones,
                       COALESCE((
                           SELECT dias_stock 
                           FROM mvw_stock_actual_detalle 
                           WHERE id_expediente = vw_expedientes_maestro.id_expediente 
                           LIMIT 1
                       ), 0) AS dias_stock
                FROM vw_expedientes_maestro
                WHERE expediente = :exp
            """
            res = conn.execute(text(sql), {"exp": clean_exp}).fetchone()
            
            if not res:
                raise HTTPException(status_code=404, detail="Expediente no encontrado.")
                
            r = res._mapping
            id_exp = r.get("id_expediente")
            trata = r.get("trata")
            expediente_nro = r.get("expediente")
            estado = r.get("estado")
            
            # Extract reparticion
            parts = expediente_nro.split('-')
            reparticion = parts[-1] if parts else ""
            
            # Resolve gerencia
            gerencia = None
            trata_upper = trata.strip().upper() if trata else ""
            trata_overrides = {
                "MDUG3001A": "etapa_proyecto",
                "MDUG0104A": "etapa_proyecto",
                "MDUG1501J": "etapa_proyecto",
                "MDUG0142A": "etapa_proyecto",
                "MDUG4003A": "etapa_proyecto"
            }
            
            if trata_upper in trata_overrides:
                gerencia = trata_overrides[trata_upper]
            else:
                for g, config in TRAMITES_CONFIG.items():
                    if trata_upper in config:
                        gerencia = g
                        break
            
            ubicacion = "EN FLUJO"
            analista = None
            fecha_movimiento = None
            
            if gerencia:
                # Stock Propio
                try:
                    sp = conn.execute(text(f"SELECT analista, fecha_recepcion_analista FROM mv_{gerencia}_stock_propio WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                    if sp:
                        ubicacion = "STOCK PROPIO"
                        analista = sp[0]
                        fecha_movimiento = sp[1]
                except Exception:
                    pass
                    
                # Subsanacion
                if ubicacion == "EN FLUJO":
                    try:
                        sub = conn.execute(text(f"SELECT analista, fecha_recepcion_analista FROM mv_{gerencia}_subsanaciones WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                        if sub:
                            ubicacion = "SUBSANACION"
                            analista = sub[0]
                            fecha_movimiento = sub[1]
                    except Exception:
                        pass
                        
                # Intervencion Stock
                if ubicacion == "EN FLUJO":
                    try:
                        sp_int = conn.execute(text(f"SELECT analista FROM mv_{gerencia}_intervenciones_stock WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                        if sp_int:
                            ubicacion = "STOCK PROPIO (INTERVENCION)"
                            analista = sp_int[0]
                    except Exception:
                        pass
                        
                # Intervencion Subsanacion
                if ubicacion == "EN FLUJO":
                    try:
                        sub_int = conn.execute(text(f"SELECT analista FROM mv_{gerencia}_intervenciones_subs WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                        if sub_int:
                            ubicacion = "SUBSANACION (INTERVENCION)"
                            analista = sub_int[0]
                    except Exception:
                        pass
                        
                # Egresado Efectivo
                if ubicacion == "EN FLUJO":
                    try:
                        egr_ef = conn.execute(text(f"SELECT usuario_egreso, fecha_egreso FROM mv_{gerencia}_gedos_egreso WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                        if egr_ef:
                            ubicacion = "EGRESADO"
                            analista = egr_ef[0]
                            fecha_movimiento = egr_ef[1]
                    except Exception:
                        pass
                        
                # Egresado No Efectivo
                if ubicacion == "EN FLUJO":
                    try:
                        egr_ne = conn.execute(text(f"SELECT poseedor_actual, fecha_ultimo_movimiento FROM mv_{gerencia}_egresos_no_efectivos WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                        if egr_ne:
                            ubicacion = "EGRESADO (NO EFECTIVO)"
                            analista = egr_ne[0]
                            fecha_movimiento = egr_ne[1]
                    except Exception:
                        pass
            
            # Check if it is currently in an archive mailbox
            if ubicacion == "EN FLUJO":
                try:
                    sql_up = "SELECT destinatario_actual, fecha_ultimo_pase FROM mv_ultimo_pase WHERE id_expediente = :id LIMIT 1"
                    up_row = conn.execute(text(sql_up), {"id": id_exp}).fetchone()
                    if up_row and up_row[0] in [
                        'ARCHIVODGTAL', 'DGIUR-PREARCHIVO', 'DGIUR-SGUI', 'DGROC-ANTECEDENTESRLM', 'DGROC-APTOSGRYCO', 
                        'DGROC-ARCHIVO', 'DGROC-ARI', 'DGROC-CIC', 'DGROC-CONTABLE', 'DGROC-COPIAPLANO', 
                        'DGROC-DCATAT', 'DGROC-DCATDES', 'DGROC-DCATPOL', 'DGROC-DCATRUD', 'DGROC-DCATTIT', 
                        'DGROC-DCG', 'DGROC-DCIDITI', 'DGROC-DCOBAAYFO', 'DGROC-DCOBLEG', 'DGROC-DCOBREG', 
                        'DGROC-DCOBREGD', 'DGROC-DESCARGOS', 'DGROC-DGROCARI', 'DGROC-DGROCDES', 'DGROC-DGROCRRHH', 
                        'DGROC-DTACONT', 'DGROC-DTADES', 'DGROC-DTARPS', 'DGROC-ELEVADORES', 'DGROC-ESPERAINSTALACIONES', 
                        'DGROC-FICHA_PARCELARIA', 'DGROC-GO', 'DGROC-LEGAJOS', 'DGROC-LEGAJOSAUTOMAT', 'DGROC-LEY104', 
                        'DGROC-MESADES', 'DGROC-MESAMIDI', 'DGROC-MESAMIDINST', 'DGROC-MESAMIDINSTINCENDIO', 
                        'DGROC-MESAMIPVO', 'DGROC-OBRASADMIN', 'DGROC-OBRASENCURSO', 'DGROC-OBRASTECNICA', 'DGROC-OBSINCENDIO', 
                        'DGROC-OBSOBRAPREARCHIVO', 'DGROC-OBSPREARCHAYFO', 'DGROC-OBSREGISTRO', 'DGROC-PENDIENTESDEPAGO', 
                        'DGROC-RECHAZADOSLEGAJOS', 'DGROC-REVISIONCONTABLE', 'DGROC-SEDR', 'DGROC-SEDRI', 'DGROC-SGUI', 
                        'DGROC-TERMICAS', 'DGSOCAI-ARCHIVO', 'MGEYA-ARCHIVO', 'MGEYA-DCG', 'PG-ARCHIVO', 
                        'SECGDU-ARCHIVODESPACHO', 'SECLYT-ARCHIVO', 'SSGDU-ARCHIVODESPACHO', 'SSGU-ARCHIVODESPACHO'
                    ]:
                        ubicacion = "EGRESADO"
                        analista = up_row[0]
                        fecha_movimiento = up_row[1]
                except Exception:
                    pass
            if ubicacion == "EN FLUJO" and not gerencia:
                ubicacion = "FUERA DE TABLERO"

            d_tramitacion = 0
            f_creacion = r.get("fecha_creacion")
            if f_creacion:
                if hasattr(f_creacion, "date"):
                    f_creacion_date = f_creacion.date()
                else:
                    f_creacion_date = datetime.strptime(str(f_creacion)[:10], "%Y-%m-%d").date()
                
                if ubicacion.startswith("EGRESADO") and fecha_movimiento:
                    if hasattr(fecha_movimiento, "date"):
                        f_mov_date = fecha_movimiento.date()
                    else:
                        f_mov_date = datetime.strptime(str(fecha_movimiento)[:10], "%Y-%m-%d").date()
                    d_tramitacion = (f_mov_date - f_creacion_date).days
                else:
                    d_tramitacion = (date.today() - f_creacion_date).days
            
            # Fetch custom ficha data
            ficha_estado = ""
            ficha_prioridad = ""
            ficha_row = conn.execute(text("SELECT estado, prioridad FROM expediente_fichas WHERE expediente = :exp"), {"exp": expediente_nro}).fetchone()
            if ficha_row:
                ficha_estado = ficha_row[0] or ""
                ficha_prioridad = ficha_row[1] or ""

            # Fetch last pase motivo
            motivo_pase = "Sin Motivo"
            try:
                mot_row = conn.execute(text("SELECT motivo FROM mvw_ee_pases_secgdu WHERE id_expediente = :id ORDER BY fecha DESC LIMIT 1"), {"id": id_exp}).fetchone()
                if mot_row and mot_row[0]:
                    motivo_pase = mot_row[0]
            except Exception:
                pass

            return {
                "id_expediente": id_exp,
                "expediente": expediente_nro,
                "trata": trata,
                "descripcion_trata": r.get("descripcion_trata"),
                "gerencia": gerencia.upper() if gerencia else reparticion,
                "estado": estado,
                "ubicacion": ubicacion,
                "analista": analista or "SIN ASIGNAR",
                "fecha_ultimo_pase": fecha_movimiento.strftime("%Y-%m-%d %H:%M:%S") if fecha_movimiento and hasattr(fecha_movimiento, "strftime") else (str(fecha_movimiento)[:19] if fecha_movimiento else None),
                "fecha_creacion": r.get("fecha_creacion").strftime("%Y-%m-%d %H:%M:%S") if r.get("fecha_creacion") and hasattr(r.get("fecha_creacion"), "strftime") else (str(r.get("fecha_creacion"))[:19] if r.get("fecha_creacion") else None),
                "dias_tramitacion": max(0, d_tramitacion),
                "dias_subsanacion": int(r.get("dias_subsanacion") or 0),
                "cant_subsanaciones": int(r.get("cant_subsanaciones") or 0),
                "dias_stock": int(r.get("dias_stock") or 0),
                "ficha_estado": ficha_estado,
                "ficha_prioridad": ficha_prioridad,
                "motivo_pase": motivo_pase,
                "trata_en_tablero": (ubicacion != "FUERA DE TABLERO")
            }
    except Exception as e:
        logger.error(f"Error in get_expediente_detalle: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/expediente/buscar")
async def buscar_expediente(
    anio: str,
    numero: str,
    reparticion: str,
    current_user: User = Depends(get_current_user)
):
    try:
        # Formatear el patrón de búsqueda (con y sin ceros a la izquierda)
        clean_num = numero.lstrip('0') or '0'
        pattern1 = f"EX-{anio}-{numero}-%-{reparticion}"
        pattern2 = f"EX-{anio}-{clean_num}-%-{reparticion}"
        
        with engine.connect() as conn:
            # 1. Buscar expediente en vw_expedientes_maestro
            sql = """
                SELECT id_expediente, expediente, trata, descripcion_trata, estado, fecha_creacion,
                       COALESCE((
                           SELECT 
                               CASE 
                                   WHEN COUNT(*) > 20 THEN 0
                                   ELSE SUM(
                                       CASE 
                                           WHEN fecha_alta IS NULL OR fecha_alta < '2015-01-01'::date THEN 0
                                           WHEN fecha_cierre IS NOT NULL THEN (fecha_cierre::date - fecha_alta::date)
                                           ELSE (CURRENT_DATE - fecha_alta::date)
                                       END
                                   )
                               END
                           FROM (
                               SELECT DISTINCT fecha_alta, fecha_cierre
                               FROM mvw_ee_actividades_secgdu
                               WHERE id_expediente = vw_expedientes_maestro.id_expediente
                                 AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                           ) t
                       ), 0) AS dias_subsanacion,
                       COALESCE((
                           SELECT 
                               CASE 
                                   WHEN COUNT(*) > 20 THEN 0
                                   ELSE COUNT(*)
                               END
                           FROM (
                               SELECT DISTINCT fecha_alta, fecha_cierre
                               FROM mvw_ee_actividades_secgdu
                               WHERE id_expediente = vw_expedientes_maestro.id_expediente
                                 AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                           ) t
                       ), 0) AS cant_subsanaciones,
                       COALESCE((
                           SELECT dias_stock 
                           FROM mvw_stock_actual_detalle 
                           WHERE id_expediente = vw_expedientes_maestro.id_expediente 
                           LIMIT 1
                       ), 0) AS dias_stock
                FROM vw_expedientes_maestro
                WHERE expediente LIKE :pattern1 OR expediente LIKE :pattern2
            """
            res = conn.execute(text(sql), {
                "pattern1": pattern1,
                "pattern2": pattern2
            }).fetchall()
            if not res:
                return []
            
            expedientes = []
            for row in res:
                r = row._mapping
                id_exp = r.get("id_expediente")
                trata = r.get("trata")
                expediente_nro = r.get("expediente")
                estado = r.get("estado")
                
                # Intentar obtener gerencia a partir del trata
                gerencia = None
                trata_upper = trata.strip().upper() if trata else ""
                trata_overrides = {
                    "MDUG3001A": "etapa_proyecto",
                    "MDUG0104A": "etapa_proyecto",
                    "MDUG1501J": "etapa_proyecto",
                    "MDUG0142A": "etapa_proyecto",
                    "MDUG4003A": "etapa_proyecto"
                }
                
                if trata_upper in trata_overrides:
                    gerencia = trata_overrides[trata_upper]
                else:
                    for g, config in TRAMITES_CONFIG.items():
                        if trata_upper in config:
                            gerencia = g
                            break
                
                ubicacion = "EN FLUJO"
                analista = None
                fecha_movimiento = None
                
                if gerencia:
                    # Consultar stock propio oficial
                    try:
                        sp = conn.execute(text(f"""
                            SELECT analista, fecha_recepcion_analista 
                            FROM mv_{gerencia}_stock_propio 
                            WHERE id_expediente = :id LIMIT 1
                        """), {"id": id_exp}).fetchone()
                        if sp:
                            ubicacion = "STOCK PROPIO"
                            analista = sp[0]
                            fecha_movimiento = sp[1]
                    except Exception:
                        pass
                        
                    # Consultar subsanaciones oficial
                    if ubicacion == "EN FLUJO":
                        try:
                            sub = conn.execute(text(f"""
                                SELECT analista, fecha_recepcion_analista 
                                FROM mv_{gerencia}_subsanaciones 
                                WHERE id_expediente = :id LIMIT 1
                            """), {"id": id_exp}).fetchone()
                            if sub:
                                ubicacion = "SUBSANACION"
                                analista = sub[0]
                                fecha_movimiento = sub[1]
                        except Exception:
                            pass
                            
                    # Consultar stock de intervenciones
                    if ubicacion == "EN FLUJO":
                        try:
                            sp_int = conn.execute(text(f"""
                                SELECT analista 
                                FROM mv_{gerencia}_intervenciones_stock 
                                WHERE id_expediente = :id LIMIT 1
                            """), {"id": id_exp}).fetchone()
                            if sp_int:
                                ubicacion = "STOCK PROPIO (INTERVENCION)"
                                analista = sp_int[0]
                        except Exception:
                            pass
                            
                    # Consultar subsanaciones de intervenciones
                    if ubicacion == "EN FLUJO":
                        try:
                            sub_int = conn.execute(text(f"""
                                SELECT analista 
                                FROM mv_{gerencia}_intervenciones_subs 
                                WHERE id_expediente = :id LIMIT 1
                            """), {"id": id_exp}).fetchone()
                            if sub_int:
                                ubicacion = "SUBSANACION (INTERVENCION)"
                                analista = sub_int[0]
                        except Exception:
                            pass
                            
                    # Consultar egreso efectivo
                    if ubicacion == "EN FLUJO":
                        try:
                            egr_ef = conn.execute(text(f"""
                                SELECT usuario_egreso, fecha_egreso 
                                FROM mv_{gerencia}_gedos_egreso 
                                WHERE id_expediente = :id LIMIT 1
                            """), {"id": id_exp}).fetchone()
                            if egr_ef:
                                ubicacion = "EGRESADO"
                                analista = egr_ef[0]
                                fecha_movimiento = egr_ef[1]
                        except Exception:
                            pass
                            
                    # Consultar egreso no efectivo
                    if ubicacion == "EN FLUJO":
                        try:
                            egr_ne = conn.execute(text(f"""
                                SELECT poseedor_actual, fecha_ultimo_movimiento 
                                FROM mv_{gerencia}_egresos_no_efectivos 
                                WHERE id_expediente = :id LIMIT 1
                            """), {"id": id_exp}).fetchone()
                            if egr_ne:
                                ubicacion = "EGRESADO (NO EFECTIVO)"
                                analista = egr_ne[0]
                                fecha_movimiento = egr_ne[1]
                        except Exception:
                            pass
                
                # Calculate dias_tramitacion
                d_tramitacion = 0
                f_creacion = r.get("fecha_creacion")
                if f_creacion:
                    if hasattr(f_creacion, "date"):
                        f_creacion_date = f_creacion.date()
                    else:
                        f_creacion_date = datetime.strptime(str(f_creacion)[:10], "%Y-%m-%d").date()
                    
                    if ubicacion.startswith("EGRESADO") and fecha_movimiento:
                        if hasattr(fecha_movimiento, "date"):
                            f_mov_date = fecha_movimiento.date()
                        else:
                            f_mov_date = datetime.strptime(str(fecha_movimiento)[:10], "%Y-%m-%d").date()
                        d_tramitacion = (f_mov_date - f_creacion_date).days
                    else:
                        d_tramitacion = (date.today() - f_creacion_date).days

                expedientes.append({
                    "id_expediente": id_exp,
                    "expediente": expediente_nro,
                    "trata": trata,
                    "descripcion_trata": r.get("descripcion_trata"),
                    "gerencia": gerencia.upper() if gerencia else reparticion,
                    "estado": estado,
                    "ubicacion": ubicacion,
                    "analista": analista or "SIN ASIGNAR",
                    "fecha_ultimo_pase": fecha_movimiento.strftime("%Y-%m-%d %H:%M:%S") if fecha_movimiento and hasattr(fecha_movimiento, "strftime") else (str(fecha_movimiento)[:19] if fecha_movimiento else None),
                    "fecha_creacion": r.get("fecha_creacion").strftime("%Y-%m-%d %H:%M:%S") if r.get("fecha_creacion") and hasattr(r.get("fecha_creacion"), "strftime") else (str(r.get("fecha_creacion"))[:19] if r.get("fecha_creacion") else None),
                    "dias_tramitacion": max(0, d_tramitacion),
                    "dias_subsanacion": int(r.get("dias_subsanacion") or 0),
                    "cant_subsanaciones": int(r.get("cant_subsanaciones") or 0),
                    "dias_stock": int(r.get("dias_stock") or 0)
                })
            return expedientes
    except Exception as e:
        logger.error(f"Error en buscar_expediente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class SearchRule(BaseModel):
    field: str
    operator: str
    value: Any

class AdvancedSearchRequest(BaseModel):
    conjunction: str
    rules: List[SearchRule]

@app.post("/api/expediente/buscar_avanzado")
async def buscar_expediente_avanzado(
    data: AdvancedSearchRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        conjunction = data.conjunction.upper()
        if conjunction not in ["AND", "OR"]:
            raise HTTPException(status_code=400, detail="Conjunción inválida. Debe ser AND u OR.")
            
        field_mapping = {
            "analista": "analista_actual",
            "dias_stock": "dias_stock",
            "gerencia": "gerencia",
            "trata": "trata",
            "is_subs": "is_subs"
        }
        
        op_mapping = {
            "eq": "=",
            "ne": "!=",
            "gt": ">",
            "gte": ">=",
            "lt": "<",
            "lte": "<=",
            "like": "LIKE"
        }

        where_clauses = []
        params = {}
        
        for i, rule in enumerate(data.rules):
            field = rule.field.lower()
            operator = rule.operator.lower()
            val = rule.value
            
            if field not in field_mapping:
                raise HTTPException(status_code=400, detail=f"Campo de búsqueda no permitido: {field}")
            if operator not in op_mapping:
                raise HTTPException(status_code=400, detail=f"Operador no permitido: {operator}")
                
            db_field = field_mapping[field]
            db_op = op_mapping[operator]
            param_name = f"val_{i}"
            
            if operator == "like":
                val = f"%{val}%"
                
            if field == "dias_stock":
                try:
                    val = int(val)
                except ValueError:
                    raise HTTPException(status_code=400, detail="El valor para dias_stock debe ser un número entero.")
            elif field == "is_subs":
                try:
                    val = int(val)
                except ValueError:
                    raise HTTPException(status_code=400, detail="El valor para is_subs debe ser 0 o 1.")
            else:
                val = str(val)
                
            where_clauses.append(f"{db_field} {db_op} :{param_name}")
            params[param_name] = val
            
        if not where_clauses:
            return []
            
        where_sql = f" {conjunction} ".join(where_clauses)
        
        sql = f"""
            SELECT id_expediente, expediente, trata, gerencia, is_subs, analista_actual as analista, dias_stock,
                   fecha_ing, fecha_ultimo_pase,
                    descripcion_trata,
                    estado,
                    fecha_creacion,
                   COALESCE((
                       SELECT 
                           CASE 
                               WHEN COUNT(*) > 20 THEN 0
                               ELSE SUM(
                                   CASE 
                                       WHEN fecha_alta IS NULL OR fecha_alta < '2015-01-01'::date THEN 0
                                       WHEN fecha_cierre IS NOT NULL THEN (fecha_cierre::date - fecha_alta::date)
                                       ELSE (CURRENT_DATE - fecha_alta::date)
                                   END
                               )
                           END
                       FROM (
                           SELECT DISTINCT fecha_alta, fecha_cierre
                           FROM mvw_ee_actividades_secgdu
                           WHERE id_expediente = mvw_stock_actual_detalle.id_expediente
                             AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                       ) t
                   ), 0) AS dias_subsanacion,
                   COALESCE((
                       SELECT 
                           CASE 
                               WHEN COUNT(*) > 20 THEN 0
                               ELSE COUNT(*)
                           END
                       FROM (
                           SELECT DISTINCT fecha_alta, fecha_cierre
                           FROM mvw_ee_actividades_secgdu
                           WHERE id_expediente = mvw_stock_actual_detalle.id_expediente
                             AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                       ) t
                   ), 0) AS cant_subsanaciones
            FROM mvw_stock_actual_detalle
            WHERE {where_sql}
        """
        
        with engine.connect() as conn:
            res = conn.execute(text(sql), params).fetchall()
            expedientes = []
            for row in res:
                r = row._mapping
                id_exp = r.get("id_expediente")
                expediente_nro = r.get("expediente")
                trata = r.get("trata")
                gerencia = r.get("gerencia")
                is_subs = r.get("is_subs")
                analista = r.get("analista")
                dias_stock = r.get("dias_stock")
                fecha_ing = r.get("fecha_ing")
                fecha_ultimo_pase = r.get("fecha_ultimo_pase")
                descripcion_trata = r.get("descripcion_trata")
                estado = r.get("estado")
                fecha_creacion = r.get("fecha_creacion")
                
                if is_subs == 1:
                    ubicacion = "SUBSANACION"
                else:
                    ubicacion = "STOCK PROPIO"
                    
                if gerencia:
                    trata_codes = list(TRAMITES_CONFIG.get(gerencia, {}).keys())
                    is_official = trata in [t for t in trata_codes if t != 'INTERVENCIONES']
                    if not is_official:
                        ubicacion += " (INTERVENCION)"
                
                # Calculate dias_tramitacion
                d_tramitacion = 0
                f_creacion = r.get("fecha_creacion")
                if f_creacion:
                    if hasattr(f_creacion, "date"):
                        f_creacion_date = f_creacion.date()
                    else:
                        f_creacion_date = datetime.strptime(str(f_creacion)[:10], "%Y-%m-%d").date()
                    d_tramitacion = (date.today() - f_creacion_date).days

                expedientes.append({
                    "id_expediente": id_exp,
                    "expediente": expediente_nro,
                    "trata": trata,
                    "descripcion_trata": descripcion_trata,
                    "gerencia": gerencia.upper() if gerencia else "-",
                    "estado": estado,
                    "ubicacion": ubicacion,
                    "analista": analista or "SIN ASIGNAR",
                    "fecha_ultimo_pase": fecha_ultimo_pase.strftime("%Y-%m-%d %H:%M:%S") if fecha_ultimo_pase and hasattr(fecha_ultimo_pase, "strftime") else (str(fecha_ultimo_pase)[:19] if fecha_ultimo_pase else None),
                    "fecha_creacion": fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if fecha_creacion and hasattr(fecha_creacion, "strftime") else (str(fecha_creacion)[:19] if fecha_creacion else None),
                    "dias_tramitacion": max(0, d_tramitacion),
                    "dias_subsanacion": int(r.get("dias_subsanacion") or 0),
                    "cant_subsanaciones": int(r.get("cant_subsanaciones") or 0),
                    "dias_stock": int(r.get("dias_stock") or 0)
                })
            return expedientes
    except Exception as e:
        logger.error(f"Error en buscar_expediente_avanzado: {e}")
        raise HTTPException(status_code=500, detail=str(e))
            
# --- Endpoints de Favoritos de Expedientes ---
# --- Endpoints de Favoritos de Expedientes ---
class FavoriteRequest(BaseModel):
    expediente: str
    folder_id: Optional[int] = None

class FolderCreateRequest(BaseModel):
    name: str

class MoveFavoriteRequest(BaseModel):
    expediente: str
    folder_id: Optional[int] = None

class FavoriteNoteRequest(BaseModel):
    note_text: str

@app.post("/api/expediente/favorito")
async def add_favorito(data: FavoriteRequest, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(data.expediente)
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO user_favorites (username, expediente, folder_id)
                VALUES (:u, :exp, :f_id)
                ON CONFLICT (username, expediente) DO UPDATE SET folder_id = EXCLUDED.folder_id
            """), {"u": current_user.username, "exp": clean_exp, "f_id": data.folder_id})
        return {"status": "ok", "message": "Expediente agregado a favoritos"}
    except Exception as e:
        logger.error(f"Error agregando favorito: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/expediente/favorito/{expediente}")
async def remove_favorito(expediente: str, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.begin() as conn:
            conn.execute(text("""
                DELETE FROM user_favorites 
                WHERE username = :u AND expediente = :exp
            """), {"u": current_user.username, "exp": clean_exp})
        return {"status": "ok", "message": "Expediente removido de favoritos"}
    except Exception as e:
        logger.error(f"Error eliminando favorito: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/expediente/favoritos")
async def get_favoritos(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            sql = """
                SELECT 
                    f.expediente,
                    f.folder_id,
                    et.id_expediente,
                    et.trata,
                    et.descripcion_trata,
                    et.estado,
                    et.fecha_creacion,
                    sad.analista_actual as analista,
                    sad.dias_stock,
                    sad.gerencia,
                    sad.is_subs,
                    sad.fecha_ultimo_pase,
                    COALESCE((
                        SELECT 
                            CASE 
                                WHEN COUNT(*) > 20 THEN 0
                                ELSE SUM(
                                    CASE 
                                        WHEN fecha_alta IS NULL OR fecha_alta < '2015-01-01'::date THEN 0
                                        WHEN fecha_cierre IS NOT NULL THEN (fecha_cierre::date - fecha_alta::date)
                                        ELSE (CURRENT_DATE - fecha_alta::date)
                                    END
                                )
                            END
                        FROM (
                            SELECT DISTINCT fecha_alta, fecha_cierre
                            FROM mvw_ee_actividades_secgdu
                            WHERE id_expediente = et.id_expediente
                              AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                        ) t
                    ), 0) AS dias_subsanacion,
                    COALESCE((
                        SELECT 
                            CASE 
                                WHEN COUNT(*) > 20 THEN 0
                                ELSE COUNT(*)
                              END
                        FROM (
                            SELECT DISTINCT fecha_alta, fecha_cierre
                            FROM mvw_ee_actividades_secgdu
                            WHERE id_expediente = et.id_expediente
                              AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                        ) t
                    ), 0) AS cant_subsanaciones,
                    (SELECT COUNT(*) FROM user_favorite_notes WHERE username = f.username AND expediente = f.expediente) AS cant_notas,
                    (SELECT note_text FROM user_favorite_notes WHERE username = f.username AND expediente = f.expediente ORDER BY created_at DESC LIMIT 1) AS ultima_nota_favorito,
                    ef.direccion AS ficha_direccion,
                    ef.responsable AS ficha_responsable,
                    u_resp.full_name AS ficha_responsable_name,
                    ef.estado AS ficha_estado,
                    ef.prioridad AS ficha_prioridad,
                    ef.proxima_reunion AS ficha_proxima_reunion,
                    (SELECT note_text FROM expediente_ficha_internal_notes WHERE expediente = f.expediente ORDER BY created_at DESC LIMIT 1) AS ficha_notas_internas,
                    (SELECT u.full_name FROM expediente_ficha_internal_notes n LEFT JOIN auth_users u ON n.username = u.username WHERE n.expediente = f.expediente ORDER BY n.created_at DESC LIMIT 1) AS ficha_notas_internas_author,
                    (SELECT n.created_at FROM expediente_ficha_internal_notes n WHERE n.expediente = f.expediente ORDER BY n.created_at DESC LIMIT 1) AS ficha_notas_internas_date
                FROM user_favorites f
                LEFT JOIN vw_expedientes_maestro et ON et.expediente = f.expediente
                LEFT JOIN mvw_stock_actual_detalle sad ON sad.id_expediente = et.id_expediente
                LEFT JOIN expediente_fichas ef ON ef.expediente = f.expediente
                LEFT JOIN auth_users u_resp ON u_resp.username = ef.responsable
                WHERE f.username = :username
                ORDER BY f.created_at DESC
            """
            
            res = conn.execute(text(sql), {"username": current_user.username}).fetchall()
            expedientes = []
            for row in res:
                r = row._mapping
                id_exp = r.get("id_expediente")
                expediente_nro = r.get("expediente")
                trata = r.get("trata")
                estado = r.get("estado")
                is_subs = r.get("is_subs")
                analista = r.get("analista")
                fecha_ultimo_pase = r.get("fecha_ultimo_pase")
                fecha_creacion = r.get("fecha_creacion")
                gerencia = r.get("gerencia")
                
                ubicacion = "EN FLUJO"
                if is_subs == 1:
                    ubicacion = "SUBSANACION"
                elif analista:
                    ubicacion = "STOCK PROPIO"
                
                if id_exp and gerencia:
                    try:
                        sp = conn.execute(text(f"SELECT analista FROM mv_{gerencia.lower()}_stock_propio WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                        if sp:
                            ubicacion = "STOCK PROPIO"
                            analista = sp[0]
                    except Exception:
                        pass
                        
                    if ubicacion == "EN FLUJO":
                        try:
                            sub = conn.execute(text(f"SELECT analista FROM mv_{gerencia.lower()}_subsanaciones WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                            if sub:
                                ubicacion = "SUBSANACION"
                                analista = sub[0]
                        except Exception:
                            pass
                
                d_tramitacion = 0
                if fecha_creacion:
                    if hasattr(fecha_creacion, "date"):
                        f_creacion_date = fecha_creacion.date()
                    else:
                        f_creacion_date = datetime.strptime(str(fecha_creacion)[:10], "%Y-%m-%d").date()
                    d_tramitacion = (date.today() - f_creacion_date).days
                
                expedientes.append({
                    "id_expediente": id_exp,
                    "expediente": expediente_nro,
                    "folder_id": r.get("folder_id"),
                    "trata": trata,
                    "descripcion_trata": r.get("descripcion_trata") or "S/D",
                    "gerencia": gerencia.upper() if gerencia else "-",
                    "estado": estado or "DESCONOCIDO",
                    "ubicacion": ubicacion,
                    "analista": analista or "SIN ASIGNAR",
                    "fecha_ultimo_pase": fecha_ultimo_pase.strftime("%Y-%m-%d %H:%M:%S") if fecha_ultimo_pase and hasattr(fecha_ultimo_pase, "strftime") else (str(fecha_ultimo_pase)[:19] if fecha_ultimo_pase else None),
                    "fecha_creacion": fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if fecha_creacion and hasattr(fecha_creacion, "strftime") else (str(fecha_creacion)[:19] if fecha_creacion else None),
                    "dias_tramitacion": max(0, d_tramitacion),
                    "dias_subsanacion": int(r.get("dias_subsanacion") or 0),
                    "cant_subsanaciones": int(r.get("cant_subsanaciones") or 0),
                    "dias_stock": int(r.get("dias_stock") or 0),
                    "cant_notas": int(r.get("cant_notas") or 0),
                    "ficha_direccion": r.get("ficha_direccion") or "",
                    "ficha_responsable": r.get("ficha_responsable") or "",
                    "ficha_responsable_name": r.get("ficha_responsable_name") or r.get("ficha_responsable") or "",
                    "ficha_estado": r.get("ficha_estado") or "",
                    "ficha_prioridad": r.get("ficha_prioridad") or "",
                    "ficha_proxima_reunion": bool(r.get("ficha_proxima_reunion")),
                    "ficha_notas_internas": r.get("ficha_notas_internas") or "",
                    "ficha_notas_internas_author": r.get("ficha_notas_internas_author") or "",
                    "ficha_notas_internas_date": r.get("ficha_notas_internas_date").strftime("%Y-%m-%d %H:%M:%S") if r.get("ficha_notas_internas_date") and hasattr(r.get("ficha_notas_internas_date"), "strftime") else (str(r.get("ficha_notas_internas_date"))[:19] if r.get("ficha_notas_internas_date") else ""),
                    "ultima_nota_favorito": r.get("ultima_nota_favorito") or ""
                })
            return expedientes
    except Exception as e:
        logger.error(f"Error listando favoritos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/expediente/favoritos/carpetas")
async def get_favoritos_carpetas(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            sql = """
                SELECT 
                    uf.id, 
                    uf.name,
                    (SELECT COUNT(*) FROM user_favorites WHERE folder_id = uf.id AND username = :u) as count
                FROM user_favorite_folders uf
                WHERE uf.username = :u
                ORDER BY uf.name ASC
            """
            res = conn.execute(text(sql), {"u": current_user.username}).fetchall()
            return [dict(r._mapping) for r in res]
    except Exception as e:
        logger.error(f"Error listando carpetas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/expediente/favoritos/carpetas")
async def create_favorito_carpeta(data: FolderCreateRequest, current_user: User = Depends(get_current_user)):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO user_favorite_folders (username, name)
                VALUES (:u, :name)
                ON CONFLICT (username, name) DO NOTHING
            """), {"u": current_user.username, "name": data.name})
        return {"status": "ok", "message": "Carpeta creada exitosamente"}
    except Exception as e:
        logger.error(f"Error creando carpeta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/expediente/favoritos/carpetas/{folder_id}")
async def delete_favorito_carpeta(folder_id: int, current_user: User = Depends(get_current_user)):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                DELETE FROM user_favorite_folders
                WHERE id = :fid AND username = :u
            """), {"fid": folder_id, "u": current_user.username})
        return {"status": "ok", "message": "Carpeta eliminada exitosamente"}
    except Exception as e:
        logger.error(f"Error eliminando carpeta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/expediente/favorito/mover")
async def move_favorito(data: MoveFavoriteRequest, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(data.expediente)
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE user_favorites
                SET folder_id = :fid
                WHERE username = :u AND expediente = :exp
            """), {"fid": data.folder_id, "u": current_user.username, "exp": clean_exp})
        return {"status": "ok", "message": "Favorito movido exitosamente"}
    except Exception as e:
        logger.error(f"Error moviendo favorito: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/expediente/favorito/{expediente}/notas")
async def get_favorito_notes(expediente: str, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.connect() as conn:
            sql = """
                SELECT 
                    n.id, 
                    n.note_text, 
                    n.created_at,
                    n.username,
                    u.full_name as author_name,
                    u.sector as author_sector
                FROM user_favorite_notes n
                LEFT JOIN auth_users u ON n.username = u.username
                WHERE n.expediente = :exp
                ORDER BY n.created_at DESC
            """
            res = conn.execute(text(sql), {"exp": clean_exp}).fetchall()
            return [{
                "id": r[0],
                "note_text": r[1],
                "created_at": r[2].strftime("%Y-%m-%d %H:%M:%S") if r[2] and hasattr(r[2], "strftime") else str(r[2])[:19],
                "username": r[3],
                "author_name": r[4] or r[3],
                "author_sector": r[5] or "-",
                "is_owner": r[3] == current_user.username
            } for r in res]
    except Exception as e:
        logger.error(f"Error listando notas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/expediente/favorito/{expediente}/notas")
async def create_favorito_nota(expediente: str, data: FavoriteNoteRequest, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.begin() as conn:
            # Verificar que el expediente está favoritado por este usuario
            fav = conn.execute(text("""
                SELECT 1 FROM user_favorites WHERE username = :u AND expediente = :exp
            """), {"u": current_user.username, "exp": clean_exp}).fetchone()
            if not fav:
                raise HTTPException(status_code=400, detail="El expediente debe estar agregado a favoritos para poder añadirle notas.")
            
            conn.execute(text("""
                INSERT INTO user_favorite_notes (username, expediente, note_text)
                VALUES (:u, :exp, :note)
            """), {"u": current_user.username, "exp": clean_exp, "note": data.note_text})
        return {"status": "ok", "message": "Nota guardada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando nota: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/expediente/favorito/notas/{note_id}")
async def delete_favorito_nota(note_id: int, current_user: User = Depends(get_current_user)):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                DELETE FROM user_favorite_notes
                WHERE id = :nid AND username = :u
            """), {"nid": note_id, "u": current_user.username})
        return {"status": "ok", "message": "Nota eliminada exitosamente"}
    except Exception as e:
        logger.error(f"Error eliminando nota: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class FichaEditRequest(BaseModel):
    direccion: Optional[str] = None
    notas_internas: Optional[str] = None
    responsable: Optional[str] = None
    estado: Optional[str] = None
    prioridad: Optional[str] = None
    proxima_reunion: Optional[bool] = False

@app.get("/api/usuarios-tablero")
async def list_usuarios_tablero(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT username, full_name FROM auth_users ORDER BY full_name"))
            return [{"username": r.username, "full_name": r.full_name or r.username} for r in result]
    except Exception as e:
        logger.error(f"Error listando usuarios tablero: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/expediente/ficha/{expediente}")
async def get_expediente_ficha(expediente: str, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT direccion, notas_internas, responsable, estado, prioridad, proxima_reunion
                FROM expediente_fichas
                WHERE expediente = :exp
            """), {"exp": clean_exp}).fetchone()
            
            if row:
                return {
                    "direccion": row[0] or "",
                    "notas_internas": row[1] or "",
                    "responsable": row[2] or "",
                    "estado": row[3] or "",
                    "prioridad": row[4] or "",
                    "proxima_reunion": bool(row[5])
                }
            else:
                return {
                    "direccion": "",
                    "notas_internas": "",
                    "responsable": "",
                    "estado": "",
                    "prioridad": "",
                    "proxima_reunion": False
                }
    except Exception as e:
        logger.error(f"Error obteniendo ficha: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class FichaInternalNoteEditRequest(BaseModel):
    note_text: str

@app.get("/api/expediente/ficha/{expediente}/notas_internas")
async def get_ficha_notas_internas(expediente: str, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.connect() as conn:
            sql = """
                SELECT 
                    n.id, 
                    n.note_text, 
                    n.created_at,
                    n.username,
                    u.full_name as author_name
                FROM expediente_ficha_internal_notes n
                LEFT JOIN auth_users u ON n.username = u.username
                WHERE n.expediente = :exp
                ORDER BY n.created_at DESC
            """
            res = conn.execute(text(sql), {"exp": clean_exp}).fetchall()
            return [{
                "id": r[0],
                "note_text": r[1],
                "created_at": r[2].strftime("%Y-%m-%d %H:%M:%S") if r[2] and hasattr(r[2], "strftime") else str(r[2])[:19],
                "username": r[3],
                "author_name": r[4] or r[3],
                "is_owner": r[3] == current_user.username or current_user.role.lower() in ['admin', 'administrador']
            } for r in res]
    except Exception as e:
        logger.error(f"Error listando notas internas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/expediente/ficha/nota/{note_id}")
async def edit_ficha_internal_note(note_id: int, data: FichaInternalNoteEditRequest, current_user: User = Depends(get_current_user)):
    try:
        with engine.begin() as conn:
            note = conn.execute(text("SELECT username FROM expediente_ficha_internal_notes WHERE id = :nid"), {"nid": note_id}).fetchone()
            if not note:
                raise HTTPException(status_code=404, detail="Nota no encontrada")
            if note[0] != current_user.username and current_user.role.lower() not in ['admin', 'administrador']:
                raise HTTPException(status_code=403, detail="No tienes permisos para editar esta nota")
                
            conn.execute(text("""
                UPDATE expediente_ficha_internal_notes
                SET note_text = :note
                WHERE id = :nid
            """), {"nid": note_id, "note": data.note_text})
        return {"status": "ok", "message": "Nota actualizada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editando nota de ficha: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/expediente/ficha/nota/{note_id}")
async def delete_ficha_internal_note(note_id: int, current_user: User = Depends(get_current_user)):
    try:
        with engine.begin() as conn:
            note = conn.execute(text("SELECT username FROM expediente_ficha_internal_notes WHERE id = :nid"), {"nid": note_id}).fetchone()
            if not note:
                raise HTTPException(status_code=404, detail="Nota no encontrada")
            if note[0] != current_user.username and current_user.role.lower() not in ['admin', 'administrador']:
                raise HTTPException(status_code=403, detail="No tienes permisos para eliminar esta nota")
                
            conn.execute(text("""
                DELETE FROM expediente_ficha_internal_notes
                WHERE id = :nid
            """), {"nid": note_id})
        return {"status": "ok", "message": "Nota eliminada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando nota de ficha: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/expediente/ficha/{expediente}")
async def save_expediente_ficha(expediente: str, data: FichaEditRequest, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO expediente_fichas (expediente, direccion, responsable, estado, prioridad, proxima_reunion, updated_at)
                VALUES (:exp, :dir, :resp, :est, :prio, :prox, CURRENT_TIMESTAMP)
                ON CONFLICT (expediente) DO UPDATE SET
                    direccion = EXCLUDED.direccion,
                    responsable = EXCLUDED.responsable,
                    estado = EXCLUDED.estado,
                    prioridad = EXCLUDED.prioridad,
                    proxima_reunion = EXCLUDED.proxima_reunion,
                    updated_at = CURRENT_TIMESTAMP
            """), {
                "exp": clean_exp,
                "dir": data.direccion,
                "resp": data.responsable,
                "est": data.estado,
                "prio": data.prioridad,
                "prox": data.proxima_reunion
            })
            
            if data.notas_internas and data.notas_internas.strip():
                conn.execute(text("""
                    INSERT INTO expediente_ficha_internal_notes (expediente, username, note_text)
                    VALUES (:exp, :username, :notes)
                """), {
                    "exp": clean_exp,
                    "username": current_user.username,
                    "notes": data.notas_internas.strip()
                })
        return {"status": "ok", "message": "Ficha de expediente guardada"}
    except Exception as e:
        logger.error(f"Error guardando ficha: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/pendientes_asociacion")
async def get_pendientes_asociacion(current_user: User = Depends(get_current_user)):
    results = {}
    
    # 1. Consultar a Oracle para obtener los documentos creados pero no asociados
    import oracledb
    import os
    
    oracle_user = os.getenv("ORACLE_USER", "CDASILVACOSTA")
    oracle_pass = os.getenv("ORACLE_PASS", "SUI_sie329(m")
    oracle_dsn = os.getenv("ORACLE_DSN", "ind01-scan1.gcba.gob.ar:1521/sadetst.gcba.gob.ar")
    
    oracle_data = []
    try:
        connection = oracledb.connect(user=oracle_user, password=oracle_pass, dsn=oracle_dsn)
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id_expediente, documento, acronimo, usuario_creador, fecha_creacion
            FROM EE_SADE.MVW_DATOS_GEDO_SECGDU
            WHERE fecha_creacion IS NOT NULL 
              AND fecha_asociacion IS NULL
        """)
        oracle_data = cursor.fetchall()
        connection.close()
    except Exception as e:
        logger.error(f"Error consultando Oracle para pendientes_asociacion: {e}")
        raise HTTPException(status_code=500, detail=f"Error al conectar con la base transaccional Oracle: {str(e)}")

    if not oracle_data:
        return results

    id_list = [row[0] for row in oracle_data]

    # 2. Filtrar y agrupar en Postgres contra las tratas y gerencias configuradas
    try:
        with engine.connect() as conn:
            for gerencia, tratas in TRAMITES_CONFIG.items():
                cfg_rows = conn.execute(text("""
                    SELECT trata_reporte, acronimos_egreso, firmantes_egreso 
                    FROM cfg_gestion_metas 
                    WHERE gerencia = :g AND trata_reporte <> 'INTERVENCIONES'
                """), {"g": gerencia}).fetchall()
                
                trata_rules = {row[0]: {"acronimos": row[1] or [], "firmantes": row[2] or []} for row in cfg_rows}
                
                gerencia_data = {}
                
                # Obtener los expedientes que coinciden con los IDs pendientes desde el universo de esta gerencia
                sql = f"""
                    SELECT id_expediente, expediente, trata
                    FROM mv_{gerencia}_universo
                    WHERE es_trata_propia = TRUE
                      AND id_expediente = ANY(:ids)
                """
                try:
                    pg_rows = conn.execute(text(sql), {"ids": id_list}).fetchall()
                    pg_exp_map = {row[0]: {"expediente": row[1], "trata": row[2]} for row in pg_rows}
                    
                    for id_exp, doc, acro, creator, created in oracle_data:
                        if id_exp in pg_exp_map:
                            trata_code = pg_exp_map[id_exp]["trata"]
                            exp_num = pg_exp_map[id_exp]["expediente"]
                            
                            rules = trata_rules.get(trata_code)
                            if not rules or not rules["acronimos"]:
                                continue
                            
                            if acro not in rules["acronimos"]:
                                continue
                                
                            if rules["firmantes"] and creator not in rules["firmantes"]:
                                continue
                                
                            if trata_code not in gerencia_data:
                                trata_name = TRAMITES_CONFIG.get(gerencia, {}).get(trata_code, {}).get("nombre") or trata_code
                                gerencia_data[trata_code] = {
                                    "trata_nombre": trata_name,
                                    "expedientes": []
                                }
                                
                            gerencia_data[trata_code]["expedientes"].append({
                                "expediente": exp_num,
                                "gedo": doc,
                                "usuario_creador": creator,
                                "fecha_creacion": created.strftime("%Y-%m-%d %H:%M:%S") if created and hasattr(created, "strftime") else (str(created)[:19] if created else None)
                            })
                except Exception as query_err:
                    logger.error(f"Error filtrando en Postgres para gerencia {gerencia}: {query_err}")
                
                if gerencia_data:
                    results[gerencia] = {
                        "area_nombre": gerencia.upper(),
                        "tratas": gerencia_data
                    }
        return results
    except Exception as e:
        logger.error(f"Error procesando pendientes en Postgres: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/subsanaciones")
async def get_subsanaciones_report(
    gerencia: Optional[str] = 'ALL',
    current_user: User = Depends(get_current_user)
):
    g_param = gerencia.lower() if gerencia else 'all'
    if g_param == 'conforme':
        g_param = 'regularizacion'

    gerencias_to_query = []
    if g_param != 'all':
        if g_param not in TRAMITES_CONFIG:
            raise HTTPException(status_code=404, detail=f"Gerencia {gerencia} no encontrada.")
        gerencias_to_query = [g_param]
    else:
        gerencias_to_query = list(TRAMITES_CONFIG.keys())

    records = []
    try:
        with engine.connect() as conn:
            for g in gerencias_to_query:
                # Query 1: Trata-level
                sql_trata = f"""
                    WITH exp_total_subs AS (
                        SELECT 
                            u.trata,
                            u.id_expediente,
                            COUNT(*) as cant_subs,
                            SUM(
                                CASE 
                                    WHEN a.fecha_alta IS NULL OR a.fecha_alta < '2015-01-01'::date THEN 0
                                    WHEN a.fecha_cierre IS NOT NULL THEN (a.fecha_cierre::date - a.fecha_alta::date)
                                    ELSE (CURRENT_DATE - a.fecha_alta::date)
                                END
                            ) as dias_subs
                        FROM mv_{g}_universo u
                        INNER JOIN mvw_ee_actividades_secgdu a ON u.id_expediente = a.id_expediente
                        WHERE u.es_trata_propia = TRUE
                          AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                        GROUP BY u.trata, u.id_expediente
                    )
                    SELECT 
                        trata,
                        COUNT(*) as total_expedientes,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cant_subs)::numeric as mediana_cant,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dias_subs)::numeric as mediana_dias
                    FROM exp_total_subs
                    GROUP BY trata
                """
                # Query 2: Analyst-level
                sql_analyst = f"""
                    WITH exp_subs AS (
                        SELECT 
                            u.trata,
                            a.usuario_alta as analista,
                            a.id_expediente,
                            COUNT(*) as cant_subs,
                            SUM(
                                CASE 
                                    WHEN a.fecha_alta IS NULL OR a.fecha_alta < '2015-01-01'::date THEN 0
                                    WHEN a.fecha_cierre IS NOT NULL THEN (a.fecha_cierre::date - a.fecha_alta::date)
                                    ELSE (CURRENT_DATE - a.fecha_alta::date)
                                END
                            ) as dias_subs
                        FROM mv_{g}_universo u
                        INNER JOIN mvw_ee_actividades_secgdu a ON u.id_expediente = a.id_expediente
                        WHERE u.es_trata_propia = TRUE
                          AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                        GROUP BY u.trata, a.usuario_alta, a.id_expediente
                    )
                    SELECT 
                        t.trata,
                        t.analista,
                        COALESCE(du.apellido_nombre, t.analista) as analista_nombre,
                        COALESCE(du.codigo_sector_interno, '-') as analista_sector,
                        COUNT(*) as total_expedientes,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.cant_subs)::numeric as mediana_cant,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.dias_subs)::numeric as mediana_dias
                    FROM exp_subs t
                    LEFT JOIN datos_usuario du ON t.analista = du.usuario
                    GROUP BY t.trata, t.analista, du.apellido_nombre, du.codigo_sector_interno
                """
                
                try:
                    trata_rows = conn.execute(text(sql_trata)).fetchall()
                    analyst_rows = conn.execute(text(sql_analyst)).fetchall()
                except Exception as query_err:
                    logger.warning(f"Error querying subsanaciones for gerencia {g}: {query_err}")
                    continue
                
                # Group analysts by trata
                trata_analysts = {}
                for ar in analyst_rows:
                    ar_dict = ar._mapping
                    t_code = ar_dict["trata"]
                    if t_code not in trata_analysts:
                        trata_analysts[t_code] = []
                    trata_analysts[t_code].append({
                        "analista": ar_dict["analista"],
                        "nombre": ar_dict["analista_nombre"],
                        "sector": ar_dict["analista_sector"],
                        "total_expedientes": int(ar_dict["total_expedientes"] or 0),
                        "mediana_cant": float(ar_dict["mediana_cant"] or 0.0),
                        "mediana_dias": float(ar_dict["mediana_dias"] or 0.0)
                    })
                    
                g_cfg = TRAMITES_CONFIG.get(g, {})
                for tr in trata_rows:
                    tr_dict = tr._mapping
                    t_code = tr_dict["trata"]
                    t_cfg = g_cfg.get(t_code, {})
                    
                    records.append({
                        "gerencia": g,
                        "trata": t_code,
                        "descripcion_trata": t_cfg.get("nombre") or "S/D",
                        "total_expedientes": int(tr_dict["total_expedientes"] or 0),
                        "mediana_cant": float(tr_dict["mediana_cant"] or 0.0),
                        "mediana_dias": float(tr_dict["mediana_dias"] or 0.0),
                        "analistas": trata_analysts.get(t_code, [])
                    })
        return records
    except Exception as e:
        logger.error(f"Error en reporte/subsanaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/subsanaciones/expedientes")
async def get_subsanaciones_expedientes(
    gerencia: str,
    trata: str,
    analista: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
        
    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail=f"Gerencia {gerencia} no encontrada.")
        
    try:
        with engine.connect() as conn:
            sql = f"""
                SELECT 
                    u.expediente AS "EXPEDIENTE",
                    u.trata AS "TRAMITE",
                    u.descripcion_trata AS "DETALLE TRATA",
                    to_char(u.fecha_creacion_ee, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA CREACION",
                    a.usuario_alta as "ANALISTA",
                    COALESCE(du.apellido_nombre, a.usuario_alta) as "ANALISTA_NOMBRE",
                    COUNT(DISTINCT a.fecha_alta) as "CANT SUBSANACIONES",
                    SUM(
                        CASE 
                            WHEN a.fecha_alta IS NULL OR a.fecha_alta < '2015-01-01'::date THEN 0
                            WHEN a.fecha_cierre IS NOT NULL THEN (a.fecha_cierre::date - a.fecha_alta::date)
                            ELSE (CURRENT_DATE - a.fecha_alta::date)
                        END
                    ) as "DIAS SUBSANACION"
                FROM mv_{gerencia_clean}_universo u
                INNER JOIN mvw_ee_actividades_secgdu a ON u.id_expediente = a.id_expediente
                LEFT JOIN datos_usuario du ON a.usuario_alta = du.usuario
                WHERE u.es_trata_propia = TRUE
                  AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                  AND u.trata = :trata
                  AND (:analista IS NULL OR a.usuario_alta = :analista)
                GROUP BY u.expediente, u.trata, u.descripcion_trata, u.fecha_creacion_ee, a.usuario_alta, du.apellido_nombre
                ORDER BY u.expediente
            """
            result = conn.execute(text(sql), {"trata": trata, "analista": analista})
            rows = [dict(row._mapping) for row in result.fetchall()]
            
            mapped_rows = []
            for r in rows:
                mapped_rows.append({
                    "expediente": r["EXPEDIENTE"],
                    "trata": r["TRAMITE"],
                    "descripcion_trata": r["DETALLE TRATA"] or "S/D",
                    "fecha_creacion": r["FECHA CREACION"],
                    "analista": r["ANALISTA_NOMBRE"],
                    "usuario_sade": r["ANALISTA"],
                    "cant_subsanaciones": int(r["CANT SUBSANACIONES"] or 0),
                    "dias_subsanacion": int(r["DIAS SUBSANACION"] or 0)
                })
            return mapped_rows
    except Exception as e:
        logger.error(f"Error en reporte/subsanaciones/expedientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints del Agente de IA Conversacional (Deshabilitado) ---

@app.get("/api/analytics/permisos-obra")
async def get_analytics_permisos_obra(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            # 1. Monthly data
            result_monthly = conn.execute(text("""
                SELECT 
                    EXTRACT(YEAR FROM e.fecha_egreso)::int as anio,
                    EXTRACT(MONTH FROM e.fecha_egreso)::int as mes,
                    e.trata,
                    cfg.descripcion_trata,
                    e.usuario_egreso as usuario,
                    COUNT(*) as cant
                FROM public.mv_contable_egresos_efectivos e
                LEFT JOIN public.cfg_gestion_metas cfg 
                  ON cfg.trata_reporte = e.trata 
                 AND cfg.gerencia = 'contable'
                WHERE e.acronimo_egreso = 'IFPDO'
                  AND e.trata IN ('MDUG3001A', 'MDUG1501J', 'MDUG3402A')
                  AND e.fecha_egreso >= '2022-01-01'
                GROUP BY anio, mes, e.trata, cfg.descripcion_trata, e.usuario_egreso
                ORDER BY anio, mes, e.trata;
            """))
            monthly_data = [dict(r._mapping) for r in result_monthly]
            
            # 2. Yearly data
            result_yearly = conn.execute(text("""
                SELECT 
                    EXTRACT(YEAR FROM fecha_egreso)::int as anio,
                    COUNT(*) as cant
                FROM public.mv_contable_egresos_efectivos
                WHERE acronimo_egreso = 'IFPDO'
                  AND trata IN ('MDUG3001A', 'MDUG1501J', 'MDUG3402A')
                  AND fecha_egreso >= '2022-01-01'
                GROUP BY anio
                ORDER BY anio;
            """))
            yearly_data = [dict(r._mapping) for r in result_yearly]
            
            return {
                "monthly_data": monthly_data,
                "yearly_data": yearly_data
            }
    except Exception as e:
        logger.error(f"Error fetching permisos obra analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/ley-blanqueo")
async def get_analytics_ley_blanqueo(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            # Check if the materialized view exists
            check_view = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM pg_matviews 
                    WHERE matviewname = 'parcelas_leydeblanqueo'
                );
            """)).fetchone()
            
            if not check_view or not check_view[0]:
                logger.info("La vista public.parcelas_leydeblanqueo no existe. Intentando crearla...")
                # Asegurar primero la existencia de la tabla base local
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS public.df_form_comp_value (
                        id_transaction BIGINT,
                        input_name VARCHAR(255),
                        value_str TEXT,
                        value_double DOUBLE PRECISION,
                        value_int INTEGER,
                        value_boolean BOOLEAN
                    );
                    CREATE INDEX IF NOT EXISTS idx_df_form_comp_value_id_tx ON public.df_form_comp_value (id_transaction);
                """))
                
                # Leer y ejecutar el script SQL
                sql_path = os.path.join(os.path.dirname(__file__), "..", "vistas", "regularizacion", "16_parcelas_leydeblanqueo.sql")
                if os.path.exists(sql_path):
                    with open(sql_path, "r", encoding="utf-8") as f:
                        sql_content = f.read()
                    
                    # Usamos el connection subyacente para ejecutar con psycopg2 directamente y poder procesar comandos múltiples
                    raw_conn = conn.connection
                    with raw_conn.cursor() as cur:
                        cur.execute(sql_content)
                    logger.info("Vista materializada parcelas_leydeblanqueo creada con éxito.")
                else:
                    logger.error(f"No se encontró el archivo SQL en la ruta: {sql_path}")
            
            # 1. Registros por barrio
            result_barrio = conn.execute(text("""
                SELECT 
                    COALESCE(NULLIF(barrio, ''), 'S/D') as barrio,
                    COUNT(*) as cant
                FROM public.parcelas_leydeblanqueo
                GROUP BY barrio
                ORDER BY cant DESC;
            """))
            barrio_data = [dict(r._mapping) for r in result_barrio]
            
            # 2. Registros por comuna
            result_comuna = conn.execute(text("""
                SELECT 
                    COALESCE(NULLIF(comuna, ''), 'S/D') as comuna,
                    COUNT(*) as cant
                FROM public.parcelas_leydeblanqueo
                GROUP BY comuna
                ORDER BY cant DESC;
            """))
            comuna_data = [dict(r._mapping) for r in result_comuna]
            
            # 3. Sumas de superficies en contravención
            result_sums = conn.execute(text("""
                SELECT 
                    COALESCE(SUM(sup_contra_no_reg_ce), 0) as sup_contra_no_reg_ce,
                    COALESCE(SUM(sup_contra_reg_ce), 0) as sup_contra_reg_ce,
                    COALESCE(SUM(sup_contra_reg_cur), 0) as sup_contra_reg_cur,
                    COALESCE(SUM(sup_contra_no_reg_cur), 0) as sup_contra_no_reg_cur
                FROM public.parcelas_leydeblanqueo;
            """)).fetchone()
            
            sums_data = dict(result_sums._mapping) if result_sums else {
                "sup_contra_no_reg_ce": 0,
                "sup_contra_reg_ce": 0,
                "sup_contra_reg_cur": 0,
                "sup_contra_no_reg_cur": 0
            }
            
            # 4. Superficies por barrio para el gráfico apilado
            result_barrio_surfaces = conn.execute(text("""
                SELECT 
                    COALESCE(NULLIF(barrio, ''), 'S/D') as barrio,
                    COALESCE(SUM(sup_contra_no_reg_ce), 0) as sup_contra_no_reg_ce,
                    COALESCE(SUM(sup_contra_reg_ce), 0) as sup_contra_reg_ce,
                    COALESCE(SUM(sup_contra_reg_cur), 0) as sup_contra_reg_cur,
                    COALESCE(SUM(sup_contra_no_reg_cur), 0) as sup_contra_no_reg_cur
                FROM public.parcelas_leydeblanqueo
                GROUP BY barrio
                ORDER BY (
                    COALESCE(SUM(sup_contra_no_reg_ce), 0) + 
                    COALESCE(SUM(sup_contra_reg_ce), 0) + 
                    COALESCE(SUM(sup_contra_reg_cur), 0) + 
                    COALESCE(SUM(sup_contra_no_reg_cur), 0)
                ) DESC;
            """))
            barrio_surfaces_data = [dict(r._mapping) for r in result_barrio_surfaces]
            
            # 5. Superficies mes a mes (línea temporal)
            result_timeline = conn.execute(text("""
                SELECT 
                    TO_CHAR(d.fecha_asociacion, 'YYYY-MM') as mes,
                    COALESCE(SUM(p.sup_contra_no_reg_ce), 0) as sup_contra_no_reg_ce,
                    COALESCE(SUM(p.sup_contra_reg_ce), 0) as sup_contra_reg_ce,
                    COALESCE(SUM(p.sup_contra_reg_cur), 0) as sup_contra_reg_cur,
                    COALESCE(SUM(p.sup_contra_no_reg_cur), 0) as sup_contra_no_reg_cur
                FROM public.parcelas_leydeblanqueo p
                JOIN public.mvw_datos_gedo_secgdu d ON p.id_transaction = d.trx_gedo
                WHERE d.fecha_asociacion IS NOT NULL
                GROUP BY TO_CHAR(d.fecha_asociacion, 'YYYY-MM')
                ORDER BY mes ASC;
            """))
            timeline_data = [dict(r._mapping) for r in result_timeline]
            
            return {
                "barrio_data": barrio_data,
                "comuna_data": comuna_data,
                "sums_data": sums_data,
                "barrio_surfaces_data": barrio_surfaces_data,
                "timeline_data": timeline_data
            }
    except Exception as e:
        logger.error(f"Error fetching ley blanqueo analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/ley-blanqueo/excel")
async def get_analytics_ley_blanqueo_excel(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    p.documento_egreso,
                    p.id_transaction,
                    p.uso_cur,
                    p.id_plano,
                    p.tramite_gobierno,
                    p.prof_nombre,
                    p.prof_apellido,
                    p.prof_matricula,
                    p.direccion,
                    p.barrio,
                    p.comuna,
                    p.sup_contra_no_reg_ce,
                    p.sup_contra_reg_ce,
                    p.sup_contra_reg_cur,
                    p.sup_contra_no_reg_cur,
                    TO_CHAR(d.fecha_asociacion, 'YYYY-MM-DD') as fecha_asociacion
                FROM public.parcelas_leydeblanqueo p
                LEFT JOIN public.mvw_datos_gedo_secgdu d ON p.id_transaction = d.trx_gedo
                ORDER BY p.documento_egreso;
            """))
            rows = [dict(r._mapping) for r in result]
            return rows
    except Exception as e:
        logger.error(f"Error fetching ley blanqueo excel data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints de Productividad Analistas ---

@app.get("/api/productividad/sectores-analistas")
async def get_sectores_analistas(current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("productividad_analistas"):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        with engine.connect() as conn:
            query = text("""
                WITH analysts AS (
                    SELECT DISTINCT gerencia, unnest(analistas_oficiales) as analista
                    FROM cfg_gestion_metas
                )
                SELECT a.gerencia, a.analista, COALESCE(du.apellido_nombre, a.analista) as apellido_nombre
                FROM analysts a
                LEFT JOIN datos_usuario du ON a.analista = du.usuario
                ORDER BY a.gerencia, apellido_nombre
            """)
            result = conn.execute(query)
            rows = result.fetchall()
            
            sectores = {}
            for r in rows:
                sec = r[0]
                user = r[1]
                name = r[2] or user
                if sec not in sectores:
                    sectores[sec] = []
                # Avoid duplicate names in the same gerencia list
                if not any(x["usuario"] == user for x in sectores[sec]):
                    sectores[sec].append({"usuario": user, "nombre": name})
            
            return sectores
    except Exception as e:
        logger.error(f"Error fetching sectores analistas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/productividad/analista/{username}")
async def get_analista_productividad(username: str, date_from: Optional[str] = None, date_to: Optional[str] = None, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("productividad_analistas"):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        try:
            from backend.productivity_engine import get_analyst_productivity_data
        except ModuleNotFoundError:
            from productivity_engine import get_analyst_productivity_data
        with engine.connect() as conn:
            data = get_analyst_productivity_data(conn, username, date_from, date_to)
            return data
    except Exception as e:
        logger.error(f"Error fetching analista productivity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_current_user_from_param_or_header(token: Optional[str] = Query(None), authorization: Optional[str] = Header(None, alias="Authorization")):
    actual_token = None
    if authorization and authorization.startswith("Bearer "):
        actual_token = authorization.split(" ")[1]
    elif token:
        actual_token = token
        
    if not actual_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo validar el acceso",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        payload = jwt.decode(actual_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        with engine.connect() as conn:
            user_row = conn.execute(text("""
                SELECT username, role, full_name, sector 
                FROM auth_users WHERE username = :u
            """), {"u": username}).fetchone()
            if not user_row:
                raise HTTPException(status_code=401, detail="Usuario no encontrado")
            resolved_perms = get_resolved_permissions(conn, user_row[0], user_row[1])
            return User(
                username=user_row[0],
                role=user_row[1],
                full_name=user_row[2],
                sector=user_row[3],
                permissions=resolved_perms
            )
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

@app.get("/api/productividad/pdf/individual")
async def get_pdf_individual(username: str, date_from: Optional[str] = None, date_to: Optional[str] = None, token: Optional[str] = Query(None), current_user: User = Depends(get_current_user_from_param_or_header)):
    if not current_user.permissions.get("productividad_analistas"):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        try:
            from backend.pdf_generator import generate_individual_pdf
        except ModuleNotFoundError:
            from pdf_generator import generate_individual_pdf
        from fastapi.responses import Response
        with engine.connect() as conn:
            pdf_bytes = generate_individual_pdf(conn, username, date_from, date_to)
            return Response(content=pdf_bytes, media_type="application/pdf", headers={
                "Content-Disposition": f"attachment; filename=productividad_{username}.pdf"
            })
    except Exception as e:
        logger.error(f"Error generating individual PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/productividad/pdf/comparativo")
async def get_pdf_comparativo(sector: str, date_from: Optional[str] = None, date_to: Optional[str] = None, token: Optional[str] = Query(None), current_user: User = Depends(get_current_user_from_param_or_header)):
    if not current_user.permissions.get("productividad_analistas"):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        try:
            from backend.pdf_generator import generate_comparative_pdf
        except ModuleNotFoundError:
            from pdf_generator import generate_comparative_pdf
        from fastapi.responses import Response
        with engine.connect() as conn:
            pdf_bytes = generate_comparative_pdf(conn, sector, date_from, date_to)
            return Response(content=pdf_bytes, media_type="application/pdf", headers={
                "Content-Disposition": f"attachment; filename=comparativo_{sector}.pdf"
            })
    except Exception as e:
        logger.error(f"Error generating comparative PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ciudad3d/stats")
def get_ciudad3d_stats(current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a Ciudad 3D")
    
    try:
        with geo_engine.connect() as conn:
            total_parcelas = conn.execute(text("SELECT COUNT(*) FROM public.cur_parcelas_ok")).scalar()
            total_manzanas = conn.execute(text("SELECT COUNT(*) FROM public.manzanas")).scalar()
            return {
                "total_parcelas": total_parcelas,
                "total_manzanas": total_manzanas
            }
    except Exception as e:
        logger.error(f"Error fetching Ciudad 3D stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error en la base de datos geo-mdr: {e}")

@app.get("/api/ciudad3d/troneras")
def get_ciudad3d_troneras(current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a Ciudad 3D")
    
    query = """
    WITH troneras_agg AS (
        SELECT TRIM(seccion) AS seccion,
               TRIM(manzana) AS manzana,
               SUM(CASE WHEN TRIM(UPPER(irregular)) = 'SI' THEN 1 ELSE 0 END) AS irregular_si,
               SUM(CASE WHEN TRIM(UPPER(irregular)) = 'NO' THEN 1 ELSE 0 END) AS irregular_no
        FROM public.mdr_troneras
        WHERE seccion IS NOT NULL AND manzana IS NOT NULL
        GROUP BY TRIM(seccion), TRIM(manzana)
    ),
    barrio_manzana AS (
        SELECT DISTINCT ON (TRIM(seccion), TRIM(manzana))
               TRIM(seccion) AS seccion,
               TRIM(manzana) AS manzana,
               TRIM(barrio) AS barrio
        FROM public.cur_parcelas_ok
        WHERE seccion IS NOT NULL AND manzana IS NOT NULL AND barrio IS NOT NULL AND TRIM(barrio) <> ''
    )
    SELECT bm.barrio,
           bm.seccion,
           bm.manzana,
           COALESCE(t.irregular_si, 0) AS irregular_si,
           COALESCE(t.irregular_no, 0) AS irregular_no
    FROM barrio_manzana bm
    JOIN public.manzanas m ON TRIM(m.seccion) = bm.seccion AND TRIM(m.manzana) = bm.manzana
    JOIN troneras_agg t ON t.seccion = bm.seccion AND t.manzana = bm.manzana
    ORDER BY bm.barrio, bm.seccion, bm.manzana
    """
    try:
        workflow_map = {}
        try:
            with engine.connect() as conn:
                wf_res = conn.execute(text("""
                    SELECT w.seccion, w.manzana, w.estado, w.analista_asignado, w.disposicion, w.archivo_trazado, w.archivo_finalizado, u.full_name
                    FROM public.manzanas_lfi_workflow w
                    LEFT JOIN public.auth_users u ON w.analista_asignado = u.username
                """)).fetchall()
                for r in wf_res:
                    key = (r[0].strip(), r[1].strip())
                    workflow_map[key] = {
                        "estado": r[2],
                        "analista_asignado": r[3] if r[3] else "",
                        "disposicion": r[4] if r[4] else "",
                        "archivo_trazado": r[5] if r[5] else "",
                        "archivo_finalizado": r[6] if r[6] else "",
                        "analista_nombre": r[7] if r[7] else (r[3] if r[3] else "")
                    }
        except Exception as wf_e:
            logger.error(f"Error fetching LFI workflow maps: {wf_e}")

        with geo_engine.connect() as conn:
            res = conn.execute(text(query)).fetchall()
            return [
                {
                    "barrio": r[0],
                    "seccion": r[1],
                    "manzana": r[2],
                    "irregular_si": r[3],
                    "irregular_no": r[4],
                    "estado": workflow_map.get((r[1].strip(), r[2].strip()), {}).get("estado", "Pendiente"),
                    "analista_asignado": workflow_map.get((r[1].strip(), r[2].strip()), {}).get("analista_asignado", ""),
                    "disposicion": workflow_map.get((r[1].strip(), r[2].strip()), {}).get("disposicion", ""),
                    "archivo_trazado": workflow_map.get((r[1].strip(), r[2].strip()), {}).get("archivo_trazado", ""),
                    "archivo_finalizado": workflow_map.get((r[1].strip(), r[2].strip()), {}).get("archivo_finalizado", ""),
                    "analista_nombre": workflow_map.get((r[1].strip(), r[2].strip()), {}).get("analista_nombre", "")
                }
                for r in res
            ]
    except Exception as e:
        logger.error(f"Error fetching Ciudad 3D troneras: {e}")
        raise HTTPException(status_code=500, detail=f"Error en la base de datos geo-mdr: {e}")

# LFI Manzanas Workflow Endpoints
class LFIAssignRequest(BaseModel):
    seccion: str
    manzana: str

@app.post("/api/ciudad3d/manzanas_lfi/assign")
def assign_manzana_lfi(req: LFIAssignRequest, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("lfi_dibujar"):
        raise HTTPException(status_code=403, detail="No tiene permisos de dibujo de LFI ('lfi_dibujar') para asignarse manzanas.")
    
    with engine.begin() as conn:
        existing = conn.execute(text("""
            SELECT estado FROM public.manzanas_lfi_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": req.seccion.strip(), "m": req.manzana.strip()}).fetchone()
        
        if existing and existing[0] != 'Pendiente':
            raise HTTPException(status_code=400, detail=f"Esta manzana ya está en estado '{existing[0]}'")
            
        conn.execute(text("""
            INSERT INTO public.manzanas_lfi_workflow (seccion, manzana, estado, analista_asignado, updated_at)
            VALUES (:s, :m, 'En curso', :a, CURRENT_TIMESTAMP)
            ON CONFLICT (seccion, manzana) 
            DO UPDATE SET estado = 'En curso', analista_asignado = :a, updated_at = CURRENT_TIMESTAMP
        """), {"s": req.seccion.strip(), "m": req.manzana.strip(), "a": current_user.username})
        
    return {"status": "ok", "estado": "En curso", "analista_asignado": current_user.username}

@app.post("/api/ciudad3d/manzanas_lfi/unassign")
def unassign_manzana_lfi(req: LFIAssignRequest, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="Solo los administradores pueden liberar asignaciones.")
        
    s_clean = req.seccion.strip()
    m_clean = req.manzana.strip()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO public.manzanas_lfi_workflow (seccion, manzana, estado, analista_asignado, updated_at)
            VALUES (:s, :m, 'Pendiente', NULL, CURRENT_TIMESTAMP)
            ON CONFLICT (seccion, manzana) 
            DO UPDATE SET estado = 'Pendiente', analista_asignado = NULL, updated_at = CURRENT_TIMESTAMP
        """), {"s": s_clean, "m": m_clean})
        
    return {"status": "ok", "estado": "Pendiente", "analista_asignado": None}


class LFINoteRequest(BaseModel):
    seccion: str
    manzana: str
    nota: str

# ─── LFI Map Coord Queries and Tile Endpoints ───────────────────────────────

@app.get("/api/ciudad3d/manzana_by_coords")
def get_manzana_by_coords(lng: float, lat: float, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="Sin permisos para Ciudad 3D")
    
    query = """
        SELECT seccion, manzana FROM public.mdr_troneras
        WHERE ST_Contains(geom, ST_Transform(ST_SetSRID(ST_Point(:lng, :lat), 4326), 22186))
        LIMIT 1
    """
    try:
        with geo_engine.connect() as conn:
            row = conn.execute(text(query), {"lng": lng, "lat": lat}).fetchone()
            if row:
                return {"seccion": row[0].strip(), "manzana": row[1].strip()}
            
            row_p = conn.execute(text("""
                SELECT seccion, manzana FROM public.cur_parcelas_ok
                WHERE ST_Contains(geom, ST_Transform(ST_SetSRID(ST_Point(:lng, :lat), 4326), 22186))
                LIMIT 1
            """), {"lng": lng, "lat": lat}).fetchone()
            if row_p:
                return {"seccion": row_p[0].strip(), "manzana": row_p[1].strip()}
                
            return {"seccion": None, "manzana": None}
    except Exception as e:
        logger.error(f"Error querying manzana by coords: {e}")
        raise HTTPException(status_code=500, detail=str(e))

LFI_MAP_LAYERS = {
    "parcelas":     ("cur_parcelas_ok",           "geom", 22186),
    "lfi":          ("mdr_lineadefrenteinterno",  "geom", 22186),
    "basamento":    ("mdr_lineadebasamento",      "geom", 22186),
    "troneras":     ("mdr_troneras",              "geom", 22186),
    "banda_minima": ("mdr_banda_minima",          "geom", 22186),
}

def _create_lfi_gist_indexes():
    """Crea índices GIST en las capas del mapa LFI si no existen."""
    index_queries = [
        "CREATE INDEX IF NOT EXISTS idx_cur_parcelas_ok_geom ON public.cur_parcelas_ok USING GIST(geom)",
        "CREATE INDEX IF NOT EXISTS idx_mdr_lfi_geom ON public.mdr_lineadefrenteinterno USING GIST(geom)",
        "CREATE INDEX IF NOT EXISTS idx_mdr_lineadebasamento_geom ON public.mdr_lineadebasamento USING GIST(geom)",
        "CREATE INDEX IF NOT EXISTS idx_mdr_troneras_geom ON public.mdr_troneras USING GIST(geom)",
        "CREATE INDEX IF NOT EXISTS idx_mdr_banda_minima_geom ON public.mdr_banda_minima USING GIST(geom)",
    ]
    try:
        with geo_engine.begin() as conn:
            for q in index_queries:
                conn.execute(text(q))
        logger.info("LFI Map: índices GIST verificados/creados correctamente.")
    except Exception as e:
        logger.warning(f"LFI Map: no se pudieron crear algunos índices GIST: {e}")

# Ejecutar creación de índices al arrancar
try:
    _create_lfi_gist_indexes()
except Exception:
    pass

# Cache en memoria para tiles MVT (evita queries repetidas)
import functools, hashlib
_lfi_tile_cache: dict = {}
_LFI_TILE_CACHE_MAX = 500

def _lfi_tile_cache_key(layer, z, x, y):
    return f"{layer}/{z}/{x}/{y}"

@app.get("/api/lfi/tiles/{layer}/{z}/{x}/{y}")
def get_lfi_map_tile(layer: str, z: int, x: int, y: int, current_user: User = Depends(get_current_user_from_param_or_header)):
    """Sirve Vector Tiles MVT para las capas del mapa LFI."""
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="Sin permisos para Ciudad 3D")
    
    # No generar tiles para zoom < 14 (demasiado costoso y no se muestra en frontend)
    if z < 14:
        from fastapi.responses import Response as FastResponse
        return FastResponse(content=b"", media_type="application/x-protobuf",
                           headers={"Cache-Control": "public, max-age=86400", "Access-Control-Allow-Origin": "*"})


    if layer not in LFI_MAP_LAYERS:
        raise HTTPException(status_code=404, detail=f"Capa '{layer}' no encontrada.")

    # Verificar cache en memoria
    cache_key = _lfi_tile_cache_key(layer, z, x, y)
    if cache_key in _lfi_tile_cache:
        mvt_bytes = _lfi_tile_cache[cache_key]
        from fastapi.responses import Response as FastResponse
        return FastResponse(content=bytes(mvt_bytes), media_type="application/x-protobuf",
                           headers={"Cache-Control": "public, max-age=21600", "X-Cache": "HIT",
                                    "Access-Control-Allow-Origin": "*"})
    table, col, srid = LFI_MAP_LAYERS[layer]
    
    # Simplificación progresiva en metros (3857 usa metros)
    if z >= 17:
        simplify_tol = 0.0
    elif z >= 15:
        simplify_tol = 1.0
    elif z >= 13:
        simplify_tol = 3.0
    else:
        simplify_tol = 8.0

    # Filtro espacial: bbox del tile transformada al SRID de origen para usar el índice GIST
    bbox_filter = f"ST_Transform(ST_TileEnvelope({z}, {x}, {y}), {srid})" if srid != 3857 else f"ST_TileEnvelope({z}, {x}, {y})"
    
    # ST_AsMVTGeom requiere geometrías en 3857 (Web Mercator)
    # Usamos ST_SetSRID para forzar el SRID origen antes del transform (defensive pattern)
    if simplify_tol > 0:
        geom_to_3857 = f"ST_Simplify(ST_Transform(ST_SetSRID({col}, {srid}), 3857), {simplify_tol})"
    else:
        geom_to_3857 = f"ST_Transform(ST_SetSRID({col}, {srid}), 3857)"

    # Atributos extra por capa para filtrado y estilos en frontend
    extra_cols = ""
    extra_join = ""
    if layer == "troneras":
        extra_cols = ", t.seccion, t.manzana, COALESCE(UPPER(TRIM(t.irregular)), '') AS irregular"
    elif layer in ("lfi", "basamento", "parcelas"):
        extra_cols = ", t.seccion, t.manzana"
    elif layer == "banda_minima":
        # mdr_banda_minima no tiene seccion/manzana, se obtienen via JOIN con cur_parcelas_ok
        extra_cols = ", p.seccion, p.manzana"
        extra_join = f"LEFT JOIN public.cur_parcelas_ok p ON p.smp = {table}.smp"

    # Alias de tabla en la subquery
    table_alias = "t" if layer != "banda_minima" else table
    from_clause = f"public.{table} t {extra_join}" if layer != "banda_minima" else f"public.{table} {extra_join}"
    geom_col_ref = f"t.{col}" if layer != "banda_minima" else f"{table}.{col}"
    geom_to_3857_aliased = geom_to_3857.replace(f"{col}", geom_col_ref)
    bbox_filter_aliased = bbox_filter

    query = text(f"""
        SELECT ST_AsMVT(q, :layer_name, 4096, 'geom') AS mvt
        FROM (
            SELECT ST_AsMVTGeom(
                {geom_to_3857_aliased},
                ST_TileEnvelope({z}, {x}, {y}),
                 4096,
                256,
                true
            ) AS geom{extra_cols}
            FROM {from_clause}
            WHERE {geom_col_ref} IS NOT NULL
              AND ST_SetSRID({geom_col_ref}, {srid}) && {bbox_filter_aliased}
        ) q
        WHERE q.geom IS NOT NULL
    """)
    
    try:
        with geo_engine.connect() as conn:
            result = conn.execute(query, {"layer_name": layer}).fetchone()
            mvt_bytes = result[0] if result else b""
            if mvt_bytes is None:
                mvt_bytes = b""
            # Guardar en cache (con límite de tamaño)
            if len(_lfi_tile_cache) >= _LFI_TILE_CACHE_MAX:
                # Eliminar entrada más antigua
                oldest = next(iter(_lfi_tile_cache))
                del _lfi_tile_cache[oldest]
            _lfi_tile_cache[cache_key] = bytes(mvt_bytes)

        from fastapi.responses import Response as FastResponse
        return FastResponse(
            content=bytes(mvt_bytes),
            media_type="application/x-protobuf",
            headers={
                "Cache-Control": "public, max-age=21600",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        logger.error(f"Error generando tile MVT para capa {layer} ({z}/{x}/{y}): {e}")
        raise HTTPException(status_code=500, detail=f"Error generando tile: {e}")


@app.get("/api/ciudad3d/manzanas_lfi/notes")
def get_manzana_lfi_notes(seccion: str, manzana: str, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a esta sección")
    
    s_clean = seccion.strip()
    m_clean = manzana.strip()
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT n.id, n.username, n.nota, n.created_at, u.full_name
            FROM public.manzanas_lfi_notes n
            LEFT JOIN public.auth_users u ON n.username = u.username
            WHERE TRIM(n.seccion) = :s AND TRIM(n.manzana) = :m
            ORDER BY n.created_at DESC
        """), {"s": s_clean, "m": m_clean}).fetchall()
        
        return [
            {
                "id": r[0],
                "username": r[1],
                "nota": r[2],
                "created_at": str(r[3]),
                "full_name": r[4] if r[4] else r[1]
            }
            for r in res
        ]

@app.post("/api/ciudad3d/manzanas_lfi/notes")
def add_manzana_lfi_note(req: LFINoteRequest, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a esta sección")
    
    s_clean = req.seccion.strip()
    m_clean = req.manzana.strip()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO public.manzanas_lfi_notes (seccion, manzana, username, nota, created_at)
            VALUES (:s, :m, :u, :n, CURRENT_TIMESTAMP)
        """), {"s": s_clean, "m": m_clean, "u": current_user.username, "n": req.nota})
        
    return {"status": "ok"}

@app.post("/api/ciudad3d/manzanas_lfi/upload")
async def upload_trazado_lfi(
    seccion: str = Form(...),
    manzana: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not current_user.permissions.get("lfi_dibujar"):
        raise HTTPException(status_code=403, detail="No tiene permisos de dibujo de LFI ('lfi_dibujar') para subir trazados.")
        
    with engine.connect() as conn:
        existing = conn.execute(text("""
            SELECT analista_asignado, estado FROM public.manzanas_lfi_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": seccion, "m": manzana}).fetchone()
        
        if not existing:
            raise HTTPException(status_code=400, detail="Esta manzana no ha sido asignada ni iniciada.")
        if existing[0] != current_user.username and current_user.role.lower() not in ['admin', 'administrador']:
            raise HTTPException(status_code=403, detail=f"Esta manzana está asignada a {existing[0]}, no puede subir el archivo.")

    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "trazados_lfi"))
    os.makedirs(upload_dir, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1]
    safe_filename = f"lfi-{seccion}-{manzana}-{int(time.time())}{file_ext}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        logger.error(f"Error saving LFI file: {e}")
        raise HTTPException(status_code=500, detail="Error interno al guardar el archivo.")
        
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE public.manzanas_lfi_workflow
            SET estado = 'Para revisión', archivo_trazado = :f, updated_at = CURRENT_TIMESTAMP
            WHERE seccion = :s AND manzana = :m
        """), {"s": seccion, "m": manzana, "f": safe_filename})
        
    return {"status": "ok", "estado": "Para revisión", "archivo_trazado": safe_filename}

@app.post("/api/ciudad3d/manzanas_lfi/review")
async def review_manzana_lfi(
    seccion: str = Form(...),
    manzana: str = Form(...),
    decision: str = Form(...),
    comentario: Optional[str] = Form(None),
    disposicion: Optional[str] = Form(None),
    file_final: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    if not current_user.permissions.get("lfi_revisar"):
        raise HTTPException(status_code=403, detail="No tiene permisos de revisión de LFI ('lfi_revisar') para revisar manzanas.")
        
    with engine.begin() as conn:
        existing = conn.execute(text("""
            SELECT estado FROM public.manzanas_lfi_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": seccion, "m": manzana}).fetchone()
        
        if not existing or existing[0] != 'Para revisión':
            raise HTTPException(status_code=400, detail="Esta manzana no está en estado 'Para revisión'")
            
        new_state = 'Subir a Ciudad 3D' if decision.upper() == 'OK' else 'En curso'
        
        safe_filename = None
        if decision.upper() == 'OK' and file_final:
            upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "trazados_lfi"))
            os.makedirs(upload_dir, exist_ok=True)
            file_ext = os.path.splitext(file_final.filename)[1]
            safe_filename = f"lfi-final-{seccion}-{manzana}-{int(time.time())}{file_ext}"
            file_path = os.path.join(upload_dir, safe_filename)
            try:
                with open(file_path, "wb") as f:
                    content = await file_final.read()
                    f.write(content)
            except Exception as e:
                logger.error(f"Error saving LFI final file: {e}")
                raise HTTPException(status_code=500, detail="Error al guardar el archivo finalizado.")
        
        # Build update query
        update_query = """
            UPDATE public.manzanas_lfi_workflow
            SET estado = :state, updated_at = CURRENT_TIMESTAMP
        """
        params = {"state": new_state, "s": seccion, "m": manzana}
        if disposicion:
            update_query += ", disposicion = :disp"
            params["disp"] = disposicion
        if safe_filename:
            update_query += ", archivo_finalizado = :file_fin"
            params["file_fin"] = safe_filename
            
        update_query += " WHERE seccion = :s AND manzana = :m"
        conn.execute(text(update_query), params)
            
        if comentario:
            note_text = f"*** REVISIÓN [{decision.upper()}]: {comentario} ***"
            conn.execute(text("""
                INSERT INTO public.manzanas_lfi_notes (seccion, manzana, username, nota, created_at)
                VALUES (:s, :m, :u, :n, CURRENT_TIMESTAMP)
            """), {"s": seccion, "m": manzana, "u": current_user.username, "n": note_text})
            
    return {"status": "ok", "estado": new_state, "archivo_finalizado": safe_filename}

@app.get("/api/ciudad3d/manzanas_lfi/download_trazado")
def download_trazado_lfi_file(
    seccion: str,
    manzana: str,
    file_type: str = Query("draft"),
    token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_from_param_or_header)
):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a esta sección")
        
    with engine.connect() as conn:
        col = "archivo_finalizado" if file_type == "final" else "archivo_trazado"
        row = conn.execute(text(f"""
            SELECT {col} FROM public.manzanas_lfi_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": seccion, "m": manzana}).fetchone()
        
        if not row or not row[0]:
            raise HTTPException(status_code=404, detail="No hay archivo subido de ese tipo para esta manzana.")
            
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "trazados_lfi", row[0]))
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="El archivo físico no fue encontrado en el servidor.")
            
        return FileResponse(file_path, filename=row[0])

class LFIDisposicionRequest(BaseModel):
    seccion: str
    manzana: str
    disposicion: str

@app.post("/api/ciudad3d/manzanas_lfi/disposicion")
def update_manzana_lfi_disposicion(req: LFIDisposicionRequest, current_user: User = Depends(get_current_user)):
    if not (current_user.permissions.get("lfi_dibujar") or current_user.permissions.get("lfi_revisar")):
        raise HTTPException(status_code=403, detail="No tiene permisos de dibujo o revisión de LFI ('lfi_dibujar'/'lfi_revisar') para actualizar la disposición.")
        
    s_clean = req.seccion.strip()
    m_clean = req.manzana.strip()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO public.manzanas_lfi_workflow (seccion, manzana, disposicion, updated_at)
            VALUES (:s, :m, :d, CURRENT_TIMESTAMP)
            ON CONFLICT (seccion, manzana)
            DO UPDATE SET disposicion = :d, updated_at = CURRENT_TIMESTAMP
        """), {"s": s_clean, "m": m_clean, "d": req.disposicion})
        
    return {"status": "ok"}

@app.get("/api/ciudad3d/manzanas_atipicas")
def get_ciudad3d_manzanas_atipicas(current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a Ciudad 3D")
    
    query = """
    SELECT m.seccion, m.manzana, m.barrio, m.comuna, m.gedo_documento, m.id_expediente, m.expediente, m.fecha_egreso,
           COALESCE(w.estado, 'Pendiente') AS estado,
           w.analista_asignado,
           w.disposicion,
           w.archivo_trazado
    FROM public.mv_morfologia_frente_interno_disposiciones m
    LEFT JOIN public.manzanas_atipicas_workflow w ON m.seccion = w.seccion AND m.manzana = w.manzana
    ORDER BY m.barrio, m.seccion, m.manzana
    """
    try:
        with engine.connect() as conn:
            res = conn.execute(text(query)).fetchall()
            return [
                {
                    "seccion": r[0],
                    "manzana": r[1],
                    "barrio": r[2] if r[2] else "SIN BARRIO",
                    "comuna": r[3] if r[3] else "SIN COMUNA",
                    "gedo_documento": r[4] if r[4] else "",
                    "id_expediente": r[5] if r[5] else "",
                    "expediente": r[6] if r[6] else "",
                    "fecha_egreso": str(r[7]) if r[7] else "",
                    "estado": r[8],
                    "analista_asignado": r[9] if r[9] else "",
                    "disposicion": r[10] if r[10] else "",
                    "archivo_trazado": r[11] if r[11] else ""
                }
                for r in res
            ]
    except Exception as e:
        logger.error(f"Error fetching atypical blocks: {e}")
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")

class AssignRequest(BaseModel):
    seccion: str
    manzana: str

@app.post("/api/ciudad3d/manzanas_atipicas/assign")
def assign_manzana_atipica(req: AssignRequest, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("lfi_dibujar"):
        raise HTTPException(status_code=403, detail="No tiene permisos de dibujo de LFI ('lfi_dibujar') para asignarse manzanas.")
    
    with engine.begin() as conn:
        existing = conn.execute(text("""
            SELECT estado, analista_asignado FROM public.manzanas_atipicas_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": req.seccion, "m": req.manzana}).fetchone()
        
        if existing:
            if existing[0] != 'Pendiente':
                raise HTTPException(status_code=400, detail=f"Esta manzana ya está en estado '{existing[0]}'")
            
        conn.execute(text("""
            INSERT INTO public.manzanas_atipicas_workflow (seccion, manzana, estado, analista_asignado, updated_at)
            VALUES (:s, :m, 'En curso', :a, CURRENT_TIMESTAMP)
            ON CONFLICT (seccion, manzana) 
            DO UPDATE SET estado = 'En curso', analista_asignado = :a, updated_at = CURRENT_TIMESTAMP
        """), {"s": req.seccion, "m": req.manzana, "a": current_user.username})
        
    return {"status": "ok", "estado": "En curso", "analista_asignado": current_user.username}

class NoteRequest(BaseModel):
    seccion: str
    manzana: str
    nota: str

@app.get("/api/ciudad3d/manzanas_atipicas/notes")
def get_manzana_atipica_notes(seccion: str, manzana: str, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a Ciudad 3D")
    
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT n.id, n.username, n.nota, n.created_at, u.full_name
            FROM public.manzanas_atipicas_notes n
            LEFT JOIN public.auth_users u ON n.username = u.username
            WHERE n.seccion = :s AND n.manzana = :m
            ORDER BY n.created_at DESC
        """), {"s": seccion, "m": manzana}).fetchall()
        
        return [
            {
                "id": r[0],
                "username": r[1],
                "nota": r[2],
                "created_at": str(r[3]),
                "full_name": r[4] if r[4] else r[1]
            }
            for r in res
        ]

@app.post("/api/ciudad3d/manzanas_atipicas/notes")
def add_manzana_atipica_note(req: NoteRequest, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a Ciudad 3D")
    
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO public.manzanas_atipicas_notes (seccion, manzana, username, nota, created_at)
            VALUES (:s, :m, :u, :n, CURRENT_TIMESTAMP)
        """), {"s": req.seccion, "m": req.manzana, "u": current_user.username, "n": req.nota})
        
    return {"status": "ok"}

@app.post("/api/ciudad3d/manzanas_atipicas/upload")
async def upload_trazado(
    seccion: str = Form(...),
    manzana: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not current_user.permissions.get("lfi_dibujar"):
        raise HTTPException(status_code=403, detail="No tiene permisos de dibujo de LFI ('lfi_dibujar') para subir archivos.")
        
    with engine.connect() as conn:
        existing = conn.execute(text("""
            SELECT analista_asignado, estado FROM public.manzanas_atipicas_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": seccion, "m": manzana}).fetchone()
        
        if not existing:
            raise HTTPException(status_code=400, detail="Esta manzana no ha sido asignada ni iniciada.")
        if existing[0] != current_user.username and current_user.role.lower() not in ['admin', 'administrador']:
            raise HTTPException(status_code=403, detail=f"Esta manzana está asignada a {existing[0]}, no puede subir el archivo.")

    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "trazados"))
    os.makedirs(upload_dir, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1]
    safe_filename = f"{seccion}-{manzana}-{int(time.time())}{file_ext}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        logger.error(f"Error saving uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Error interno al guardar el archivo.")
        
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE public.manzanas_atipicas_workflow
            SET estado = 'Para revisión', archivo_trazado = :f, updated_at = CURRENT_TIMESTAMP
            WHERE seccion = :s AND manzana = :m
        """), {"s": seccion, "m": manzana, "f": safe_filename})
        
    return {"status": "ok", "estado": "Para revisión", "archivo_trazado": safe_filename}

class ReviewRequest(BaseModel):
    seccion: str
    manzana: str
    decision: str
    comentario: Optional[str] = None
    disposicion: Optional[str] = None

@app.post("/api/ciudad3d/manzanas_atipicas/review")
def review_manzana_atipica(req: ReviewRequest, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("lfi_revisar"):
        raise HTTPException(status_code=403, detail="No tiene permisos de revisión de LFI ('lfi_revisar') para revisar manzanas.")
        
    with engine.begin() as conn:
        existing = conn.execute(text("""
            SELECT estado FROM public.manzanas_atipicas_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": req.seccion, "m": req.manzana}).fetchone()
        
        if not existing or existing[0] != 'Para revisión':
            raise HTTPException(status_code=400, detail="Esta manzana no está en estado 'Para revisión'")
            
        new_state = 'Subir a Ciudad 3D' if req.decision.upper() == 'OK' else 'En curso'
        
        if req.disposicion:
            conn.execute(text("""
                UPDATE public.manzanas_atipicas_workflow
                SET estado = :state, disposicion = :disp, updated_at = CURRENT_TIMESTAMP
                WHERE seccion = :s AND manzana = :m
            """), {"state": new_state, "disp": req.disposicion, "s": req.seccion, "m": req.manzana})
        else:
            conn.execute(text("""
                UPDATE public.manzanas_atipicas_workflow
                SET estado = :state, updated_at = CURRENT_TIMESTAMP
                WHERE seccion = :s AND manzana = :m
            """), {"state": new_state, "s": req.seccion, "m": req.manzana})
            
        if req.comentario:
            note_text = f"*** REVISIÓN [{req.decision.upper()}]: {req.comentario} ***"
            conn.execute(text("""
                INSERT INTO public.manzanas_atipicas_notes (seccion, manzana, username, nota, created_at)
                VALUES (:s, :m, :u, :n, CURRENT_TIMESTAMP)
            """), {"s": req.seccion, "m": req.manzana, "u": current_user.username, "n": note_text})
            
    return {"status": "ok", "estado": new_state}

@app.get("/api/ciudad3d/manzanas_atipicas/download_trazado")
def download_trazado_file(seccion: str, manzana: str, token: Optional[str] = Query(None), current_user: User = Depends(get_current_user_from_param_or_header)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a esta sección")
        
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT archivo_trazado FROM public.manzanas_atipicas_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": seccion, "m": manzana}).fetchone()
        
        if not row or not row[0]:
            raise HTTPException(status_code=404, detail="No hay trazado subido para esta manzana.")
            
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "trazados", row[0]))
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="El archivo físico no fue encontrado en el servidor.")
            
        return FileResponse(file_path, filename=row[0])

class DisposicionRequest(BaseModel):
    seccion: str
    manzana: str
    disposicion: str

@app.post("/api/ciudad3d/manzanas_atipicas/disposicion")
def update_manzana_atipica_disposicion(req: DisposicionRequest, current_user: User = Depends(get_current_user)):
    if not (current_user.permissions.get("lfi_dibujar") or current_user.permissions.get("lfi_revisar") or current_user.role.lower() in ['troneras', 'troneras-visor', 'admin', 'administrador']):
        raise HTTPException(status_code=403, detail="No tiene permisos de dibujo o revisión de LFI ('lfi_dibujar'/'lfi_revisar') para actualizar la disposición.")
        
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO public.manzanas_atipicas_workflow (seccion, manzana, disposicion, updated_at)
            VALUES (:s, :m, :d, CURRENT_TIMESTAMP)
            ON CONFLICT (seccion, manzana)
            DO UPDATE SET disposicion = :d, updated_at = CURRENT_TIMESTAMP
        """), {"s": req.seccion, "m": req.manzana, "d": req.disposicion})
        
    return {"status": "ok"}

@app.get("/api/ciudad3d/dxf/download")
async def download_manzana_dxf(
    seccion: str,
    manzana: str,
    token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_from_param_or_header)
):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a Ciudad 3D")
        
    import os
    import tempfile
    import warnings
    from starlette.background import BackgroundTasks
    from fastapi.responses import FileResponse
    
    warnings.filterwarnings("ignore")
    os.environ["DXF_WRITE_HATCH"] = "FALSE"
    
    try:
        import geopandas as gpd
        import pandas as pd
        import ezdxf
        from ezdxf.enums import TextEntityAlignment
        from shapely.geometry import LineString, MultiLineString
        import fiona
    except ImportError as ie:
        logger.error(f"Missing geospatial dependencies for DXF generation: {ie}")
        raise HTTPException(status_code=500, detail="El servidor no tiene instaladas las dependencias cartográficas.")
        
    def extract_lines(geom):
        if geom is None or geom.is_empty:
            return []
        gtype = geom.geom_type
        if gtype == 'Polygon':
            lines = [LineString(geom.exterior.coords)]
            for hole in geom.interiors:
                lines.append(LineString(hole.coords))
            return lines
        elif gtype == 'MultiPolygon':
            lines = []
            for poly in geom.geoms:
                lines.extend(extract_lines(poly))
            return lines
        elif gtype == 'LineString':
            return [geom]
        elif gtype == 'MultiLineString':
            return list(geom.geoms)
        elif gtype == 'GeometryCollection':
            lines = []
            for sub_geom in geom.geoms:
                lines.extend(extract_lines(sub_geom))
            return lines
        return []

    def polygon_to_boundary(geom):
        lines = extract_lines(geom)
        if not lines:
            return None
        return MultiLineString(lines)

    sec_escaped = seccion.strip()
    m_val = manzana.strip()
    
    if not sec_escaped or not m_val:
        raise HTTPException(status_code=400, detail="La sección y la manzana son obligatorias")
        
    sec_clean = sec_escaped.replace("'", "''")
    m_clean = m_val.replace("'", "''")
    
    m_layers = {}
    
    try:
        with geo_engine.connect() as conn:
            # 1. Manzanas
            query_manzanas = f"SELECT geom, seccion, manzana FROM manzanas WHERE seccion = '{sec_clean}' AND manzana = '{m_clean}' AND geom IS NOT NULL"
            gdf_manzanas = gpd.read_postgis(query_manzanas, con=conn, geom_col="geom", crs="EPSG:3857")
            if gdf_manzanas.empty:
                raise HTTPException(status_code=404, detail=f"No se encontró la manzana {m_val} en la sección {sec_escaped}")
            gdf_manzanas = gdf_manzanas.to_crs("EPSG:22186")
            
            m_boundary = gdf_manzanas.copy()
            m_boundary['geometry'] = m_boundary.geometry.apply(polygon_to_boundary)
            m_layers['manzanas'] = m_boundary
            
            # 2. Parcelas
            query_parcelas = f"SELECT geom, smp, seccion, manzana FROM cur_parcelas_ok WHERE seccion = '{sec_clean}' AND manzana = '{m_clean}' AND geom IS NOT NULL"
            gdf_parcelas = gpd.read_postgis(query_parcelas, con=conn, geom_col="geom", crs="EPSG:22186")
            if not gdf_parcelas.empty:
                m_parcelas = gdf_parcelas.copy()
                m_parcelas['geometry'] = m_parcelas.geometry.apply(polygon_to_boundary)
                m_layers['parcelas'] = m_parcelas
                
            # 3. LFI
            query_lfi = f"SELECT geom, seccion, manzana FROM mdr_lineadefrenteinterno WHERE seccion = '{sec_clean}' AND manzana = '{m_clean}' AND geom IS NOT NULL"
            gdf_lfi = gpd.read_postgis(query_lfi, con=conn, geom_col="geom", crs="EPSG:22186")
            if not gdf_lfi.empty:
                m_layers['lfi'] = gdf_lfi
                
            # 4. LIB
            query_lib = f"SELECT geom, seccion, manzana FROM mdr_lineadebasamento WHERE seccion = '{sec_clean}' AND manzana = '{m_clean}' AND geom IS NOT NULL"
            gdf_lib = gpd.read_postgis(query_lib, con=conn, geom_col="geom", crs="EPSG:22186")
            if not gdf_lib.empty:
                m_layers['lib'] = gdf_lib
                
            # 5. Troneras
            query_troneras = f"SELECT geom, seccion, manzana, id_tronera, sm, comuna, irregular FROM mdr_troneras WHERE seccion = '{sec_clean}' AND manzana = '{m_clean}' AND geom IS NOT NULL"
            gdf_troneras = gpd.read_postgis(query_troneras, con=conn, geom_col="geom", crs="EPSG:22186")
            if not gdf_troneras.empty:
                m_troneras_si = gdf_troneras[gdf_troneras['irregular'] == 'NO'].copy()
                if not m_troneras_si.empty:
                    m_troneras_si['geometry'] = m_troneras_si.geometry.apply(polygon_to_boundary)
                    m_layers['Tronera SI'] = m_troneras_si
                    
                m_irregular = gdf_troneras[gdf_troneras['irregular'] == 'SI'].copy()
                if not m_irregular.empty:
                    m_irregular['geometry'] = m_irregular.geometry.apply(polygon_to_boundary)
                    m_layers['Irregular'] = m_irregular
                    
            m_smps = []
            if not gdf_parcelas.empty:
                m_smps = gdf_parcelas['smp'].dropna().unique().tolist()
                
            if m_smps:
                smps_str = ",".join([f"'{s}'" for s in m_smps])
                
                # 6. Banda Minima
                query_bm = f"SELECT geom, smp FROM mdr_banda_minima WHERE smp IN ({smps_str}) AND geom IS NOT NULL"
                try:
                    gdf_bm = gpd.read_postgis(query_bm, con=conn, geom_col="geom", crs="EPSG:22186")
                    if not gdf_bm.empty:
                        gdf_bm['geometry'] = gdf_bm.geometry.apply(polygon_to_boundary)
                        m_layers['banda_minima'] = gdf_bm
                except Exception:
                    pass
                    
                # 7. LDF
                query_ldf = f"SELECT geom, smp FROM mdr_ldf_parc WHERE smp IN ({smps_str}) AND geom IS NOT NULL"
                try:
                    gdf_ldf = gpd.read_postgis(query_ldf, con=conn, geom_col="geom", crs="EPSG:22186")
                    if not gdf_ldf.empty:
                        m_layers['ldf'] = gdf_ldf
                except Exception:
                    pass
                    
                # 9. Tejido Consolidado
                query_tc = f"SELECT geometry AS geom, smp FROM mdr_tejidoconsolidado WHERE smp IN ({smps_str}) AND geometry IS NOT NULL"
                try:
                    gdf_consolidado = gpd.read_postgis(query_tc, con=conn, geom_col="geom", crs="EPSG:22186")
                    if not gdf_consolidado.empty:
                        m_layers['mdr_tejidoconsolidado'] = gdf_consolidado
                except Exception:
                    pass
                    
                # 10. Tejido Para Irregular
                query_tpi = f"SELECT geometry AS geom, smp FROM mdr_tejidoparairregular WHERE smp IN ({smps_str}) AND geometry IS NOT NULL"
                try:
                    gdf_tejido_irreg = gpd.read_postgis(query_tpi, con=conn, geom_col="geom", crs="EPSG:22186")
                    if not gdf_tejido_irreg.empty:
                        m_layers['mdr_tejidoparairregular'] = gdf_tejido_irreg
                except Exception:
                    pass

            # 8. Tejido
            query_tejido = f"SELECT geom, smp, LPAD(sec, 3, '0') AS seccion, man AS manzana, altura FROM tejido WHERE LPAD(sec, 3, '0') = '{sec_clean}' AND man = '{m_clean}' AND geom IS NOT NULL"
            m_tejido_data = []
            try:
                gdf_tejido = gpd.read_postgis(query_tejido, con=conn, geom_col="geom", crs="EPSG:3857")
                if not gdf_tejido.empty:
                    gdf_tejido = gdf_tejido.to_crs("EPSG:22186")
                    for idx, row in gdf_tejido.iterrows():
                        geom = row['geom']
                        alt = row.get('altura', None)
                        if geom and not geom.is_empty and alt is not None:
                            centroid = geom.centroid
                            m_tejido_data.append(((centroid.x, centroid.y), alt))
                    
                    gdf_tejido['geometry'] = gdf_tejido.geometry.apply(polygon_to_boundary)
                    m_layers['tejido'] = gdf_tejido
            except Exception:
                pass

        gdfs_to_combine = []
        for layer_name, gdf in m_layers.items():
            gdf_clean = gpd.GeoDataFrame({'geometry': gdf.geometry}, crs="EPSG:22186")
            gdf_clean['Layer'] = layer_name
            
            if layer_name == 'lib':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#ffd306)'
            elif layer_name == 'lfi':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#3579b1)'
            elif layer_name == 'banda_minima':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#e41a1c)'
            elif layer_name == 'tejido':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#808080)'
            elif layer_name == 'mdr_tejidoconsolidado':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#c0c0c0)'
            elif layer_name == 'mdr_tejidoparairregular':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#808080)'
            elif layer_name == 'manzanas':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#404040)'
            elif layer_name == 'parcelas':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#606060)'
            elif layer_name == 'Tronera SI':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#3579b1)'
            elif layer_name == 'Irregular':
                gdf_clean['OGR_STYLE'] = 'PEN(c:#e41a1c)'
            else:
                gdf_clean['OGR_STYLE'] = 'PEN(c:#000000)'
                
            gdfs_to_combine.append(gdf_clean)

        if not gdfs_to_combine:
            raise HTTPException(status_code=404, detail="No se encontraron capas vectoriales para esta manzana.")
            
        combined_gdf = pd.concat(gdfs_to_combine, ignore_index=True)
        combined_gdf = gpd.GeoDataFrame(combined_gdf, geometry='geometry', crs="EPSG:22186")
        combined_gdf = combined_gdf[~combined_gdf.geometry.is_empty].copy()
        
        if len(combined_gdf) == 0:
            raise HTTPException(status_code=404, detail="No se encontraron datos espaciales válidos para esta manzana.")

        temp_fd, temp_path = tempfile.mkstemp(suffix=".dxf")
        os.close(temp_fd)
        
        with fiona.Env(DXF_WRITE_HATCH="FALSE"):
            combined_gdf.to_file(temp_path, driver="DXF", layer="entities")
            
        try:
            doc = ezdxf.readfile(temp_path)
            msp = doc.modelspace()
            
            layer_colors = {
                'lib': (2, (255, 211, 6)),
                'lfi': (141, (53, 121, 177)),
                'banda_minima': (1, (228, 26, 28)),
                'tejido': (8, (128, 128, 128)),
                'mdr_tejidoconsolidado': (9, (192, 192, 192)),
                'mdr_tejidoparairregular': (8, (128, 128, 128)),
                'manzanas': (250, (64, 64, 64)),
                'parcelas': (252, (96, 96, 96)),
                'Tronera SI': (141, (53, 121, 177)),
                'Irregular': (1, (228, 26, 28))
            }
            
            for l_name, (aci, rgb) in layer_colors.items():
                if l_name in doc.layers:
                    layer = doc.layers.get(l_name)
                    layer.color = aci
                    layer.rgb = rgb
                    if l_name in ('mdr_tejidoconsolidado', 'mdr_tejidoparairregular'):
                        layer.transparency = 0.5
                        
            hatch_layers = ('mdr_tejidoconsolidado', 'mdr_tejidoparairregular')
            for l_name in hatch_layers:
                if l_name in doc.layers:
                    polylines = [e for e in msp if e.dxf.layer == l_name and e.dxftype() in ('LWPOLYLINE', 'POLYLINE')]
                    for poly in polylines:
                        if poly.dxftype() == 'LWPOLYLINE':
                            pts = [(p[0], p[1]) for p in poly.get_points()]
                        else:
                            pts = [(v.dxf.location.x, v.dxf.location.y) for v in poly.vertices]
                            
                        if len(pts) >= 3:
                            h_color = doc.layers.get(l_name).color
                            hatch = msp.add_hatch(color=h_color, dxfattribs={'layer': l_name})
                            hatch.set_pattern_fill('SOLID')
                            hatch.paths.add_polyline_path(pts, is_closed=True)
                            
                        msp.delete_entity(poly)
                        
            if m_tejido_data:
                if 'ArialBold' not in doc.styles:
                    style = doc.styles.new('ArialBold', dxfattribs={'font': 'Arial.ttf'})
                    style.set_extended_font_data(family='Arial', italic=False, bold=True)
                    
                h_color = doc.layers.get('tejido').color if 'tejido' in doc.layers else 8
                for pos, alt in m_tejido_data:
                    try:
                        alt_val = float(alt)
                        text_str = f"{alt_val:.1f}"
                    except (ValueError, TypeError):
                        text_str = str(alt)
                        
                    t = msp.add_text(text_str, dxfattribs={
                        'layer': 'tejido',
                        'color': h_color,
                        'height': 0.375,
                        'style': 'ArialBold'
                    })
                    t.set_placement(pos, align=TextEntityAlignment.MIDDLE_CENTER)
                    
            doc.save()
        except Exception as e_dxf:
            logger.warning(f"Error applying ACI colors with ezdxf: {e_dxf}")
            
        def clean_temp():
            try:
                os.remove(temp_path)
            except Exception:
                pass
                
        background_tasks = BackgroundTasks()
        background_tasks.add_task(clean_temp)
        
        return FileResponse(
            temp_path,
            media_type="application/dxf",
            filename=f"{sec_escaped}-{m_val}.dxf",
            background=background_tasks
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating DXF for {sec_escaped}-{m_val}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno en la generación del DXF: {e}")



if __name__ == "__main__":
    import uvicorn
    import sys
    import os
    
    # Agregar el directorio raíz al path para que uvicorn encuentre el módulo 'backend'
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
        
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

