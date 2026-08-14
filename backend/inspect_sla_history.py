from database import engine
from sqlalchemy import text

g_list = ['catastro', 'instalaciones', 'regularizacion', 'contable', 'etapa_proyecto', 'morfologia', 'aph', 'usos', 'aviso_obra']

with engine.connect() as conn:
    print("--- Checking mv_tiempos_resolucion_{g} columns and sample row ---")
    r = conn.execute(text("SELECT * FROM mv_tiempos_resolucion_catastro LIMIT 1")).mappings().first()
    print("mv_tiempos_resolucion_catastro keys:", list(r.keys()) if r else "Empty")
    if r:
        print("Sample data:", dict(r))
