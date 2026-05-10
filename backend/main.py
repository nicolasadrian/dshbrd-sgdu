import logging
import time
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
import os
import sys
from datetime import datetime

# --- CONFIGURACIÓN DE LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("backend-api")

# Añadir el directorio padre al sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from .config import TRAMITES_CONFIG
except ImportError:
    try:
        from config import TRAMITES_CONFIG
    except ImportError:
        sys.path.append(current_dir)
        from config import TRAMITES_CONFIG

app = FastAPI(
    title="API Tablero Gestión SGDU",
    description="Backend optimizado para alta concurrencia y producción"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- OPTIMIZACIÓN DE CONEXIÓN A DB ---
# IMPORTANTE: Configurar la variable DATABASE_URL en el panel de Vercel/GitHub
DB_URL = os.getenv('DATABASE_URL')

if not DB_URL:
    logger.warning("DATABASE_URL no configurada. Usando fallback de desarrollo (localhost).")
    DB_URL = 'postgresql://postgres:lenovo@localhost:5432/sade_db'

# Pool de conexiones para manejar concurrencia (hasta 20 usuarios simultáneos recomendado)
engine = create_engine(
    DB_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    poolclass=QueuePool
)

# --- SISTEMA DE CACHÉ SIMPLE ---
# Almacena resultados de consultas pesadas que no cambian en tiempo real
api_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 300 # 5 minutos de caché para reportes consolidados

def get_cached_data(key: str):
    if key in api_cache:
        entry = api_cache[key]
        if time.time() - entry['timestamp'] < CACHE_TTL:
            return entry['data']
    return None

def set_cached_data(key: str, data: Any):
    api_cache[key] = {
        'data': data,
        'timestamp': time.time()
    }

# --- NOMINAS OFICIALES DE ANALISTAS ---
# Mantenemos las listas en memoria para acceso ultrarrápido
WHITELISTS = {
    'catastro': ["ACOSTAPA", "AFAHLER", "AGUSMAZZONI", "ALEALFONSIN", "ALEGREM", "ARGENTOES", "BARTROLIG", "CABRERAM", "CANALEAL", "CARBONELLIM", "CHIANETTAR", "CIOPKOG", "CISTERNACA", "COHENCAD", "CONTIL", "CONVERTID", "DELGADODE", "DIBIASEO", "DIEZGASTON", "DIHARCEP", "DURSIM", "ECIJAN", "FMARCHISELLA", "FOLLONIERLE", "FREIXASC", "GARCIASIL", "GILESJP", "GONZALEZAMA", "GONZALEZHORAC", "GUZMANO", "IGARZABALP", "JTIRADO", "LAGUNAMA", "LBELLY", "LOISIG", "LUCCIC", "M.NAPOLI", "MALATTOR", "MANNOP", "MARCHETTIJ", "MHOSBALIKCIYAN", "MOSCOVICHA", "NCITRANGOLO", "NOGUERAH", "NPONZO", "NQUINTERNO", "PONZOS", "ROLDANG", "SALGUEROM", "SORIAANDREA", "TARRUA", "TAVELLAE", "VEGAJ", "VILLAGI", "WVIRGILIO"],
    'regularizacion': ["AGUEROJO", "AKRACOFF", "ALVAREZ.M", "ARAOZLUIS", "ATENCIOAL", "DALBORAF", "ENCISOA", "EPARLATO", "ERDOCIAINA", "JBARRACO", "JLGARMENDIA", "JTERRILE", "MYUSHU", "S.SANCHEZPAZ", "SCAVALLARO"],
    'instalaciones': ["AQUINOLUCAS", "ARENAJ", "ARGUELLOJ", "BATALLANJ", "BENITOG", "BRIANMARTINEZ", "CORNAZM", "FICARRAR", "GAGLIARDIA", "LOPARDOC", "QUEIJASGUILLINP", "ROBLEDOJO", "ROLDANMI", "RUDAC", "SARIDISD", "TOLESANOA", "AURENA", "BATALLANGE", "BRITANP", "GUARDADOB", "JDECIMA", "PEREZGA", "RODRIGUEZESTEBAN", "RODRIGUEZNE", "SILESC", "VILLAGAB", "ABCRAGNO", "AGARCIAFIGUEROA", "CABRERAARI", "CAFELICE", "CAPOZZOG", "CSALGUERO", "DARANGURI", "DMOFFA", "FUHRY", "GONMAR", "J.OLIVERA", "LOPEZFE", "MARIANELAROCARO", "MBALDOME", "MLMAMONE", "MTRENQUE", "NIEVAL", "PCHERBENCO", "RADAA", "RIOSFE", "ROMANOFLA", "SANTACRUZ", "CANTARELLTORRES", "CIRIAE", "LOIACONOANA", "MCDIAMANTI", "POUSAF", "ARGUELLOSOL", "COSSM", "EIERACI", "HAMALAG", "RUIZMA", "BRITANG", "ENCISOROMERO", "PITTERIE", "WIERZBICKIIGOR"],
    'contable': ["AMONTEVERDE", "AMORINC", "CARLOSDUARTE", "CAROJAS", "COLOTTAP", "CPENDON", "DAS", "DASTUGUEO", "DEGODOY", "DIAZBAR", "DKRENZ", "EDEFEO", "FABIANSANTILLAN", "FMHERRERA", "FSPANTI", "GARCIASEBA", "HRICCIARDI", "JOSEMARIAORTIZ", "JPOMAR", "JULILOPARDO", "LAMORGIAKA", "LBARRIENTOS", "LICETB", "M.ROSSO", "MARQUEZMAR", "MARTINEZCLA", "MLAURITO", "MMALACALZA", "NMONTEVERDE", "NMORENO", "POVIEDO", "PRESAF", "PVACEVEDO", "RIVERAMA", "ROBLEDOE", "RODRIGUEZLEA", "RODRIGUEZMAGD", "ROSARIODECRIS", "SCHULERG", "SENING", "SMERMOZ", "SORIAD", "SPOSAROAL", "TATOJ", "TIRENDIC", "TOMIPITES", "VICSOLMORE", "VILLACRI"],
    'etapa_proyecto': ["A.PEREZ", "AGUSDEMARCO", "ANTOVERA", "BELOCURESJ", "COIROL", "DBECERRACURITIMA", "DIMASOM", "DNKAINSKY", "FORGIONEA", "GAILLURJP", "GARRIONDO", "JOSEFINA.P", "M.SANCHEZ", "MARCE.TOSONI", "MARCETOSONI", "MARCETOSONI1", "MBRISA", "MCANOGARAY", "MCARLUCCIO", "MGALLARDOC", "MSTIBERTI", "NLOPEZQUIROGA", "ROCABERTJ", "SPUET", "TALAMOM", "VERA"]
}

BUZZERS_MAP = {
    'catastro': ['DGROC-CIC', 'DGROC-COPIAPLANO', 'DGROC-DCATDES', 'DGROC-DCATPOL', 'DGROC-DCATTIT'],
    'instalaciones': ['DGROC-ELECTRICAS', 'DGROC-ELEVADORES', 'DGROC-INCENDIO', 'DGROC-SANITARIAS', 'DGROC-TERMICAS'],
    'regularizacion': ['DGROC-OBRASDEMO'],
    'contable': ['DGROC-CONTABLE', 'DGROC-OBRASADMIN'],
    'etapa_proyecto': ['DGROC-OBRASTECNICA'],
    'aviso_obra': ['DGROC-AUTOMAT']
}

@app.get("/api/reporte/{gerencia}/consolidado")
async def get_reporte_consolidado_gerencia(gerencia: str):
    gerencia_clean = gerencia.lower()
    cache_key = f"consolidado_{gerencia_clean}"
    
    cached = get_cached_data(cache_key)
    if cached:
        logger.info(f"Cache hit: {cache_key}")
        return cached

    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail=f"Gerencia '{gerencia}' no configurada.")
    
    trata_codes = list(TRAMITES_CONFIG[gerencia_clean].keys())
    now = datetime.now()
    target_months = []
    curr_month = now.month
    curr_year = now.year
    for i in range(4):
        m = curr_month - i
        y = curr_year
        while m <= 0:
            m += 12
            y -= 1
        target_months.append((y, m))
    
    months_filter = ", ".join([f"({y}, {m})" for y, m in target_months])
    
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
            data = [dict(row._mapping) for row in result.all()]
            set_cached_data(cache_key, data)
            return data
    except Exception as e:
        logger.error(f"Error en consolidado: {e}")
        raise HTTPException(status_code=500, detail="Error interno al obtener el consolidado.")

