import os
import time
import logging
import bcrypt
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Query, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text
from typing import Optional, Dict, Any
try:
    from database import engine
    from schemas import User
except ImportError:
    from backend.database import engine
    from backend.schemas import User

SECRET_KEY = os.getenv("SECRET_KEY", "7b6f8e9a2c4d5f1a3b5e7d9c0a2b4d6f8e0a2c4d")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

logger = logging.getLogger(__name__)

_auth_cache: Dict[str, Any] = {}
_AUTH_CACHE_TTL = 60  # segundos

def verify_password(plain_password, password_hash):
    return bcrypt.checkpw(plain_password.encode('utf-8'), password_hash.encode('utf-8'))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

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
        
    if resolved is None:
        # Fallback to role permissions
        role_perm = conn.execute(text("SELECT permissions FROM auth_roles WHERE role_name = :r"), {"r": role_name}).scalar()
        if role_perm is not None:
            resolved = dict(role_perm)
            
    if resolved is None:
        resolved = {}
        
    # Admins get ALL permissions automatically
    if r_lower in ["admin", "administrador"]:
        for k in ["dgroc", "dgiur", "family", "seguimiento", "cierre", "sla", "subsanaciones", "buscador", "favoritos", "favoritos-seguimiento", "analytics_estadistica", "analytics_datasets", "analytics_m2_permisados", "analytics_avisos_obra", "analytics_pdl_blanqueo", "asignados-mi", "productividad_analistas", "reportes_rrhh", "carga_reportes_rrhh", "universo_tratas"]:
            resolved[k] = True

            
    return resolved

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el acceso",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Caché de auth por token
    cached = _auth_cache.get(token)
    if cached and (time.time() - cached["ts"]) < _AUTH_CACHE_TTL:
        return cached["user"]

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
            user = User(
                username=user_row[0],
                role=user_row[1],
                full_name=user_row[2],
                sector=user_row[3],
                permissions=resolved_perms
            )
            # Guardar en caché
            _auth_cache[token] = {"ts": time.time(), "user": user}
            if len(_auth_cache) > 100:
                cutoff = time.time() - _AUTH_CACHE_TTL
                expired = [k for k, v in _auth_cache.items() if v["ts"] < cutoff]
                for k in expired:
                    _auth_cache.pop(k, None)
            return user
    except JWTError as e:
        logger.warning(f"[auth] JWTError validating token: {type(e).__name__}: {e}")
        raise credentials_exception

async def get_current_user_from_param_or_header(token: Optional[str] = Query(None), authorization: Optional[str] = Header(None, alias="Authorization")):
    actual_token = None
    if authorization and authorization.startswith("Bearer "):
        actual_token = authorization.split(" ")[1]
    elif token:
        if token.startswith("Bearer "):
            actual_token = token.split(" ")[1]
        else:
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
