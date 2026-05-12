import os
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime, timedelta
import logging
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

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

class User(BaseModel):
    username: str
    role: str

# Función para obtener el motor de DB de forma segura
def get_engine():
    db_url = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_PUBLIC") or os.getenv("DATABASE_URL_LOCAL")
    if not db_url:
        db_url = "postgresql://postgres:lenovo@localhost:5432/sade_db"
    
    # Corregir prefijo para SQLAlchemy si viene de Heroku/Vercel legacy
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    return create_engine(db_url, pool_size=5, max_overflow=10)

engine = get_engine()

# Utilidades de Seguridad
def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el acceso",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        return User(username=username, role=role)
    except JWTError:
        raise credentials_exception

# --- Endpoints de Autenticación ---

@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        with engine.connect() as conn:
            # Intentamos con el nombre nuevo, si falla probamos con el viejo
            try:
                query = text("SELECT username, hashed_password as pwd, role FROM auth_users WHERE username = :u")
                result = conn.execute(query, {"u": form_data.username}).fetchone()
            except Exception:
                query = text("SELECT username, password_hash as pwd, role FROM auth_users WHERE username = :u")
                result = conn.execute(query, {"u": form_data.username}).fetchone()
            
            if not result or not verify_password(form_data.password, result[1]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario o contraseña incorrectos",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            access_token = create_access_token(data={"sub": result[0], "role": result[2]})
            return {"access_token": access_token, "token_type": "bearer", "username": result[0], "role": result[2]}
    except Exception as e:
        logger.error(f"Error en login: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

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
            return {
                "status": "online",
                "database": "connected",
                "detected_var": db_var,
                "db_name": DATABASE_URL.split('/')[-1].split('?')[0]
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
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, username, role, created_at FROM auth_users ORDER BY username"))
            return [dict(r._mapping) for r in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

@app.post("/api/admin/users")
async def create_user(user_data: UserCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        hashed = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        with engine.connect() as conn:
            # Intentar insertar con el nombre nuevo, si falla probamos con el viejo
            try:
                conn.execute(
                    text("INSERT INTO auth_users (username, hashed_password, role) VALUES (:u, :p, :r)"),
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
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    if username == current_user.username:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM auth_users WHERE username = :u"), {"u": username})
            conn.commit()
            return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints de Reportes (Protegidos) ---

@app.get("/api/reporte/{gerencia}/consolidado")
async def get_reporte_consolidado_gerencia(gerencia: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
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
            sql = f"""
                WITH config_order AS (
                    SELECT * FROM (VALUES {", ".join([f"('{c}', {i})" for i, c in enumerate(trata_codes)])}) as t(trata_code, ord)
                )
                SELECT h.* FROM mvw_reporte_historico_{gerencia_clean} h
                JOIN config_order o ON h."COD TRATA" = o.trata_code
                WHERE (h.anio, h.mes) IN ({months_filter})
                ORDER BY o.ord, h.anio DESC, h.mes DESC
            """
            result = conn.execute(text(sql))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error en consolidado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/{gerencia}/tramite/{trata}")
async def get_reporte_tramite_historico(gerencia: str, trata: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
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
            # Seleccionamos directamente los valores de la vista histórica para asegurar consistencia total con la tabla
            if trata == 'INTERVENCIONES':
                propios = list(TRAMITES_CONFIG.get(gerencia_clean, {}).keys())
                propios_sql = ", ".join([f"'{p}'" for p in propios])
                sql = f"""
                    SELECT anio, mes, 
                           'INTERVENCIONES' as "DETALLE TRATA",
                           SUM("ING") as "ING", 
                           SUM("EGR_EF") as "EGR_EF", 
                           SUM("EGR_NE") as "EGR_NE",
                           SUM("STOCK_PROPIO") as "STOCK_PROPIO",
                           SUM("STOCK_SUBS") as "STOCK_SUBS"
                    FROM mvw_reporte_historico_{gerencia_clean}
                    WHERE "COD TRATA" NOT IN ({propios_sql})
                      AND "COD TRATA" != 'MDUG0102B'
                      AND (anio, mes) IN ({months_filter})
                    GROUP BY anio, mes
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
    if gerencia_clean not in TRAMITES_CONFIG: raise HTTPException(status_code=404, detail="Gerencia no encontrada.")

    try:
        with engine.connect() as conn:
            buzzers = BUZZERS_MAP.get(gerencia_clean, [])
            whitelist_users = WHITELISTS.get(gerencia_clean, [])
            sector_whitelist = whitelist_users + buzzers
            sector_whitelist_sql = ", ".join([f"'{u}'" for u in sector_whitelist])

            # Usamos la vista materializada optimizada para el detalle
            sql = f"""
                SELECT id_expediente, expediente, fecha_ing, fecha_ultimo_pase, 
                       dias_ultimo_movimiento as dias, analista_actual as analista
                FROM mvw_stock_actual_detalle
                WHERE trata_reporte = '{trata}' 
                  AND gerencia = '{gerencia_clean}'
                  AND is_subs = 0
                  AND analista_actual IN ({sector_whitelist_sql})
            """
            result = conn.execute(text(sql))
            rows = result.fetchall()

            
            # Formatear la respuesta enfocada en STOCK ACTUAL PROPIO REAL
            propio_month_counts = {}
            analyst_data = {}
            ranges = [(0, 15, "Menos de 15 dias"), (15, 30, "15 a 30 dias"), (30, 45, "30 a 45 dias"), (45, 60, "45 a 60 dias"), (60, 75, "60 a 75 dias"), (75, 90, "75 a 90 dias"), (90, 999999, "Mas de 90 dias")]
            
            for row in rows:
                # La antigüedad del stock se mide por el ÚLTIMO MOVIMIENTO (fecha_ultimo_pase)
                if row.fecha_ultimo_pase:
                    m_key = row.fecha_ultimo_pase.strftime("%Y-%m")
                else:
                    m_key = row.fecha_ing.strftime("%Y-%m") if row.fecha_ing else "sin-fecha"
                propio_month_counts[m_key] = propio_month_counts.get(m_key, 0) + 1
                
                analista = row.analista or "SIN ASIGNAR"
                if analista not in analyst_data:
                    analyst_data[analista] = {r[2]: 0 for r in ranges}
                    analyst_data[analista]["TOTAL"] = 0
                
                # Clasificar por días desde el último movimiento
                dias = row.dias if row.dias is not None else 0
                for start, end, label in ranges:
                    if start <= dias < end:
                        analyst_data[analista][label] += 1
                        break
                analyst_data[analista]["TOTAL"] += 1
            
            return {
                "stock_propio_count": len(rows),
                "month_distribution": [{"periodo": m, "cantidad": propio_month_counts.get(m, 0)} for m in sorted(propio_month_counts.keys())],
                "analyst_distribution": [{"analista": name, **counts} for name, counts in analyst_data.items()],
                "expedientes": [
                    {
                        "id_expediente": r.id_expediente,
                        "expediente": r.expediente,
                        "fecha_ing": r.fecha_ing.strftime("%Y-%m-%d %H:%M:%S") if r.fecha_ing else None,
                        "fecha_ultimo_pase": r.fecha_ultimo_pase.strftime("%Y-%m-%d %H:%M:%S") if r.fecha_ultimo_pase else None,
                        "dias": r.dias if r.dias is not None else 0,
                        "analista": r.analista
                    } 
                    for r in rows[:1000]
                ]
            }
    except Exception as e:
        logger.error(f"Error en stock_detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/{gerencia}/intervenciones/detalle")
async def get_intervenciones_detalle(gerencia: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
    
    # Lista de trámites propios para excluir del desglose de intervenciones
    propios = list(TRAMITES_CONFIG[gerencia_clean].keys())
    propios_sql = ", ".join([f"'{p}'" for p in propios])

    try:
        with engine.connect() as conn:
            # Consultamos directamente el stock actual usando la columna trata_reporte
            sql = f"""
                SELECT trata, descripcion as detalle, dias_stock
                FROM mvw_stock_actual_detalle
                WHERE is_subs = 0 
                  AND gerencia = '{gerencia_clean}'
                  AND trata_reporte = 'INTERVENCIONES'
            """
            result = conn.execute(text(sql))
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

if __name__ == "__main__":
    import uvicorn
    import sys
    import os
    
    # Agregar el directorio raíz al path para que uvicorn encuentre el módulo 'backend'
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
        
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
