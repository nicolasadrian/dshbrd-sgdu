import os
import io
import time
from sqlalchemy import create_engine, text

def copy_table_to_local(pdi_engine, local_engine, src_schema, src_table, dst_schema, dst_table, geom_srid=98207):
    print(f"\n=======================================================")
    print(f"Copiando {src_schema}.{src_table} -> {dst_schema}.{dst_table} (SRID {geom_srid})")
    print(f"=======================================================")
    
    t0 = time.time()
    
    # 1. Obtener columnas de origen
    with pdi_engine.connect() as conn:
        cols_info = conn.execute(text(f"""
            SELECT column_name, data_type, udt_name, is_nullable
            FROM information_schema.columns 
            WHERE table_schema = '{src_schema}' AND table_name = '{src_table}'
            ORDER BY ordinal_position
        """)).fetchall()

    if not cols_info:
        print(f"Error: No se encontraron columnas para {src_schema}.{src_table}")
        return

    col_names = [c[0] for c in cols_info]
    geom_cols = [c[0] for c in cols_info if c[2] == 'geometry' or c[0] in ('the_geom', 'geom', 'geometry')]

    print(f"Total columnas: {len(col_names)}. Columnas geométricas: {geom_cols}")

    # 2. Crear tabla en local_engine
    col_defs = []
    select_parts = []
    
    for c in cols_info:
        c_name = c[0]
        c_type = c[1]
        c_udt = c[2]

        if c_name in geom_cols:
            # Obtener tipo geométrico desde origen
            with pdi_engine.connect() as conn:
                g_type = conn.execute(text(f"""
                    SELECT GeometryType({c_name}) 
                    FROM {src_schema}.{src_table} 
                    WHERE {c_name} IS NOT NULL 
                    LIMIT 1
                """)).scalar() or 'GEOMETRY'

            col_defs.append(f'"{c_name}" geometry({g_type}, {geom_srid})')
            # En el select, exportamos como WKB binario (HEX) o EWKT asignando el SRID deseado
            select_parts.append(f'encode(ST_AsBinary(ST_SetSRID({c_name}, {geom_srid})), \'hex\') AS "{c_name}"')
        else:
            # Tipos compatibles
            if c_udt in ('int4', 'serial'):
                dtype = 'INTEGER'
            elif c_udt in ('int8', 'bigserial'):
                dtype = 'BIGINT'
            elif c_udt in ('int2',):
                dtype = 'SMALLINT'
            elif c_udt in ('float4', 'float8', 'numeric'):
                dtype = 'NUMERIC'
            elif c_udt in ('bool',):
                dtype = 'BOOLEAN'
            elif c_udt in ('date',):
                dtype = 'DATE'
            elif c_udt in ('timestamp', 'timestamptz'):
                dtype = 'TIMESTAMP'
            elif c_udt in ('text',):
                dtype = 'TEXT'
            else:
                dtype = 'TEXT'
            
            col_defs.append(f'"{c_name}" {dtype}')
            select_parts.append(f'"{c_name}"')

    create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {dst_schema}.{dst_table} (
            {', '.join(col_defs)}
        );
        TRUNCATE TABLE {dst_schema}.{dst_table};
    """

    with local_engine.begin() as conn:
        conn.execute(text(create_table_sql))
        print(f"Tabla {dst_schema}.{dst_table} creada / truncada exitosamente.")

    # 3. Extraer e insertar en lotes usando COPY o raw_connection
    src_conn = pdi_engine.connect()
    
    total_count = src_conn.execute(text(f"SELECT count(*) FROM {src_schema}.{src_table}")).scalar()
    print(f"Total registros a transferir: {total_count}")

    if total_count == 0:
        src_conn.close()
        return

    # Usar cursor del lado del servidor para no cargar 300k filas en memoria
    batch_size = 20000
    select_query = f"SELECT {', '.join(select_parts)} FROM {src_schema}.{src_table}"
    
    # Conexión local psycopg2 para COPY rápido
    raw_local = local_engine.raw_connection()
    cursor_local = raw_local.cursor()
    
    # Cursor PDI con streaming
    dbapi_src = pdi_engine.raw_connection()
    src_cur = dbapi_src.cursor(name='pdi_fetch_cursor')
    src_cur.itersize = batch_size
    src_cur.execute(select_query)

    copied = 0
    buffer = io.StringIO()

    while True:
        rows = src_cur.fetchmany(batch_size)
        if not rows:
            break
        
        buffer.seek(0)
        buffer.truncate(0)

        for row in rows:
            line_parts = []
            for idx, val in enumerate(row):
                if val is None:
                    line_parts.append(r'\N')
                else:
                    col_name = col_names[idx]
                    if col_name in geom_cols:
                        # WKB Hex string
                        line_parts.append(str(val))
                    else:
                        s_val = str(val).replace('\\', '\\\\').replace('\t', ' ').replace('\n', ' ').replace('\r', '')
                        line_parts.append(s_val)
            buffer.write('\t'.join(line_parts) + '\n')

        buffer.seek(0)
        copy_sql = f"COPY {dst_schema}.{dst_table} FROM STDIN WITH (FORMAT text, NULL '\\N')"
        cursor_local.copy_expert(copy_sql, buffer)
        raw_local.commit()
        
        copied += len(rows)
        print(f"  Transferidos: {copied}/{total_count} ({(time.time()-t0):.1f}s)")

    src_cur.close()
    dbapi_src.close()
    cursor_local.close()
    raw_local.close()

    # 4. Crear índice espacial
    with local_engine.begin() as conn:
        for g in geom_cols:
            idx_name = f"idx_{dst_table}_{g}"
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {dst_schema}.{dst_table} USING GIST (\"{g}\");"))
            print(f"Índice espacial GIST creado en \"{g}\".")

    print(f"Completado {dst_schema}.{dst_table} en {(time.time()-t0):.1f}s.")

def main():
    pdi_url = os.getenv('PDI_DATABASE_URL') or 'postgresql://postgres:lenovo@10.10.8.207:5432/geodb'
    local_url = 'postgresql://postgres:lenovo@localhost:5432/pdi-prima'

    print(f"Origen: {pdi_url}")
    print(f"Destino: {local_url}")

    pdi_engine = create_engine(pdi_url)
    local_engine = create_engine(local_url)

    # Las 6 tablas requeridas:
    # cur_parcelas, mo_parcelasmap, cur_manzanasatipicas, mo_manzanasmap, frentesparcelas, cur_objetosterritoriales
    tables_to_copy = [
        ('public', 'cur_objetosterritoriales', 'geodb', 'cur_objetosterritoriales'),
        ('public', 'cur_manzanasatipicas', 'geodb', 'cur_manzanasatipicas'),
        ('public', 'mo_manzanasmap', 'geodb', 'mo_manzanasmap'),
        ('public', 'frentesparcelas', 'geodb', 'frentesparcelas'),
        ('public', 'cur_parcelas', 'geodb', 'cur_parcelas'),
        ('public', 'mo_parcelasmap', 'geodb', 'mo_parcelasmap'),
    ]

    for src_sch, src_tbl, dst_sch, dst_tbl in tables_to_copy:
        copy_table_to_local(pdi_engine, local_engine, src_sch, src_tbl, dst_sch, dst_tbl, geom_srid=98207)

    print("\n=======================================================")
    print("TODAS LAS TABLAS HAN SIDO COPIADAS EXITOSAMENTE EN pdi-prima.geodb")
    print("=======================================================")

if __name__ == '__main__':
    main()
