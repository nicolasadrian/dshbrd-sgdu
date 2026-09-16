import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text
import json
import re

def update_build_views_file():
    filepath = 'deploy/build_all_local_views.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Reemplazar definiciones de matviews en VIEWS_DATA
    # Vamos a cargar VIEWS_DATA o actualizar usando json
    with engine.connect() as conn:
        views_to_update = [
            'mv_catastro_egresos_efectivos',
            'mv_catastro_gedos_egreso',
            'mv_catastro_egresos_no_efectivos',
            'mv_catastro_subsanaciones',
            'mv_catastro_stock_propio'
        ]
        new_defs = {}
        for v in views_to_update:
            sql_def = conn.execute(text(f"SELECT pg_get_viewdef('{v}'::regclass, true)")).scalar()
            new_defs[v] = sql_def

    # Leemos la variable VIEWS_DATA del archivo
    prefix = "VIEWS_DATA = "
    idx = content.find(prefix)
    if idx != -1:
        # Buscamos el final del JSON / dict
        # VIEWS_DATA termina antes de las funciones
        # O podemos usar ast / regex
        pass

    print("Definiciones obtenidas para exportar si es necesario.")

if __name__ == '__main__':
    update_build_views_file()
