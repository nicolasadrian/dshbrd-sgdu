import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== CRUCE DE MOTIVOS EN PASES PARA MDUG0134N ===")
    r = conn.execute(text("""
        SELECT 
            count(DISTINCT u.id_expediente) as total_egresos_actuales,
            count(DISTINCT CASE WHEN p.motivo ~* 'constituc|certific' THEN u.id_expediente END) as con_motivo_en_pases,
            count(DISTINCT CASE WHEN p.motivo ~* 'constituc' THEN u.id_expediente END) as motivo_constitucion,
            count(DISTINCT CASE WHEN p.motivo ~* 'certific' THEN u.id_expediente END) as motivo_certificado
        FROM mv_catastro_egresos_efectivos ee
        JOIN mv_catastro_universo u ON u.id_expediente = ee.id_expediente
        LEFT JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente
        WHERE u.trata = 'MDUG0134N'
    """)).mappings().first()
    print("MDUG0134N Egresos con filtro motivo en pases:", dict(r))

    print("\n=== REVISANDO MOTIVO EN EL PASE QUE GENERA EL EGRESO O EN CUALQUIER PASE POSTERIOR AL PRIMER INGRESO ===")
    r2 = conn.execute(text("""
        SELECT 
            count(DISTINCT u.id_expediente) as total_egresos,
            count(DISTINCT CASE WHEN p.motivo ~* 'constituc|certific' AND p.fecha >= u.fecha_primer_ingreso_gerencia THEN u.id_expediente END) as motivo_en_pase_posterior_ingreso
        FROM mv_catastro_egresos_efectivos ee
        JOIN mv_catastro_universo u ON u.id_expediente = ee.id_expediente
        LEFT JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente
        WHERE u.trata = 'MDUG0134N'
    """)).mappings().first()
    print("MDUG0134N Egresos filtrados por pase >= ingreso:", dict(r2))

    print("\n=== TOP 20 MOTIVOS DE PASES EN MDUG0134N ===")
    top_motivos = conn.execute(text("""
        SELECT p.motivo, count(*) 
        FROM mvw_ee_pases_secgdu p
        JOIN mv_catastro_universo u ON u.id_expediente = p.id_expediente
        WHERE u.trata = 'MDUG0134N' AND p.motivo IS NOT NULL AND p.motivo <> ''
        GROUP BY p.motivo
        ORDER BY count(*) DESC
        LIMIT 20
    """)).mappings().fetchall()
    for tm in top_motivos:
        print(dict(tm))
