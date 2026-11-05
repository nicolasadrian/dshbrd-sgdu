import os
from sqlalchemy import create_engine, text

def inspect_pdi():
    pdi_url = os.getenv('PDI_DATABASE_URL') or 'postgresql://postgres:lenovo@10.10.8.207:5432/geodb'
    print(f"Probando conexion a PDI: {pdi_url}")
    try:
        engine = create_engine(pdi_url, connect_args={'connect_timeout': 5})
        with engine.connect() as conn:
            print("Conexion exitosa a PDI geodb!")
            tables = ['cur_parcelas', 'mo_parcelasmap', 'cur_manzanasatipicas', 'mo_manzanasmap', 'frentesparcelas', 'cur_objetosterritoriales']
            for t in tables:
                r = conn.execute(text("""
                    SELECT t.table_schema, t.table_name, c.column_name, c.udt_name
                    FROM information_schema.tables t
                    LEFT JOIN information_schema.columns c 
                      ON t.table_schema = c.table_schema AND t.table_name = c.table_name 
                      AND (c.udt_name = 'geometry' OR c.column_name IN ('geom', 'geometry', 'the_geom'))
                    WHERE t.table_name = :t
                """), {'t': t}).fetchall()
                if r:
                    for row in r:
                        schema = row[0]
                        tbl = row[1]
                        geom_col = row[2]
                        srid_info = None
                        count = conn.execute(text(f"SELECT count(*) FROM {schema}.{tbl}")).scalar()
                        if geom_col:
                            try:
                                srid_info = conn.execute(text(f"SELECT ST_SRID({geom_col}), GeometryType({geom_col}) FROM {schema}.{tbl} WHERE {geom_col} IS NOT NULL LIMIT 1")).fetchone()
                            except Exception as ex:
                                srid_info = f"Error SRID: {ex}"
                        print(f"Tabla: {schema}.{tbl} | Filas: {count} | Geom: {geom_col} | SRID: {srid_info}")
                else:
                    print(f"Tabla {t}: NO ENCONTRADA")
    except Exception as e:
        print(f"Error conectando a PDI: {e}")

if __name__ == '__main__':
    inspect_pdi()
