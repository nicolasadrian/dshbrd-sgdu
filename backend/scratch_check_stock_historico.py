import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== INSPECTING DEFINITION OF mv_catastro_stock_historico ===")
    try:
        res = conn.execute(text("SELECT pg_get_viewdef('mv_catastro_stock_historico'::regclass, true)")).scalar()
        print(res)
    except Exception as e:
        print("Error reading def:", e)

    print("\n=== VALORES ACTUALES EN mv_catastro_stock_historico PARA MDUG0134N ===")
    try:
        rows = conn.execute(text("""
            SELECT mes_label, categoria, cant_expedientes
            FROM mv_catastro_stock_historico
            WHERE trata = 'MDUG0134N'
            ORDER BY mes_label, categoria
        """)).mappings().fetchall()
        for r in rows:
            print(dict(r))
    except Exception as e:
        print("Error reading data:", e)
