import os
import csv
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

local_sade = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
eng = create_engine(local_sade)

tratas_map = [
    {"tramite": "Registro Etapa Proyecto", "trata": "MDUG3001A", "gerencia": "etapa_proyecto"},
    {"tramite": "Registro De Plano Conforme A Obra Civil", "trata": "MDUG0141A", "gerencia": "regularizacion"},
    {"tramite": "Regularizacion De Obra En Contravencion Ley 6478", "trata": "MDUG0104A", "gerencia": "regularizacion"},
    {"tramite": "Permiso De Ejecucion De Obra Civil", "trata": "MDUG1501J", "gerencia": "contable"},
    {"tramite": "Permiso De Demolicion", "trata": "MDUG1501K", "gerencia": "regularizacion"},
    {"tramite": "Tramite Aviso De Obra - APH", "trata": "MDUG0102B", "gerencia": "aviso_obra"},
    {"tramite": "Consulta Obligatoria Para Inmuebles En Aph O Catal", "trata": "MDUG3701A", "gerencia": "aph"},
    {"tramite": "Registro De Proyecto De Elementos Guiados De Transporte (elevadores)", "trata": "MDUG2901A", "gerencia": "instalaciones"},
    {"tramite": "Plano De Propiedad Horizontal Nuevo", "trata": "MDUG0131B", "gerencia": "catastro"},
    {"tramite": "Registro De Proyecto De Prevención Contra Incendios", "trata": "MDUG2101A", "gerencia": "instalaciones"},
    {"tramite": "Plano De Mensura Particular", "trata": "MDUG0115B", "gerencia": "catastro"}
]

with eng.connect() as conn:
    sql = text("""
        SELECT *
        FROM planificacion_tiempos_tramitacion_resumen
        WHERE trata = :t AND gerencia = :g
    """)
    
    rows_out = []
    for item in tratas_map:
        res = conn.execute(sql, {"t": item["trata"], "g": item["gerencia"]}).mappings().fetchone()
        if not res:
            # fallback only by trata
            res = conn.execute(text("SELECT * FROM planificacion_tiempos_tramitacion_resumen WHERE trata = :t ORDER BY total_resueltos_ultimo_mes DESC LIMIT 1"), {"t": item["trata"]}).mappings().fetchone()
        
        if res:
            r = dict(res)
            rows_out.append({
                "Gerencia / Área": item["gerencia"].upper(),
                "Código Trata": item["trata"],
                "Trámite Solicitado": item["tramite"],
                "Descripción Trata en Sistema": r.get("descripcion_trata", ""),
                "Último Mes Cerrado": r.get("ultimo_mes_cerrado", ""),
                "Resueltos Último Mes": int(r.get("total_resueltos_ultimo_mes") or 0),
                "Días Propio Sector (Último Mes)": float(r.get("dias_propio_sector") or 0.0),
                "Días Subsanación (Último Mes)": float(r.get("dias_subsanacion") or 0.0),
                "Días Intervenciones (Último Mes)": float(r.get("dias_intervenciones") or 0.0),
                "Días Totales Promedio (Último Mes)": float(r.get("dias_totales") or 0.0),
                "Resueltos Año en Curso (2026)": int(r.get("total_resueltos_este_ano") or 0),
                "Días Propio Sector (Año 2026)": float(r.get("dias_propio_sector_este_ano") or 0.0),
                "Días Subsanación (Año 2026)": float(r.get("dias_subsanacion_este_ano") or 0.0),
                "Días Intervenciones (Año 2026)": float(r.get("dias_intervenciones_este_ano") or 0.0),
                "Días Totales Promedio (Año 2026)": float(r.get("dias_totales_este_ano") or 0.0),
                "Días Mediana (Año 2026)": float(r.get("dias_mediana_ingresados_este_ano") or 0.0)
            })
        else:
            print(f"No data for {item['trata']}")

# Guardar como CSV en root del proyecto
csv_filename = "reporte_sla_tratas_seleccionadas.csv"
fieldnames = list(rows_out[0].keys())

with open(csv_filename, mode="w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()
    writer.writerows(rows_out)

print(f"CSV generado exitosamente: {csv_filename} ({len(rows_out)} filas)")
