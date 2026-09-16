import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    exp_num = '28612115'
    print(f"=== INSPECTING EXPEDIENTE CON NUMERO {exp_num} ===")
    
    # 1. Buscar en mvw_expedientes_tratas_secgdu
    e_row = conn.execute(text(f"""
        SELECT * FROM mvw_expedientes_tratas_secgdu 
        WHERE expediente LIKE '%{exp_num}%'
    """)).mappings().fetchall()
    
    for e in e_row:
        print("\n--- Expediente en mvw_expedientes_tratas_secgdu ---")
        print(dict(e))
        id_exp = e['id_expediente']
        
        # 2. Buscar en mv_ultimo_pase
        up = conn.execute(text(f"SELECT * FROM mv_ultimo_pase WHERE id_expediente = {id_exp}")).mappings().first()
        print("\n--- Ultimo Pase ---")
        print(dict(up) if up else "None")

        # 3. Buscar en mvw_datos_gedo_secgdu
        gedos = conn.execute(text(f"SELECT * FROM mvw_datos_gedo_secgdu WHERE id_expediente = {id_exp}")).mappings().fetchall()
        print("\n--- Documentos GEDO asociados ---")
        for g in gedos:
            print(dict(g))

        # 4. Buscar en mvw_ee_actividades_secgdu
        acts = conn.execute(text(f"SELECT * FROM mvw_ee_actividades_secgdu WHERE id_expediente = {id_exp} ORDER BY fecha_alta DESC")).mappings().fetchall()
        print("\n--- Actividades ---")
        for a in acts:
            print(dict(a))

        # 5. Estado en las distintas vistas de Catastro
        views = [
            'mv_catastro_universo',
            'mv_catastro_stock_propio',
            'mv_catastro_subsanaciones',
            'mv_catastro_egresos_efectivos',
            'mv_catastro_egresos_no_efectivos',
            'mv_catastro_gedos_egreso'
        ]
        print("\n--- Presencia en vistas materializadas de Catastro ---")
        for v in views:
            r = conn.execute(text(f"SELECT * FROM {v} WHERE id_expediente = {id_exp}")).mappings().first()
            print(f"{v}: {'PRESENTE -> ' + str(dict(r)) if r else 'NO PRESENTE'}")
