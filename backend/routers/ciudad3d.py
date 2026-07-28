import os
import time
import logging
import warnings
import tempfile
import io
import csv
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text

try:
    from database import engine, geo_engine
    from config import TRAMITES_CONFIG
    from schemas import User
    from auth_utils import get_current_user, get_current_user_from_param_or_header
except ImportError:
    from backend.database import engine, geo_engine
    from backend.config import TRAMITES_CONFIG
    from backend.schemas import User
    from backend.auth_utils import get_current_user, get_current_user_from_param_or_header

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ciudad 3D & LFI"])


def normalize_expediente(exp_str: str) -> str:
    if not exp_str:
        return exp_str
    from urllib.parse import unquote
    clean_exp = unquote(exp_str).strip()
    parts = clean_exp.split('-')
    if len(parts) == 5:
        parts.insert(3, '   ')
    elif len(parts) >= 6:
        if parts[3].strip() == '':
            parts[3] = '   '
    return '-'.join(parts)


# --- Models ---

class SearchRule(BaseModel):
    field: str
    operator: str
    value: Any

class AdvancedSearchRequest(BaseModel):
    conjunction: str
    rules: List[SearchRule]

class FavoriteRequest(BaseModel):
    expediente: str
    folder_id: Optional[int] = None

class FolderCreateRequest(BaseModel):
    name: str

class MoveFavoriteRequest(BaseModel):
    expediente: str
    folder_id: Optional[int] = None

class FavoriteNoteRequest(BaseModel):
    note_text: str

class FichaEditRequest(BaseModel):
    direccion: Optional[str] = None
    notas_internas: Optional[str] = None
    responsable: Optional[str] = None
    estado: Optional[str] = None
    prioridad: Optional[str] = None
    proxima_reunion: Optional[bool] = False

class FichaInternalNoteEditRequest(BaseModel):
    note_text: str

class LFIAssignRequest(BaseModel):
    seccion: str
    manzana: str

class LFIAssignSeccionRequest(BaseModel):
    seccion: str

class LFINoteRequest(BaseModel):
    seccion: str
    manzana: str
    nota: str

class AssignRequest(BaseModel):
    seccion: str
    manzana: str

class NoteRequest(BaseModel):
    seccion: str
    manzana: str
    nota: str

class ReviewRequest(BaseModel):
    seccion: str
    manzana: str
    decision: str
    comentario: Optional[str] = None
    disposicion: Optional[str] = None

class DisposicionRequest(BaseModel):
    seccion: str
    manzana: str
    disposicion: str

class LFIDisposicionRequest(BaseModel):
    seccion: str
    manzana: str
    disposicion: str


# --- Endpoints de Expediente y Búsqueda ---

