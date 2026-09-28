import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

pdi_url = os.getenv('PDI_DATABASE_URL')
prod_url = ((os.getenv('DATABASE_URL_PUBLIC') or os.getenv('DATABASE_URL')).replace('postgres://', 'postgresql://')).rsplit('/', 1)[0] + '/geo-mdr'

print("1. Extrayendo cur_manzanasatipicas de PDI...")
p_conn = psycopg2.connect(pdi_url)
p_cur = p_conn.cursor()
p_cur.execute("""
    SELECT column_name, data_type, udt_name 
    FROM information_schema.columns 
    WHERE table_name = 'cur_manzanasatipicas' 
    ORDER BY ordinal_position
""")
cols_meta = p_cur.fetchall()
cols = [c[0] for c in cols_meta]

p_cur.execute(f"SELECT {', '.join(['\"' + c + '\"' for c in cols])} FROM public.cur_manzanasatipicas")
rows = p_cur.fetchall()
p_conn.close()
print(f"Total filas leídas: {len(rows)}")

print("\n2. Preparando tabla en Producción geo-mdr...")
d_conn = psycopg2.connect(prod_url)
d_conn.autocommit = True
d_cur = d_conn.cursor()

try:
    d_cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
except Exception:
    pass

col_defs = []
for col_name, data_type, udt_name in cols_meta:
    if udt_name == 'geometry':
        type_str = "geometry"
    elif data_type == 'character varying':
        type_str = "character varying"
    elif data_type == 'character':
        type_str = "character"
    elif data_type == 'USER-DEFINED':
        type_str = udt_name
    else:
        type_str = data_type
    col_defs.append(f'"{col_name}" {type_str}')

d_cur.execute(f"CREATE TABLE IF NOT EXISTS public.cur_manzanasatipicas ({', '.join(col_defs)});")
d_cur.execute("TRUNCATE TABLE public.cur_manzanasatipicas;")

cols_str = ', '.join([f'"{c}"' for c in cols])
insert_query = f"INSERT INTO public.cur_manzanasatipicas ({cols_str}) VALUES %s"

print("\n3. Insertando en streaming rápido vía execute_values...")
batch_size = 2000
for i in range(0, len(rows), batch_size):
    batch = rows[i:i + batch_size]
    execute_values(d_cur, insert_query, batch, page_size=2000)
    print(f"Insertadas {min(i + batch_size, len(rows))} / {len(rows)} filas...")

print("\n4. Creando índices...")
d_cur.execute("CREATE INDEX IF NOT EXISTS idx_cur_manzanasatipicas_sm ON public.cur_manzanasatipicas (sm);")
d_cur.execute("CREATE INDEX IF NOT EXISTS idx_cur_manzanasatipicas_sec_man ON public.cur_manzanasatipicas (seccion, manzana);")
d_cur.execute("CREATE INDEX IF NOT EXISTS idx_cur_manzanasatipicas_tipo ON public.cur_manzanasatipicas (mz_tipo);")

# Verificación inmediata
d_cur.execute("SELECT COUNT(*), COUNT(CASE WHEN UPPER(TRIM(mz_tipo))='ATIPICA' THEN 1 END) FROM public.cur_manzanasatipicas")
res = d_cur.fetchone()
print(f"\n¡Verificación final en PROD! Total: {res[0]} | Atípicas: {res[1]}")

d_conn.close()
