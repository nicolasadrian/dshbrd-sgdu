import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text
from config import TRAMITES_CONFIG
from routers.reportes import calculate_all_trata_expected_egresos_batch

with engine.connect() as conn:
    print("=== PROBANDO FALLBACKS CON TRANSACCIÓN AISLADA ===")
    gerencia_clean = 'catastro'
    trata_codes = list(TRAMITES_CONFIG[gerencia_clean].keys())

    fallbacks = calculate_all_trata_expected_egresos_batch(conn, gerencia_clean, trata_codes + ['INTERVENCIONES'])
    print("Fallbacks devueltos:")
    for k, v in sorted(fallbacks.items()):
        print(f"  {k}: {v}")
