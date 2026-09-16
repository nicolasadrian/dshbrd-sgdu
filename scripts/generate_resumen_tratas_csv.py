import os
import sys
import pandas as pd
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text
from config import TRAMITES_CONFIG

def generate_csv_summary(output_filepath="resumen_ingresos_egresos_por_trata.csv"):
    print("Iniciando cálculo de métricas consolidadas trata por trata...")
    
    # Estructura: key = (gerencia, trata_codigo)
    trata_data = {}
    
    # Inicializar con todas las tratas configuradas
    for g, g_cfg in TRAMITES_CONFIG.items():
        g_clean = g.lower()
        for t_code, cfg in g_cfg.items():
            key = (g_clean, t_code)
            trata_data[key] = {
                "gerencia": g_clean,
                "trata_codigo": t_code,
                "descripcion_trata": cfg.get("nombre", t_code if t_code != "INTERVENCIONES" else "Intervenciones"),
                "tipo_trata": "OFICIAL" if t_code != "INTERVENCIONES" else "INTERVENCION",
                "ingresos_totales": 0,
                "egresos_efectivos_totales": 0,
                "egresos_no_efectivos_totales": 0,
                "egresos_totales": 0
            }
            
    with engine.connect() as conn:
        for g, g_cfg in TRAMITES_CONFIG.items():
            g_clean = g.lower()
            tratas_oficiales = [t for t in g_cfg.keys() if t != 'INTERVENCIONES']
            print(f"Procesando {g_clean}...")
            
            # 1. INGRESOS
            sql_ing = f"""
                SELECT 
                    CASE WHEN TRIM(trata) = ANY(:tratas) THEN TRIM(trata) ELSE 'INTERVENCIONES' END as trata_agrupada,
                    COUNT(*) as cant
                FROM mv_{g_clean}_ingresos_eventos
                GROUP BY 1
            """
            try:
                for r in conn.execute(text(sql_ing), {"tratas": tratas_oficiales}).fetchall():
                    t_code = r[0]
                    key = (g_clean, t_code)
                    if key in trata_data:
                        trata_data[key]["ingresos_totales"] += int(r[1] or 0)
            except Exception as e:
                print(f"Error ingresos en {g_clean}:", e)
                
            # 2. EGRESOS EFECTIVOS (Tratas Propias vía GEDO)
            sql_egr_ef = f"""
                SELECT 
                    CASE WHEN TRIM(trata) = ANY(:tratas) THEN TRIM(trata) ELSE 'INTERVENCIONES' END as trata_agrupada,
                    COUNT(*) as cant
                FROM mv_{g_clean}_gedos_egreso
                GROUP BY 1
            """
            try:
                for r in conn.execute(text(sql_egr_ef), {"tratas": tratas_oficiales}).fetchall():
                    t_code = r[0]
                    key = (g_clean, t_code)
                    if key in trata_data:
                        trata_data[key]["egresos_efectivos_totales"] += int(r[1] or 0)
            except Exception as e:
                print(f"Error egresos efectivos en {g_clean}:", e)

            # 3. EGRESOS EFECTIVOS (Intervenciones Egresadas)
            interv_egr_table = f"mv_{g_clean}_interv_egresos_eventos" if g_clean != 'contable' else "mv_contable_intervenciones_egresadas"
            sql_egr_int = f"""
                SELECT COUNT(*) as cant FROM {interv_egr_table}
            """
            try:
                r = conn.execute(text(sql_egr_int)).fetchone()
                if r:
                    key = (g_clean, "INTERVENCIONES")
                    if key in trata_data:
                        trata_data[key]["egresos_efectivos_totales"] += int(r[0] or 0)
            except Exception as e:
                pass

            # 4. EGRESOS NO EFECTIVOS (Guarda Temporal, Archivo, etc.)
            sql_egr_ne = f"""
                SELECT 
                    CASE WHEN TRIM(trata) = ANY(:tratas) THEN TRIM(trata) ELSE 'INTERVENCIONES' END as trata_agrupada,
                    COUNT(*) as cant
                FROM mv_{g_clean}_egresos_no_efectivos
                GROUP BY 1
            """
            try:
                for r in conn.execute(text(sql_egr_ne), {"tratas": tratas_oficiales}).fetchall():
                    t_code = r[0]
                    key = (g_clean, t_code)
                    if key in trata_data:
                        trata_data[key]["egresos_no_efectivos_totales"] += int(r[1] or 0)
            except Exception as e:
                print(f"Error egresos no efectivos en {g_clean}:", e)

    # Calcular egresos totales
    rows = list(trata_data.values())
    for row in rows:
        row["egresos_totales"] = row["egresos_efectivos_totales"] + row["egresos_no_efectivos_totales"]

    df = pd.DataFrame(rows)
    
    # Exportar a CSV delimitado por punto y coma con UTF-8 BOM
    df.to_csv(output_filepath, index=False, encoding='utf-8-sig', sep=';')
    print(f"\nArchivo generado exitosamente en: {os.path.abspath(output_filepath)}")
    print(f"Total de tratas configuradas exportadas: {len(df)}")
    print("\nPrimeras 15 filas:")
    print(df[['gerencia', 'trata_codigo', 'ingresos_totales', 'egresos_efectivos_totales', 'egresos_no_efectivos_totales', 'egresos_totales']].head(15).to_string())

if __name__ == '__main__':
    generate_csv_summary()
