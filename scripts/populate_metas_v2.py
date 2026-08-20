import sys, time
sys.path.insert(0, './backend')
sys.path.insert(0, '.')
from database import engine
from sqlalchemy import text

g_list = ['catastro', 'instalaciones', 'regularizacion', 'contable', 'etapa_proyecto', 'morfologia', 'aph', 'usos', 'aviso_obra']

def populate():
    t0 = time.time()
    with engine.connect() as conn:
        print("=== RE-CREATING planificacion_metas_v2_resumen TABLE ===")
        conn.execute(text("DROP TABLE IF EXISTS planificacion_metas_v2_resumen CASCADE;"))
        conn.execute(text("""
            CREATE TABLE planificacion_metas_v2_resumen (
                gerencia VARCHAR(50),
                trata VARCHAR(50),
                descripcion_trata VARCHAR(255),
                stock_total INT,
                
                -- Modelo Base: Mediana Último Mes Cerrado (Escenarios 1 y 2)
                dias_tramitacion_base NUMERIC(10, 1),
                stock_propio_estancado INT,
                stock_flujo INT,
                cuota_stock_propio_mensual NUMERIC(10, 1),
                
                -- Modelo Año Actual: Mediana de Expedientes Ingresados Este Año (Escenarios 3 y 4)
                dias_tramitacion_este_ano NUMERIC(10, 1),
                stock_propio_estancado_este_ano INT,
                stock_flujo_este_ano INT,
                cuota_stock_propio_mensual_este_ano NUMERIC(10, 1),

                -- Escenario 1: Ingresos Interanuales + Stock Mes Cerrado
                esc1_ago INT, esc1_sep INT, esc1_oct INT, esc1_nov INT,
                ing_esc1_ago INT, ing_esc1_sep INT, ing_esc1_oct INT, ing_esc1_nov INT,

                -- Escenario 2: Ingresos Mes Anterior + Stock Mes Cerrado
                esc2_ago INT, esc2_sep INT, esc2_oct INT, esc2_nov INT,
                ing_esc2_ago INT, ing_esc2_sep INT, ing_esc2_oct INT, ing_esc2_nov INT,

                -- Escenario 3: Ingresos Interanuales + Stock Caratulados Este Año
                esc3_ago INT, esc3_sep INT, esc3_oct INT, esc3_nov INT,
                ing_esc3_ago INT, ing_esc3_sep INT, ing_esc3_oct INT, ing_esc3_nov INT,

                -- Escenario 4: Ingresos Mes Anterior + Stock Caratulados Este Año
                esc4_ago INT, esc4_sep INT, esc4_oct INT, esc4_nov INT,
                ing_esc4_ago INT, ing_esc4_sep INT, ing_esc4_oct INT, ing_esc4_nov INT,

                -- Vencimientos de Flujo
                vence_agosto INT, vence_septiembre INT, vence_octubre INT,
                vence_agosto_este_ano INT, vence_septiembre_este_ano INT, vence_octubre_este_ano INT
            );
        """))
        conn.commit()

        insert_sql = text("""
            INSERT INTO planificacion_metas_v2_resumen (
                gerencia, trata, descripcion_trata, stock_total,
                dias_tramitacion_base, stock_propio_estancado, stock_flujo, cuota_stock_propio_mensual,
                dias_tramitacion_este_ano, stock_propio_estancado_este_ano, stock_flujo_este_ano, cuota_stock_propio_mensual_este_ano,
                esc1_ago, esc1_sep, esc1_oct, esc1_nov,
                ing_esc1_ago, ing_esc1_sep, ing_esc1_oct, ing_esc1_nov,
                esc2_ago, esc2_sep, esc2_oct, esc2_nov,
                ing_esc2_ago, ing_esc2_sep, ing_esc2_oct, ing_esc2_nov,
                esc3_ago, esc3_sep, esc3_oct, esc3_nov,
                ing_esc3_ago, ing_esc3_sep, ing_esc3_oct, ing_esc3_nov,
                esc4_ago, esc4_sep, esc4_oct, esc4_nov,
                ing_esc4_ago, ing_esc4_sep, ing_esc4_oct, ing_esc4_nov,
                vence_agosto, vence_septiembre, vence_octubre,
                vence_agosto_este_ano, vence_septiembre_este_ano, vence_octubre_este_ano
            ) VALUES (
                :gerencia, :trata, :descripcion_trata, :stock_total,
                :dias_tramitacion_base, :stock_propio_estancado, :stock_flujo, :cuota_stock_propio_mensual,
                :dias_tramitacion_este_ano, :stock_propio_estancado_este_ano, :stock_flujo_este_ano, :cuota_stock_propio_mensual_este_ano,
                :esc1_ago, :esc1_sep, :esc1_oct, :esc1_nov,
                :ing_esc1_ago, :ing_esc1_sep, :ing_esc1_oct, :ing_esc1_nov,
                :esc2_ago, :esc2_sep, :esc2_oct, :esc2_nov,
                :ing_esc2_ago, :ing_esc2_sep, :ing_esc2_oct, :ing_esc2_nov,
                :esc3_ago, :esc3_sep, :esc3_oct, :esc3_nov,
                :ing_esc3_ago, :ing_esc3_sep, :ing_esc3_oct, :ing_esc3_nov,
                :esc4_ago, :esc4_sep, :esc4_oct, :esc4_nov,
                :ing_esc4_ago, :ing_esc4_sep, :ing_esc4_oct, :ing_esc4_nov,
                :vence_agosto, :vence_septiembre, :vence_octubre,
                :vence_agosto_este_ano, :vence_septiembre_este_ano, :vence_octubre_este_ano
            )
        """)

        # Cargar tiempos desde la tabla de tiempos de tramitación (mediana del mes cerrado y mediana de ingresados este año)
        sql_tiempos_resumen = """
            SELECT gerencia, trata, dias_propio_sector, dias_totales, dias_mediana_ingresados_este_ano
            FROM planificacion_tiempos_tramitacion_resumen
        """
        tiempos_map = {}
        for r in conn.execute(text(sql_tiempos_resumen)).mappings():
            # Guardamos dias_propio_sector (si es > 0, sino dias_totales) y dias_mediana_ingresados_este_ano
            t_base_val = float(r['dias_propio_sector'] or 0)
            if t_base_val <= 0:
                t_base_val = float(r['dias_totales'] or 0)
            
            t_ea_val = float(r['dias_mediana_ingresados_este_ano'] or 0)
            if t_ea_val <= 0:
                t_ea_val = t_base_val

            tiempos_map[(r['gerencia'], r['trata'])] = {
                "t_base": t_base_val,
                "t_este_ano": t_ea_val
            }

        for g in g_list:
            t_g0 = time.time()
            print(f"Processing gerencia '{g}' for Metas V2 (4 Scenarios)...")
            try:
                # 1. Official tratas
                sql_tratas = f"""
                    SELECT trata_reporte, descripcion_trata
                    FROM cfg_gestion_metas
                    WHERE gerencia = '{g}' AND trata_reporte <> 'INTERVENCIONES'
                    ORDER BY trata_reporte
                """
                official_tratas = conn.execute(text(sql_tratas)).mappings().fetchall()

                # 2. Current stock (Propio)
                sql_stock = f"SELECT id_expediente, trata, COALESCE(dias_en_poder_actual, 0) as dias FROM mv_{g}_stock_propio;"
                expedientes = conn.execute(text(sql_stock)).mappings().fetchall()

                # 3. Ingresos oficiales
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
                    
                    t_info = tiempos_map.get((g, t), {"t_base": 0.0, "t_este_ano": 0.0})
                    t_base = round(t_info["t_base"], 1)
                    t_este_ano = round(t_info["t_este_ano"], 1)

                    exp_list = stock_by_trata.get(t, [])
                    st_total = len(exp_list)

                    # --- Base 1: Mes Cerrado ---
                    st_estancado_1 = sum(1 for d in exp_list if d > t_base)
                    st_flujo_1 = st_total - st_estancado_1
                    cuota_1 = round(st_estancado_1 / 3.0, 1)

                    # --- Base 2: Ingresados Este Año ---
                    st_estancado_2 = sum(1 for d in exp_list if d > t_este_ano)
                    st_flujo_2 = st_total - st_estancado_2
                    cuota_2 = round(st_estancado_2 / 3.0, 1)

                    # Ingresos Interanuales (2025)
                    ing_esc1_ago = ing_map.get((t, '2025-08'), 0)
                    ing_esc1_sep = ing_map.get((t, '2025-09'), 0)
                    ing_esc1_oct = ing_map.get((t, '2025-10'), 0)
                    ing_esc1_nov = ing_map.get((t, '2025-11'), 0)

                    # Ingresos Flat Mes Anterior (Julio 2026)
                    ing_esc2_base = ing_map.get((t, '2026-07'), 0)
                    ing_esc2_ago = ing_esc2_base
                    ing_esc2_sep = ing_esc2_base
                    ing_esc2_oct = ing_esc2_base
                    ing_esc2_nov = ing_esc2_base

                    # Vencimientos Flujo Base 1
                    v_ago_1 = st_flujo_1
                    v_sep_1 = ing_esc1_sep if ing_esc1_sep > 0 else ing_esc2_base
                    v_oct_1 = ing_esc1_oct if ing_esc1_oct > 0 else ing_esc2_base

                    # Vencimientos Flujo Base 2
                    v_ago_2 = st_flujo_2
                    v_sep_2 = ing_esc1_sep if ing_esc1_sep > 0 else ing_esc2_base
                    v_oct_2 = ing_esc1_oct if ing_esc1_oct > 0 else ing_esc2_base

                    # Escenario 1 (Interanual + Cuota Mes Cerrado)
                    esc1_ago = int(round(ing_esc1_ago + cuota_1))
                    esc1_sep = int(round(ing_esc1_sep + cuota_1))
                    esc1_oct = int(round(ing_esc1_oct + cuota_1))
                    esc1_nov = int(round(ing_esc1_nov))

                    # Escenario 2 (Mes Anterior + Cuota Mes Cerrado)
                    esc2_ago = int(round(ing_esc2_ago + cuota_1))
                    esc2_sep = int(round(ing_esc2_sep + cuota_1))
                    esc2_oct = int(round(ing_esc2_oct + cuota_1))
                    esc2_nov = int(round(ing_esc2_nov))

                    # Escenario 3 (Interanual + Cuota Ingresados Este Año)
                    esc3_ago = int(round(ing_esc1_ago + cuota_2))
                    esc3_sep = int(round(ing_esc1_sep + cuota_2))
                    esc3_oct = int(round(ing_esc1_oct + cuota_2))
                    esc3_nov = int(round(ing_esc1_nov))

                    # Escenario 4 (Mes Anterior + Cuota Ingresados Este Año)
                    esc4_ago = int(round(ing_esc2_ago + cuota_2))
                    esc4_sep = int(round(ing_esc2_sep + cuota_2))
                    esc4_oct = int(round(ing_esc2_oct + cuota_2))
                    esc4_nov = int(round(ing_esc2_nov))

                    conn.execute(insert_sql, {
                        "gerencia": g,
                        "trata": t,
                        "descripcion_trata": desc,
                        "stock_total": st_total,
                        "dias_tramitacion_base": t_base,
                        "stock_propio_estancado": st_estancado_1,
                        "stock_flujo": st_flujo_1,
                        "cuota_stock_propio_mensual": cuota_1,
                        "dias_tramitacion_este_ano": t_este_ano,
                        "stock_propio_estancado_este_ano": st_estancado_2,
                        "stock_flujo_este_ano": st_flujo_2,
                        "cuota_stock_propio_mensual_este_ano": cuota_2,
                        "esc1_ago": esc1_ago, "esc1_sep": esc1_sep, "esc1_oct": esc1_oct, "esc1_nov": esc1_nov,
                        "ing_esc1_ago": ing_esc1_ago, "ing_esc1_sep": ing_esc1_sep, "ing_esc1_oct": ing_esc1_oct, "ing_esc1_nov": ing_esc1_nov,
                        "esc2_ago": esc2_ago, "esc2_sep": esc2_sep, "esc2_oct": esc2_oct, "esc2_nov": esc2_nov,
                        "ing_esc2_ago": ing_esc2_ago, "ing_esc2_sep": ing_esc2_sep, "ing_esc2_oct": ing_esc2_oct, "ing_esc2_nov": ing_esc2_nov,
                        "esc3_ago": esc3_ago, "esc3_sep": esc3_sep, "esc3_oct": esc3_oct, "esc3_nov": esc3_nov,
                        "ing_esc3_ago": ing_esc1_ago, "ing_esc3_sep": ing_esc1_sep, "ing_esc3_oct": ing_esc1_oct, "ing_esc3_nov": ing_esc1_nov,
                        "esc4_ago": esc4_ago, "esc4_sep": esc4_oct, "esc4_oct": esc4_oct, "esc4_nov": esc4_nov,
                        "ing_esc4_ago": ing_esc2_ago, "ing_esc4_sep": ing_esc2_sep, "ing_esc4_oct": ing_esc2_oct, "ing_esc4_nov": ing_esc2_nov,
                        "vence_agosto": v_ago_1, "vence_septiembre": v_sep_1, "vence_octubre": v_oct_1,
                        "vence_agosto_este_ano": v_ago_2, "vence_septiembre_este_ano": v_sep_2, "vence_octubre_este_ano": v_oct_2
                    })

                # 4. PROCESS INTERVENCIONES FOR THIS GERENCIA
                exp_int = []
                st_int_total = 0
                try:
                    with engine.connect() as sub_conn:
                        sql_st_int = f"SELECT id_expediente, COALESCE(dias_en_poder_actual, 0) as dias FROM mv_{g}_intervenciones_stock;"
                        exp_int = sub_conn.execute(text(sql_st_int)).mappings().fetchall()
                        st_int_total = len(exp_int)
                except Exception:
                    pass

                t_int_info = tiempos_map.get((g, 'INTERVENCIONES'), {"t_base": 15.0, "t_este_ano": 15.0})
                t_int_base = round(t_int_info["t_base"], 1)
                t_int_este_ano = round(t_int_info["t_este_ano"], 1)
                if t_int_base <= 0: t_int_base = 15.0
                if t_int_este_ano <= 0: t_int_este_ano = t_int_base

                st_int_estancado_1 = sum(1 for exp in exp_int if float(exp['dias'] or 0) > t_int_base)
                st_int_flujo_1 = st_int_total - st_int_estancado_1
                cuota_int_1 = round(st_int_estancado_1 / 3.0, 1)

                st_int_estancado_2 = sum(1 for exp in exp_int if float(exp['dias'] or 0) > t_int_este_ano)
                st_int_flujo_2 = st_int_total - st_int_estancado_2
                cuota_int_2 = round(st_int_estancado_2 / 3.0, 1)

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

                v_int_ago_1 = st_int_flujo_1
                v_int_sep_1 = ing_int_esc1_sep if ing_int_esc1_sep > 0 else ing_int_esc2_base
                v_int_oct_1 = ing_int_esc1_oct if ing_int_esc1_oct > 0 else ing_int_esc2_base

                v_int_ago_2 = st_int_flujo_2
                v_int_sep_2 = ing_int_esc1_sep if ing_int_esc1_sep > 0 else ing_int_esc2_base
                v_int_oct_2 = ing_int_esc1_oct if ing_int_esc1_oct > 0 else ing_int_esc2_base

                esc1_int_ago = int(round(ing_int_esc1_ago + cuota_int_1))
                esc1_int_sep = int(round(ing_int_esc1_sep + cuota_int_1))
                esc1_int_oct = int(round(ing_int_esc1_oct + cuota_int_1))
                esc1_int_nov = int(round(ing_int_esc1_nov))

                esc2_int_ago = int(round(ing_int_esc2_ago + cuota_int_1))
                esc2_int_sep = int(round(ing_int_esc2_sep + cuota_int_1))
                esc2_int_oct = int(round(ing_int_esc2_oct + cuota_int_1))
                esc2_int_nov = int(round(ing_int_esc2_nov))

                esc3_int_ago = int(round(ing_int_esc1_ago + cuota_int_2))
                esc3_int_sep = int(round(ing_int_esc1_sep + cuota_int_2))
                esc3_int_oct = int(round(ing_int_esc1_oct + cuota_int_2))
                esc3_int_nov = int(round(ing_int_esc1_nov))

                esc4_int_ago = int(round(ing_int_esc2_ago + cuota_int_2))
                esc4_int_sep = int(round(ing_int_esc2_sep + cuota_int_2))
                esc4_int_oct = int(round(ing_int_esc2_oct + cuota_int_2))
                esc4_int_nov = int(round(ing_int_esc2_nov))

                conn.execute(insert_sql, {
                    "gerencia": g,
                    "trata": "INTERVENCIONES",
                    "descripcion_trata": "Intervenciones del Sector",
                    "stock_total": st_int_total,
                    "dias_tramitacion_base": t_int_base,
                    "stock_propio_estancado": st_int_estancado_1,
                    "stock_flujo": st_int_flujo_1,
                    "cuota_stock_propio_mensual": cuota_int_1,
                    "dias_tramitacion_este_ano": t_int_este_ano,
                    "stock_propio_estancado_este_ano": st_int_estancado_2,
                    "stock_flujo_este_ano": st_int_flujo_2,
                    "cuota_stock_propio_mensual_este_ano": cuota_int_2,
                    "esc1_ago": esc1_int_ago, "esc1_sep": esc1_int_sep, "esc1_oct": esc1_int_oct, "esc1_nov": esc1_int_nov,
                    "ing_esc1_ago": ing_int_esc1_ago, "ing_esc1_sep": ing_int_esc1_sep, "ing_esc1_oct": ing_int_esc1_oct, "ing_esc1_nov": ing_int_esc1_nov,
                    "esc2_ago": esc2_int_ago, "esc2_sep": esc2_int_sep, "esc2_oct": esc2_int_oct, "esc2_nov": esc2_int_nov,
                    "ing_esc2_ago": ing_int_esc2_ago, "ing_esc2_sep": ing_int_esc2_sep, "ing_esc2_oct": ing_int_esc2_oct, "ing_esc2_nov": ing_int_esc2_nov,
                    "esc3_ago": esc3_int_ago, "esc3_sep": esc3_int_sep, "esc3_oct": esc3_int_oct, "esc3_nov": esc3_int_nov,
                    "ing_esc3_ago": ing_int_esc1_ago, "ing_esc3_sep": ing_int_esc1_sep, "ing_esc3_oct": ing_int_esc1_oct, "ing_esc3_nov": ing_int_esc1_nov,
                    "esc4_ago": esc4_int_ago, "esc4_sep": esc4_int_sep, "esc4_oct": esc4_int_oct, "esc4_nov": esc4_int_nov,
                    "ing_esc4_ago": ing_int_esc2_ago, "ing_esc4_sep": ing_int_esc2_sep, "ing_esc4_oct": ing_int_esc2_oct, "ing_esc4_nov": ing_int_esc2_nov,
                    "vence_agosto": v_int_ago_1, "vence_septiembre": v_int_sep_1, "vence_octubre": v_int_oct_1,
                    "vence_agosto_este_ano": v_int_ago_2, "vence_septiembre_este_ano": v_int_sep_2, "vence_octubre_este_ano": v_int_oct_2
                })

                conn.commit()
                print(f"  Gerencia '{g}' Metas V2 (4 Scenarios) populated in {round(time.time() - t_g0, 2)}s.")
            except Exception as e:
                print(f"  Error populating Metas V2 for gerencia '{g}': {e}")
                conn.rollback()

    print(f"All 4 Metas V2 scenarios populated in {round(time.time() - t0, 2)}s!")

if __name__ == '__main__':
    populate()
