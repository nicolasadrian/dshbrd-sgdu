import io
import logging
import pandas as pd
import traceback
from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import text

# Import database and authentication utilities
from database import engine
from schemas import User
from auth_utils import get_current_user, get_current_user_from_param_or_header

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Human Resources (RRHH)"])

# Helper function
def format_capital(val):
    if not val:
        return ""
    val = str(val).strip()
    if not val:
        return ""
    return val[0].upper() + val[1:].lower()

# --- Endpoints de RRHH ---

@router.get("/api/rrhh/reporte")
async def get_rrhh_reporte(month: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$"), current_user: User = Depends(get_current_user)):
    if not (current_user.permissions.get("reportes_rrhh") or current_user.role.lower() in ['admin', 'administrador']):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        with engine.connect() as conn:
            # Verificar que la tabla existe antes de consultarla
            table_exists = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'reportes_rrhh'
                )
            """)).scalar()

            if not table_exists:
                return {"month": month or datetime.now().strftime("%Y-%m"), "sectores": {}, "message": "La tabla reportes_rrhh aún no existe. Por favor suba un Excel desde la pestaña 'Carga de Excel'."}

            # If month is not provided, find the max date in the table
            if not month:
                max_date = conn.execute(text("SELECT MAX(fecha) FROM public.reportes_rrhh")).scalar()
                if max_date:
                    month = max_date.strftime("%Y-%m-%d")[:7]
                else:
                    d = datetime.now()
                    month = f"{d.year}-{d.month:02d}"

            year_str, month_str = month.split("-")
            y_val = int(year_str)
            m_val = int(month_str)

            # Query all records for this month with SADE user matching
            sql = text("""
                SELECT r.cuil, r.nombreyapellido, r.fecha, r.feriado, r.convocado,
                       r.hora_ingreso, r.hora_salida, r.cant_horas, r.estado_incidencia, r.estado,
                       du.usuario, du.apellido, du.nombre,
                       COALESCE((SELECT MIN(c.gerencia) FROM cfg_gestion_metas c WHERE du.usuario = ANY(c.analistas_oficiales)), 'OTROS') as gerencia
                FROM public.reportes_rrhh r
                LEFT JOIN public.datos_usuario du ON REPLACE(du.numero_cuit, '-', '') = REPLACE(r.cuil, '-', '')
                WHERE EXTRACT(YEAR FROM r.fecha) = :year AND EXTRACT(MONTH FROM r.fecha) = :month
                ORDER BY r.fecha, r.nombreyapellido
            """)
            result = conn.execute(sql, {"year": y_val, "month": m_val}).fetchall()

            if not result:
                return {"month": month, "sectores": {}, "message": "No hay datos para este mes"}

            # Process records
            sectores = {}
            for r in result:
                sec = r[13].upper() # gerencia
                cuil = r[0]
                nombre_comp = r[1]
                fecha = r[2].strftime("%Y-%m-%d") if r[2] else None
                feriado = (r[3] or "").strip().upper() == "SI"
                convocado = (r[4] or "").strip().upper() == "SI"
                
                h_ingreso = r[5] # time object
                h_salida = r[6] # time object
                c_horas = r[7] # time object
                incidencia = r[8] or ""
                est = r[9] or ""

                if sec not in sectores:
                    sectores[sec] = {
                        "gerencia": sec,
                        "earliest_ingreso": None,
                        "latest_salida": None,
                        "dias_laborados": 0,
                        "dias_presentes_total": 0,
                        "dias_a_tiempo": 0,
                        "agentes": {},
                        "hourly_coverage": {f"{h:02d}:00": 0 for h in range(7, 20)}
                    }

                s_data = sectores[sec]

                # Analista key
                agente_key = cuil
                if agente_key not in s_data["agentes"]:
                    s_data["agentes"][agente_key] = {
                        "cuil": cuil,
                        "nombre": nombre_comp,
                        "usuario": r[10] or "N/A",
                        "presentes": 0,
                        "ausentes": 0,
                        "total_convocado": 0,
                        "asistencia_pct": 0,
                        "total_minutos_horas": 0,
                        "dias_con_horas": 0,
                        "promedio_horas": "--"
                    }
                ag_data = s_data["agentes"][agente_key]

                # Registros con hora_ingreso = 00:00 son agentes no presentes
                from datetime import time as _time
                ingreso_es_valido = h_ingreso is not None and h_ingreso != _time(0, 0)

                # Presence / attendance check
                is_present = ("PRESENTE" in est.upper()) or ingreso_es_valido
                if convocado:
                    ag_data["total_convocado"] += 1
                    if is_present:
                        ag_data["presentes"] += 1
                        s_data["dias_presentes_total"] += 1
                    else:
                        ag_data["ausentes"] += 1

                # Daily check-in / check-out bounds — sólo para registros con ingreso válido (no 00:00)
                if ingreso_es_valido:
                    h_str = h_ingreso.strftime("%H:%M")
                    if not s_data["earliest_ingreso"] or h_str < s_data["earliest_ingreso"]:
                        s_data["earliest_ingreso"] = h_str

                    # Hourly coverage matrix (determinar turnos)
                    start_h = h_ingreso.hour
                    end_h = h_salida.hour if (h_salida and h_salida != _time(0, 0)) else 18
                    for hour in range(start_h, min(end_h + 1, 20)):
                        h_key = f"{hour:02d}:00"
                        if h_key in s_data["hourly_coverage"]:
                            s_data["hourly_coverage"][h_key] += 1

                    # Acumular horas trabajadas (cant_horas) — excluir 00:00
                    c_horas = r[7]  # cant_horas
                    if c_horas and c_horas != _time(0, 0):
                        minutos = c_horas.hour * 60 + c_horas.minute
                        ag_data["total_minutos_horas"] += minutos
                        ag_data["dias_con_horas"] += 1

                if h_salida:
                    s_str = h_salida.strftime("%H:%M")
                    if not s_data["latest_salida"] or s_str > s_data["latest_salida"]:
                        s_data["latest_salida"] = s_str

            # Finalize averages & percents
            for sec, s_data in sectores.items():
                for ag_key, ag_data in s_data["agentes"].items():
                    tot = ag_data["total_convocado"]
                    if tot > 0:
                        ag_data["asistencia_pct"] = round((ag_data["presentes"] / tot) * 100)
                    else:
                        ag_data["asistencia_pct"] = 100
                    dias_h = ag_data["dias_con_horas"]
                    if dias_h > 0:
                        prom_min = ag_data["total_minutos_horas"] // dias_h
                        ag_data["promedio_horas"] = f"{prom_min // 60:02d}:{prom_min % 60:02d}"
                    else:
                        ag_data["promedio_horas"] = "--"
                    del ag_data["total_minutos_horas"]
                    del ag_data["dias_con_horas"]

                # Convert agents dict to list
                s_data["agentes_list"] = list(s_data["agentes"].values())
                del s_data["agentes"]

            return {"sectores": sectores}
    except Exception as e:
        logger.error(f"Error fetching RRHH metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/rrhh/reporte/detalle-agente")
async def get_rrhh_agente_detalle(cuil: str = Query(...), month: str = Query(..., regex=r"^\d{4}-\d{2}$"), current_user: User = Depends(get_current_user)):
    if not (current_user.permissions.get("reportes_rrhh") or current_user.role.lower() in ['admin', 'administrador']):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        year_str, month_str = month.split("-")
        y_val = int(year_str)
        m_val = int(month_str)

        with engine.connect() as conn:
            sql = text("""
                SELECT fecha, feriado, convocado, hora_ingreso, hora_salida, cant_horas, estado_incidencia, estado
                FROM public.reportes_rrhh
                WHERE REPLACE(cuil, '-', '') = REPLACE(:cuil, '-', '')
                  AND EXTRACT(YEAR FROM fecha) = :year
                  AND EXTRACT(MONTH FROM fecha) = :month
                ORDER BY fecha
            """)
            result = conn.execute(sql, {"cuil": cuil, "year": y_val, "month": m_val}).fetchall()
            
            rows = []
            for r in result:
                rows.append({
                    "fecha": r[0].strftime("%Y-%m-%d") if r[0] else "",
                    "feriado": r[1],
                    "convocado": r[2],
                    "hora_ingreso": r[3].strftime("%H:%M:%S") if r[3] else "",
                    "hora_salida": r[4].strftime("%H:%M:%S") if r[4] else "",
                    "cant_horas": r[5].strftime("%H:%M:%S") if r[5] else "",
                    "estado_incidencia": r[6] or "",
                    "estado": r[7] or ""
                })
            return rows
    except Exception as e:
        logger.error(f"Error fetching agent RRHH detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/rrhh/upload")
async def upload_rrhh_excel(
    file: UploadFile = File(...),
    token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_from_param_or_header)
):
    if not (current_user.permissions.get("carga_reportes_rrhh") or current_user.role.lower() in ['admin', 'administrador']):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        # Read Excel using pandas via BytesIO to avoid 'seekable' error on SpooledTemporaryFile
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Log columnas originales
        logger.info(f"Excel subido: {len(df)} filas, columnas originales detectadas: {list(df.columns)}")
        
        # Auto-detectar fila de cabecera si las columnas son Unnamed o si no contienen 'cuil'
        has_cuil = any("cuil" in str(c).lower() for c in df.columns)
        is_unnamed = all(str(c).startswith("Unnamed:") for c in df.columns) or not has_cuil
        
        if is_unnamed:
            header_row_idx = None
            # Buscar en las primeras 20 filas una que contenga "cuil"
            for i in range(min(20, len(df))):
                row_values = [str(val).strip().lower() for val in df.iloc[i].values if pd.notna(val)]
                if any("cuil" in val for val in row_values):
                    header_row_idx = i
                    break
            
            if header_row_idx is not None:
                logger.info(f"Fila de cabecera detectada dinámicamente en el índice {header_row_idx}")
                new_cols = []
                for col_idx in range(len(df.columns)):
                    val = df.iloc[header_row_idx, col_idx]
                    new_cols.append(str(val).strip() if pd.notna(val) else f"col_{col_idx}")
                
                df.columns = new_cols
                df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
                logger.info(f"Columnas reasignadas a: {list(df.columns)}")
        
        # Check minimum columns count
        if len(df.columns) < 10:
            raise HTTPException(status_code=400, detail=f"El archivo Excel debe contener al menos 10 columnas. Se detectaron {len(df.columns)} columnas: {list(df.columns)}")

        # Normalizar nombres de columnas para matchear
        cols_norm = {str(c).strip().lower(): c for c in df.columns}
        
        def find_col(aliases, required=True):
            for a in aliases:
                if a in cols_norm:
                    return cols_norm[a]
            if required:
                raise HTTPException(status_code=400, detail=f"No se encontró la columna requerida. Buscado: {aliases}. Columnas detectadas: {list(df.columns)}")
            return None

        c_cuil = find_col(["cuil"])
        c_nombre = find_col(["nombre y apellido", "nombreyapellido", "nombre"])
        c_fecha = find_col(["fecha"])
        c_feriado = find_col(["feriado"])
        c_convocado = find_col(["convocado"])
        c_ingreso = find_col(["hora ingreso (r)", "hora_ingreso", "hora ingreso", "ingreso"])
        c_salida = find_col(["hora salida (r)", "hora_salida", "hora salida", "salida"])
        c_horas = find_col(["cant horas (r)", "cant_horas", "cant horas", "cantidad horas", "horas"])
        c_incidencia = find_col(["estado incidencia", "estado_incidencia", "incidencia"], required=False)
        c_estado = find_col(["estado"])

        records_to_insert = []
        dates_present = set()

        for idx, row in df.iterrows():
            cuil_val = row[c_cuil]
            if pd.isna(cuil_val):
                continue
            cuil_raw = str(cuil_val).strip()
            if cuil_raw.endswith('.0'):
                cuil_raw = cuil_raw[:-2]
                
            if not cuil_raw or cuil_raw.lower() in ['cuil', 'nan', 'none', '']:
                continue

            nombre = str(row[c_nombre]).strip()
            fecha_raw = row[c_fecha]
            feriado = str(row[c_feriado]).strip()
            convocado = str(row[c_convocado]).strip()
            
            h_ingreso_raw = row[c_ingreso]
            h_salida_raw = row[c_salida]
            c_horas_raw = row[c_horas]
            
            incidencia = str(row[c_incidencia]).strip() if c_incidencia and pd.notna(row[c_incidencia]) else ""
            estado = str(row[c_estado]).strip() if pd.notna(row[c_estado]) else ""

            # Parse date safely
            try:
                type_str = str(type(fecha_raw)).lower()
                is_invalid = False
                if pd.isna(fecha_raw):
                    is_invalid = True
                elif 'time' in type_str or 'delta' in type_str:
                    if 'timestamp' not in type_str and 'datetime' not in type_str:
                        is_invalid = True
                        
                if is_invalid:
                    continue

                if hasattr(fecha_raw, 'to_pydatetime'):
                    fecha = fecha_raw.to_pydatetime()
                elif isinstance(fecha_raw, (datetime, date)):
                    if isinstance(fecha_raw, date) and not isinstance(fecha_raw, datetime):
                        fecha = datetime.combine(fecha_raw, datetime.min.time())
                    else:
                        fecha = fecha_raw
                else:
                    fecha = pd.to_datetime(str(fecha_raw).strip(), dayfirst=True).to_pydatetime()
                
                res_type_str = str(type(fecha)).lower()
                is_res_invalid = False
                if 'time' in res_type_str or 'delta' in res_type_str:
                    if 'timestamp' not in res_type_str and 'datetime' not in res_type_str:
                        is_res_invalid = True
                
                if is_res_invalid or not hasattr(fecha, 'year') or fecha.year < 2000:
                    continue
            except Exception as e:
                logger.warning(f"Fila {idx} salteada: Error parseando fecha '{fecha_raw}': {e}")
                continue

            dates_present.add(fecha.date())

            # Parse times safely helper
            def parse_time(val):
                from datetime import time as datetime_time
                if pd.isna(val) or str(val).strip().lower() in ['nan', 'none', '', ':']:
                    return None
                try:
                    if isinstance(val, datetime):
                        return val.time()
                    if isinstance(val, datetime_time):
                        return val
                    
                    if isinstance(val, (int, float)) and val == 0:
                        return datetime_time(0, 0, 0)
                        
                    t_str = str(val).strip()
                    if t_str in ['0', '00', '0.0', '00:00', '00:00:00']:
                        return datetime_time(0, 0, 0)
                        
                    if t_str == ':':
                        return None

                    parts = t_str.split(":")
                    if len(parts) >= 2:
                        p0 = parts[0].strip()
                        p1 = parts[1].strip()
                        if not p0 or not p1:
                            return None
                        h = int(p0)
                        m = int(p1)
                        s = int(parts[2].strip()) if len(parts) > 2 and parts[2].strip() else 0
                        return datetime_time(h, m, s)
                except Exception as e:
                    logger.debug(f"Error parsing time value '{val}': {e}")
                return None

            h_ingreso = parse_time(h_ingreso_raw)
            h_salida = parse_time(h_salida_raw)
            c_horas = parse_time(c_horas_raw)

            records_to_insert.append({
                "cuil": cuil_raw,
                "nombreyapellido": nombre,
                "fecha": fecha,
                "feriado": feriado,
                "convocado": convocado,
                "hora_ingreso": h_ingreso,
                "hora_salida": h_salida,
                "cant_horas": c_horas,
                "estado_incidencia": incidencia,
                "estado": estado
            })

        if not records_to_insert:
            raise HTTPException(status_code=400, detail="No se encontraron registros válidos para insertar.")

        # Clean and insert in database
        with engine.begin() as conn:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_reportes_rrhh_cuil_fecha ON public.reportes_rrhh (cuil, fecha)"))
            conn.execute(
                text("""
                    INSERT INTO public.reportes_rrhh (
                        cuil, nombreyapellido, fecha, feriado, convocado,
                        hora_ingreso, hora_salida, cant_horas, estado_incidencia, estado
                    ) VALUES (
                        :cuil, :nombreyapellido, :fecha, :feriado, :convocado,
                        :hora_ingreso, :hora_salida, :cant_horas, :estado_incidencia, :estado
                    )
                    ON CONFLICT (cuil, fecha) DO UPDATE SET
                        nombreyapellido = EXCLUDED.nombreyapellido,
                        feriado = EXCLUDED.feriado,
                        convocado = EXCLUDED.convocado,
                        hora_ingreso = EXCLUDED.hora_ingreso,
                        hora_salida = EXCLUDED.hora_salida,
                        cant_horas = EXCLUDED.cant_horas,
                        estado_incidencia = EXCLUDED.estado_incidencia,
                        estado = EXCLUDED.estado
                """),
                records_to_insert
            )

        min_date = min(dates_present) if dates_present else "N/A"
        max_date = max(dates_present) if dates_present else "N/A"
        return {
            "status": "ok", 
            "message": f"Se procesaron e ingresaron correctamente {len(records_to_insert)} registros correspondientes a las fechas {min_date} hasta {max_date}."
        }
    except HTTPException:
        raise
    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(f"Error uploading RRHH excel: {e}\nTraceback:\n{tb_str}")
        raise HTTPException(status_code=500, detail=str(e))
