import os
import json
import psycopg2
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path if os.path.exists(env_path) else None)

LOCAL_URL = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')

def update_views_data():
    conn = psycopg2.connect(LOCAL_URL)
    cur = conn.cursor()

    # 1. Obtener vistas estándar
    cur.execute("""
        SELECT table_name, view_definition 
        FROM information_schema.views 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    views = cur.fetchall()

    # 2. Obtener vistas materializadas
    cur.execute("""
        SELECT matviewname, definition 
        FROM pg_matviews 
        WHERE schemaname = 'public'
        ORDER BY matviewname;
    """)
    matviews = cur.fetchall()

    data = {
        "views": [[v[0], v[1]] for v in views],
        "matviews": [[m[0], m[1]] for m in matviews]
    }

    target_file = 'deploy/build_all_local_views.py'
    
    script_header = '''import psycopg2
import time
import os
import json
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path if os.path.exists(env_path) else None)

LOCAL_URL = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')

def get_conn():
    conn = psycopg2.connect(LOCAL_URL)
    conn.autocommit = True
    return conn

VIEWS_DATA = ''' + json.dumps(data) + '''

def build_views():
    views = VIEWS_DATA.get("views", [])
    print(f"\\n--- Reconstruyendo {len(views)} Vistas Estándar ---")
    for name, v_def in views:
        full_name = f"public.{name}"
        clean_def = v_def.rstrip('; \\t\\n\\r')
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"CREATE OR REPLACE VIEW {full_name} AS {clean_def};")
            print(f"  [+] Vista OK: {name}")
        except Exception as e:
            print(f"  [-] Error en vista {name}: {e}")

def build_matviews():
    matviews = VIEWS_DATA.get("matviews", [])
    print(f"\\n--- Reconstruyendo {len(matviews)} Vistas Materializadas ---")
    pending = list(matviews)
    pass_num = 1
    while pending:
        still_pending = []
        created = 0
        print(f"\\n-- Pasada {pass_num} (Pendientes: {len(pending)}) --")
        pass_num += 1
        for name, v_def in pending:
            full_name = f"public.{name}"
            clean_def = v_def.rstrip('; \\t\\n\\r')
            try:
                t0 = time.time()
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(f"DROP MATERIALIZED VIEW IF EXISTS {full_name} CASCADE;")
                        cur.execute(f"CREATE MATERIALIZED VIEW {full_name} AS {clean_def} WITH DATA;")
                print(f"  [+] MV Creada: {name} ({time.time() - t0:.2f}s)", flush=True)
                created += 1
            except Exception as e:
                still_pending.append((name, v_def, str(e)))
        if created == 0:
            if still_pending:
                print("\\n  [!] Vistas materializadas que no pudieron resolverse:", flush=True)
                for n, d, err in still_pending:
                    print(f"    - {n}: {err.splitlines()[0]}", flush=True)
            break
        pending = [(n, d) for n, d, _ in still_pending]

def main():
    start = time.time()
    print("==========================================================")
    print(" 🚀 CONSTRUCCIÓN COMPLETA DE VISTAS (155 VISTAS DE ENTORNO LOCAL)")
    print("==========================================================")
    build_views()
    build_matviews()
    print("==========================================================")
    print(f" ✅ Finalizado en {(time.time() - start)/60:.2f} minutos.")
    print("==========================================================")

if __name__ == '__main__':
    main()
'''

    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(script_header)
    print(f"Actualizado {target_file} con las nuevas definiciones de vistas y matviews.")

if __name__ == '__main__':
    update_views_data()
