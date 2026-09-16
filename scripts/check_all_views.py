import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text
from config import TRAMITES_CONFIG

with engine.connect() as conn:
    for g in TRAMITES_CONFIG.keys():
        g_clean = g.lower()
        print(f"=== {g_clean} ===")
        # check if egresos_no_efectivos has columns
        t_ne = f"mv_{g_clean}_egresos_no_efectivos"
        r = conn.execute(text(f"SELECT * FROM {t_ne} LIMIT 1")).fetchone()
        print(f" {t_ne}:", list(r._mapping.keys()) if r else "EMPTY")
        
        # check intervenciones egresadas table name
        t_int = f"mv_{g_clean}_interv_egresos_eventos" if g_clean != 'contable' else "mv_contable_intervenciones_egresadas"
        r2 = conn.execute(text(f"SELECT * FROM {t_int} LIMIT 1")).fetchone()
        print(f" {t_int}:", list(r2._mapping.keys()) if r2 else "EMPTY")