@app.get("/api/reporte/{gerencia}/tramite/{trata}/stock_detail")
async def get_reporte_tramite_stock_detail(gerencia: str, trata: str):
    gerencia_clean = gerencia.lower()
    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
        
    config = TRAMITES_CONFIG[gerencia_clean].get(trata)
    if not config:
        raise HTTPException(status_code=404, detail="Trámite no encontrado.")
        
    acronimos = config["acronimos"]
    trata_db = trata.split('_')[0] if '_' in trata else trata
    is_auto = '_AUTO' in trata
    is_dgiur = '_DGIUR' in trata
    
    buzzers = BUZZERS_MAP.get(gerencia_clean, [])
    buzzers_sql = ", ".join([f"'{s}'" for s in buzzers]) or "'DGROC-SIN-BUZZER'"
    whitelist_users = WHITELISTS.get(gerencia_clean, [])
    sector_whitelist = whitelist_users + buzzers
    sector_whitelist_sql = ", ".join([f"'{u}'" for u in sector_whitelist])

    try:
        with engine.connect() as conn:
            if trata == 'INTERVENCIONES':
                sql = f"""
                    WITH target_expedientes AS (
                        SELECT id_expediente, trata, expediente
                        FROM mvw_expedientes_tratas_secgdu 
                        WHERE trata NOT IN ({", ".join([f"'{t}'" for t in TRAMITES_CONFIG[gerencia_clean].keys() if t != 'INTERVENCIONES'])})
                          AND trata != 'MDUG0102B'
                    ),
                    all_pases AS (
                        SELECT p.id_expediente, p.fecha, p.destinatario, p.usuario
                        FROM mvw_ee_pases_secgdu p
                        JOIN target_expedientes te ON p.id_expediente = te.id_expediente
                    ),
                    ingresos AS (
                        SELECT id_expediente, MIN(fecha)::date as fecha_ing
                        FROM all_pases
                        WHERE destinatario IN ({buzzers_sql})
                        GROUP BY id_expediente
                    ),
                    egresos_efectivos AS (
                        SELECT p.id_expediente, MIN(p.fecha)::date as fecha_egr
                        FROM all_pases p
                        JOIN ingresos i ON p.id_expediente = i.id_expediente
                        WHERE p.fecha > i.fecha_ing
                          AND p.usuario IN ({", ".join([f"'{u}'" for u in whitelist_users])})
                          AND p.destinatario NOT IN ({sector_whitelist_sql})
                        GROUP BY p.id_expediente
                    ),
                    stock_potencial AS (
                        SELECT i.id_expediente, i.fecha_ing, (CURRENT_DATE - i.fecha_ing) as dias, te.expediente
                        FROM ingresos i
                        JOIN target_expedientes te ON i.id_expediente = te.id_expediente
                        LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente
                        WHERE ee.id_expediente IS NULL
                    ),
                    analista_actual AS (
                        SELECT s.id_expediente, s.expediente, s.fecha_ing, s.dias, p.destinatario as analista,
                                ROW_NUMBER() OVER (PARTITION BY s.id_expediente ORDER BY p.fecha DESC) as rn
                        FROM stock_potencial s
                        JOIN all_pases p ON s.id_expediente = p.id_expediente
                    )
                    SELECT id_expediente, expediente, fecha_ing, dias, analista
                    FROM analista_actual
                    WHERE rn = 1 AND analista IN ({sector_whitelist_sql});
                """
            else:
                sql = f"""
                    WITH target_expedientes AS (
                        SELECT id_expediente, expediente 
                        FROM mvw_expedientes_tratas_secgdu 
                        WHERE trata = '{trata_db}'
                    ),
                    all_pases AS (
                        SELECT p.id_expediente, p.fecha, p.destinatario, p.estado,
                                LAG(p.destinatario) OVER (PARTITION BY p.id_expediente ORDER BY p.fecha) as remitente
                        FROM mvw_ee_pases_secgdu p
                        JOIN target_expedientes te ON p.id_expediente = te.id_expediente
                    ),
                    ingresos AS (
                        SELECT id_expediente, MIN(fecha)::date as fecha_ing
                        FROM all_pases
                        WHERE (
                            (NOT {is_dgiur} AND destinatario IN ({buzzers_sql}))
                            OR
                            ({is_dgiur} AND destinatario = 'DGIUR-21' AND remitente = 'DGROC-AUTOMAT')
                        )
                        GROUP BY id_expediente
                    ),
                    egresos_efectivos AS (
                        SELECT g.id_expediente, MIN(g.fecha_creacion)::date as fecha_egr
                        FROM mvw_datos_gedo_secgdu g
                        JOIN ingresos i ON g.id_expediente = i.id_expediente
                        WHERE g.acronimo IN ({acronimos})
                          AND g.fecha_creacion >= i.fecha_ing
                          AND (NOT {is_dgiur} OR g.usuario_creador IN ('VASTAM', 'ALANDAZURI', 'FVERDAGUER', 'VGAYTAN', 'ZONCA', 'CGIRAUD'))
                          AND ('{trata_db}' != 'MDUG0901A' OR g.usuario_creador IN ('FABIANSANTILLAN', 'LICETB'))
                        GROUP BY g.id_expediente
                    ),
                    egresos_no_efectivos AS (
                        SELECT id_expediente, MIN(fecha_egr) as fecha_egr
                        FROM (
                            SELECT p.id_expediente, MIN(p.fecha)::date as fecha_egr
                            FROM all_pases p
                            JOIN ingresos i ON p.id_expediente = i.id_expediente
                            WHERE (p.estado = 'Guarda Temporal' OR p.destinatario = 'GUARDA TEMPORAL')
                              AND p.fecha > i.fecha_ing
                            GROUP BY p.id_expediente
                            UNION ALL
                            SELECT g.id_expediente, MIN(g.fecha_creacion)::date as fecha_egr
                            FROM mvw_datos_gedo_secgdu g
                            JOIN ingresos i ON g.id_expediente = i.id_expediente
                            WHERE ({is_auto} OR {is_dgiur}) AND g.acronimo = 'IFCFP'
                            GROUP BY g.id_expediente
                            UNION ALL
                            SELECT p.id_expediente, MIN(p.fecha)::date as fecha_egr
                            FROM all_pases p
                            JOIN ingresos i ON p.id_expediente = i.id_expediente
                            WHERE {is_auto} AND p.destinatario = 'DGIUR-21' AND p.remitente = 'DGROC-AUTOMAT'
                            GROUP BY p.id_expediente
                        ) sub
                        GROUP BY id_expediente
                    ),
                    stock_potencial AS (
                        SELECT i.id_expediente, i.fecha_ing, (CURRENT_DATE - i.fecha_ing) as dias, te.expediente,
                                CASE WHEN te.estado ILIKE 'Subsanaci%' OR te.estado ILIKE 'Subsanación%' THEN 1 ELSE 0 END as is_subs
                        FROM ingresos i
                        JOIN mvw_expedientes_tratas_secgdu te ON i.id_expediente = te.id_expediente
                        LEFT JOIN egresos_efectivos ee ON i.id_expediente = ee.id_expediente
                        LEFT JOIN egresos_no_efectivos en ON i.id_expediente = en.id_expediente
                        WHERE ee.id_expediente IS NULL AND en.id_expediente IS NULL
                    ),
                    analista_actual AS (
                        SELECT s.id_expediente, s.expediente, s.fecha_ing, s.dias, s.is_subs, p.destinatario as analista,
                                ROW_NUMBER() OVER (PARTITION BY s.id_expediente ORDER BY p.fecha DESC) as rn
                        FROM stock_potencial s
                        JOIN mvw_ee_pases_secgdu p ON s.id_expediente = p.id_expediente
                    )
                    SELECT id_expediente, expediente, fecha_ing, dias, analista, is_subs
                    FROM analista_actual
                    WHERE rn = 1 AND (analista IN ({sector_whitelist_sql}) OR is_subs = 1);
                """
            
            result = conn.execute(text(sql))
            rows = result.fetchall()
            
            propio_month_counts = {}
            analyst_data = {}
            ranges = [(0, 15, "Menos de 15 dias"), (15, 30, "15 a 30 dias"), (30, 45, "30 a 45 dias"), (45, 60, "45 a 60 dias"), (60, 75, "60 a 75 dias"), (75, 90, "75 a 90 dias"), (90, 999999, "Mas de 90 dias")]
            
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
            
            month_dist = [{"periodo": m, "cantidad": propio_month_counts.get(m, 0)} for m in sorted(propio_month_counts.keys())]
            
            analyst_dist = []
            for name, counts in analyst_data.items():
                counts["analista"] = name
                analyst_dist.append(counts)
            analyst_dist.sort(key=lambda x: x["TOTAL"], reverse=True)
            
            expedientes = [
                {
                    "id_expediente": r.id_expediente, 
                    "expediente": r.expediente, 
                    "fecha_ing": r.fecha_ing.isoformat(), 
                    "dias": r.dias, 
                    "analista": r.analista or "SIN ASIGNAR",
                    "is_subs": r.is_subs
                } for r in rows
            ]
            
            return {"month_distribution": month_dist, "analyst_distribution": analyst_dist, "expedientes": expedientes}
            
    except Exception as e:
        logger.error(f"Error en stock_detail ({trata}): {e}")
        raise HTTPException(status_code=500, detail="Error al obtener detalle de stock.")

