"""
Script para migrar la capa cur_restricciones desde LOCAL geo-mdr hacia PRODUCCIÓN geo-mdr.
Asegura:
- Tipos de datos limpios.
- Geometrías convertidas a 2D y con SRID oficial 3857 (Web Mercator).
- Creación de índices espaciales GIST sobre geom y sobre tipo/sm/seccion/manzana.
"""

import os
import sys
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

LOCAL_DB_URL = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
local_base, _ = LOCAL_DB_URL.rsplit('/', 1)
LOCAL_GEO_URL = f"{local_base}/geo-mdr"

PROD_DB_URL = (os.getenv("DATABASE_URL_PUBLIC") or os.getenv("DATABASE_URL")).replace("postgres://", "postgresql://")
prod_base, _ = PROD_DB_URL.rsplit('/', 1)
PROD_GEO_URL = f"{prod_base}/geo-mdr"

def migrate_cur_restricciones():
    print("=== INICIANDO MIGRACIÓN DE cur_restricciones ===")
    print(f"Origen: LOCAL geo-mdr ({LOCAL_GEO_URL})")
    print(f"Destino: PROD geo-mdr ({PROD_GEO_URL})")

    # 1. Leer datos de Local
    print("\n1. Conectando a LOCAL geo-mdr y extrayendo registros...")
    s_conn = psycopg2.connect(LOCAL_GEO_URL)
    s_cur = s_conn.cursor()
    
    # Extraer convirtiendo geom a 2D y con SRID 3857 explícito
    query_src = """
        SELECT 
            gid,
            __gid,
            seccion,
            manzana,
            tipo,
            obs,
            sm,
            nro_ord,
            ST_AsBinary(ST_Force2D(ST_SetSRID(geom, 3857))) AS geom_wkb
        FROM public.cur_restricciones
        ORDER BY gid;
    """
    s_cur.execute(query_src)
    rows = s_cur.fetchall()
    s_conn.close()
    print(f"   -> Leídos {len(rows)} registros de LOCAL geo-mdr.")

    if not rows:
        print("No se encontraron registros para migrar.")
        return

    # 2. Conectar a Producción y crear tabla
    print("\n2. Conectando a PRODUCCIÓN geo-mdr...")
    d_conn = psycopg2.connect(PROD_GEO_URL)
    d_conn.autocommit = True
    d_cur = d_conn.cursor()

    try:
        d_cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    except Exception as e:
        print(f"   Advertencia PostGIS: {e}")

    print("   Creando tabla public.cur_restricciones con SRID 3857 en Producción...")
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS public.cur_restricciones (
            gid integer PRIMARY KEY,
            __gid double precision,
            seccion character varying,
            manzana character varying,
            tipo character varying,
            obs character varying,
            sm character varying,
            nro_ord character varying,
            geom geometry(MultiLineString, 3857)
        );
    """
    d_cur.execute(create_table_sql)
    d_cur.execute("TRUNCATE TABLE public.cur_restricciones;")

    print(f"3. Insertando {len(rows)} registros en bloques...")
    insert_sql = """
        INSERT INTO public.cur_restricciones (
            gid, __gid, seccion, manzana, tipo, obs, sm, nro_ord, geom
        ) VALUES %s;
    """
    
    # Preparamos las tuplas convirtiendo el WKB a geometría con ST_GeomFromWKB(%s, 3857)
    # usando psycopg2 Binary o subconsulta
    from psycopg2 import Binary
    prepared_data = [
        (
            r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7],
            r[8] # WKB en bytes
        )
        for r in rows
    ]

    template = "(%s, %s, %s, %s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromWKB(%s), 3857))"
    execute_values(d_cur, insert_sql, prepared_data, template=template, page_size=1000)
    print("   -> Inserción completada con éxito.")

    # 4. Crear índices
    print("\n4. Creando índices en PRODUCCIÓN...")
    indices = [
        "CREATE INDEX IF NOT EXISTS idx_cur_restricciones_geom ON public.cur_restricciones USING GIST (geom);",
        "CREATE INDEX IF NOT EXISTS idx_cur_restricciones_tipo ON public.cur_restricciones (tipo);",
        "CREATE INDEX IF NOT EXISTS idx_cur_restricciones_sm ON public.cur_restricciones (sm);",
        "CREATE INDEX IF NOT EXISTS idx_cur_restricciones_sec_man ON public.cur_restricciones (seccion, manzana);"
    ]
    for idx_sql in indices:
        d_cur.execute(idx_sql)
    print("   -> Índices creados.")

    # 5. Verificación
    d_cur.execute("""
        SELECT 
            COUNT(*), 
            ST_SRID(geom), 
            GeometryType(geom), 
            ST_CoordDim(geom)
        FROM public.cur_restricciones
        GROUP BY 2, 3, 4;
    """)
    stats = d_cur.fetchall()
    print("\n=== VERIFICACIÓN EN PRODUCCIÓN ===")
    for s in stats:
        print(f"Total: {s[0]} | SRID: {s[1]} | Tipo Geom: {s[2]} | CoordDim: {s[3]}")

    d_cur.execute("SELECT tipo, count(*) FROM public.cur_restricciones GROUP BY tipo ORDER BY count(*) DESC;")
    print("\nDesglose por tipo en Producción:")
    for t, c in d_cur.fetchall():
        print(f"  - {t}: {c}")

    d_conn.close()
    print("\n=== MIGRACIÓN A PRODUCCIÓN COMPLETADA SATISFACTORIAMENTE ===")

if __name__ == "__main__":
    migrate_cur_restricciones()
