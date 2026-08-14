from database import engine
from sqlalchemy import text

g_list = ['catastro', 'instalaciones', 'regularizacion', 'contable', 'etapa_proyecto', 'morfologia', 'aph', 'usos', 'aviso_obra']

with engine.connect() as conn:
    print("=== INSPECTING mv_catastro_interv_egresos_eventos ===")
    r = conn.execute(text("SELECT * FROM mv_catastro_interv_egresos_eventos LIMIT 1")).mappings().first()
    print("Keys:", list(r.keys()) if r else "Empty")
    if r:
        print("Sample row:", dict(r))
