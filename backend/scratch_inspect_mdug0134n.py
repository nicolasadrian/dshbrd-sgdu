import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text
import json

with engine.connect() as conn:
    print("=== CFG GESTION METAS (CATASTRO MDUG0134N y CATASTRO INTERVENCIONES) ===")
    rows = conn.execute(text("""
        SELECT id, gerencia, trata_reporte, tratas_incluidas, buzones_ingreso, 
               acronimos_egreso, firmantes_egreso, descripciones_validas, activo
        FROM cfg_gestion_metas 
        WHERE gerencia = 'catastro' AND trata_reporte IN ('MDUG0134N', 'INTERVENCIONES')
    """)).mappings().fetchall()
    for r in rows:
        print(dict(r))

    print("\n=== CONTEOS ACTUALES PARA MDUG0134N EN MATVIEWS DE CATASTRO ===")
    
    # Stock Propio
    st_propio = conn.execute(text("SELECT COUNT(*) FROM mv_catastro_stock_propio WHERE trata = 'MDUG0134N'")).scalar()
    print("Stock Propio (mv_catastro_stock_propio):", st_propio)
    
    # Subsanaciones
    subs = conn.execute(text("SELECT COUNT(*) FROM mv_catastro_subsanaciones WHERE trata = 'MDUG0134N'")).scalar()
    print("Subsanaciones (mv_catastro_subsanaciones):", subs)
    
    # Egresos efectivos
    egr_efectivos = conn.execute(text("SELECT COUNT(*) FROM mv_catastro_egresos_efectivos WHERE trata = 'MDUG0134N'")).scalar()
    print("Egresos Efectivos (mv_catastro_egresos_efectivos):", egr_efectivos)

    # Egresos no efectivos (Guarda Temporal sin GEDO)
    egr_no_efectivos = conn.execute(text("SELECT COUNT(*) FROM mv_catastro_egresos_no_efectivos WHERE trata = 'MDUG0134N'")).scalar()
    print("Egresos No Efectivos (mv_catastro_egresos_no_efectivos):", egr_no_efectivos)
    
    # GEDOs de egreso
    gedos = conn.execute(text("SELECT COUNT(*) FROM mv_catastro_gedos_egreso WHERE trata = 'MDUG0134N'")).scalar()
    print("GEDOs Egreso (mv_catastro_gedos_egreso):", gedos)

    # Universo
    universo = conn.execute(text("SELECT count(*), es_trata_propia FROM mv_catastro_universo WHERE trata = 'MDUG0134N' GROUP BY es_trata_propia")).mappings().fetchall()
    print("Universo Catastro MDUG0134N:", [dict(u) for u in universo])

    # Intervenciones stock / subs
    int_st = conn.execute(text("SELECT COUNT(*) FROM mv_catastro_intervenciones_stock WHERE trata = 'MDUG0134N'")).scalar()
    int_subs = conn.execute(text("SELECT COUNT(*) FROM mv_catastro_intervenciones_subs WHERE trata = 'MDUG0134N'")).scalar()
    print(f"Intervenciones Stock: {int_st}, Intervenciones Subs: {int_subs}")
