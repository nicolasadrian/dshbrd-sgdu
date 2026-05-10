import oracledb
import psycopg2
from psycopg2 import sql
import pandas as pd
from sqlalchemy import create_engine, text
import time
import sys
import io
import csv

# --- CONFIGURACIÓN ---
ORACLE_CONFIG = {
    "user": "CDASILVACOSTA",
    "pass": "SUI_sie329(m",
    "dsn": "ind01-scan1.gcba.gob.ar:1521/sadetst.gcba.gob.ar"
}

POSTGRES_CONFIG = {
    "host": "localhost",
    "user": "postgres",
    "pass": "lenovo",
    "port": 5432,
    "dbname": "sade_db"
}

TABLES = [
    {"schema": "EE_SADE", "name": "MVW_EXPEDIENTES_TRATAS_SECGDU", "filter": None},
    {"schema": "EE_SADE", "name": "MVW_DATOS_GEDO_SECGDU", "filter": None},
    {"schema": "EE_SADE", "name": "MVW_EE_PASES_SECGDU", "filter": None},
    {"schema": "EE_SADE", "name": "MVW_EE_GEDO_SECGDU", "filter": None},
    {"schema": "GEDO_SADE", "name": "DF_FORM_COMP_VALUE", "filter": "ROWNUM <= 500000"}
]

def psql_insert_copy(table, conn, keys, data_iter):
    """Método de alta velocidad usando COPY FROM para PostgreSQL."""
    dbapi_conn = conn.connection
    with dbapi_conn.cursor() as cur:
        s_buf = io.StringIO()
        writer = csv.writer(s_buf)
        writer.writerows(data_iter)
        s_buf.seek(0)
        columns = ', '.join([f'"{k}"' for k in keys])
        table_name = f'"{table.name}"'
        sql_query = f'COPY {table_name} ({columns}) FROM STDIN WITH CSV'
        cur.copy_expert(sql=sql_query, file=s_buf)

def create_db_if_not_exists():
    try:
        conn = psycopg2.connect(host=POSTGRES_CONFIG["host"], user=POSTGRES_CONFIG["user"], password=POSTGRES_CONFIG["pass"], dbname="postgres")
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (POSTGRES_CONFIG["dbname"],))
            if not cur.fetchone():
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(POSTGRES_CONFIG["dbname"])))
                print(f"Base de datos {POSTGRES_CONFIG['dbname']} creada.")
        conn.close()
    except Exception as e:
        print(f"Error en Postgres: {e}")
        sys.exit(1)

def create_indexes(engine):
    """Crea índices para optimizar las consultas del tablero."""
    indexes = [
        ("idx_pases_id_exp", "mvw_ee_pases_secgdu", "id_expediente"),
        ("idx_pases_fecha", "mvw_ee_pases_secgdu", "fecha"),
        ("idx_pases_dest", "mvw_ee_pases_secgdu", "destinatario"),
        ("idx_exp_trata_id_exp", "mvw_expedientes_tratas_secgdu", "id_expediente"),
        ("idx_exp_trata_trata", "mvw_expedientes_tratas_secgdu", "trata"),
        ("idx_gedo_id_exp", "mvw_datos_gedo_secgdu", "id_expediente"),
        ("idx_gedo_acro", "mvw_datos_gedo_secgdu", "acronimo")
    ]
    
    print("\n[3/3] Optimizando base de datos (Creando índices)...", flush=True)
    with engine.connect() as conn:
        for idx_name, table, column in indexes:
            start_t = time.time()
            print(f"  > Índice {idx_name}...", end='', flush=True)
            try:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({column})"))
                conn.commit()
                print(f" [OK] ({round(time.time() - start_t, 2)}s)", flush=True)
            except Exception as e:
                print(f" [ERROR] {e}", flush=True)

