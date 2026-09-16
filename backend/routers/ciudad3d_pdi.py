import os
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from database import pdi_engine
from schemas import User
from auth_utils import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pdi", tags=["Ciudad 3D - Backend PDI"])

VPN_ERROR_MESSAGE = "Verifica estar conectado a la red GCBA o tener la VPN activa"

# Whitelist de tablas permitidas para consultas de lectura en PDI
PDI_ALLOWED_TABLES: Dict[str, Dict[str, str]] = {
    "mo_parcelasmap": {
        "nombre": "Parcelas Map",
        "descripcion": "Capa cartográfica y geométrica de parcelas de la Ciudad",
        "icono": "fa-draw-polygon",
        "color": "#0284c7"
    },
    "mo_manzanasmap": {
        "nombre": "Manzanas Map",
        "descripcion": "Capa geométrica de manzanas urbanas consolidadas",
        "icono": "fa-cubes",
        "color": "#d97706"
    },
    "cur_objetosterritoriales": {
        "nombre": "Objetos Territoriales",
        "descripcion": "Polígonos y delimitaciones de afectaciones territoriales específicas",
        "icono": "fa-layer-group",
        "color": "#8b5cf6"
    },
    "cur_manzanasatipicas": {
        "nombre": "Manzanas Atípicas",
        "descripcion": "Manzanas con geometrías irregulares y parámetros LFI especiales",
        "icono": "fa-shapes",
        "color": "#ec4899"
    },
    "cur_parcelas": {
        "nombre": "Parcelas CUR",
        "descripcion": "Padrón parcelario del Código Urbanístico",
        "icono": "fa-map-location-dot",
        "color": "#10b981"
    },
    "aph_ssregic": {
        "nombre": "APH SSREGIC",
        "descripcion": "Áreas de Protección Histórica y Catálogo de Inmuebles Protegidos",
        "icono": "fa-landmark",
        "color": "#6366f1"
    },
    "cur_lfi_particularizadas": {
        "nombre": "LFI Particularizadas",
        "descripcion": "Trazados oficiales de Línea de Frente Interno particularizadas",
        "icono": "fa-bezier-curve",
        "color": "#06b6d4"
    },
    "cur_lib_particularizadas": {
        "nombre": "LIB Particularizadas",
        "descripcion": "Trazados oficiales de Línea Interna de Basamento particularizadas",
        "icono": "fa-vector-square",
        "color": "#14b8a6"
    },
    "cur_restricciones": {
        "nombre": "Restricciones Urbanas",
        "descripcion": "Restricciones de dominio y servidumbres urbanísticas",
        "icono": "fa-triangle-exclamation",
        "color": "#f59e0b"
    },
    "frentesparcelas": {
        "nombre": "Frentes de Parcelas",
        "descripcion": "Líneas de frente y afectaciones de línea oficial",
        "icono": "fa-arrows-left-right",
        "color": "#3b82f6"
    },
    "cur_tejido": {
        "nombre": "Tejido Urbano",
        "descripcion": "Volumetrías y capacidades constructivas del tejido",
        "icono": "fa-building",
        "color": "#64748b"
    }
}


@router.get("/status")
def get_pdi_status(current_user: User = Depends(get_current_user)):
    """
    Comprueba conectividad inmediata hacia la base de datos PostgreSQL geodb en 10.10.8.207.
    Si falla por timeout de red, devuelve el mensaje de verificación de VPN.
    """
    try:
        with pdi_engine.connect() as conn:
            db_name = conn.execute(text("SELECT current_database()")).scalar()
            version = conn.execute(text("SELECT version()")).scalar()
            return {
                "connected": True,
                "host": "10.10.8.207",
                "database": db_name or "geodb",
                "schema": "public",
                "version": version[:50] if version else "PostgreSQL",
                "message": "Conexión a la red corporativa GCBA / Base de datos PDI establecida correctamente."
            }
    except Exception as e:
        logger.warning(f"Fallo al conectar con Base de Datos PDI (10.10.8.207): {e}")
        return {
            "connected": False,
            "host": "10.10.8.207",
            "database": "geodb",
            "error": VPN_ERROR_MESSAGE,
            "detail": str(e)
        }


@router.get("/stats")
def get_pdi_stats(current_user: User = Depends(get_current_user)):
    """
    Devuelve las métricas principales y el conteo seguro de registros de las 11 tablas PDI.
    """
    try:
        with pdi_engine.connect() as conn:
            tables_summary: List[Dict[str, Any]] = []
            counts_map: Dict[str, int] = {}

            for table_name, meta in PDI_ALLOWED_TABLES.items():
                try:
                    # Consulta segura de solo lectura
                    cnt = conn.execute(text(f"SELECT COUNT(*) FROM public.{table_name}")).scalar() or 0
                    counts_map[table_name] = int(cnt)
                    tables_summary.append({
                        "table_name": table_name,
                        "display_name": meta["nombre"],
                        "description": meta["descripcion"],
                        "icon": meta["icono"],
                        "color": meta["color"],
                        "count": int(cnt),
                        "status": "OK"
                    })
                except Exception as t_err:
                    logger.error(f"Error consultando tabla PDI {table_name}: {t_err}")
                    counts_map[table_name] = 0
                    tables_summary.append({
                        "table_name": table_name,
                        "display_name": meta["nombre"],
                        "description": meta["descripcion"],
                        "icon": meta["icono"],
                        "color": meta["color"],
                        "count": 0,
                        "status": "ERROR",
                        "error": str(t_err)
                    })

            return {
                "connected": True,
                "host": "10.10.8.207",
                "database": "geodb",
                "schema": "public",
                "kpis": {
                    "total_parcelas": counts_map.get("mo_parcelasmap", 0),
                    "total_manzanas": counts_map.get("mo_manzanasmap", 0),
                    "total_objetos_territoriales": counts_map.get("cur_objetosterritoriales", 0)
                },
                "tables": tables_summary
            }
    except Exception as e:
        logger.warning(f"Error en PDI stats (10.10.8.207): {e}")
        return {
            "connected": False,
            "host": "10.10.8.207",
            "database": "geodb",
            "error": VPN_ERROR_MESSAGE,
            "detail": str(e),
            "kpis": {
                "total_parcelas": 0,
                "total_manzanas": 0,
                "total_objetos_territoriales": 0
            },
            "tables": [
                {
                    "table_name": t,
                    "display_name": meta["nombre"],
                    "description": meta["descripcion"],
                    "icon": meta["icono"],
                    "color": meta["color"],
                    "count": 0,
                    "status": "UNREACHABLE"
                }
                for t, meta in PDI_ALLOWED_TABLES.items()
            ]
        }


