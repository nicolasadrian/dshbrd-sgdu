"""
Script para migrar las tablas de Manzanas Atipicas desde PDI (10.10.8.207)
hacia la base de datos geo-mdr (tanto LOCAL como PRODUCCIÓN).

Tablas a replicar:
- cur_manzanasatipicas
- cur_lfi_particularizadas
- cur_lib_particularizadas
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

PDI_URL = os.getenv("PDI_DATABASE_URL")
if not PDI_URL:
    print("ERROR: PDI_DATABASE_URL no configurada en el archivo .env")
    sys.exit(1)

# Destinos
LOCAL_DB_URL = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
local_base, _ = LOCAL_DB_URL.rsplit('/', 1)
LOCAL_GEO_URL = f"{local_base}/geo-mdr"

PROD_DB_URL = (os.getenv("DATABASE_URL_PUBLIC") or os.getenv("DATABASE_URL")).replace("postgres://", "postgresql://")
prod_base, _ = PROD_DB_URL.rsplit('/', 1)
PROD_GEO_URL = f"{prod_base}/geo-mdr"

TABLES = [
    "cur_manzanasatipicas",
    "cur_lfi_particularizadas",
    "cur_lib_particularizadas"
]

def dump_table_from_pdi(table_name):
    print(f"\n[PDI] Extrayendo datos de {table_name}...")
    p_conn = psycopg2.connect(PDI_URL)
    p_cur = p_conn.cursor()
    
    # Obtener DDL / Columnas
    p_cur.execute("""
        SELECT column_name, data_type, udt_name 
        FROM information_schema.columns 
        WHERE table_name = %s 
        ORDER BY ordinal_position
    """, (table_name,))
    cols_meta = p_cur.fetchall()
    cols = [c[0] for c in cols_meta]
    
    p_cur.execute(f"SELECT {', '.join(cols)} FROM public.{table_name}")
    rows = p_cur.fetchall()
    p_conn.close()
    
    print(f"[PDI] {table_name}: {len(rows)} filas extraídas exitosamente.")
    return cols_meta, rows

def sync_table_to_dest(dest_url, dest_name, table_name, cols_meta, rows):
    print(f"[{dest_name}] Sincronizando {table_name}...")
    d_conn = psycopg2.connect(dest_url)
    d_conn.autocommit = True
    d_cur = d_conn.cursor()
    
    # Habilitar postgis por si las tablas tienen geom
    try:
        d_cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    except Exception:
        pass
    
    # Construir definición de columnas para CREATE TABLE
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
        
    create_sql = f"""
        CREATE TABLE IF NOT EXISTS public.{table_name} (
            {', '.join(col_defs)}
        );
    """
    d_cur.execute(create_sql)
    d_cur.execute(f"TRUNCATE TABLE public.{table_name};")
    
    cols = [f'"{c[0]}"' for c in cols_meta]
    placeholders = [f"%s" for _ in cols_meta]
    insert_sql = f"""
        INSERT INTO public.{table_name} ({', '.join(cols)})
        VALUES ({', '.join(placeholders)})
    """
    
    # Batch insert en bloques de 1000
    batch_size = 1000
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        d_cur.executemany(insert_sql, batch)
        
    # Crear índices comunes para acelerar consultas (seccion, manzana, sm, etc.)
    try:
        if "sm" in [c[0] for c in cols_meta]:
            d_cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_sm ON public.{table_name} (sm);")
        if "seccion" in [c[0] for c in cols_meta] and "manzana" in [c[0] for c in cols_meta]:
            d_cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_sec_man ON public.{table_name} (seccion, manzana);")
    except Exception as e:
        print(f"[{dest_name}] Nota sobre índices: {e}")
        
    d_conn.close()
    print(f"[{dest_name}] {table_name} migrada: {len(rows)} registros.")

def main():
    print("=== INICIANDO MIGRACIÓN DE TABLAS DE PDI A GEO-MDR ===")
    for table_name in TABLES:
        cols_meta, rows = dump_table_from_pdi(table_name)
        # Sincronizar a Local
        sync_table_to_dest(LOCAL_GEO_URL, "LOCAL geo-mdr", table_name, cols_meta, rows)
        # Sincronizar a Producción
        sync_table_to_dest(PROD_GEO_URL, "PROD geo-mdr", table_name, cols_meta, rows)
        
    print("\n=== MIGRACIÓN COMPLETADA CON ÉXITO EN LOCAL Y PRODUCCIÓN ===")

if __name__ == "__main__":
    main()
