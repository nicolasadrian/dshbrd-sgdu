import sys
import psycopg2
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path if os.path.exists(env_path) else None)

LOCAL_URL = os.getenv('DATABASE_URL_LOCAL', 'postgresql://postgres:lenovo@localhost:5432/sade_db')

def recreate_fast():
    conn = psycopg2.connect(LOCAL_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    # Quitar timeout para esta sesión
    cur.execute("SET statement_timeout = 0;")

    print("Recreando mv_catastro_stock_historico con optimización...")
    cur.execute("DROP MATERIALIZED VIEW IF EXISTS mv_catastro_stock_historico CASCADE;")
    
    query = """
    CREATE MATERIALIZED VIEW mv_catastro_stock_historico AS
    WITH cfg AS (
        SELECT cfg_gestion_metas.analistas_oficiales
        FROM cfg_gestion_metas
        WHERE cfg_gestion_metas.gerencia = 'catastro'::text AND cfg_gestion_metas.trata_reporte = 'INTERVENCIONES'::text
    ), fechas_corte AS (
        SELECT (date_trunc('month'::text, mes.mes) + '1 mon -1 days'::interval)::date AS fecha_corte
        FROM generate_series(date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) - '11 mons'::interval, date_trunc('month'::text, CURRENT_DATE::timestamp with time zone), '1 mon'::interval) mes(mes)
    ), pases_catastro AS (
        SELECT p.id_expediente, p.fecha, p.destinatario
        FROM mvw_ee_pases_secgdu p
        JOIN mv_catastro_universo u ON u.id_expediente = p.id_expediente
    ), destinatario_por_corte AS (
        SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte) 
            u.id_expediente,
            u.trata,
            u.es_trata_propia,
            fc.fecha_corte,
            p.destinatario AS destinatario_cierre
        FROM mv_catastro_universo u
        CROSS JOIN fechas_corte fc
        JOIN pases_catastro p ON p.id_expediente = u.id_expediente AND p.fecha::date <= fc.fecha_corte
        LEFT JOIN mv_catastro_egresos_efectivos ee ON ee.id_expediente = u.id_expediente
        WHERE u.fecha_primer_ingreso_gerencia::date <= fc.fecha_corte
          AND (ee.id_expediente IS NULL OR ee.fecha_egreso::date > fc.fecha_corte)
        ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
    ), act_subs AS (
        SELECT a.id_expediente, a.fecha_alta, a.nombre_tipo_actividad, a.estado
        FROM mvw_ee_actividades_secgdu a
        JOIN mv_catastro_universo u ON u.id_expediente = a.id_expediente
        WHERE a.nombre_tipo_actividad IN ('SOLICITUD_SUBSANACION_TAD', 'SUBSANACION')
    ), subs_al_cierre AS (
        SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
            dpc.id_expediente,
            dpc.fecha_corte,
            a.nombre_tipo_actividad,
            a.estado
        FROM destinatario_por_corte dpc
        JOIN act_subs a ON a.id_expediente = dpc.id_expediente 
             AND a.fecha_alta::date <= dpc.fecha_corte
        ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
    )
    SELECT 
        dpc.fecha_corte AS mes_cierre,
        to_char(dpc.fecha_corte::timestamp with time zone, 'YYYY-MM'::text) AS mes_label,
        dpc.trata,
        dpc.es_trata_propia,
        CASE
            WHEN sac.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD' AND sac.estado = 'PENDIENTE' THEN 'SUBSANACION'::text
            ELSE 'STOCK_PROPIO'::text
        END AS categoria,
        count(*) AS cant_expedientes
    FROM destinatario_por_corte dpc
    LEFT JOIN subs_al_cierre sac ON sac.id_expediente = dpc.id_expediente AND sac.fecha_corte = dpc.fecha_corte
    CROSS JOIN cfg
    WHERE dpc.destinatario_cierre = ANY (cfg.analistas_oficiales)
    GROUP BY dpc.fecha_corte, to_char(dpc.fecha_corte::timestamp with time zone, 'YYYY-MM'::text), dpc.trata, dpc.es_trata_propia, 
             CASE
                 WHEN sac.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD' AND sac.estado = 'PENDIENTE' THEN 'SUBSANACION'::text
                 ELSE 'STOCK_PROPIO'::text
             END;
    """
    cur.execute(query)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_catastro_sh_corte ON mv_catastro_stock_historico(mes_cierre, trata);")
    print("¡mv_catastro_stock_historico creada exitosamente!")

if __name__ == '__main__':
    recreate_fast()
