import psycopg2
import time
import os
import tempfile
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACIÓN ---
LOCAL_URL = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')
REMOTE_URL = os.getenv('DATABASE_URL_PUBLIC', 'postgresql://postgres:frQB7%7D0%26p~.C_.X%40Ymu(1tAO7@34.136.69.128:5432/sade_db')

# Configuración de las 6 tablas transaccionales masivas
SADE_TABLES_CONFIG = {
    "df_form_comp_value": {
        "key_col": "id",
        "key_type": "integer"
    },
    "mvw_datos_gedo_secgdu": {
        "key_col": "fecha_creacion",
        "key_type": "timestamp",
        "safety_hours": 3
    },
    "mvw_ee_actividades_secgdu": {
        "key_col": "fecha_alta",
        "key_type": "timestamp",
        "safety_hours": 3
    },
    "mvw_ee_gedo_secgdu": {
        "key_col": "id_transaccion",
        "key_type": "integer"
    },
    "mvw_ee_pases_secgdu": {
        "key_col": "fecha",
        "key_type": "timestamp",
        "safety_hours": 3
    },
    "mvw_expedientes_tratas_secgdu": {
        "key_col": "id_expediente",
        "key_type": "integer"
    }
}

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

def check_remote_table_exists(table_name):
    try:
        with get_conn(REMOTE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_tables WHERE tablename = %s
                    )
                """, (table_name,))
                return cur.fetchone()[0]
    except Exception as e:
        print(f"    [!] Error al chequear existencia de {table_name}: {e}")
        return False

def create_remote_table_from_local(table_name):
    print(f"    - [NUEVA TABLA] La tabla no existe en remoto. Creando DDL...", end='', flush=True)
    try:
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
                    
        with get_conn(REMOTE_URL) as remote_conn:
            remote_conn.autocommit = True
            with remote_conn.cursor() as remote_cur:
                remote_cur.execute(f'CREATE TABLE "{table_name}" ({", ".join(cols_ddl)})')
        print(" [OK]")
        return True
    except Exception as e:
        print(f" [ERROR] No se pudo crear la tabla {table_name}: {e}")
        return False

def get_max_remote_value(table_name, key_col):
    try:
        with get_conn(REMOTE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(f'SELECT MAX("{key_col}") FROM "{table_name}"')
                val = cur.fetchone()[0]
                return val
    except Exception as e:
        print(f"    [!] Error al obtener el maximo remoto de {table_name}: {e}")
        return None

def sync_table_incremental(table_name, config):
    key_col = config["key_col"]
    key_type = config["key_type"]
    
    print(f"\n>>> [2/2] Sincronizando tabla: {table_name}...", flush=True)
    start_t = time.time()
    
    # 1. Verificar existencia de la tabla en remoto
    table_exists = check_remote_table_exists(table_name)
    if not table_exists:
        success = create_remote_table_from_local(table_name)
        if not success:
            return False
            
    # 2. Obtener valor máximo en producción remota
    remote_max = get_max_remote_value(table_name, key_col)
    is_full_sync = (remote_max is None)
    
    tmp_path = None
    try:
        local_conn = get_conn(LOCAL_URL)
        local_cur = local_conn.cursor()
        
        # 3. Definir query de extracción local y limpiar remota en caso de overlap
        if is_full_sync:
            print("    - Carga de inicializacion (Tabla vacia en remoto)...")
            extract_query = f'SELECT * FROM "{table_name}"'
        else:
            if key_type == "integer":
                print(f"    - Carga delta por ID (Ultimo ID remoto: {remote_max:,})")
                extract_query = f'SELECT * FROM "{table_name}" WHERE "{key_col}" > {remote_max}'
            else: # timestamp
                safety_hours = config.get("safety_hours", 3)
                start_time = remote_max - timedelta(hours=safety_hours)
                print(f"    - Carga delta por fecha (Ultima: {remote_max} | Inicio con overlap: {start_time})")
                
                # Borrar registros en el remoto para evitar duplicados por el overlap de seguridad
                print("    - Removiendo overlap de seguridad en servidor remoto...", end='', flush=True)
                with get_conn(REMOTE_URL) as remote_conn:
                    remote_conn.autocommit = True
                    with remote_conn.cursor() as remote_cur:
                        remote_cur.execute(f'DELETE FROM "{table_name}" WHERE "{key_col}" >= %s', (start_time,))
                print(" [OK]")
                
                extract_query = local_cur.mogrify(f'SELECT * FROM "{table_name}" WHERE "{key_col}" >= %s', (start_time,)).decode('utf-8')

        # 4. Exportar localmente usando COPY optimizado
        print("    - Exportando delta local a archivo temporal...", end='', flush=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tsv') as tmp:
            tmp_path = tmp.name
            copy_query = f'COPY ({extract_query}) TO STDOUT WITH (FORMAT TEXT, NULL \'NULL\')'
            local_cur.copy_expert(copy_query, tmp)
        print(" [OK]")
        
        # Verificar tamaño
        file_size = os.path.getsize(tmp_path)
        if file_size == 0:
            print("    - [INFO] Sin registros nuevos para sincronizar.")
            local_conn.close()
            return True
            
        print(f"    - Delta exportada con exito ({file_size/(1024*1024):.2f} MB)")

        # 5. Subir e importar a remoto
        print(f"    - Subiendo delta al servidor remoto...", end='', flush=True)
        with open(tmp_path, 'rb') as f:
            with get_conn(REMOTE_URL) as remote_conn:
                remote_conn.autocommit = True
                with remote_conn.cursor() as remote_cur:
                    remote_cur.copy_from(f, table_name, sep='\t', null='NULL')
        print(" [OK]")
        print(f"    - [OK] Tabla {table_name} sincronizada exitosamente en {time.time()-start_t:.2f}s.")
        local_conn.close()
        return True

    except Exception as e:
        print(f" [ERROR] Fallo en la sincronizacion de {table_name}: {e}")
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

def main():
    print("====================================================")
    print("SINCRO DIARIA DE TABLAS SADE (LOCAL -> PUBLIC)")
    print("====================================================")
    start_total = time.time()
    
    # 1. Limpiar sesiones bloqueantes
    kill_remote_sessions()
    
    # 2. Sincronizar de forma quirúrgica e incremental cada una de las 6 tablas masivas
    for table_name, config in SADE_TABLES_CONFIG.items():
        sync_table_incremental(table_name, config)
        
    print(f"\n====================================================")
    print(f"PROCESO DE SINCRO DIARIA FINALIZADO EN {time.time()-start_total:.2f}s")
    print("====================================================")

if __name__ == "__main__":
    main()
