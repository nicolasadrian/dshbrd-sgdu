import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

local_url = os.getenv("DATABASE_URL_LOCAL") or "postgresql://postgres:lenovo@localhost:5432/geo-mdr"
if not local_url.endswith("/geo-mdr"):
    base_local, _ = local_url.rsplit('/', 1)
    local_url = f"{base_local}/geo-mdr"

if local_url.startswith("postgres://"): local_url = local_url.replace("postgres://", "postgresql://", 1)

print(f"-> Leyendo tabla 'public.calles' desde Local ({local_url.split('@')[-1]})...")
engine_local = create_engine(local_url)

query = "SELECT nomoficial, ST_AsText(geom) AS wkt_geom FROM public.calles WHERE geom IS NOT NULL AND nomoficial IS NOT NULL AND TRIM(nomoficial) <> ''"
df = pd.read_sql_query(query, con=engine_local)

print(f"-> {len(df)} registros leídos. Generando archivo SQL dump 'scripts/calles_dump.sql'...")

sql_lines = [
    "CREATE EXTENSION IF NOT EXISTS postgis;",
    "DROP TABLE IF EXISTS public.calles CASCADE;",
    "CREATE TABLE public.calles (id SERIAL PRIMARY KEY, nomoficial VARCHAR(255), geom geometry(MultiLineString, 22186));",
    "BEGIN;"
]

for idx, row in df.iterrows():
    nom = str(row['nomoficial']).replace("'", "''")
    wkt = row['wkt_geom']
    sql_lines.append(f"INSERT INTO public.calles (nomoficial, geom) VALUES ('{nom}', ST_Multi(ST_SetSRID(ST_GeomFromText('{wkt}'), 22186)));")

sql_lines.append("COMMIT;")
sql_lines.append("CREATE INDEX IF NOT EXISTS idx_calles_geom ON public.calles USING GIST (geom);")

output_path = os.path.join(os.path.dirname(__file__), "calles_dump.sql")
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(sql_lines))

print(f"¡ÉXITO! Se generó el archivo '{output_path}' ({os.path.getsize(output_path) / (1024*1024):.2f} MB).")
