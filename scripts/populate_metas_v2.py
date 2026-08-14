import sys, time
sys.path.insert(0, './backend')
sys.path.insert(0, '.')
from database import engine
from sqlalchemy import text

g_list = ['catastro', 'instalaciones', 'regularizacion', 'contable', 'etapa_proyecto', 'morfologia', 'aph', 'usos', 'aviso_obra']

def populate():
    t0 = time.time()
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE planificacion_metas_v2_resumen;"))
        conn.commit()

        insert_sql = text("""
            INSERT INTO planificacion_metas_v2_resumen (
                gerencia, trata, descripcion_trata, stock_total, dias_tramitacion_base,
                stock_propio_estancado, stock_flujo, cuota_stock_propio_mensual,
                esc1_ago, esc1_sep, esc1_oct, esc1_nov,
                esc2_ago, esc2_sep, esc2_oct, esc2_nov,
                ing_esc1_ago, ing_esc1_sep, ing_esc1_oct, ing_esc1_nov,
                ing_esc2_ago, ing_esc2_sep, ing_esc2_oct, ing_esc2_nov,
                vence_agosto, vence_septiembre, vence_octubre
            ) VALUES (
                :gerencia, :trata, :descripcion_trata, :stock_total, :dias_tramitacion_base,
                :stock_propio_estancado, :stock_flujo, :cuota_stock_propio_mensual,
                :esc1_ago, :esc1_sep, :esc1_oct, :esc1_nov,
                :esc2_ago, :esc2_sep, :esc2_oct, :esc2_nov,
                :ing_esc1_ago, :ing_esc1_sep, :ing_esc1_oct, :ing_esc1_nov,
                :ing_esc2_ago, :ing_esc2_sep, :ing_esc2_oct, :ing_esc2_nov,
                :vence_agosto, :vence_septiembre, :vence_octubre
            )
        """)

        for g in g_list:
            t_g0 = time.time()
            print(f"Processing gerencia '{g}' for Metas V2...")
            try:
                # 1. Official tratas
                sql_tratas = f"""
                    SELECT trata_reporte, descripcion_trata
                    FROM cfg_gestion_metas
                    WHERE gerencia = '{g}' AND trata_reporte <> 'INTERVENCIONES'
                    ORDER BY trata_reporte
                """
                official_tratas = conn.execute(text(sql_tratas)).mappings().fetchall()

                # 2. Tiempos base (SLA baseline)
                tiempos = {}
                try:
                    with engine.connect() as sub_conn:
                        sql_tiempos = f"SELECT trata, duracion_neta_promedio FROM mv_tiempos_resolucion_{g};"
                        tiempos = {r['trata']: float(r['duracion_neta_promedio'] or 0) for r in sub_conn.execute(text(sql_tiempos)).mappings()}
                except Exception:
                    pass

                # 3. Current stock (Propio)
                sql_stock = f"SELECT id_expediente, trata, COALESCE(dias_en_poder_actual, 0) as dias FROM mv_{g}_stock_propio;"
                expedientes = conn.execute(text(sql_stock)).mappings().fetchall()

                # 4. Ingresos oficiales
                sql_ing = f"""
                    SELECT ext.trata, to_char(ext.fecha_creacion, 'YYYY-MM') as mes_label, COUNT(DISTINCT ext.id_expediente) as cant
                    FROM mv_{g}_universo u
                    JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = u.id_expediente
                    WHERE ext.fecha_creacion >= '2025-01-01'
                    GROUP BY 1, 2
                """
                ing_rows = conn.execute(text(sql_ing)).mappings().fetchall()
                ing_map = {}
                for r in ing_rows:
                    ing_map[(r['trata'], r['mes_label'])] = int(r['cant'] or 0)

                stock_by_trata = {}
                for exp in expedientes:
                    stock_by_trata.setdefault(exp['trata'], []).append(float(exp['dias'] or 0))

                for ot in official_tratas:
                    t = ot['trata_reporte']
                    desc = ot['descripcion_trata']
                    t_base = round(tiempos.get(t, 0.0), 1)

                    exp_list = stock_by_trata.get(t, [])
                    st_total = len(exp_list)
                    st_estancado = sum(1 for d in exp_list if d > t_base)
                    st_flujo = st_total - st_estancado
                    cuota = round(st_estancado / 3.0, 1)

                    ing_esc1_ago = ing_map.get((t, '2025-08'), 0)
                    ing_esc1_sep = ing_map.get((t, '2025-09'), 0)
                    ing_esc1_oct = ing_map.get((t, '2025-10'), 0)
                    ing_esc1_nov = ing_map.get((t, '2025-11'), 0)

                    ing_esc2_base = ing_map.get((t, '2026-07'), 0)
                    ing_esc2_ago = ing_esc2_base
                    ing_esc2_sep = ing_esc2_base
                    ing_esc2_oct = ing_esc2_base
                    ing_esc2_nov = ing_esc2_base

                    v_ago = st_flujo
                    v_sep = ing_esc1_sep if ing_esc1_sep > 0 else ing_esc2_base
                    v_oct = ing_esc1_oct if ing_esc1_oct > 0 else ing_esc2_base

                    esc1_ago = int(round(ing_esc1_ago + cuota))
                    esc1_sep = int(round(ing_esc1_sep + cuota))
                    esc1_oct = int(round(ing_esc1_oct + cuota))
                    esc1_nov = int(round(ing_esc1_nov))

                    esc2_ago = int(round(ing_esc2_ago + cuota))
                    esc2_sep = int(round(ing_esc2_sep + cuota))
                    esc2_oct = int(round(ing_esc2_oct + cuota))
                    esc2_nov = int(round(ing_esc2_nov))

                    conn.execute(insert_sql, {
                        "gerencia": g,
                        "trata": t,
                        "descripcion_trata": desc,
                        "stock_total": st_total,
                        "dias_tramitacion_base": t_base,
                        "stock_propio_estancado": st_estancado,
                        "stock_flujo": st_flujo,
                        "cuota_stock_propio_mensual": cuota,
                        "esc1_ago": esc1_ago, "esc1_sep": esc1_sep, "esc1_oct": esc1_oct, "esc1_nov": esc1_nov,
                        "esc2_ago": esc2_ago, "esc2_sep": esc2_sep, "esc2_oct": esc2_oct, "esc2_nov": esc2_nov,
                        "ing_esc1_ago": ing_esc1_ago, "ing_esc1_sep": ing_esc1_sep, "ing_esc1_oct": ing_esc1_oct, "ing_esc1_nov": ing_esc1_nov,
                        "ing_esc2_ago": ing_esc2_ago, "ing_esc2_sep": ing_esc2_sep, "ing_esc2_oct": ing_esc2_oct, "ing_esc2_nov": ing_esc2_nov,
                        "vence_agosto": v_ago, "vence_septiembre": v_sep, "vence_octubre": v_oct
                    })

                # 5. PROCESS INTERVENCIONES FOR THIS GERENCIA
                exp_int = []
                st_int_total = 0
                try:
                    with engine.connect() as sub_conn:
                        sql_st_int = f"SELECT id_expediente, COALESCE(dias_en_poder_actual, 0) as dias FROM mv_{g}_intervenciones_stock;"
                        exp_int = sub_conn.execute(text(sql_st_int)).mappings().fetchall()
                        st_int_total = len(exp_int)
                except Exception:
                    pass

                t_int_base = 15.0
                try:
                    with engine.connect() as sub_conn:
                        sql_t_int = f"SELECT AVG(duracion_neta_promedio) FROM mv_tiempos_resolucion_intervenciones_{g};"
                        res_t_int = sub_conn.execute(text(sql_t_int)).scalar()
                        if res_t_int is not None:
                            t_int_base = float(res_t_int)
                except Exception:
                    pass
                t_int_base = round(t_int_base, 1)

                st_int_estancado = sum(1 for exp in exp_int if float(exp['dias'] or 0) > t_int_base)
                st_int_flujo = st_int_total - st_int_estancado
                cuota_int = round(st_int_estancado / 3.0, 1)

                ing_int_map = {}
                try:
                    with engine.connect() as sub_conn:
                        sql_ing_int = f"""
                            SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                            FROM mv_{g}_intervenciones_egresadas
                            WHERE fecha_egreso >= '2025-01-01'
                            GROUP BY 1
                        """
                        for r in sub_conn.execute(text(sql_ing_int)).mappings():
                            ing_int_map[r['mes_label']] = int(r['cant'] or 0)
                except Exception:
                    pass

                ing_int_esc1_ago = ing_int_map.get('2025-08', 0)
                ing_int_esc1_sep = ing_int_map.get('2025-09', 0)
                ing_int_esc1_oct = ing_int_map.get('2025-10', 0)
                ing_int_esc1_nov = ing_int_map.get('2025-11', 0)

                ing_int_esc2_base = ing_int_map.get('2026-07', 0)
                ing_int_esc2_ago = ing_int_esc2_base
                ing_int_esc2_sep = ing_int_esc2_base
                ing_int_esc2_oct = ing_int_esc2_base
                ing_int_esc2_nov = ing_int_esc2_base

                v_int_ago = st_int_flujo
                v_int_sep = ing_int_esc1_sep if ing_int_esc1_sep > 0 else ing_int_esc2_base
                v_int_oct = ing_int_esc1_oct if ing_int_esc1_oct > 0 else ing_int_esc2_base

                esc1_int_ago = int(round(ing_int_esc1_ago + cuota_int))
                esc1_int_sep = int(round(ing_int_esc1_sep + cuota_int))
                esc1_int_oct = int(round(ing_int_esc1_oct + cuota_int))
                esc1_int_nov = int(round(ing_int_esc1_nov))

                esc2_int_ago = int(round(ing_int_esc2_ago + cuota_int))
                esc2_int_sep = int(round(ing_int_esc2_sep + cuota_int))
                esc2_int_oct = int(round(ing_int_esc2_oct + cuota_int))
                esc2_int_nov = int(round(ing_int_esc2_nov))

                conn.execute(insert_sql, {
                    "gerencia": g,
                    "trata": "INTERVENCIONES",
                    "descripcion_trata": "Intervenciones del Sector",
                    "stock_total": st_int_total,
                    "dias_tramitacion_base": t_int_base,
                    "stock_propio_estancado": st_int_estancado,
                    "stock_flujo": st_int_flujo,
                    "cuota_stock_propio_mensual": cuota_int,
                    "esc1_ago": esc1_int_ago, "esc1_sep": esc1_int_sep, "esc1_oct": esc1_int_oct, "esc1_nov": esc1_int_nov,
                    "esc2_ago": esc2_int_ago, "esc2_sep": esc2_int_sep, "esc2_oct": esc2_int_oct, "esc2_nov": esc2_int_nov,
                    "ing_esc1_ago": ing_int_esc1_ago, "ing_esc1_sep": ing_int_esc1_sep, "ing_esc1_oct": ing_int_esc1_oct, "ing_esc1_nov": ing_int_esc1_nov,
                    "ing_esc2_ago": ing_int_esc2_ago, "ing_esc2_sep": ing_int_esc2_sep, "ing_esc2_oct": ing_int_esc2_oct, "ing_esc2_nov": ing_int_esc2_nov,
                    "vence_agosto": v_int_ago, "vence_septiembre": v_int_sep, "vence_octubre": v_int_oct
                })

                conn.commit()
                print(f"  Gerencia '{g}' Metas V2 (official + intervenciones) populated in {round(time.time() - t_g0, 2)}s.")
            except Exception as e:
                print(f"  Error populating Metas V2 for gerencia '{g}': {e}")
                conn.rollback()

    print(f"All Metas V2 (official + intervenciones) populated in {round(time.time() - t0, 2)}s!")

if __name__ == '__main__':
    populate()
