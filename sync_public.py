import psycopg2
import time
import sys
import os
import tempfile
import re
from dotenv import load_dotenv

load_dotenv() # Carga variables desde el archivo .env

# --- CONFIGURACIÓN ---
LOCAL_URL = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')
REMOTE_URL = os.getenv('DATABASE_URL_PUBLIC', 'postgresql://postgres:frQB7%7D0%26p~.C_.X%40Ymu(1tAO7@34.136.69.128:5432/prefapp')

BASE_TABLES = [
    "mvw_expedientes_tratas_secgdu",
    "mvw_ee_pases_secgdu",
    "mvw_datos_gedo_secgdu",
    "mvw_ee_gedo_secgdu",
    "df_form_comp_value",
    "auth_users"
]

def get_conn(url):
    return psycopg2.connect(url)

def kill_remote_sessions():
    print(">>> [1/4] Limpiando bloqueos en el servidor remoto...", flush=True)
    try:
        base_url = REMOTE_URL.rsplit('/', 1)[0]
        with get_conn(f"{base_url}/postgres") as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'prefapp' AND pid <> pg_backend_pid();")
        print("    [OK] Sesiones limpiadas.")
    except Exception as e:
        print(f"    [!] Aviso: {e}")

class ProgressWrapper:
    def __init__(self, f, total_size):
        self.f = f
        self.total_size = total_size
        self.bytes_read = 0
        self.last_update = 0

    def read(self, size):
        chunk = self.f.read(size)
        if chunk:
            self.bytes_read += len(chunk)
            percent = (self.bytes_read / self.total_size) * 100
            if percent - self.last_update >= 5 or percent >= 100:
                print(f"\r    - Progreso: {percent:.1f}% ({self.bytes_read/(1024*1024):.1f}/{self.total_size/(1024*1024):.1f} MB)", end='', flush=True)
                self.last_update = percent
        return chunk

