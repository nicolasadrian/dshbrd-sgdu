import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text
from config import TRAMITES_CONFIG
from routers.reportes import calculate_all_trata_expected_egresos_batch

with engine.connect() as conn:
    print("=== TARGETS / METAS PARA CATASTRO EN SEGUIMIENTO ===")
    gerencia_clean = 'catastro'
    trata_codes = list(TRAMITES_CONFIG[gerencia_clean].keys())

    # 1. Chequeamos mv_plan_metas_catastro si existe
    try:
        r = conn.execute(text("SELECT * FROM mv_plan_metas_catastro LIMIT 5")).mappings().fetchall()
        print(f"Filas en mv_plan_metas_catastro: {len(r)}")
        for row in r:
            print(dict(row))
    except Exception as e:
        print("Error en mv_plan_metas_catastro:", e)

    # 2. Fallbacks de calculate_all_trata_expected_egresos_batch
    fallbacks = calculate_all_trata_expected_egresos_batch(conn, gerencia_clean, trata_codes + ['INTERVENCIONES'])
    print("\nFallbacks calculados (targetEgr):")
    for k, v in fallbacks.items():
        print(f"  {k}: {v}")
