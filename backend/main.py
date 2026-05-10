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
        now = datetime.now()
        months_to_show = []
        for i in range(12):
            d = (now.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            months_to_show.append(f"({d.year}, {d.month})")
        months_filter = ", ".join(months_to_show)

        with engine.connect() as conn:
            # 1. Obtener el STOCK FÍSICO REAL ACTUAL (El Ancla)
            sql_fisico = f"""
                SELECT COUNT(*) as total 
                FROM mvw_stock_actual_detalle 
                WHERE is_subs = 0 AND gerencia = '{gerencia_clean}'
            """
            if trata != 'INTERVENCIONES':
                sql_fisico += f" AND trata = '{trata}'"
            else:
                propios = list(TRAMITES_CONFIG.get(gerencia_clean, {}).keys())
                propios_sql = ", ".join([f"'{p}'" for p in propios])
                sql_fisico += f" AND trata NOT IN ({propios_sql}) AND trata != 'MDUG0102B'"
                
            res_fisico = conn.execute(text(sql_fisico)).fetchone()
            stock_actual_fisico = res_fisico[0] if res_fisico else 0

            # 2. Obtener los Ingresos y Egresos históricos
            sql_hist = f"""
                SELECT anio, mes, 
                       SUM("INGRESOS") as ING, 
                       SUM("EGRESOS_EFECTIVOS") as EGR_EF, 
                       SUM("EGRESOS_NO_EFECTIVOS") as EGR_NE
                FROM mvw_reporte_historico_dgroc
                WHERE "GERENCIA" = '{gerencia_clean}' 
                  AND "COD TRATA" = '{trata}'
                  AND (anio, mes) IN ({months_filter})
                GROUP BY anio, mes
                ORDER BY anio DESC, mes DESC
            """
            # Si es intervenciones, sumamos todo lo que no es propio
            if trata == 'INTERVENCIONES':
                propios = list(TRAMITES_CONFIG.get(gerencia_clean, {}).keys())
                propios_sql = ", ".join([f"'{p}'" for p in propios])
                sql_hist = f"""
                    SELECT anio, mes, 
                           SUM("INGRESOS") as ING, 
                           SUM("EGRESOS_EFECTIVOS") as EGR_EF, 
                           SUM("EGRESOS_NO_EFECTIVOS") as EGR_NE
                    FROM mvw_reporte_historico_dgroc
                    WHERE "GERENCIA" = '{gerencia_clean}' 
                      AND "COD TRATA" NOT IN ({propios_sql})
                      AND "COD TRATA" != 'MDUG0102B'
                      AND (anio, mes) IN ({months_filter})
                    GROUP BY anio, mes
                    ORDER BY anio DESC, mes DESC
                """

            df_hist = pd.read_sql(sql_hist, conn)
            
        if df_hist.empty: return []

        # 3. Reconstruir la serie asegurando que el mes actual COINCIDA con el físico
        result = []
        current_stock = stock_actual_fisico
        
        for i, row in df_hist.iterrows():
            mes_row = {
                "anio": int(row['anio']),
                "mes": int(row['mes']),
                "ING": int(row['ING']),
                "EGR_EF": int(row['EGR_EF']),
                "EGR_NE": int(row['EGR_NE']),
                "STOCK_PROPIO": current_stock,
                "STOCK_SUBS": 0
            }
            result.append(mes_row)
            # Para el mes anterior, el stock era: Stock_Hoy - Ingresos + Egresos
            net_flow = int(row['ING']) - (int(row['EGR_EF']) + int(row['EGR_NE']))
            current_stock = max(0, current_stock - net_flow)
            
        return result
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
                "expedientes": [dict(r._mapping) for r in propio_rows[:1000]]
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
