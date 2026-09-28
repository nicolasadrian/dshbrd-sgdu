"""
Script para sincronizar y migrar completamente hacia PRODUCCIÓN (geo-mdr):
1. cur_manzanasatipicas (desde PDI)
2. cur_lfi_particularizadas (desde PDI)
3. cur_lib_particularizadas (desde PDI)
4. atipicas_base_morfo (desde Local geo-mdr, ya normalizada)
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

PDI_URL = os.getenv("PDI_DATABASE_URL")

LOCAL_DB_URL = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
local_base, _ = LOCAL_DB_URL.rsplit('/', 1)
LOCAL_GEO_URL = f"{local_base}/geo-mdr"

PROD_DB_URL = (os.getenv("DATABASE_URL_PUBLIC") or os.getenv("DATABASE_URL")).replace("postgres://", "postgresql://")
prod_base, _ = PROD_DB_URL.rsplit('/', 1)
PROD_GEO_URL = f"{prod_base}/geo-mdr"

def copy_table(src_url, src_name, dest_url, dest_name, table_name):
    print(f"\n--- Migrando {table_name} desde {src_name} hacia {dest_name} ---")
    s_conn = psycopg2.connect(src_url)
    s_cur = s_conn.cursor()
    
    s_cur.execute("""
        SELECT column_name, data_type, udt_name 
        FROM information_schema.columns 
        WHERE table_name = %s 
        ORDER BY ordinal_position
    """, (table_name,))
    cols_meta = s_cur.fetchall()
    cols = [c[0] for c in cols_meta]
    
    s_cur.execute(f"SELECT {', '.join(['\"' + c + '\"' for c in cols])} FROM public.{table_name}")
    rows = s_cur.fetchall()
    s_conn.close()
    print(f"[{src_name}] {len(rows)} filas leídas de {table_name}.")
    
    d_conn = psycopg2.connect(dest_url)
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
        
    create_sql = f"""
        CREATE TABLE IF NOT EXISTS public.{table_name} (
            {', '.join(col_defs)}
        );
    """
    d_cur.execute(create_sql)
    d_cur.execute(f"TRUNCATE TABLE public.{table_name};")
    
    cols_quoted = [f'"{c}"' for c in cols]
    placeholders = [f"%s" for _ in cols]
    insert_sql = f"""
        INSERT INTO public.{table_name} ({', '.join(cols_quoted)})
        VALUES ({', '.join(placeholders)})
    """
    
    batch_size = 1000
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        d_cur.executemany(insert_sql, batch)
        print(f"[{dest_name}] Insertadas {min(i + batch_size, len(rows))} / {len(rows)} filas...")
        
    # Indices
    try:
        if "sm" in cols:
            d_cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_sm ON public.{table_name} (sm);")
        if "seccion" in cols and "manzana" in cols:
            d_cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_sec_man ON public.{table_name} (seccion, manzana);")
    except Exception as e:
        print(f"[{dest_name}] Nota sobre índices: {e}")
        
    d_conn.close()
    print(f"[{dest_name}] {table_name} sincronizada exitosamente con {len(rows)} registros.")

def main():
    print("=== PASANDO DATOS A PRODUCCIÓN (geo-mdr) ===")
    
    # 1. cur_manzanasatipicas desde PDI
    copy_table(PDI_URL, "PDI (10.10.8.207)", PROD_GEO_URL, "PROD geo-mdr", "cur_manzanasatipicas")
    
    # 2. cur_lfi_particularizadas desde PDI
    copy_table(PDI_URL, "PDI (10.10.8.207)", PROD_GEO_URL, "PROD geo-mdr", "cur_lfi_particularizadas")
    
    # 3. cur_lib_particularizadas desde PDI
    copy_table(PDI_URL, "PDI (10.10.8.207)", PROD_GEO_URL, "PROD geo-mdr", "cur_lib_particularizadas")
    
    # 4. atipicas_base_morfo desde Local geo-mdr (ya normalizada)
    copy_table(LOCAL_GEO_URL, "LOCAL geo-mdr", PROD_GEO_URL, "PROD geo-mdr", "atipicas_base_morfo")
    
    print("\n=== TODAS LAS TABLAS FUERON REPLICADAS A PRODUCCIÓN CON ÉXITO ===")

if __name__ == "__main__":
    main()