@router.get("/table/{table_name}")
def get_pdi_table_preview(
    table_name: str,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    Consulta paginada y estrictamente de sólo lectura (SELECT) para explorar una tabla PDI específica.
    """
    clean_table = table_name.lower().strip()
    if clean_table not in PDI_ALLOWED_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Tabla no autorizada. Solo se permiten consultas a las 11 tablas autorizadas de PDI."
        )

    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)

    try:
        with pdi_engine.connect() as conn:
            # Conteo total
            total_count = conn.execute(text(f"SELECT COUNT(*) FROM public.{clean_table}")).scalar() or 0
            
            # Obtener columnas
            cols_res = conn.execute(text(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = :t
                ORDER BY ordinal_position
            """), {"t": clean_table}).fetchall()
            
            # Excluir o abreviar columnas geométricas pesadas si existen (para respuesta rápida JSON)
            col_names = [c[0] for c in cols_res]
            select_cols = []
            for col in col_names:
                if col.lower() in ('geom', 'geometry', 'the_geom', 'shape', 'wkb_geometry'):
                    select_cols.append(f"ST_AsText({col}) as {col}")
                else:
                    select_cols.append(col)
            
            cols_clause = ", ".join(select_cols) if select_cols else "*"
            
            query = text(f"SELECT {cols_clause} FROM public.{clean_table} LIMIT :lim OFFSET :off")
            rows = conn.execute(query, {"lim": safe_limit, "off": safe_offset}).mappings().fetchall()
            
            return {
                "connected": True,
                "table_name": clean_table,
                "meta": PDI_ALLOWED_TABLES[clean_table],
                "total_rows": int(total_count),
                "limit": safe_limit,
                "offset": safe_offset,
                "columns": [c[0] for c in cols_res],
                "rows": [dict(r) for r in rows]
            }
    except Exception as e:
        logger.error(f"Error consultando tabla PDI {clean_table}: {e}")
        return {
            "connected": False,
            "table_name": clean_table,
            "error": VPN_ERROR_MESSAGE,
            "detail": str(e),
            "total_rows": 0,
            "rows": []
        }


