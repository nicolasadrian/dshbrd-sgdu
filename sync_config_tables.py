import psycopg2
import time
import os
import tempfile
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACIÓN ---
LOCAL_URL = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')
REMOTE_URL = os.getenv('DATABASE_URL_PUBLIC', 'postgresql://postgres:frQB7%7D0%26p~.C_.X%40Ymu(1tAO7@34.136.69.128:5432/sade_db')

CONFIG_TABLES = [
    "cfg_egresos_por_trata",
    "cfg_gestion_metas"
]

def get_conn(url):
    return psycopg2.connect(url)

def kill_remote_sessions():
    print(">>> [1/2] Limpiando bloqueos en el servidor remoto...", flush=True)
    try:
        base_url = REMOTE_URL.rsplit('/', 1)[0]
        with get_conn(f"{base_url}/postgres") as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'prefapp' AND pid <> pg_backend_pid();")
        print("    [OK] Sesiones limpiadas.")
    except Exception as e:
        print(f"    [!] Aviso (Sesiones): {e}")

def sync_config_table(table_name):
    print(f"\n>>> [2/2] Sincronizando tabla de configuracion: {table_name}...", flush=True)
    start_t = time.time()
    tmp_path = None
    
    try:
        # 1. Exportar datos locales a TSV temporal
        print("    - Exportando datos locales...", end='', flush=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tsv') as tmp:
            tmp_path = tmp.name
            with get_conn(LOCAL_URL) as local_conn:
                with local_conn.cursor() as local_cur:
                    query = f'COPY (SELECT * FROM "{table_name}") TO STDOUT WITH (FORMAT TEXT, NULL \'NULL\')'
                    local_cur.copy_expert(query, tmp)
        print(" [OK]")

        # 2. Obtener estructura DDL exacta de la tabla local
        print("    - Obteniendo columnas y tipos...", end='', flush=True)
        with get_conn(LOCAL_URL) as local_conn:
            with local_conn.cursor() as local_cur:
                local_cur.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' 
                    ORDER BY ordinal_position
                """)
                cols_info = local_cur.fetchall()
                
                cols_ddl = []
                for col_name, col_type in cols_info:
                    if 'timestamp' in col_type: col_type = 'TIMESTAMP'
                    elif 'date' in col_type: col_type = 'DATE'
                    elif 'integer' in col_type: col_type = 'INTEGER'
                    elif 'bigint' in col_type: col_type = 'BIGINT'
                    elif 'double precision' in col_type: col_type = 'DOUBLE PRECISION'
                    elif 'numeric' in col_type: col_type = 'NUMERIC'
                    elif 'boolean' in col_type: col_type = 'BOOLEAN'
                    elif 'jsonb' in col_type: col_type = 'JSONB'
                    elif 'array' in col_type or 'ARRAY' in col_type or col_type.endswith('[]'): col_type = 'TEXT[]'
                    else: col_type = 'TEXT'
                    cols_ddl.append(f'"{col_name}" {col_type}')
        print(" [OK]")

        # 3. Recrear tabla en servidor remoto
        print("    - Recreando tabla en servidor remoto...", end='', flush=True)
        with get_conn(REMOTE_URL) as remote_conn:
            remote_conn.autocommit = True
            with remote_conn.cursor() as remote_cur:
                remote_cur.execute(f"""
                    DO $$ BEGIN
                        IF EXISTS (SELECT 1 FROM pg_matviews WHERE matviewname = '{table_name}') THEN DROP MATERIALIZED VIEW "{table_name}" CASCADE;
                        ELSIF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = '{table_name}') THEN DROP TABLE "{table_name}" CASCADE;
                        ELSIF EXISTS (SELECT 1 FROM pg_views WHERE viewname = '{table_name}') THEN DROP VIEW "{table_name}" CASCADE;
                        END IF;
                    END $$;
                """)
                remote_cur.execute(f'CREATE TABLE "{table_name}" ({", ".join(cols_ddl)})')
        print(" [OK]")

        # 4. Importar datos al servidor remoto
        print("    - Subiendo registros a servidor remoto...", end='', flush=True)
        with open(tmp_path, 'rb') as f:
            with get_conn(REMOTE_URL) as remote_conn:
                remote_conn.autocommit = True
                with remote_conn.cursor() as remote_cur:
                    remote_cur.copy_from(f, table_name, sep='\t', null='NULL')
        print(" [OK]")
        print(f"    - Tabla {table_name} sincronizada exitosamente en {time.time()-start_t:.2f}s.")
        return True
    except Exception as e:
        print(f" [ERROR] No se pudo sincronizar la tabla {table_name}: {e}")
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

def main():
    print("====================================================")
    print("REPLICA DE CONFIGURACIONES (LOCAL -> PUBLIC)")
    print("====================================================")
    start_total = time.time()
    
    # 1. Limpiar sesiones remotas
    kill_remote_sessions()
    
    # 2. Sincronizar las dos tablas de configuración de metas y egresos
    for t in CONFIG_TABLES:
        sync_config_table(t)
        
    print(f"\n====================================================")
    print(f"PROCESO DE CONFIGURACIONES FINALIZADO EN {time.time()-start_total:.2f}s")
    print("====================================================")

if __name__ == "__main__":
    main()
