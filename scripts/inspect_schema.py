import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text
from config import TRAMITES_CONFIG

def inspect_schema():
    with engine.connect() as conn:
        for g in TRAMITES_CONFIG.keys():
            g_clean = g.lower()
            print(f"\n--- Gerencia: {g_clean} ---")
            
            # check columns of ingresos
            try:
                cols = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = 'mv_{g_clean}_ingresos_eventos'")).fetchall()
                print(f"mv_{g_clean}_ingresos_eventos columns:", [c[0] for c in cols])
            except Exception as e:
                print(f"Error checking ingresos for {g_clean}:", e)
                
            # check columns of gedos_egreso
            try:
                cols = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = 'mv_{g_clean}_gedos_egreso'")).fetchall()
                print(f"mv_{g_clean}_gedos_egreso columns:", [c[0] for c in cols])
            except Exception as e:
                print(f"Error checking gedos_egreso for {g_clean}:", e)

            # check columns of interv egreso
            interv_egr_table = f"mv_{g_clean}_interv_egresos_eventos" if g_clean != 'contable' else "mv_contable_intervenciones_egresadas"
            try:
                cols = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{interv_egr_table}'")).fetchall()
                print(f"{interv_egr_table} columns:", [c[0] for c in cols])
            except Exception as e:
                print(f"Error checking {interv_egr_table}:", e)

            # check columns of egresos_no_efectivos
            try:
                cols = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = 'mv_{g_clean}_egresos_no_efectivos'")).fetchall()
                print(f"mv_{g_clean}_egresos_no_efectivos columns:", [c[0] for c in cols])
            except Exception as e:
                print(f"Error checking egresos_no_efectivos for {g_clean}:", e)

if __name__ == '__main__':
    inspect_schema()
