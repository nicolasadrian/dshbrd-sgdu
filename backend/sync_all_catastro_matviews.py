import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
prod_url = (os.getenv('DATABASE_URL_PUBLIC') or os.getenv('DATABASE_URL')).replace('postgres://', 'postgresql://')
local_url = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')

p_conn = psycopg2.connect(prod_url)
p_cur = p_conn.cursor()
p_cur.execute("""
    SELECT matviewname, definition 
    FROM pg_matviews 
    WHERE matviewname LIKE '%catastro%';
""")
p_views = p_cur.fetchall()
p_conn.close()

print(f"Total matviews de Catastro en Prod: {len(p_views)}")
for n, _ in p_views:
    print(f" - {n}")

l_conn = psycopg2.connect(local_url)
l_conn.autocommit = True
l_cur = l_conn.cursor()
l_cur.execute('SET statement_timeout = 0;')

for name, definition in p_views:
    print(f"Replicando {name} en Local...")
    try:
        l_cur.execute(f"DROP MATERIALIZED VIEW IF EXISTS {name} CASCADE;")
        clean_def = definition.strip().rstrip(';')
        l_cur.execute(f"CREATE MATERIALIZED VIEW {name} AS {clean_def} WITH DATA;")
        print(f"  [+] {name} OK")
    except Exception as e:
        print(f"  [-] {name} Error: {e}")

l_conn.close()
print("Sincronización de todas las vistas de Catastro completada.")