def sync_table(table_name):
    print(f"\n>>> [2/4] Sincronizando: {table_name}...", flush=True)
    start_t = time.time()
    tmp_path = None
    
    try:
        # 0. Contar filas
        row_count = 0
        with get_conn(LOCAL_URL) as local_conn:
            with local_conn.cursor() as local_cur:
                local_cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                row_count = local_cur.fetchone()[0]
        print(f"    - Filas totales: {row_count:,}")

        # 1. Exportar de local
        print(f"    - Exportando de local...", end='', flush=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tsv') as tmp:
            tmp_path = tmp.name
            with get_conn(LOCAL_URL) as local_conn:
                with local_conn.cursor() as local_cur:
                    query = f'COPY (SELECT * FROM "{table_name}") TO STDOUT WITH (FORMAT TEXT, NULL \'NULL\')'
                    local_cur.copy_expert(query, tmp)
        print(f" [DONE]")

        # 2. Preparar Remoto (Recrear tabla con tipos reales)
        print(f"    - Recreando tabla en remoto...", end='', flush=True)
        with get_conn(REMOTE_URL) as remote_conn:
            remote_conn.autocommit = True
            with remote_conn.cursor() as remote_cur:
                with get_conn(LOCAL_URL) as local_conn:
                    with local_conn.cursor() as local_cur:
                        local_cur.execute(f"""
                            SELECT column_name, data_type, character_maximum_length 
                            FROM information_schema.columns 
                            WHERE table_name = '{table_name}' 
                            ORDER BY ordinal_position
                        """)
                        cols_info = local_cur.fetchall()
                        
                        if not cols_info:
                            local_cur.execute(f"""
                                SELECT a.attname, format_type(a.atttypid, a.atttypmod)
                                FROM pg_attribute a
                                JOIN pg_class t ON a.attrelid = t.oid
                                WHERE t.relname = '{table_name}' AND a.attnum > 0
                            """)
                            cols_info = local_cur.fetchall()
                            
                        cols_ddl = []
                        for c in cols_info:
                            col_name, col_type = c[0], c[1]
                            if 'timestamp' in col_type: col_type = 'TIMESTAMP'
                            elif 'date' in col_type: col_type = 'DATE'
                            elif 'integer' in col_type: col_type = 'INTEGER'
                            elif 'bigint' in col_type: col_type = 'BIGINT'
                            elif 'double precision' in col_type: col_type = 'DOUBLE PRECISION'
                            elif 'numeric' in col_type: col_type = 'NUMERIC'
                            else: col_type = 'TEXT'
                            cols_ddl.append(f'"{col_name}" {col_type}')
                
                remote_cur.execute(f"""
                    DO $$ BEGIN
                        IF EXISTS (SELECT 1 FROM pg_matviews WHERE matviewname = '{table_name}') THEN DROP MATERIALIZED VIEW "{table_name}" CASCADE;
                        ELSIF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = '{table_name}') THEN DROP TABLE "{table_name}" CASCADE;
                        ELSIF EXISTS (SELECT 1 FROM pg_views WHERE viewname = '{table_name}') THEN DROP VIEW "{table_name}" CASCADE;
                        END IF;
                    END $$;
                """)
                remote_cur.execute(f'CREATE TABLE "{table_name}" ({", ".join(cols_ddl)})')
        print(f" [DONE]")

        # 3. Importar a remoto con progreso
        file_size = os.path.getsize(tmp_path)
        print(f"    - Subiendo a remoto ({file_size/(1024*1024):.1f} MB)...")
        with open(tmp_path, 'rb') as f:
            wrapped_f = ProgressWrapper(f, file_size)
            with get_conn(REMOTE_URL) as remote_conn:
                remote_conn.autocommit = True
                with remote_conn.cursor() as remote_cur:
                    remote_cur.copy_from(wrapped_f, table_name, sep='\t', null='NULL')
        
        print(f"\n    - [OK] ({time.time()-start_t:.2f}s)")
        return True
    except Exception as e:
        print(f"\n    - [ERROR] {e}")
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

def create_indexes():
    print("\n>>> [3/4] Creando índices de optimización...", flush=True)
    indexes = [
        ("idx_pases_id_exp_prod", "mvw_ee_pases_secgdu", "id_expediente"),
        ("idx_gedo_id_exp_prod", "mvw_datos_gedo_secgdu", "id_expediente"),
        ("idx_exp_trata_id_prod", "mvw_expedientes_tratas_secgdu", "id_expediente")
    ]
    with get_conn(REMOTE_URL) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            for name, table, col in indexes:
                print(f"    - Índice {name}...", end='', flush=True)
                try:
                    cur.execute(f'CREATE INDEX IF NOT EXISTS "{name}" ON "{table}" ("{col}")')
                    print(" [OK]")
                except Exception as e:
                    print(f" [ERROR] {e}")

def deploy_queries():
    print("\n>>> [4/4] Desplegando Vistas (Carpeta /queries)...", flush=True)
    q_dir = "queries"
    priority = [
        "setup_auth_table.sql",
        "setup_unified_analytics.sql",
        "populate_cfg_metas.sql",
        "create_consolidated_view.sql",
        "mvw_reporte_historico_catastro.sql",
        "mvw_reporte_historico_instalaciones.sql",
        "mvw_reporte_historico_contable.sql",
        "mvw_reporte_historico_regularizacion.sql",
        "mvw_reporte_historico_etapa_proyecto.sql",
        "mvw_reporte_historico_aviso_obra.sql",
        "mvw_reporte_historico_morfologia.sql",
        "mvw_reporte_historico_aph.sql",
        "mvw_reporte_historico_usos.sql",
        "mvw_stock_actual_detalle.sql",
        "mvw_reporte_historico_global.sql",
        "create_historical_view.sql"
    ]
    
    available = [f for f in os.listdir(q_dir) if f.endswith('.sql')]
    to_run = [f for f in priority if f in available]
    to_run += [f for f in available if f not in priority]
    
    for sql_file in to_run:
        path = os.path.join(q_dir, sql_file)
        print(f"    - Ejecutando {sql_file}...", end='', flush=True)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            if not content.strip(): continue
            
            match = re.search(r'CREATE\s+(?:MATERIALIZED\s+)?VIEW\s+(\w+)', content, re.IGNORECASE)
            if match:
                obj_name = match.group(1)
                smart_drop = f"""
                    DO $$ BEGIN
                        IF EXISTS (SELECT 1 FROM pg_matviews WHERE matviewname = '{obj_name}') THEN DROP MATERIALIZED VIEW "{obj_name}" CASCADE;
                        ELSIF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = '{obj_name}') THEN DROP TABLE "{obj_name}" CASCADE;
                        ELSIF EXISTS (SELECT 1 FROM pg_views WHERE viewname = '{obj_name}') THEN DROP VIEW "{obj_name}" CASCADE;
                        END IF;
                    END $$;
                """
                content = smart_drop + content

            with get_conn(REMOTE_URL) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute("SET statement_timeout = 0;")
                    cur.execute("SET work_mem = '128MB';")
                    cur.execute(content)
            print(" [OK]")
        except Exception as e:
            print(f" [ERROR] {str(e).splitlines()[0][:100]}...")

def main():
    print("====================================================")
    print("REPLICADOR DE BASE DE DATOS SGDU (LOCAL -> PUBLIC)")
    print("====================================================")
    start_total = time.time()
    kill_remote_sessions()
    for t in BASE_TABLES:
        sync_table(t)
    create_indexes()
    deploy_queries()
    print(f"\n====================================================")
    print(f"PROCESO FINALIZADO EN {time.time()-start_total:.2f}s")
    print("====================================================")

if __name__ == "__main__":
    main()
