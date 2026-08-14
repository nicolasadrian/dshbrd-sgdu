from database import engine
from sqlalchemy import text

g_list = ['catastro', 'instalaciones', 'regularizacion', 'contable', 'etapa_proyecto', 'morfologia', 'aph', 'usos', 'aviso_obra']

with engine.connect() as conn:
    print("=== MATERIALIZED VIEWS WITH 'interv' ===")
    sql = "SELECT matviewname FROM pg_matviews WHERE matviewname LIKE '%interv%' ORDER BY matviewname"
    views = conn.execute(text(sql)).scalars().all()
    for v in views:
        print("  -", v)

    print("\n=== RECORD COUNTS PER GERENCIA FOR INTERVENCIONES STOCK, SUBS & EGRESOS/INGRESOS ===")
    for g in g_list:
        st_count = 0
        sub_count = 0
        ing_count = 0
        
        # Stock
        try:
            st_count = conn.execute(text(f"SELECT COUNT(*) FROM mv_{g}_intervenciones_stock")).scalar() or 0
        except Exception as e:
            st_count = f"Error ({e})"

        # Subsanaciones
        try:
            sub_count = conn.execute(text(f"SELECT COUNT(*) FROM mv_{g}_intervenciones_subs")).scalar() or 0
        except Exception as e:
            sub_count = f"Error ({e})"

        # Egresos / Eventos / Ingresos
        for v_name in [f"mv_{g}_interv_egresos_eventos", f"mv_{g}_intervenciones_egresadas", f"mv_{g}_intervenciones_eventos"]:
            try:
                c = conn.execute(text(f"SELECT COUNT(*) FROM {v_name}")).scalar() or 0
                ing_count = f"{v_name}: {c}"
                break
            except Exception:
                pass

        print(f"Gerencia {g:15s} | Stock: {str(st_count):6s} | Subs: {str(sub_count):6s} | Egresos/Ingresos: {ing_count}")
