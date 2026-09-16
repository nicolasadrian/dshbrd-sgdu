import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== ESTADO DEL EXPEDIENTE EX-2026-28612115-   -GCABA-DGROC ===")
    id_exp = 32017770
    views = [
        'mv_catastro_universo',
        'mv_catastro_stock_propio',
        'mv_catastro_subsanaciones',
        'mv_catastro_egresos_efectivos',
        'mv_catastro_egresos_no_efectivos'
    ]
    for v in views:
        r = conn.execute(text(f"SELECT * FROM {v} WHERE id_expediente = {id_exp}")).mappings().first()
        print(f"{v}: {'PRESENTE' if r else 'NO PRESENTE'}")

    print("\n=== TOTALES MDUG0134N CON EL NUEVO CRITERIO DE SUBSANACIONES ===")
    st = conn.execute(text("SELECT COUNT(*) FROM mv_catastro_stock_propio WHERE trata = 'MDUG0134N'")).scalar()
    subs = conn.execute(text("SELECT COUNT(*) FROM mv_catastro_subsanaciones WHERE trata = 'MDUG0134N'")).scalar()
    egr = conn.execute(text("SELECT COUNT(*) FROM mv_catastro_egresos_efectivos WHERE trata = 'MDUG0134N'")).scalar()
    egr_no = conn.execute(text("SELECT COUNT(*) FROM mv_catastro_egresos_no_efectivos WHERE trata = 'MDUG0134N'")).scalar()
    print(f"Stock Propio: {st}")
    print(f"Subsanaciones: {subs}")
    print(f"Egresos Efectivos: {egr}")
    print(f"Egresos No Efectivos: {egr_no}")
