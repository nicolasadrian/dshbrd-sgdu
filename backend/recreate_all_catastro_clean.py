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
    WHERE matviewname LIKE '%catastro%' 
    ORDER BY matviewname;
""")
views_data = p_cur.fetchall()
p_conn.close()

l_conn = psycopg2.connect(local_url)
l_conn.autocommit = True
l_cur = l_conn.cursor()
l_cur.execute('SET statement_timeout = 0;')

# Drop all first
for n, _ in views_data:
    l_cur.execute(f"DROP MATERIALIZED VIEW IF EXISTS {n} CASCADE;")

# Create iteratively
pending = list(views_data)
pass_idx = 1
while pending and pass_idx <= 6:
    still = []
    print(f"Pasada {pass_idx} ({len(pending)} pendientes)...")
    for n, d in pending:
        try:
            clean = d.strip().rstrip(';')
            l_cur.execute(f"CREATE MATERIALIZED VIEW {n} AS {clean} WITH DATA;")
            print(f"  [+] {n} OK")
        except Exception as e:
            still.append((n, d))
    pending = still
    pass_idx += 1

# Indices
indices = [
    'CREATE INDEX IF NOT EXISTS idx_catastro_ee_id ON mv_catastro_egresos_efectivos(id_expediente);',
    'CREATE INDEX IF NOT EXISTS idx_catastro_ee_trata ON mv_catastro_egresos_efectivos(trata);',
    'CREATE INDEX IF NOT EXISTS idx_catastro_ge_id ON mv_catastro_gedos_egreso(id_expediente);',
    'CREATE INDEX IF NOT EXISTS idx_catastro_ge_trata ON mv_catastro_gedos_egreso(trata);',
    'CREATE INDEX IF NOT EXISTS idx_catastro_ene_id ON mv_catastro_egresos_no_efectivos(id_expediente);',
    'CREATE INDEX IF NOT EXISTS idx_catastro_ene_trata ON mv_catastro_egresos_no_efectivos(trata);',
    'CREATE INDEX IF NOT EXISTS idx_catastro_sp_id ON mv_catastro_stock_propio(id_expediente);',
    'CREATE INDEX IF NOT EXISTS idx_catastro_sp_trata ON mv_catastro_stock_propio(trata);',
    'CREATE INDEX IF NOT EXISTS idx_catastro_subs_id ON mv_catastro_subsanaciones(id_expediente);',
    'CREATE INDEX IF NOT EXISTS idx_catastro_subs_trata ON mv_catastro_subsanaciones(trata);',
    'CREATE INDEX IF NOT EXISTS idx_catastro_sh_corte ON mv_catastro_stock_historico(mes_cierre, trata);'
]
for idx_sql in indices:
    try:
        l_cur.execute(idx_sql)
    except Exception as e:
        pass

l_conn.close()
print("¡Todas las 13 vistas de Catastro recreadas e indexadas exitosamente en Local!")
