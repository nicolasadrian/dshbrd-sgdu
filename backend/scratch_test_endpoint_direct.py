import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text
from routers.reportes import get_reporte_consolidado_gerencia

class DummyUser:
    username = "test"
    role = "admin"

print("Llamando a get_reporte_consolidado_gerencia('catastro')...")
try:
    res = get_reporte_consolidado_gerencia("catastro", current_user=DummyUser())
    print(f"Total filas consolidadas retornadas: {len(res)}")
    # Filtrar para MDUG0134N
    mdug = [r for r in res if r['COD TRATA'] == 'MDUG0134N']
    print(f"Filas para MDUG0134N: {len(mdug)}")
    for r in mdug:
        print(r)
except Exception as e:
    import traceback
    traceback.print_exc()
