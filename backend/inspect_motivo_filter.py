import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

local_sade = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
eng = create_engine(local_sade)

with eng.connect() as conn:
    print("=== 1. Cuántos expedientes MDUG0131B tienen GEDO IFMHC en Agosto 2026? ===", flush=True)
    res_gedo = conn.execute(text("""
        SELECT count(DISTINCT u.id_expediente)
        FROM mv_catastro_universo u
        JOIN mvw_datos_gedo_secgdu d ON d.id_expediente = u.id_expediente AND d.acronimo = 'IFMHC'
        WHERE u.trata = 'MDUG0131B'
          AND d.fecha_asociacion >= '2026-08-01' AND d.fecha_asociacion < '2026-09-01';
    """)).scalar()
    print("MDUG0131B con IFMHC en Agosto 2026:", res_gedo, flush=True)

    print("\n=== 2. Cuántos de esos tienen p.motivo ~* 'constituc|certific'? ===", flush=True)
    res_motivo = conn.execute(text("""
        SELECT count(DISTINCT u.id_expediente)
        FROM mv_catastro_universo u
        JOIN mvw_datos_gedo_secgdu d ON d.id_expediente = u.id_expediente AND d.acronimo = 'IFMHC'
        WHERE u.trata = 'MDUG0131B'
          AND d.fecha_asociacion >= '2026-08-01' AND d.fecha_asociacion < '2026-09-01'
          AND EXISTS (
              SELECT 1 FROM mvw_ee_pases_secgdu p
              WHERE p.id_expediente = u.id_expediente AND p.motivo ~* 'constituc|certific'
          );
    """)).scalar()
    print("Con filtro p.motivo ~* 'constituc|certific':", res_motivo, flush=True)

    print("\n=== 3. Qué motivos tienen los pases de esos 65 expedientes? ===", flush=True)
    pases_motivos = conn.execute(text("""
        SELECT p.motivo, count(1)
        FROM mv_catastro_universo u
        JOIN mvw_datos_gedo_secgdu d ON d.id_expediente = u.id_expediente AND d.acronimo = 'IFMHC'
        JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente
        WHERE u.trata = 'MDUG0131B'
          AND d.fecha_asociacion >= '2026-08-01' AND d.fecha_asociacion < '2026-09-01'
        GROUP BY p.motivo
        ORDER BY count(1) DESC
        LIMIT 20;
    """)).fetchall()
    for pm in pases_motivos:
        print(" ", pm, flush=True)
