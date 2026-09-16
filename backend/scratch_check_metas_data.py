import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== REGISTROS EN planificacion_metas_v2_resumen ===")
    try:
        r = conn.execute(text("SELECT gerencia, count(*) as cant FROM planificacion_metas_v2_resumen GROUP BY gerencia")).mappings().fetchall()
        for row in r:
            print(dict(row))
    except Exception as e:
        print("Error:", e)

    print("\n=== TABLA cfg_tiempos_tramitacion PARA CATASTRO ===")
    try:
        r_t = conn.execute(text("SELECT * FROM cfg_tiempos_tramitacion WHERE gerencia = 'catastro'")).mappings().fetchall()
        print(f"Total filas tiempos tramitacion catastro: {len(r_t)}")
        for row in r_t:
            print(dict(row))
    except Exception as e:
        print("Error:", e)
