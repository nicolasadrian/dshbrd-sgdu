import os
import sys
import pandas as pd
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text
from config import TRAMITES_CONFIG

def generate_csv_all_movements(output_filepath="detalle_ingresos_egresos_todas_tratas.csv"):
    print("Iniciando extracción de movimientos para todas las tratas configuradas...")
    
    rows = []
    
    with engine.connect() as conn:
        for g, g_cfg in TRAMITES_CONFIG.items():
            g_clean = g.lower()
            tratas_oficiales = [t for t in g_cfg.keys() if t != 'INTERVENCIONES']
            print(f"\nProcesando Gerencia: {g_clean} ({len(tratas_oficiales)} tratas oficiales + Intervenciones)...")
            
            # 1. INGRESOS
            sql_ing = f"""
                SELECT 
                    id_expediente,
                    expediente,
                    trata,
                    descripcion_trata,
                    fecha_ingreso as fecha_evento,
                    usuario_remitente as usuario_responsable_o_remitente,
                    buzon,
                    buzon_ingreso
                FROM mv_{g_clean}_ingresos_eventos
            """
            try:
                ing_res = conn.execute(text(sql_ing)).fetchall()
                for r in ing_res:
                    m = dict(r._mapping)
                    t_code = (m.get('trata') or '').strip().upper()
                    
                    # Determinar si es trata oficial de la gerencia o intervención
                    if t_code in tratas_oficiales:
                        tipo_trata = "TRATA_OFICIAL"
                        desc_config = g_cfg[t_code].get('nombre', m.get('descripcion_trata'))
                    else:
                        tipo_trata = "INTERVENCION"
                        desc_config = "Intervenciones del Sector"
                    
                    rows.append({
                        "gerencia": g_clean,
                        "tipo_movimiento": "INGRESO",
                        "clasificacion_movimiento": "INGRESO",
                        "trata_codigo": t_code,
                        "descripcion_trata": desc_config or m.get('descripcion_trata'),
                        "tipo_trata": tipo_trata,
                        "id_expediente": m.get('id_expediente'),
                        "expediente": m.get('expediente'),
                        "fecha_evento": m.get('fecha_evento'),
                        "usuario": m.get('usuario_responsable_o_remitente'),
                        "documento_gedo": None,
                        "acronimo_gedo": None,
                        "buzon": m.get('buzon'),
                        "buzon_ingreso": m.get('buzon_ingreso'),
                        "destino_externo": None,
                        "estado_expediente": None,
                        "poseedor_actual": None
                    })
                print(f"  -> {len(ing_res)} ingresos procesados.")
            except Exception as e:
                print(f"  Error extrayendo ingresos de {g_clean}:", e)

            # 2. EGRESOS EFECTIVOS (Tratas Propias vía GEDO)
            sql_egr_ef = f"""
                SELECT 
                    id_expediente,
                    expediente,
                    trata,
                    descripcion_trata,
                    documento_egreso,
                    acronimo_egreso,
                    fecha_egreso as fecha_evento,
                    usuario_egreso
                FROM mv_{g_clean}_gedos_egreso
            """
            try:
                egr_ef_res = conn.execute(text(sql_egr_ef)).fetchall()
                for r in egr_ef_res:
                    m = dict(r._mapping)
                    t_code = (m.get('trata') or '').strip().upper()
                    
                    if t_code in tratas_oficiales:
                        tipo_trata = "TRATA_OFICIAL"
                        desc_config = g_cfg[t_code].get('nombre', m.get('descripcion_trata'))
                    else:
                        tipo_trata = "INTERVENCION"
                        desc_config = "Intervenciones del Sector"
                    
                    rows.append({
                        "gerencia": g_clean,
                        "tipo_movimiento": "EGRESO",
                        "clasificacion_movimiento": "EGRESO_EFECTIVO",
                        "trata_codigo": t_code,
                        "descripcion_trata": desc_config or m.get('descripcion_trata'),
                        "tipo_trata": tipo_trata,
                        "id_expediente": m.get('id_expediente'),
                        "expediente": m.get('expediente'),
                        "fecha_evento": m.get('fecha_evento'),
                        "usuario": m.get('usuario_egreso'),
                        "documento_gedo": m.get('documento_egreso'),
                        "acronimo_gedo": m.get('acronimo_egreso'),
                        "buzon": None,
                        "buzon_ingreso": None,
                        "destino_externo": None,
                        "estado_expediente": None,
                        "poseedor_actual": None
                    })
                print(f"  -> {len(egr_ef_res)} egresos efectivos (GEDO) procesados.")
            except Exception as e:
                print(f"  Error extrayendo egresos efectivos de {g_clean}:", e)

            # 3. EGRESOS EFECTIVOS (Intervenciones Egresadas / Pase externo)
            interv_egr_table = f"mv_{g_clean}_interv_egresos_eventos" if g_clean != 'contable' else "mv_contable_intervenciones_egresadas"
            sql_egr_int = f"""
                SELECT 
                    id_expediente,
                    expediente,
                    trata,
                    descripcion_trata,
                    fecha_egreso as fecha_evento,
                    usuario_que_envia,
                    destino_externo
                FROM {interv_egr_table}
            """
            try:
                egr_int_res = conn.execute(text(sql_egr_int)).fetchall()
                for r in egr_int_res:
                    m = dict(r._mapping)
                    t_code = (m.get('trata') or '').strip().upper()
                    
                    rows.append({
                        "gerencia": g_clean,
                        "tipo_movimiento": "EGRESO",
                        "clasificacion_movimiento": "EGRESO_EFECTIVO_INTERVENCION",
                        "trata_codigo": t_code or "INTERVENCIONES",
                        "descripcion_trata": "Intervenciones del Sector",
                        "tipo_trata": "INTERVENCION",
                        "id_expediente": m.get('id_expediente'),
                        "expediente": m.get('expediente'),
                        "fecha_evento": m.get('fecha_evento'),
                        "usuario": m.get('usuario_que_envia'),
                        "documento_gedo": None,
                        "acronimo_gedo": None,
                        "buzon": None,
                        "buzon_ingreso": None,
                        "destino_externo": m.get('destino_externo'),
                        "estado_expediente": None,
                        "poseedor_actual": None
                    })
                print(f"  -> {len(egr_int_res)} egresos efectivos de intervenciones procesados.")
            except Exception as e:
                print(f"  Aviso/Error extrayendo intervenciones egresadas de {g_clean}:", e)

            # 4. EGRESOS NO EFECTIVOS (Guarda Temporal, Archivo, etc.)
            sql_egr_ne = f"""
                SELECT 
                    id_expediente,
                    expediente,
                    trata,
                    descripcion_trata,
                    estado_expediente,
                    fecha_ultimo_movimiento as fecha_evento,
                    poseedor_actual
                FROM mv_{g_clean}_egresos_no_efectivos
            """
            try:
                egr_ne_res = conn.execute(text(sql_egr_ne)).fetchall()
                for r in egr_ne_res:
                    m = dict(r._mapping)
                    t_code = (m.get('trata') or '').strip().upper()
                    
                    if t_code in tratas_oficiales:
                        tipo_trata = "TRATA_OFICIAL"
                        desc_config = g_cfg[t_code].get('nombre', m.get('descripcion_trata'))
                    else:
                        tipo_trata = "INTERVENCION"
                        desc_config = "Intervenciones del Sector"
                    
                    rows.append({
                        "gerencia": g_clean,
                        "tipo_movimiento": "EGRESO",
                        "clasificacion_movimiento": "EGRESO_NO_EFECTIVO",
                        "trata_codigo": t_code,
                        "descripcion_trata": desc_config or m.get('descripcion_trata'),
                        "tipo_trata": tipo_trata,
                        "id_expediente": m.get('id_expediente'),
                        "expediente": m.get('expediente'),
                        "fecha_evento": m.get('fecha_evento'),
                        "usuario": None,
                        "documento_gedo": None,
                        "acronimo_gedo": None,
                        "buzon": None,
                        "buzon_ingreso": None,
                        "destino_externo": None,
                        "estado_expediente": m.get('estado_expediente'),
                        "poseedor_actual": m.get('poseedor_actual')
                    })
                print(f"  -> {len(egr_ne_res)} egresos no efectivos procesados.")
            except Exception as e:
                print(f"  Error extrayendo egresos no efectivos de {g_clean}:", e)

    df = pd.DataFrame(rows)
    print(f"\nTotal de registros consolidados: {len(df)}")
    
    # Exportar a CSV con codificación UTF-8 con BOM para que Excel en Windows lo abra correctamente
    df.to_csv(output_filepath, index=False, encoding='utf-8-sig', sep=';')
    print(f"Archivo generado exitosamente en: {os.path.abspath(output_filepath)}")
    
    # Resumen rápido
    print("\n--- RESUMEN POR TIPO DE MOVIMIENTO ---")
    print(df['clasificacion_movimiento'].value_counts())
    
    print("\n--- RESUMEN POR GERENCIA ---")
    print(df['gerencia'].value_counts())

if __name__ == '__main__':
    generate_csv_all_movements()
