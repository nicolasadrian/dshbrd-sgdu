import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# Conexiones
local_sade = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
if local_sade.startswith("postgres://"):
    local_sade = local_sade.replace("postgres://", "postgresql://", 1)
local_geo = f"{local_sade.rsplit('/', 1)[0]}/geo-mdr"

prod_sade = os.getenv("DATABASE_URL_PUBLIC") or os.getenv("DATABASE_URL")
if prod_sade and prod_sade.startswith("postgres://"):
    prod_sade = prod_sade.replace("postgres://", "postgresql://", 1)
prod_geo = f"{prod_sade.rsplit('/', 1)[0]}/geo-mdr" if prod_sade else None

if not prod_geo:
    print("ERROR: No se encontró URL de base de datos de producción en .env")
    sys.exit(1)

print("=== 1. Conectando a PROD geo-mdr ===")
eng_prod = create_engine(prod_geo)
with eng_prod.connect() as pconn:
    # Verificar si existe la tabla
    exists = pconn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'lfi_troneras'
        );
    """)).fetchone()[0]
    
    if not exists:
        print("La tabla public.lfi_troneras no existe en producción.")
        sys.exit(1)
        
    # Leer registros con WKT de la geometría
    rows = pconn.execute(text("""
        SELECT gid, seccion, manzana, mz_tipo, sm, disposicio, ST_AsText(geom) as wkt
        FROM public.lfi_troneras
        ORDER BY gid
    """)).fetchall()
    
    print(f"Total registros encontrados en PROD public.lfi_troneras: {len(rows)}")

print("\n=== 2. Conectando a LOCAL geo-mdr y creando/actualizando tabla ===")
eng_local = create_engine(local_geo)
with eng_local.begin() as lconn:
    # Crear estructura
    lconn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.lfi_troneras (
            gid BIGSERIAL PRIMARY KEY,
            seccion VARCHAR(10) NOT NULL,
            manzana VARCHAR(10) NOT NULL,
            mz_tipo VARCHAR(50),
            sm VARCHAR(20) NOT NULL,
            disposicio VARCHAR(100) DEFAULT 'A designar',
            geom geometry(Geometry, 22186)
        );
        ALTER TABLE public.lfi_troneras DROP COLUMN IF EXISTS capa;
        CREATE INDEX IF NOT EXISTS idx_lfi_troneras_sm ON public.lfi_troneras(sm);
        CREATE INDEX IF NOT EXISTS idx_lfi_troneras_geom ON public.lfi_troneras USING GIST(geom);
    """))
    
    # Limpiar tabla local
    lconn.execute(text("TRUNCATE TABLE public.lfi_troneras RESTART IDENTITY;"))
    
    if rows:
        # Insertar registros
        for r in rows:
            lconn.execute(text("""
                INSERT INTO public.lfi_troneras (gid, seccion, manzana, mz_tipo, sm, disposicio, geom)
                VALUES (:gid, :seccion, :manzana, :mz_tipo, :sm, :disposicio, ST_SetSRID(ST_GeomFromText(:wkt), 22186))
            """), {
                "gid": r[0],
                "seccion": r[1],
                "manzana": r[2],
                "mz_tipo": r[3],
                "sm": r[4],
                "disposicio": r[5],
                "wkt": r[6]
            })
            
        # Actualizar secuencia del id
        lconn.execute(text("""
            SELECT setval(pg_get_serial_sequence('public.lfi_troneras', 'gid'), COALESCE(MAX(gid), 1))
            FROM public.lfi_troneras;
        """))
        print(f"  -> {len(rows)} registros copiados exitosamente a LOCAL geo-mdr.")
    else:
        print("  -> La tabla en producción estaba vacía, tabla local truncada.")

print("\n=== 3. Verificando tabla LOCAL ===")
with eng_local.connect() as lconn:
    count = lconn.execute(text("SELECT COUNT(*) FROM public.lfi_troneras")).scalar()
    print(f"Total registros en LOCAL public.lfi_troneras: {count}")
    
    sample = lconn.execute(text("""
        SELECT gid, seccion, manzana, mz_tipo, sm, disposicio, ST_GeometryType(geom), ST_SRID(geom)
        FROM public.lfi_troneras
        LIMIT 5
    """)).fetchall()
    print("\nMuestra de registros en LOCAL:")
    for s in sample:
        print(" ", s)
