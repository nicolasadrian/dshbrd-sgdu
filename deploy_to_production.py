import psycopg2
import time
import os
import tempfile
import re
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACIÓN ---
LOCAL_URL = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')
REMOTE_URL = os.getenv('DATABASE_URL_PUBLIC', 'postgresql://postgres:frQB7%7D0%26p~.C_.X%40Ymu(1tAO7@34.136.69.128:5432/sade_db')

# Tablas de Metadatos/Configuración a sincronizar
METADATA_TABLES = [
    "auth_users",
    "cfg_gestion_metas"
]

# Vistas y Consultas a compilar en orden de dependencia
VIEWS_TO_DEPLOY = [
    "v_expedientes_lifecycle.sql",
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

def get_conn(url):
    return psycopg2.connect(url)

def kill_remote_sessions():
    print(">>> [1/4] Limpiando bloqueos de sesion en servidor remoto...", flush=True)
    try:
        base_url = REMOTE_URL.rsplit('/', 1)[0]
        with get_conn(f"{base_url}/postgres") as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'prefapp' AND pid <> pg_backend_pid();")
        print("    [OK] Sesiones limpiadas.")
    except Exception as e:
        print(f"    [!] Aviso (Sesiones): {e}")

def sync_metadata_table(table_name):
    print(f"\n>>> [2/4] Sincronizando tabla de configuracion: {table_name}...", flush=True)
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
        print("    - Creando tabla en servidor remoto...", end='', flush=True)
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
        print(f" [ERROR] {e}")
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

def deploy_views():
    print("\n>>> [3/4] Desplegando Vistas Analiticas (queries/)...", flush=True)
    q_dir = "queries"
    
    for sql_file in VIEWS_TO_DEPLOY:
        path = os.path.join(q_dir, sql_file)
        if not os.path.exists(path):
            print(f"    - [!] Omitiendo {sql_file} (No se encuentra el archivo)")
            continue
            
        print(f"    - Ejecutando {sql_file}...", end='', flush=True)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            if not content.strip(): 
                print(" [VACIO]")
                continue
            
            # Buscar nombre del objeto para smart drop
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
            error_line = str(e).splitlines()[0][:120]
            print(f" [ERROR] {error_line}...")

def main():
    print("====================================================")
    print("ORQUESTRADOR DE LANZAMIENTO SEGURO - SGDU ANALYTICS")
    print("====================================================")
    start_total = time.time()
    
    # 1. Limpiar sesiones remotas para evitar bloqueos
    kill_remote_sessions()
    
    # 2. Sincronizar solo tablas de metadatos/configuración
    for t in METADATA_TABLES:
        sync_metadata_table(t)
        
    # 3. Compilar todas las vistas analíticas modularizadas
    deploy_views()
    
    print(f"\n====================================================")
    print(f"DESPLIEGUE FINALIZADO EXITOSAMENTE EN {time.time()-start_total:.2f}s")
    print("====================================================")

if __name__ == "__main__":
    main()
