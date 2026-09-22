import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

local_sade = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
eng = create_engine(local_sade)

with eng.connect() as conn:
    print("=== 1. Conteo en mv_catastro_egresos_efectivos por mes para MDUG0131B ===", flush=True)
    try:
        res = conn.execute(text("""
            SELECT to_char(fecha_egreso, 'YYYY-MM') as mes, count(1) 
            FROM mv_catastro_egresos_efectivos 
            WHERE trata = 'MDUG0131B' 
            GROUP BY 1 ORDER BY 1 DESC;
        """)).fetchall()
        print("mv_catastro_egresos_efectivos:", res, flush=True)
    except Exception as e:
        print("Error en mv_catastro_egresos_efectivos:", e, flush=True)

    print("\n=== 2. Conteo en mvw_catastro_egresos (o similares) para MDUG0131B ===", flush=True)
    # Check all views that have catastro or egresos
    views = conn.execute(text("SELECT table_name FROM information_schema.views WHERE table_name LIKE '%catastro%' OR table_name LIKE '%egreso%'")).fetchall()
    matviews = conn.execute(text("SELECT matviewname FROM pg_matviews WHERE matviewname LIKE '%catastro%' OR matviewname LIKE '%egreso%'")).fetchall()
    print("Views:", [v[0] for v in views])
    print("MatViews:", [m[0] for m in matviews])

    print("\n=== 3. Conteo en mvw_ee_egresos_secgdu / mvw_sade_acciones para MDUG0131B en Agosto 2026 (2026-08) ===", flush=True)
    try:
        res2 = conn.execute(text("""
            SELECT to_char(fecha_egreso, 'YYYY-MM') as mes, count(1)
            FROM mvw_ee_egresos_secgdu
            WHERE trata = 'MDUG0131B'
            GROUP BY 1 ORDER BY 1 DESC;
        """)).fetchall()
        print("mvw_ee_egresos_secgdu:", res2, flush=True)
    except Exception as e:
        print("Error mvw_ee_egresos_secgdu:", e, flush=True)

    print("\n=== 4. Definición de mv_catastro_egresos_efectivos ===", flush=True)
    try:
        view_def = conn.execute(text("""
            SELECT definition FROM pg_matviews WHERE matviewname = 'mv_catastro_egresos_efectivos'
            UNION ALL
            SELECT view_definition FROM information_schema.views WHERE table_name = 'mv_catastro_egresos_efectivos';
        """)).scalar()
        print(view_def)
    except Exception as e:
        print("Error getting view def:", e)
