import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== DEFINICIONES DE MATVIEWS DE CATASTRO ===")
    views = [
        'mv_catastro_universo',
        'mv_catastro_stock_propio',
        'mv_catastro_subsanaciones',
        'mv_catastro_egresos_efectivos',
        'mv_catastro_egresos_no_efectivos',
        'mv_catastro_gedos_egreso',
        'mv_catastro_ingresos_eventos'
    ]
    for v in views:
        res = conn.execute(text(f"SELECT pg_get_viewdef('{v}'::regclass, true)")).scalar()
        print(f"\n****************** {v} ******************")
        print(res)