@router.get("/api/expediente/detalle")
async def get_expediente_detalle(
    expediente: str,
    current_user: User = Depends(get_current_user)
):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.connect() as conn:
            sql = """
                SELECT id_expediente, expediente, trata, descripcion_trata, estado, fecha_creacion,
                       COALESCE((
                           SELECT 
                               CASE 
                                   WHEN COUNT(*) > 20 THEN 0
                                   ELSE SUM(
                                       CASE 
                                           WHEN fecha_alta IS NULL OR fecha_alta < '2015-01-01'::date THEN 0
                                           WHEN fecha_cierre IS NOT NULL THEN (fecha_cierre::date - fecha_alta::date)
                                           ELSE (CURRENT_DATE - fecha_alta::date)
                                       END
                                   )
                               END
                           FROM (
                               SELECT DISTINCT fecha_alta, fecha_cierre
                               FROM mvw_ee_actividades_secgdu
                               WHERE id_expediente = vw_expedientes_maestro.id_expediente
                                 AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                           ) t
                       ), 0) AS dias_subsanacion,
                       COALESCE((
                           SELECT 
                               CASE 
                                   WHEN COUNT(*) > 20 THEN 0
                                   ELSE COUNT(*)
                               END
                           FROM (
                               SELECT DISTINCT fecha_alta, fecha_cierre
                               FROM mvw_ee_actividades_secgdu
                               WHERE id_expediente = vw_expedientes_maestro.id_expediente
                                 AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                           ) t
                       ), 0) AS cant_subsanaciones,
                       COALESCE((
                           SELECT dias_stock 
                           FROM mvw_stock_actual_detalle 
                           WHERE id_expediente = vw_expedientes_maestro.id_expediente 
                           LIMIT 1
                       ), 0) AS dias_stock
                FROM vw_expedientes_maestro
                WHERE expediente = :exp
            """
            res = conn.execute(text(sql), {"exp": clean_exp}).fetchone()
            
            if not res:
                raise HTTPException(status_code=404, detail="Expediente no encontrado.")
                
            r = res._mapping
            id_exp = r.get("id_expediente")
            trata = r.get("trata")
            expediente_nro = r.get("expediente")
            estado = r.get("estado")
            
            parts = expediente_nro.split('-')
            reparticion = parts[-1] if parts else ""
            
            gerencia = None
            trata_upper = trata.strip().upper() if trata else ""
            trata_overrides = {
                "MDUG3001A": "etapa_proyecto",
                "MDUG0104A": "etapa_proyecto",
                "MDUG1501J": "etapa_proyecto",
                "MDUG0142A": "etapa_proyecto",
                "MDUG4003A": "etapa_proyecto"
            }
            
            if trata_upper in trata_overrides:
                gerencia = trata_overrides[trata_upper]
            else:
                for g, config in TRAMITES_CONFIG.items():
                    if trata_upper in config:
                        gerencia = g
                        break
            
            ubicacion = "EN FLUJO"
            analista = None
            fecha_movimiento = None
            
            if gerencia:
                try:
                    sp = conn.execute(text(f"SELECT analista, fecha_recepcion_analista FROM mv_{gerencia}_stock_propio WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                    if sp:
                        ubicacion = "STOCK PROPIO"
                        analista = sp[0]
                        fecha_movimiento = sp[1]
                except Exception:
                    pass
                    
                if ubicacion == "EN FLUJO":
                    try:
                        sub = conn.execute(text(f"SELECT analista, fecha_recepcion_analista FROM mv_{gerencia}_subsanaciones WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                        if sub:
                            ubicacion = "SUBSANACION"
                            analista = sub[0]
                            fecha_movimiento = sub[1]
                    except Exception:
                        pass
                        
                if ubicacion == "EN FLUJO":
                    try:
                        sp_int = conn.execute(text(f"SELECT analista FROM mv_{gerencia}_intervenciones_stock WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                        if sp_int:
                            ubicacion = "STOCK PROPIO (INTERVENCION)"
                            analista = sp_int[0]
                    except Exception:
                        pass
                        
                if ubicacion == "EN FLUJO":
                    try:
                        sub_int = conn.execute(text(f"SELECT analista FROM mv_{gerencia}_intervenciones_subs WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                        if sub_int:
                            ubicacion = "SUBSANACION (INTERVENCION)"
                            analista = sub_int[0]
                    except Exception:
                        pass
                        
                if ubicacion == "EN FLUJO":
                    try:
                        egr_ef = conn.execute(text(f"SELECT usuario_egreso, fecha_egreso FROM mv_{gerencia}_gedos_egreso WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                        if egr_ef:
                            ubicacion = "EGRESADO"
                            analista = egr_ef[0]
                            fecha_movimiento = egr_ef[1]
                    except Exception:
                        pass
                        
                if ubicacion == "EN FLUJO":
                    try:
                        egr_ne = conn.execute(text(f"SELECT poseedor_actual, fecha_ultimo_movimiento FROM mv_{gerencia}_egresos_no_efectivos WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                        if egr_ne:
                            ubicacion = "EGRESADO (NO EFECTIVO)"
                            analista = egr_ne[0]
                            fecha_movimiento = egr_ne[1]
                    except Exception:
                        pass
            
            if ubicacion == "EN FLUJO":
                try:
                    sql_up = "SELECT destinatario_actual, fecha_ultimo_pase FROM mv_ultimo_pase WHERE id_expediente = :id LIMIT 1"
                    up_row = conn.execute(text(sql_up), {"id": id_exp}).fetchone()
                    if up_row and up_row[0] in [
                        'ARCHIVODGTAL', 'DGIUR-PREARCHIVO', 'DGIUR-SGUI', 'DGROC-ANTECEDENTESRLM', 'DGROC-APTOSGRYCO', 
                        'DGROC-ARCHIVO', 'DGROC-ARI', 'DGROC-CIC', 'DGROC-CONTABLE', 'DGROC-COPIAPLANO', 
                        'DGROC-DCATAT', 'DGROC-DCATDES', 'DGROC-DCATPOL', 'DGROC-DCATRUD', 'DGROC-DCATTIT', 
                        'DGROC-DCG', 'DGROC-DCIDITI', 'DGROC-DCOBAAYFO', 'DGROC-DCOBLEG', 'DGROC-DCOBREG', 
                        'DGROC-DCOBREGD', 'DGROC-DESCARGOS', 'DGROC-DGROCARI', 'DGROC-DGROCDES', 'DGROC-DGROCRRHH', 
                        'DGROC-DTACONT', 'DGROC-DTADES', 'DGROC-DTARPS', 'DGROC-ELEVADORES', 'DGROC-ESPERAINSTALACIONES', 
                        'DGROC-FICHA_PARCELARIA', 'DGROC-GO', 'DGROC-LEGAJOS', 'DGROC-LEGAJOSAUTOMAT', 'DGROC-LEY104', 
                        'DGROC-MESADES', 'DGROC-MESAMIDI', 'DGROC-MESAMIDINST', 'DGROC-MESAMIDINSTINCENDIO', 
                        'DGROC-MESAMIPVO', 'DGROC-OBRASADMIN', 'DGROC-OBRASENCURSO', 'DGROC-OBRASTECNICA', 'DGROC-OBSINCENDIO', 
                        'DGROC-OBSOBRAPREARCHIVO', 'DGROC-OBSPREARCHAYFO', 'DGROC-OBSREGISTRO', 'DGROC-PENDIENTESDEPAGO', 
                        'DGROC-RECHAZADOSLEGAJOS', 'DGROC-REVISIONCONTABLE', 'DGROC-SEDR', 'DGROC-SEDRI', 'DGROC-SGUI', 
                        'DGROC-TERMICAS', 'DGSOCAI-ARCHIVO', 'MGEYA-ARCHIVO', 'MGEYA-DCG', 'PG-ARCHIVO', 
                        'SECGDU-ARCHIVODESPACHO', 'SECLYT-ARCHIVO', 'SSGDU-ARCHIVODESPACHO', 'SSGU-ARCHIVODESPACHO'
                    ]:
                        ubicacion = "EGRESADO"
                        analista = up_row[0]
                        fecha_movimiento = up_row[1]
                except Exception:
                    pass
            if ubicacion == "EN FLUJO" and not gerencia:
                ubicacion = "FUERA DE TABLERO"

            d_tramitacion = 0
            f_creacion = r.get("fecha_creacion")
            if f_creacion:
                if hasattr(f_creacion, "date"):
                    f_creacion_date = f_creacion.date()
                else:
                    f_creacion_date = datetime.strptime(str(f_creacion)[:10], "%Y-%m-%d").date()
                
                if ubicacion.startswith("EGRESADO") and fecha_movimiento:
                    if hasattr(fecha_movimiento, "date"):
                        f_mov_date = fecha_movimiento.date()
                    else:
                        f_mov_date = datetime.strptime(str(fecha_movimiento)[:10], "%Y-%m-%d").date()
                    d_tramitacion = (f_mov_date - f_creacion_date).days
                else:
                    d_tramitacion = (date.today() - f_creacion_date).days
            
            ficha_estado = ""
            ficha_prioridad = ""
            ficha_row = conn.execute(text("SELECT estado, prioridad FROM expediente_fichas WHERE expediente = :exp"), {"exp": expediente_nro}).fetchone()
            if ficha_row:
                ficha_estado = ficha_row[0] or ""
                ficha_prioridad = ficha_row[1] or ""

            motivo_pase = "Sin Motivo"
            try:
                mot_row = conn.execute(text("SELECT motivo FROM mvw_ee_pases_secgdu WHERE id_expediente = :id ORDER BY fecha DESC LIMIT 1"), {"id": id_exp}).fetchone()
                if mot_row and mot_row[0]:
                    motivo_pase = mot_row[0]
            except Exception:
                pass

            return {
                "id_expediente": id_exp,
                "expediente": expediente_nro,
                "trata": trata,
                "descripcion_trata": r.get("descripcion_trata"),
                "gerencia": gerencia.upper() if gerencia else reparticion,
                "estado": estado,
                "ubicacion": ubicacion,
                "analista": analista or "SIN ASIGNAR",
                "fecha_ultimo_pase": fecha_movimiento.strftime("%Y-%m-%d %H:%M:%S") if fecha_movimiento and hasattr(fecha_movimiento, "strftime") else (str(fecha_movimiento)[:19] if fecha_movimiento else None),
                "fecha_creacion": r.get("fecha_creacion").strftime("%Y-%m-%d %H:%M:%S") if r.get("fecha_creacion") and hasattr(r.get("fecha_creacion"), "strftime") else (str(r.get("fecha_creacion"))[:19] if r.get("fecha_creacion") else None),
                "dias_tramitacion": max(0, d_tramitacion),
                "dias_subsanacion": int(r.get("dias_subsanacion") or 0),
                "cant_subsanaciones": int(r.get("cant_subsanaciones") or 0),
                "dias_stock": int(r.get("dias_stock") or 0),
                "ficha_estado": ficha_estado,
                "ficha_prioridad": ficha_prioridad,
                "motivo_pase": motivo_pase,
                "trata_en_tablero": (ubicacion != "FUERA DE TABLERO")
            }
    except Exception as e:
        logger.error(f"Error in get_expediente_detalle: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/expediente/buscar")
async def buscar_expediente(
    anio: str,
    numero: str,
    reparticion: str,
    current_user: User = Depends(get_current_user)
):
    try:
        clean_num = numero.lstrip('0') or '0'
        pattern1 = f"EX-{anio}-{numero}-%-{reparticion}"
        pattern2 = f"EX-{anio}-{clean_num}-%-{reparticion}"
        
        with engine.connect() as conn:
            sql = """
                SELECT id_expediente, expediente, trata, descripcion_trata, estado, fecha_creacion,
                       COALESCE((
                           SELECT 
                               CASE 
                                   WHEN COUNT(*) > 20 THEN 0
                                   ELSE SUM(
                                       CASE 
                                           WHEN fecha_alta IS NULL OR fecha_alta < '2015-01-01'::date THEN 0
                                           WHEN fecha_cierre IS NOT NULL THEN (fecha_cierre::date - fecha_alta::date)
                                           ELSE (CURRENT_DATE - fecha_alta::date)
                                       END
                                   )
                               END
                           FROM (
                               SELECT DISTINCT fecha_alta, fecha_cierre
                               FROM mvw_ee_actividades_secgdu
                               WHERE id_expediente = vw_expedientes_maestro.id_expediente
                                 AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                           ) t
                       ), 0) AS dias_subsanacion,
                       COALESCE((
                           SELECT 
                               CASE 
                                   WHEN COUNT(*) > 20 THEN 0
                                   ELSE COUNT(*)
                               END
                           FROM (
                               SELECT DISTINCT fecha_alta, fecha_cierre
                               FROM mvw_ee_actividades_secgdu
                               WHERE id_expediente = vw_expedientes_maestro.id_expediente
                                 AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                           ) t
                       ), 0) AS cant_subsanaciones,
                       COALESCE((
                           SELECT dias_stock 
                           FROM mvw_stock_actual_detalle 
                           WHERE id_expediente = vw_expedientes_maestro.id_expediente 
                           LIMIT 1
                       ), 0) AS dias_stock
                FROM vw_expedientes_maestro
                WHERE expediente LIKE :pattern1 OR expediente LIKE :pattern2
            """
            res = conn.execute(text(sql), {
                "pattern1": pattern1,
                "pattern2": pattern2
            }).fetchall()
            if not res:
                return []
            
            expedientes = []
            for row in res:
                r = row._mapping
                id_exp = r.get("id_expediente")
                trata = r.get("trata")
                expediente_nro = r.get("expediente")
                estado = r.get("estado")
                
                gerencia = None
                trata_upper = trata.strip().upper() if trata else ""
                trata_overrides = {
                    "MDUG3001A": "etapa_proyecto",
                    "MDUG0104A": "etapa_proyecto",
                    "MDUG1501J": "etapa_proyecto",
                    "MDUG0142A": "etapa_proyecto",
                    "MDUG4003A": "etapa_proyecto"
                }
                
                if trata_upper in trata_overrides:
                    gerencia = trata_overrides[trata_upper]
                else:
                    for g, config in TRAMITES_CONFIG.items():
                        if trata_upper in config:
                            gerencia = g
                            break
                
                ubicacion = "EN FLUJO"
                analista = None
                fecha_movimiento = None
                
                if gerencia:
                    try:
                        sp = conn.execute(text(f"""
                            SELECT analista, fecha_recepcion_analista 
                            FROM mv_{gerencia}_stock_propio 
                            WHERE id_expediente = :id LIMIT 1
                        """), {"id": id_exp}).fetchone()
                        if sp:
                            ubicacion = "STOCK PROPIO"
                            analista = sp[0]
                            fecha_movimiento = sp[1]
                    except Exception:
                        pass
                        
                    if ubicacion == "EN FLUJO":
                        try:
                            sub = conn.execute(text(f"""
                                SELECT analista, fecha_recepcion_analista 
                                FROM mv_{gerencia}_subsanaciones 
                                WHERE id_expediente = :id LIMIT 1
                            """), {"id": id_exp}).fetchone()
                            if sub:
                                ubicacion = "SUBSANACION"
                                analista = sub[0]
                                fecha_movimiento = sub[1]
                        except Exception:
                            pass
                            
                    if ubicacion == "EN FLUJO":
                        try:
                            sp_int = conn.execute(text(f"""
                                SELECT analista 
                                FROM mv_{gerencia}_intervenciones_stock 
                                WHERE id_expediente = :id LIMIT 1
                            """), {"id": id_exp}).fetchone()
                            if sp_int:
                                ubicacion = "STOCK PROPIO (INTERVENCION)"
                                analista = sp_int[0]
                        except Exception:
                            pass
                            
                    if ubicacion == "EN FLUJO":
                        try:
                            sub_int = conn.execute(text(f"""
                                SELECT analista 
                                FROM mv_{gerencia}_intervenciones_subs 
                                WHERE id_expediente = :id LIMIT 1
                            """), {"id": id_exp}).fetchone()
                            if sub_int:
                                ubicacion = "SUBSANACION (INTERVENCION)"
                                analista = sub_int[0]
                        except Exception:
                            pass
                            
                    if ubicacion == "EN FLUJO":
                        try:
                            egr_ef = conn.execute(text(f"""
                                SELECT usuario_egreso, fecha_egreso 
                                FROM mv_{gerencia}_gedos_egreso 
                                WHERE id_expediente = :id LIMIT 1
                            """), {"id": id_exp}).fetchone()
                            if egr_ef:
                                ubicacion = "EGRESADO"
                                analista = egr_ef[0]
                                fecha_movimiento = egr_ef[1]
                        except Exception:
                            pass
                            
                    if ubicacion == "EN FLUJO":
                        try:
                            egr_ne = conn.execute(text(f"""
                                SELECT poseedor_actual, fecha_ultimo_movimiento 
                                FROM mv_{gerencia}_egresos_no_efectivos 
                                WHERE id_expediente = :id LIMIT 1
                            """), {"id": id_exp}).fetchone()
                            if egr_ne:
                                ubicacion = "EGRESADO (NO EFECTIVO)"
                                analista = egr_ne[0]
                                fecha_movimiento = egr_ne[1]
                        except Exception:
                            pass
                
                d_tramitacion = 0
                f_creacion = r.get("fecha_creacion")
                if f_creacion:
                    if hasattr(f_creacion, "date"):
                        f_creacion_date = f_creacion.date()
                    else:
                        f_creacion_date = datetime.strptime(str(f_creacion)[:10], "%Y-%m-%d").date()
                    
                    if ubicacion.startswith("EGRESADO") and fecha_movimiento:
                        if hasattr(fecha_movimiento, "date"):
                            f_mov_date = fecha_movimiento.date()
                        else:
                            f_mov_date = datetime.strptime(str(fecha_movimiento)[:10], "%Y-%m-%d").date()
                        d_tramitacion = (f_mov_date - f_creacion_date).days
                    else:
                        d_tramitacion = (date.today() - f_creacion_date).days

                expedientes.append({
                    "id_expediente": id_exp,
                    "expediente": expediente_nro,
                    "trata": trata,
                    "descripcion_trata": r.get("descripcion_trata"),
                    "gerencia": gerencia.upper() if gerencia else reparticion,
                    "estado": estado,
                    "ubicacion": ubicacion,
                    "analista": analista or "SIN ASIGNAR",
                    "fecha_ultimo_pase": fecha_movimiento.strftime("%Y-%m-%d %H:%M:%S") if fecha_movimiento and hasattr(fecha_movimiento, "strftime") else (str(fecha_movimiento)[:19] if fecha_movimiento else None),
                    "fecha_creacion": r.get("fecha_creacion").strftime("%Y-%m-%d %H:%M:%S") if r.get("fecha_creacion") and hasattr(r.get("fecha_creacion"), "strftime") else (str(r.get("fecha_creacion"))[:19] if r.get("fecha_creacion") else None),
                    "dias_tramitacion": max(0, d_tramitacion),
                    "dias_subsanacion": int(r.get("dias_subsanacion") or 0),
                    "cant_subsanaciones": int(r.get("cant_subsanaciones") or 0),
                    "dias_stock": int(r.get("dias_stock") or 0)
                })
            return expedientes
    except Exception as e:
        logger.error(f"Error en buscar_expediente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/expediente/buscar_avanzado")
async def buscar_expediente_avanzado(
    data: AdvancedSearchRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        conjunction = data.conjunction.upper()
        if conjunction not in ["AND", "OR"]:
            raise HTTPException(status_code=400, detail="Conjunción inválida. Debe ser AND u OR.")
            
        field_mapping = {
            "analista": "analista_actual",
            "dias_stock": "dias_stock",
            "gerencia": "gerencia",
            "trata": "trata",
            "is_subs": "is_subs"
        }
        
        op_mapping = {
            "eq": "=",
            "ne": "!=",
            "gt": ">",
            "gte": ">=",
            "lt": "<",
            "lte": "<=",
            "like": "LIKE"
        }

        where_clauses = []
        params = {}
        
        for i, rule in enumerate(data.rules):
            field = rule.field.lower()
            operator = rule.operator.lower()
            val = rule.value
            
            if field not in field_mapping:
                raise HTTPException(status_code=400, detail=f"Campo de búsqueda no permitido: {field}")
            if operator not in op_mapping:
                raise HTTPException(status_code=400, detail=f"Operador no permitido: {operator}")
                
            db_field = field_mapping[field]
            db_op = op_mapping[operator]
            param_name = f"val_{i}"
            
            if operator == "like":
                val = f"%{val}%"
                
            if field == "dias_stock":
                try:
                    val = int(val)
                except ValueError:
                    raise HTTPException(status_code=400, detail="El valor para dias_stock debe ser un número entero.")
            elif field == "is_subs":
                try:
                    val = int(val)
                except ValueError:
                    raise HTTPException(status_code=400, detail="El valor para is_subs debe ser 0 o 1.")
            else:
                val = str(val)
                
            where_clauses.append(f"{db_field} {db_op} :{param_name}")
            params[param_name] = val
            
        if not where_clauses:
            return []
            
        where_sql = f" {conjunction} ".join(where_clauses)
        
        sql = f"""
            SELECT id_expediente, expediente, trata, gerencia, is_subs, analista_actual as analista, dias_stock,
                   fecha_ing, fecha_ultimo_pase,
                    descripcion_trata,
                    estado,
                    fecha_creacion,
                   COALESCE((
                       SELECT 
                           CASE 
                               WHEN COUNT(*) > 20 THEN 0
                               ELSE SUM(
                                   CASE 
                                       WHEN fecha_alta IS NULL OR fecha_alta < '2015-01-01'::date THEN 0
                                       WHEN fecha_cierre IS NOT NULL THEN (fecha_cierre::date - fecha_alta::date)
                                       ELSE (CURRENT_DATE - fecha_alta::date)
                                   END
                               )
                           END
                       FROM (
                           SELECT DISTINCT fecha_alta, fecha_cierre
                           FROM mvw_ee_actividades_secgdu
                           WHERE id_expediente = mvw_stock_actual_detalle.id_expediente
                             AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                       ) t
                   ), 0) AS dias_subsanacion,
                   COALESCE((
                       SELECT 
                           CASE 
                               WHEN COUNT(*) > 20 THEN 0
                               ELSE COUNT(*)
                           END
                       FROM (
                           SELECT DISTINCT fecha_alta, fecha_cierre
                           FROM mvw_ee_actividades_secgdu
                           WHERE id_expediente = mvw_stock_actual_detalle.id_expediente
                             AND nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                       ) t
                   ), 0) AS cant_subsanaciones
            FROM mvw_stock_actual_detalle
            WHERE {where_sql}
        """
        
        with engine.connect() as conn:
            res = conn.execute(text(sql), params).fetchall()
            expedientes = []
            for row in res:
                r = row._mapping
                id_exp = r.get("id_expediente")
                expediente_nro = r.get("expediente")
                trata = r.get("trata")
                gerencia = r.get("gerencia")
                is_subs = r.get("is_subs")
                analista = r.get("analista")
                dias_stock = r.get("dias_stock")
                fecha_ing = r.get("fecha_ing")
                fecha_ultimo_pase = r.get("fecha_ultimo_pase")
                descripcion_trata = r.get("descripcion_trata")
                estado = r.get("estado")
                fecha_creacion = r.get("fecha_creacion")
                
                if is_subs == 1:
                    ubicacion = "SUBSANACION"
                else:
                    ubicacion = "STOCK PROPIO"
                    
                if gerencia:
                    trata_codes = list(TRAMITES_CONFIG.get(gerencia, {}).keys())
                    is_official = trata in [t for t in trata_codes if t != 'INTERVENCIONES']
                    if not is_official:
                        ubicacion += " (INTERVENCION)"
                
                d_tramitacion = 0
                f_creacion = r.get("fecha_creacion")
                if f_creacion:
                    if hasattr(f_creacion, "date"):
                        f_creacion_date = f_creacion.date()
                    else:
                        f_creacion_date = datetime.strptime(str(f_creacion)[:10], "%Y-%m-%d").date()
                    d_tramitacion = (date.today() - f_creacion_date).days

                expedientes.append({
                    "id_expediente": id_exp,
                    "expediente": expediente_nro,
                    "trata": trata,
                    "descripcion_trata": descripcion_trata,
                    "gerencia": gerencia.upper() if gerencia else "-",
                    "estado": estado,
                    "ubicacion": ubicacion,
                    "analista": analista or "SIN ASIGNAR",
                    "fecha_ultimo_pase": fecha_ultimo_pase.strftime("%Y-%m-%d %H:%M:%S") if fecha_ultimo_pase and hasattr(fecha_ultimo_pase, "strftime") else (str(fecha_ultimo_pase)[:19] if fecha_ultimo_pase else None),
                    "fecha_creacion": fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if fecha_creacion and hasattr(fecha_creacion, "strftime") else (str(fecha_creacion)[:19] if fecha_creacion else None),
                    "dias_tramitacion": max(0, d_tramitacion),
                    "dias_subsanacion": int(r.get("dias_subsanacion") or 0),
                    "cant_subsanaciones": int(r.get("cant_subsanaciones") or 0),
                    "dias_stock": int(r.get("dias_stock") or 0)
                })
            return expedientes
    except Exception as e:
        logger.error(f"Error en buscar_expediente_avanzado: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Endpoints de Favoritos ---

@router.post("/api/expediente/favorito")
async def add_favorito(data: FavoriteRequest, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(data.expediente)
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO user_favorites (username, expediente, folder_id)
                VALUES (:u, :exp, :f_id)
                ON CONFLICT (username, expediente) DO UPDATE SET folder_id = EXCLUDED.folder_id
            """), {"u": current_user.username, "exp": clean_exp, "f_id": data.folder_id})
        return {"status": "ok", "message": "Expediente agregado a favoritos"}
    except Exception as e:
        logger.error(f"Error agregando favorito: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/expediente/favorito/{expediente}")
async def remove_favorito(expediente: str, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.begin() as conn:
            conn.execute(text("""
                DELETE FROM user_favorites 
                WHERE username = :u AND expediente = :exp
            """), {"u": current_user.username, "exp": clean_exp})
        return {"status": "ok", "message": "Expediente removido de favoritos"}
    except Exception as e:
        logger.error(f"Error eliminando favorito: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/expediente/favoritos")
async def get_favoritos(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            sql = """
                SELECT 
                    f.expediente,
                    f.folder_id,
                    et.id_expediente,
                    et.trata,
                    et.descripcion_trata,
                    et.estado,
                    et.fecha_creacion,
                    sad.analista_actual as analista,
                    sad.dias_stock,
                    sad.gerencia,
                    sad.is_subs,
                    sad.fecha_ultimo_pase,
                    0 AS dias_subsanacion,
                    0 AS cant_subsanaciones,
                    (SELECT COUNT(*) FROM user_favorite_notes WHERE username = f.username AND expediente = f.expediente) AS cant_notes,
                    (SELECT note_text FROM user_favorite_notes WHERE username = f.username AND expediente = f.expediente ORDER BY created_at DESC LIMIT 1) AS ultima_nota_favorito,
                    ef.direccion AS ficha_direccion,
                    ef.responsable AS ficha_responsable,
                    u_resp.full_name AS ficha_responsable_name,
                    ef.estado AS ficha_estado,
                    ef.prioridad AS ficha_prioridad,
                    ef.proxima_reunion AS ficha_proxima_reunion,
                    (SELECT note_text FROM expediente_ficha_internal_notes WHERE expediente = f.expediente ORDER BY created_at DESC LIMIT 1) AS ficha_notes_internas,
                    (SELECT u.full_name FROM expediente_ficha_internal_notes n LEFT JOIN auth_users u ON n.username = u.username WHERE n.expediente = f.expediente ORDER BY n.created_at DESC LIMIT 1) AS ficha_notes_internas_author,
                    (SELECT n.created_at FROM expediente_ficha_internal_notes n WHERE n.expediente = f.expediente ORDER BY n.created_at DESC LIMIT 1) AS ficha_notes_internas_date
                FROM user_favorites f
                LEFT JOIN vw_expedientes_maestro et ON et.expediente = f.expediente
                LEFT JOIN mvw_stock_actual_detalle sad ON sad.id_expediente = et.id_expediente
                LEFT JOIN expediente_fichas ef ON ef.expediente = f.expediente
                LEFT JOIN auth_users u_resp ON u_resp.username = ef.responsable
                WHERE f.username = :username
                ORDER BY f.created_at DESC
            """
            
            res = conn.execute(text(sql), {"username": current_user.username}).fetchall()
            expedientes = []
            for row in res:
                r = row._mapping
                id_exp = r.get("id_expediente")
                expediente_nro = r.get("expediente")
                trata = r.get("trata")
                estado = r.get("estado")
                is_subs = r.get("is_subs")
                analista = r.get("analista")
                fecha_ultimo_pase = r.get("fecha_ultimo_pase")
                fecha_creacion = r.get("fecha_creacion")
                gerencia = r.get("gerencia")
                
                ubicacion = "EN FLUJO"
                if is_subs == 1:
                    ubicacion = "SUBSANACION"
                elif analista:
                    ubicacion = "STOCK PROPIO"
                
                if id_exp and gerencia:
                    try:
                        sp = conn.execute(text(f"SELECT analista FROM mv_{gerencia.lower()}_stock_propio WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                        if sp:
                            ubicacion = "STOCK PROPIO"
                            analista = sp[0]
                    except Exception:
                        pass
                        
                    if ubicacion == "EN FLUJO":
                        try:
                            sub = conn.execute(text(f"SELECT analista FROM mv_{gerencia.lower()}_subsanaciones WHERE id_expediente = :id LIMIT 1"), {"id": id_exp}).fetchone()
                            if sub:
                                ubicacion = "SUBSANACION"
                                analista = sub[0]
                        except Exception:
                            pass
                
                d_tramitacion = 0
                if fecha_creacion:
                    if hasattr(fecha_creacion, "date"):
                        f_creacion_date = fecha_creacion.date()
                    else:
                        f_creacion_date = datetime.strptime(str(fecha_creacion)[:10], "%Y-%m-%d").date()
                    d_tramitacion = (date.today() - f_creacion_date).days
                
                expedientes.append({
                    "id_expediente": id_exp,
                    "expediente": expediente_nro,
                    "folder_id": r.get("folder_id"),
                    "trata": trata,
                    "descripcion_trata": r.get("descripcion_trata") or "S/D",
                    "gerencia": gerencia.upper() if gerencia else "-",
                    "estado": estado or "DESCONOCIDO",
                    "ubicacion": ubicacion,
                    "analista": analista or "SIN ASIGNAR",
                    "fecha_ultimo_pase": fecha_ultimo_pase.strftime("%Y-%m-%d %H:%M:%S") if fecha_ultimo_pase and hasattr(fecha_ultimo_pase, "strftime") else (str(fecha_ultimo_pase)[:19] if fecha_ultimo_pase else None),
                    "fecha_creacion": fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if fecha_creacion and hasattr(fecha_creacion, "strftime") else (str(fecha_creacion))[:19] if fecha_creacion else None,
                    "dias_tramitacion": max(0, d_tramitacion),
                    "dias_subsanacion": int(r.get("dias_subsanacion") or 0),
                    "cant_subsanaciones": int(r.get("cant_subsanaciones") or 0),
                    "dias_stock": int(r.get("dias_stock") or 0),
                    "cant_notas": int(r.get("cant_notas") or 0),
                    "ficha_direccion": r.get("ficha_direccion") or "",
                    "ficha_responsable": r.get("ficha_responsable") or "",
                    "ficha_responsable_name": r.get("ficha_responsable_name") or r.get("ficha_responsable") or "",
                    "ficha_estado": r.get("ficha_estado") or "",
                    "ficha_prioridad": r.get("ficha_prioridad") or "",
                    "ficha_proxima_reunion": bool(r.get("ficha_proxima_reunion")),
                    "ficha_notas_internas": r.get("ficha_notas_internas") or "",
                    "ficha_notas_internas_author": r.get("ficha_notas_internas_author") or "",
                    "ficha_notas_internas_date": r.get("ficha_notas_internas_date").strftime("%Y-%m-%d %H:%M:%S") if r.get("ficha_notas_internas_date") and hasattr(r.get("ficha_notas_internas_date"), "strftime") else (str(r.get("ficha_notas_internas_date"))[:19] if r.get("ficha_notas_internas_date") else ""),
                    "ultima_nota_favorito": r.get("ultima_nota_favorito") or ""
                })
            return expedientes
    except Exception as e:
        logger.error(f"Error listando favoritos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/expediente/favoritos/carpetas")
async def get_favoritos_carpetas(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            sql = """
                SELECT 
                    uf.id, 
                    uf.name,
                    (SELECT COUNT(*) FROM user_favorites WHERE folder_id = uf.id AND username = :u) as count
                FROM user_favorite_folders uf
                WHERE uf.username = :u
                ORDER BY uf.name ASC
            """
            res = conn.execute(text(sql), {"u": current_user.username}).fetchall()
            return [dict(r._mapping) for r in res]
    except Exception as e:
        logger.error(f"Error listando carpetas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/expediente/favoritos/carpetas")
async def create_favorito_carpeta(data: FolderCreateRequest, current_user: User = Depends(get_current_user)):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO user_favorite_folders (username, name)
                VALUES (:u, :name)
                ON CONFLICT (username, name) DO NOTHING
            """), {"u": current_user.username, "name": data.name})
        return {"status": "ok", "message": "Carpeta creada exitosamente"}
    except Exception as e:
        logger.error(f"Error creando carpeta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/expediente/favoritos/carpetas/{folder_id}")
async def delete_favorito_carpeta(folder_id: int, current_user: User = Depends(get_current_user)):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                DELETE FROM user_favorite_folders
                WHERE id = :fid AND username = :u
            """), {"fid": folder_id, "u": current_user.username})
        return {"status": "ok", "message": "Carpeta de favoritos eliminada"}
    except Exception as e:
        logger.error(f"Error eliminando carpeta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/expediente/favorito/mover")
async def move_favorito(data: MoveFavoriteRequest, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(data.expediente)
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE user_favorites
                SET folder_id = :fid
                WHERE username = :u AND expediente = :exp
            """), {"fid": data.folder_id, "u": current_user.username, "exp": clean_exp})
        return {"status": "ok", "message": "Favorito movido exitosamente"}
    except Exception as e:
        logger.error(f"Error moviendo favorito: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/expediente/favorito/{expediente}/notas")
async def get_favorito_notes(expediente: str, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.connect() as conn:
            sql = """
                SELECT 
                    n.id, 
                    n.note_text, 
                    n.created_at,
                    n.username,
                    u.full_name as author_name,
                    u.sector as author_sector
                FROM user_favorite_notes n
                LEFT JOIN auth_users u ON n.username = u.username
                WHERE n.expediente = :exp
                ORDER BY n.created_at DESC
            """
            res = conn.execute(text(sql), {"exp": clean_exp}).fetchall()
            return [{
                "id": r[0],
                "note_text": r[1],
                "created_at": r[2].strftime("%Y-%m-%d %H:%M:%S") if r[2] and hasattr(r[2], "strftime") else str(r[2])[:19],
                "username": r[3],
                "author_name": r[4] or r[3],
                "author_sector": r[5] or "-",
                "is_owner": r[3] == current_user.username
            } for r in res]
    except Exception as e:
        logger.error(f"Error listando notas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/expediente/favorito/{expediente}/notas")
async def create_favorito_nota(expediente: str, data: FavoriteNoteRequest, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.begin() as conn:
            fav = conn.execute(text("""
                SELECT 1 FROM user_favorites WHERE username = :u AND expediente = :exp
            """), {"u": current_user.username, "exp": clean_exp}).fetchone()
            if not fav:
                raise HTTPException(status_code=400, detail="El expediente debe estar agregado a favoritos para poder añadirle notas.")
            
            conn.execute(text("""
                INSERT INTO user_favorite_notes (username, expediente, note_text)
                VALUES (:u, :exp, :note)
            """), {"u": current_user.username, "exp": clean_exp, "note": data.note_text})
        return {"status": "ok", "message": "Nota guardada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando nota: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/expediente/favorito/notas/{note_id}")
async def delete_favorito_nota(note_id: int, current_user: User = Depends(get_current_user)):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                DELETE FROM user_favorite_notes
                WHERE id = :nid AND username = :u
            """), {"nid": note_id, "u": current_user.username})
        return {"status": "ok", "message": "Nota eliminada exitosamente"}
    except Exception as e:
        logger.error(f"Error eliminando nota: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Endpoints de Ficha de Expediente ---

@router.get("/api/usuarios-tablero")
async def list_usuarios_tablero(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT username, full_name FROM auth_users ORDER BY full_name"))
            return [{"username": r.username, "full_name": r.full_name or r.username} for r in result]
    except Exception as e:
        logger.error(f"Error listando usuarios tablero: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/expediente/ficha/{expediente}")
async def get_expediente_ficha(expediente: str, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT direccion, notas_internas, responsable, estado, prioridad, proxima_reunion
                FROM expediente_fichas
                WHERE expediente = :exp
            """), {"exp": clean_exp}).fetchone()
            
            if row:
                return {
                    "direccion": row[0] or "",
                    "notes_internas": row[1] or "",
                    "responsable": row[2] or "",
                    "estado": row[3] or "",
                    "prioridad": row[4] or "",
                    "proxima_reunion": bool(row[5])
                }
            else:
                return {
                    "direccion": "",
                    "notas_internas": "",
                    "responsable": "",
                    "estado": "",
                    "prioridad": "",
                    "proxima_reunion": False
                }
    except Exception as e:
        logger.error(f"Error obteniendo ficha: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/expediente/ficha/{expediente}/notas_internas")
async def get_ficha_notas_internas(expediente: str, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.connect() as conn:
            sql = """
                SELECT 
                    n.id, 
                    n.note_text, 
                    n.created_at,
                    n.username,
                    u.full_name as author_name
                FROM expediente_ficha_internal_notes n
                LEFT JOIN auth_users u ON n.username = u.username
                WHERE n.expediente = :exp
                ORDER BY n.created_at DESC
            """
            res = conn.execute(text(sql), {"exp": clean_exp}).fetchall()
            return [{
                "id": r[0],
                "note_text": r[1],
                "created_at": r[2].strftime("%Y-%m-%d %H:%M:%S") if r[2] and hasattr(r[2], "strftime") else str(r[2])[:19],
                "username": r[3],
                "author_name": r[4] or r[3],
                "is_owner": r[3] == current_user.username or current_user.role.lower() in ['admin', 'administrador']
            } for r in res]
    except Exception as e:
        logger.error(f"Error listando notas internas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/expediente/ficha/nota/{note_id}")
async def edit_ficha_internal_note(note_id: int, data: FichaInternalNoteEditRequest, current_user: User = Depends(get_current_user)):
    try:
        with engine.begin() as conn:
            note = conn.execute(text("SELECT username FROM expediente_ficha_internal_notes WHERE id = :nid"), {"nid": note_id}).fetchone()
            if not note:
                raise HTTPException(status_code=404, detail="Nota no encontrada")
            if note[0] != current_user.username and current_user.role.lower() not in ['admin', 'administrador']:
                raise HTTPException(status_code=403, detail="No tienes permisos para editar esta nota")
                
            conn.execute(text("""
                UPDATE expediente_ficha_internal_notes
                SET note_text = :note
                WHERE id = :nid
            """), {"nid": note_id, "note": data.note_text})
        return {"status": "ok", "message": "Nota actualizada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editando nota de ficha: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/expediente/ficha/nota/{note_id}")
async def delete_ficha_internal_note(note_id: int, current_user: User = Depends(get_current_user)):
    try:
        with engine.begin() as conn:
            note = conn.execute(text("SELECT username FROM expediente_ficha_internal_notes WHERE id = :nid"), {"nid": note_id}).fetchone()
            if not note:
                raise HTTPException(status_code=404, detail="Nota no encontrada")
            if note[0] != current_user.username and current_user.role.lower() not in ['admin', 'administrador']:
                raise HTTPException(status_code=403, detail="No tienes permisos para eliminar esta nota")
                
            conn.execute(text("""
                DELETE FROM expediente_ficha_internal_notes
                WHERE id = :nid
            """), {"nid": note_id})
        return {"status": "ok", "message": "Nota eliminada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando nota de ficha: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/expediente/ficha/{expediente}")
async def save_expediente_ficha(expediente: str, data: FichaEditRequest, current_user: User = Depends(get_current_user)):
    try:
        clean_exp = normalize_expediente(expediente)
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO expediente_fichas (expediente, direccion, responsable, estado, prioridad, proxima_reunion, updated_at)
                VALUES (:exp, :dir, :resp, :est, :prio, :prox, CURRENT_TIMESTAMP)
                ON CONFLICT (expediente) DO UPDATE SET
                    direccion = EXCLUDED.direccion,
                    responsable = EXCLUDED.responsable,
                    estado = EXCLUDED.estado,
                    prioridad = EXCLUDED.prioridad,
                    proxima_reunion = EXCLUDED.proxima_reunion,
                    updated_at = CURRENT_TIMESTAMP
            """), {
                "exp": clean_exp,
                "dir": data.direccion,
                "resp": data.responsable,
                "est": data.estado,
                "prio": data.prioridad,
                "prox": data.proxima_reunion
            })
            
            if data.notas_internas and data.notas_internas.strip():
                conn.execute(text("""
                    INSERT INTO expediente_ficha_internal_notes (expediente, username, note_text)
                    VALUES (:exp, :username, :notes)
                """), {
                    "exp": clean_exp,
                    "username": current_user.username,
                    "notes": data.notas_internas.strip()
                })
        return {"status": "ok", "message": "Ficha de expediente guardada"}
    except Exception as e:
        logger.error(f"Error guardando ficha: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Endpoints de Reportes y Subsanaciones Especiales ---

@router.get("/api/reporte/pendientes_asociacion")
async def get_pendientes_asociacion(current_user: User = Depends(get_current_user)):
    results = {}
    import oracledb
    
    oracle_user = os.getenv("ORACLE_USER", "CDASILVACOSTA")
    oracle_pass = os.getenv("ORACLE_PASS", "SUI_sie329(m")
    oracle_dsn = os.getenv("ORACLE_DSN", "ind01-scan1.gcba.gob.ar:1521/sadetst.gcba.gob.ar")
    
    oracle_data = []
    try:
        connection = oracledb.connect(user=oracle_user, password=oracle_pass, dsn=oracle_dsn)
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id_expediente, documento, acronimo, usuario_creador, fecha_creacion
            FROM EE_SADE.MVW_DATOS_GEDO_SECGDU
            WHERE fecha_creacion IS NOT NULL 
              AND fecha_asociacion IS NULL
        """)
        oracle_data = cursor.fetchall()
        connection.close()
    except Exception as e:
        logger.error(f"Error consultando Oracle para pendientes_asociacion: {e}")
        raise HTTPException(status_code=500, detail=f"Error al conectar con la base transaccional Oracle: {str(e)}")

    if not oracle_data:
        return results

    id_list = [row[0] for row in oracle_data]

    try:
        with engine.connect() as conn:
            for gerencia, tratas in TRAMITES_CONFIG.items():
                cfg_rows = conn.execute(text("""
                    SELECT trata_reporte, acronimos_egreso, firmantes_egreso 
                    FROM cfg_gestion_metas 
                    WHERE gerencia = :g AND trata_reporte <> 'INTERVENCIONES'
                """), {"g": gerencia}).fetchall()
                
                trata_rules = {row[0]: {"acronimos": row[1] or [], "firmantes": row[2] or []} for row in cfg_rows}
                
                gerencia_data = {}
                
                sql = f"""
                    SELECT id_expediente, expediente, trata
                    FROM mv_{gerencia}_universo
                    WHERE es_trata_propia = TRUE
                      AND id_expediente = ANY(:ids)
                """
                try:
                    pg_rows = conn.execute(text(sql), {"ids": id_list}).fetchall()
                    pg_exp_map = {row[0]: {"expediente": row[1], "trata": row[2]} for row in pg_rows}
                    
                    for id_exp, doc, acro, creator, created in oracle_data:
                        if id_exp in pg_exp_map:
                            trata_code = pg_exp_map[id_exp]["trata"]
                            exp_num = pg_exp_map[id_exp]["expediente"]
                            
                            rules = trata_rules.get(trata_code)
                            if not rules or not rules["acronimos"]:
                                continue
                            
                            if acro not in rules["acronimos"]:
                                continue
                                
                            if rules["firmantes"] and creator not in rules["firmantes"]:
                                continue
                                
                            if trata_code not in gerencia_data:
                                trata_name = TRAMITES_CONFIG.get(gerencia, {}).get(trata_code, {}).get("nombre") or trata_code
                                gerencia_data[trata_code] = {
                                    "trata_nombre": trata_name,
                                    "expedientes": []
                                }
                                
                            gerencia_data[trata_code]["expedientes"].append({
                                    "expediente": exp_num,
                                    "gedo": doc,
                                    "usuario_creador": creator,
                                    "fecha_creacion": created.strftime("%Y-%m-%d %H:%M:%S") if created and hasattr(created, "strftime") else (str(created)[:19] if created else None)
                            })
                except Exception as query_err:
                    logger.error(f"Error filtrando en Postgres para gerencia {gerencia}: {query_err}")
                
                if gerencia_data:
                    results[gerencia] = {
                        "area_nombre": gerencia.upper(),
                        "tratas": gerencia_data
                    }
        return results
    except Exception as e:
        logger.error(f"Error procesando pendientes en Postgres: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/subsanaciones")
async def get_subsanaciones_report(
    gerencia: Optional[str] = 'ALL',
    current_user: User = Depends(get_current_user)
):
    from cache_utils import cached_response, set_cache

    g_param = gerencia.lower() if gerencia else 'all'
    if g_param == 'conforme':
        g_param = 'regularizacion'

    _ck = f"subsanaciones_{g_param}"
    hit, data = cached_response(_ck, ttl_seconds=120)
    if hit:
        return data

    gerencias_to_query = []
    if g_param != 'all':
        if g_param not in TRAMITES_CONFIG:
            raise HTTPException(status_code=404, detail=f"Gerencia {gerencia} no encontrada.")
        gerencias_to_query = [g_param]
    else:
        gerencias_to_query = list(TRAMITES_CONFIG.keys())

    records = []
    try:
        with engine.connect() as conn:
            for g in gerencias_to_query:
                sql_trata = f"""
                    WITH exp_total_subs AS (
                        SELECT 
                            u.trata,
                            u.id_expediente,
                            COUNT(*) as cant_subs,
                            SUM(
                                CASE 
                                    WHEN a.fecha_alta IS NULL OR a.fecha_alta < '2015-01-01'::date THEN 0
                                    WHEN a.fecha_cierre IS NOT NULL THEN (a.fecha_cierre::date - a.fecha_alta::date)
                                    ELSE (CURRENT_DATE - a.fecha_alta::date)
                                END
                            ) as dias_subs
                        FROM mv_{g}_universo u
                        INNER JOIN mvw_ee_actividades_secgdu a ON u.id_expediente = a.id_expediente
                        WHERE u.es_trata_propia = TRUE
                          AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                        GROUP BY u.trata, u.id_expediente
                    )
                    SELECT 
                        trata,
                        COUNT(*) as total_expedientes,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cant_subs)::numeric as mediana_cant,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dias_subs)::numeric as mediana_dias
                    FROM exp_total_subs
                    GROUP BY trata
                """
                sql_analyst = f"""
                    WITH exp_subs AS (
                        SELECT 
                            u.trata,
                            a.usuario_alta as analista,
                            a.id_expediente,
                            COUNT(*) as cant_subs,
                            SUM(
                                CASE 
                                    WHEN a.fecha_alta IS NULL OR a.fecha_alta < '2015-01-01'::date THEN 0
                                    WHEN a.fecha_cierre IS NOT NULL THEN (a.fecha_cierre::date - a.fecha_alta::date)
                                    ELSE (CURRENT_DATE - a.fecha_alta::date)
                                END
                            ) as dias_subs
                        FROM mv_{g}_universo u
                        INNER JOIN mvw_ee_actividades_secgdu a ON u.id_expediente = a.id_expediente
                        WHERE u.es_trata_propia = TRUE
                          AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                        GROUP BY u.trata, a.usuario_alta, a.id_expediente
                    )
                    SELECT 
                        t.trata,
                        t.analista,
                        COALESCE(du.apellido_nombre, t.analista) as analista_nombre,
                        COALESCE(du.codigo_sector_interno, '-') as analista_sector,
                        COUNT(*) as total_expedientes,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.cant_subs)::numeric as mediana_cant,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.dias_subs)::numeric as mediana_dias
                    FROM exp_subs t
                    LEFT JOIN datos_usuario du ON t.analista = du.usuario
                    GROUP BY t.trata, t.analista, du.apellido_nombre, du.codigo_sector_interno
                """
                
                try:
                    trata_rows = conn.execute(text(sql_trata)).fetchall()
                    analyst_rows = conn.execute(text(sql_analyst)).fetchall()
                except Exception as query_err:
                    logger.warning(f"Error querying subsanaciones for gerencia {g}: {query_err}")
                    continue
                
                trata_analysts = {}
                for ar in analyst_rows:
                    ar_dict = ar._mapping
                    t_code = ar_dict["trata"]
                    if t_code not in trata_analysts:
                        trata_analysts[t_code] = []
                    trata_analysts[t_code].append({
                        "analista": ar_dict["analista"],
                        "nombre": ar_dict["analista_nombre"],
                        "sector": ar_dict["analista_sector"],
                        "total_expedientes": int(ar_dict["total_expedientes"] or 0),
                        "mediana_cant": float(ar_dict["mediana_cant"] or 0.0),
                        "mediana_dias": float(ar_dict["mediana_dias"] or 0.0)
                    })
                    
                g_cfg = TRAMITES_CONFIG.get(g, {})
                for tr in trata_rows:
                    tr_dict = tr._mapping
                    t_code = tr_dict["trata"]
                    t_cfg = g_cfg.get(t_code, {})
                    
                    records.append({
                        "gerencia": g,
                        "trata": t_code,
                        "descripcion_trata": t_cfg.get("nombre") or "S/D",
                        "total_expedientes": int(tr_dict["total_expedientes"] or 0),
                        "mediana_cant": float(tr_dict["mediana_cant"] or 0.0),
                        "mediana_dias": float(tr_dict["mediana_dias"] or 0.0),
                        "analistas": trata_analysts.get(t_code, [])
                    })
        set_cache(_ck, records)
        return records
    except Exception as e:
        logger.error(f"Error en reporte/subsanaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/subsanaciones/expedientes")
async def get_subsanaciones_expedientes(
    gerencia: str,
    trata: str,
    analista: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
        
    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail=f"Gerencia {gerencia} no encontrada.")
        
    try:
        with engine.connect() as conn:
            sql = f"""
                SELECT 
                    u.expediente AS "EXPEDIENTE",
                    u.trata AS "TRAMITE",
                    u.descripcion_trata AS "DETALLE TRATA",
                    to_char(u.fecha_creacion_ee, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA CREACION",
                    a.usuario_alta as "ANALISTA",
                    COALESCE(du.apellido_nombre, a.usuario_alta) as "ANALISTA_NOMBRE",
                    COUNT(DISTINCT a.fecha_alta) as "CANT SUBSANACIONES",
                    SUM(
                        CASE 
                            WHEN a.fecha_alta IS NULL OR a.fecha_alta < '2015-01-01'::date THEN 0
                            WHEN a.fecha_cierre IS NOT NULL THEN (a.fecha_cierre::date - a.fecha_alta::date)
                            ELSE (CURRENT_DATE - a.fecha_alta::date)
                        END
                    ) as "DIAS SUBSANACION"
                FROM mv_{gerencia_clean}_universo u
                INNER JOIN mvw_ee_actividades_secgdu a ON u.id_expediente = a.id_expediente
                LEFT JOIN datos_usuario du ON a.usuario_alta = du.usuario
                WHERE u.es_trata_propia = TRUE
                  AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                  AND u.trata = :trata
                  AND (:analista IS NULL OR a.usuario_alta = :analista)
                GROUP BY u.expediente, u.trata, u.descripcion_trata, u.fecha_creacion_ee, a.usuario_alta, du.apellido_nombre
                ORDER BY u.expediente
            """
            result = conn.execute(text(sql), {"trata": trata, "analista": analista})
            rows = [dict(row._mapping) for row in result.fetchall()]
            
            mapped_rows = []
            for r in rows:
                mapped_rows.append({
                    "expediente": r["EXPEDIENTE"],
                    "trata": r["TRAMITE"],
                    "descripcion_trata": r["DETALLE TRATA"] or "S/D",
                    "fecha_creacion": r["FECHA CREACION"],
                    "analista": r["ANALISTA_NOMBRE"],
                    "usuario_sade": r["ANALISTA"],
                    "cant_subsanaciones": int(r["CANT SUBSANACIONES"] or 0),
                    "dias_subsanacion": int(r["DIAS SUBSANACION"] or 0)
                })
            return mapped_rows
    except Exception as e:
        logger.error(f"Error en reporte/subsanaciones/expedientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Endpoints de Analytics ---

@router.get("/api/analytics/permisos-obra")
async def get_analytics_permisos_obra(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            result_monthly = conn.execute(text("""
                SELECT 
                    EXTRACT(YEAR FROM e.fecha_egreso)::int as anio,
                    EXTRACT(MONTH FROM e.fecha_egreso)::int as mes,
                    e.trata,
                    cfg.descripcion_trata,
                    e.usuario_egreso as usuario,
                    COUNT(*) as cant
                FROM public.mv_contable_egresos_efectivos e
                LEFT JOIN public.cfg_gestion_metas cfg 
                  ON cfg.trata_reporte = e.trata 
                 AND cfg.gerencia = 'contable'
                WHERE e.acronimo_egreso = 'IFPDO'
                  AND e.trata IN ('MDUG3001A', 'MDUG1501J', 'MDUG3402A')
                  AND e.fecha_egreso >= '2022-01-01'
                GROUP BY anio, mes, e.trata, cfg.descripcion_trata, e.usuario_egreso
                ORDER BY anio, mes, e.trata;
            """))
            monthly_data = [dict(r._mapping) for r in result_monthly]
            
            result_yearly = conn.execute(text("""
                SELECT 
                    EXTRACT(YEAR FROM fecha_egreso)::int as anio,
                    COUNT(*) as cant
                FROM public.mv_contable_egresos_efectivos
                WHERE acronimo_egreso = 'IFPDO'
                  AND trata IN ('MDUG3001A', 'MDUG1501J', 'MDUG3402A')
                  AND fecha_egreso >= '2022-01-01'
                GROUP BY anio
                ORDER BY anio;
            """))
            yearly_data = [dict(r._mapping) for r in result_yearly]
            
            return {
                "monthly_data": monthly_data,
                "yearly_data": yearly_data
            }
    except Exception as e:
        logger.error(f"Error fetching permisos obra analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/analytics/m2-permisados")
async def get_analytics_m2_permisados(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    comuna: Optional[str] = Query(None),
    barrio: Optional[str] = Query(None),
    tipo_obra: Optional[str] = Query(None),
    tipo_tarea: Optional[str] = Query(None),
    anio: Optional[int] = Query(None),
    categoria: Optional[str] = Query(None), # "construir", "ampliar", "modificar"
    current_user: User = Depends(get_current_user)
):
    try:
        page_val = int(page.default) if hasattr(page, 'default') else int(page)
        limit_val = int(limit.default) if hasattr(limit, 'default') else int(limit)
        search_str = str(search).strip() if search and isinstance(search, str) else None
        comuna_str = str(comuna).strip() if comuna and isinstance(comuna, str) else None
        barrio_str = str(barrio).strip() if barrio and isinstance(barrio, str) else None
        tipo_obra_str = str(tipo_obra).strip() if tipo_obra and isinstance(tipo_obra, str) else None
        tipo_tarea_str = str(tipo_tarea).strip() if tipo_tarea and isinstance(tipo_tarea, str) else None
        categoria_str = str(categoria).strip() if categoria and isinstance(categoria, str) else None
        anio_val = anio if isinstance(anio, int) else (int(anio.default) if hasattr(anio, 'default') and isinstance(anio.default, int) else None)

        where_clauses = ["1=1"]
        params = {}
        
        if search_str:
            search_clean = f"%{search_str}%"
            where_clauses.append("(expediente ILIKE :search OR direccion ILIKE :search OR smp ILIKE :search OR matricula_profesional ILIKE :search OR apellido_profesional ILIKE :search)")
            params["search"] = search_clean
            
        if comuna_str:
            where_clauses.append("comuna = :comuna")
            params["comuna"] = comuna_str
            
        if barrio_str:
            where_clauses.append("barrio = :barrio")
            params["barrio"] = barrio_str
            
        if tipo_obra_str:
            where_clauses.append("tipo_obra = :tipo_obra")
            params["tipo_obra"] = tipo_obra_str
            
        if tipo_tarea_str:
            where_clauses.append("tipo_tarea = :tipo_tarea")
            params["tipo_tarea"] = tipo_tarea_str
            
        if isinstance(anio, int) and anio > 0:
            where_clauses.append("EXTRACT(YEAR FROM fecha_creacion_pdo)::int = :anio")
            params["anio"] = anio

        if categoria_str:
            cat_val = categoria_str.lower()
            if cat_val == "construir":
                where_clauses.append("sup_construir > 0")
            elif cat_val == "ampliar":
                where_clauses.append("sup_ampliar > 0")
            elif cat_val == "modificar":
                where_clauses.append("sup_modificar > 0")
            
        where_str = " AND ".join(where_clauses)
        offset = (page_val - 1) * limit_val
        
        with engine.connect() as conn:
            # 1. Total records count
            total_count = conn.execute(text(f"SELECT COUNT(*) FROM public.mvw_m2_permisados WHERE {where_str}"), params).scalar() or 0
            
            # 2. Summary stats
            stats = conn.execute(text(f"""
                SELECT 
                    COALESCE(SUM(sup_construir), 0) as total_construir,
                    COALESCE(SUM(sup_ampliar), 0) as total_ampliar,
                    COALESCE(SUM(sup_modificar), 0) as total_modificar,
                    COALESCE(SUM(sup_demoler), 0) as total_demoler,
                    COALESCE(SUM(sup_terreno), 0) as total_terreno
                FROM public.mvw_m2_permisados
                WHERE {where_str}
            """), params).mappings().fetchone()
            
            # 3. Paginated records
            records_res = conn.execute(text(f"""
                SELECT * FROM public.mvw_m2_permisados
                WHERE {where_str}
                ORDER BY fecha_creacion_pdo DESC, id_expediente DESC
                LIMIT :limit OFFSET :offset
            """), {**params, "limit": limit_val, "offset": offset})
            records = [dict(r._mapping) for r in records_res]
            
            # 4. Barrio chart data (Todos los barrios, ordenados por m2 desc)
            barrio_res = conn.execute(text(f"""
                SELECT 
                    COALESCE(barrio, 'SIN ESPECIFICAR') as barrio,
                    COUNT(DISTINCT id_expediente) as cantidad_expedientes,
                    ROUND(SUM(sup_construir)::numeric, 2) as total_construir,
                    ROUND(SUM(sup_ampliar)::numeric, 2) as total_ampliar,
                    ROUND(SUM(sup_modificar)::numeric, 2) as total_modificar,
                    ROUND((SUM(sup_construir) + SUM(sup_ampliar) + SUM(sup_modificar))::numeric, 2) as total_m2
                FROM public.mvw_m2_permisados
                WHERE {where_str} AND (sup_construir > 0 OR sup_ampliar > 0 OR sup_modificar > 0)
                GROUP BY 1
                ORDER BY total_m2 DESC
            """), params)
            barrio_data = [dict(r._mapping) for r in barrio_res]
            
            # 5. Comuna chart data
            comuna_res = conn.execute(text(f"""
                SELECT 
                    COALESCE(comuna, 'SIN ESPECIFICAR') as comuna,
                    COUNT(DISTINCT id_expediente) as cantidad_expedientes,
                    ROUND(SUM(sup_construir)::numeric, 2) as total_construir,
                    ROUND(SUM(sup_ampliar)::numeric, 2) as total_ampliar,
                    ROUND(SUM(sup_modificar)::numeric, 2) as total_modificar,
                    ROUND((SUM(sup_construir) + SUM(sup_ampliar) + SUM(sup_modificar))::numeric, 2) as total_m2
                FROM public.mvw_m2_permisados
                WHERE {where_str} AND (sup_construir > 0 OR sup_ampliar > 0 OR sup_modificar > 0)
                GROUP BY 1
                ORDER BY total_m2 DESC
            """), params)
            comuna_data = [dict(r._mapping) for r in comuna_res]
            
            # 5b. Evolución mensual de m2 construidos
            if isinstance(anio_val, int) and anio_val > 0:
                monthly_res = conn.execute(text(f"""
                    SELECT 
                        EXTRACT(MONTH FROM fecha_creacion_pdo)::int as mes,
                        ROUND((SUM(sup_construir) + SUM(sup_ampliar) + SUM(sup_modificar))::numeric, 2) as total_m2
                    FROM public.mvw_m2_permisados
                    WHERE {where_str} AND (sup_construir > 0 OR sup_ampliar > 0 OR sup_modificar > 0) AND fecha_creacion_pdo IS NOT NULL
                    GROUP BY 1
                    ORDER BY 1
                """), params)
                monthly_data = [dict(r._mapping) for r in monthly_res]
            else:
                monthly_res = conn.execute(text(f"""
                    SELECT 
                        EXTRACT(YEAR FROM fecha_creacion_pdo)::int as anio,
                        EXTRACT(MONTH FROM fecha_creacion_pdo)::int as mes,
                        ROUND((SUM(sup_construir) + SUM(sup_ampliar) + SUM(sup_modificar))::numeric, 2) as total_m2
                    FROM public.mvw_m2_permisados
                    WHERE {where_str} AND (sup_construir > 0 OR sup_ampliar > 0 OR sup_modificar > 0) AND fecha_creacion_pdo IS NOT NULL
                    GROUP BY 1, 2
                    ORDER BY 1, 2
                """), params)
                monthly_data = [dict(r._mapping) for r in monthly_res]
            
            # 5c. Map points (Todos los puntos que cumplan los filtros para mostrarlos en el mapa)
            map_points_res = conn.execute(text(f"""
                SELECT x, y, expediente, direccion, smp, sup_construir, sup_ampliar, sup_modificar, tipo_obra, tipo_tarea, apellido_profesional, nombre_profesional
                FROM public.mvw_m2_permisados
                WHERE {where_str} AND x IS NOT NULL AND y IS NOT NULL
            """), params)
            map_points = [dict(r._mapping) for r in map_points_res]

            # 5d. Lightweight list of all filtered records to count unique expedientes dynamically
            all_summary_res = conn.execute(text(f"""
                SELECT id_expediente, sup_construir, sup_ampliar, sup_modificar
                FROM public.mvw_m2_permisados
                WHERE {where_str}
            """), params)
            summary_records = [{"id": r[0], "c": float(r[1] or 0), "a": float(r[2] or 0), "m": float(r[3] or 0)} for r in all_summary_res.fetchall()]
            
            # 6. Filters
            filter_comunas = [r[0] for r in conn.execute(text("SELECT DISTINCT comuna FROM public.mvw_m2_permisados WHERE comuna IS NOT NULL AND comuna <> '' ORDER BY 1")).fetchall()]
            filter_barrios = [r[0] for r in conn.execute(text("SELECT DISTINCT barrio FROM public.mvw_m2_permisados WHERE barrio IS NOT NULL AND barrio <> '' ORDER BY 1")).fetchall()]
            filter_obras = [r[0] for r in conn.execute(text("SELECT DISTINCT tipo_obra FROM public.mvw_m2_permisados WHERE tipo_obra IS NOT NULL AND tipo_obra <> '' ORDER BY 1")).fetchall()]
            filter_tareas = [r[0] for r in conn.execute(text("SELECT DISTINCT tipo_tarea FROM public.mvw_m2_permisados WHERE tipo_tarea IS NOT NULL AND tipo_tarea <> '' ORDER BY 1")).fetchall()]
            filter_anios = [int(r[0]) for r in conn.execute(text("SELECT DISTINCT EXTRACT(YEAR FROM fecha_creacion_pdo)::int as anio FROM public.mvw_m2_permisados WHERE fecha_creacion_pdo IS NOT NULL ORDER BY 1 DESC")).fetchall()]
            
            return {
                "total_records": total_count,
                "page": page,
                "limit": limit,
                "summary": {
                    "total_construir": stats["total_construir"],
                    "total_ampliar": stats["total_ampliar"],
                    "total_modificar": stats["total_modificar"],
                    "total_demoler": stats["total_demoler"],
                    "total_terreno": stats["total_terreno"]
                },
                "summary_records": summary_records,
                "records": records,
                "map_points": map_points,
                "charts": {
                    "barrio": barrio_data,
                    "comuna": comuna_data,
                    "evolucion_mensual": monthly_data
                },
                "filters": {
                    "comunas": filter_comunas,
                    "barrios": filter_barrios,
                    "tipos_obra": filter_obras,
                    "tipos_tarea": filter_tareas,
                    "anios": filter_anios
                }
            }
    except Exception as e:
        logger.error(f"Error in m2-permisados analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/analytics/m2-permisados/download")
async def download_analytics_m2_permisados(
    search: Optional[str] = Query(None),
    comuna: Optional[str] = Query(None),
    barrio: Optional[str] = Query(None),
    tipo_obra: Optional[str] = Query(None),
    tipo_tarea: Optional[str] = Query(None),
    anio: Optional[int] = Query(None),
    categoria: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    try:
        where_clauses = ["1=1"]
        params = {}
        
        if search:
            search_clean = f"%{search.strip()}%"
            where_clauses.append("(expediente ILIKE :search OR direccion ILIKE :search OR smp ILIKE :search OR matricula_profesional ILIKE :search OR apellido_profesional ILIKE :search)")
            params["search"] = search_clean
            
        if comuna:
            where_clauses.append("comuna = :comuna")
            params["comuna"] = comuna.strip()
            
        if barrio:
            where_clauses.append("barrio = :barrio")
            params["barrio"] = barrio.strip()
            
        if tipo_obra:
            where_clauses.append("tipo_obra = :tipo_obra")
            params["tipo_obra"] = tipo_obra.strip()

        if tipo_tarea:
            where_clauses.append("tipo_tarea = :tipo_tarea")
            params["tipo_tarea"] = tipo_tarea.strip()

        if anio is not None and anio > 0:
            where_clauses.append("EXTRACT(YEAR FROM fecha_creacion_pdo)::int = :anio")
            params["anio"] = anio

        if categoria:
            cat_val = categoria.strip().lower()
            if cat_val == "construir":
                where_clauses.append("sup_construir > 0")
            elif cat_val == "ampliar":
                where_clauses.append("sup_ampliar > 0")
            elif cat_val == "modificar":
                where_clauses.append("sup_modificar > 0")

        where_str = " AND ".join(where_clauses)



        
        from fastapi.responses import StreamingResponse
        import csv
        import io
        
        def generate_csv():
            output = io.StringIO()
            # Agregar UTF-8 BOM para Excel
            output.write('\ufeff')
            writer = csv.writer(output, delimiter=';')
            # Escribir cabeceras
            writer.writerow([
                "Expediente", "Direccion", "Seccion", "Manzana", "Parcela", "Comuna", "Barrio", "Es UF", "SMP",
                "Uso Particularizado", "Tipo Tarea", "Tipo Obra", "Superficie Terreno", "Superficie Libre",
                "Superficie Existente", "Superficie Demoler", "Superficie Construir", "Superficie Modificar",
                "Superficie Ampliar", "Superficie Plusvalia", "Superficie Anti Reglamentaria", "Profundidad Subsuelos",
                "Cantidad Subsuelos", "Cantidad Pisos", "Altura Metros", "Uso CUR", "Apellido Profesional",
                "Nombre Profesional", "Matricula Profesional", "Plano", "Encomienda Profesional",
                "Comprobante Pagos Derechos", "Informe Dominio", "Fecha Creacion OCD", "Fecha Creacion PDO"
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            
            with engine.connect() as conn:
                res = conn.execute(text(f"""
                    SELECT * FROM public.mvw_m2_permisados
                    WHERE {where_str}
                    ORDER BY fecha_creacion_pdo DESC, id_expediente DESC
                """), params)
                
                for row in res:
                    r = row._mapping
                    writer.writerow([
                        r["expediente"], r["direccion"], r["seccion"], r["manzana"], r["parcela"], r["comuna"], r["barrio"],
                        "SI" if r["es_uf"] else "NO", r["smp"], r["uso_particularizado"], r["tipo_tarea"], r["tipo_obra"],
                        r["sup_terreno"], r["sup_libre"], r["sup_existente"], r["sup_demoler"], r["sup_construir"],
                        r["sup_modificar"], r["sup_ampliar"], r["sup_plusvalia"], r["sup_anti_reglamentaria"],
                        r["profundidad_subsuelos"], r["cantidad_subsuelos"], r["cantidad_pisos"], r["altura_metros"],
                        r["uso_cur"], r["apellido_profesional"], r["nombre_profesional"], r["matricula_profesional"],
                        r["plano"], r["encomienda_profesional"], r["comprobante_pagos_derechos"], r["informe_dominio"],
                        r["fecha_creacion_ocd"], r["fecha_creacion_pdo"]
                    ])
                    yield output.getvalue()
                    output.seek(0)
                    output.truncate(0)
                    
        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=m2_permisados.csv"}
        )
    except Exception as e:
        logger.error(f"Error in download m2-permisados: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/analytics/avisos-obra")
async def get_analytics_avisos_obra(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    comuna: Optional[str] = Query(None),
    barrio: Optional[str] = Query(None),
    acronimo: Optional[str] = Query(None),
    anio: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user)
):
    try:
        page_val = int(page.default) if hasattr(page, 'default') else int(page)
        limit_val = int(limit.default) if hasattr(limit, 'default') else int(limit)
        search_str = str(search).strip() if search and isinstance(search, str) else None
        comuna_str = str(comuna).strip() if comuna and isinstance(comuna, str) else None
        barrio_str = str(barrio).strip() if barrio and isinstance(barrio, str) else None
        acronimo_str = str(acronimo).strip() if acronimo and isinstance(acronimo, str) else None
        anio_val = anio if isinstance(anio, int) else (int(anio.default) if hasattr(anio, 'default') and isinstance(anio.default, int) else None)

        where_clauses = ["1=1"]
        params = {}
        
        if search_str:
            search_clean = f"%{search_str}%"
            where_clauses.append("(expediente ILIKE :search OR documento ILIKE :search OR direccion ILIKE :search OR motivo ILIKE :search)")
            params["search"] = search_clean
            
        if comuna_str:
            where_clauses.append("comuna = :comuna")
            params["comuna"] = comuna_str
            
        if barrio_str:
            where_clauses.append("barrio = :barrio")
            params["barrio"] = barrio_str
            
        if acronimo_str:
            where_clauses.append("acronimo = :acronimo")
            params["acronimo"] = acronimo_str.upper()
            
        if isinstance(anio_val, int) and anio_val > 0:
            where_clauses.append("anio = :anio")
            params["anio"] = anio_val

        where_str = " AND ".join(where_clauses)
        offset = (page_val - 1) * limit_val
        
        with engine.connect() as conn:
            # 1. Total records count
            total_count = conn.execute(text(f"SELECT COUNT(*) FROM public.mvw_avisos_obra WHERE {where_str}"), params).scalar() or 0
            
            # 2. Count by acronym (IFCAO, IFCFP, IFCAC)
            acro_res = conn.execute(text(f"""
                SELECT acronimo, COUNT(*) as cant
                FROM public.mvw_avisos_obra
                WHERE {where_str}
                GROUP BY acronimo
            """), params).fetchall()
            acro_counts = {r[0]: int(r[1]) for r in acro_res}
            
            # 3. Paginated table records
            records_res = conn.execute(text(f"""
                SELECT id_expediente, expediente, documento, acronimo, direccion, barrio, comuna, fecha_asociacion, x, y
                FROM public.mvw_avisos_obra
                WHERE {where_str}
                ORDER BY fecha_asociacion DESC NULLS LAST, id_expediente DESC
                LIMIT :limit OFFSET :offset
            """), {**params, "limit": limit_val, "offset": offset})
            records = [dict(r._mapping) for r in records_res]
            for r in records:
                if r.get("fecha_asociacion"):
                    r["fecha_asociacion"] = str(r["fecha_asociacion"])

            # 4. Chart: Ranking Barrios (Top 15 + summary)
            barrio_res = conn.execute(text(f"""
                SELECT COALESCE(NULLIF(barrio, ''), 'SIN ESPECIFICAR') as b, COUNT(*) as cant
                FROM public.mvw_avisos_obra
                WHERE {where_str}
                GROUP BY 1
                ORDER BY cant DESC
            """), params).fetchall()
            barrio_data = [{"barrio": r[0], "total": int(r[1])} for r in barrio_res]

            # 5. Chart: Comunas
            comuna_res = conn.execute(text(f"""
                SELECT COALESCE(NULLIF(comuna, ''), 'SIN ESPECIFICAR') as c, COUNT(*) as cant
                FROM public.mvw_avisos_obra
                WHERE {where_str}
                GROUP BY 1
                ORDER BY cant DESC
            """), params).fetchall()
            comuna_data = [{"comuna": r[0], "total": int(r[1])} for r in comuna_res]

            # 6. Chart: Evolución mensual
            monthly_res = conn.execute(text(f"""
                SELECT TO_CHAR(fecha_asociacion, 'YYYY-MM') as mes, COUNT(*) as cant
                FROM public.mvw_avisos_obra
                WHERE {where_str} AND fecha_asociacion IS NOT NULL
                GROUP BY mes
                ORDER BY mes ASC
            """), params).fetchall()
            monthly_data = [{"mes": r[0], "total": int(r[1])} for r in monthly_res]

            # 7. Map points (all points with coords)
            map_points_res = conn.execute(text(f"""
                SELECT id_expediente, expediente, documento, acronimo, direccion, barrio, comuna, x, y
                FROM public.mvw_avisos_obra
                WHERE {where_str} AND x IS NOT NULL AND y IS NOT NULL
            """), params)
            map_points = [dict(r._mapping) for r in map_points_res]

            # 8. Available Filters dropdown values
            filter_comunas = [r[0] for r in conn.execute(text("SELECT DISTINCT comuna FROM public.mvw_avisos_obra WHERE comuna IS NOT NULL AND comuna <> '' ORDER BY 1")).fetchall()]
            filter_barrios = [r[0] for r in conn.execute(text("SELECT DISTINCT barrio FROM public.mvw_avisos_obra WHERE barrio IS NOT NULL AND barrio <> '' ORDER BY 1")).fetchall()]
            filter_anios = [int(r[0]) for r in conn.execute(text("SELECT DISTINCT anio FROM public.mvw_avisos_obra WHERE anio IS NOT NULL ORDER BY 1 DESC")).fetchall()]

            return {
                "total_records": total_count,
                "page": page,
                "limit": limit,
                "acronyms": {
                    "IFCAO": acro_counts.get("IFCAO", 0),
                    "IFCFP": acro_counts.get("IFCFP", 0),
                    "IFCAC": acro_counts.get("IFCAC", 0)
                },
                "records": records,
                "map_points": map_points,
                "charts": {
                    "barrio": barrio_data,
                    "comuna": comuna_data,
                    "evolucion_mensual": monthly_data
                },
                "filters": {
                    "comunas": filter_comunas,
                    "barrios": filter_barrios,
                    "anios": filter_anios
                }
            }
    except Exception as e:
        logger.error(f"Error in avisos-obra analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/analytics/avisos-obra/download")
async def download_analytics_avisos_obra(
    search: Optional[str] = Query(None),
    comuna: Optional[str] = Query(None),
    barrio: Optional[str] = Query(None),
    acronimo: Optional[str] = Query(None),
    anio: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user)
):
    try:
        where_clauses = ["1=1"]
        params = {}
        
        if search:
            search_clean = f"%{search.strip()}%"
            where_clauses.append("(expediente ILIKE :search OR documento ILIKE :search OR direccion ILIKE :search OR motivo ILIKE :search)")
            params["search"] = search_clean
            
        if comuna:
            where_clauses.append("comuna = :comuna")
            params["comuna"] = comuna.strip()
            
        if barrio:
            where_clauses.append("barrio = :barrio")
            params["barrio"] = barrio.strip()
            
        if acronimo:
            where_clauses.append("acronimo = :acronimo")
            params["acronimo"] = acronimo.strip().upper()
            
        if anio is not None and anio > 0:
            where_clauses.append("anio = :anio")
            params["anio"] = anio

        where_str = " AND ".join(where_clauses)

        def generate_csv():
            output = io.StringIO()
            output.write('\ufeff')
            writer = csv.writer(output, delimiter=';')
            
            writer.writerow([
                "ID Expediente", "Acrónimo", "Expediente", "Documento", "Usuario Creador", "Motivo",
                "Fecha Creación", "Fecha Asociación", "Dirección", "Barrio", "Comuna",
                "Sección", "Manzana", "Parcela", "Coordenada X", "Coordenada Y"
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            
            with engine.connect() as conn:
                res = conn.execute(text(f"""
                    SELECT id_expediente, acronimo, expediente, documento, usuario_creador, motivo,
                           fecha_creacion, fecha_asociacion, direccion, barrio, comuna,
                           seccion, manzana, parcela, x, y
                    FROM public.mvw_avisos_obra
                    WHERE {where_str}
                    ORDER BY fecha_asociacion DESC NULLS LAST, id_expediente DESC
                """), params)
                
                for row in res:
                    r = row._mapping
                    writer.writerow([
                        r["id_expediente"], r["acronimo"], r["expediente"], r["documento"], r["usuario_creador"], r["motivo"],
                        str(r["fecha_creacion"]) if r["fecha_creacion"] else "",
                        str(r["fecha_asociacion"]) if r["fecha_asociacion"] else "",
                        r["direccion"], r["barrio"], r["comuna"], r["seccion"], r["manzana"], r["parcela"],
                        r["x"], r["y"]
                    ])
                    yield output.getvalue()
                    output.seek(0)
                    output.truncate(0)
                    
        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=avisos_de_obra.csv"}
        )
    except Exception as e:
        logger.error(f"Error in download avisos-obra: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/analytics/ley-blanqueo")
async def get_analytics_ley_blanqueo(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            check_view = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM pg_matviews 
                    WHERE matviewname = 'parcelas_leydeblanqueo'
                );
            """)).fetchone()
            
            if not check_view or not check_view[0]:
                logger.info("La vista public.parcelas_leydeblanqueo no existe. Intentando crearla...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS public.df_form_comp_value (
                        id_transaction BIGINT,
                        input_name VARCHAR(255),
                        value_str TEXT,
                        value_double DOUBLE PRECISION,
                        value_int INTEGER,
                        value_boolean BOOLEAN
                    );
                    CREATE INDEX IF NOT EXISTS idx_df_form_comp_value_id_tx ON public.df_form_comp_value (id_transaction);
                """))
                
                sql_path = os.path.join(os.path.dirname(__file__), "..", "vistas", "regularizacion", "16_parcelas_leydeblanqueo.sql")
                if os.path.exists(sql_path):
                    with open(sql_path, "r", encoding="utf-8") as f:
                        sql_content = f.read()
                    
                    raw_conn = conn.connection
                    with raw_conn.cursor() as cur:
                        cur.execute(sql_content)
                    logger.info("Vista materializada parcelas_leydeblanqueo creada con éxito.")
                else:
                    logger.error(f"No se encontró el archivo SQL en la ruta: {sql_path}")
            
            result_barrio = conn.execute(text("""
                SELECT 
                    COALESCE(NULLIF(barrio, ''), 'S/D') as barrio,
                    COUNT(*) as cant
                FROM public.parcelas_leydeblanqueo
                GROUP BY barrio
                ORDER BY cant DESC;
            """))
            barrio_data = [dict(r._mapping) for r in result_barrio]
            
            result_comuna = conn.execute(text("""
                SELECT 
                    COALESCE(NULLIF(comuna, ''), 'S/D') as comuna,
                    COUNT(*) as cant
                FROM public.parcelas_leydeblanqueo
                GROUP BY comuna
                ORDER BY cant DESC;
            """))
            comuna_data = [dict(r._mapping) for r in result_comuna]
            
            result_sums = conn.execute(text("""
                SELECT 
                    COALESCE(SUM(sup_contra_no_reg_ce), 0) as sup_contra_no_reg_ce,
                    COALESCE(SUM(sup_contra_reg_ce), 0) as sup_contra_reg_ce,
                    COALESCE(SUM(sup_contra_reg_cur), 0) as sup_contra_reg_cur,
                    COALESCE(SUM(sup_contra_no_reg_cur), 0) as sup_contra_no_reg_cur
                FROM public.parcelas_leydeblanqueo;
            """)).fetchone()
            
            sums_data = dict(result_sums._mapping) if result_sums else {
                "sup_contra_no_reg_ce": 0,
                "sup_contra_reg_ce": 0,
                "sup_contra_reg_cur": 0,
                "sup_contra_no_reg_cur": 0
            }
            
            result_barrio_surfaces = conn.execute(text("""
                SELECT 
                    COALESCE(NULLIF(barrio, ''), 'S/D') as barrio,
                    COALESCE(SUM(sup_contra_no_reg_ce), 0) as sup_contra_no_reg_ce,
                    COALESCE(SUM(sup_contra_reg_ce), 0) as sup_contra_reg_ce,
                    COALESCE(SUM(sup_contra_reg_cur), 0) as sup_contra_reg_cur,
                    COALESCE(SUM(sup_contra_no_reg_cur), 0) as sup_contra_no_reg_cur
                FROM public.parcelas_leydeblanqueo
                GROUP BY barrio
                ORDER BY (
                    COALESCE(SUM(sup_contra_no_reg_ce), 0) + 
                    COALESCE(SUM(sup_contra_reg_ce), 0) + 
                    COALESCE(SUM(sup_contra_reg_cur), 0) + 
                    COALESCE(SUM(sup_contra_no_reg_cur), 0)
                ) DESC;
            """))
            barrio_surfaces_data = [dict(r._mapping) for r in result_barrio_surfaces]
            
            result_timeline = conn.execute(text("""
                SELECT 
                    TO_CHAR(d.fecha_asociacion, 'YYYY-MM') as mes,
                    COALESCE(SUM(p.sup_contra_no_reg_ce), 0) as sup_contra_no_reg_ce,
                    COALESCE(SUM(p.sup_contra_reg_ce), 0) as sup_contra_reg_ce,
                    COALESCE(SUM(p.sup_contra_reg_cur), 0) as sup_contra_reg_cur,
                    COALESCE(SUM(p.sup_contra_no_reg_cur), 0) as sup_contra_no_reg_cur
                FROM public.parcelas_leydeblanqueo p
                JOIN public.mvw_datos_gedo_secgdu d ON p.id_transaction = d.trx_gedo
                WHERE d.fecha_asociacion IS NOT NULL
                GROUP BY TO_CHAR(d.fecha_asociacion, 'YYYY-MM')
                ORDER BY mes ASC;
            """))
            timeline_data = [dict(r._mapping) for r in result_timeline]
            
            return {
                "barrio_data": barrio_data,
                "comuna_data": comuna_data,
                "sums_data": sums_data,
                "barrio_surfaces_data": barrio_surfaces_data,
                "timeline_data": timeline_data
            }
    except Exception as e:
        logger.error(f"Error fetching ley blanqueo analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/analytics/ley-blanqueo/excel")
async def get_analytics_ley_blanqueo_excel(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    p.documento_egreso,
                    p.id_transaction,
                    p.uso_cur,
                    p.id_plano,
                    p.tramite_gobierno,
                    p.prof_nombre,
                    p.prof_apellido,
                    p.prof_matricula,
                    p.direccion,
                    p.barrio,
                    p.comuna,
                    p.sup_contra_no_reg_ce,
                    p.sup_contra_reg_ce,
                    p.sup_contra_reg_cur,
                    p.sup_contra_no_reg_cur,
                    TO_CHAR(d.fecha_asociacion, 'YYYY-MM-DD') as fecha_asociacion
                FROM public.parcelas_leydeblanqueo p
                LEFT JOIN public.mvw_datos_gedo_secgdu d ON p.id_transaction = d.trx_gedo
                ORDER BY p.documento_egreso;
            """))
            rows = [dict(r._mapping) for r in result]
            return rows
    except Exception as e:
        logger.error(f"Error fetching ley blanqueo excel data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Endpoints de Productividad Analistas ---

@router.get("/api/productividad/sectores-analistas")
async def get_sectores_analistas(current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("productividad_analistas"):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        with engine.connect() as conn:
            query = text("""
                WITH analysts AS (
                    SELECT DISTINCT gerencia, unnest(analistas_oficiales) as analista
                    FROM cfg_gestion_metas
                )
                SELECT a.gerencia, a.analista, COALESCE(du.apellido_nombre, a.analista) as apellido_nombre
                FROM analysts a
                LEFT JOIN datos_usuario du ON a.analista = du.usuario
                ORDER BY a.gerencia, apellido_nombre
            """)
            result = conn.execute(query)
            rows = result.fetchall()
            
            sectores = {}
            for r in rows:
                sec = r[0]
                user = r[1]
                name = r[2] or user
                if sec not in sectores:
                    sectores[sec] = []
                if not any(x["usuario"] == user for x in sectores[sec]):
                    sectores[sec].append({"usuario": user, "nombre": name})
            
            return sectores
    except Exception as e:
        logger.error(f"Error fetching sectores analistas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/productividad/analista/{username}")
async def get_analista_productividad(username: str, date_from: Optional[str] = None, date_to: Optional[str] = None, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("productividad_analistas"):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        try:
            from backend.productivity_engine import get_analyst_productivity_data
        except ModuleNotFoundError:
            from productivity_engine import get_analyst_productivity_data
        with engine.connect() as conn:
            data = get_analyst_productivity_data(conn, username, date_from, date_to)
            return data
    except Exception as e:
        logger.error(f"Error fetching analista productivity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/productividad/pdf/individual")
async def get_pdf_individual(username: str, date_from: Optional[str] = None, date_to: Optional[str] = None, token: Optional[str] = Query(None), current_user: User = Depends(get_current_user_from_param_or_header)):
    if not current_user.permissions.get("productividad_analistas"):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        try:
            from backend.pdf_generator import generate_individual_pdf
        except ModuleNotFoundError:
            from pdf_generator import generate_individual_pdf
        from fastapi.responses import Response
        with engine.connect() as conn:
            pdf_bytes = generate_individual_pdf(conn, username, date_from, date_to)
            return Response(content=pdf_bytes, media_type="application/pdf", headers={
                "Content-Disposition": f"attachment; filename=productividad_{username}.pdf"
            })
    except Exception as e:
        logger.error(f"Error generating individual PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/productividad/pdf/comparativo")
async def get_pdf_comparativo(sector: str, date_from: Optional[str] = None, date_to: Optional[str] = None, token: Optional[str] = Query(None), current_user: User = Depends(get_current_user_from_param_or_header)):
    if not current_user.permissions.get("productividad_analistas"):
        raise HTTPException(status_code=403, detail="No tienes permisos para esta sección")
    try:
        try:
            from backend.pdf_generator import generate_comparative_pdf
        except ModuleNotFoundError:
            from pdf_generator import generate_comparative_pdf
        from fastapi.responses import Response
        with engine.connect() as conn:
            pdf_bytes = generate_comparative_pdf(conn, sector, date_from, date_to)
            return Response(content=pdf_bytes, media_type="application/pdf", headers={
                "Content-Disposition": f"attachment; filename=comparativo_{sector}.pdf"
            })
    except Exception as e:
        logger.error(f"Error generating comparative PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Endpoints de Ciudad 3D ---

@router.get("/api/ciudad3d/stats")
def get_ciudad3d_stats(current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a Ciudad 3D")
    
    try:
        with geo_engine.connect() as conn:
            total_parcelas = conn.execute(text("SELECT COUNT(*) FROM public.cur_parcelas_ok")).scalar()
            total_manzanas = conn.execute(text("SELECT COUNT(*) FROM public.manzanas")).scalar()
            return {
                "total_parcelas": total_parcelas,
                "total_manzanas": total_manzanas
            }
    except Exception as e:
        logger.error(f"Error fetching Ciudad 3D stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error en la base de datos geo-mdr: {e}")

@router.get("/api/ciudad3d/troneras")
def get_ciudad3d_troneras(current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a Ciudad 3D")
    
    query = """
    WITH troneras_agg AS (
        SELECT TRIM(seccion) AS seccion,
               TRIM(manzana) AS manzana,
               SUM(CASE WHEN TRIM(UPPER(irregular)) = 'SI' THEN 1 ELSE 0 END) AS irregular_si,
               SUM(CASE WHEN TRIM(UPPER(irregular)) = 'NO' THEN 1 ELSE 0 END) AS irregular_no
        FROM public.mdr_troneras
        WHERE seccion IS NOT NULL AND manzana IS NOT NULL
        GROUP BY TRIM(seccion), TRIM(manzana)
    ),
    barrio_manzana AS (
        SELECT DISTINCT ON (TRIM(seccion), TRIM(manzana))
               TRIM(seccion) AS seccion,
               TRIM(manzana) AS manzana,
               TRIM(barrio) AS barrio
        FROM public.cur_parcelas_ok
        WHERE seccion IS NOT NULL AND manzana IS NOT NULL AND barrio IS NOT NULL AND TRIM(barrio) <> ''
    )
    SELECT bm.barrio,
           bm.seccion,
           bm.manzana,
           COALESCE(t.irregular_si, 0) AS irregular_si,
           COALESCE(t.irregular_no, 0) AS irregular_no
    FROM barrio_manzana bm
    JOIN public.manzanas m ON TRIM(m.seccion) = bm.seccion AND TRIM(m.manzana) = bm.manzana
    JOIN troneras_agg t ON t.seccion = bm.seccion AND t.manzana = bm.manzana
    ORDER BY bm.barrio, bm.seccion, bm.manzana
    """
    try:
        workflow_map = {}
        try:
            with engine.connect() as conn:
                wf_res = conn.execute(text("""
                    SELECT w.seccion, w.manzana, w.estado, w.analista_asignado, w.disposicion, w.archivo_trazado, w.archivo_finalizado, u.full_name
                    FROM public.manzanas_lfi_workflow w
                    LEFT JOIN public.auth_users u ON w.analista_asignado = u.username
                """)).fetchall()
                for r in wf_res:
                    key = (r[0].strip(), r[1].strip())
                    workflow_map[key] = {
                        "estado": r[2],
                        "analista_asignado": r[3] if r[3] else "",
                        "disposicion": r[4] if r[4] else "",
                        "archivo_trazado": r[5] if r[5] else "",
                        "archivo_finalizado": r[6] if r[6] else "",
                        "analista_nombre": r[7] if r[7] else (r[3] if r[3] else "")
                    }
        except Exception as wf_e:
            logger.error(f"Error fetching LFI workflow maps: {wf_e}")

        with geo_engine.connect() as conn:
            res = conn.execute(text(query)).fetchall()
            return [
                {
                    "barrio": r[0],
                    "seccion": r[1],
                    "manzana": r[2],
                    "irregular_si": r[3],
                    "irregular_no": r[4],
                    "estado": workflow_map.get((r[1].strip(), r[2].strip()), {}).get("estado", "Pendiente"),
                    "analista_asignado": workflow_map.get((r[1].strip(), r[2].strip()), {}).get("analista_asignado", ""),
                    "disposicion": workflow_map.get((r[1].strip(), r[2].strip()), {}).get("disposicion", ""),
                    "archivo_trazado": workflow_map.get((r[1].strip(), r[2].strip()), {}).get("archivo_trazado", ""),
                    "archivo_finalizado": workflow_map.get((r[1].strip(), r[2].strip()), {}).get("archivo_finalizado", ""),
                    "analista_nombre": workflow_map.get((r[1].strip(), r[2].strip()), {}).get("analista_nombre", "")
                }
                for r in res
            ]
    except Exception as e:
        logger.error(f"Error fetching Ciudad 3D troneras: {e}")
        raise HTTPException(status_code=500, detail=f"Error en la base de datos geo-mdr: {e}")

@router.post("/api/ciudad3d/manzanas_lfi/assign")
def assign_manzana_lfi(req: LFIAssignRequest, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("lfi_dibujar"):
        raise HTTPException(status_code=403, detail="No tiene permisos de dibujo de LFI ('lfi_dibujar') para asignarse manzanas.")
    
    with engine.begin() as conn:
        existing = conn.execute(text("""
            SELECT estado FROM public.manzanas_lfi_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": req.seccion.strip(), "m": req.manzana.strip()}).fetchone()
        
        if existing and existing[0] != 'Pendiente':
            raise HTTPException(status_code=400, detail=f"Esta manzana ya está en estado '{existing[0]}'")
            
        conn.execute(text("""
            INSERT INTO public.manzanas_lfi_workflow (seccion, manzana, estado, analista_asignado, updated_at)
            VALUES (:s, :m, 'En curso', :a, CURRENT_TIMESTAMP)
            ON CONFLICT (seccion, manzana) 
            DO UPDATE SET estado = 'En curso', analista_asignado = :a, updated_at = CURRENT_TIMESTAMP
        """), {"s": req.seccion.strip(), "m": req.manzana.strip(), "a": current_user.username})
        
    return {"status": "ok", "estado": "En curso", "analista_asignado": current_user.username}

@router.post("/api/ciudad3d/manzanas_lfi/assign_seccion")
def assign_seccion_lfi(req: LFIAssignSeccionRequest, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("lfi_dibujar"):
        raise HTTPException(status_code=403, detail="No tiene permisos de dibujo de LFI ('lfi_dibujar') para asignarse manzanas.")
    
    seccion_clean = req.seccion.strip()
    
    # Obtener todas las manzanas de esa sección desde mdr_troneras
    with geo_engine.connect() as geo_conn:
        m_rows = geo_conn.execute(text("""
            SELECT DISTINCT TRIM(manzana) 
            FROM public.mdr_troneras 
            WHERE TRIM(seccion) = :s AND manzana IS NOT NULL AND TRIM(manzana) <> ''
        """), {"s": seccion_clean}).fetchall()
        manzanas = [r[0] for r in m_rows]
        
    if not manzanas:
        raise HTTPException(status_code=404, detail=f"No se encontraron manzanas para la Sección {seccion_clean}.")
        
    assigned_count = 0
    with engine.begin() as conn:
        for m in manzanas:
            existing = conn.execute(text("""
                SELECT estado FROM public.manzanas_lfi_workflow
                WHERE seccion = :s AND manzana = :m
            """), {"s": seccion_clean, "m": m}).fetchone()
            
            # Asignar solo las manzanas que están pendientes o no asignadas previamente
            if not existing or existing[0] == 'Pendiente':
                conn.execute(text("""
                    INSERT INTO public.manzanas_lfi_workflow (seccion, manzana, estado, analista_asignado, updated_at)
                    VALUES (:s, :m, 'En curso', :a, CURRENT_TIMESTAMP)
                    ON CONFLICT (seccion, manzana) 
                    DO UPDATE SET estado = 'En curso', analista_asignado = :a, updated_at = CURRENT_TIMESTAMP
                """), {"s": seccion_clean, "m": m, "a": current_user.username})
                assigned_count += 1
                
    return {
        "status": "ok", 
        "seccion": seccion_clean, 
        "assigned_count": assigned_count, 
        "total_manzanas": len(manzanas),
        "analista_asignado": current_user.username
    }

@router.post("/api/ciudad3d/manzanas_lfi/unassign")
def unassign_manzana_lfi(req: LFIAssignRequest, current_user: User = Depends(get_current_user)):
    if current_user.role.lower() not in ['admin', 'administrador']:
        raise HTTPException(status_code=403, detail="Solo los administradores pueden liberar asignaciones.")
        
    s_clean = req.seccion.strip()
    m_clean = req.manzana.strip()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO public.manzanas_lfi_workflow (seccion, manzana, estado, analista_asignado, updated_at)
            VALUES (:s, :m, 'Pendiente', NULL, CURRENT_TIMESTAMP)
            ON CONFLICT (seccion, manzana) 
            DO UPDATE SET estado = 'Pendiente', analista_asignado = NULL, updated_at = CURRENT_TIMESTAMP
        """), {"s": s_clean, "m": m_clean})
        
    return {"status": "ok", "estado": "Pendiente", "analista_asignado": None}

@router.get("/api/ciudad3d/manzana_by_coords")
def get_manzana_by_coords(lng: float, lat: float, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="Sin permisos para Ciudad 3D")
    
    query = """
        SELECT seccion, manzana FROM public.mdr_troneras
        WHERE ST_Contains(geom, ST_Transform(ST_SetSRID(ST_Point(:lng, :lat), 4326), 22186))
        LIMIT 1
    """
    try:
        with geo_engine.connect() as conn:
            row = conn.execute(text(query), {"lng": lng, "lat": lat}).fetchone()
            if row:
                return {"seccion": row[0].strip(), "manzana": row[1].strip()}
            
            row_p = conn.execute(text("""
                SELECT seccion, manzana FROM public.cur_parcelas_ok
                WHERE ST_Contains(geom, ST_Transform(ST_SetSRID(ST_Point(:lng, :lat), 4326), 22186))
                LIMIT 1
            """), {"lng": lng, "lat": lat}).fetchone()
            if row_p:
                return {"seccion": row_p[0].strip(), "manzana": row_p[1].strip()}
                
            return {"seccion": None, "manzana": None}
    except Exception as e:
        logger.error(f"Error querying manzana by coords: {e}")
        raise HTTPException(status_code=500, detail=str(e))

LFI_MAP_LAYERS = {
    "parcelas":     ("cur_parcelas_ok",           "geom", 22186),
    "lfi":          ("mdr_lineadefrenteinterno",  "geom", 22186),
    "basamento":    ("mdr_lineadebasamento",      "geom", 22186),
    "troneras":     ("mdr_troneras",              "geom", 22186),
    "banda_minima": ("mdr_banda_minima",          "geom", 22186),
}

_lfi_tile_cache: dict = {}
_LFI_TILE_CACHE_MAX = 500

def _lfi_tile_cache_key(layer, z, x, y):
    return f"{layer}/{z}/{x}/{y}"

@router.get("/api/lfi/tiles/{layer}/{z}/{x}/{y}")
def get_lfi_map_tile(layer: str, z: int, x: int, y: int, current_user: User = Depends(get_current_user_from_param_or_header)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="Sin permisos para Ciudad 3D")
    
    if z < 14:
        return Response(content=b"", media_type="application/x-protobuf",
                        headers={"Cache-Control": "public, max-age=86400", "Access-Control-Allow-Origin": "*"})

    if layer not in LFI_MAP_LAYERS:
        raise HTTPException(status_code=404, detail=f"Capa '{layer}' no encontrada.")

    cache_key = _lfi_tile_cache_key(layer, z, x, y)
    if cache_key in _lfi_tile_cache:
        mvt_bytes = _lfi_tile_cache[cache_key]
        return Response(content=bytes(mvt_bytes), media_type="application/x-protobuf",
                        headers={"Cache-Control": "public, max-age=21600", "X-Cache": "HIT",
                                 "Access-Control-Allow-Origin": "*"})
    table, col, srid = LFI_MAP_LAYERS[layer]
    
    if z >= 17:
        simplify_tol = 0.0
    elif z >= 15:
        simplify_tol = 1.0
    elif z >= 13:
        simplify_tol = 3.0
    else:
        simplify_tol = 8.0

    bbox_filter = f"ST_Transform(ST_TileEnvelope({z}, {x}, {y}), {srid})" if srid != 3857 else f"ST_TileEnvelope({z}, {x}, {y})"
    
    if simplify_tol > 0:
        geom_to_3857 = f"ST_Simplify(ST_Transform(ST_SetSRID({col}, {srid}), 3857), {simplify_tol})"
    else:
        geom_to_3857 = f"ST_Transform(ST_SetSRID({col}, {srid}), 3857)"

    extra_cols = ""
    extra_join = ""
    if layer == "troneras":
        extra_cols = ", t.seccion, t.manzana, COALESCE(UPPER(TRIM(t.irregular)), '') AS irregular"
    elif layer in ("lfi", "basamento", "parcelas"):
        extra_cols = ", t.seccion, t.manzana"
    elif layer == "banda_minima":
        extra_cols = ", p.seccion, p.manzana"
        extra_join = f"LEFT JOIN public.cur_parcelas_ok p ON p.smp = {table}.smp"

    table_alias = "t" if layer != "banda_minima" else table
    from_clause = f"public.{table} t {extra_join}" if layer != "banda_minima" else f"public.{table} {extra_join}"
    geom_col_ref = f"t.{col}" if layer != "banda_minima" else f"{table}.{col}"
    geom_to_3857_aliased = geom_to_3857.replace(f"{col}", geom_col_ref)
    bbox_filter_aliased = bbox_filter

    query = text(f"""
        SELECT ST_AsMVT(q, :layer_name, 4096, 'geom') AS mvt
        FROM (
            SELECT ST_AsMVTGeom(
                {geom_to_3857_aliased},
                ST_TileEnvelope({z}, {x}, {y}),
                 4096,
                256,
                true
            ) AS geom{extra_cols}
            FROM {from_clause}
            WHERE {geom_col_ref} IS NOT NULL
              AND ST_SetSRID({geom_col_ref}, {srid}) && {bbox_filter_aliased}
        ) q
        WHERE q.geom IS NOT NULL
    """)
    
    try:
        with geo_engine.connect() as conn:
            result = conn.execute(query, {"layer_name": layer}).fetchone()
            mvt_bytes = result[0] if result else b""
            if mvt_bytes is None:
                mvt_bytes = b""
            if len(_lfi_tile_cache) >= _LFI_TILE_CACHE_MAX:
                oldest = next(iter(_lfi_tile_cache))
                del _lfi_tile_cache[oldest]
            _lfi_tile_cache[cache_key] = bytes(mvt_bytes)

        return Response(
            content=bytes(mvt_bytes),
            media_type="application/x-protobuf",
            headers={
                "Cache-Control": "public, max-age=21600",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        logger.error(f"Error generando tile MVT para capa {layer} ({z}/{x}/{y}): {e}")
        raise HTTPException(status_code=500, detail=f"Error generando tile: {e}")

@router.get("/api/ciudad3d/manzanas_lfi/notes")
def get_manzana_lfi_notes(seccion: str, manzana: str, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a esta sección")
    
    s_clean = seccion.strip()
    m_clean = manzana.strip()
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT n.id, n.username, n.nota, n.created_at, u.full_name
            FROM public.manzanas_lfi_notes n
            LEFT JOIN public.auth_users u ON n.username = u.username
            WHERE TRIM(n.seccion) = :s AND TRIM(n.manzana) = :m
            ORDER BY n.created_at DESC
        """), {"s": s_clean, "m": m_clean}).fetchall()
        
        return [
            {
                "id": r[0],
                "username": r[1],
                "nota": r[2],
                "created_at": str(r[3]),
                "full_name": r[4] if r[4] else r[1]
            }
            for r in res
        ]

@router.post("/api/ciudad3d/manzanas_lfi/notes")
def add_manzana_lfi_note(req: LFINoteRequest, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a esta sección")
    
    s_clean = req.seccion.strip()
    m_clean = req.manzana.strip()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO public.manzanas_lfi_notes (seccion, manzana, username, nota, created_at)
            VALUES (:s, :m, :u, :n, CURRENT_TIMESTAMP)
        """), {"s": s_clean, "m": m_clean, "u": current_user.username, "n": req.nota})
        
    return {"status": "ok"}

@router.post("/api/ciudad3d/manzanas_lfi/upload")
async def upload_trazado_lfi(
    seccion: str = Form(...),
    manzana: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    try:
        if not current_user.permissions.get("lfi_dibujar"):
            raise HTTPException(status_code=403, detail="No tiene permisos de dibujo de LFI ('lfi_dibujar') para subir trazados.")
            
        sec_clean = seccion.strip()
        man_clean = manzana.strip()
        
        sec_unpadded = sec_clean.lstrip('0') or '0'
        sec_padded = sec_clean.zfill(3)
        man_unpadded = man_clean.lstrip('0') or '0'
        man_padded = man_clean.zfill(3)

        file_filename = file.filename or "trazado.dxf"
        file_ext = os.path.splitext(file_filename)[1]
        if not file_ext or file_ext.lower() not in ['.dxf', '.dwg']:
            raise HTTPException(status_code=400, detail="Solo se permiten archivos con extensión .dxf o .dwg")

        with engine.connect() as conn:
            existing = conn.execute(text("""
                SELECT analista_asignado, estado, seccion, manzana 
                FROM public.manzanas_lfi_workflow
                WHERE (TRIM(seccion) IN (:s, :s_unpadded, :s_padded))
                  AND (TRIM(manzana) IN (:m, :m_unpadded, :m_padded))
            """), {
                "s": sec_clean, "s_unpadded": sec_unpadded, "s_padded": sec_padded,
                "m": man_clean, "m_unpadded": man_unpadded, "m_padded": man_padded
            }).fetchone()
            
            if not existing:
                raise HTTPException(status_code=400, detail=f"La manzana {sec_clean}-{man_clean} no ha sido asignada ni iniciada.")
            
            assigned_user = (existing[0] or "").strip().lower()
            current_username = (current_user.username or "").strip().lower()
            
            if assigned_user and assigned_user != current_username and current_user.role.lower() not in ['admin', 'administrador']:
                raise HTTPException(status_code=403, detail=f"Esta manzana está asignada a {existing[0]}, no puede subir el archivo.")
                
            real_sec = existing[2]
            real_man = existing[3]

        upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "trazados_lfi"))
        try:
            os.makedirs(upload_dir, exist_ok=True)
        except Exception as dir_err:
            logger.error(f"Error creando directorio uploads: {dir_err}")

        safe_filename = f"lfi-{real_sec}-{real_man}-{int(time.time())}{file_ext}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Error saving LFI file: {e}")
            raise HTTPException(status_code=500, detail=f"Error al guardar archivo en el servidor: {str(e)}")
            
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE public.manzanas_lfi_workflow
                SET estado = 'Para revisión', archivo_trazado = :f, updated_at = CURRENT_TIMESTAMP
                WHERE seccion = :s AND manzana = :m
            """), {"s": real_sec, "m": real_man, "f": safe_filename})
            
        return {"status": "ok", "estado": "Para revisión", "archivo_trazado": safe_filename}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Error inesperado en upload_trazado_lfi: {exc}")
        raise HTTPException(status_code=500, detail=f"Error inesperado en el servidor: {str(exc)}")

@router.post("/api/ciudad3d/manzanas_lfi/review")
async def review_manzana_lfi(
    seccion: str = Form(...),
    manzana: str = Form(...),
    decision: str = Form(...),
    comentario: Optional[str] = Form(None),
    disposicion: Optional[str] = Form(None),
    file_final: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    if not current_user.permissions.get("lfi_revisar"):
        raise HTTPException(status_code=403, detail="No tiene permisos de revisión de LFI ('lfi_revisar') para revisar manzanas.")
        
    with engine.begin() as conn:
        existing = conn.execute(text("""
            SELECT estado FROM public.manzanas_lfi_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": seccion, "m": manzana}).fetchone()
        
        if not existing or existing[0] != 'Para revisión':
            raise HTTPException(status_code=400, detail="Esta manzana no está en estado 'Para revisión'")
            
        new_state = 'Subir a Ciudad 3D' if decision.upper() == 'OK' else 'En curso'
        
        safe_filename = None
        if decision.upper() == 'OK' and file_final:
            upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "trazados_lfi"))
            os.makedirs(upload_dir, exist_ok=True)
            file_ext = os.path.splitext(file_final.filename)[1]
            safe_filename = f"lfi-final-{seccion}-{manzana}-{int(time.time())}{file_ext}"
            file_path = os.path.join(upload_dir, safe_filename)
            try:
                with open(file_path, "wb") as f:
                    content = await file_final.read()
                    f.write(content)
            except Exception as e:
                logger.error(f"Error saving LFI final file: {e}")
                raise HTTPException(status_code=500, detail="Error al guardar el archivo finalizado.")
        
        update_query = """
            UPDATE public.manzanas_lfi_workflow
            SET estado = :state, updated_at = CURRENT_TIMESTAMP
        """
        params = {"state": new_state, "s": seccion, "m": manzana}
        if disposicion:
            update_query += ", disposicion = :disp"
            params["disp"] = disposicion
        if safe_filename:
            update_query += ", archivo_finalizado = :file_fin"
            params["file_fin"] = safe_filename
            
        update_query += " WHERE seccion = :s AND manzana = :m"
        conn.execute(text(update_query), params)
            
        if comentario:
            note_text = f"*** REVISIÓN [{decision.upper()}]: {comentario} ***"
            conn.execute(text("""
                INSERT INTO public.manzanas_lfi_notes (seccion, manzana, username, nota, created_at)
                VALUES (:s, :m, :u, :n, CURRENT_TIMESTAMP)
            """), {"s": seccion, "m": manzana, "u": current_user.username, "n": note_text})
            
    return {"status": "ok", "estado": new_state, "archivo_finalizado": safe_filename}

@router.get("/api/ciudad3d/manzanas_lfi/download_trazado")
def download_trazado_lfi_file(
    seccion: str,
    manzana: str,
    file_type: str = Query("draft"),
    token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_from_param_or_header)
):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a esta sección")
        
    with engine.connect() as conn:
        col = "archivo_finalizado" if file_type == "final" else "archivo_trazado"
        row = conn.execute(text(f"""
            SELECT {col} FROM public.manzanas_lfi_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": seccion, "m": manzana}).fetchone()
        
        if not row or not row[0]:
            raise HTTPException(status_code=404, detail="No hay archivo subido de ese tipo para esta manzana.")
            
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "trazados_lfi", row[0]))
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="El archivo físico no fue encontrado en el servidor.")
            
        return FileResponse(file_path, filename=row[0])

@router.get("/api/ciudad3d/manzanas_lfi/download_pdf")
def download_lfi_pdf(
    seccion: str,
    manzana: str,
    token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_from_param_or_header)
):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a esta sección")
        
    s_clean = seccion.strip()
    m_clean = manzana.strip()
    
    barrio = "CABA"
    comuna = ""
    disposicion = ""
    estado = "Pendiente"
    analista = "Sin asignar"
    file_path = None
    
    with engine.connect() as conn:
        wf_row = conn.execute(text("""
            SELECT estado, analista_asignado, disposicion, archivo_trazado, archivo_finalizado
            FROM public.manzanas_lfi_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": s_clean, "m": m_clean}).fetchone()
        
        if wf_row:
            estado = wf_row[0] or "Pendiente"
            analista = wf_row[1] or "Sin asignar"
            disposicion = wf_row[2] or ""
            
            fname = wf_row[4] or wf_row[3]
            if fname:
                file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "trazados_lfi", fname))
                
    with geo_engine.connect() as geo_conn:
        bm_row = geo_conn.execute(text("""
            SELECT barrio, comuna FROM public.cur_parcelas_ok
            WHERE TRIM(seccion) = :s AND TRIM(manzana) = :m AND barrio IS NOT NULL AND TRIM(barrio) <> ''
            LIMIT 1
        """), {"s": s_clean, "m": m_clean}).fetchone()
        if bm_row:
            barrio = bm_row[0] or "CABA"
            comuna = str(bm_row[1]) if bm_row[1] else ""

    from pdf_generator import generate_lfi_a3_pdf
    pdf_bytes = generate_lfi_a3_pdf(
        seccion=s_clean,
        manzana=m_clean,
        barrio=barrio,
        comuna=comuna,
        disposicion=disposicion,
        estado=estado,
        analista=analista,
        file_path=file_path
    )
    
    filename = f"Ficha_A3_LFI_{s_clean}_{m_clean}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/api/ciudad3d/manzanas_lfi/disposicion")
def update_manzana_lfi_disposicion(req: LFIDisposicionRequest, current_user: User = Depends(get_current_user)):
    if not (current_user.permissions.get("lfi_dibujar") or current_user.permissions.get("lfi_revisar")):
        raise HTTPException(status_code=403, detail="No tiene permisos de dibujo o revisión de LFI ('lfi_dibujar'/'lfi_revisar') para actualizar la disposición.")
        
    s_clean = req.seccion.strip()
    m_clean = req.manzana.strip()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO public.manzanas_lfi_workflow (seccion, manzana, disposicion, updated_at)
            VALUES (:s, :m, :d, CURRENT_TIMESTAMP)
            ON CONFLICT (seccion, manzana)
            DO UPDATE SET disposicion = :d, updated_at = CURRENT_TIMESTAMP
        """), {"s": s_clean, "m": m_clean, "d": req.disposicion})
        
    return {"status": "ok"}

@router.get("/api/ciudad3d/manzanas_atipicas")
def get_ciudad3d_manzanas_atipicas(current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a Ciudad 3D")
    
    query = """
    SELECT m.seccion, m.manzana, m.barrio, m.comuna, m.gedo_documento, m.id_expediente, m.expediente, m.fecha_egreso,
           COALESCE(w.estado, 'Pendiente') AS estado,
           w.analista_asignado,
           w.disposicion,
           w.archivo_trazado
    FROM public.mv_morfologia_frente_interno_disposiciones m
    LEFT JOIN public.manzanas_atipicas_workflow w ON m.seccion = w.seccion AND m.manzana = w.manzana
    ORDER BY m.barrio, m.seccion, m.manzana
    """
    try:
        with engine.connect() as conn:
            res = conn.execute(text(query)).fetchall()
            return [
                {
                    "seccion": r[0],
                    "manzana": r[1],
                    "barrio": r[2] if r[2] else "SIN BARRIO",
                    "comuna": r[3] if r[3] else "SIN COMUNA",
                    "gedo_documento": r[4] if r[4] else "",
                    "id_expediente": r[5] if r[5] else "",
                    "expediente": r[6] if r[6] else "",
                    "fecha_egreso": str(r[7]) if r[7] else "",
                    "estado": r[8],
                    "analista_asignado": r[9] if r[9] else "",
                    "disposicion": r[10] if r[10] else "",
                    "archivo_trazado": r[11] if r[11] else ""
                }
                for r in res
            ]
    except Exception as e:
        logger.error(f"Error fetching atypical blocks: {e}")
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")

@router.post("/api/ciudad3d/manzanas_atipicas/assign")
def assign_manzana_atipica(req: AssignRequest, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("lfi_dibujar"):
        raise HTTPException(status_code=403, detail="No tiene permisos de dibujo de LFI ('lfi_dibujar') para asignarse manzanas.")
    
    with engine.begin() as conn:
        existing = conn.execute(text("""
            SELECT estado, analista_asignado FROM public.manzanas_atipicas_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": req.seccion, "m": req.manzana}).fetchone()
        
        if existing:
            if existing[0] != 'Pendiente':
                raise HTTPException(status_code=400, detail=f"Esta manzana ya está en estado '{existing[0]}'")
            
        conn.execute(text("""
            INSERT INTO public.manzanas_atipicas_workflow (seccion, manzana, estado, analista_asignado, updated_at)
            VALUES (:s, :m, 'En curso', :a, CURRENT_TIMESTAMP)
            ON CONFLICT (seccion, manzana) 
            DO UPDATE SET estado = 'En curso', analista_asignado = :a, updated_at = CURRENT_TIMESTAMP
        """), {"s": req.seccion, "m": req.manzana, "a": current_user.username})
        
    return {"status": "ok", "estado": "En curso", "analista_asignado": current_user.username}

@router.get("/api/ciudad3d/manzanas_atipicas/notes")
def get_manzana_atipica_notes(seccion: str, manzana: str, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a Ciudad 3D")
    
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT n.id, n.username, n.nota, n.created_at, u.full_name
            FROM public.manzanas_atipicas_notes n
            LEFT JOIN public.auth_users u ON n.username = u.username
            WHERE n.seccion = :s AND n.manzana = :m
            ORDER BY n.created_at DESC
        """), {"s": seccion, "m": manzana}).fetchall()
        
        return [
            {
                "id": r[0],
                "username": r[1],
                "nota": r[2],
                "created_at": str(r[3]),
                "full_name": r[4] if r[4] else r[1]
            }
            for r in res
        ]

@router.post("/api/ciudad3d/manzanas_atipicas/notes")
def add_manzana_atipica_note(req: NoteRequest, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a Ciudad 3D")
    
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO public.manzanas_atipicas_notes (seccion, manzana, username, nota, created_at)
            VALUES (:s, :m, :u, :n, CURRENT_TIMESTAMP)
        """), {"s": req.seccion, "m": req.manzana, "u": current_user.username, "n": req.nota})
        
    return {"status": "ok"}

@router.post("/api/ciudad3d/manzanas_atipicas/upload")
async def upload_trazado(
    seccion: str = Form(...),
    manzana: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    try:
        if not current_user.permissions.get("lfi_dibujar"):
            raise HTTPException(status_code=403, detail="No tiene permisos de dibujo de LFI ('lfi_dibujar') para subir archivos.")
            
        sec_clean = seccion.strip()
        man_clean = manzana.strip()
        
        sec_unpadded = sec_clean.lstrip('0') or '0'
        sec_padded = sec_clean.zfill(3)
        man_unpadded = man_clean.lstrip('0') or '0'
        man_padded = man_clean.zfill(3)

        file_filename = file.filename or "trazado.dxf"
        file_ext = os.path.splitext(file_filename)[1]
        if not file_ext or file_ext.lower() not in ['.dxf', '.dwg']:
            raise HTTPException(status_code=400, detail="Solo se permiten archivos con extensión .dxf o .dwg")

        with engine.connect() as conn:
            existing = conn.execute(text("""
                SELECT analista_asignado, estado, seccion, manzana 
                FROM public.manzanas_atipicas_workflow
                WHERE (TRIM(seccion) IN (:s, :s_unpadded, :s_padded))
                  AND (TRIM(manzana) IN (:m, :m_unpadded, :m_padded))
            """), {
                "s": sec_clean, "s_unpadded": sec_unpadded, "s_padded": sec_padded,
                "m": man_clean, "m_unpadded": man_unpadded, "m_padded": man_padded
            }).fetchone()
            
            if not existing:
                raise HTTPException(status_code=400, detail=f"La manzana {sec_clean}-{man_clean} no ha sido asignada ni iniciada.")
                
            assigned_user = (existing[0] or "").strip().lower()
            current_username = (current_user.username or "").strip().lower()
            
            if assigned_user and assigned_user != current_username and current_user.role.lower() not in ['admin', 'administrador']:
                raise HTTPException(status_code=403, detail=f"Esta manzana está asignada a {existing[0]}, no puede subir el archivo.")

            real_sec = existing[2]
            real_man = existing[3]

        upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "trazados"))
        try:
            os.makedirs(upload_dir, exist_ok=True)
        except Exception as dir_err:
            logger.error(f"Error creando directorio uploads: {dir_err}")

        safe_filename = f"{real_sec}-{real_man}-{int(time.time())}{file_ext}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Error saving uploaded file: {e}")
            raise HTTPException(status_code=500, detail=f"Error al guardar archivo en el servidor: {str(e)}")
            
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE public.manzanas_atipicas_workflow
                SET estado = 'Para revisión', archivo_trazado = :f, updated_at = CURRENT_TIMESTAMP
                WHERE seccion = :s AND manzana = :m
            """), {"s": real_sec, "m": real_man, "f": safe_filename})
            
        return {"status": "ok", "estado": "Para revisión", "archivo_trazado": safe_filename}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Error inesperado en upload_trazado: {exc}")
        raise HTTPException(status_code=500, detail=f"Error inesperado en el servidor: {str(exc)}")

@router.post("/api/ciudad3d/manzanas_atipicas/review")
def review_manzana_atipica(req: ReviewRequest, current_user: User = Depends(get_current_user)):
    if not current_user.permissions.get("lfi_revisar"):
        raise HTTPException(status_code=403, detail="No tiene permisos de revisión de LFI ('lfi_revisar') para revisar manzanas.")
        
    with engine.begin() as conn:
        existing = conn.execute(text("""
            SELECT estado FROM public.manzanas_atipicas_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": req.seccion, "m": req.manzana}).fetchone()
        
        if not existing or existing[0] != 'Para revisión':
            raise HTTPException(status_code=400, detail="Esta manzana no está en estado 'Para revisión'")
            
        new_state = 'Subir a Ciudad 3D' if req.decision.upper() == 'OK' else 'En curso'
        
        if req.disposicion:
            conn.execute(text("""
                UPDATE public.manzanas_atipicas_workflow
                SET estado = :state, disposicion = :disp, updated_at = CURRENT_TIMESTAMP
                WHERE seccion = :s AND manzana = :m
            """), {"state": new_state, "disp": req.disposicion, "s": req.seccion, "m": req.manzana})
        else:
            conn.execute(text("""
                UPDATE public.manzanas_atipicas_workflow
                SET estado = :state, updated_at = CURRENT_TIMESTAMP
                WHERE seccion = :s AND manzana = :m
            """), {"state": new_state, "s": req.seccion, "m": req.manzana})
            
        if req.comentario:
            note_text = f"*** REVISIÓN [{req.decision.upper()}]: {req.comentario} ***"
            conn.execute(text("""
                INSERT INTO public.manzanas_atipicas_notes (seccion, manzana, username, nota, created_at)
                VALUES (:s, :m, :u, :n, CURRENT_TIMESTAMP)
            """), {"s": req.seccion, "m": req.manzana, "u": current_user.username, "n": note_text})
            
    return {"status": "ok", "estado": new_state}

@router.get("/api/ciudad3d/manzanas_atipicas/download_trazado")
def download_trazado_file(seccion: str, manzana: str, token: Optional[str] = Query(None), current_user: User = Depends(get_current_user_from_param_or_header)):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a esta sección")
        
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT archivo_trazado FROM public.manzanas_atipicas_workflow
            WHERE seccion = :s AND manzana = :m
        """), {"s": seccion, "m": manzana}).fetchone()
        
        if not row or not row[0]:
            raise HTTPException(status_code=404, detail="No hay trazado subido para esta manzana.")
            
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "trazados", row[0]))
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="El archivo físico no fue encontrado en el servidor.")
            
        return FileResponse(file_path, filename=row[0])

@router.post("/api/ciudad3d/manzanas_atipicas/disposicion")
def update_manzana_atipica_disposicion(req: DisposicionRequest, current_user: User = Depends(get_current_user)):
    if not (current_user.permissions.get("lfi_dibujar") or current_user.permissions.get("lfi_revisar") or current_user.role.lower() in ['troneras', 'troneras-visor', 'admin', 'administrador']):
        raise HTTPException(status_code=403, detail="No tiene permisos de dibujo o revisión de LFI ('lfi_dibujar'/'lfi_revisar') para actualizar la disposición.")
        
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO public.manzanas_atipicas_workflow (seccion, manzana, disposicion, updated_at)
            VALUES (:s, :m, :d, CURRENT_TIMESTAMP)
            ON CONFLICT (seccion, manzana)
            DO UPDATE SET disposicion = :d, updated_at = CURRENT_TIMESTAMP
        """), {"s": req.seccion, "m": req.manzana, "d": req.disposicion})
        
    return {"status": "ok"}

@router.get("/api/ciudad3d/dxf/download")
async def download_manzana_dxf(
    seccion: str,
    manzana: str,
    token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_from_param_or_header)
):
    if not current_user.permissions.get("ciudad_3d"):
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a Ciudad 3D")
        
    warnings.filterwarnings("ignore")
    os.environ["DXF_WRITE_HATCH"] = "FALSE"
    
    try:
        import geopandas as gpd
        import pandas as pd
        import ezdxf
        from ezdxf.enums import TextEntityAlignment
        from shapely.geometry import LineString, MultiLineString
        import fiona
    except ImportError as ie:
        logger.error(f"Missing geospatial dependencies for DXF generation: {ie}")
        raise HTTPException(status_code=500, detail="El servidor no tiene instaladas las dependencias cartográficas.")
        
    def extract_lines(geom):
        if geom is None or geom.is_empty:
            return []
        gtype = geom.geom_type
        if gtype == 'Polygon':
            lines = [LineString(geom.exterior.coords)]
            for hole in geom.interiors:
                lines.append(LineString(hole.coords))
            return lines
        elif gtype == 'MultiPolygon':
            lines = []
            for poly in geom.geoms:
                lines.extend(extract_lines(poly))
            return lines
        elif gtype == 'LineString':
            return [geom]
        elif gtype == 'MultiLineString':
            return list(geom.geoms)
        elif gtype == 'GeometryCollection':
            lines = []
            for sub_geom in geom.geoms:
                lines.extend(extract_lines(sub_geom))
            return lines
        return []

    def polygon_to_boundary(geom):
        lines = extract_lines(geom)
        if not lines:
            return None
        return MultiLineString(lines)

    sec_escaped = seccion.strip()
    m_val = manzana.strip()
    
    if not sec_escaped or not m_val:
        raise HTTPException(status_code=400, detail="La sección y la manzana son obligatorias")

    from backend.routers.exportar_dwg import exportar_single_manzana_dxf

    try:
        temp_path = exportar_single_manzana_dxf(geo_engine, sec_escaped, m_val)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error generando DXF desde exportar_dwg: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando DXF: {e}")

    from starlette.background import BackgroundTasks
    
    def clean_temp():
        try:
            os.remove(temp_path)
        except Exception:
            pass
            
    background_tasks = BackgroundTasks()
    background_tasks.add_task(clean_temp)
    
    sec_folder = sec_escaped.zfill(3)
    m_folder = m_val.zfill(3)
    filename = f"{sec_folder}-{m_folder}.dxf"
    
    return FileResponse(
        temp_path,
        media_type="application/dxf",
        filename=filename,
        background=background_tasks
    )