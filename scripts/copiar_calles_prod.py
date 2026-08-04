import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DEFAULT_PROD_URL = "postgresql://postgres:frQB7%7D0%26p~.C_.X%40Ymu(1tAO7@34.136.69.128:5432/sade_db"
DEFAULT_LOCAL_URL = "postgresql://postgres:lenovo@localhost:5432/sade_db"

local_base = os.getenv("DATABASE_URL_LOCAL") or DEFAULT_LOCAL_URL
prod_base = os.getenv("DATABASE_URL_PUBLIC") or os.getenv("DATABASE_URL") or DEFAULT_PROD_URL

if local_base.startswith("postgres://"): local_base = local_base.replace("postgres://", "postgresql://", 1)
if prod_base.startswith("postgres://"): prod_base = prod_base.replace("postgres://", "postgresql://", 1)

local_url = local_base.rsplit('/', 1)[0] + "/geo-mdr"
prod_url = prod_base.rsplit('/', 1)[0] + "/geo-mdr"

print(f"\n-> Conectando ETL a Origen (Local): {local_url.split('@')[-1]}")
print(f"-> Conectando ETL a Destino (Producción): {prod_url.split('@')[-1]}")

connect_args = {
    "connect_timeout": 15,
    "keepalives": 1,
    "keepalives_idle": 10,
    "keepalives_interval": 5,
    "keepalives_count": 3
}

try:
    engine_local = create_engine(local_url, connect_args=connect_args)
    engine_prod = create_engine(prod_url, connect_args=connect_args)

    print("\n1. Obteniendo estructura completa de la tabla 'public.calles' desde Local...")
    with engine_local.connect() as conn:
        cols_info = conn.execute(text("""
            SELECT column_name, data_type, udt_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'calles'
            ORDER BY ordinal_position
        """)).fetchall()

    print(f"   -> Columnas detectadas ({len(cols_info)}): {[c[0] for c in cols_info]}")

    print("\n2. Leyendo todos los campos de 'public.calles' con ST_AsText(geom)...")
    query = """
        SELECT gid, alt_if, alt_ii, alt_di, alt_df, id, tipo_c, nomoficial, corregido, ST_AsText(geom) AS wkt_geom 
        FROM public.calles
    """
    df = pd.read_sql_query(query, con=engine_local)
    print(f"   -> {len(df)} registros leídos de la base local.")

    if df.empty:
        print("La tabla local está vacía. Abortando.")
        sys.exit(0)

    print("\n3. Recreando la tabla 'public.calles' completa en Producción con PostGIS...")
    with engine_prod.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.execute(text("DROP TABLE IF EXISTS public.calles CASCADE;"))
        conn.execute(text("""
            CREATE TABLE public.calles (
                gid BIGINT PRIMARY KEY,
                alt_if NUMERIC,
                alt_ii NUMERIC,
                alt_di NUMERIC,
                alt_df NUMERIC,
                id NUMERIC,
                tipo_c VARCHAR(255),
                nomoficial VARCHAR(255),
                corregido BIGINT,
                geom geometry(MultiLineString, 22186)
            );
        """))

    print("\n4. Insertando todos los campos masivamente con psycopg2 execute_values...")
    raw_conn = engine_prod.raw_connection()
    try:
        cur = raw_conn.cursor()
        
        insert_query = """
            INSERT INTO public.calles (gid, alt_if, alt_ii, alt_di, alt_df, id, tipo_c, nomoficial, corregido, geom) 
            VALUES %s;
        """
        
        # Convertir NaN/NAT a None explícito y tipos nativos
        data_tuples = []
        for _, r in df.iterrows():
            wkt_val = f"SRID=22186;{r['wkt_geom']}" if pd.notnull(r['wkt_geom']) else None
            data_tuples.append((
                int(r['gid']) if pd.notnull(r['gid']) else None,
                float(r['alt_if']) if pd.notnull(r['alt_if']) else None,
                float(r['alt_ii']) if pd.notnull(r['alt_ii']) else None,
                float(r['alt_di']) if pd.notnull(r['alt_di']) else None,
                float(r['alt_df']) if pd.notnull(r['alt_df']) else None,
                float(r['id']) if pd.notnull(r['id']) else None,
                str(r['tipo_c']) if pd.notnull(r['tipo_c']) else None,
                str(r['nomoficial']) if pd.notnull(r['nomoficial']) else None,
                int(r['corregido']) if pd.notnull(r['corregido']) else None,
                wkt_val
            ))
        
        template = "(%s::bigint, %s::numeric, %s::numeric, %s::numeric, %s::numeric, %s::numeric, %s::varchar, %s::varchar, %s::bigint, ST_Multi(ST_GeomFromEWKT(%s)))"
        
        page_size = 2000
        total = len(data_tuples)
        
        for idx in range(0, total, page_size):
            batch = data_tuples[idx:idx + page_size]
            execute_values(cur, insert_query, batch, template=template, page_size=len(batch))
            raw_conn.commit()
            print(f"   -> Sincronizados {min(idx + page_size, total)}/{total} registros...")
            
        cur.close()
    finally:
        raw_conn.close()

    print("\n5. Creando índice espacial GIST en Producción...")
    with engine_prod.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_calles_geom ON public.calles USING GIST (geom);"))

    print("\n==========================================")
    print("¡PROCESO ETL COMPLETADO CON ÉXITO!")
    print(f"Se migró la tabla 'public.calles' completa con sus 10 columnas y {len(df)} filas a producción.")
    print("==========================================\n")

except Exception as e:
    print(f"\nError en proceso ETL: {e}\n")
