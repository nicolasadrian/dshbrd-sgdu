import os
import sys
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

prod_sade = os.getenv("DATABASE_URL_PUBLIC")
local_sade = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")

if prod_sade and prod_sade.startswith("postgres://"):
    prod_sade = prod_sade.replace("postgres://", "postgresql://", 1)

prod_geo = f"{prod_sade.rsplit('/', 1)[0]}/geo-mdr"
local_geo = f"{local_sade.rsplit('/', 1)[0]}/geo-mdr"

print("===============================================================")
print(" SINCRONIZADOR DE DATOS DE AVANCE (LFI / TRONERAS) PROD -> LOCAL")
print("===============================================================")

eng_prod_sade = create_engine(prod_sade)
eng_local_sade = create_engine(local_sade)

# 1. Sincronizar manzanas_lfi_workflow
print("\n[1/3] Sincronizando tabla: 'manzanas_lfi_workflow' (sade_db)...")
try:
    with eng_prod_sade.connect() as conn:
        df_wf = pd.read_sql(text("SELECT * FROM public.manzanas_lfi_workflow"), conn)
    print(f"  -> Descargadas {len(df_wf)} filas desde PROD.")

    with eng_local_sade.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.manzanas_lfi_workflow (
                seccion VARCHAR,
                manzana VARCHAR,
                estado VARCHAR,
                analista_asignado VARCHAR,
                disposicion TEXT,
                archivo_trazado VARCHAR,
                archivo_finalizado VARCHAR,
                updated_at TIMESTAMP,
                PRIMARY KEY (seccion, manzana)
            );
        """))
        conn.execute(text("TRUNCATE TABLE public.manzanas_lfi_workflow;"))
        df_wf.to_sql("manzanas_lfi_workflow", conn, if_exists="append", index=False)
    print("  -> Insertadas exitosamente en LOCAL sade_db.")
except Exception as e:
    print(f"  [ERROR] Fallo sincronizando manzanas_lfi_workflow: {e}")

# 2. Sincronizar manzanas_lfi_notes (si existe)
print("\n[2/3] Sincronizando notas: 'manzanas_lfi_notes' (sade_db)...")
try:
    with eng_prod_sade.connect() as conn:
        df_notes = pd.read_sql(text("SELECT * FROM public.manzanas_lfi_notes"), conn)
    print(f"  -> Descargadas {len(df_notes)} notas desde PROD.")

    with eng_local_sade.begin() as conn:
        # Check structure / create if not exists
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.manzanas_lfi_notes (
                id SERIAL PRIMARY KEY,
                seccion VARCHAR,
                manzana VARCHAR,
                usuario VARCHAR,
                nota TEXT,
                created_at TIMESTAMP
            );
        """))
        conn.execute(text("TRUNCATE TABLE public.manzanas_lfi_notes;"))
        df_notes.to_sql("manzanas_lfi_notes", conn, if_exists="append", index=False)
    print("  -> Insertadas exitosamente en LOCAL sade_db.")
except Exception as e:
    print(f"  [AVISO] No se pudo copiar manzanas_lfi_notes: {e}")

# 3. Sincronizar lfi_troneras (geometrías trazadas en geo-mdr)
print("\n[3/3] Sincronizando capas trazadas: 'lfi_troneras' (geo-mdr)...")
try:
    eng_prod_geo = create_engine(prod_geo)
    eng_local_geo = create_engine(local_geo)

    with eng_prod_geo.connect() as conn:
        df_lfi = pd.read_sql(text("SELECT * FROM public.lfi_troneras"), conn)
    print(f"  -> Descargadas {len(df_lfi)} geometrías/registros desde PROD geo-mdr.")

    with eng_local_geo.begin() as conn:
        # Borrar y reescribir
        try:
            conn.execute(text("TRUNCATE TABLE public.lfi_troneras;"))
            df_lfi.to_sql("lfi_troneras", conn, if_exists="append", index=False)
            print("  -> Insertadas exitosamente en LOCAL geo-mdr.")
        except Exception as table_err:
            # Si la tabla no existía o difiere schema, crear vía to_sql
            df_lfi.to_sql("lfi_troneras", conn, if_exists="replace", index=False)
            print("  -> Tabla creada y poblada en LOCAL geo-mdr.")
except Exception as e:
    print(f"  [AVISO/ERROR] Sincronizando lfi_troneras: {e}")

# Validar estado final en LOCAL
print("\n=== RESUMEN FINAL EN LOCAL ===")
with eng_local_sade.connect() as conn:
    res = conn.execute(text("SELECT COUNT(*) FROM public.manzanas_lfi_workflow")).scalar()
    estados = conn.execute(text("SELECT estado, COUNT(*) FROM public.manzanas_lfi_workflow GROUP BY estado")).fetchall()
    print(f"Total manzanas_lfi_workflow en LOCAL: {res}")
    for est, cnt in estados:
        print(f"  - {est}: {cnt}")

try:
    os.remove("check_prod_tables.py")
except:
    pass

print("\n¡Sincronización completada con éxito!")
