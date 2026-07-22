import os
import re
import sys
import json
import logging
import psycopg2
from collections import defaultdict
from sqlalchemy import text
from database import engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('create_pivoted_tables.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("creador_pivotes")

# Cargar la configuración de los campos del análisis anterior
ANALYSIS_PATH = "scratch/pivot_fields_analysis.json"

def sanitize_column_name(name):
    if not name:
        return "empty_col"
    s = name.strip().lower()
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ñ': 'n', 'ü': 'u', 'ä': 'a', 'ö': 'o', 'ë': 'e'
    }
    for char, replacement in replacements.items():
        s = s.replace(char, replacement)
    s = re.sub(r'[^a-z0-9_]', '_', s)
    s = re.sub(r'_+', '_', s)
    s = s.strip('_')
    if not s:
        return "empty_col"
    if s[0].isdigit():
        s = "col_" + s
    return s[:60]

def main():
    logger.info("Iniciando creación de tablas pivoteadas...")
    
    if not os.path.exists(ANALYSIS_PATH):
        logger.error(f"No se encontró el archivo de análisis en {ANALYSIS_PATH}. Ejecuta primero el análisis de campos.")
        sys.exit(1)
        
    with open(ANALYSIS_PATH, "r", encoding="utf-8") as f:
        fields_config = json.load(f)
        
    postgres_conn = engine.raw_connection()
    pg_cursor = postgres_conn.cursor()
    
    # Desactivar el timeout de sentencias para la conexión cruda
    pg_cursor.execute("SET statement_timeout = 0;")
    
    acronimos = [
        "IFOCD", "IFPDO", "PROIN", "PLINE", "IFSMC", "IFROC", "IFSMI", "IFDEX", 
        "CECNU", "IFGPA", "FIPAR", "IFPCB", "IFPCO", "IFTPT", "IFPEO", "IFCIS", "IFRSP",
        "IFCAO", "IFCFP", "IFCAC"
    ]
    
    gerencias = ["morfologia", "usos", "aph"]
    
    targets = [(acr, "acronimo", acr) for acr in acronimos] + [(ger, "gerencia", ger) for ger in gerencias]
    
    for name, target_type, value in targets:
        table_name = f"gedo_{name.lower()}_datos"
        logger.info(f"\n==========================================")
        logger.info(f"Procesando: {name} (Tipo: {target_type}) -> Tabla: {table_name}")
        logger.info(f"==========================================")
        
        fields_to_use = []
        if target_type == "gerencia":
            logger.info(f"Obteniendo campos únicos para gerencia {name} desde Postgres...")
            view_name = f"mv_{name}_gedos_egreso"
            query_fields = f"""
                SELECT DISTINCT val.input_name
                FROM public.df_form_comp_value val
                WHERE val.id_transaction IN (
                    SELECT DISTINCT id_transaction 
                    FROM (
                        SELECT trx_gedo AS id_transaction FROM public.mvw_datos_gedo_secgdu 
                        WHERE id_expediente IN (SELECT id_expediente FROM public.{view_name}) AND trx_gedo IS NOT NULL
                        UNION
                        SELECT trx_ee AS id_transaction FROM public.mvw_datos_gedo_secgdu 
                        WHERE id_expediente IN (SELECT id_expediente FROM public.{view_name}) AND trx_ee IS NOT NULL
                        UNION
                        SELECT trx_tad AS id_transaction FROM public.mvw_datos_gedo_secgdu 
                        WHERE id_expediente IN (SELECT id_expediente FROM public.{view_name}) AND trx_tad IS NOT NULL
                    ) sub
                ) AND val.input_name IS NOT NULL AND val.input_name <> '';
            """
            pg_cursor.execute(query_fields)
            fields_to_use = [{'input_name': row[0], 'type': 'TEXT'} for row in pg_cursor.fetchall()]
        else:
            fields_to_use = fields_config.get(value, [])
            
        if not fields_to_use:
            logger.warning(f"No se encontraron campos de formulario para {name}. Se creará la tabla solo con metadatos.")
            
        seen_cols = {}
        columns_def = []
        metadata_cols = [
            ("id_expediente", "BIGINT"),
            ("expediente", "TEXT"),
            ("documento", "TEXT"),
            ("usuario_creador", "TEXT"),
            ("motivo", "TEXT"),
            ("usuario_asociador", "TEXT"),
            ("fecha_creacion", "TIMESTAMP WITHOUT TIME ZONE"),
            ("fecha_asociacion", "TIMESTAMP WITHOUT TIME ZONE"),
            ("acronimo", "TEXT"),
            ("trx_gedo", "BIGINT"),
            ("trx_ee", "BIGINT"),
            ("trx_tad", "BIGINT"),
            ("trx_cv_tad", "BIGINT")
        ]
        
        for col_name, col_type in metadata_cols:
            seen_cols[col_name] = col_name
            columns_def.append(f"{col_name} {col_type}")
            
        pivot_mapping = {}
        for field in fields_to_use:
            input_name = field['input_name']
            san_name = sanitize_column_name(input_name)
            
            orig_san = san_name
            counter = 2
            while san_name in seen_cols:
                san_name = f"{orig_san}_{counter}"
                counter += 1
                
            seen_cols[san_name] = input_name
            pivot_mapping[input_name] = san_name
            
            t_type = field.get('type', 'TEXT')
            sql_type = "TEXT"
            if t_type == "INT":
                sql_type = "DOUBLE PRECISION"
            elif t_type == "DATE":
                sql_type = "TIMESTAMP WITHOUT TIME ZONE"
            elif t_type == "BOOL":
                sql_type = "BOOLEAN"
            elif t_type == "DOUBLE":
                sql_type = "DOUBLE PRECISION"
                
            columns_def.append(f"{san_name} {sql_type}")
            
        logger.info("Creando la tabla en Postgres...")
        pg_cursor.execute(f"DROP TABLE IF EXISTS public.{table_name};")
        create_sql = f"CREATE TABLE public.{table_name} (\n    " + ",\n    ".join(columns_def) + "\n);"
        pg_cursor.execute(create_sql)
        postgres_conn.commit()
        logger.info(f"Tabla public.{table_name} creada exitosamente.")
        
        logger.info("Obteniendo registros de origen...")
        if target_type == "gerencia":
            view_name = f"mv_{name}_gedos_egreso"
            query_source = f"""
                SELECT DISTINCT g.id_expediente, g.expediente, g.documento, g.usuario_creador, g.motivo, 
                       g.usuario_asociador, g.fecha_creacion, g.fecha_asociacion, g.acronimo, 
                       g.trx_gedo, g.trx_ee, g.trx_tad, g.trx_cv_tad
                FROM public.mvw_datos_gedo_secgdu g
                WHERE g.id_expediente IN (SELECT id_expediente FROM public.{view_name});
            """
        else:
            query_source = """
                SELECT id_expediente, expediente, documento, usuario_creador, motivo, 
                       usuario_asociador, fecha_creacion, fecha_asociacion, acronimo, 
                       trx_gedo, trx_ee, trx_tad, trx_cv_tad
                FROM public.mvw_datos_gedo_secgdu
                WHERE acronimo = %s;
            """
            
        if target_type == "gerencia":
            pg_cursor.execute(query_source)
        else:
            pg_cursor.execute(query_source, (value,))
            
        source_rows = pg_cursor.fetchall()
        logger.info(f"Se encontraron {len(source_rows):,} registros de origen.")
        
        if not source_rows:
            logger.info("No hay registros de origen para procesar.")
            continue
            
        logger.info("Pivotando y cargando registros...")
        batch_size = 1000
        for b_idx in range(0, len(source_rows), batch_size):
            batch_rows = source_rows[b_idx:b_idx+batch_size]
            
            tx_ids = []
            for r in batch_rows:
                if r[9]: tx_ids.append(r[9])   # trx_gedo
                if r[10]: tx_ids.append(r[10]) # trx_ee
                if r[11]: tx_ids.append(r[11]) # trx_tad
                if r[12]: tx_ids.append(int(r[12])) # trx_cv_tad
                
            tx_ids = list(set(tx_ids))
            values_map = defaultdict(dict)
            
            if tx_ids:
                placeholders = ", ".join(["%s"] * len(tx_ids))
                query_values = f"""
                    SELECT id_transaction, input_name, value_str, value_int, value_date, value_double, value_boolean
                    FROM public.df_form_comp_value
                    WHERE id_transaction IN ({placeholders});
                """
                pg_cursor.execute(query_values, tx_ids)
                for val_row in pg_cursor.fetchall():
                    tx_id = val_row[0]
                    input_name = val_row[1]
                    
                    val = None
                    if val_row[2] is not None and val_row[2] != '':
                        val = val_row[2]
                    elif val_row[3] is not None:
                        val = val_row[3]
                    elif val_row[4] is not None:
                        val = val_row[4]
                    elif val_row[5] is not None:
                        val = val_row[5]
                    elif val_row[6] is not None:
                        val = val_row[6]
                        
                    if val is not None:
                        values_map[tx_id][input_name] = val
                        
            insert_rows = []
            for r in batch_rows:
                row_data = list(r)
                
                merged_values = {}
                for tx_col in [9, 10, 11, 12]:
                    tx_id = r[tx_col]
                    if tx_id in values_map:
                        merged_values.update(values_map[tx_id])
                        
                for field in fields_to_use:
                    input_name = field['input_name']
                    val = merged_values.get(input_name, None)
                    
                    t_type = field.get('type', 'TEXT')
                    if val is not None:
                        if t_type == 'BOOL':
                            s_val = str(val).strip().lower()
                            if s_val in ['si', 's', 'true', '1', 'yes', 'y', 't', 'verdadero']:
                                val = True
                            else:
                                val = False
                        elif t_type in ['INT', 'DOUBLE']:
                            try:
                                val = float(val)
                            except ValueError:
                                val = None
                    row_data.append(val)
                    
                insert_rows.append(tuple(row_data))
                
            if insert_rows:
                placeholders = ", ".join(["%s"] * len(row_data))
                cols_names = [col[0] for col in metadata_cols] + [pivot_mapping[f['input_name']] for f in fields_to_use]
                cols_str = ", ".join(cols_names)
                
                insert_query = f"INSERT INTO public.{table_name} ({cols_str}) VALUES ({placeholders})"
                pg_cursor.executemany(insert_query, insert_rows)
                postgres_conn.commit()
                
            sys.stdout.write(f"\r    Progreso: {min(b_idx+batch_size, len(source_rows)):,} / {len(source_rows):,} cargados")
            sys.stdout.flush()
            
        logger.info(f"\n[OK] Carga completada para tabla {table_name}.")
        
    pg_cursor.close()
    postgres_conn.close()
    logger.info("\nProceso de generación de tablas pivote finalizado exitosamente.")

if __name__ == "__main__":
    main()
