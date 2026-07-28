import os
import sys
import time
import logging
from collections import defaultdict
import oracledb
from sqlalchemy import text
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('import_df_form_comp_value.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("importador")

# Cargar variables de entorno
load_dotenv()

# Configuración de base de datos Postgres (usamos la misma lógica del backend)
from database import engine

def main():
    logger.info("Iniciando proceso de importación de df_form_comp_value...")

    # 1. Conexión a Oracle
    oracle_user = os.getenv("ORACLE_USER", "CDASILVACOSTA")
    oracle_pass = os.getenv("ORACLE_PASS", "SUI_sie329(m")
    oracle_dsn = os.getenv("ORACLE_DSN", "ind01-scan1.gcba.gob.ar:1521/sadetst.gcba.gob.ar")

    try:
        # Configurar oracledb para que traiga LOBs como strings/bytes automáticamente
        oracledb.defaults.fetch_lobs = False
        oracle_conn = oracledb.connect(user=oracle_user, password=oracle_pass, dsn=oracle_dsn)
        logger.info("Conexión a base de datos Oracle establecida.")
    except Exception as e:
        logger.error(f"Error al conectar con Oracle: {e}")
        sys.exit(1)

    # 2. Conectar a Postgres y crear la tabla de control si no existe
    try:
        postgres_conn = engine.raw_connection()
        pg_cursor = postgres_conn.cursor()
        
        # Crear tabla de control
        pg_cursor.execute("""
            CREATE TABLE IF NOT EXISTS public.control_importacion_transacciones (
                id_transaction BIGINT PRIMARY KEY,
                fecha_importacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        postgres_conn.commit()
        logger.info("Tabla de control 'control_importacion_transacciones' verificada/creada en Postgres.")
    except Exception as e:
        logger.error(f"Error al conectar/inicializar Postgres: {e}")
        oracle_conn.close()
        sys.exit(1)

    # 3. Obtener transacciones pendientes
    try:
        logger.info("Buscando transacciones asociadas a documentos IFOCD en 2022, 2023, 2024, 2025 y 2026...")
        # Buscamos trx_gedo y trx_ee que estén en los años 2022-2026 para IFOCD, y que no estén ya en la tabla de control.
        query_pendientes = """
            SELECT DISTINCT id_transaction 
            FROM (
                SELECT trx_gedo AS id_transaction FROM public.mvw_datos_gedo_secgdu 
                WHERE acronimo = 'IFOCD' AND EXTRACT(YEAR FROM fecha_asociacion) IN (2022, 2023, 2024, 2025, 2026) AND trx_gedo IS NOT NULL
                UNION
                SELECT trx_ee AS id_transaction FROM public.mvw_datos_gedo_secgdu 
                WHERE acronimo = 'IFOCD' AND EXTRACT(YEAR FROM fecha_asociacion) IN (2022, 2023, 2024, 2025, 2026) AND trx_ee IS NOT NULL
                UNION
                SELECT trx_tad AS id_transaction FROM public.mvw_datos_gedo_secgdu 
                WHERE acronimo = 'IFOCD' AND EXTRACT(YEAR FROM fecha_asociacion) IN (2022, 2023, 2024, 2025, 2026) AND trx_tad IS NOT NULL
            ) t
            WHERE NOT EXISTS (
                SELECT 1 FROM public.control_importacion_transacciones c 
                WHERE c.id_transaction = t.id_transaction
            );
        """
        pg_cursor.execute(query_pendientes)
        pendientes = [row[0] for row in pg_cursor.fetchall()]
        logger.info(f"Se encontraron {len(pendientes)} transacciones pendientes de importación.")
    except Exception as e:
        logger.error(f"Error al buscar transacciones pendientes en Postgres: {e}")
        oracle_conn.close()
        postgres_conn.close()
        sys.exit(1)

    if not pendientes:
        logger.info("No hay transacciones pendientes para importar. Finalizando.")
        oracle_conn.close()
        postgres_conn.close()
        return

    # 4. Procesar en lotes/batches (ej. de 500 IDs para evitar límites en la cláusula IN)
    batch_size = 500
    total_lotes = (len(pendientes) + batch_size - 1) // batch_size
    oracle_cursor = oracle_conn.cursor()

    logger.info(f"Comenzando procesamiento en {total_lotes} lotes de hasta {batch_size} IDs.")

    for i in range(total_lotes):
        lote_ids = pendientes[i * batch_size : (i + 1) * batch_size]
        logger.info(f"Procesando lote {i + 1}/{total_lotes} (IDs: {len(lote_ids)})")

        try:
            # Consultar en Oracle
            # Generar placeholders para la cláusula IN de Oracle (:1, :2, ...)
            placeholders = ", ".join([f":{k+1}" for k in range(len(lote_ids))])
            query_oracle = f"""
                SELECT ID, ID_TRANSACTION, ID_FORM_COMPONENT, VALUE_STR, VALUE_INT, VALUE_DATE, VALUE_DOUBLE, VALUE_BOOLEAN, INPUT_NAME, VALUE_BLOB, ORDER_VALUE
                FROM EE_SADE.DF_FORM_COMP_VALUE
                WHERE ID_TRANSACTION IN ({placeholders})
            """
            oracle_cursor.execute(query_oracle, lote_ids)
            filas_oracle = oracle_cursor.fetchall()
            
            logger.info(f"Oracle retornó {len(filas_oracle)} filas para este lote.")

            # Insertar en Postgres
            if filas_oracle:
                # Usamos executemany para inserción masiva eficiente
                insert_query = """
                    INSERT INTO public.df_form_comp_value (
                        id, id_transaction, id_form_component, value_str, value_int, 
                        value_date, value_double, value_boolean, input_name, value_blob, order_value
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                # Convertir posibles tipos incompatibles o LOBs y sanitizar caracteres NUL (\x00)
                processed_rows = []
                for row in filas_oracle:
                    processed_row = tuple(
                        (cell.replace('\x00', '') if isinstance(cell, str) else cell)
                        for cell in row
                    )
                    processed_rows.append(processed_row)

                pg_cursor.executemany(insert_query, processed_rows)
                logger.info(f"Insertadas {len(filas_oracle)} filas en Postgres.")

            # Marcar como importados en la tabla de control
            control_query = """
                INSERT INTO public.control_importacion_transacciones (id_transaction)
                VALUES (%s)
                ON CONFLICT (id_transaction) DO NOTHING
            """
            pg_cursor.executemany(control_query, [(val,) for val in lote_ids])

            # Hacer commit de este lote
            postgres_conn.commit()
            logger.info(f"Lote {i + 1} completado y comiteado con éxito.")

        except Exception as batch_error:
            postgres_conn.rollback()
            logger.error(f"Error procesando el lote {i + 1}: {batch_error}")
            # Continuar con el siguiente lote en vez de abortar todo, o frenar según preferencia
            continue

    # 5. Cerrar conexiones
    oracle_cursor.close()
    oracle_conn.close()
    pg_cursor.close()
    postgres_conn.close()
    logger.info("Proceso de importación finalizado con éxito.")

if __name__ == "__main__":
    main()
