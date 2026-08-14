from database import engine
from sqlalchemy import text

g_list = ['catastro', 'instalaciones', 'regularizacion', 'contable', 'etapa_proyecto', 'morfologia', 'aph', 'usos', 'aviso_obra']

with engine.connect() as conn:
    matviews = [r[0] for r in conn.execute(text("SELECT matviewname FROM pg_matviews WHERE schemaname = 'public'"))]
    for g in g_list:
        v_tr = f"mv_tiempos_resolucion_{g}"
        v_eg = f"mv_{g}_egresos_efectivos"
        print(f"Gerencia {g:15s} -> {v_tr}: {'EXISTS' if v_tr in matviews else 'MISSING'} | {v_eg}: {'EXISTS' if v_eg in matviews else 'MISSING'}")
