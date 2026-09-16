import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== SIMULANDO STOCK HISTORICO MES A MES CORRECTO PARA MDUG0134N ===")
    
    # Un expediente a la fecha de corte fc.fecha_corte está en STOCK PROPIO si:
    # 1. Ingresó a la gerencia antes o en la fecha de corte (fecha_primer_ingreso_gerencia <= fc.fecha_corte).
    # 2. NO había egresado efectivamente a la fecha de corte (ee.fecha_egreso IS NULL OR ee.fecha_egreso::date > fc.fecha_corte).
    # 3. Su destinatario en el pase a la fecha de corte era un analista oficial.
    # 4. A la fecha de corte, la última actividad de subsanación (SOLICITUD vs SUBSANACION) anterior o igual a la fecha_corte NO era SOLICITUD_SUBSANACION_TAD PENDIENTE.

    sim_sql = """
    WITH cfg AS (
        SELECT cfg_gestion_metas.analistas_oficiales
        FROM cfg_gestion_metas
        WHERE cfg_gestion_metas.gerencia = 'catastro'::text AND cfg_gestion_metas.trata_reporte = 'INTERVENCIONES'::text
    ), fechas_corte AS (
        SELECT (date_trunc('month'::text, mes.mes) + '1 mon -1 days'::interval)::date AS fecha_corte
        FROM generate_series(date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) - '11 mons'::interval, date_trunc('month'::text, CURRENT_DATE::timestamp with time zone), '1 mon'::interval) mes(mes)
    ), destinatario_por_corte AS (
        SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte) 
            u.id_expediente,
            u.trata,
            u.es_trata_propia,
            fc.fecha_corte,
            p.destinatario AS destinatario_cierre
        FROM mv_catastro_universo u
        CROSS JOIN fechas_corte fc
        JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente AND p.fecha::date <= fc.fecha_corte
        LEFT JOIN mv_catastro_egresos_efectivos ee ON ee.id_expediente = u.id_expediente
        WHERE u.trata = 'MDUG0134N'
          AND u.fecha_primer_ingreso_gerencia::date <= fc.fecha_corte
          AND (ee.id_expediente IS NULL OR ee.fecha_egreso::date > fc.fecha_corte)
        ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
    ), subs_al_cierre AS (
        SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
            dpc.id_expediente,
            dpc.fecha_corte,
            a.nombre_tipo_actividad,
            a.estado
        FROM destinatario_por_corte dpc
        JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = dpc.id_expediente 
             AND a.fecha_alta::date <= dpc.fecha_corte
             AND a.nombre_tipo_actividad IN ('SOLICITUD_SUBSANACION_TAD', 'SUBSANACION')
        ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
    )
    SELECT 
        to_char(dpc.fecha_corte::timestamp with time zone, 'YYYY-MM'::text) AS mes_label,
        CASE
            WHEN sac.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD' AND sac.estado = 'PENDIENTE' THEN 'SUBSANACION'
            ELSE 'STOCK_PROPIO'
        END AS categoria,
        count(*) AS cant_expedientes
    FROM destinatario_por_corte dpc
    LEFT JOIN subs_al_cierre sac ON sac.id_expediente = dpc.id_expediente AND sac.fecha_corte = dpc.fecha_corte
    CROSS JOIN cfg
    WHERE dpc.destinatario_cierre = ANY (cfg.analistas_oficiales)
    GROUP BY dpc.fecha_corte, 2
    ORDER BY dpc.fecha_corte, 2;
    """

    res = conn.execute(text(sim_sql)).mappings().fetchall()
    print("Recálculo mes a mes coherente con egresos y ciclo de subsanaciones:")
    for r in res:
        print(dict(r))
