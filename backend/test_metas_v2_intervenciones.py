from database import engine
from sqlalchemy import text

g_list = ['catastro', 'instalaciones', 'regularizacion', 'contable', 'etapa_proyecto', 'morfologia', 'aph', 'usos', 'aviso_obra']

for g in g_list:
    with engine.connect() as conn:
        # Stock
        try:
            sql_st = f"SELECT id_expediente, COALESCE(dias_en_poder_actual, 0) as dias FROM mv_{g}_intervenciones_stock;"
            rows_st = conn.execute(text(sql_st)).mappings().fetchall()
            st_tot = len(rows_st)
        except Exception as e:
            rows_st = []
            st_tot = 0

        # Baseline processing days for intervenciones
        t_base = 15.0
        try:
            sql_t = f"SELECT AVG(duracion_neta_promedio) as avg_dias FROM mv_tiempos_resolucion_intervenciones_{g};"
            res_t = conn.execute(text(sql_t)).scalar()
            if res_t is not None:
                t_base = float(res_t)
        except Exception:
            pass
        t_base = round(t_base, 1)

        st_estancado = sum(1 for r in rows_st if float(r['dias'] or 0) > t_base)
        st_flujo = st_tot - st_estancado
        cuota = round(st_estancado / 3.0, 1)

        # Ingresos / Eventos
        ing_map = {}
        try:
            sql_ing = f"""
                SELECT to_char(fecha_ingreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                FROM mv_{g}_interv_egresos_eventos
                WHERE fecha_ingreso >= '2025-01-01'
                GROUP BY 1
            """
            for r in conn.execute(text(sql_ing)).mappings():
                ing_map[r['mes_label']] = int(r['cant'] or 0)
        except Exception:
            pass

        ing_esc2_base = ing_map.get('2026-07', 0)

        print(f"Gerencia {g:15s} | Stock Interv: {st_tot:4d} | Estancado: {st_estancado:4d} | Flujo: {st_flujo:4d} | Cuota: {cuota:5.1f} | Ing Jul26: {ing_esc2_base:4d}")