@router.get("/validations")
def get_pdi_validations(current_user: User = Depends(get_current_user)):
    """
    Ejecuta el catálogo completo de validaciones territoriales, consistencia, duplicados,
    normativa y calidad geométrica en la base de datos PDI.
    """
    def _safe_rows(conn, sql, params=None):
        try:
            return [dict(r) for r in conn.execute(text(sql), params or {}).mappings().fetchall()]
        except Exception as e:
            logger.warning(f"Aviso en consulta de validación ({sql[:40]}...): {e}")
            return []

    def _safe_val(conn, sql, params=None):
        try:
            return conn.execute(text(sql), params or {}).scalar() or 0
        except Exception as e:
            logger.warning(f"Aviso en escalar de validación: {e}")
            return 0

    try:
        with pdi_engine.connect() as conn:
            validations_dict: Dict[str, Any] = {}

            # =========================================================================
            # 1. ESPEJADO DE CAPAS PRINCIPALES
            # =========================================================================
            # 1.1 Parcelas: mo_parcelasmap vs cur_parcelas
            q_p_mo_not_cur = _safe_rows(conn, """
                SELECT smp, seccion, manzana, parcela 
                FROM public.mo_parcelasmap 
                WHERE smp IS NOT NULL AND smp != ''
                  AND smp IN (
                      SELECT smp FROM public.mo_parcelasmap WHERE smp IS NOT NULL AND smp != ''
                      EXCEPT 
                      SELECT smp FROM public.cur_parcelas WHERE smp IS NOT NULL AND smp != ''
                  )
                ORDER BY smp LIMIT 200
            """)
            q_p_cur_not_mo = _safe_rows(conn, """
                SELECT smp, seccion, manzana, parcela 
                FROM public.cur_parcelas 
                WHERE smp IS NOT NULL AND smp != ''
                  AND smp IN (
                      SELECT smp FROM public.cur_parcelas WHERE smp IS NOT NULL AND smp != ''
                      EXCEPT 
                      SELECT smp FROM public.mo_parcelasmap WHERE smp IS NOT NULL AND smp != ''
                  )
                ORDER BY smp LIMIT 200
            """)
            tot_mo_p = _safe_val(conn, "SELECT COUNT(DISTINCT smp) FROM public.mo_parcelasmap WHERE smp IS NOT NULL AND smp != ''")
            tot_cur_p = _safe_val(conn, "SELECT COUNT(DISTINCT smp) FROM public.cur_parcelas WHERE smp IS NOT NULL AND smp != ''")
            p_disc = len(q_p_mo_not_cur) + len(q_p_cur_not_mo)
            validations_dict["parcelas_mo_vs_cur"] = {
                "category": "Espejado de Tablas",
                "title": "Espejado de Parcelas (SMP): mo_parcelasmap vs cur_parcelas",
                "table_a": "mo_parcelasmap",
                "table_b": "cur_parcelas",
                "key_field": "smp",
                "type": "two_way",
                "total_table_a": int(tot_mo_p),
                "total_table_b": int(tot_cur_p),
                "missing_in_b_count": len(q_p_mo_not_cur),
                "missing_in_b": q_p_mo_not_cur,
                "missing_in_a_count": len(q_p_cur_not_mo),
                "missing_in_a": q_p_cur_not_mo,
                "error_count": p_disc,
                "status": "DIVERGENTE" if p_disc > 0 else "OK"
            }

            # 1.2 Manzanas: mo_manzanasmap vs cur_manzanasatipicas
            q_m_mo_not_cur = _safe_rows(conn, """
                SELECT sm, seccion, manzana, mz_tipo 
                FROM public.mo_manzanasmap 
                WHERE sm IS NOT NULL AND sm != ''
                  AND sm IN (
                      SELECT sm FROM public.mo_manzanasmap WHERE sm IS NOT NULL AND sm != ''
                      EXCEPT 
                      SELECT sm FROM public.cur_manzanasatipicas WHERE sm IS NOT NULL AND sm != ''
                  )
                ORDER BY sm LIMIT 200
            """)
            q_m_cur_not_mo = _safe_rows(conn, """
                SELECT sm, seccion, manzana, mz_tipo 
                FROM public.cur_manzanasatipicas 
                WHERE sm IS NOT NULL AND sm != ''
                  AND sm IN (
                      SELECT sm FROM public.cur_manzanasatipicas WHERE sm IS NOT NULL AND sm != ''
                      EXCEPT 
                      SELECT sm FROM public.mo_manzanasmap WHERE sm IS NOT NULL AND sm != ''
                  )
                ORDER BY sm LIMIT 200
            """)
            tot_mo_m = _safe_val(conn, "SELECT COUNT(DISTINCT sm) FROM public.mo_manzanasmap WHERE sm IS NOT NULL AND sm != ''")
            tot_cur_m = _safe_val(conn, "SELECT COUNT(DISTINCT sm) FROM public.cur_manzanasatipicas WHERE sm IS NOT NULL AND sm != ''")
            m_disc = len(q_m_mo_not_cur) + len(q_m_cur_not_mo)
            validations_dict["manzanas_mo_vs_cur"] = {
                "category": "Espejado de Tablas",
                "title": "Espejado de Manzanas (SM): mo_manzanasmap vs cur_manzanasatipicas",
                "table_a": "mo_manzanasmap",
                "table_b": "cur_manzanasatipicas",
                "key_field": "sm",
                "type": "two_way",
                "total_table_a": int(tot_mo_m),
                "total_table_b": int(tot_cur_m),
                "missing_in_b_count": len(q_m_mo_not_cur),
                "missing_in_b": q_m_mo_not_cur,
                "missing_in_a_count": len(q_m_cur_not_mo),
                "missing_in_a": q_m_cur_not_mo,
                "error_count": m_disc,
                "status": "DIVERGENTE" if m_disc > 0 else "OK"
            }

            # 1.3 Frentes: mo_parcelasmap vs frentesparcelas
            q_fp_mo_not_fp = _safe_rows(conn, """
                SELECT smp, seccion, manzana, parcela 
                FROM public.mo_parcelasmap 
                WHERE smp IS NOT NULL AND smp != ''
                  AND smp IN (
                      SELECT smp FROM public.mo_parcelasmap WHERE smp IS NOT NULL AND smp != ''
                      EXCEPT 
                      SELECT smp FROM public.frentesparcelas WHERE smp IS NOT NULL AND smp != ''
                  )
                ORDER BY smp LIMIT 200
            """)
            q_fp_fp_not_mo = _safe_rows(conn, """
                SELECT DISTINCT smp, seccion, manzana, parcela 
                FROM public.frentesparcelas 
                WHERE smp IS NOT NULL AND smp != ''
                  AND smp IN (
                      SELECT smp FROM public.frentesparcelas WHERE smp IS NOT NULL AND smp != ''
                      EXCEPT 
                      SELECT smp FROM public.mo_parcelasmap WHERE smp IS NOT NULL AND smp != ''
                  )
                ORDER BY smp LIMIT 200
            """)
            tot_fp = _safe_val(conn, "SELECT COUNT(DISTINCT smp) FROM public.frentesparcelas WHERE smp IS NOT NULL AND smp != ''")
            fp_disc = len(q_fp_mo_not_fp) + len(q_fp_fp_not_mo)
            validations_dict["parcelas_mo_vs_frentes"] = {
                "category": "Espejado de Tablas",
                "title": "Espejado de Frentes (SMP): mo_parcelasmap vs frentesparcelas",
                "table_a": "mo_parcelasmap",
                "table_b": "frentesparcelas",
                "key_field": "smp",
                "type": "two_way",
                "total_table_a": int(tot_mo_p),
                "total_table_b": int(tot_fp),
                "missing_in_b_count": len(q_fp_mo_not_fp),
                "missing_in_b": q_fp_mo_not_fp,
                "missing_in_a_count": len(q_fp_fp_not_mo),
                "missing_in_a": q_fp_fp_not_mo,
                "error_count": fp_disc,
                "status": "DIVERGENTE" if fp_disc > 0 else "OK"
            }

            # =========================================================================
            # 2. BARRIOS Y COMUNAS
            # =========================================================================
            # 2.1 Más de un barrio por manzana en cur_parcelas
            r_barrio_extra = _safe_rows(conn, """
                SELECT sm, COUNT(DISTINCT barrio) AS cantidad_valores, string_agg(DISTINCT barrio, ', ') AS detalle_valores 
                FROM public.cur_parcelas 
                WHERE sm IS NOT NULL AND barrio IS NOT NULL AND barrio != ''
                GROUP BY sm 
                HAVING COUNT(DISTINCT barrio) > 1 
                ORDER BY cantidad_valores DESC LIMIT 100
            """)
            validations_dict["barrio_extra_cur_parcelas"] = {
                "category": "Barrios y Comunas",
                "title": "Más de un Barrio para una Manzana (cur_parcelas)",
                "table_a": "cur_parcelas",
                "key_field": "sm",
                "type": "single",
                "records": r_barrio_extra,
                "error_count": len(r_barrio_extra),
                "status": "DIVERGENTE" if len(r_barrio_extra) > 0 else "OK"
            }

            # 2.2 Más de una comuna por manzana en cur_parcelas
            r_comuna_extra = _safe_rows(conn, """
                SELECT sm, COUNT(DISTINCT comuna) AS cantidad_valores, string_agg(DISTINCT CAST(comuna AS text), ', ') AS detalle_valores 
                FROM public.cur_parcelas 
                WHERE sm IS NOT NULL AND comuna IS NOT NULL
                GROUP BY sm 
                HAVING COUNT(DISTINCT comuna) > 1 
                ORDER BY cantidad_valores DESC LIMIT 100
            """)
            validations_dict["comuna_extra_cur_parcelas"] = {
                "category": "Barrios y Comunas",
                "title": "Más de una Comuna para una Manzana (cur_parcelas)",
                "table_a": "cur_parcelas",
                "key_field": "sm",
                "type": "single",
                "records": r_comuna_extra,
                "error_count": len(r_comuna_extra),
                "status": "DIVERGENTE" if len(r_comuna_extra) > 0 else "OK"
            }

            # 2.3 Barrios NULL en mo_parcelasmap
            r_b_null_mo = _safe_rows(conn, "SELECT smp, seccion, manzana, parcela FROM public.mo_parcelasmap WHERE barrios IS NULL OR barrios = '' LIMIT 100")
            validations_dict["barrios_null_mo_parcelasmap"] = {
                "category": "Barrios y Comunas",
                "title": "Barrios NULL o Vacío en mo_parcelasmap",
                "table_a": "mo_parcelasmap",
                "key_field": "smp",
                "type": "single",
                "records": r_b_null_mo,
                "error_count": len(r_b_null_mo),
                "status": "DIVERGENTE" if len(r_b_null_mo) > 0 else "OK"
            }

            # 2.4 Barrios NULL en cur_parcelas
            r_b_null_cur = _safe_rows(conn, "SELECT smp, seccion, manzana, parcela FROM public.cur_parcelas WHERE barrio IS NULL OR barrio = '' LIMIT 100")
            validations_dict["barrio_null_cur_parcelas"] = {
                "category": "Barrios y Comunas",
                "title": "Barrio NULL o Vacío en cur_parcelas",
                "table_a": "cur_parcelas",
                "key_field": "smp",
                "type": "single",
                "records": r_b_null_cur,
                "error_count": len(r_b_null_cur),
                "status": "DIVERGENTE" if len(r_b_null_cur) > 0 else "OK"
            }

            # 2.5 Comuna NULL en mo_parcelasmap
            r_c_null_mo = _safe_rows(conn, "SELECT smp, seccion, manzana, parcela FROM public.mo_parcelasmap WHERE comuna IS NULL OR CAST(comuna AS text) = '' LIMIT 100")
            validations_dict["comuna_null_mo_parcelasmap"] = {
                "category": "Barrios y Comunas",
                "title": "Comuna NULL o Vacía en mo_parcelasmap",
                "table_a": "mo_parcelasmap",
                "key_field": "smp",
                "type": "single",
                "records": r_c_null_mo,
                "error_count": len(r_c_null_mo),
                "status": "DIVERGENTE" if len(r_c_null_mo) > 0 else "OK"
            }

            # 2.6 Comuna NULL en cur_parcelas
            r_c_null_cur = _safe_rows(conn, "SELECT smp, seccion, manzana, parcela FROM public.cur_parcelas WHERE comuna IS NULL OR CAST(comuna AS text) = '' LIMIT 100")
            validations_dict["comuna_null_cur_parcelas"] = {
                "category": "Barrios y Comunas",
                "title": "Comuna NULL o Vacía en cur_parcelas",
                "table_a": "cur_parcelas",
                "key_field": "smp",
                "type": "single",
                "records": r_c_null_cur,
                "error_count": len(r_c_null_cur),
                "status": "DIVERGENTE" if len(r_c_null_cur) > 0 else "OK"
            }

            # =========================================================================
            # 3. NORMATIVA, EDIFICABILIDAD Y ÁREAS ESPECIALES
            # =========================================================================
            # 3.1 Áreas Especiales nulas cuando uni_edif_1 = 0
            r_area_esp_null = _safe_rows(conn, """
                SELECT smp, seccion, manzana, parcela, uni_edif_1, dist_1_grp AS detalle 
                FROM public.cur_parcelas 
                WHERE uni_edif_1 = 0 AND (dist_1_grp IS NULL OR dist_1_grp = '') 
                LIMIT 100
            """)
            validations_dict["area_esp_null_cur_parcelas"] = {
                "category": "Normativa y Edificabilidad",
                "title": "Áreas Especiales NULL cuando uni_edif_1 = 0 (cur_parcelas)",
                "table_a": "cur_parcelas",
                "key_field": "smp",
                "type": "single",
                "records": r_area_esp_null,
                "error_count": len(r_area_esp_null),
                "status": "DIVERGENTE" if len(r_area_esp_null) > 0 else "OK"
            }

            # 3.2 Plano Límite nulo con uni_edif_1 > 0
            r_plano_l_null = _safe_rows(conn, """
                SELECT smp, seccion, manzana, parcela, uni_edif_1, plano_l AS detalle 
                FROM public.cur_parcelas 
                WHERE uni_edif_1 > 0 AND plano_l IS NULL 
                LIMIT 100
            """)
            validations_dict["plano_limite_null_cur_parcelas"] = {
                "category": "Normativa y Edificabilidad",
                "title": "Plano Límite NULL con Unidad de Edificabilidad > 0 (cur_parcelas)",
                "table_a": "cur_parcelas",
                "key_field": "smp",
                "type": "single",
                "records": r_plano_l_null,
                "error_count": len(r_plano_l_null),
                "status": "DIVERGENTE" if len(r_plano_l_null) > 0 else "OK"
            }

            # =========================================================================
            # 4. CONSISTENCIA ECONÓMICA (INCIDENCIA Y ALÍCUOTAS POR MANZANA)
            # =========================================================================
            # 4.1 Incidencia UVA mixta por manzana
            r_incidencia_mix = _safe_rows(conn, """
                SELECT sm, COUNT(DISTINCT inc_uva_21) AS cantidad_valores, string_agg(DISTINCT CAST(inc_uva_21 AS text), ', ') AS detalle_valores 
                FROM public.cur_parcelas 
                WHERE sm IS NOT NULL AND inc_uva_21 IS NOT NULL
                GROUP BY sm 
                HAVING COUNT(DISTINCT inc_uva_21) > 1 
                ORDER BY cantidad_valores DESC LIMIT 100
            """)
            validations_dict["incidencia_mix_cur_parcelas"] = {
                "category": "Consistencia Económica",
                "title": "Más de un valor de Incidencia UVA por Manzana (cur_parcelas)",
                "table_a": "cur_parcelas",
                "key_field": "sm",
                "type": "single",
                "records": r_incidencia_mix,
                "error_count": len(r_incidencia_mix),
                "status": "DIVERGENTE" if len(r_incidencia_mix) > 0 else "OK"
            }

            # 4.2 Alícuota mixta por manzana
            r_alicuota_mix = _safe_rows(conn, """
                SELECT sm, COUNT(DISTINCT alicuota) AS cantidad_valores, string_agg(DISTINCT CAST(alicuota AS text), ', ') AS detalle_valores 
                FROM public.cur_parcelas 
                WHERE sm IS NOT NULL AND alicuota IS NOT NULL
                GROUP BY sm 
                HAVING COUNT(DISTINCT alicuota) > 1 
                ORDER BY cantidad_valores DESC LIMIT 100
            """)
            validations_dict["alicuota_mix_cur_parcelas"] = {
                "category": "Consistencia Económica",
                "title": "Más de un valor de Alícuota por Manzana (cur_parcelas)",
                "table_a": "cur_parcelas",
                "key_field": "sm",
                "type": "single",
                "records": r_alicuota_mix,
                "error_count": len(r_alicuota_mix),
                "status": "DIVERGENTE" if len(r_alicuota_mix) > 0 else "OK"
            }

            # =========================================================================
            # 5. DUPLICADOS E INCONSISTENCIAS DE CONCATENACIÓN (SM / SMP)
            # =========================================================================
            # 5.1 SM duplicados por concatenación en cur_manzanasatipicas
            r_sm_concat_cur = _safe_rows(conn, """
                SELECT sm, count(*) AS cantidad 
                FROM (
                    SELECT seccion||'-'||manzana AS sm 
                    FROM public.cur_manzanasatipicas 
                    WHERE seccion IS NOT NULL AND manzana IS NOT NULL
                ) a 
                GROUP BY sm HAVING count(*) > 1 
                ORDER BY cantidad DESC LIMIT 100
            """)
            validations_dict["duplicados_sm_concat_cur_manzanas"] = {
                "category": "Duplicados y Concatenación",
                "title": "SM duplicados por concatenación SEC-MZA (cur_manzanasatipicas)",
                "table_a": "cur_manzanasatipicas",
                "key_field": "sm",
                "type": "single",
                "records": r_sm_concat_cur,
                "error_count": len(r_sm_concat_cur),
                "status": "DIVERGENTE" if len(r_sm_concat_cur) > 0 else "OK"
            }

            # 5.2 SM duplicados por concatenación en mo_manzanasmap
            r_sm_concat_mo = _safe_rows(conn, """
                SELECT sm, count(*) AS cantidad 
                FROM (
                    SELECT seccion||'-'||manzana AS sm 
                    FROM public.mo_manzanasmap 
                    WHERE seccion IS NOT NULL AND manzana IS NOT NULL
                ) a 
                GROUP BY sm HAVING count(*) > 1 
                ORDER BY cantidad DESC LIMIT 100
            """)
            validations_dict["duplicados_sm_concat_mo_manzanas"] = {
                "category": "Duplicados y Concatenación",
                "title": "SM duplicados por concatenación SEC-MZA (mo_manzanasmap)",
                "table_a": "mo_manzanasmap",
                "key_field": "sm",
                "type": "single",
                "records": r_sm_concat_mo,
                "error_count": len(r_sm_concat_mo),
                "status": "DIVERGENTE" if len(r_sm_concat_mo) > 0 else "OK"
            }

            # 5.3 SM duplicados directos en mo_manzanasmap
            r_sm_dup_mo = _safe_rows(conn, """
                SELECT sm, count(*) AS cantidad 
                FROM public.mo_manzanasmap 
                WHERE sm IS NOT NULL AND sm != ''
                GROUP BY sm HAVING count(*) > 1 
                ORDER BY cantidad DESC LIMIT 100
            """)
            validations_dict["duplicados_sm_directo_mo_manzanas"] = {
                "category": "Duplicados y Concatenación",
                "title": "SM duplicados por campo directo (mo_manzanasmap)",
                "table_a": "mo_manzanasmap",
                "key_field": "sm",
                "type": "single",
                "records": r_sm_dup_mo,
                "error_count": len(r_sm_dup_mo),
                "status": "DIVERGENTE" if len(r_sm_dup_mo) > 0 else "OK"
            }

            # 5.4 SM duplicados directos en cur_manzanasatipicas
            r_sm_dup_cur = _safe_rows(conn, """
                SELECT sm, count(*) AS cantidad 
                FROM public.cur_manzanasatipicas 
                WHERE sm IS NOT NULL AND sm != ''
                GROUP BY sm HAVING count(*) > 1 
                ORDER BY cantidad DESC LIMIT 100
            """)
            validations_dict["duplicados_sm_directo_cur_manzanas"] = {
                "category": "Duplicados y Concatenación",
                "title": "SM duplicados por campo directo (cur_manzanasatipicas)",
                "table_a": "cur_manzanasatipicas",
                "key_field": "sm",
                "type": "single",
                "records": r_sm_dup_cur,
                "error_count": len(r_sm_dup_cur),
                "status": "DIVERGENTE" if len(r_sm_dup_cur) > 0 else "OK"
            }

            # 5.5 SMP no coincide con concatenación en mo_parcelasmap
            r_smp_diff_mo = _safe_rows(conn, """
                SELECT smp, seccion||'-'||manzana||'-'||parcela AS smp_concatenado, seccion, manzana, parcela 
                FROM public.mo_parcelasmap 
                WHERE seccion IS NOT NULL AND manzana IS NOT NULL AND parcela IS NOT NULL 
                  AND (seccion||'-'||manzana||'-'||parcela) <> smp 
                LIMIT 100
            """)
            validations_dict["smp_no_coincide_concat_mo_parcelas"] = {
                "category": "Duplicados y Concatenación",
                "title": "SMP no coincide con concatenación SEC-MZA-PARC (mo_parcelasmap)",
                "table_a": "mo_parcelasmap",
                "key_field": "smp",
                "type": "single",
                "records": r_smp_diff_mo,
                "error_count": len(r_smp_diff_mo),
                "status": "DIVERGENTE" if len(r_smp_diff_mo) > 0 else "OK"
            }

            # 5.6 SMP no coincide con concatenación en cur_parcelas
            r_smp_diff_cur = _safe_rows(conn, """
                SELECT smp, seccion||'-'||manzana||'-'||parcela AS smp_concatenado, seccion, manzana, parcela 
                FROM public.cur_parcelas 
                WHERE seccion IS NOT NULL AND manzana IS NOT NULL AND parcela IS NOT NULL 
                  AND (seccion||'-'||manzana||'-'||parcela) <> smp 
                LIMIT 100
            """)
            validations_dict["smp_no_coincide_concat_cur_parcelas"] = {
                "category": "Duplicados y Concatenación",
                "title": "SMP no coincide con concatenación SEC-MZA-PARC (cur_parcelas)",
                "table_a": "cur_parcelas",
                "key_field": "smp",
                "type": "single",
                "records": r_smp_diff_cur,
                "error_count": len(r_smp_diff_cur),
                "status": "DIVERGENTE" if len(r_smp_diff_cur) > 0 else "OK"
            }

            # 5.7 SMP duplicados directos en cur_parcelas
            r_smp_dup_cur = _safe_rows(conn, """
                SELECT smp, count(*) AS cantidad 
                FROM public.cur_parcelas 
                WHERE smp IS NOT NULL AND smp != ''
                GROUP BY smp HAVING count(*) > 1 
                ORDER BY cantidad DESC LIMIT 100
            """)
            validations_dict["duplicados_smp_directo_cur_parcelas"] = {
                "category": "Duplicados y Concatenación",
                "title": "SMP duplicados por campo directo (cur_parcelas)",
                "table_a": "cur_parcelas",
                "key_field": "smp",
                "type": "single",
                "records": r_smp_dup_cur,
                "error_count": len(r_smp_dup_cur),
                "status": "DIVERGENTE" if len(r_smp_dup_cur) > 0 else "OK"
            }

            # 5.8 SMP duplicados directos en mo_parcelasmap
            r_smp_dup_mo = _safe_rows(conn, """
                SELECT smp, count(*) AS cantidad 
                FROM public.mo_parcelasmap 
                WHERE smp IS NOT NULL AND smp != ''
                GROUP BY smp HAVING count(*) > 1 
                ORDER BY cantidad DESC LIMIT 100
            """)
            validations_dict["duplicados_smp_directo_mo_parcelas"] = {
                "category": "Duplicados y Concatenación",
                "title": "SMP duplicados por campo directo (mo_parcelasmap)",
                "table_a": "mo_parcelasmap",
                "key_field": "smp",
                "type": "single",
                "records": r_smp_dup_mo,
                "error_count": len(r_smp_dup_mo),
                "status": "DIVERGENTE" if len(r_smp_dup_mo) > 0 else "OK"
            }

            # =========================================================================
            # 6. CALIDAD GEOMÉTRICA Y TIPOLOGÍA MZ_TIPO
            # =========================================================================
            # 6.1 Superposición de parcelas en mo_parcelasmap
            r_superposicion = _safe_rows(conn, """
                SELECT a.smp, b.smp AS superpuesto, a.seccion, a.manzana, a.parcela 
                FROM public.mo_parcelasmap a 
                JOIN public.mo_parcelasmap b ON st_intersects(st_pointonsurface(a.the_geom), b.the_geom) 
                WHERE a.smp <> b.smp AND a.the_geom && b.the_geom 
                LIMIT 100
            """)
            validations_dict["superposicion_parcelas_mo"] = {
                "category": "Calidad Geométrica",
                "title": "Superposición geométrica entre Parcelas (mo_parcelasmap)",
                "table_a": "mo_parcelasmap",
                "key_field": "smp",
                "type": "single",
                "records": r_superposicion,
                "error_count": len(r_superposicion),
                "status": "DIVERGENTE" if len(r_superposicion) > 0 else "OK"
            }

            # 6.2 Geometrías de parcelas inválidas en mo_parcelasmap
            r_p_invalidas = _safe_rows(conn, """
                SELECT smp, seccion, manzana, parcela, st_isvalidreason(the_geom) AS motivo 
                FROM public.mo_parcelasmap 
                WHERE st_isvalid(the_geom) IS FALSE 
                LIMIT 100
            """)
            validations_dict["parcelas_invalidas_mo"] = {
                "category": "Calidad Geométrica",
                "title": "Geometría de Parcelas Inválidas (mo_parcelasmap)",
                "table_a": "mo_parcelasmap",
                "key_field": "smp",
                "type": "single",
                "records": r_p_invalidas,
                "error_count": len(r_p_invalidas),
                "status": "DIVERGENTE" if len(r_p_invalidas) > 0 else "OK"
            }

            # 6.3 Geometrías de manzanas inválidas en mo_manzanasmap
            r_m_invalidas = _safe_rows(conn, """
                SELECT sm, seccion, manzana, st_isvalidreason(the_geom) AS motivo 
                FROM public.mo_manzanasmap 
                WHERE st_isvalid(the_geom) IS FALSE 
                LIMIT 100
            """)
            validations_dict["manzanas_invalidas_mo"] = {
                "category": "Calidad Geométrica",
                "title": "Geometría de Manzanas Inválidas (mo_manzanasmap)",
                "table_a": "mo_manzanasmap",
                "key_field": "sm",
                "type": "single",
                "records": r_m_invalidas,
                "error_count": len(r_m_invalidas),
                "status": "DIVERGENTE" if len(r_m_invalidas) > 0 else "OK"
            }

            # 6.4 Campo mz_tipo NULL en cur_manzanasatipicas
            r_mz_tipo_cur = _safe_rows(conn, "SELECT sm, seccion, manzana FROM public.cur_manzanasatipicas WHERE mz_tipo IS NULL OR mz_tipo = '' LIMIT 100")
            validations_dict["mz_tipo_null_cur_manzanas"] = {
                "category": "Calidad Geométrica",
                "title": "Campo mz_tipo NULL o Vacío (cur_manzanasatipicas)",
                "table_a": "cur_manzanasatipicas",
                "key_field": "sm",
                "type": "single",
                "records": r_mz_tipo_cur,
                "error_count": len(r_mz_tipo_cur),
                "status": "DIVERGENTE" if len(r_mz_tipo_cur) > 0 else "OK"
            }

            # 6.5 Campo mz_tipo NULL en mo_manzanasmap
            r_mz_tipo_mo = _safe_rows(conn, "SELECT sm, seccion, manzana FROM public.mo_manzanasmap WHERE mz_tipo IS NULL OR mz_tipo = '' LIMIT 100")
            validations_dict["mz_tipo_null_mo_manzanas"] = {
                "category": "Calidad Geométrica",
                "title": "Campo mz_tipo NULL o Vacío (mo_manzanasmap)",
                "table_a": "mo_manzanasmap",
                "key_field": "sm",
                "type": "single",
                "records": r_mz_tipo_mo,
                "error_count": len(r_mz_tipo_mo),
                "status": "DIVERGENTE" if len(r_mz_tipo_mo) > 0 else "OK"
            }

            return {
                "connected": True,
                "total_validations_count": len(validations_dict),
                "validations": validations_dict
            }
    except Exception as e:
        logger.error(f"Error ejecutando catálogo de validaciones PDI: {e}")
        return {
            "connected": False,
            "error": VPN_ERROR_MESSAGE,
            "detail": str(e),
            "validations": {}
        }


