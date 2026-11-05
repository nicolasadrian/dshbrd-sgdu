import os
from sqlalchemy import create_engine, text

def setup_pdi_prima():
    local_base = (os.getenv('DATABASE_URL_LOCAL') or 'postgresql://postgres:lenovo@localhost:5432/sade_db').rsplit('/', 1)[0]
    postgres_url = f"{local_base}/postgres"
    print(f"Conectando a postgres default: {postgres_url}")
    
    engine = create_engine(postgres_url, isolation_level='AUTOCOMMIT')
    with engine.connect() as conn:
        dbs = [r[0] for r in conn.execute(text("SELECT datname FROM pg_database")).fetchall()]
        print(f"Bases existentes: {dbs}")
        if 'pdi-prima' not in dbs:
            conn.execute(text('CREATE DATABASE "pdi-prima"'))
            print("Base de datos 'pdi-prima' creada exitosamente.")
        else:
            print("Base 'pdi-prima' ya existe.")

    # Conectar a pdi-prima
    prima_url = f"{local_base}/pdi-prima"
    print(f"Configurando extensiones y schema en: {prima_url}")
    prima_engine = create_engine(prima_url)
    with prima_engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS geodb;"))
        
        # Insertar SRID 98207 / 102160 para GKBA si no existe
        conn.execute(text("""
            INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text)
            SELECT 98207, 'GCABA', 98207, 
                   'PROJCS["Buenos_Aires_GCBA",GEOGCS["GCS_Campo_Inchauspe",DATUM["D_Campo_Inchauspe",SPHEROID["International_1924",6378388.0,297.0]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",100000.0],PARAMETER["False_Northing",100000.0],PARAMETER["Central_Meridian",-58.4627],PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",-34.6297166],UNIT["Meter",1.0]]',
                   '+proj=tmerc +lat_0=-34.6297166 +lon_0=-58.4627 +k=0.9996 +x_0=100000 +y_0=100000 +ellps=intl +units=m +no_defs'
            WHERE NOT EXISTS (SELECT 1 FROM spatial_ref_sys WHERE srid = 98207);
        """))
        print("Schema 'geodb' y PostGIS configurados en 'pdi-prima'.")

if __name__ == '__main__':
    setup_pdi_prima()
