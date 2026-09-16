import os
import pandas as pd
from sqlalchemy import text
from database import get_geo_mdr_engine

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1qkfkG_jP22zPh1DegPe70emPsShAcu_vjvCYNCZYhw4/export?format=csv&gid=413969321"
TABLE_NAME = "seguimiento_catastro_pdi"

COLUMN_MAPPING = {
    0: "marca_temporal",
    1: "fecha",
    2: "mensura",
    3: "expediente",
    4: "tipo",
    5: "smp_origen",
    6: "smp_surgente",
    7: "if_registro",
    8: "registro",
    9: "proceso_cartografia",
    10: "constitucion",
    11: "ficha_parcelaria",
    12: "shape_parcelas",
    13: "tad",
    14: "ciudad_3d"
}

def import_data():
    print(f"Descargando datos desde Google Sheets...")
    # Leer primeras 15 columnas (A a O)
    df = pd.read_csv(SPREADSHEET_URL, encoding="utf-8").iloc[:, :15]
    
    # Renombrar columnas según el mapeo
    df.columns = [COLUMN_MAPPING[i] for i in range(len(df.columns))]
    
    # Limpiar strings (quitar espacios en blanco al inicio/final) y reemplazar NaN por None
    for col in df.columns:
        df[col] = df[col].apply(lambda x: str(x).strip() if pd.notnull(x) and str(x).strip() != "" else None)
    
    # Filtrar filas totalmente vacías
    df = df.dropna(how="all")
    
    print(f"Filas a insertar: {len(df)}")
    
    engine = get_geo_mdr_engine()
    
    with engine.begin() as conn:
        print(f"Creando tabla '{TABLE_NAME}' si no existe...")
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id SERIAL PRIMARY KEY,
                marca_temporal TEXT,
                fecha TEXT,
                mensura TEXT,
                expediente TEXT,
                tipo TEXT,
                smp_origen TEXT,
                smp_surgente TEXT,
                if_registro TEXT,
                registro TEXT,
                proceso_cartografia TEXT,
                constitucion TEXT,
                ficha_parcelaria TEXT,
                shape_parcelas TEXT,
                tad TEXT,
                ciudad_3d TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Opcional: truncar si se vuelve a correr
        conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME} RESTART IDENTITY;"))
        
        # Insertar registros
        cols = list(COLUMN_MAPPING.values())
        col_names = ", ".join(cols)
        placeholders = ", ".join([f":{c}" for c in cols])
        insert_sql = text(f"INSERT INTO {TABLE_NAME} ({col_names}) VALUES ({placeholders})")
        
        records = df.to_dict(orient="records")
        conn.execute(insert_sql, records)
        
        count = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME};")).scalar()
        print(f"Éxito! Total de registros en {TABLE_NAME}: {count}")

if __name__ == "__main__":
    import_data()
