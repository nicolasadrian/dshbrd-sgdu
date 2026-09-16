import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== INSPECTING mvw_ee_pases_secgdu ===")
    pases_cols = conn.execute(text("SELECT * FROM mvw_ee_pases_secgdu LIMIT 1")).mappings().first()
    print("Columnas mvw_ee_pases_secgdu:", list(pases_cols.keys()) if pases_cols else "None")
    
    print("\n=== SAMPLE PASES CON MOTIVO PARA MDUG0134N ===")
    pases_sample = conn.execute(text("""
        SELECT p.id_expediente, p.fecha, p.usuario, p.destinatario, p.motivo
        FROM mvw_ee_pases_secgdu p
        JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = p.id_expediente
        WHERE e.trata = 'MDUG0134N' AND p.motivo IS NOT NULL AND p.motivo <> ''
        LIMIT 10
    """)).mappings().fetchall()
    for ps in pases_sample:
        print(dict(ps))

    print("\n=== MOTIVOS EN PASES DE EGRESO vs MOTIVOS EN GEDO ===")
    gedo_cols = conn.execute(text("SELECT * FROM mvw_datos_gedo_secgdu LIMIT 1")).mappings().first()
    print("Columnas mvw_datos_gedo_secgdu:", list(gedo_cols.keys()) if gedo_cols else "None")
    
    print("\n=== INSPECTING mvw_ee_actividades_secgdu ===")
    act_cols = conn.execute(text("SELECT * FROM mvw_ee_actividades_secgdu LIMIT 1")).mappings().first()
    print("Columnas mvw_ee_actividades_secgdu:", list(act_cols.keys()) if act_cols else "None")

    print("\n=== SAMPLE ACTIVIDADES DE SUBSANACION PARA CATASTRO ===")
    acts = conn.execute(text("""
        SELECT a.id_expediente, a.usuario_alta, a.nombre_tipo_actividad, a.estado, a.fecha_alta, a.fecha_cierre
        FROM mvw_ee_actividades_secgdu a
        JOIN mv_catastro_universo u ON u.id_expediente = a.id_expediente
        WHERE a.nombre_tipo_actividad ILIKE '%SUBSANACION%'
        ORDER BY a.id_expediente, a.fecha_alta DESC
        LIMIT 15
    """)).mappings().fetchall()
    for a in acts:
        print(dict(a))

    print("\n=== DISTINTOS ESTADOS EN ACTIVIDADES ===")
    estados = conn.execute(text("SELECT DISTINCT estado, nombre_tipo_actividad FROM mvw_ee_actividades_secgdu WHERE nombre_tipo_actividad ILIKE '%SUBSANACION%'")).mappings().fetchall()
    for e in estados:
        print(dict(e))
