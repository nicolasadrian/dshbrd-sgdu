import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

local_sade = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
eng = create_engine(local_sade)

with eng.connect() as conn:
    print("=== DEFINICION DE mv_catastro_egresos_efectivos ===", flush=True)
    vdef = conn.execute(text("SELECT definition FROM pg_matviews WHERE matviewname = 'mv_catastro_egresos_efectivos'")).scalar()
    print(vdef, flush=True)

    print("\n=== DEFINICION DE mv_catastro_gedos_egreso ===", flush=True)
    gdef = conn.execute(text("SELECT definition FROM pg_matviews WHERE matviewname = 'mv_catastro_gedos_egreso'")).scalar()
    print(gdef, flush=True)

    print("\n=== GEDOS DE EGRESO PARA MDUG0131B EN AGOSTO 2026 (2026-08) ===", flush=True)
    # Check GEDO documents for catastro in 2026-08
    cfg_cat = conn.execute(text("SELECT * FROM cfg_gestion_metas WHERE gerencia='catastro' AND trata_reporte='MDUG0131B'")).mappings().fetchone()
    print("cfg_gestion_metas para MDUG0131B:", dict(cfg_cat) if cfg_cat else "None", flush=True)
