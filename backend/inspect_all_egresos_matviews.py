import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

local_sade = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
prod_sade = (os.getenv("DATABASE_URL_PUBLIC") or os.getenv("DATABASE_URL")).replace("postgres://", "postgresql://")

def inspect_db(name, url):
    print(f"\n=================== {name} ===================", flush=True)
    eng = create_engine(url, connect_args={"connect_timeout": 15})
    
    matviews = []
    with eng.connect() as conn:
        res = conn.execute(text("SELECT matviewname FROM pg_matviews WHERE matviewname LIKE '%egresos_efectivos%' ORDER BY matviewname")).fetchall()
        matviews = [r[0] for r in res]
    
    for mv in matviews:
        with eng.connect() as conn:
            vdef = conn.execute(text(f"SELECT definition FROM pg_matviews WHERE matviewname = '{mv}'")).scalar()
            has_special = "motivo" in (vdef or "").lower() or "~*" in (vdef or "")
            m_res = conn.execute(text(f"SELECT to_char(fecha_egreso, 'YYYY-MM') as mes, count(1) FROM {mv} GROUP BY 1 ORDER BY 1 DESC LIMIT 3")).fetchall()
            print(f"  {mv} -> Has 'motivo' filter: {has_special} | Months: {m_res}", flush=True)

inspect_db("LOCAL", local_sade)
inspect_db("PROD", prod_sade)
