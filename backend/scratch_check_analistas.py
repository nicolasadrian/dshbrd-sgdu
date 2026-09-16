import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== BUSCANDO BAGLIONIM Y MOMILLALONCO EN DB ===")
    r = conn.execute(text("SELECT id, gerencia, trata_reporte, analistas_oficiales FROM cfg_gestion_metas WHERE gerencia='catastro'")).mappings().fetchall()
    for row in r:
        analistas = row['analistas_oficiales'] or []
        has_b = 'BAGLIONIM' in analistas
        has_m = 'MOMILLALONCO' in analistas
        if has_b or has_m:
            print(f"Row id={row['id']}, trata={row['trata_reporte']}, has_BAGLIONIM={has_b}, has_MOMILLALONCO={has_m}")
            print(f"Total analistas: {len(analistas)}")
            break
    else:
        print("No se encontraron en las filas analizadas o se listarán analistas...")
        if r:
            print("Ejemplo analistas fila 1:", r[0]['analistas_oficiales'])
