import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    for t in ['mv_catastro_ingresos_eventos', 'mv_catastro_gedos_egreso', 'mv_catastro_interv_egresos_eventos', 'mv_catastro_egresos_no_efectivos']:
        try:
            r = conn.execute(text(f"SELECT * FROM {t} LIMIT 1")).fetchone()
            print(f"{t}:", list(r._mapping.keys()) if r else "Empty table")
            if r:
                print(" Sample row:", dict(r._mapping))
        except Exception as e:
            print(f"Error reading {t}:", e)
