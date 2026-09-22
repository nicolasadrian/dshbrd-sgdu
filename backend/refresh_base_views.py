import psycopg2
import os
import time
from dotenv import load_dotenv

load_dotenv()
local_url = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')

print("Refrescando vistas base en Local...")
l_conn = psycopg2.connect(local_url)
l_conn.autocommit = True
l_cur = l_conn.cursor()
l_cur.execute('SET statement_timeout = 0;')

t0 = time.time()
print("1. REFRESH MATERIALIZED VIEW mv_ultimo_pase...")
l_cur.execute("REFRESH MATERIALIZED VIEW mv_ultimo_pase;")
print(f"   mv_ultimo_pase refrescada en {time.time() - t0:.2f}s")

t1 = time.time()
print("2. REFRESH MATERIALIZED VIEW mv_primer_ingreso_buzon...")
l_cur.execute("REFRESH MATERIALIZED VIEW mv_primer_ingreso_buzon;")
print(f"   mv_primer_ingreso_buzon refrescada en {time.time() - t1:.2f}s")

l_conn.close()
print("Vistas base refrescadas al día.")
