import psycopg2
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path if os.path.exists(env_path) else None)

LOCAL_URL = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')

def dump_sql():
    conn = psycopg2.connect(LOCAL_URL)
    cur = conn.cursor()
    cur.execute("SELECT id, gerencia, trata_reporte, tratas_incluidas, buzones_ingreso, analistas_oficiales, acronimos_egreso, metas_mensuales, activo, firmantes_egreso, buzones_ingreso_intervenciones, descripciones_validas FROM cfg_gestion_metas ORDER BY id;")
    rows = cur.fetchall()

    lines = [
        "-- Replicación de cfg_gestion_metas desde base local a base pública",
        "-- 1. Agregar columna nueva descripciones_validas si no existe en la base pública",
        "ALTER TABLE cfg_gestion_metas ADD COLUMN IF NOT EXISTS descripciones_validas text[];",
        "",
        "-- 2. Vaciar la tabla en la base pública antes de rellenar",
        "TRUNCATE TABLE cfg_gestion_metas CASCADE;",
        "",
        "-- 3. Insertar datos de la base local"
    ]

    for r in rows:
        _id, gerencia, trata_reporte, tratas_incluidas, buzones_ingreso, analistas_oficiales, acronimos_egreso, metas_mensuales, activo, firmantes_egreso, buzones_ingreso_intervenciones, descripciones_validas = r
        
        def to_pg_array(arr):
            if arr is None: return "NULL"
            items = ','.join(f'"{x}"' for x in arr)
            return f"'{{{items}}}'"

        def to_jsonb(obj):
            import json
            if obj is None: return "NULL"
            return f"'{json.dumps(obj)}'::jsonb"

        def to_text(val):
            if val is None: return "NULL"
            return f"'{val}'"

        s = f"INSERT INTO cfg_gestion_metas (id, gerencia, trata_reporte, tratas_incluidas, buzones_ingreso, analistas_oficiales, acronimos_egreso, metas_mensuales, activo, firmantes_egreso, buzones_ingreso_intervenciones, descripciones_validas) VALUES ({_id}, {to_text(gerencia)}, {to_text(trata_reporte)}, {to_pg_array(tratas_incluidas)}, {to_pg_array(buzones_ingreso)}, {to_pg_array(analistas_oficiales)}, {to_pg_array(acronimos_egreso)}, {to_jsonb(metas_mensuales)}, {'TRUE' if activo else 'FALSE'}, {to_pg_array(firmantes_egreso)}, {to_pg_array(buzones_ingreso_intervenciones)}, {to_pg_array(descripciones_validas)});"
        lines.append(s)

    with open('sql/replicate_cfg_gestion_metas.sql', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print("Actualizado sql/replicate_cfg_gestion_metas.sql exitosamente.")

if __name__ == '__main__':
    dump_sql()
