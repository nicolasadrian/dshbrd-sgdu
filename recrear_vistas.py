import psycopg2
import time
import os
import re
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de conexión (Base Pública)
REMOTE_URL = os.getenv('DATABASE_URL_PUBLIC', 'postgresql://postgres:frQB7%7D0%26p~.C_.X%40Ymu(1tAO7@34.136.69.128:5432/sade_db')

# Orden de ejecución (Prioridad de dependencias)
QUERIES_ORDER = [
    "setup_auth_table.sql",
    "setup_unified_analytics.sql",      # Crea cfg_gestion_metas
    "v_expedientes_lifecycle.sql",      # Vista lógica central
    "populate_cfg_metas.sql",           # Puebla la configuración
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
    "mvw_reporte_historico_global.sql"
]

def kill_remote_sessions():
    """Mata procesos colgados en la base de datos remota para evitar bloqueos."""
    print(">>> Limpiando procesos colgados en el servidor remoto...", end="", flush=True)
    try:
        # Conectar a la db 'postgres' para poder matar sesiones de la db principal
        base_url = REMOTE_URL.rsplit('/', 1)[0]
        db_name = REMOTE_URL.rsplit('/', 1)[1]
        
        with psycopg2.connect(f"{base_url}/postgres") as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                # Matar todas las sesiones excepto la nuestra
                cur.execute(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}' AND pid <> pg_backend_pid();")
        print(" ✅ [LIMPIO]")
    except Exception as e:
        print(f" ⚠️  [AVISO] No se pudieron limpiar sesiones: {e}")

def print_notices(conn):
    """Imprime los avisos (RAISE NOTICE) generados por PostgreSQL."""
    for notice in conn.notices:
        print(f"      > {notice.strip()}")
    conn.notices = []

def format_duration(seconds):
    """Convierte segundos en formato Xm Ys."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"

def recrear_vistas():
    print("\n" + "="*70)
    print("🚀 RECONSTRUCCIÓN DE CAPA ANALÍTICA - LOG DETALLADO")
    print("="*70 + "\n")
    
    start_total = time.time()
    kill_remote_sessions()
    
    try:
        conn = psycopg2.connect(
            REMOTE_URL,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Optimizaciones de sesión
        cur.execute("SET statement_timeout = 0;") 
        cur.execute("SET work_mem = '256MB';")    
        
        for sql_file in QUERIES_ORDER:
            path = os.path.join("queries", sql_file)
            
            if not os.path.exists(path):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  [SALTADO] No existe: {sql_file}")
                continue
                
            now = datetime.now().strftime('%H:%M:%S')
            print(f"[{now}] 📄 Procesando: {sql_file}")
            start_q = time.time()
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extraer nombre del objeto para el Smart Drop
                match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:MATERIALIZED\s+)?VIEW\s+(\w+)', content, re.IGNORECASE)
                if match:
                    obj_name = match.group(1)
                    print(f"    - Paso 1/2: Limpieza previa de '{obj_name}'...", end="", flush=True)
                    smart_drop = f"""
                    DO $$ BEGIN
                        IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND relname = '{obj_name}' AND relkind = 'm') THEN 
                            RAISE NOTICE 'Borrando vista materializada %', '{obj_name}';
                            DROP MATERIALIZED VIEW "{obj_name}" CASCADE;
                        ELSIF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND relname = '{obj_name}' AND relkind = 'v') THEN 
                            RAISE NOTICE 'Borrando vista lógica %', '{obj_name}';
                            DROP VIEW "{obj_name}" CASCADE;
                        END IF;
                    END $$;
                    """
                    cur.execute(smart_drop)
                    print_notices(conn)
                    print(" ✅")
                    
                    print(f"    - Paso 2/2: Creando '{obj_name}' (esto puede tardar)...", end="", flush=True)
                else:
                    print(f"    - Ejecutando script general...", end="", flush=True)
                
                # Ejecutar SQL
                cur.execute(content)
                print_notices(conn)
                
                duration = time.time() - start_q
                print(f" ✅ ({format_duration(duration)})")
                
            except Exception as e:
                print(f" ❌ ERROR: {str(e).splitlines()[0][:120]}")
                
        cur.close()
        conn.close()
        
        total_duration = time.time() - start_total
        print(f"\n✨ FINALIZADO EN {format_duration(total_duration)}\n")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n🛑 ERROR DE CONEXIÓN: {e}")

if __name__ == "__main__":
    recrear_vistas()
