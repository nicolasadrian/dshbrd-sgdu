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
    # Fallback para local si no hay variable de entorno
    DATABASE_URL = "postgresql://postgres:lenovo@localhost:5432/sade_db"

engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

@app.get("/health")
async def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            # Obtener el host de la DB para debug (mascarado)
            db_host = DATABASE_URL.split('@')[-1].split(':')[0]
            db_name = DATABASE_URL.split('/')[-1]
            return {
                "status": "ok", 
                "database": "connected", 
                "host": f"***{db_host[-4:]}", 
                "db": db_name
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/reporte/{gerencia}/consolidado")
async def get_reporte_consolidado_gerencia(gerencia: str):
    gerencia_clean = gerencia.lower()
    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
    
    trata_codes = list(TRAMITES_CONFIG[gerencia_clean].keys())
    
    # Obtener los últimos 5 meses para el filtro
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
                SELECT h.* 
                FROM mvw_reporte_historico_dgroc h
                JOIN config_order o ON h."COD TRATA" = o.trata_code
                WHERE h."GERENCIA" = '{gerencia_clean}'
                  AND (h.anio, h.mes) IN ({months_filter})
                ORDER BY o.ord, h.anio DESC, h.mes DESC
            """
            result = conn.execute(text(sql))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error en consolidado: {e}")
        raise HTTPException(status_code=500, detail="Error interno al obtener el consolidado.")

@app.get("/api/reporte/{gerencia}/tramite/{trata}/stock_detail")
async def get_reporte_tramite_stock_detail(gerencia: str, trata: str):
    gerencia_clean = gerencia.lower()
    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
        
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
                      AND trata != 'MDUG0102B'
                      AND analista_actual IN ({sector_whitelist_sql})
                """
            else:
                sql = f"""
                    SELECT id_expediente, expediente, fecha_ingreso as fecha_ing, dias_stock as dias, analista_actual as analista, 0 as is_subs
                    FROM mvw_stock_actual_detalle
                    WHERE trata = '{trata}'
                      AND analista_actual IN ({sector_whitelist_sql})
                """

            result = conn.execute(text(sql))
            rows = result.fetchall()
            
            # Formatear la respuesta como espera el frontend
            propio_month_counts = {}
            analyst_data = {}
            ranges = [(0, 15, "Menos de 15 dias"), (15, 30, "15 a 30 dias"), (30, 45, "30 a 45 dias"), (45, 60, "45 a 60 dias"), (60, 75, "60 a 75 dias"), (75, 90, "75 a 90 dias"), (90, 999999, "Mas de 90 dias")]
            
            for row in rows:
                # 1. Distribución mensual
                m_key = row.fecha_ing.strftime("%Y-%m")
                propio_month_counts[m_key] = propio_month_counts.get(m_key, 0) + 1
                
                # 2. Distribución por analista
                analista = row.analista or "SIN ASIGNAR"
                if analista not in analyst_data:
                    analyst_data[analista] = {r[2]: 0 for r in ranges}
                    analyst_data[analista]["TOTAL"] = 0
                
                for start, end, label in ranges:
                    if start <= row.dias < end:
                        analyst_data[analista][label] += 1
                        break
                analyst_data[analista]["TOTAL"] += 1
            
            month_dist = [{"periodo": m, "cantidad": propio_month_counts.get(m, 0)} for m in sorted(propio_month_counts.keys())]
            analyst_dist = [{"analista": name, **counts} for name, counts in analyst_data.items()]
            
            return {
                "month_dist": month_dist,
                "analyst_dist": analyst_dist,
                "raw_data": [dict(r._mapping) for r in rows[:1000]] # Limitar raw data para performance
            }
            
    except Exception as e:
        logger.error(f"Error en stock_detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))