def run_etl():
    create_db_if_not_exists()
    pg_uri = f"postgresql://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['pass']}@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['dbname']}"
    pg_engine = create_engine(pg_uri)
    
    # Motor Oracle (Configurado para Service Name)
    host_port = ORACLE_CONFIG['dsn'].split('/')[0]
    service_name = ORACLE_CONFIG['dsn'].split('/')[1]
    ora_uri = f"oracle+oracledb://{ORACLE_CONFIG['user']}:{ORACLE_CONFIG['pass']}@{host_port}/?service_name={service_name}"
    ora_engine = create_engine(ora_uri)
    
    print("\n[1/2] Calculando volumen de datos en Oracle...", flush=True)
    total_counts = {}
    with ora_engine.connect() as ora_conn:
        for t in TABLES:
            print(f"  > Contando {t['name']}...", end='', flush=True)
            q = f"SELECT count(*) FROM {t['schema']}.{t['name']}"
            if t['filter']: q += f" WHERE {t['filter']}"
            try:
                res = ora_conn.execute(text(q)).fetchone()
                total_counts[t['name']] = res[0]
                print(f"\r  - {t['name']}: {res[0]:,} registros", flush=True)
            except Exception as e:
                print(f"\r  [!] No se pudo contar {t['name']}: {e}", flush=True)
                total_counts[t['name']] = 0

    print("\n[2/2] Iniciando copia masiva (Método COPY ultra-rápido)...", flush=True)
    for t in TABLES:
        start_t = time.time()
        print(f"\n>>> Procesando {t['name']} ({total_counts[t['name']]:,} filas)", flush=True)
        query = f"SELECT * FROM {t['schema']}.{t['name']}"
        if t['filter']: query += f" WHERE {t['filter']}"
            
        try:
            total_rows = 0
            first_batch = True
            with ora_engine.connect() as ora_conn:
                # Chunk de 50k para actualizaciones más frecuentes
                for chunk in pd.read_sql(text(query), ora_conn, chunksize=50000):
                    chunk.columns = [c.lower() for c in chunk.columns]
                    if first_batch:
                        table_name = t['name'].lower()
                        # Usamos TRUNCATE para no romper vistas materializadas dependientes
                        with pg_engine.connect() as pg_conn:
                            try:
                                pg_conn.execute(text(f"TRUNCATE TABLE {table_name}"))
                                pg_conn.commit()
                            except Exception:
                                # Si la tabla no existe, la creamos
                                chunk.head(0).to_sql(table_name, pg_engine, if_exists='replace', index=False)
                        first_batch = False
                    
                    # Carga ultra-rápida usando COPY nativo
                    chunk.to_sql(t['name'].lower(), pg_engine, if_exists='append', index=False, method=psql_insert_copy)
                    total_rows += len(chunk)
                    
                    # Calcular progreso y mostrar porcentaje
                    if total_counts[t['name']] > 0:
                        pct = (total_rows / total_counts[t['name']]) * 100
                        # Barra de progreso visual simple
                        bar_len = 20
                        filled_len = int(bar_len * total_rows // total_counts[t['name']])
                        bar = '=' * filled_len + '-' * (bar_len - filled_len)
                        print(f"    [{bar}] {total_rows:,} / {total_counts[t['name']]:,} ({pct:.1f}%) cargado", end='\r', flush=True)
                    else:
                        print(f"    ... {total_rows:,} cargados", end='\r', flush=True)

            print(f"\n  [✓] {t['name']} migrada en {round(time.time() - start_t, 2)}s", flush=True)
        except Exception as e:
            print(f"\n  [!] Error en {t['name']}: {e}")

    print("\n==========================================")
    print("MIGRACIÓN DE DATOS FINALIZADA")
    print("==========================================")
    
    # Nuevo paso: Indexación
    create_indexes(pg_engine)
    
    print("\n==========================================")
    print("ETL FINALIZADO CON ÉXITO")
    print("==========================================")

if __name__ == "__main__":
    run_etl()
