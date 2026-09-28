import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

pdi_url = os.getenv('PDI_DATABASE_URL')
prod_url = ((os.getenv('DATABASE_URL_PUBLIC') or os.getenv('DATABASE_URL')).replace('postgres://', 'postgresql://')).rsplit('/', 1)[0] + '/geo-mdr'

print("1. Leyendo cur_manzanasatipicas desde PDI...")
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
print(f"Total filas leídas de PDI: {len(rows)}")

print("\n2. Conectando a Producción geo-mdr...")
d_conn = psycopg2.connect(prod_url)
d_cur = d_conn.cursor()

# Habilitar postgis
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

cols_quoted = [f'"{c}"' for c in cols]
placeholders = [f"%s" for _ in cols]
insert_sql = f"INSERT INTO public.cur_manzanasatipicas ({', '.join(cols_quoted)}) VALUES ({', '.join(placeholders)})"

print("3. Insertando registros en Producción...")
batch_size = 1000
for i in range(0, len(rows), batch_size):
    batch = rows[i:i + batch_size]
    d_cur.executemany(insert_sql, batch)
    print(f"Progreso: {min(i + batch_size, len(rows))} / {len(rows)}...")

# Commit explícito de la transacción
d_conn.commit()

print("4. Creando índices...")
try:
    d_cur.execute("CREATE INDEX IF NOT EXISTS idx_cur_manzanasatipicas_sm ON public.cur_manzanasatipicas (sm);")
    d_cur.execute("CREATE INDEX IF NOT EXISTS idx_cur_manzanasatipicas_sec_man ON public.cur_manzanasatipicas (seccion, manzana);")
    d_conn.commit()
except Exception as e:
    print(f"Nota índices: {e}")

d_conn.close()
print("\n¡cur_manzanasatipicas completada con éxito en Producción!")
