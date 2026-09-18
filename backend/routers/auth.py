import os
import re
import json
import logging
import bcrypt
from typing import List, Dict, Any, Optional
from collections import defaultdict
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text

# Import database and authentication utilities
from database import engine
from schemas import (
    Token, User, PasswordChange, UserUpdate, RoleCreate, RoleUpdate,
    MetaUpdateRequest, MetaCreateRequest, UserCreate, FamiliaUpdate, FamiliaCreate,
    BuzonAccesoUpdate, AddAnalystRequest
)
from auth_utils import (
    verify_password, get_password_hash, create_access_token,
    get_resolved_permissions, get_current_user
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication & Admin"])

# Helper function
def format_capital(val):
    if not val:
        return ""
    val = str(val).strip()
    if not val:
        return ""
    return val[0].upper() + val[1:].lower()

# --- Endpoints de Autenticación ---

@router.post("/api/auth/login", response_model=Token)
async def login(from_data: OAuth2PasswordRequestForm = Depends()):
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

@router.post("/api/auth/change-password")
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

@router.get("/api/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/api/health")
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

# --- Endpoints de Admin de Usuarios ---

@router.get("/api/admin/users")
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

@router.put("/api/admin/users/{username}")
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

@router.post("/api/admin/users")
async def create_user(user_data: UserCreate, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        hashed = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        perms_json = json.dumps(user_data.permissions) if user_data.permissions is not None else None
        
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO auth_users (username, password_hash, role, full_name, sector, email, permissions) 
                    VALUES (:u, :p, :r, :fn, :s, :e, :perms)
                """),
                {
                    "u": user_data.username.strip(),
                    "p": hashed,
                    "r": user_data.role,
                    "fn": user_data.full_name or user_data.username.strip(),
                    "s": user_data.sector or "General",
                    "e": user_data.email or "",
                    "perms": perms_json
                }
            )
        return {"status": "ok", "message": f"Usuario {user_data.username} creado correctamente"}
    except Exception as e:
        logger.error(f"Error creando usuario: {e}")
        raise HTTPException(status_code=400, detail=f"Error al crear usuario: {str(e)}")

@router.delete("/api/admin/users/{username}")
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

@router.get("/api/admin/roles")
async def list_roles(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT role_name, permissions FROM auth_roles ORDER BY role_name"))
            return [dict(r._mapping) for r in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/admin/roles")
async def create_role(role_data: RoleCreate, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    r_name = role_data.role_name.strip().lower()
    if not r_name:
        raise HTTPException(status_code=400, detail="El nombre del rol no puede estar vacío")
    try:
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

@router.put("/api/admin/roles/{role_name}")
async def update_role(role_name: str, role_update: RoleUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE auth_roles SET permissions = :p WHERE role_name = :n"),
                {"p": json.dumps(role_update.permissions), "n": role_name}
            )
            return {"status": "ok", "message": "Permisos del rol actualizados"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/admin/roles/{role_name}")
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

@router.get("/api/admin/familias")
async def list_admin_familias(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, nombre, tratas FROM public.cfg_tramites_familias ORDER BY id"))
            return [dict(r._mapping) for r in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/admin/familias")
async def create_admin_familia(data: FamiliaCreate, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    name_clean = data.nombre.strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="El nombre de la familia no puede estar vacío")
    try:
        clean_tratas = [t.strip().upper() for t in data.tratas if t.strip()]
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO public.cfg_tramites_familias (nombre, tratas) VALUES (:n, :t)"),
                {"n": name_clean, "t": json.dumps(clean_tratas)}
            )
            return {"status": "ok", "message": f"Familia {name_clean} creada con éxito"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al crear familia (tal vez ya existe): {str(e)}")

@router.put("/api/admin/familias/{nombre}")
async def update_admin_familia(nombre: str, data: FamiliaUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        clean_tratas = [t.strip().upper() for t in data.tratas if t.strip()]
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE public.cfg_tramites_familias SET tratas = :t WHERE nombre = :n"),
                {"t": json.dumps(clean_tratas), "n": nombre}
            )
            return {"status": "ok", "message": f"Familia {nombre} actualizada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/admin/familias/{nombre}")
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

# --- Configuración de Buzones / Analistas por Gerencia (Admin Buzones para Análisis) ---

def _ensure_buzones_adicionales_table(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.cfg_buzones_areas (
            gerencia_key VARCHAR(100) PRIMARY KEY,
            nombre VARCHAR(150) NOT NULL,
            direccion VARCHAR(100) NOT NULL,
            es_sistema BOOLEAN DEFAULT FALSE,
            creado_el TIMESTAMP DEFAULT NOW()
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.cfg_gerencias_buzones_adicionales (
            id SERIAL PRIMARY KEY,
            gerencia VARCHAR(100) NOT NULL,
            usuario_buzon VARCHAR(150) NOT NULL,
            creado_el TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_gerencia_usuario UNIQUE (gerencia, usuario_buzon)
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.cfg_analistas_areas (
            id SERIAL PRIMARY KEY,
            direccion VARCHAR(100),
            gerencia VARCHAR(100) NOT NULL,
            usuario_sade VARCHAR(150) NOT NULL,
            nombre_completo VARCHAR(255),
            tipo VARCHAR(50) DEFAULT 'analista',
            activo BOOLEAN DEFAULT TRUE,
            creado_el TIMESTAMP DEFAULT NOW()
        )
    """))
    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_cfg_analistas_areas_ger_usr 
        ON public.cfg_analistas_areas (gerencia, usuario_sade);
    """))
    
    # Pre-cargar áreas por defecto si la tabla está vacía
    area_count = conn.execute(text("SELECT COUNT(*) FROM public.cfg_buzones_areas")).scalar()
    if not area_count:
        default_areas = [
            ('catastro', 'Catastro', 'DGROC', True),
            ('instalaciones', 'Instalaciones', 'DGROC', True),
            ('conforme', 'Conforme a Obra', 'DGROC', True),
            ('contable', 'Contable', 'DGROC', True),
            ('etapa_proyecto', 'Etapa Proyecto', 'DGROC', True),
            ('aviso_obra', 'Aviso de Obra', 'DGROC', True),
            ('morfologia', 'Morfología', 'DGIUR', True),
            ('aph', 'APH', 'DGIUR', True),
            ('usos', 'Usos', 'DGIUR', True),
            ('publico_privado', 'Público Privado', 'DGIUR', True),
            ('copua', 'COPUA', 'DGIUR', True),
            ('privada', 'Privada', 'DGIUR', True)
        ]
        for k, nom, dir_name, es_sis in default_areas:
            conn.execute(text("""
                INSERT INTO public.cfg_buzones_areas (gerencia_key, nombre, direccion, es_sistema)
                VALUES (:k, :nom, :dir, :es_sis)
                ON CONFLICT (gerencia_key) DO NOTHING
            """), {"k": k, "nom": nom, "dir": dir_name, "es_sis": es_sis})

class CreateAreaRequest(BaseModel):
    nombre: str
    direccion: str = "DGROC"
    gerencia_key: Optional[str] = None

class MoveBuzonAnalistaRequest(BaseModel):
    usuario_buzon: str
    gerencia_origen: str
    gerencia_destino: str

class GerenciaBuzonAdicionalRequest(BaseModel):
    usuario_buzon: str

@router.get("/api/admin/gerencias-buzones")
async def list_gerencias_buzones_config(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.begin() as conn:
            _ensure_buzones_adicionales_table(conn)
            
            # Obtener catálogo de áreas registradas
            areas_rows = conn.execute(text("""
                SELECT gerencia_key, nombre, direccion, COALESCE(es_sistema, false) as es_sistema
                FROM public.cfg_buzones_areas
                ORDER BY direccion, nombre
            """)).fetchall()
            
            known_areas = {r[0]: {"nombre": r[1], "direccion": r[2], "es_sistema": r[3]} for r in areas_rows}

            # Obtener analistas oficiales y buzones de ingreso por gerencia desde cfg_gestion_metas (Default)
            cfg_rows = conn.execute(text("""
                SELECT 
                    LOWER(TRIM(gerencia)) as gerencia,
                    COALESCE(ARRAY(SELECT UPPER(TRIM(b)) FROM unnest(buzones_ingreso) b), ARRAY[]::text[]) as buzones_ingreso,
                    COALESCE(ARRAY(SELECT UPPER(TRIM(a)) FROM unnest(analistas_oficiales) a), ARRAY[]::text[]) as analistas_oficiales
                FROM cfg_gestion_metas
            """)).fetchall()

            defaults_by_gerencia = defaultdict(set)
            for cr in cfg_rows:
                g = cr[0]
                target_keys = [g]
                if g == 'regularizacion':
                    target_keys.append('conforme')
                elif g == 'conforme':
                    target_keys.append('regularizacion')

                for tk in target_keys:
                    for b in cr[1]:
                        if b:
                            defaults_by_gerencia[tk].add(b)
                    for a in cr[2]:
                        if a:
                            defaults_by_gerencia[tk].add(a)

            # Obtener analistas registrados en cfg_analistas_areas
            try:
                area_analistas_rows = conn.execute(text("""
                    SELECT LOWER(TRIM(gerencia)), UPPER(TRIM(usuario_sade)), direccion
                    FROM public.cfg_analistas_areas
                    WHERE activo = true
                """)).fetchall()
                for ar in area_analistas_rows:
                    g = ar[0]
                    u = ar[1]
                    if g not in known_areas:
                        known_areas[g] = {"nombre": g.replace('_', ' ').title(), "direccion": ar[2] or "DGROC", "es_sistema": False}
                    defaults_by_gerencia[g].add(u)
            except Exception:
                pass

            # Obtener buzones/analistas adicionales configurados en cfg_gerencias_buzones_adicionales
            adic_rows = conn.execute(text("""
                SELECT LOWER(TRIM(gerencia)), UPPER(TRIM(usuario_buzon))
                FROM public.cfg_gerencias_buzones_adicionales
            """)).fetchall()

            adicionales_by_gerencia = defaultdict(set)
            for ar in adic_rows:
                g = ar[0]
                target_keys = [g]
                if g == 'regularizacion':
                    target_keys.append('conforme')
                elif g == 'conforme':
                    target_keys.append('regularizacion')
                for tk in target_keys:
                    adicionales_by_gerencia[tk].add(ar[1])
                    if tk not in known_areas:
                        known_areas[tk] = {"nombre": tk.replace('_', ' ').title(), "direccion": "DGROC", "es_sistema": False}

            # Agregar cualquier gerencia de cfg_gestion_metas a known_areas si faltara
            for g in defaults_by_gerencia:
                if g not in known_areas:
                    known_areas[g] = {"nombre": g.replace('_', ' ').title(), "direccion": "DGROC", "es_sistema": False}

            # Mapa de nombres desde datos_usuario
            nombres_sql = conn.execute(text("""
                SELECT UPPER(TRIM(usuario)) as u, 
                       UPPER(TRIM(COALESCE(NULLIF(TRIM(apellido_nombre), ''), NULLIF(TRIM(CONCAT(nombre, ' ', apellido)), '')))) as nom
                FROM datos_usuario
            """)).fetchall()
            nombres_map = {r[0]: r[1] for r in nombres_sql if r[0] and r[1]}

            result = []
            for g_key, info in known_areas.items():
                def_set = defaults_by_gerencia.get(g_key, set())
                adic_set = adicionales_by_gerencia.get(g_key, set())
                
                # Excluir de def_set lo que ya esté en adic_set para no duplicar
                def_set_clean = def_set - adic_set

                def_list = [{
                    "usuario": u,
                    "nombre": nombres_map.get(u, u),
                    "es_default": True,
                    "tipo": 'buzon' if ('-' in u or u.startswith('DG') or u.startswith('SEC')) else 'analista'
                } for u in sorted(def_set_clean)]

                adic_list = [{
                    "usuario": u,
                    "nombre": nombres_map.get(u, u),
                    "es_default": False,
                    "tipo": 'buzon' if ('-' in u or u.startswith('DG') or u.startswith('SEC')) else 'analista'
                } for u in sorted(adic_set)]

                all_items = def_list + adic_list

                result.append({
                    "gerencia": g_key,
                    "nombre": info["nombre"],
                    "direccion": info["direccion"],
                    "label": f"{info['direccion']} - {info['nombre']}",
                    "es_personalizada": not info["es_sistema"],
                    "default_analistas": def_list,
                    "adicionales_analistas": adic_list,
                    "analistas": all_items,
                    "total_analistas": len(all_items)
                })

            # Ordenar por direccion y luego nombre
            result.sort(key=lambda x: (x["direccion"], x["nombre"]))
            return result
    except Exception as e:
        logger.error(f"Error en list_gerencias_buzones_config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/admin/gerencias-buzones/areas")
async def create_gerencia_buzon_area(
    data: CreateAreaRequest,
    current_user: User = Depends(get_current_user)
):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    
    nombre_clean = data.nombre.strip()
    if not nombre_clean:
        raise HTTPException(status_code=400, detail="El nombre del área es requerido.")
    
    key_clean = (data.gerencia_key or nombre_clean).strip().lower()
    # Sanitizar key a formato alfanumérico con guiones bajos
    key_clean = re.sub(r'[^a-z0-9_]', '_', key_clean)
    key_clean = re.sub(r'_+', '_', key_clean).strip('_')
    
    dir_clean = data.direccion.strip().upper() or "DGROC"

    try:
        with engine.begin() as conn:
            _ensure_buzones_adicionales_table(conn)
            conn.execute(text("""
                INSERT INTO public.cfg_buzones_areas (gerencia_key, nombre, direccion, es_sistema)
                VALUES (:k, :nom, :dir, FALSE)
                ON CONFLICT (gerencia_key) DO UPDATE 
                SET nombre = EXCLUDED.nombre,
                    direccion = EXCLUDED.direccion
            """), {"k": key_clean, "nom": nombre_clean, "dir": dir_clean})

            return {"status": "ok", "gerencia": key_clean, "nombre": nombre_clean, "direccion": dir_clean, "message": f"Área '{nombre_clean}' creada exitosamente."}
    except Exception as e:
        logger.error(f"Error creating buzon area: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/admin/gerencias-buzones/areas/{gerencia}")
async def delete_gerencia_buzon_area(
    gerencia: str,
    current_user: User = Depends(get_current_user)
):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    
    g_clean = gerencia.strip().lower()
    try:
        with engine.begin() as conn:
            _ensure_buzones_adicionales_table(conn)
            
            # Verificar si es área de sistema
            is_sys = conn.execute(text("SELECT es_sistema FROM public.cfg_buzones_areas WHERE gerencia_key = :g"), {"g": g_clean}).scalar()
            if is_sys:
                raise HTTPException(status_code=400, detail="No se pueden eliminar áreas nativas del sistema.")

            conn.execute(text("DELETE FROM public.cfg_buzones_areas WHERE gerencia_key = :g"), {"g": g_clean})
            conn.execute(text("DELETE FROM public.cfg_gerencias_buzones_adicionales WHERE gerencia = :g"), {"g": g_clean})
            conn.execute(text("DELETE FROM public.cfg_analistas_areas WHERE gerencia = :g"), {"g": g_clean})

            return {"status": "ok", "message": f"Área '{g_clean}' eliminada exitosamente."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting buzon area: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/admin/gerencias-buzones/mover")
async def move_gerencia_buzon_analista(
    data: MoveBuzonAnalistaRequest,
    current_user: User = Depends(get_current_user)
):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    
    u_clean = data.usuario_buzon.strip().upper()
    orig_clean = data.gerencia_origen.strip().lower()
    dest_clean = data.gerencia_destino.strip().lower()

    if not u_clean or not orig_clean or not dest_clean:
        raise HTTPException(status_code=400, detail="Datos incompletos para el traslado.")
    if orig_clean == dest_clean:
        raise HTTPException(status_code=400, detail="El área de origen y destino deben ser distintas.")

    orig_keys = [orig_clean]
    if orig_clean == 'conforme':
        orig_keys.append('regularizacion')
    elif orig_clean == 'regularizacion':
        orig_keys.append('conforme')

    dest_key = 'regularizacion' if dest_clean == 'conforme' else dest_clean

    try:
        with engine.begin() as conn:
            _ensure_buzones_adicionales_table(conn)
            
            # 1. Quitar de gerencia origen
            # a) En cfg_gerencias_buzones_adicionales
            conn.execute(text("""
                DELETE FROM public.cfg_gerencias_buzones_adicionales 
                WHERE LOWER(TRIM(gerencia)) IN :g_list AND UPPER(TRIM(usuario_buzon)) = :u
            """), {"g_list": tuple(orig_keys), "u": u_clean})

            # b) En cfg_analistas_areas
            conn.execute(text("""
                DELETE FROM public.cfg_analistas_areas 
                WHERE LOWER(TRIM(gerencia)) IN :g_list AND UPPER(TRIM(usuario_sade)) = :u
            """), {"g_list": tuple(orig_keys), "u": u_clean})

            # c) En cfg_gestion_metas (remover de analistas_oficiales y buzones_ingreso del origen)
            for ok in orig_keys:
                rows = conn.execute(text("SELECT id, analistas_oficiales, buzones_ingreso FROM cfg_gestion_metas WHERE TRIM(LOWER(gerencia)) = :g"), {"g": ok}).fetchall()
                for r in rows:
                    c_analysts = [a for a in (r[1] or []) if a and a.strip().upper() != u_clean]
                    c_buzones = [b for b in (r[2] or []) if b and b.strip().upper() != u_clean]
                    conn.execute(text("UPDATE cfg_gestion_metas SET analistas_oficiales = :a, buzones_ingreso = :b WHERE id = :id"), {"a": c_analysts, "b": c_buzones, "id": r[0]})

            # 2. Agregar a gerencia destino
            # Determinar dirección de destino
            dest_dir = conn.execute(text("SELECT direccion FROM public.cfg_buzones_areas WHERE gerencia_key = :g"), {"g": dest_clean}).scalar()
            if not dest_dir:
                dest_dir = 'DGROC' if dest_clean in DGROC_GERENCIAS else ('DGIUR' if dest_clean in DGIUR_GERENCIAS else 'DGROC')
            
            # a) Insertar en cfg_gerencias_buzones_adicionales (idempotente)
            exists_adic = conn.execute(text("""
                SELECT 1 FROM public.cfg_gerencias_buzones_adicionales 
                WHERE LOWER(TRIM(gerencia)) = :g AND UPPER(TRIM(usuario_buzon)) = :u
            """), {"g": dest_clean, "u": u_clean}).scalar()
            if not exists_adic:
                conn.execute(text("""
                    INSERT INTO public.cfg_gerencias_buzones_adicionales (gerencia, usuario_buzon)
                    VALUES (:g, :u)
                """), {"g": dest_clean, "u": u_clean})

            # b) Insertar o actualizar en cfg_analistas_areas (idempotente sin requerir índice de conflicto)
            user_row = conn.execute(text("""
                SELECT UPPER(TRIM(usuario)) as u, 
                       UPPER(TRIM(COALESCE(NULLIF(TRIM(apellido_nombre), ''), NULLIF(TRIM(CONCAT(nombre, ' ', apellido)), '')))) as nom
                FROM public.datos_usuario 
                WHERE TRIM(UPPER(usuario)) = :u
            """), {"u": u_clean}).fetchone()
            nombre_completo = user_row[1] if (user_row and user_row[1]) else u_clean
            tipo = 'buzon' if ('-' in u_clean or u_clean.startswith('DG') or u_clean.startswith('SEC')) else 'analista'

            exists_analista = conn.execute(text("""
                SELECT id FROM public.cfg_analistas_areas 
                WHERE LOWER(TRIM(gerencia)) = :g AND UPPER(TRIM(usuario_sade)) = :u
            """), {"g": dest_clean, "u": u_clean}).fetchone()

            if exists_analista:
                conn.execute(text("""
                    UPDATE public.cfg_analistas_areas 
                    SET direccion = :dir, 
                        nombre_completo = COALESCE(:nom, nombre_completo), 
                        tipo = :tipo, 
                        activo = true 
                    WHERE id = :id
                """), {"dir": dest_dir, "nom": nombre_completo, "tipo": tipo, "id": exists_analista[0]})
            else:
                conn.execute(text("""
                    INSERT INTO public.cfg_analistas_areas (direccion, gerencia, usuario_sade, nombre_completo, tipo, activo)
                    VALUES (:dir, :ger, :usr, :nom, :tipo, true)
                """), {"dir": dest_dir, "ger": dest_clean, "usr": u_clean, "nom": nombre_completo, "tipo": tipo})

            return {"status": "ok", "message": f"{tipo.title()} {u_clean} trasladado exitosamente a {dest_clean.upper()}."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving buzon/analyst: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/admin/gerencias-buzones/{gerencia}")
async def add_gerencia_buzon_adicional(
    gerencia: str, 
    data: GerenciaBuzonAdicionalRequest, 
    current_user: User = Depends(get_current_user)
):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    
    g_clean = gerencia.strip().lower()
    if g_clean == 'conforme':
        g_clean = 'regularizacion'
    u_clean = data.usuario_buzon.strip().upper()
    if not u_clean:
        raise HTTPException(status_code=400, detail="Debe ingresar un usuario o buzón válido.")
    
    try:
        with engine.begin() as conn:
            _ensure_buzones_adicionales_table(conn)
            # a) Insertar en cfg_gerencias_buzones_adicionales (idempotente)
            exists_adic = conn.execute(text("""
                SELECT 1 FROM public.cfg_gerencias_buzones_adicionales 
                WHERE LOWER(TRIM(gerencia)) = :g AND UPPER(TRIM(usuario_buzon)) = :u
            """), {"g": g_clean, "u": u_clean}).scalar()
            if not exists_adic:
                conn.execute(text("""
                    INSERT INTO public.cfg_gerencias_buzones_adicionales (gerencia, usuario_buzon)
                    VALUES (:g, :u)
                """), {"g": g_clean, "u": u_clean})

            # También sincronizar en cfg_analistas_areas
            dest_dir = conn.execute(text("SELECT direccion FROM public.cfg_buzones_areas WHERE gerencia_key = :g"), {"g": g_clean}).scalar()
            if not dest_dir:
                dest_dir = 'DGROC' if g_clean in DGROC_GERENCIAS else ('DGIUR' if g_clean in DGIUR_GERENCIAS else 'DGROC')

            user_row = conn.execute(text("""
                SELECT UPPER(TRIM(usuario)) as u, 
                       UPPER(TRIM(COALESCE(NULLIF(TRIM(apellido_nombre), ''), NULLIF(TRIM(CONCAT(nombre, ' ', apellido)), '')))) as nom
                FROM public.datos_usuario 
                WHERE TRIM(UPPER(usuario)) = :u
            """), {"u": u_clean}).fetchone()
            nombre_completo = user_row[1] if (user_row and user_row[1]) else u_clean
            tipo = 'buzon' if ('-' in u_clean or u_clean.startswith('DG') or u_clean.startswith('SEC')) else 'analista'

            exists_analista = conn.execute(text("""
                SELECT id FROM public.cfg_analistas_areas 
                WHERE LOWER(TRIM(gerencia)) = :g AND UPPER(TRIM(usuario_sade)) = :u
            """), {"g": g_clean, "u": u_clean}).fetchone()

            if exists_analista:
                conn.execute(text("""
                    UPDATE public.cfg_analistas_areas 
                    SET direccion = :dir, 
                        nombre_completo = COALESCE(:nom, nombre_completo), 
                        tipo = :tipo, 
                        activo = true 
                    WHERE id = :id
                """), {"dir": dest_dir, "nom": nombre_completo, "tipo": tipo, "id": exists_analista[0]})
            else:
                conn.execute(text("""
                    INSERT INTO public.cfg_analistas_areas (direccion, gerencia, usuario_sade, nombre_completo, tipo, activo)
                    VALUES (:dir, :ger, :usr, :nom, :tipo, true)
                """), {"dir": dest_dir, "ger": g_clean, "usr": u_clean, "nom": nombre_completo, "tipo": tipo})

            return {"status": "ok", "message": f"Buzón/Analista {u_clean} agregado a la gerencia {g_clean.upper()}."}
    except Exception as e:
        logger.error(f"Error adding gerencia buzon adicional: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/admin/gerencias-buzones/{gerencia}/{usuario_buzon}")
async def delete_gerencia_buzon_adicional(
    gerencia: str, 
    usuario_buzon: str, 
    current_user: User = Depends(get_current_user)
):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    
    g_clean = gerencia.strip().lower()
    if g_clean == 'conforme':
        g_clean = 'regularizacion'
    u_clean = usuario_buzon.strip().upper()
    try:
        with engine.begin() as conn:
            _ensure_buzones_adicionales_table(conn)
            
            # 1. Eliminar de cfg_gerencias_buzones_adicionales
            conn.execute(text("""
                DELETE FROM public.cfg_gerencias_buzones_adicionales 
                WHERE (LOWER(TRIM(gerencia)) = :g OR (LOWER(TRIM(gerencia)) = 'conforme' AND :g = 'regularizacion')) AND UPPER(TRIM(usuario_buzon)) = :u
            """), {"g": g_clean, "u": u_clean})

            # 2. Eliminar de cfg_analistas_areas
            conn.execute(text("""
                DELETE FROM public.cfg_analistas_areas 
                WHERE (LOWER(TRIM(gerencia)) = :g OR (LOWER(TRIM(gerencia)) = 'conforme' AND :g = 'regularizacion')) AND UPPER(TRIM(usuario_sade)) = :u
            """), {"g": g_clean, "u": u_clean})

            # 3. Sincronizar cfg_gestion_metas
            rows = conn.execute(text("SELECT id, analistas_oficiales, buzones_ingreso FROM cfg_gestion_metas WHERE TRIM(LOWER(gerencia)) = :g"), {"g": g_clean}).fetchall()
            for r in rows:
                c_analysts = [a for a in (r[1] or []) if a and a.strip().upper() != u_clean]
                c_buzones = [b for b in (r[2] or []) if b and b.strip().upper() != u_clean]
                conn.execute(text("UPDATE cfg_gestion_metas SET analistas_oficiales = :a, buzones_ingreso = :b WHERE id = :id"), {"a": c_analysts, "b": c_buzones, "id": r[0]})

            return {"status": "ok", "message": f"Buzón/Analista {u_clean} removido de {g_clean.upper()}."}
    except Exception as e:
        logger.error(f"Error deleting gerencia buzon adicional: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Búsqueda de Usuarios SADE (Autocompletado Admin) ---

@router.get("/api/admin/sade_users/search")
async def search_sade_users(
    q: str = Query(..., min_length=2, description="Texto de búsqueda para usuario o apellido/nombre"),
    current_user: User = Depends(get_current_user)
):
    try:
        query_text = f"%{q.strip()}%"
        with engine.connect() as conn:
            sql = text("""
                SELECT 
                    UPPER(TRIM(usuario)) as usuario,
                    UPPER(TRIM(COALESCE(
                        NULLIF(TRIM(apellido_nombre), ''),
                        NULLIF(TRIM(CONCAT(nombre, ' ', apellido)), ''),
                        usuario
                    ))) as apellido_nombre,
                    COALESCE(codigo_sector_interno, '') as codigo_sector_interno,
                    COALESCE(mail, '') as mail
                FROM public.datos_usuario
                WHERE usuario IS NOT NULL 
                  AND (usuario ILIKE :q OR apellido_nombre ILIKE :q OR CONCAT(nombre, ' ', apellido) ILIKE :q)
                ORDER BY usuario
                LIMIT 20
            """)
            rows = conn.execute(sql, {"q": query_text}).fetchall()
            return [
                {
                    "usuario": r[0],
                    "apellido_nombre": r[1],
                    "codigo_sector_interno": r[2],
                    "mail": r[3]
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Error buscando usuarios SADE: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints de Analistas (Admin - Maestro de Analistas por Área) ---

@router.get("/api/admin/analistas")
async def list_admin_analistas(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.connect() as conn:
            # Traer analistas del maestro cfg_analistas_areas cruzando con datos_usuario
            result = conn.execute(text("""
                SELECT 
                    a.id,
                    a.direccion,
                    a.gerencia,
                    a.usuario_sade,
                    COALESCE(a.nombre_completo, du.apellido_nombre, CONCAT(du.nombre, ' ', du.apellido)) as nombre_completo,
                    a.tipo,
                    a.activo,
                    du.apellido,
                    du.nombre,
                    du.mail,
                    du.ocupacion,
                    du.numero_cuit
                FROM public.cfg_analistas_areas a
                LEFT JOIN public.datos_usuario du ON TRIM(UPPER(a.usuario_sade)) = TRIM(UPPER(du.usuario))
                ORDER BY a.direccion, a.gerencia, a.usuario_sade
            """)).fetchall()
            
            # Agrupar por gerencia
            gerencias_map = {}
            for row in result:
                g = row.gerencia
                d = row.direccion
                if g not in gerencias_map:
                    gerencias_map[g] = {
                        "gerencia": g,
                        "direccion": d,
                        "analistas": []
                    }
                
                gerencias_map[g]["analistas"].append({
                    "id": row.id,
                    "direccion": d,
                    "gerencia": g,
                    "usuario": row.usuario_sade,
                    "nombre_completo": row.nombre_completo or row.usuario_sade,
                    "apellido": format_capital(row.apellido),
                    "nombre": format_capital(row.nombre),
                    "mail": format_capital(row.mail),
                    "ocupacion": format_capital(row.ocupacion),
                    "numero_cuit": format_capital(row.numero_cuit),
                    "tipo": row.tipo,
                    "activo": row.activo
                })
            
            return list(gerencias_map.values())
    except Exception as e:
        logger.error(f"Error listing admin analysts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/admin/analistas/{gerencia}")
async def add_admin_analista(gerencia: str, req: AddAnalystRequest, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    
    usuario_to_add = req.usuario.strip().upper()
    g_clean = gerencia.strip().lower()
    if not usuario_to_add:
        raise HTTPException(status_code=400, detail="Debe ingresar un usuario válido.")
        
    DGROC_GERENCIAS = {'catastro', 'instalaciones', 'conforme', 'contable', 'etapa_proyecto', 'aviso_obra', 'regularizacion'}
    DGIUR_GERENCIAS = {'morfologia', 'aph', 'usos', 'publico_privado', 'copua', 'privada'}
    dir_name = 'DGROC' if g_clean in DGROC_GERENCIAS else ('DGIUR' if g_clean in DGIUR_GERENCIAS else 'SECGDU')

    try:
        with engine.begin() as conn:
            # 1. Obtener datos del usuario si existe en datos_usuario
            user_row = conn.execute(text("""
                SELECT UPPER(TRIM(usuario)) as u, 
                       UPPER(TRIM(COALESCE(NULLIF(TRIM(apellido_nombre), ''), NULLIF(TRIM(CONCAT(nombre, ' ', apellido)), '')))) as nom
                FROM public.datos_usuario 
                WHERE TRIM(UPPER(usuario)) = :u
            """), {"u": usuario_to_add}).fetchone()
            
            nombre_completo = user_row.nom if user_row and user_row.nom else usuario_to_add
            tipo = 'buzon' if ('-' in usuario_to_add or usuario_to_add.startswith('DGROC') or usuario_to_add.startswith('DGIUR') or usuario_to_add.startswith('SEC')) else 'analista'

            # 2. Insertar o reactivar en cfg_analistas_areas (idempotente)
            exists_analista = conn.execute(text("""
                SELECT id FROM public.cfg_analistas_areas 
                WHERE LOWER(TRIM(gerencia)) = :g AND UPPER(TRIM(usuario_sade)) = :u
            """), {"g": g_clean, "u": usuario_to_add}).fetchone()

            if exists_analista:
                conn.execute(text("""
                    UPDATE public.cfg_analistas_areas 
                    SET direccion = :dir, 
                        nombre_completo = COALESCE(:nom, nombre_completo), 
                        tipo = :tipo, 
                        activo = true 
                    WHERE id = :id
                """), {"dir": dir_name, "nom": nombre_completo, "tipo": tipo, "id": exists_analista[0]})
            else:
                conn.execute(text("""
                    INSERT INTO public.cfg_analistas_areas (direccion, gerencia, usuario_sade, nombre_completo, tipo, activo)
                    VALUES (:dir, :ger, :usr, :nom, :tipo, true)
                """), {"dir": dir_name, "ger": g_clean, "usr": usuario_to_add, "nom": nombre_completo, "tipo": tipo})

            # 3. Mantener sincronizada cfg_gestion_metas para tratas existentes de esa gerencia
            rows = conn.execute(text("SELECT id, analistas_oficiales FROM cfg_gestion_metas WHERE TRIM(LOWER(gerencia)) = :g"), {"g": g_clean}).fetchall()
            for r in rows:
                current_analysts = r[1] or []
                current_analysts_upper = [a.strip().upper() for a in current_analysts if a]
                if usuario_to_add not in current_analysts_upper:
                    new_analysts = current_analysts + [usuario_to_add]
                    conn.execute(text("UPDATE cfg_gestion_metas SET analistas_oficiales = :a WHERE id = :id"), {"a": new_analysts, "id": r[0]})
            
            return {"status": "ok", "message": f"Usuario {usuario_to_add} agregado a {g_clean.upper()}."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding analyst: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/admin/analistas/{gerencia}/{usuario}")
async def delete_admin_analista(gerencia: str, usuario: str, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    
    usuario_to_remove = usuario.strip().upper()
    g_clean = gerencia.strip().lower()
    try:
        with engine.begin() as conn:
            # 1. Eliminar de cfg_analistas_areas
            conn.execute(text("""
                DELETE FROM public.cfg_analistas_areas 
                WHERE TRIM(LOWER(gerencia)) = :g AND TRIM(UPPER(usuario_sade)) = :u
            """), {"g": g_clean, "u": usuario_to_remove})

            # 2. Sincronizar cfg_gestion_metas para esa gerencia
            rows = conn.execute(text("SELECT id, analistas_oficiales FROM cfg_gestion_metas WHERE TRIM(LOWER(gerencia)) = :g"), {"g": g_clean}).fetchall()
            for r in rows:
                current_analysts = r[1] or []
                new_analysts = [a for a in current_analysts if a and a.strip().upper() != usuario_to_remove]
                conn.execute(text("UPDATE cfg_gestion_metas SET analistas_oficiales = :a WHERE id = :id"), {"a": new_analysts, "id": r[0]})
            
            return {"status": "ok", "message": f"Usuario {usuario_to_remove} eliminado de {g_clean.upper()}."}
    except Exception as e:
        logger.error(f"Error deleting analyst: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ToggleAnalystStatusRequest(BaseModel):
    activo: bool

@router.patch("/api/admin/analistas/{gerencia}/{usuario}/status")
async def toggle_admin_analista_status(gerencia: str, usuario: str, req: ToggleAnalystStatusRequest, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    
    usuario_target = usuario.strip().upper()
    g_clean = gerencia.strip().lower()
    nuevo_estado = bool(req.activo)
    
    try:
        with engine.begin() as conn:
            # 1. Actualizar en cfg_analistas_areas
            conn.execute(text("""
                UPDATE public.cfg_analistas_areas 
                SET activo = :act
                WHERE TRIM(LOWER(gerencia)) = :g AND TRIM(UPPER(usuario_sade)) = :u
            """), {"g": g_clean, "u": usuario_target, "act": nuevo_estado})

            # 2. Sincronizar cfg_gestion_metas: si se activa y no está en la lista, agregarlo; si se desactiva, removerlo
            rows = conn.execute(text("SELECT id, analistas_oficiales FROM cfg_gestion_metas WHERE TRIM(LOWER(gerencia)) = :g"), {"g": g_clean}).fetchall()
            for r in rows:
                current_analysts = r[1] or []
                current_analysts_upper = [a.strip().upper() for a in current_analysts if a]
                if nuevo_estado:
                    if usuario_target not in current_analysts_upper:
                        new_analysts = current_analysts + [usuario_target]
                        conn.execute(text("UPDATE cfg_gestion_metas SET analistas_oficiales = :a WHERE id = :id"), {"a": new_analysts, "id": r[0]})
                else:
                    if usuario_target in current_analysts_upper:
                        new_analysts = [a for a in current_analysts if a and a.strip().upper() != usuario_target]
                        conn.execute(text("UPDATE cfg_gestion_metas SET analistas_oficiales = :a WHERE id = :id"), {"a": new_analysts, "id": r[0]})
            
            return {
                "status": "ok", 
                "message": f"Estado del analista {usuario_target} actualizado a {'Activo' if nuevo_estado else 'Inactivo'}."
            }
    except Exception as e:
        logger.error(f"Error toggling analyst active status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints de Metas (Admin) ---

@router.get("/api/admin/metas")
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
                    d["direccion"] = "DGROC"
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

@router.post("/api/admin/metas")
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

@router.put("/api/admin/metas/{meta_id}")
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

@router.delete("/api/admin/metas/{meta_id}")
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
