import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

prod_sade = (os.getenv("DATABASE_URL_PUBLIC") or os.getenv("DATABASE_URL")).replace("postgres://", "postgresql://")
eng = create_engine(prod_sade, connect_args={"connect_timeout": 15})

with eng.connect() as conn:
    print("=== 1. Cuántos MDUG0131B hay en mv_catastro_egresos_efectivos en PROD por mes? ===", flush=True)
    res = conn.execute(text("""
        SELECT to_char(fecha_egreso, 'YYYY-MM') as mes, count(1)
        FROM mv_catastro_egresos_efectivos
        WHERE trata = 'MDUG0131B'
        GROUP BY 1 ORDER BY 1 DESC;
    """)).fetchall()
    print("En PROD mv_catastro_egresos_efectivos:", res, flush=True)

    print("\n=== 2. Qué hay actualmente en PROD planificacion_tiempos_tramitacion_resumen para Catastro? ===", flush=True)
    res_sla = conn.execute(text("""
        SELECT trata, descripcion_trata, total_resueltos_ultimo_mes, ultimo_mes_cerrado, dias_totales, total_resueltos_este_ano
        FROM planificacion_tiempos_tramitacion_resumen
        WHERE gerencia = 'catastro'
        ORDER BY trata;
    """)).fetchall()
    for r in res_sla:
        print(" ", r, flush=True)
