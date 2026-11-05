import os
from sqlalchemy import create_engine, text

def inspect_coords():
    pdi_url = os.getenv('PDI_DATABASE_URL') or 'postgresql://postgres:lenovo@10.10.8.207:5432/geodb'
    engine = create_engine(pdi_url)
    with engine.connect() as conn:
        tables = [
            ('public', 'cur_parcelas'),
            ('public', 'mo_parcelasmap'),
            ('actualizaciones', 'mo_parcelasmap'),
            ('public', 'cur_manzanasatipicas'),
            ('public', 'mo_manzanasmap'),
            ('public', 'frentesparcelas'),
            ('public', 'cur_objetosterritoriales')
        ]
        for sch, tbl in tables:
            r = conn.execute(text(f"""
                SELECT ST_AsText(ST_Centroid(the_geom)), 
                       ST_XMin(the_geom), ST_YMin(the_geom), 
                       ST_XMax(the_geom), ST_YMax(the_geom)
                FROM {sch}.{tbl}
                WHERE the_geom IS NOT NULL
                LIMIT 1
            """)).fetchone()
            print(f"{sch}.{tbl} -> Centroid: {r[0]} | BBOX: [{r[1]:.2f}, {r[2]:.2f}, {r[3]:.2f}, {r[4]:.2f}]")

if __name__ == '__main__':
    inspect_coords()
