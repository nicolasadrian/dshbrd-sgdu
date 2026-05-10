import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text
import sys
import os

# Configuración
DB_CONFIG = {
    "host": "localhost",
    "user": "postgres",
    "pass": "lenovo",
    "port": 5432,
    "dbname": "sade_db"
}

def run_sql_file(file_path):
    if not os.path.exists(file_path):
        print(f"Error: No se encuentra el archivo {file_path}")
        return

    # Crear carpeta de resultados si no existe
    if not os.path.exists('results'):
        os.makedirs('results')

    engine = create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['pass']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            query = f.read()
        
        print(f"\nEjecutando: {os.path.basename(file_path)}...")
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        
        if df.empty:
            print("La consulta no devolvió resultados.")
        else:
            # Mostrar en pantalla
            print("\nResultados (primeras 20 filas):")
            print(df.head(20).to_string(index=False))
            
            # Exportar a CSV
            base_name = os.path.basename(file_path).replace('.sql', '')
            output_file = f"results/{base_name}_resultado.csv"
            df.to_csv(output_file, index=False, sep=';', encoding='utf-8-sig')
            print(f"\n[✓] Archivo exportado exitosamente a: {output_file}")
            
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python run_query.py queries/archivo.sql")
    else:
        run_sql_file(sys.argv[1])
