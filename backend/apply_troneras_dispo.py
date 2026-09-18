import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DISPOSICION_VAL = "DI-2026-1989-GCABA-DGIUR"
ESTADO_VAL = "Subir a Ciudad 3D"

local_sade = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
local_geo = f"{local_sade.rsplit('/', 1)[0]}/geo-mdr"

prod_sade = os.getenv("DATABASE_URL_PUBLIC") or os.getenv("DATABASE_URL")
if prod_sade and prod_sade.startswith("postgres://"):
    prod_sade = prod_sade.replace("postgres://", "postgresql://", 1)
prod_geo = f"{prod_sade.rsplit('/', 1)[0]}/geo-mdr" if prod_sade else None

print("=== 1. Leyendo troneras_dispo desde LOCAL SADE_DB ===", flush=True)
eng_local_sade = create_engine(local_sade)
with eng_local_sade.connect() as conn:
    td_rows = conn.execute(text("SELECT TRIM(seccion), TRIM(manzana), TRIM(sm) FROM troneras_dispo")).fetchall()
    print(f"Total registros en troneras_dispo local: {len(td_rows)}", flush=True)

if not td_rows:
    print("ERROR: No se encontraron registros en troneras_dispo", flush=True)
    sys.exit(1)

secciones = [r[0] for r in td_rows]
manzanas = [r[1] for r in td_rows]
sms = [r[2] for r in td_rows]

# 2. LOCAL SADE_DB: Actualizar manzanas_lfi_workflow
print("\n=== 2. Aplicando en LOCAL SADE_DB (manzanas_lfi_workflow) ===", flush=True)
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
    
    # Bulk upsert using unnest with CAST
    conn.execute(text("""
        INSERT INTO public.manzanas_lfi_workflow (seccion, manzana, estado, disposicion, updated_at)
        SELECT s, m, :estado, :dispo, CURRENT_TIMESTAMP
        FROM unnest(CAST(:secs AS text[]), CAST(:mzs AS text[])) AS t(s, m)
        ON CONFLICT (seccion, manzana)
        DO UPDATE SET
            estado = EXCLUDED.estado,
            disposicion = EXCLUDED.disposicion,
            updated_at = EXCLUDED.updated_at;
    """), {"secs": secciones, "mzs": manzanas, "estado": ESTADO_VAL, "dispo": DISPOSICION_VAL})
    print(f"  -> {len(secciones)} registros insertados/actualizados en manzanas_lfi_workflow (LOCAL).", flush=True)

# 3. LOCAL GEO-MDR: Actualizar public.manzanas (disposicio)
print("\n=== 3. Aplicando en LOCAL GEO-MDR (public.manzanas) ===", flush=True)
try:
    eng_local_geo = create_engine(local_geo)
    with eng_local_geo.begin() as conn:
        res = conn.execute(text("""
            UPDATE public.manzanas m
            SET disposicio = :dispo
            FROM unnest(CAST(:secs AS text[]), CAST(:mzs AS text[])) AS t(s, m)
            WHERE TRIM(m.seccion) = t.s AND TRIM(m.manzana) = t.m;
        """), {"secs": secciones, "mzs": manzanas, "dispo": DISPOSICION_VAL})
        print(f"  -> {res.rowcount} filas actualizadas en manzanas de geo-mdr (LOCAL).", flush=True)
except Exception as e:
    print(f"  -> Error en local geo-mdr: {e}", flush=True)

# 4. PROD SADE_DB: Copiar troneras_dispo y actualizar manzanas_lfi_workflow
if prod_sade:
    print("\n=== 4. Aplicando en PROD SADE_DB ===", flush=True)
    try:
        eng_prod_sade = create_engine(prod_sade)
        with eng_prod_sade.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.troneras_dispo (
                    seccion VARCHAR,
                    manzana VARCHAR,
                    sm VARCHAR
                );
            """))
            conn.execute(text("TRUNCATE TABLE public.troneras_dispo;"))
            
            # Bulk insert into troneras_dispo
            conn.execute(text("""
                INSERT INTO public.troneras_dispo (seccion, manzana, sm)
                SELECT s, m, sm
                FROM unnest(CAST(:secs AS text[]), CAST(:mzs AS text[]), CAST(:sms AS text[])) AS t(s, m, sm);
            """), {"secs": secciones, "mzs": manzanas, "sms": sms})
            print(f"  -> {len(secciones)} registros copiados a troneras_dispo (PROD).", flush=True)

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

            # Bulk upsert in prod
            conn.execute(text("""
                INSERT INTO public.manzanas_lfi_workflow (seccion, manzana, estado, disposicion, updated_at)
                SELECT s, m, :estado, :dispo, CURRENT_TIMESTAMP
                FROM unnest(CAST(:secs AS text[]), CAST(:mzs AS text[])) AS t(s, m)
                ON CONFLICT (seccion, manzana)
                DO UPDATE SET
                    estado = EXCLUDED.estado,
                    disposicion = EXCLUDED.disposicion,
                    updated_at = EXCLUDED.updated_at;
            """), {"secs": secciones, "mzs": manzanas, "estado": ESTADO_VAL, "dispo": DISPOSICION_VAL})
            print(f"  -> {len(secciones)} registros insertados/actualizados en manzanas_lfi_workflow (PROD).", flush=True)
    except Exception as e:
        print(f"  -> Error en PROD SADE_DB: {e}", flush=True)

# 5. PROD GEO-MDR: Actualizar public.manzanas
if prod_geo:
    print("\n=== 5. Aplicando en PROD GEO-MDR ===", flush=True)
    try:
        eng_prod_geo = create_engine(prod_geo)
        with eng_prod_geo.begin() as conn:
            res_p = conn.execute(text("""
                UPDATE public.manzanas m
                SET disposicio = :dispo
                FROM unnest(CAST(:secs AS text[]), CAST(:mzs AS text[])) AS t(s, m)
                WHERE TRIM(m.seccion) = t.s AND TRIM(m.manzana) = t.m;
            """), {"secs": secciones, "mzs": manzanas, "dispo": DISPOSICION_VAL})
            print(f"  -> {res_p.rowcount} filas actualizadas en manzanas de geo-mdr (PROD).", flush=True)
    except Exception as e:
        print(f"  -> Error en PROD GEO-MDR: {e}", flush=True)

print("\n=== PROCESO FINALIZADO EXITOSAMENTE ===", flush=True)
