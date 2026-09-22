import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
prod_url = (os.getenv('DATABASE_URL_PUBLIC') or os.getenv('DATABASE_URL')).replace('postgres://', 'postgresql://')
local_url = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')

print("1. Conectando a Producción para extraer definiciones exactas...")
p_conn = psycopg2.connect(prod_url)
p_cur = p_conn.cursor()

# Orden de creación respetando dependencias
views_ordered = [
    'mv_catastro_universo',
    'mv_catastro_egresos_efectivos',
    'mv_catastro_gedos_egreso',
    'mv_catastro_egresos_no_efectivos',
    'mv_catastro_stock_propio',
    'mv_catastro_subsanaciones',
    'mv_catastro_stock_historico'
]

views_defs = {}
for v in views_ordered:
    p_cur.execute("SELECT definition FROM pg_matviews WHERE matviewname = %s", (v,))
    r = p_cur.fetchone()
    if r:
        views_defs[v] = r[0].strip().rstrip(';')

p_conn.close()

print(f"Definiciones extraídas: {list(views_defs.keys())}")

print("\n2. Conectando a Local para aplicar en el orden correcto...")
l_conn = psycopg2.connect(local_url)
l_conn.autocommit = True
l_cur = l_conn.cursor()
l_cur.execute("SET statement_timeout = 0;")

# Eliminar en orden inverso
for v in reversed(views_ordered):
    print(f"  Dropping {v} CASCADE...")
    l_cur.execute(f"DROP MATERIALIZED VIEW IF EXISTS {v} CASCADE;")

# Crear en orden
for v in views_ordered:
    if v in views_defs:
        print(f"  Creating {v}...")
        l_cur.execute(f"CREATE MATERIALIZED VIEW {v} AS {views_defs[v]} WITH DATA;")

print("\n3. Creando índices en Local...")
l_cur.execute("CREATE INDEX IF NOT EXISTS idx_catastro_ee_id ON mv_catastro_egresos_efectivos(id_expediente);")
l_cur.execute("CREATE INDEX IF NOT EXISTS idx_catastro_ee_trata ON mv_catastro_egresos_efectivos(trata);")
l_cur.execute("CREATE INDEX IF NOT EXISTS idx_catastro_ge_id ON mv_catastro_gedos_egreso(id_expediente);")
l_cur.execute("CREATE INDEX IF NOT EXISTS idx_catastro_ge_trata ON mv_catastro_gedos_egreso(trata);")
l_cur.execute("CREATE INDEX IF NOT EXISTS idx_catastro_ene_id ON mv_catastro_egresos_no_efectivos(id_expediente);")
l_cur.execute("CREATE INDEX IF NOT EXISTS idx_catastro_ene_trata ON mv_catastro_egresos_no_efectivos(trata);")
l_cur.execute("CREATE INDEX IF NOT EXISTS idx_catastro_sp_id ON mv_catastro_stock_propio(id_expediente);")
l_cur.execute("CREATE INDEX IF NOT EXISTS idx_catastro_sp_trata ON mv_catastro_stock_propio(trata);")
l_cur.execute("CREATE INDEX IF NOT EXISTS idx_catastro_subs_id ON mv_catastro_subsanaciones(id_expediente);")
l_cur.execute("CREATE INDEX IF NOT EXISTS idx_catastro_subs_trata ON mv_catastro_subsanaciones(trata);")
l_cur.execute("CREATE INDEX IF NOT EXISTS idx_catastro_sh_corte ON mv_catastro_stock_historico(mes_cierre, trata);")

l_conn.close()
print("\n¡Vistas de Catastro sincronizadas al 100% con Producción!")
