import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime, timedelta
import logging
from .config import TRAMITES_CONFIG, WHITELISTS, BUZZERS_MAP

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
    current_date = datetime.now()
    months = []
    for i in range(5):
        d = current_date - timedelta(days=i*30)
        months.append((d.year, d.month))
    months_filter = ", ".join([f"({anio}, {mes})" for anio, mes in months])
    
    try:
        with engine.connect() as conn:
            sql = f"""
                WITH config_order AS (
                    SELECT * FROM (VALUES {", ".join([f"('{c}', {i})" for i, c in enumerate(trata_codes)])}) as t(trata_code, ord)
                )
                SELECT h.* FROM mvw_reporte_historico_dgroc h
                JOIN config_order o ON h."COD TRATA" = o.trata_code
                WHERE h."GERENCIA" = '{gerencia_clean}' AND (h.anio, h.mes) IN ({months_filter})
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
        with engine.connect() as conn:
            sql = f"""
                SELECT * FROM mvw_reporte_historico_dgroc 
                WHERE "GERENCIA" = '{gerencia_clean}' AND "COD TRATA" = '{trata}'
                ORDER BY anio DESC, mes DESC LIMIT 12
            """
            result = conn.execute(text(sql))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df.to_dict(orient='records')
    except Exception as e:
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
                    SELECT id_expediente, expediente, fecha_ingreso as fecha_ing, dias_stock as dias, analista_actual as analista, 0 as is_subs
                    FROM mvw_stock_actual_detalle
                    WHERE trata NOT IN ({", ".join([f"'{t}'" for t in TRAMITES_CONFIG[gerencia_clean].keys() if t != 'INTERVENCIONES'])})
                      AND trata != 'MDUG0102B' AND analista_actual IN ({sector_whitelist_sql})
                """
            else:
                sql = f"""
                    SELECT id_expediente, expediente, fecha_ingreso as fecha_ing, dias_stock as dias, analista_actual as analista, 0 as is_subs
                    FROM mvw_stock_actual_detalle
                    WHERE trata = '{trata}' AND analista_actual IN ({sector_whitelist_sql})
                """
            result = conn.execute(text(sql))
            rows = result.fetchall()
            propio_month_counts = {}
            analyst_data = {}
            ranges = [(0, 15, "Menos de 15 dias"), (15, 30, "15 a 30 dias"), (30, 45, "30 a 45 dias"), (45, 60, "45 a 60 dias"), (60, 75, "60 a 75 dias"), (75, 90, "75 a 90 dias"), (90, 999999, "Mas de 90 dias")]
            for row in rows:
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
                "expedientes": [dict(r._mapping) for r in rows[:1000]]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/{gerencia}/intervenciones/detalle")
async def get_intervenciones_detalle(gerencia: str):
    gerencia_clean = gerencia.lower()
    try:
        with engine.connect() as conn:
            # Esta consulta agrupa los trámites externos que están en stock para la gerencia
            sql = f"""
                SELECT trata, "DETALLE TRATA" as detalle, anio, mes, "ING" as cantidad
                FROM mvw_reporte_historico_dgroc
                WHERE "GERENCIA" = '{gerencia_clean}' AND "COD TRATA" = 'INTERVENCIONES'
                ORDER BY anio DESC, mes DESC
            """
            # Por ahora devolvemos el consolidado de intervenciones
            result = conn.execute(text(sql))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            # Transformar a formato meses
            output = []
            for name, group in df.groupby(['trata', 'detalle']):
                meses = {f"{r.anio}-{r.mes:02d}": int(r.cantidad) for r in group.itertuples()}
                output.append({"trata": name[0], "detalle": name[1], "meses": meses})
            return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
