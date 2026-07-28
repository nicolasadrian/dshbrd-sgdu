import os
import sys
import pandas as pd
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

print(f"\n-> Conectando a Origen (Local): {local_url.split('@')[-1]}")
print(f"-> Conectando a Destino (Producción): {prod_url.split('@')[-1]}")

try:
    engine_local = create_engine(local_url)
    engine_prod = create_engine(prod_url)

    print("\n1. Leyendo tabla 'public.calles' desde Local...")
    query = "SELECT nomoficial, ST_AsText(geom) AS wkt_geom FROM public.calles WHERE geom IS NOT NULL"
    df = pd.read_sql_query(query, con=engine_local)
    print(f"   -> {len(df)} registros leídos de local.")

    if df.empty:
        print("La tabla local está vacía. Abortando.")
        sys.exit(0)

    print("\n2. Recreando tabla 'public.calles' en Producción...")
    with engine_prod.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.execute(text("DROP TABLE IF EXISTS public.calles CASCADE;"))
        conn.execute(text("""
            CREATE TABLE public.calles (
                id SERIAL PRIMARY KEY,
                nomoficial VARCHAR(255),
                geom geometry(MultiLineString, 22186)
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_calles_geom ON public.calles USING GIST (geom);"))

    print("\n3. Insertando registros en Producción (por lotes)...")
    insert_sql = text("""
        INSERT INTO public.calles (nomoficial, geom) 
        VALUES (:nomoficial, ST_Multi(ST_SetSRID(ST_GeomFromText(:wkt_geom), 22186)));
    """)

    records = df.to_dict(orient="records")
    batch_size = 5000
    total = len(records)
    
    for i in range(0, total, batch_size):
        batch = records[i:i+batch_size]
        with engine_prod.begin() as conn:
            conn.execute(insert_sql, batch)
        print(f"   -> Sincronizados {min(i+batch_size, total)}/{total} registros...")

    print("\n==========================================")
    print("¡MIGRACIÓN COMPLETADA CON ÉXITO! La tabla 'public.calles' fue copiada idénticamente a producción.")
    print("==========================================\n")

except Exception as e:
    print(f"\nError durante la migración: {e}\n")