# =============================================================================
# VALIDACIÓN CIUDAD 3D (API EPOK: seccion_edificabilidad)
# =============================================================================
import concurrent.futures
import urllib.request
import urllib.parse
import json

# Estado en memoria para escaneo en progreso / resultados de Ciudad 3D
c3d_scan_state = {
    "is_running": False,
    "total_to_check": 0,
    "checked_count": 0,
    "missing_count": 0,
    "last_run": None,
    "missing_records": [],
    "error": None
}


import time

def _check_smp_epok(row_dict: dict) -> dict:
    smp = row_dict.get("smp", "").strip()
    base_res = {
        "smp": smp,
        "seccion": row_dict.get("seccion"),
        "manzana": row_dict.get("manzana"),
        "parcela": row_dict.get("parcela"),
        "status": "OK",
        "error_msg": None,
        "status_code": 200,
        "is_missing": False
    }
    if not smp:
        base_res["status"] = "ERROR"
        base_res["error_msg"] = "SMP vacío"
        return base_res

    url = f"https://epok.buenosaires.gob.ar/cur3d/seccion_edificabilidad/?smp={urllib.parse.quote(smp)}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Connection": "keep-alive"
    })

    # Hasta 3 reintentos con backoff progresivo para tolerar 503 / throttling del servidor EPOK
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                body = response.read().decode("utf-8", errors="ignore")
                data = json.loads(body)
                if isinstance(data, dict) and data.get("error") == "ObjetoTerritorial matching query does not exist.":
                    base_res["status"] = "ERROR"
                    base_res["is_missing"] = True
                    base_res["error_msg"] = "ObjetoTerritorial matching query does not exist."
                    base_res["status_code"] = response.status
                elif isinstance(data, dict) and "error" in data:
                    base_res["status"] = "ERROR"
                    base_res["is_missing"] = True
                    base_res["error_msg"] = str(data.get("error"))
                    base_res["status_code"] = response.status
                else:
                    base_res["status"] = "OK"
                    base_res["status_code"] = response.status
                return base_res
        except urllib.error.HTTPError as he:
            if he.code == 503 and attempt < max_retries - 1:
                # Servicio temporalmente saturado en EPOK: esperar y reintentar
                time.sleep(0.6 * (attempt + 1))
                continue
            base_res["status"] = "ERROR"
            base_res["is_missing"] = True
            base_res["error_msg"] = f"HTTP {he.code}"
            base_res["status_code"] = he.code
            return base_res
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))
                continue
            base_res["status"] = "ERROR"
            base_res["error_msg"] = f"Error de red: {str(e)}"
            base_res["status_code"] = 0
            return base_res
    return base_res


