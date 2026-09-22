import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

local_sade = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
eng = create_engine(local_sade)

gerencias = [
    'catastro',
    'instalaciones',
    'regularizacion',
    'contable',
    'etapa_proyecto',
    'aviso_obra',
    'morfologia',
    'aph',
    'usos',
    'publico_privado',
    'copua',
    'privada'
]

with eng.connect() as conn:
    print("=== REVISION DE TODAS LAS VISTAS DE EGRESOS EFECTIVOS ===", flush=True)
    for g in gerencias:
        mv_name = f"mv_{g}_egresos_efectivos"
        try:
            vdef = conn.execute(text(f"SELECT definition FROM pg_matviews WHERE matviewname = '{mv_name}'")).scalar()
            has_special_where = "motivo" in (vdef or "").lower() or "like" in (vdef or "").lower() or "~*" in (vdef or "")
            
            # Check latest months in this view
            months = conn.execute(text(f"SELECT to_char(fecha_egreso, 'YYYY-MM') as mes, count(1) FROM {mv_name} GROUP BY 1 ORDER BY 1 DESC LIMIT 3")).fetchall()
            print(f"[{g.upper()}] ({mv_name}) -> Special WHERE filters: {has_special_where} | Últimos meses: {months}", flush=True)
            if has_special_where:
                print(f"   --> WHERE clause in {mv_name}:\n{vdef}\n", flush=True)
        except Exception as e:
            print(f"[{g.upper()}] Error: {e}", flush=True)
