import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import execute_values, Json
import json
import sys
import time

# Configuración Origen (Local) y Destino (Nuevo servidor)
ORIGEN_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "lenovo"
}

DESTINO_CONFIG = {
    "host": "10.78.33.238",
    "port": 5432,
    "user": "postgres",
    "password": "lenovo"
}

DATABASES_TO_MIGRATE = ["sade_db", "geo-mdr"]

def get_connection(cfg, dbname="postgres"):
    params = cfg.copy()
    params["dbname"] = dbname
    params["connect_timeout"] = 10
    return psycopg2.connect(**params)

def asegurar_base_datos_destino(dbname):
    """Crea la base de datos en el destino si no existe."""
    conn = get_connection(DESTINO_CONFIG, "postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (dbname,))
    exists = cur.fetchone()
    if not exists:
        print(f"  [+] Creando base de datos destino '{dbname}'...")
        cur.execute(f'CREATE DATABASE "{dbname}";')
    else:
        print(f"  [*] La base de datos destino '{dbname}' ya existe.")
    cur.close()
    conn.close()

def migrar_base_datos(dbname):
    print(f"\n==================================================")
    print(f" Iniciando migración de la base de datos: {dbname}")
    print(f"==================================================")
    
    asegurar_base_datos_destino(dbname)
    
    conn_src = get_connection(ORIGEN_CONFIG, dbname)
    conn_dst = get_connection(DESTINO_CONFIG, dbname)
    cur_src = conn_src.cursor()
    cur_dst = conn_dst.cursor()
    
    # 1. Copiar y habilitar Extensiones (PostGIS, dblink, postgis_raster, etc.)
    cur_src.execute("SELECT extname FROM pg_extension WHERE extname NOT IN ('plpgsql');")
    exts = [r[0] for r in cur_src.fetchall()]
    for ext in exts:
        print(f"  [+] Habilitando extensión '{ext}' en el destino...")
        try:
            cur_dst.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext}";')
            conn_dst.commit()
        except Exception as e:
            conn_dst.rollback()
            print(f"  [!] No se pudo activar extensión '{ext}': {e}")

    # 2. Copiar Esquemas (Schemas)
    cur_src.execute("""
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast', 'topology')
          AND schema_name NOT LIKE 'pg_%%'
          AND schema_name NOT LIKE '_pg_%%';
    """)
    schemas = [r[0] for r in cur_src.fetchall()]
    for s in schemas:
        if s != 'public':
            print(f"  [+] Creando esquema '{s}'...")
            cur_dst.execute(f'CREATE SCHEMA IF NOT EXISTS "{s}";')
    conn_dst.commit()

    # 3. Copiar Secuencias
    cur_src.execute("""
        SELECT sequence_schema, sequence_name 
        FROM information_schema.sequences
        WHERE sequence_schema NOT IN ('pg_catalog', 'information_schema', 'topology')
          AND sequence_schema NOT LIKE 'pg_%%'
          AND sequence_schema NOT LIKE '_pg_%%';
    """)
    sequences = cur_src.fetchall()
    for s_schema, s_name in sequences:
        q_name = f'"{s_schema}"."{s_name}"'
        print(f"  [+] Creando secuencia {q_name}...")
        cur_dst.execute(f"CREATE SEQUENCE IF NOT EXISTS {q_name};")
    conn_dst.commit()

    # 4. Copiar Tablas Base
    cur_src.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_type = 'BASE TABLE' 
          AND table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast', 'topology')
          AND table_schema NOT LIKE 'pg_%%'
          AND table_schema NOT LIKE '_pg_%%'
          AND table_name != 'spatial_ref_sys';
    """)
    tables = cur_src.fetchall()
    print(f"\n  [-->] {len(tables)} tablas encontradas para migrar estructura y datos.")

    for schema, table in tables:
        full_table = f'"{schema}"."{table}"'
        
        # Verificar si la tabla existe en el destino y el conteo de registros coincide
        cur_src.execute(f"SELECT COUNT(*) FROM {full_table};")
        src_count = cur_src.fetchone()[0]
        
        cur_dst.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s AND table_type = 'BASE TABLE'
            );
        """, (schema, table))
        dst_exists = cur_dst.fetchone()[0]
        
        if dst_exists:
            cur_dst.execute(f"SELECT COUNT(*) FROM {full_table};")
            dst_count = cur_dst.fetchone()[0]
            if src_count == dst_count:
                print(f"  [=] Tabla {full_table} ya migrada ({dst_count} filas). Omitiendo...")
                continue

        print(f"\n  Procesando Tabla: {full_table} (Origen: {src_count} filas)")
        
        # Eliminar si existe en el destino (para re-crear con la estructura exacta)
        cur_dst.execute(f"DROP TABLE IF EXISTS {full_table} CASCADE;")
        conn_dst.commit()
        
        # Obtener columnas y tipos
        cur_src.execute("""
            SELECT column_name, data_type, udt_name, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position;
        """, (schema, table))
        cols = cur_src.fetchall()
        
        col_defs = []
        col_names = []
        is_geometry = False
        
        for c_name, d_type, udt_name, is_null, c_def in cols:
            col_names.append(f'"{c_name}"')
            
            if udt_name == 'geometry':
                is_geometry = True
                cur_src.execute(f"""
                    SELECT type, srid 
                    FROM geometry_columns 
                    WHERE f_table_schema = %s AND f_table_name = %s AND f_geometry_column = %s;
                """, (schema, table, c_name))
                geom_info = cur_src.fetchone()
                if geom_info:
                    g_type, g_srid = geom_info
                    col_defs.append(f'"{c_name}" geometry({g_type}, {g_srid})')
                else:
                    col_defs.append(f'"{c_name}" geometry')
            else:
                type_str = d_type.upper() if d_type != 'USER-DEFINED' else udt_name
                if d_type == 'ARRAY':
                    type_str = f"{udt_name.lstrip('_')}[]"
                
                null_str = "" if is_null == 'YES' else " NOT NULL"
                col_defs.append(f'"{c_name}" {type_str}{null_str}')

        create_table_sql = f"CREATE TABLE {full_table} ({', '.join(col_defs)});"
        cur_dst.execute(create_table_sql)
        conn_dst.commit()
        
        # Migración de datos
        cols_joined = ", ".join(col_names)
        if is_geometry:
            select_cols = []
            for c_name, d_type, udt_name, _, _ in cols:
                if udt_name == 'geometry':
                    select_cols.append(f'ST_AsEWKT("{c_name}") AS "{c_name}"')
                else:
                    select_cols.append(f'"{c_name}"')
            cur_src.execute(f"SELECT {', '.join(select_cols)} FROM {full_table};")
        else:
            cur_src.execute(f"SELECT {cols_joined} FROM {full_table};")
            
        rows = cur_src.fetchall()
        if rows:
            print(f"     -> Insertando {len(rows)} filas...")
            val_templates = []
            for c_name, d_type, udt_name, _, _ in cols:
                if udt_name == 'geometry':
                    val_templates.append("ST_GeomFromEWKT(%s)")
                elif (d_type in ('json', 'jsonb') or udt_name in ('json', 'jsonb')) and d_type != 'ARRAY':
                    val_templates.append("%s::jsonb")
                else:
                    val_templates.append("%s")
            
            # Para la lectura de filas, si la columna es ARRAY y val es list, psycopg2 maneja el array nativo de Python a Postgres
            processed_rows = []
            for row in rows:
                new_row = []
                for idx, val in enumerate(row):
                    c_name, d_type, udt_name, _, _ = cols[idx]
                    if d_type != 'ARRAY' and udt_name not in ('_text', '_varchar', '_int4', '_int8') and isinstance(val, (dict, list)):
                        new_row.append(json.dumps(val))
                    else:
                        new_row.append(val)
                processed_rows.append(tuple(new_row))

            template_str = f"({', '.join(val_templates)})"
            insert_sql = f"INSERT INTO {full_table} ({cols_joined}) VALUES %s;"
            execute_values(cur_dst, insert_sql, processed_rows, template=template_str, page_size=2000)
            conn_dst.commit()
        else:
            print("     -> Tabla vacía.")

    # 5. Copiar Vistas Estándar (VIEW)
    print("\n  [-->] Migrando Vistas Estándar (VIEW)...")
    cur_src.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_type = 'VIEW' 
          AND table_schema NOT IN ('pg_catalog', 'information_schema', 'topology')
          AND table_name NOT IN ('geometry_columns', 'geography_columns', 'raster_columns', 'raster_overviews')
          AND table_schema NOT LIKE 'pg_%%'
          AND table_schema NOT LIKE '_pg_%%';
    """)
    views = cur_src.fetchall()
    
    pending_views = []
    for schema, view in views:
        full_view = f'"{schema}"."{view}"'
        cur_src.execute("SELECT pg_get_viewdef(%s::regclass, true);", (f"{schema}.{view}",))
        view_def = cur_src.fetchone()[0]
        pending_views.append((full_view, view_def))

    max_passes = 5
    for pass_num in range(1, max_passes + 1):
        if not pending_views:
            break
        still_pending = []
        for full_view, view_def in pending_views:
            try:
                cur_dst.execute(f"DROP VIEW IF EXISTS {full_view} CASCADE;")
                cur_dst.execute(f"CREATE VIEW {full_view} AS {view_def}")
                conn_dst.commit()
                print(f"  [+] Recreada Vista {full_view}")
            except Exception as err:
                conn_dst.rollback()
                still_pending.append((full_view, view_def, str(err)))
        
        if len(still_pending) == len(pending_views):
            for fv, vd, err_msg in still_pending:
                print(f"  [!] Advertencia: No se pudo crear la vista {fv} (Falta tabla/dependencia en origen): {err_msg.splitlines()[0]}")
            break
        pending_views = [(fv, vd) for fv, vd, _ in still_pending]

    # 6. Copiar Vistas Materializadas (MATERIALIZED VIEW) como mvw_stock_actual_detalle, mvw_m2_permisados, etc.
    print("\n  [-->] Migrando Vistas Materializadas (MATERIALIZED VIEW)...")
    cur_src.execute("""
        SELECT schemaname, matviewname 
        FROM pg_matviews 
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema', 'topology')
          AND schemaname NOT LIKE 'pg_%%'
          AND schemaname NOT LIKE '_pg_%%';
    """)
    mat_views = cur_src.fetchall()
    
    pending_matviews = []
    for schema, mv in mat_views:
        full_mv = f'"{schema}"."{mv}"'
        cur_src.execute("SELECT pg_get_viewdef(%s::regclass, true);", (f"{schema}.{mv}",))
        mv_def = cur_src.fetchone()[0]
        pending_matviews.append((schema, mv, full_mv, mv_def))

    for pass_num in range(1, max_passes + 1):
        if not pending_matviews:
            break
        still_pending_mv = []
        for schema, mv, full_mv, mv_def in pending_matviews:
            try:
                # Comprobar si ya existe en el destino y tiene registros
                cur_src.execute(f"SELECT COUNT(*) FROM {full_mv};")
                src_mv_cnt = cur_src.fetchone()[0]
                
                cur_dst.execute("SELECT EXISTS (SELECT 1 FROM pg_matviews WHERE schemaname = %s AND matviewname = %s);", (schema, mv))
                dst_mv_exists = cur_dst.fetchone()[0]
                
                if dst_mv_exists:
                    cur_dst.execute(f"SELECT COUNT(*) FROM {full_mv};")
                    dst_mv_cnt = cur_dst.fetchone()[0]
                    if src_mv_cnt == dst_mv_cnt:
                        print(f"  [=] Vista Materializada {full_mv} ya migrada ({dst_mv_cnt} filas). Omitiendo...")
                        continue

                cur_dst.execute(f"DROP MATERIALIZED VIEW IF EXISTS {full_mv} CASCADE;")
                print(f"  [+] Recreando e insertando datos en Vista Materializada {full_mv} ({src_mv_cnt} filas)...")
                cur_dst.execute(f"CREATE MATERIALIZED VIEW {full_mv} AS {mv_def} WITH DATA;")
                conn_dst.commit()
            except Exception as err:
                conn_dst.rollback()
                still_pending_mv.append((schema, mv, full_mv, mv_def, str(err)))
                
        if len(still_pending_mv) == len(pending_matviews):
            for s, m, fv, vd, err_msg in still_pending_mv:
                print(f"  [!] Advertencia: No se pudo crear Vista Materializada {fv}: {err_msg.splitlines()[0]}")
            break
        pending_matviews = [(s, m, fv, vd) for s, m, fv, vd, _ in still_pending_mv]

    # Sincronizar secuencias
    for s_schema, s_name in sequences:
        q_name = f'"{s_schema}"."{s_name}"'
        try:
            cur_src.execute(f"SELECT last_value, is_called FROM {q_name};")
            last_val, is_called = cur_src.fetchone()
            cur_dst.execute(f"SELECT setval('{q_name}', %s, %s);", (last_val, is_called))
            conn_dst.commit()
        except Exception:
            pass

    cur_src.close()
    cur_dst.close()
    conn_src.close()
    conn_dst.close()
    print(f"\n[OK] Migracion completada exitosamente para la base de datos: {dbname}\n")

def main():
    print("==========================================================")
    print(" SCRIPT DE MIGRACIÓN COMPLETA DE POSTGRESQL (SADE & GEO)  ")
    print("==========================================================")
    print(f"Origen:  {ORIGEN_CONFIG['host']}:{ORIGEN_CONFIG['port']}")
    print(f"Destino: {DESTINO_CONFIG['host']}:{DESTINO_CONFIG['port']}")
    print("Bases a migrar:", ", ".join(DATABASES_TO_MIGRATE))
    print("----------------------------------------------------------\n")
    
    try:
        c_src = get_connection(ORIGEN_CONFIG, "postgres")
        c_src.close()
        print("[+] Conexión con servidor Origen (Local) OK.")
    except Exception as e:
        print(f"[!] Error al conectar con el PostgreSQL Origen: {e}")
        sys.exit(1)

    try:
        c_dst = get_connection(DESTINO_CONFIG, "postgres")
        c_dst.close()
        print("[+] Conexión con servidor Destino (10.78.33.238) OK.")
        for db in DATABASES_TO_MIGRATE:
            migrar_base_datos(db)
    except Exception as e:
        print(f"\n[!] ATENCIÓN: No se pudo conectar al servidor destino (10.78.33.238):")
        print(f"    {e}")

if __name__ == "__main__":
    main()
