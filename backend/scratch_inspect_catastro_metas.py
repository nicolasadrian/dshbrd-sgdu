import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== INSPECTING planificacion_metas_v2_resumen FOR CATASTRO ===")
    r = conn.execute(text("SELECT * FROM planificacion_metas_v2_resumen WHERE gerencia = 'catastro'")).mappings().fetchall()
    for row in r:
        print(dict(row))

    print("\n=== INSPECTING planificacion_tiempos_tramitacion_resumen FOR CATASTRO ===")
    r2 = conn.execute(text("SELECT * FROM planificacion_tiempos_tramitacion_resumen WHERE gerencia = 'catastro'")).mappings().fetchall()
    for row in r2:
        print(dict(row))
