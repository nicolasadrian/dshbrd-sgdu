import psycopg2
import os
import json
from dotenv import load_dotenv

load_dotenv()
prod_url = (os.getenv('DATABASE_URL_PUBLIC') or os.getenv('DATABASE_URL')).replace('postgres://', 'postgresql://')
local_url = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')

print("1. Extrayendo cfg_gestion_metas desde Producción...")
p_conn = psycopg2.connect(prod_url)
p_cur = p_conn.cursor()
p_cur.execute("""
    SELECT id, gerencia, trata_reporte, tratas_incluidas, buzones_ingreso, 
           analistas_oficiales, acronimos_egreso, metas_mensuales, activo, 
           firmantes_egreso, buzones_ingreso_intervenciones, descripciones_validas
    FROM cfg_gestion_metas 
    ORDER BY id;
""")
cols = [desc[0] for desc in p_cur.description]
rows = p_cur.fetchall()
p_conn.close()
print(f"Total registros de cfg_gestion_metas en Prod: {len(rows)}")

print("\n2. Sincronizando cfg_gestion_metas en Local...")
l_conn = psycopg2.connect(local_url)
l_conn.autocommit = True
l_cur = l_conn.cursor()

l_cur.execute("TRUNCATE TABLE cfg_gestion_metas CASCADE;")

insert_sql = f"""
    INSERT INTO cfg_gestion_metas ({', '.join(cols)})
    VALUES ({', '.join(['%s'] * len(cols))});
"""

for r in rows:
    # Asegurar formato de metas_mensuales como json string si es dict
    r_list = list(r)
    if isinstance(r_list[7], dict):
        r_list[7] = json.dumps(r_list[7])
    l_cur.execute(insert_sql, tuple(r_list))

print("cfg_gestion_metas sincronizada exitosamente!")
l_conn.close()
