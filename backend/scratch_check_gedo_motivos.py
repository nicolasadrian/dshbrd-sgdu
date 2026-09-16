import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== MOTIVOS EN GEDO PARA MDUG0134N ===")
    r = conn.execute(text("""
        SELECT d.motivo, d.acronimo, count(*)
        FROM mvw_datos_gedo_secgdu d
        JOIN mv_catastro_universo u ON u.id_expediente = d.id_expediente
        WHERE u.trata = 'MDUG0134N' AND d.acronimo IN ('IFGPA', 'FIPAR')
        GROUP BY d.motivo, d.acronimo
        ORDER BY count(*) DESC
        LIMIT 25
    """)).mappings().fetchall()
    for row in r:
        print(dict(row))

    print("\n=== CONTEO TOTAL DE GEDOS SEGUN MOTIVO EN GEDO ===")
    r_gedo_filter = conn.execute(text("""
        SELECT 
            count(DISTINCT u.id_expediente) as total,
            count(DISTINCT CASE WHEN d.motivo ~* 'constituc|certific' THEN u.id_expediente END) as con_motivo_en_gedo
        FROM mvw_datos_gedo_secgdu d
        JOIN mv_catastro_universo u ON u.id_expediente = d.id_expediente
        WHERE u.trata = 'MDUG0134N' AND d.acronimo IN ('IFGPA', 'FIPAR')
    """)).mappings().first()
    print("Filtro por motivo en mvw_datos_gedo_secgdu:", dict(r_gedo_filter))
