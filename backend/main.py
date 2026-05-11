import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime, timedelta
import logging
try:
    from .config import TRAMITES_CONFIG, WHITELISTS, BUZZERS_MAP
except ImportError:
    from config import TRAMITES_CONFIG, WHITELISTS, BUZZERS_MAP

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

# Conexión a la base de datos
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:lenovo@localhost:5432/sade_db"

engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

@app.get("/health")
async def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_host = DATABASE_URL.split('@')[-1].split(':')[0]
            db_name = DATABASE_URL.split('/')[-1]
            return {"status": "ok", "database": "connected", "host": f"***{db_host[-4:]}", "db": db_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/reporte/{gerencia}/consolidado")
async def get_reporte_consolidado_gerencia(gerencia: str):
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
async def get_reporte_tramite_historico(gerencia: str, trata: str):
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
                    SELECT anio, mes, "ING", "EGR_EF", "EGR_NE", "STOCK_PROPIO", "STOCK_SUBS"
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
async def get_reporte_tramite_stock_detail(gerencia: str, trata: str):
    gerencia_clean = gerencia.lower()
    if gerencia_clean not in TRAMITES_CONFIG: raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
    buzzers = BUZZERS_MAP.get(gerencia_clean, [])
    whitelist_users = WHITELISTS.get(gerencia_clean, [])
    sector_whitelist = whitelist_users + buzzers
    sector_whitelist_sql = ", ".join([f"'{u}'" for u in sector_whitelist])

    try:
        with engine.connect() as conn:
            if trata == 'INTERVENCIONES':
                sql = f"""
                    SELECT id_expediente, expediente, fecha_ing, dias_stock as dias, analista_actual as analista, is_subs
                    FROM mvw_stock_actual_detalle
                    WHERE trata NOT IN ({", ".join([f"'{t}'" for t in TRAMITES_CONFIG[gerencia_clean].keys() if t != 'INTERVENCIONES'])})
                      AND trata != 'MDUG0102B' AND gerencia = '{gerencia_clean}'
                """
            else:
                sql = f"""
                    SELECT id_expediente, expediente, fecha_ing, dias_stock as dias, analista_actual as analista, is_subs
                    FROM mvw_stock_actual_detalle
                    WHERE trata = '{trata}' AND gerencia = '{gerencia_clean}'
                """
            result = conn.execute(text(sql))
            rows = result.fetchall()
            
            # Formatear la respuesta enfocada en STOCK ACTUAL PROPIO
            propio_month_counts = {}
            analyst_data = {}
            ranges = [(0, 15, "Menos de 15 dias"), (15, 30, "15 a 30 dias"), (30, 45, "30 a 45 dias"), (45, 60, "45 a 60 dias"), (60, 75, "60 a 75 dias"), (75, 90, "75 a 90 dias"), (90, 999999, "Mas de 90 dias")]
            
            # Solo procesamos para el detalle lo que es STOCK PROPIO (is_subs = 0)
            propio_rows = [r for r in rows if r.is_subs == 0]
            
            for row in propio_rows:
                m_key = row.fecha_ing.strftime("%Y-%m")
                propio_month_counts[m_key] = propio_month_counts.get(m_key, 0) + 1
                analista = row.analista or "SIN ASIGNAR"
                if analista not in analyst_data:
                    analyst_data[analista] = {r[2]: 0 for r in ranges}
                    analyst_data[analista]["TOTAL"] = 0
                for start, end, label in ranges:
                    if start <= row.dias < end:
                        analyst_data[analista][label] += 1
                        break
                analyst_data[analista]["TOTAL"] += 1
            
            return {
                "month_distribution": [{"periodo": m, "cantidad": propio_month_counts.get(m, 0)} for m in sorted(propio_month_counts.keys())],
                "analyst_distribution": [{"analista": name, **counts} for name, counts in analyst_data.items()],
                "expedientes": [
                    {**dict(r._mapping), "fecha_ing": r.fecha_ing.strftime("%Y-%m-%d %H:%M:%S") if r.fecha_ing else None} 
                    for r in propio_rows[:1000]
                ]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/{gerencia}/intervenciones/detalle")
async def get_intervenciones_detalle(gerencia: str):
    gerencia_clean = gerencia.lower()
    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
    
    # Lista de trámites propios para excluir del desglose de intervenciones
    propios = list(TRAMITES_CONFIG[gerencia_clean].keys())
    propios_sql = ", ".join([f"'{p}'" for p in propios])

    try:
        with engine.connect() as conn:
            # Consultamos directamente el stock actual de la gerencia, excluyendo los propios
            sql = f"""
                SELECT trata, descripcion as detalle, dias_stock
                FROM mvw_stock_actual_detalle
                WHERE is_subs = 0 
                  AND gerencia = '{gerencia_clean}'
                  AND trata NOT IN ({propios_sql})
                  AND trata != 'MDUG0102B'
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