@app.get("/api/reporte/{gerencia}/intervenciones/detalle")
async def get_intervenciones_detalle(gerencia: str):
    gerencia_clean = gerencia.lower()
    cache_key = f"intervenciones_det_{gerencia_clean}"
    cached = get_cached_data(cache_key)
    if cached: return cached

    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
        
    excluir_tratas = list(TRAMITES_CONFIG[gerencia_clean].keys())
    if 'INTERVENCIONES' in excluir_tratas: excluir_tratas.remove('INTERVENCIONES')
    excluir_filter = ", ".join([f"'{t}'" for t in excluir_tratas])
    
    buzzers = BUZZERS_MAP.get(gerencia_clean, [])
    buzzers_sql = ", ".join([f"'{s}'" for s in buzzers]) or "'DGROC-SIN-BUZZER'"

    sql = f"""
        WITH target_expedientes AS (
            SELECT id_expediente, trata, descripcion_trata
            FROM mvw_expedientes_tratas_secgdu 
            WHERE trata NOT IN ({excluir_filter}) AND trata != 'MDUG0102B'
        ),
        ingresos AS (
            SELECT p.id_expediente, MIN(p.fecha) as fecha_ing
            FROM mvw_ee_pases_secgdu p
            JOIN target_expedientes te ON p.id_expediente = te.id_expediente
            WHERE p.destinatario IN ({buzzers_sql})
            GROUP BY p.id_expediente
        )
        SELECT 
            te.trata, te.descripcion_trata as detalle,
            EXTRACT(YEAR FROM i.fecha_ing)::int as anio,
            EXTRACT(MONTH FROM i.fecha_ing)::int as mes,
            COUNT(*) as cantidad
        FROM ingresos i
        JOIN target_expedientes te ON i.id_expediente = te.id_expediente
        WHERE i.fecha_ing >= (CURRENT_DATE - INTERVAL '4 months')
        GROUP BY te.trata, te.descripcion_trata, anio, mes
        ORDER BY anio DESC, mes DESC, cantidad DESC
    """
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [dict(row._mapping) for row in result.all()]
            breakdown = {}
            for r in rows:
                key = r['trata']
                if key not in breakdown:
                    breakdown[key] = {"trata": r['trata'], "detalle": r['detalle'], "meses": {}}
                breakdown[key]["meses"][f"{r['anio']}-{r['mes']}"] = r['cantidad']
            data = list(breakdown.values())
            set_cached_data(cache_key, data)
            return data
    except Exception as e:
        logger.error(f"Error en intervenciones/detalle: {e}")
        return []

