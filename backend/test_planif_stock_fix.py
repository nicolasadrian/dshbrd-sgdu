import sys, time
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text
from config import TRAMITES_CONFIG

def test_full_fix(target_year=2026):
    with engine.connect() as conn:
        for g, g_cfg in TRAMITES_CONFIG.items():
            g_clean = g.lower()
            tratas_oficiales = [t for t in g_cfg.keys() if t != 'INTERVENCIONES']

            g_stock_ea = 0; g_stock_pr = 0
            g_subs_ea = 0; g_subs_pr = 0
            g_ing_ea = 0; g_ing_pr = 0

            # 1. Stock (Propio + Intervenciones)
            # Propio
            sql_stock_p = f"""
                SELECT sp.expediente, ext.fecha_creacion
                FROM mv_{g_clean}_stock_propio sp
                LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = sp.id_expediente
                WHERE TRIM(sp.trata) = ANY(:tratas)
            """
            for r in conn.execute(text(sql_stock_p), {"tratas": tratas_oficiales}).mappings():
                year = None
                exp_num = r['expediente'] or ''
                if 'EX-' in exp_num:
                    parts = exp_num.split('-')
                    if len(parts) >= 2 and parts[1].isdigit() and len(parts[1]) == 4:
                        year = int(parts[1])
                if not year and r['fecha_creacion']:
                    year = r['fecha_creacion'].year
                if not year: year = 1900
                if year == target_year: g_stock_ea += 1
                else: g_stock_pr += 1

            # Intervenciones
            sql_stock_i = f"""
                SELECT sp.expediente, ext.fecha_creacion
                FROM mv_{g_clean}_intervenciones_stock sp
                LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = sp.id_expediente
            """
            try:
                for r in conn.execute(text(sql_stock_i)).mappings():
                    year = None
                    exp_num = r['expediente'] or ''
                    if 'EX-' in exp_num:
                        parts = exp_num.split('-')
                        if len(parts) >= 2 and parts[1].isdigit() and len(parts[1]) == 4:
                            year = int(parts[1])
                    if not year and r['fecha_creacion']:
                        year = r['fecha_creacion'].year
                    if not year: year = 1900
                    if year == target_year: g_stock_ea += 1
                    else: g_stock_pr += 1
            except Exception: pass

            # 2. Subsanaciones (Propio + Intervenciones)
            sql_subs_p = f"""
                SELECT sub.expediente, ext.fecha_creacion
                FROM mv_{g_clean}_subsanaciones sub
                LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = sub.id_expediente
                WHERE TRIM(sub.trata) = ANY(:tratas)
            """
            for r in conn.execute(text(sql_subs_p), {"tratas": tratas_oficiales}).mappings():
                year = None
                exp_num = r['expediente'] or ''
                if 'EX-' in exp_num:
                    parts = exp_num.split('-')
                    if len(parts) >= 2 and parts[1].isdigit() and len(parts[1]) == 4:
                        year = int(parts[1])
                if not year and r['fecha_creacion']:
                    year = r['fecha_creacion'].year
                if not year: year = 1900
                if year == target_year: g_subs_ea += 1
                else: g_subs_pr += 1

            sql_subs_i = f"""
                SELECT sub.expediente, ext.fecha_creacion
                FROM mv_{g_clean}_intervenciones_subs sub
                LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = sub.id_expediente
            """
            try:
                for r in conn.execute(text(sql_subs_i)).mappings():
                    year = None
                    exp_num = r['expediente'] or ''
                    if 'EX-' in exp_num:
                        parts = exp_num.split('-')
                        if len(parts) >= 2 and parts[1].isdigit() and len(parts[1]) == 4:
                            year = int(parts[1])
                    if not year and r['fecha_creacion']:
                        year = r['fecha_creacion'].year
                    if not year: year = 1900
                    if year == target_year: g_subs_ea += 1
                    else: g_subs_pr += 1
            except Exception: pass

            # 3. Ingresos
            sql_ing = f"""
                SELECT fecha_ingreso
                FROM mv_{g_clean}_ingresos_eventos
            """
            try:
                for r in conn.execute(text(sql_ing)).mappings():
                    if r['fecha_ingreso'] and r['fecha_ingreso'].year == target_year:
                        g_ing_ea += 1
                    else:
                        g_ing_pr += 1
            except Exception: pass

            print(f"{g_clean:15s} | Stock: {g_stock_ea + g_stock_pr:5d} (EA:{g_stock_ea:4d}/PR:{g_stock_pr:4d}) | Subs: {g_subs_ea + g_subs_pr:5d} (EA:{g_subs_ea:4d}/PR:{g_subs_pr:4d}) | Ing: {g_ing_ea + g_ing_pr:6d}")

if __name__ == '__main__':
    test_full_fix()
