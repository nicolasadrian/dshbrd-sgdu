import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text
from config import TRAMITES_CONFIG

def test_configured_tratas(target_year=2026):
    with engine.connect() as conn:
        trata_metrics = {}

        for g, g_cfg in TRAMITES_CONFIG.items():
            g_clean = g.lower()
            tratas_oficiales = [t for t in g_cfg.keys() if t != 'INTERVENCIONES']

            # Initialize ONLY configured official tratas + INTERVENCIONES
            for t_code in tratas_oficiales:
                t_desc = g_cfg[t_code].get('nombre', t_code)
                key = (g_clean, t_code)
                trata_metrics[key] = {
                    "trata": t_code,
                    "descripcion_trata": t_desc,
                    "gerencia": g_clean,
                    "stock_este_ano": 0, "stock_previo": 0,
                    "subs_este_ano": 0, "subs_previo": 0,
                    "ingresos_este_ano": 0, "ingresos_previo": 0
                }

            key_int = (g_clean, "INTERVENCIONES")
            trata_metrics[key_int] = {
                "trata": "INTERVENCIONES",
                "descripcion_trata": "Intervenciones del Sector",
                "gerencia": g_clean,
                "stock_este_ano": 0, "stock_previo": 0,
                "subs_este_ano": 0, "subs_previo": 0,
                "ingresos_este_ano": 0, "ingresos_previo": 0
            }

            # 1. Stock Propio (Oficiales)
            sql_stock_p = f"""
                SELECT sp.trata, sp.descripcion_trata,
                    COUNT(CASE WHEN (
                        CASE WHEN sp.expediente LIKE 'EX-%' AND LENGTH(SPLIT_PART(sp.expediente, '-', 2)) = 4 THEN SPLIT_PART(sp.expediente, '-', 2)::integer
                        WHEN ext.fecha_creacion IS NOT NULL THEN EXTRACT(YEAR FROM ext.fecha_creacion)::integer ELSE 1900 END
                    ) = :y THEN 1 END) as este_ano,
                    COUNT(CASE WHEN (
                        CASE WHEN sp.expediente LIKE 'EX-%' AND LENGTH(SPLIT_PART(sp.expediente, '-', 2)) = 4 THEN SPLIT_PART(sp.expediente, '-', 2)::integer
                        WHEN ext.fecha_creacion IS NOT NULL THEN EXTRACT(YEAR FROM ext.fecha_creacion)::integer ELSE 1900 END
                    ) < :y THEN 1 END) as previo
                FROM mv_{g_clean}_stock_propio sp
                LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = sp.id_expediente
                WHERE TRIM(sp.trata) = ANY(:tratas)
                GROUP BY sp.trata, sp.descripcion_trata
            """
            try:
                for r in conn.execute(text(sql_stock_p), {"y": target_year, "tratas": tratas_oficiales}).fetchall():
                    ea, pr = int(r[2] or 0), int(r[3] or 0)
                    t_code = (r[0] or "").strip().upper()
                    key = (g_clean, t_code)
                    if key in trata_metrics:
                        trata_metrics[key]["stock_este_ano"] += ea
                        trata_metrics[key]["stock_previo"] += pr
            except Exception as e:
                print("Error stock p:", e)

            # 1b. Stock Intervenciones
            sql_stock_i = f"""
                SELECT 
                    COUNT(CASE WHEN (
                        CASE WHEN sp.expediente LIKE 'EX-%' AND LENGTH(SPLIT_PART(sp.expediente, '-', 2)) = 4 THEN SPLIT_PART(sp.expediente, '-', 2)::integer
                        WHEN ext.fecha_creacion IS NOT NULL THEN EXTRACT(YEAR FROM ext.fecha_creacion)::integer ELSE 1900 END
                    ) = :y THEN 1 END) as este_ano,
                    COUNT(CASE WHEN (
                        CASE WHEN sp.expediente LIKE 'EX-%' AND LENGTH(SPLIT_PART(sp.expediente, '-', 2)) = 4 THEN SPLIT_PART(sp.expediente, '-', 2)::integer
                        WHEN ext.fecha_creacion IS NOT NULL THEN EXTRACT(YEAR FROM ext.fecha_creacion)::integer ELSE 1900 END
                    ) < :y THEN 1 END) as previo
                FROM mv_{g_clean}_intervenciones_stock sp
                LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = sp.id_expediente
            """
            try:
                r = conn.execute(text(sql_stock_i), {"y": target_year}).fetchone()
                if r:
                    ea, pr = int(r[0] or 0), int(r[1] or 0)
                    key = (g_clean, "INTERVENCIONES")
                    trata_metrics[key]["stock_este_ano"] += ea
                    trata_metrics[key]["stock_previo"] += pr
            except Exception as e:
                print("Error stock i:", e)

            # 2. Subsanaciones Abiertas (Oficiales)
            sql_subs_p = f"""
                SELECT sub.trata, sub.descripcion_trata,
                    COUNT(CASE WHEN (
                        CASE WHEN sub.expediente LIKE 'EX-%' AND LENGTH(SPLIT_PART(sub.expediente, '-', 2)) = 4 THEN SPLIT_PART(sub.expediente, '-', 2)::integer
                        WHEN ext.fecha_creacion IS NOT NULL THEN EXTRACT(YEAR FROM ext.fecha_creacion)::integer ELSE 1900 END
                    ) = :y THEN 1 END) as este_ano,
                    COUNT(CASE WHEN (
                        CASE WHEN sub.expediente LIKE 'EX-%' AND LENGTH(SPLIT_PART(sub.expediente, '-', 2)) = 4 THEN SPLIT_PART(sub.expediente, '-', 2)::integer
                        WHEN ext.fecha_creacion IS NOT NULL THEN EXTRACT(YEAR FROM ext.fecha_creacion)::integer ELSE 1900 END
                    ) < :y THEN 1 END) as previo
                FROM mv_{g_clean}_subsanaciones sub
                LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = sub.id_expediente
                WHERE TRIM(sub.trata) = ANY(:tratas)
                GROUP BY sub.trata, sub.descripcion_trata
            """
            try:
                for r in conn.execute(text(sql_subs_p), {"y": target_year, "tratas": tratas_oficiales}).fetchall():
                    ea, pr = int(r[2] or 0), int(r[3] or 0)
                    t_code = (r[0] or "").strip().upper()
                    key = (g_clean, t_code)
                    if key in trata_metrics:
                        trata_metrics[key]["subs_este_ano"] += ea
                        trata_metrics[key]["subs_previo"] += pr
            except Exception as e:
                print("Error subs p:", e)

            # 2b. Subsanaciones Intervenciones
            sql_subs_i = f"""
                SELECT 
                    COUNT(CASE WHEN (
                        CASE WHEN sub.expediente LIKE 'EX-%' AND LENGTH(SPLIT_PART(sub.expediente, '-', 2)) = 4 THEN SPLIT_PART(sub.expediente, '-', 2)::integer
                        WHEN ext.fecha_creacion IS NOT NULL THEN EXTRACT(YEAR FROM ext.fecha_creacion)::integer ELSE 1900 END
                    ) = :y THEN 1 END) as este_ano,
                    COUNT(CASE WHEN (
                        CASE WHEN sub.expediente LIKE 'EX-%' AND LENGTH(SPLIT_PART(sub.expediente, '-', 2)) = 4 THEN SPLIT_PART(sub.expediente, '-', 2)::integer
                        WHEN ext.fecha_creacion IS NOT NULL THEN EXTRACT(YEAR FROM ext.fecha_creacion)::integer ELSE 1900 END
                    ) < :y THEN 1 END) as previo
                FROM mv_{g_clean}_intervenciones_subs sub
                LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = sub.id_expediente
            """
            try:
                r = conn.execute(text(sql_subs_i), {"y": target_year}).fetchone()
                if r:
                    ea, pr = int(r[0] or 0), int(r[1] or 0)
                    key = (g_clean, "INTERVENCIONES")
                    trata_metrics[key]["subs_este_ano"] += ea
                    trata_metrics[key]["subs_previo"] += pr
            except Exception as e:
                print("Error subs i:", e)

            # 3. Ingresos (FILTERED STRICTLY BY CONFIGURED TRATAS)
            sql_ing = f"""
                SELECT trata, descripcion_trata,
                    COUNT(CASE WHEN EXTRACT(YEAR FROM fecha_ingreso) = :y THEN 1 END) as este_ano,
                    COUNT(CASE WHEN EXTRACT(YEAR FROM fecha_ingreso) < :y THEN 1 END) as previo
                FROM mv_{g_clean}_ingresos_eventos
                WHERE TRIM(trata) = ANY(:tratas)
                GROUP BY trata, descripcion_trata
            """
            try:
                for r in conn.execute(text(sql_ing), {"y": target_year, "tratas": tratas_oficiales}).fetchall():
                    ea, pr = int(r[2] or 0), int(r[3] or 0)
                    t_code = (r[0] or "").strip().upper()
                    key = (g_clean, t_code)
                    if key in trata_metrics:
                        trata_metrics[key]["ingresos_este_ano"] += ea
                        trata_metrics[key]["ingresos_previo"] += pr
            except Exception as e:
                print("Error ing:", e)

        tratas_list = list(trata_metrics.values())
        print(f"Total configured tratas in result: {len(tratas_list)}")
        print("\nSample tratas:")
        for t in tratas_list[:10]:
            print(t['gerencia'], t['trata'], t['descripcion_trata'][:30], 'Stock EA:', t['stock_este_ano'], 'Pr:', t['stock_previo'], 'Ing EA:', t['ingresos_este_ano'])

if __name__ == '__main__':
    test_configured_tratas()
