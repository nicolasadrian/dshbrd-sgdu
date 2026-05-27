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
    full_name: str
    sector: str
    needs_password_change: bool

class User(BaseModel):
    username: str
    role: str
    full_name: Optional[str] = None
    sector: Optional[str] = None

class PasswordChange(BaseModel):
    new_password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    sector: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

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

# Utilidades de Seguridad
def verify_password(plain_password, password_hash):
    return bcrypt.checkpw(plain_password.encode('utf-8'), password_hash.encode('utf-8'))

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
            
            return {
                "access_token": access_token, 
                "token_type": "bearer", 
                "username": result[0], 
                "role": result[2],
                "full_name": result[3] or result[0],
                "sector": result[4] or "General",
                "needs_password_change": result[5]
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
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, username, role, full_name, sector, email, needs_password_change, created_at 
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

@app.get("/api/reporte/{gerencia}/consolidado")
async def get_reporte_consolidado_gerencia(gerencia: str, current_user: User = Depends(get_current_user)):
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
                        SELECT DISTINCT trata, descripcion_trata FROM mvw_expedientes_tratas_secgdu 
                        WHERE trata IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = :g)
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
                metas_query = f"SELECT TRIM(trata) as trata, nueva_meta_produccion FROM mv_metas_dinamicas_{gerencia_clean}"
                res_metas = conn.execute(text(metas_query))
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
            
            # Capacidad recomendada total (Egresos Totales Estimados): Intentar leerla directamente de la tabla mv_metas_dinamicas
            db_expected_target = None
            try:
                if trata and trata != 'INTERVENCIONES':
                    meta_res = conn.execute(text(f"SELECT COALESCE(nueva_meta_produccion, 0) FROM mv_metas_dinamicas_{gerencia_clean} WHERE trata = :t LIMIT 1"), {"t": trata}).fetchone()
                    if meta_res:
                        db_expected_target = float(meta_res[0])
                else:
                    sum_res = conn.execute(text(f"SELECT SUM(COALESCE(nueva_meta_produccion, 0)) FROM mv_metas_dinamicas_{gerencia_clean}")).fetchone()
                    if sum_res and sum_res[0] is not None:
                        db_expected_target = float(sum_res[0])
            except Exception as meta_err:
                logger.warning(f"Error obteniendo nueva_meta_produccion de mv_metas_dinamicas_{gerencia_clean}: {meta_err}")

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
                trata_info = conn.execute(text("SELECT descripcion_trata FROM mvw_expedientes_tratas_secgdu WHERE trata = :t LIMIT 1"), {"t": trata}).fetchone()
                nombre_trata = trata_info[0] if trata_info else trata

            # Seleccionamos directamente los valores de la vista histórica para asegurar consistencia total con la tabla
            if gerencia_clean in ['instalaciones', 'morfologia', 'contable', 'etapa_proyecto', 'catastro', 'aph', 'usos', 'regularizacion', 'aviso_obra']:
                # Usamos el ecosistema modular para el gráfico histórico de 12 meses
                # Filtro especial para agrupar intervenciones si es necesario
                trata_filter = f"trata = '{trata}'" if trata != 'INTERVENCIONES' else f"trata NOT IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = '{gerencia_clean}')"
                
                # Definir tabla de egresos de intervenciones (Contable tiene nombre distinto)
                interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"

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
                        WHERE {'trata = \'INTERVENCIONES\'' if trata == 'INTERVENCIONES' else f"trata = '{trata}'"}
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
                        SELECT COUNT(*) as cant FROM mv_{gerencia_clean}_intervenciones_stock WHERE {'trata = \'INTERVENCIONES\'' if trata == 'INTERVENCIONES' else 'FALSE'}
                    ),
                    current_subs AS (
                        -- Foto de HOY para subsanaciones
                        SELECT COUNT(*) as cant FROM mv_{gerencia_clean}_subsanaciones WHERE {trata_filter}
                        UNION ALL
                        SELECT COUNT(*) as cant FROM mv_{gerencia_clean}_intervenciones_subs WHERE {'trata = \'INTERVENCIONES\'' if trata == 'INTERVENCIONES' else 'FALSE'}
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
                trata_info = conn.execute(text("SELECT descripcion_trata FROM mvw_expedientes_tratas_secgdu WHERE trata = :t LIMIT 1"), {"t": trata}).fetchone()
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
                           {view_name}.dias_en_poder_actual as dias, {view_name}.analista, {view_name}.trata, 
                           ext.fecha_creacion as caratula,
                           ext.descripcion_trata, ext.descripcion, ext.estado as estado_expediente,
                           (CURRENT_DATE - {view_name}.fecha_primer_ingreso_gerencia::date) as dias_en_gerencia
                    FROM {view_name}
                    LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = {view_name}.id_expediente
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
                    dias = row.get('dias') or 0
                    f_pase = row.get('fecha_ultimo_pase')
                    
                    # Agrupación por mes (Antigüedad Real)
                    if f_pase and hasattr(f_pase, 'strftime'):
                        m_key = f_pase.strftime("%Y-%m")
                        propio_month_counts[m_key] = propio_month_counts.get(m_key, 0) + 1

                    # Agrupación por Analista y Rango
                    if analista not in analyst_data:
                        analyst_data[analista] = {"analista": analista, "TOTAL": 0}
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
                           dias_ultimo_movimiento as dias, analista_actual as analista, trata,
                           (SELECT fecha_creacion FROM mvw_expedientes_tratas_secgdu WHERE id_expediente = mvw_stock_actual_detalle.id_expediente LIMIT 1) as caratula,
                           (SELECT descripcion_trata FROM mvw_expedientes_tratas_secgdu WHERE id_expediente = mvw_stock_actual_detalle.id_expediente LIMIT 1) as descripcion_trata,
                           (SELECT descripcion FROM mvw_expedientes_tratas_secgdu WHERE id_expediente = mvw_stock_actual_detalle.id_expediente LIMIT 1) as descripcion,
                           (SELECT estado FROM mvw_expedientes_tratas_secgdu WHERE id_expediente = mvw_stock_actual_detalle.id_expediente LIMIT 1) as estado_expediente,
                           dias_stock as dias_en_gerencia
                    FROM mvw_stock_actual_detalle
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
                    dias = row.get('dias') or 0
                    
                    if analista not in analyst_data:
                        analyst_data[analista] = {"analista": analista, "TOTAL": 0}
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
                            FROM mv_{gerencia_clean}_egresos_efectivos t
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
                            FROM mv_{gerencia_clean}_egresos_efectivos t
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
                            FROM mv_{gerencia_clean}_egresos_efectivos t
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
                            FROM mv_{gerencia_clean}_egresos_efectivos t
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
                            FROM mv_{gerencia_clean}_egresos_efectivos t
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
                            FROM mv_{gerencia_clean}_egresos_efectivos t
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
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
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
                        LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
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
                        COALESCE(SUM(
                            CASE 
                                WHEN fecha_cierre IS NOT NULL THEN (fecha_cierre::date - fecha_alta::date)
                                ELSE (CURRENT_DATE - fecha_alta::date)
                            END
                        ), 0) AS dias_subs
                    FROM mvw_ee_actividades_secgdu
                    WHERE nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
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

if __name__ == "__main__":
    import uvicorn
    import sys
    import os
    
    # Agregar el directorio raíz al path para que uvicorn encuentre el módulo 'backend'
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
        
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
