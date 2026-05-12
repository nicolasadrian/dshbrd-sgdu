import psycopg2
import os
import re
import time
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- CONFIGURACIÓN ---
# Se utilizan las mismas credenciales que en sync_public.py
LOCAL_URL = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')
REMOTE_URL = os.getenv('DATABASE_URL_PUBLIC', 'postgresql://postgres:frQB7%7D0%26p~.C_.X%40Ymu(1tAO7@34.136.69.128:5432/sade_db')
QUERIES_DIR = 'queries'

# Orden de prioridad para evitar errores de dependencia
PRIORITY = [
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
    "mvw_reporte_historico_global.sql",  # Esta debe ir después de las áreas
    "create_historical_view.sql"       # Se mueve al final por ser muy pesada y posible causa de desconexión
]

def get_conn(url):
    return psycopg2.connect(url)

def kill_remote_sessions():
    """Limpia sesiones en el servidor remoto para evitar bloqueos al dropear vistas."""
    print(">>> Limpiando bloqueos en el servidor remoto...", flush=True)
    try:
        base_url = REMOTE_URL.rsplit('/', 1)[0]
        with get_conn(f"{base_url}/postgres") as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'prefapp' AND pid <> pg_backend_pid();")
        print("    [OK] Sesiones limpiadas.")
    except Exception as e:
        print(f"    [!] Aviso: {e}")

def deploy_view(file_path):
    filename = os.path.basename(file_path)
    print(f"    - Ejecutando {filename}...", end='', flush=True)
    
    conn = None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            print(" [VACÍO]")
            return

        # Extraer el nombre del objeto para el Smart Drop
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

        # Abrir conexión dedicada para este archivo
        conn = get_conn(REMOTE_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            # Configuración de sesión para queries pesadas
            cur.execute("SET statement_timeout = 0;") 
            cur.execute("SET work_mem = '128MB';")
            cur.execute("SET maintenance_work_mem = '256MB';")
            cur.execute(content)
        print(" [OK]")
    except Exception as e:
        error_msg = str(e).split('\n')[0]
        print(f" [ERROR] {error_msg[:150]}")
        time.sleep(2) # Pausa para que el servidor respire tras un fallo de conexión
    finally:
        if conn:
            conn.close()

def main():
    print("====================================================")
    print("ACTUALIZADOR DE VISTAS (LOCAL -> PUBLIC)")
    print("====================================================")
    start_t = time.time()

    if not os.path.exists(QUERIES_DIR):
        print(f"Error: No se encontró el directorio '{QUERIES_DIR}'")
        return

    # 1. Limpiar sesiones remotas
    # kill_remote_sessions()

    # 2. Desplegar vistas
    print(f"\n>>> Desplegando vistas desde '{QUERIES_DIR}'...")
    
    # Filtrar archivos .sql
    available = [f for f in os.listdir(QUERIES_DIR) if f.endswith('.sql')]
    
    # Determinar orden: Primero los de prioridad, luego el resto
    to_run = [f for f in PRIORITY if f in available]
    to_run += [f for f in available if f not in PRIORITY]
    
    for sql_file in to_run:
        path = os.path.join(QUERIES_DIR, sql_file)
        deploy_view(path)
                    
    print(f"\n====================================================")
    print(f"PROCESO FINALIZADO EN {time.time()-start_t:.2f}s")
    print("====================================================")

if __name__ == "__main__":
    main()
