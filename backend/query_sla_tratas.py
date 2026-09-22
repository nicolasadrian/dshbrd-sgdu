import os
import json
import csv
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

prod_sade = (os.getenv("DATABASE_URL_PUBLIC") or os.getenv("DATABASE_URL")).replace("postgres://", "postgresql://")
local_sade = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")

tratas_solicitadas = [
    "MDUG3001A",
    "MDUG0141A",
    "MDUG0104A",
    "MDUG1501J",
    "MDUG1501K",
    "MDUG0102B",
    "MDUG3701A",
    "MDUG2901A",
    "MDUG0131B",
    "MDUG2101A",
    "MDUG0115B"
]

print("=== Consultando PROD SADE_DB ===", flush=True)
try:
    eng = create_engine(prod_sade, connect_args={"connect_timeout": 15})
    with eng.connect() as conn:
        cols = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='planificacion_tiempos_tramitacion_resumen'")).fetchall()
        print("Columnas:", [c[0] for c in cols], flush=True)
        
        query = text("""
            SELECT *
            FROM planificacion_tiempos_tramitacion_resumen
            WHERE trata = ANY(:tratas)
            ORDER BY gerencia, trata;
        """)
        rows = conn.execute(query, {"tratas": tratas_solicitadas}).mappings().fetchall()
        print(f"Encontrados en PROD: {len(rows)} de {len(tratas_solicitadas)}", flush=True)
        for r in rows:
            print(dict(r), flush=True)
except Exception as e:
    print("Error en PROD:", e, flush=True)

print("\n=== Consultando LOCAL SADE_DB ===", flush=True)
try:
    eng_loc = create_engine(local_sade)
    with eng_loc.connect() as conn:
        rows_loc = conn.execute(text("SELECT * FROM planificacion_tiempos_tramitacion_resumen WHERE trata = ANY(:tratas) ORDER BY gerencia, trata;"), {"tratas": tratas_solicitadas}).mappings().fetchall()
        print(f"Encontrados en LOCAL: {len(rows_loc)} de {len(tratas_solicitadas)}", flush=True)
        for r in rows_loc:
            print(dict(r), flush=True)
except Exception as e:
    print("Error en LOCAL:", e, flush=True)
