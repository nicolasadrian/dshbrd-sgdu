import os
import json
import logging
import bcrypt
from typing import List, Dict, Any, Optional
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

@router.get("/api/admin/buzones-analisis/catalogo")
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

@router.get("/api/admin/buzones-analisis/accesos")
async def list_buzones_accesos(current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, tipo_sujeto, nombre_sujeto, buzones FROM public.cfg_buzones_analisis_acceso ORDER BY tipo_sujeto, nombre_sujeto"))
            return [dict(r._mapping) for r in result.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/admin/buzones-analisis/accesos")
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

@router.delete("/api/admin/buzones-analisis/accesos/{nombre_sujeto}")
async def delete_buzon_acceso(nombre_sujeto: str, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM public.cfg_buzones_analisis_acceso WHERE nombre_sujeto = :name"), {"name": nombre_sujeto})
            return {"status": "ok", "message": "Acceso personalizado eliminado"}
    except Exception as e:
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

# --- Endpoints de Analistas (Admin) ---

@router.get("/api/admin/analistas")
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

@router.post("/api/admin/analistas/{gerencia}")
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

@router.delete("/api/admin/analistas/{gerencia}/{usuario}")
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
