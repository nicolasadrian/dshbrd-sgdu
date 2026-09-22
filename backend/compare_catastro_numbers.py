import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
prod_url = (os.getenv('DATABASE_URL_PUBLIC') or os.getenv('DATABASE_URL')).replace('postgres://', 'postgresql://')
local_url = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')

p_conn = psycopg2.connect(prod_url)
p_cur = p_conn.cursor()
p_cur.execute('SET statement_timeout = 0;')

l_conn = psycopg2.connect(local_url)
l_cur = l_conn.cursor()
l_cur.execute('SET statement_timeout = 0;')

print('=== COMPARANDO CATASTRO AGOSTO 2026: PROD VS LOCAL ===\n')

# 1. Egresos Efectivos por trata
p_cur.execute("""
    SELECT trata, count(*) 
    FROM mv_catastro_egresos_efectivos 
    WHERE fecha_egreso >= '2026-08-01' AND fecha_egreso < '2026-09-01'
    GROUP BY trata ORDER BY trata;
""")
p_egr = dict(p_cur.fetchall())

l_cur.execute("""
    SELECT trata, count(*) 
    FROM mv_catastro_egresos_efectivos 
    WHERE fecha_egreso >= '2026-08-01' AND fecha_egreso < '2026-09-01'
    GROUP BY trata ORDER BY trata;
""")
l_egr = dict(l_cur.fetchall())

print("1. Egresos Efectivos Agosto 2026:")
for t in sorted(set(list(p_egr.keys()) + list(l_egr.keys()))):
    print(f"  {t:<15}: PROD={p_egr.get(t,0):<5} | LOCAL={l_egr.get(t,0):<5}")

# 2. Stock Propio al cierre de Agosto 2026
p_cur.execute("""
    SELECT trata, sum(cant_expedientes) 
    FROM mv_catastro_stock_historico 
    WHERE mes_label = '2026-08' AND categoria = 'STOCK_PROPIO' 
    GROUP BY trata ORDER BY trata;
""")
p_sh = dict(p_cur.fetchall())

l_cur.execute("""
    SELECT trata, sum(cant_expedientes) 
    FROM mv_catastro_stock_historico 
    WHERE mes_label = '2026-08' AND categoria = 'STOCK_PROPIO' 
    GROUP BY trata ORDER BY trata;
""")
l_sh = dict(l_cur.fetchall())

print("\n2. Stock Propio Agosto 2026 (mv_catastro_stock_historico):")
for t in sorted(set(list(p_sh.keys()) + list(l_sh.keys()))):
    print(f"  {t:<15}: PROD={p_sh.get(t,0):<5} | LOCAL={l_sh.get(t,0):<5}")

# 3. Subsanaciones al cierre de Agosto 2026
p_cur.execute("""
    SELECT trata, sum(cant_expedientes) 
    FROM mv_catastro_stock_historico 
    WHERE mes_label = '2026-08' AND categoria = 'SUBSANACION' 
    GROUP BY trata ORDER BY trata;
""")
p_subs = dict(p_cur.fetchall())

l_cur.execute("""
    SELECT trata, sum(cant_expedientes) 
    FROM mv_catastro_stock_historico 
    WHERE mes_label = '2026-08' AND categoria = 'SUBSANACION' 
    GROUP BY trata ORDER BY trata;
""")
l_subs = dict(l_cur.fetchall())

print("\n3. Subsanaciones Agosto 2026 (mv_catastro_stock_historico):")
for t in sorted(set(list(p_subs.keys()) + list(l_subs.keys()))):
    print(f"  {t:<15}: PROD={p_subs.get(t,0):<5} | LOCAL={l_subs.get(t,0):<5}")

p_conn.close()
l_conn.close()
