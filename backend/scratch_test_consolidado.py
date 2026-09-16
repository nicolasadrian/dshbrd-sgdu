import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== PROBANDO QUERY DE /api/reporte/catastro/consolidado ===")
    from config import TRAMITES_CONFIG
    import pandas as pd
    from datetime import datetime
    
    gerencia_clean = 'catastro'
    trata_codes = list(TRAMITES_CONFIG[gerencia_clean].keys())
    now = datetime.now()
    modular_months = []
    m_y, m_m = now.year, now.month
    for _ in range(5):
        modular_months.append(f"'{m_y}-{str(m_m).zfill(2)}'")
        m_m -= 1
        if m_m == 0: m_m = 12; m_y -= 1

    interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos"

    sql = f"""
        WITH periodos(mes_label) AS (
            SELECT * FROM (VALUES {", ".join([f"({m})" for m in modular_months])}) as t(m)
        ),
        ing AS (
            SELECT to_char(fecha_ingreso, 'YYYY-MM') as mes_label, 
                    CASE WHEN trata = ANY(:tratas_oficiales) THEN trata ELSE 'INTERVENCIONES' END as trata, 
                    COUNT(*) as cant
            FROM mv_{gerencia_clean}_ingresos_eventos
            GROUP BY 1, 2
        ),
        egr_ef AS (
            SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, trata, COUNT(*) as cant
            FROM mv_{gerencia_clean}_gedos_egreso
            GROUP BY 1, 2
            UNION ALL
            SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, 'INTERVENCIONES' as trata, COUNT(*) as cant
            FROM {interv_egr_table}
            GROUP BY 1, 2
        ),
        egr_ne AS (
            SELECT to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_label, 
                    CASE WHEN trata = ANY(:tratas_oficiales) THEN trata ELSE 'INTERVENCIONES' END as trata, 
                    COUNT(*) as cant
            FROM mv_{gerencia_clean}_egresos_no_efectivos
            GROUP BY 1, 2
        ),
        stock_data AS (
            SELECT mes_label, 
                    CASE WHEN trata = ANY(:tratas_oficiales) THEN trata ELSE 'INTERVENCIONES' END as trata,
                    SUM(CASE WHEN categoria = 'STOCK_PROPIO' THEN cant_expedientes ELSE 0 END) as stock_propio,
                    SUM(CASE WHEN categoria = 'SUBSANACION' THEN cant_expedientes ELSE 0 END) as stock_subs
            FROM mv_{gerencia_clean}_stock_historico
            GROUP BY 1, 2
        ),
        config_order AS (
            SELECT * FROM (VALUES {", ".join([f"('{c}', {i})" for i, c in enumerate(trata_codes)])}) as t(trata_code, ord)
        ),
        current_stock AS (
            SELECT trata, COUNT(*) as cant FROM mv_{gerencia_clean}_stock_propio GROUP BY 1
            UNION ALL
            SELECT 'INTERVENCIONES' as trata, COUNT(*) as cant FROM mv_{gerencia_clean}_intervenciones_stock GROUP BY 1
        ),
        current_subs AS (
            SELECT trata, COUNT(*) as cant FROM mv_{gerencia_clean}_subsanaciones GROUP BY 1
            UNION ALL
            SELECT 'INTERVENCIONES' as trata, COUNT(*) as cant FROM mv_{gerencia_clean}_intervenciones_subs GROUP BY 1
        )
        SELECT 
            et.trata as "COD TRATA", 
            et.descripcion_trata as "DETALLE TRATA",
            p.mes_label,
            to_number(split_part(p.mes_label, '-', 1), '9999') as anio,
            to_number(split_part(p.mes_label, '-', 2), '99') as mes,
            COALESCE(i.cant, 0) as "ING",
            COALESCE(ef.cant, 0) as "EGR_EF",
            COALESCE(ne.cant, 0) as "EGR_NE",
            CASE 
                WHEN p.mes_label = to_char(now(), 'YYYY-MM')
                THEN COALESCE(MAX(cs.cant), 0) 
                ELSE COALESCE(SUM(s.stock_propio), 0) 
            END as "STOCK_PROPIO",
            CASE 
                WHEN p.mes_label = to_char(now(), 'YYYY-MM')
                THEN COALESCE(MAX(csub.cant), 0) 
                ELSE COALESCE(SUM(s.stock_subs), 0) 
            END as "STOCK_SUBS"
        FROM periodos p
        CROSS JOIN (
            SELECT v.trata_code as trata,
                    COALESCE(
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE trata_reporte = v.trata_code AND gerencia = :g LIMIT 1),
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE v.trata_code = ANY(tratas_incluidas) AND gerencia = :g LIMIT 1),
                        v.trata_code
                    ) as descripcion_trata
            FROM (VALUES {", ".join([f"('{c}')" for c in trata_codes if c != 'INTERVENCIONES'])}) as v(trata_code)
            UNION ALL
            SELECT 'INTERVENCIONES', 'Intervenciones'
        ) et
        JOIN config_order o ON et.trata = o.trata_code
        LEFT JOIN ing i ON i.mes_label = p.mes_label AND i.trata = et.trata
        LEFT JOIN egr_ef ef ON ef.mes_label = p.mes_label AND ef.trata = et.trata
        LEFT JOIN egr_ne ne ON ne.mes_label = p.mes_label AND ne.trata = et.trata
        LEFT JOIN stock_data s ON s.mes_label = p.mes_label AND s.trata = et.trata
        LEFT JOIN current_stock cs ON cs.trata = et.trata
        LEFT JOIN current_subs csub ON csub.trata = et.trata
        GROUP BY p.mes_label, 1, 2, 3, 4, o.ord, i.cant, ef.cant, ne.cant
        ORDER BY o.ord, anio DESC, mes DESC
    """
    params = {"tratas_oficiales": [t for t in trata_codes if t != 'INTERVENCIONES'], "g": gerencia_clean}
    
    try:
        res = conn.execute(text(sql), params).fetchall()
        print(f"Total registros obtenidos para Catastro: {len(res)}")
        for r in res[:10]:
            print(r)
    except Exception as e:
        print("Error en query consolidado:", e)
