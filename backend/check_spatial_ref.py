import os
from sqlalchemy import create_engine, text

def check_spatial():
    pdi_engine = create_engine('postgresql://postgres:lenovo@10.10.8.207:5432/geodb')
    with pdi_engine.connect() as conn:
        print("Buscando en PDI geodb...")
        rows = conn.execute(text("""
            SELECT srid, auth_name, auth_srid, srtext, proj4text 
            FROM spatial_ref_sys 
            WHERE srtext ILIKE '%buenos aires%' OR proj4text ILIKE '%x_0=100000%' OR srid IN (22186, 98207, 102160, 2088)
        """)).fetchall()
        for r in rows:
            print(f"SRID: {r[0]} | Auth: {r[1]} {r[2]} | Proj4: {r[4]}")
            print(f"  srtext: {r[3][:120]}...")

    local_engine = create_engine('postgresql://postgres:lenovo@localhost:5432/geo-mdr')
    with local_engine.connect() as conn:
        print("\nBuscando en Local geo-mdr...")
        rows = conn.execute(text("""
            SELECT srid, auth_name, auth_srid, proj4text 
            FROM spatial_ref_sys 
            WHERE srid IN (22186, 98207, 102160, 2088) OR proj4text ILIKE '%x_0=100000%'
        """)).fetchall()
        for r in rows:
            print(f"SRID: {r[0]} | Auth: {r[1]} {r[2]} | Proj4: {r[3]}")

if __name__ == '__main__':
    check_spatial()
