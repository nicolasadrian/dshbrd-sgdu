from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    view_def = conn.execute(text("SELECT definition FROM pg_matviews WHERE matviewname = 'mv_tiempos_resolucion_catastro'")).scalar()
    print('View definition for mv_tiempos_resolucion_catastro:\n')
    print(view_def)
