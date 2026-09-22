import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

local_sade = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
eng = create_engine(local_sade)

with eng.connect() as conn:
    print("=== 1. Reglas de Catastro en cfg_gestion_metas ===", flush=True)
    res = conn.execute(text("SELECT trata_reporte, acronimos_egreso, firmantes_egreso FROM cfg_gestion_metas WHERE gerencia='catastro'")).mappings().fetchall()
    for r in res:
        print(" ", dict(r), flush=True)

    print("\n=== 2. Egresos efectivos de Catastro SIN el filtro 'constituc|certific' en Agosto 2026 ===", flush=True)
    q_test = """
        WITH reglas_por_trata AS (
            SELECT cfg.trata_reporte AS trata,
               unnest(cfg.acronimos_egreso) AS acronimo,
               cfg.firmantes_egreso
            FROM cfg_gestion_metas cfg
            WHERE ((cfg.gerencia = 'catastro'::text) AND (cfg.trata_reporte <> 'INTERVENCIONES'::text))
        ), egresos_validos AS (
            SELECT u.id_expediente,
               u.expediente,
               u.trata,
               u.descripcion_trata,
               u.descripcion,
               u.caratula,
               u.fecha_primer_ingreso_gerencia,
               d.documento AS documento_egreso,
               d.acronimo AS acronimo_egreso,
               d.fecha_asociacion AS fecha_egreso,
               d.usuario_creador AS usuario_egreso,
               row_number() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_asociacion) AS rn
            FROM ((mv_catastro_universo u
               JOIN reglas_por_trata r ON ((r.trata = u.trata)))
               JOIN mvw_datos_gedo_secgdu d ON (((d.id_expediente = u.id_expediente) AND (d.acronimo = r.acronimo) AND ((r.firmantes_egreso IS NULL) OR (d.usuario_creador = ANY (r.firmantes_egreso))) AND (d.fecha_asociacion >= u.fecha_primer_ingreso_gerencia))))
            WHERE (u.es_trata_propia = true)
        )
        SELECT trata, to_char(fecha_egreso, 'YYYY-MM') as mes, count(1)
        FROM egresos_validos
        WHERE rn = 1 AND fecha_egreso >= '2026-08-01' AND fecha_egreso < '2026-09-01'
        GROUP BY trata, to_char(fecha_egreso, 'YYYY-MM')
        ORDER BY trata;
    """
    res_egresos = conn.execute(text(q_test)).fetchall()
    print("Egresos calculados para Catastro en Agosto 2026:")
    for r in res_egresos:
        print(" ", r, flush=True)
