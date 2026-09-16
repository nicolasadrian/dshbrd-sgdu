import os
import sys
import argparse
import time
import pandas as pd
from sqlalchemy import create_engine, text

# Add backend directory to path to allow importing local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import engine as local_engine

ACRONIMOS = [
    "IFOCD", "IFPDO", "PROIN", "PLINE", "IFSMC", "IFROC", "IFSMI", "IFDEX", 
    "CECNU", "IFGPA", "FIPAR", "IFPCB", "IFPCO", "IFTPT", "IFPEO", "IFCIS", "IFRSP",
    "IFCAO", "IFCFP", "IFCAC", "IFMAD", "IFMHC", "IFMMH", "IFMOT", "IFMSC",
    "APH", "MORFOLOGIA", "USOS"
]

DEFAULT_PROD_URL = os.getenv("DATABASE_URL_PUBLIC", "postgresql://postgres:frQB7%7D0%26p~.C_.X%40Ymu(1tAO7@34.136.69.128:5432/sade_db")

import io
import csv

def psql_insert_copy(table, conn, keys, data_iter):
    """
    Inserción ultrarrápida usando PostgreSQL COPY.
    """
    dbapi_conn = conn.connection
    with dbapi_conn.cursor() as cur:
        s_buf = io.StringIO()
        writer = csv.writer(s_buf)
        writer.writerows(data_iter)
        s_buf.seek(0)

        columns = ', '.join([f'"{k}"' for k in keys])
        if table.schema:
            table_name = f'"{table.schema}"."{table.name}"'
        else:
            table_name = f'"{table.name}"'

        sql = f'COPY {table_name} ({columns}) FROM STDIN WITH CSV'
        cur.copy_expert(sql=sql, file=s_buf)

def get_prod_engine(prod_db_url):
    if not prod_db_url:
        prod_db_url = os.getenv("DATABASE_URL_PROD") or DEFAULT_PROD_URL
        
    if not prod_db_url:
        print("[-] Error: No se especificó la URL de la base de datos de producción.")
        sys.exit(1)
        
    if prod_db_url.startswith("postgres://"):
        prod_db_url = prod_db_url.replace("postgres://", "postgresql://", 1)
        
    print(f"[*] Conectando a la base de datos de producción: {prod_db_url.split('@')[-1]}")
    return create_engine(
        prod_db_url,
        pool_pre_ping=True,
        connect_args={"options": "-c statement_timeout=600000"}  # 10 minutos de timeout
    )

def copy_table(table_name, prod_engine):
    print(f"\n[*] Procesando tabla: {table_name}...")
    start_time = time.time()
    
    # 1. Leer datos de la base local
    try:
        with local_engine.connect() as lconn:
            local_exists = lconn.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = '{table_name}'
                );
            """)).scalar()
            
        if not local_exists:
            print(f"    [!] La tabla {table_name} no existe en la base local. Saltando.")
            return True
            
        df = pd.read_sql_query(f"SELECT * FROM public.{table_name}", local_engine)
        print(f"    - Leídos {len(df)} registros de la base local.")
    except Exception as e:
        print(f"    [-] Error al leer la tabla local {table_name}: {e}")
        return False
        
    if len(df) == 0:
        print(f"    [!] La tabla {table_name} está vacía. Saltando copia.")
        return True

    # 2. Subir datos a la base de producción
    try:
        with prod_engine.connect() as conn:
            table_exists = conn.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = '{table_name}'
                );
            """)).scalar()
            
            if table_exists:
                # Comprobar si hay columnas nuevas en el dataframe que falten en prod
                existing_cols = [r[0] for r in conn.execute(text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = '{table_name}'
                """)).fetchall()]
                
                for col in df.columns:
                    if col not in existing_cols:
                        print(f"    - Agregando columna faltante '{col}' en {table_name}...")
                        conn.execute(text(f'ALTER TABLE public.{table_name} ADD COLUMN "{col}" TEXT'))
                
                print(f"    - Vaciando tabla existente en producción (TRUNCATE)...")
                conn.execute(text(f"TRUNCATE TABLE public.{table_name}"))
                conn.commit()
                
                # Insertar los datos manteniendo la tabla y sus dependencias (vistas)
                df.to_sql(
                    name=table_name,
                    con=prod_engine,
                    schema='public',
                    if_exists='append',
                    index=False,
                    method=psql_insert_copy,
                    chunksize=10000
                )
            else:
                print(f"    - Creando tabla en producción...")
                # Crear solo la estructura
                df.head(0).to_sql(
                    name=table_name,
                    con=prod_engine,
                    schema='public',
                    if_exists='replace',
                    index=False
                )
                # Insertar con COPY
                df.to_sql(
                    name=table_name,
                    con=prod_engine,
                    schema='public',
                    if_exists='append',
                    index=False,
                    method=psql_insert_copy,
                    chunksize=10000
                )
        print(f"    - Subida a producción completada con éxito.")
    except Exception as e:
        print(f"    [-] Error al escribir la tabla {table_name} en producción: {e}")
        return False

    # 3. Recrear índices clave en la tabla de producción
    try:
        with prod_engine.connect() as conn:
            # Crear índice en id_expediente si la columna existe en el dataframe
            if 'id_expediente' in df.columns:
                print(f"    - Creando índice en id_expediente para {table_name}...")
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_id_exp ON public.{table_name} (id_expediente)"))
                
            if 'smp' in df.columns:
                print(f"    - Creando índice en smp para {table_name}...")
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_smp ON public.{table_name} (smp)"))
                
            conn.commit()
            print(f"    - Índices creados correctamente.")
    except Exception as e:
        print(f"    [-] Advertencia al crear índices en {table_name}: {e}")

    elapsed = time.time() - start_time
    print(f"    [+] Completado en {elapsed:.2f} segundos.")
    return True

def main():
    parser = argparse.ArgumentParser(description="Script para subir las tablas gedo_xxxx_datos a PostgreSQL productivo.")
    parser.add_argument("--prod-db", help="URL de conexión de la base de datos de producción (postgresql://...)")
    parser.add_argument("--tables", help="Lista separada por comas de acrónimos específicos a subir (ej. IFOCD,IFPDO)")
    
    args = parser.parse_args()
    
    prod_engine = get_prod_engine(args.prod_db)
    
    # Filtrar acrónimos a procesar
    target_acronyms = ACRONIMOS
    if args.tables:
        target_acronyms = [a.strip().upper() for a in args.tables.split(",") if a.strip()]

    print(f"[*] Se procesarán las tablas de acrónimos: {', '.join(target_acronyms)}")
    
    successful = 0
    failed = 0
    
    for acr in target_acronyms:
        table_name = f"gedo_{acr.lower()}_datos"
        success = copy_table(table_name, prod_engine)
        if success:
            successful += 1
        else:
            failed += 1
            
    print("\n==========================================")
    print(f"[*] Resumen del proceso:")
    print(f"    - Tablas copiadas con éxito: {successful}")
    print(f"    - Tablas fallidas: {failed}")
    print("==========================================")

if __name__ == "__main__":
    main()