@app.get("/api/reporte/{gerencia}/tramite/{trata}")
async def get_reporte_tramite(gerencia: str, trata: str):
    gerencia_clean = gerencia.lower()
    try:
        with engine.connect() as conn:
            sql = f"""
                SELECT anio, mes, "ING", "EGR_EF", "EGR_NE", "STOCK_TOTAL", "STOCK_SUBS", "STOCK_PROPIO"
                FROM mvw_reporte_historico_dgroc 
                WHERE "GERENCIA" = '{gerencia_clean}' AND "COD TRATA" = '{trata}'
                  AND (anio < 2026 OR (anio = 2026 AND mes <= 5))
                ORDER BY anio DESC, mes DESC LIMIT 12
            """
            result = conn.execute(text(sql))
            return [dict(row._mapping) for row in result.all()]
    except Exception as e:
        logger.error(f"Error en tramite {trata}: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener reporte histórico.")

@app.get("/api/catastro/tramites")
async def list_tramites_catastro():
    return [{"id": k, "nombre": v["nombre"]} for k, v in TRAMITES_CONFIG.get("catastro", {}).items()]

@app.get("/health")
async def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected", "timestamp": datetime.now().isoformat()}
    except Exception:
        return {"status": "error", "db": "disconnected", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    # En producción (Vercel/GitHub), se recomienda usar workers y no reload
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