@router.get("/c3d-validation/status")
def get_c3d_validation_status(current_user: User = Depends(get_current_user)):
    """
    Retorna el estado actual de la validación contra la API de Ciudad 3D.
    """
    return {
        "connected": True,
        **c3d_scan_state
    }


@router.get("/c3d-validation/parcelas")
def get_c3d_validation_parcelas(
    seccion: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    Retorna el listado de parcelas para procesar en frontend con barra de progreso reactiva.
    """
    try:
        with pdi_engine.connect() as conn:
            query_str = """
                SELECT smp, seccion, manzana, parcela 
                FROM public.mo_parcelasmap 
                WHERE smp IS NOT NULL AND smp != ''
            """
            params = {}
            if seccion:
                query_str += " AND seccion = :sec"
                params["sec"] = seccion.strip().zfill(3)
            
            # Conteo total para la sección o universo
            count_query = f"SELECT COUNT(*) FROM public.mo_parcelasmap WHERE smp IS NOT NULL AND smp != ''"
            if seccion:
                count_query += " AND seccion = :sec"
            total = conn.execute(text(count_query), params).scalar() or 0

            query_str += " ORDER BY seccion, manzana, parcela LIMIT :lim OFFSET :off"
            params["lim"] = max(1, min(limit, 5000))
            params["off"] = max(0, offset)

            rows = conn.execute(text(query_str), params).mappings().fetchall()
            return {
                "connected": True,
                "total_available": int(total),
                "seccion": seccion,
                "limit": params["lim"],
                "offset": params["off"],
                "parcelas": [dict(r) for r in rows]
            }
    except Exception as e:
        logger.error(f"Error obteniendo parcelas para C3D: {e}")
        return {
            "connected": False,
            "error": VPN_ERROR_MESSAGE,
            "detail": str(e),
            "total_available": 0,
            "parcelas": []
        }


@router.post("/c3d-validation/check-batch")
def check_c3d_validation_batch(
    seccion: Optional[str] = None,
    limit: int = 1,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    Valida parcelas de forma estrictamente secuencial (1 a 1) contra la API EPOK de Ciudad 3D.
    Retorna el total real disponible en la base de datos para barrer el 100% de las parcelas.
    """
    try:
        with pdi_engine.connect() as conn:
            query_str = """
                SELECT smp, seccion, manzana, parcela 
                FROM public.mo_parcelasmap 
                WHERE smp IS NOT NULL AND smp != ''
            """
            params = {}
            if seccion:
                query_str += " AND seccion = :sec"
                params["sec"] = seccion.strip().zfill(3)
            
            # Conteo total real de parcelas para la sección seleccionada o para todas las secciones
            count_query = "SELECT COUNT(*) FROM public.mo_parcelasmap WHERE smp IS NOT NULL AND smp != ''"
            if seccion:
                count_query += " AND seccion = :sec"
            total = conn.execute(text(count_query), params).scalar() or 0

            query_str += " ORDER BY seccion, manzana, parcela LIMIT :lim OFFSET :off"
            params["lim"] = max(1, min(limit, 100))
            params["off"] = max(0, offset)

            rows = conn.execute(text(query_str), params).mappings().fetchall()
            rows_list = [dict(r) for r in rows]

            # Ejecución estrictamente secuencial de a una parcela por vez (1 a 1)
            all_results = []
            for row in rows_list:
                res = _check_smp_epok(row)
                all_results.append(res)

            ok_count = sum(1 for r in all_results if r["status"] == "OK")
            error_count = sum(1 for r in all_results if r["status"] != "OK")

            return {
                "connected": True,
                "total_available": int(total),
                "checked_count": len(rows_list),
                "ok_count": ok_count,
                "error_count": error_count,
                "seccion_filter": seccion,
                "limit": params["lim"],
                "offset": params["off"],
                "results": all_results
            }
    except Exception as e:
        logger.error(f"Error en check-batch C3D: {e}")
        return {
            "connected": False,
            "error": VPN_ERROR_MESSAGE,
            "detail": str(e),
            "total_available": 0,
            "checked_count": 0,
            "ok_count": 0,
            "error_count": 0,
            "results": []
        }


@router.get("/c3d-validation/secciones")
def get_c3d_validation_secciones(current_user: User = Depends(get_current_user)):
    """
    Retorna la lista de secciones catastrales con su conteo de parcelas para facilitar el barrido y validación.
    """
    try:
        with pdi_engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT seccion, COUNT(*) as total_parcelas
                FROM public.mo_parcelasmap
                WHERE seccion IS NOT NULL AND seccion != ''
                GROUP BY seccion
                ORDER BY seccion
            """)).mappings().fetchall()
            return {
                "connected": True,
                "secciones": [dict(r) for r in rows]
            }
    except Exception as e:
        logger.error(f"Error obteniendo secciones PDI: {e}")
        return {
            "connected": False,
            "error": VPN_ERROR_MESSAGE,
            "secciones": []
        }


@router.get("/c3d-validation/check-single/{smp}")
def check_c3d_validation_single(smp: str, current_user: User = Depends(get_current_user)):
    """
    Valida un SMP puntual directamente contra la API de Ciudad 3D.
    """
    clean_smp = smp.strip()
    result = _check_smp_epok({"smp": clean_smp})
    return {
        "smp": clean_smp,
        "is_missing": result is not None,
        "detail": result
    }


# =============================================================================
# ANÁLISIS DE MANZANAS ATÍPICAS (cur_manzanasatipicas vs cur_lfi/lib)
# =============================================================================

@router.get("/atipicas-analysis")
def get_pdi_atipicas_analysis(current_user: User = Depends(get_current_user)):
    """
    Analiza el universo completo de cur_manzanasatipicas donde mz_tipo = 'ATIPICA'.
    Calcula:
    1. Total de manzanas atípicas.
    2. Con disposición no nula / Sin disposición.
    3. De las que tienen disposición: Trazado SI vs Trazado NO (vs otros).
    4. De las que tienen Trazado SI: cuántas tienen LFI, LIB, ambas o ninguna cargadas en cur_lfi_particularizadas / cur_lib_particularizadas.
    """
    try:
        with pdi_engine.connect() as conn:
            # Métricas globales de mz_tipo = 'ATIPICA'
            kpis_q = text("""
                SELECT 
                    COUNT(*) as total_atipicas,
                    COUNT(CASE WHEN disposicio IS NOT NULL AND TRIM(disposicio) != '' THEN 1 END) as con_disposicion,
                    COUNT(CASE WHEN disposicio IS NULL OR TRIM(disposicio) = '' THEN 1 END) as sin_disposicion,
                    COUNT(CASE WHEN disposicio IS NOT NULL AND TRIM(disposicio) != '' AND UPPER(TRIM(trazado)) = 'SI' THEN 1 END) as disp_trazado_si,
                    COUNT(CASE WHEN disposicio IS NOT NULL AND TRIM(disposicio) != '' AND UPPER(TRIM(trazado)) = 'NO' THEN 1 END) as disp_trazado_no,
                    COUNT(CASE WHEN disposicio IS NOT NULL AND TRIM(disposicio) != '' AND (trazado IS NULL OR TRIM(trazado) NOT IN ('SI', 'NO')) THEN 1 END) as disp_trazado_otro
                FROM public.cur_manzanasatipicas
                WHERE UPPER(TRIM(mz_tipo)) = 'ATIPICA'
            """)
            kpis = dict(conn.execute(kpis_q).mappings().fetchone() or {})

            # Métricas detalladas para Trazado SI con cruce a LFI / LIB por campo SM
            lfi_lib_q = text("""
                WITH atipicas_si AS (
                    SELECT sm, seccion, manzana, disposicio, trazado, comuna
                    FROM public.cur_manzanasatipicas
                    WHERE UPPER(TRIM(mz_tipo)) = 'ATIPICA'
                      AND disposicio IS NOT NULL AND TRIM(disposicio) != ''
                      AND UPPER(TRIM(trazado)) = 'SI'
                ),
                lfi_agg AS (
                    SELECT sm, COUNT(*) as cant_lfi FROM public.cur_lfi_particularizadas WHERE sm IS NOT NULL GROUP BY sm
                ),
                lib_agg AS (
                    SELECT sm, COUNT(*) as cant_lib FROM public.cur_lib_particularizadas WHERE sm IS NOT NULL GROUP BY sm
                )
                SELECT 
                    COUNT(*) as total_trazado_si,
                    COUNT(CASE WHEN COALESCE(l.cant_lfi, 0) > 0 OR COALESCE(b.cant_lib, 0) > 0 THEN 1 END) as con_lfi_o_lib,
                    COUNT(CASE WHEN COALESCE(l.cant_lfi, 0) = 0 AND COALESCE(b.cant_lib, 0) = 0 THEN 1 END) as ninguna,
                    COUNT(CASE WHEN l.cant_lfi > 0 AND b.cant_lib > 0 THEN 1 END) as ambas,
                    COUNT(CASE WHEN l.cant_lfi > 0 AND (b.cant_lib IS NULL OR b.cant_lib = 0) THEN 1 END) as solo_lfi,
                    COUNT(CASE WHEN b.cant_lib > 0 AND (l.cant_lfi IS NULL OR l.cant_lfi = 0) THEN 1 END) as solo_lib,
                    COUNT(CASE WHEN l.cant_lfi > 0 THEN 1 END) as total_con_lfi,
                    COUNT(CASE WHEN b.cant_lib > 0 THEN 1 END) as total_con_lib
                FROM atipicas_si a
                LEFT JOIN lfi_agg l ON a.sm = l.sm
                LEFT JOIN lib_agg b ON a.sm = b.sm
            """)
            lfi_lib_res = dict(conn.execute(lfi_lib_q).mappings().fetchone() or {})

            return {
                "connected": True,
                "universo_atipicas": {
                    "total": kpis.get("total_atipicas", 0),
                    "con_disposicion": kpis.get("con_disposicion", 0),
                    "sin_disposicion": kpis.get("sin_disposicion", 0),
                    "disp_trazado_si": kpis.get("disp_trazado_si", 0),
                    "disp_trazado_no": kpis.get("disp_trazado_no", 0),
                    "disp_trazado_otro": kpis.get("disp_trazado_otro", 0)
                },
                "trazado_si_detalle": {
                    "total": lfi_lib_res.get("total_trazado_si", 0),
                    "con_lfi_o_lib": lfi_lib_res.get("con_lfi_o_lib", 0),
                    "ninguna": lfi_lib_res.get("ninguna", 0),
                    "ambas": lfi_lib_res.get("ambas", 0),
                    "solo_lfi": lfi_lib_res.get("solo_lfi", 0),
                    "solo_lib": lfi_lib_res.get("solo_lib", 0),
                    "total_con_lfi": lfi_lib_res.get("total_con_lfi", 0),
                    "total_con_lib": lfi_lib_res.get("total_con_lib", 0)
                }
            }
    except Exception as e:
        logger.error(f"Error obteniendo análisis de manzanas atípicas PDI: {e}")
        return {
            "connected": False,
            "error": VPN_ERROR_MESSAGE,
            "detail": str(e),
            "universo_atipicas": {},
            "trazado_si_detalle": {}
        }


@router.get("/atipicas-analysis/list")
def get_pdi_atipicas_list(
    filter_group: str = "todos",
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """
    Retorna el listado paginado y filtrado de manzanas atípicas con su estado morfológico de LFI/LIB.
    filter_group: 'todos', 'con_disp', 'sin_disp', 'trazado_si', 'trazado_no', 'con_lfi_o_lib', 'ambas', 'solo_lfi', 'solo_lib', 'ninguna'
    """
    safe_limit = max(1, min(limit, 500))
    safe_offset = max(0, offset)
    clean_search = f"%{search.strip()}%" if search and search.strip() else None

    where_clauses = ["UPPER(TRIM(m.mz_tipo)) = 'ATIPICA'"]
    params: Dict[str, Any] = {"lim": safe_limit, "off": safe_offset}

    if filter_group == "con_disp":
        where_clauses.append("(m.disposicio IS NOT NULL AND TRIM(m.disposicio) != '')")
    elif filter_group == "sin_disp":
        where_clauses.append("(m.disposicio IS NULL OR TRIM(m.disposicio) = '')")
    elif filter_group == "trazado_si":
        where_clauses.append("(m.disposicio IS NOT NULL AND TRIM(m.disposicio) != '' AND UPPER(TRIM(m.trazado)) = 'SI')")
    elif filter_group == "trazado_no":
        where_clauses.append("(m.disposicio IS NOT NULL AND TRIM(m.disposicio) != '' AND UPPER(TRIM(m.trazado)) = 'NO')")
    elif filter_group == "con_lfi_o_lib":
        where_clauses.append("(m.disposicio IS NOT NULL AND TRIM(m.disposicio) != '' AND UPPER(TRIM(m.trazado)) = 'SI' AND (COALESCE(l.cant_lfi, 0) > 0 OR COALESCE(b.cant_lib, 0) > 0))")
    elif filter_group == "ambas":
        where_clauses.append("(m.disposicio IS NOT NULL AND TRIM(m.disposicio) != '' AND UPPER(TRIM(m.trazado)) = 'SI' AND COALESCE(l.cant_lfi, 0) > 0 AND COALESCE(b.cant_lib, 0) > 0)")
    elif filter_group == "solo_lfi":
        where_clauses.append("(m.disposicio IS NOT NULL AND TRIM(m.disposicio) != '' AND UPPER(TRIM(m.trazado)) = 'SI' AND COALESCE(l.cant_lfi, 0) > 0 AND COALESCE(b.cant_lib, 0) = 0)")
    elif filter_group == "solo_lib":
        where_clauses.append("(m.disposicio IS NOT NULL AND TRIM(m.disposicio) != '' AND UPPER(TRIM(m.trazado)) = 'SI' AND COALESCE(l.cant_lfi, 0) = 0 AND COALESCE(b.cant_lib, 0) > 0)")
    elif filter_group == "ninguna":
        where_clauses.append("(m.disposicio IS NOT NULL AND TRIM(m.disposicio) != '' AND UPPER(TRIM(m.trazado)) = 'SI' AND COALESCE(l.cant_lfi, 0) = 0 AND COALESCE(b.cant_lib, 0) = 0)")

    if clean_search:
        params["search"] = clean_search
        where_clauses.append("(m.sm ILIKE :search OR m.seccion ILIKE :search OR m.manzana ILIKE :search OR m.disposicio ILIKE :search)")

    where_sql = " AND ".join(where_clauses)

    query_count = f"""
        WITH lfi_agg AS (
            SELECT sm, COUNT(*) as cant_lfi FROM public.cur_lfi_particularizadas WHERE sm IS NOT NULL GROUP BY sm
        ),
        lib_agg AS (
            SELECT sm, COUNT(*) as cant_lib FROM public.cur_lib_particularizadas WHERE sm IS NOT NULL GROUP BY sm
        )
        SELECT COUNT(*)
        FROM public.cur_manzanasatipicas m
        LEFT JOIN lfi_agg l ON m.sm = l.sm
        LEFT JOIN lib_agg b ON m.sm = b.sm
        WHERE {where_sql}
    """

    query_rows = f"""
        WITH lfi_agg AS (
            SELECT sm, COUNT(*) as cant_lfi FROM public.cur_lfi_particularizadas WHERE sm IS NOT NULL GROUP BY sm
        ),
        lib_agg AS (
            SELECT sm, COUNT(*) as cant_lib FROM public.cur_lib_particularizadas WHERE sm IS NOT NULL GROUP BY sm
        )
        SELECT 
            m.sm,
            m.seccion,
            m.manzana,
            m.mz_tipo,
            m.disposicio,
            m.trazado,
            m.comuna,
            COALESCE(l.cant_lfi, 0) as cant_lfi,
            COALESCE(b.cant_lib, 0) as cant_lib,
            CASE 
                WHEN UPPER(TRIM(m.trazado)) != 'SI' OR m.disposicio IS NULL OR TRIM(m.disposicio) = '' THEN 'N/A'
                WHEN COALESCE(l.cant_lfi, 0) > 0 AND COALESCE(b.cant_lib, 0) > 0 THEN 'AMBAS'
                WHEN COALESCE(l.cant_lfi, 0) > 0 THEN 'SOLO_LFI'
                WHEN COALESCE(b.cant_lib, 0) > 0 THEN 'SOLO_LIB'
                ELSE 'NINGUNA'
            END as cobertura_particularizada
        FROM public.cur_manzanasatipicas m
        LEFT JOIN lfi_agg l ON m.sm = l.sm
        LEFT JOIN lib_agg b ON m.sm = b.sm
        WHERE {where_sql}
        ORDER BY m.seccion, m.manzana
        LIMIT :lim OFFSET :off
    """

    try:
        with pdi_engine.connect() as conn:
            total_filtered = conn.execute(text(query_count), params).scalar() or 0
            rows = conn.execute(text(query_rows), params).mappings().fetchall()
            return {
                "connected": True,
                "total": int(total_filtered),
                "limit": safe_limit,
                "offset": safe_offset,
                "filter_group": filter_group,
                "records": [dict(r) for r in rows]
            }
    except Exception as e:
        logger.error(f"Error listando manzanas atípicas PDI: {e}")
        return {
            "connected": False,
            "error": VPN_ERROR_MESSAGE,
            "detail": str(e),
            "total": 0,
            "records": []
        }




