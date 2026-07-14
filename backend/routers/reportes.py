import logging
import pandas as pd
import traceback
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from collections import defaultdict

# Import configs, database, auth and cache utilities
from config import TRAMITES_CONFIG
from database import engine
from schemas import User
from auth_utils import get_current_user, get_current_user_from_param_or_header
from cache_utils import cached_response, set_cache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Reports & Analytics"])


def calculate_trata_expected_egresos(conn, gerencia_clean: str, trata: Optional[str] = None) -> int:
    try:
        interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"
        trata_filter = "TRUE"
        egr_trata_filter = "TRUE"
        if trata:
            trata_clean = trata.strip()
            if trata_clean == 'INTERVENCIONES':
                trata_filter = f"TRIM(trata) NOT IN (SELECT TRIM(unnest(tratas_incluidas)) FROM cfg_gestion_metas WHERE gerencia = '{gerencia_clean}')"
                egr_trata_filter = "TRIM(trata) = 'INTERVENCIONES'"
            else:
                trata_filter = f"TRIM(trata) = '{trata_clean}'"
                egr_trata_filter = f"TRIM(trata) = '{trata_clean}'"

        # Generate last 6 complete months in python
        now = datetime.now()
        curr_y, curr_m = now.year, now.month
        curr_m -= 1
        if curr_m == 0:
            curr_m = 12
            curr_y -= 1
            
        complete_months = []
        for _ in range(6):
            complete_months.append(f"{curr_y}-{str(curr_m).zfill(2)}")
            curr_m -= 1
            if curr_m == 0:
                curr_m = 12
                curr_y -= 1

        sql_hist = f"""
            WITH periodos(mes_label) AS (
                SELECT * FROM (VALUES {", ".join([f"('{m}')" for m in complete_months])}) as t(m)
            ),
            egr AS (
                SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                FROM (
                    SELECT fecha_egreso, trata FROM mv_{gerencia_clean}_gedos_egreso
                    UNION ALL
                    SELECT fecha_egreso, 'INTERVENCIONES' as trata FROM {interv_egr_table}
                ) t_egr
                WHERE {egr_trata_filter}
                GROUP BY 1
            ),
            egr_ne AS (
                SELECT to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_label, COUNT(*) as cant
                FROM mv_{gerencia_clean}_egresos_no_efectivos
                WHERE {trata_filter}
                GROUP BY 1
            )
            SELECT 
                p.mes_label,
                COALESCE(e.cant, 0) + COALESCE(ne.cant, 0) as egresos_totales
            FROM periodos p
            LEFT JOIN egr e ON e.mes_label = p.mes_label
            LEFT JOIN egr_ne ne ON ne.mes_label = p.mes_label
            ORDER BY p.mes_label ASC
        """
        result = conn.execute(text(sql_hist))
        hist_data = [dict(row._mapping) for row in result]
        if not hist_data:
            return 0
        sorted_vals = sorted([float(d['egresos_totales']) for d in hist_data])
        n = len(sorted_vals)
        mid = n // 2
        if n % 2 == 1:
            val = sorted_vals[mid]
        else:
            val = (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
        return round(val)
    except Exception as e:
        logger.error(f"Error calculate_trata_expected_egresos: {e}")
        return 0


def calculate_all_trata_expected_egresos_batch(conn, gerencia_clean: str, trata_codes: list) -> dict:
    """Versión batch: 1 sola query para todas las tratas en vez de N queries separadas."""
    try:
        interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"

        now = datetime.now()
        curr_y, curr_m = now.year, now.month
        curr_m -= 1
        if curr_m == 0:
            curr_m = 12
            curr_y -= 1
        complete_months = []
        for _ in range(6):
            complete_months.append(f"{curr_y}-{str(curr_m).zfill(2)}")
            curr_m -= 1
            if curr_m == 0:
                curr_m = 12
                curr_y -= 1

        sql = f"""
            WITH periodos(mes_label) AS (
                SELECT * FROM (VALUES {", ".join([f"('{m}')" for m in complete_months])}) as t(m)
            ),
            egr AS (
                SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, TRIM(trata) as trata, COUNT(*) as cant
                FROM mv_{gerencia_clean}_gedos_egreso
                GROUP BY 1, 2
            ),
            egr_interv AS (
                SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, 'INTERVENCIONES' as trata, COUNT(*) as cant
                FROM {interv_egr_table}
                GROUP BY 1
            ),
            egr_ne AS (
                SELECT to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_label, TRIM(trata) as trata, COUNT(*) as cant
                FROM mv_{gerencia_clean}_egresos_no_efectivos
                GROUP BY 1, 2
            ),
            all_egr AS (
                SELECT mes_label, trata, cant FROM egr
                UNION ALL
                SELECT mes_label, trata, cant FROM egr_interv
                UNION ALL
                SELECT mes_label, trata, cant FROM egr_ne
            )
            SELECT p.mes_label, ae.trata, COALESCE(SUM(ae.cant), 0) as total
            FROM periodos p
            LEFT JOIN all_egr ae ON ae.mes_label = p.mes_label
            GROUP BY p.mes_label, ae.trata
        """
        result = conn.execute(text(sql))

        trata_months: dict = defaultdict(lambda: defaultdict(int))
        for row in result:
            r = row._mapping
            t = str(r["trata"] or "").strip().upper()
            trata_months[t][r["mes_label"]] += int(r["total"] or 0)

        targets = {}
        for t_code in trata_codes:
            t_upper = t_code.strip().upper()
            vals = sorted(float(trata_months[t_upper].get(m, 0)) for m in complete_months)
            n = len(vals)
            if n == 0:
                targets[t_upper] = 0
            else:
                mid = n // 2
                targets[t_upper] = round(vals[mid] if n % 2 == 1 else (vals[mid - 1] + vals[mid]) / 2.0)
        return targets
    except Exception as e:
        logger.error(f"Error calculate_all_trata_expected_egresos_batch: {e}")
        return {t.strip().upper(): 0 for t in trata_codes}


# --- Endpoints de Reportes ---

def get_analyst_consolidado_data(analysts: List[str], cache_key: str) -> List[Dict[str, Any]]:
    hit, cached_val = cached_response(cache_key, ttl_seconds=120)
    if hit:
        return cached_val

    now = datetime.now()
    months_list = []
    curr_y, curr_m = now.year, now.month
    for _ in range(5):
        months_list.append(f"{curr_y}-{str(curr_m).zfill(2)}")
        curr_m -= 1
        if curr_m == 0:
            curr_m = 12
            curr_y -= 1

    grid = {}
    for analyst in analysts:
        for m_label in months_list:
            parts = m_label.split('-')
            grid[(analyst, m_label)] = {
                "COD TRATA": analyst,
                "DETALLE TRATA": analyst,
                "mes_label": m_label,
                "anio": int(parts[0]),
                "mes": int(parts[1]),
                "ING": 0,
                "EGR_EF": 0,
                "EGR_NE": 0,
                "STOCK_PROPIO": 0,
                "STOCK_SUBS": 0,
                "acronimos": "",
                "meta_egr_prom": 0
            }

    try:
        with engine.connect() as conn:
            sql_ing = """
                WITH primer_ingreso AS (
                    SELECT id_expediente, destinatario, min(fecha) as min_fecha
                    FROM mvw_ee_pases_secgdu
                    WHERE destinatario = ANY(:targets)
                    GROUP BY id_expediente, destinatario
                )
                SELECT 
                    destinatario AS analyst,
                    to_char(min_fecha, 'YYYY-MM') AS mes_label,
                    COUNT(*) as cant
                FROM primer_ingreso
                GROUP BY 1, 2
            """
            res_ing = conn.execute(text(sql_ing), {"targets": analysts}).fetchall()
            for r in res_ing:
                k = (r[0], r[1])
                if k in grid:
                    grid[k]["ING"] = r[2]

            sql_egr = """
                SELECT 
                    usuario AS analyst,
                    to_char(fecha, 'YYYY-MM') AS mes_label,
                    COUNT(DISTINCT id_expediente) as cant
                FROM mvw_ee_pases_secgdu
                WHERE usuario = ANY(:targets) AND NOT (destinatario = ANY(:targets))
                GROUP BY 1, 2
            """
            res_egr = conn.execute(text(sql_egr), {"targets": analysts}).fetchall()
            for r in res_egr:
                k = (r[0], r[1])
                if k in grid:
                    grid[k]["EGR_NE"] = r[2]

            sql_stock_hist = """
                WITH fechas_corte AS (
                    SELECT (date_trunc('month', mes.mes) + '1 mon -1 days'::interval)::date AS fecha_corte
                    FROM generate_series(
                        date_trunc('month', CURRENT_DATE) - '5 mons'::interval,
                        date_trunc('month', CURRENT_DATE),
                        '1 mon'::interval
                    ) mes(mes)
                ),
                destinatario_por_corte AS (
                    SELECT DISTINCT ON (p.id_expediente, fc.fecha_corte)
                        p.id_expediente,
                        fc.fecha_corte,
                        p.destinatario AS destinatario_cierre
                    FROM fechas_corte fc
                    JOIN mvw_ee_pases_secgdu p ON p.fecha::date <= fc.fecha_corte
                    WHERE p.id_expediente IN (
                        SELECT DISTINCT id_expediente FROM mvw_ee_pases_secgdu WHERE destinatario = ANY(:targets)
                    )
                    ORDER BY p.id_expediente, fc.fecha_corte, p.fecha DESC
                ),
                subsanacion_abierta_al_cierre AS (
                    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
                        dpc.id_expediente,
                        dpc.fecha_corte,
                        true AS tiene_subsanacion_abierta
                    FROM destinatario_por_corte dpc
                    JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = dpc.id_expediente 
                        AND a.usuario_alta = dpc.destinatario_cierre 
                        AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD' 
                        AND a.fecha_alta::date <= dpc.fecha_corte 
                        AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
                    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
                )
                SELECT 
                    to_char(dpc.fecha_corte, 'YYYY-MM') AS mes_label,
                    dpc.destinatario_cierre AS analyst,
                    SUM(CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, false) THEN 0 ELSE 1 END) AS stock_propio,
                    SUM(CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, false) THEN 1 ELSE 0 END) AS stock_subs
                FROM destinatario_por_corte dpc
                LEFT JOIN subsanacion_abierta_al_cierre sac ON sac.id_expediente = dpc.id_expediente AND sac.fecha_corte = dpc.fecha_corte
                WHERE dpc.destinatario_cierre = ANY(:targets)
                GROUP BY 1, 2
            """
            res_stock = conn.execute(text(sql_stock_hist), {"targets": analysts}).fetchall()
            for r in res_stock:
                k = (r[1], r[0])
                if k in grid:
                    grid[k]["STOCK_PROPIO"] = int(r[2] or 0)
                    grid[k]["STOCK_SUBS"] = int(r[3] or 0)

            curr_mes_label = now.strftime('%Y-%m')
            
            sql_stock_live = """
                SELECT 
                    up.destinatario_actual AS analyst,
                    COUNT(*) AS cant
                FROM mv_ultimo_pase up
                WHERE up.destinatario_actual = ANY(:targets)
                  AND NOT EXISTS (
                      SELECT 1 FROM mvw_ee_actividades_secgdu a
                      WHERE a.id_expediente = up.id_expediente
                        AND a.usuario_alta = up.destinatario_actual
                        AND a.estado = 'PENDIENTE'
                        AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                  )
                GROUP BY 1
            """
            res_stock_live = conn.execute(text(sql_stock_live), {"targets": analysts}).fetchall()
            for r in res_stock_live:
                k = (r[0], curr_mes_label)
                if k in grid:
                    grid[k]["STOCK_PROPIO"] = r[1]

            sql_subs_live = """
                SELECT 
                    up.destinatario_actual AS analyst,
                    COUNT(*) AS cant
                FROM mv_ultimo_pase up
                JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = up.id_expediente AND a.usuario_alta = up.destinatario_actual
                WHERE up.destinatario_actual = ANY(:targets)
                  AND a.estado = 'PENDIENTE'
                  AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                GROUP BY 1
            """
            res_subs_live = conn.execute(text(sql_subs_live), {"targets": analysts}).fetchall()
            for r in res_subs_live:
                k = (r[0], curr_mes_label)
                if k in grid:
                    grid[k]["STOCK_SUBS"] = r[1]

    except Exception as e:
        logger.error(f"Error querying analyst consolidado data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    result = []
    for analyst in analysts:
        for m_label in months_list:
            result.append(grid[(analyst, m_label)])

    set_cache(cache_key, result)
    return result

@router.get("/api/reporte/publico_privado/consolidado")
def get_publico_privado_consolidado(current_user: User = Depends(get_current_user)):
    analysts = ["NDEFAVERI", "NARGANDONAJULIO", "DGIUR-GERENCIAPPP"]
    return get_analyst_consolidado_data(analysts, "consolidado_publico_privado")

@router.get("/api/reporte/copua/consolidado")
def get_copua_consolidado(current_user: User = Depends(get_current_user)):
    analysts = ["CAPUAM-02"]
    return get_analyst_consolidado_data(analysts, "consolidado_copua")

@router.get("/api/reporte/publico_privado/config/all")
def get_publico_privado_config(current_user: User = Depends(get_current_user)):
    analysts = ["NDEFAVERI", "NARGANDONAJULIO", "DGIUR-GERENCIAPPP"]
    return {a: {"buzones_ingreso": [], "analistas_oficiales": [], "acronimos_egreso": [], "buzones_ingreso_intervenciones": []} for a in analysts}

@router.get("/api/reporte/copua/config/all")
def get_copua_config(current_user: User = Depends(get_current_user)):
    analysts = ["CAPUAM-02"]
    return {a: {"buzones_ingreso": [], "analistas_oficiales": [], "acronimos_egreso": [], "buzones_ingreso_intervenciones": []} for a in analysts}

@router.get("/api/reporte/{gerencia}/config/all")
async def get_gerencia_config(gerencia: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT trata_reporte, buzones_ingreso, analistas_oficiales, acronimos_egreso, buzones_ingreso_intervenciones
                FROM cfg_gestion_metas
                WHERE gerencia = :g
            """)
            result = conn.execute(query, {"g": gerencia_clean})
            config_data = {}
            for r in result.fetchall():
                config_data[r[0]] = {
                    "buzones_ingreso": r[1] or [],
                    "analistas_oficiales": r[2] or [],
                    "acronimos_egreso": r[3] or [],
                    "buzones_ingreso_intervenciones": r[4] or []
                }
            return config_data
    except Exception as e:
        logger.error(f"Error fetching gerencia config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/{gerencia}/consolidado")
def get_reporte_consolidado_gerencia(gerencia: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'

    _ck = f"consolidado_{gerencia_clean}"
    hit, data = cached_response(_ck, ttl_seconds=120)
    if hit:
        return data
        
    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
    
    trata_codes = list(TRAMITES_CONFIG[gerencia_clean].keys())
    
    # Obtener el último cuatrimestre completo + mes actual (5 meses total)
    now = datetime.now()
    months_list = []
    curr_y, curr_m = now.year, now.month
    
    for i in range(5):
        months_list.append(f"({curr_y}, {curr_m})")
        curr_m -= 1
        if curr_m == 0:
            curr_m = 12
            curr_y -= 1
            
    months_filter = ", ".join(months_list)
    
    try:
        with engine.connect() as conn:
            if gerencia_clean in ['instalaciones', 'morfologia', 'contable', 'etapa_proyecto', 'catastro', 'aph', 'usos', 'regularizacion', 'aviso_obra']:
                modular_months = []
                m_y, m_m = now.year, now.month
                for _ in range(5):
                    modular_months.append(f"'{m_y}-{str(m_m).zfill(2)}'")
                    m_m -= 1
                    if m_m == 0: m_m = 12; m_y -= 1

                interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"

                sql = f"""
                    WITH periodos(mes_label) AS (
                        SELECT * FROM (VALUES {", ".join([f"({m})" for m in modular_months])}) as t(m)
                    ),
                    ing AS (
                        SELECT to_char(fecha_ingreso, 'YYYY-MM') as mes_label, 
                               CASE WHEN trata = ANY(:tratas_oficiales) THEN trata ELSE 'INTERVENCIONES' END as trata, 
                               COUNT(*) as cant
                        FROM mv_{gerencia_clean}_ingresos_eventos
                        GROUP BY 1, 2
                    ),
                    egr_ef AS (
                        SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, trata, COUNT(*) as cant
                        FROM mv_{gerencia_clean}_gedos_egreso
                        GROUP BY 1, 2
                        UNION ALL
                        SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, 'INTERVENCIONES' as trata, COUNT(*) as cant
                        FROM {interv_egr_table}
                        GROUP BY 1, 2
                    ),
                    egr_ne AS (
                        SELECT to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_label, 
                               CASE WHEN trata = ANY(:tratas_oficiales) THEN trata ELSE 'INTERVENCIONES' END as trata, 
                               COUNT(*) as cant
                        FROM mv_{gerencia_clean}_egresos_no_efectivos
                        GROUP BY 1, 2
                    ),
                    stock_data AS (
                        SELECT mes_label, 
                               CASE WHEN trata = ANY(:tratas_oficiales) THEN trata ELSE 'INTERVENCIONES' END as trata,
                               SUM(CASE WHEN categoria = 'STOCK_PROPIO' THEN cant_expedientes ELSE 0 END) as stock_propio,
                               SUM(CASE WHEN categoria = 'SUBSANACION' THEN cant_expedientes ELSE 0 END) as stock_subs
                        FROM mv_{gerencia_clean}_stock_historico
                        GROUP BY 1, 2
                    ),
                    config_order AS (
                        SELECT * FROM (VALUES {", ".join([f"('{c}', {i})" for i, c in enumerate(trata_codes)])}) as t(trata_code, ord)
                    ),
                    current_stock AS (
                        SELECT trata, COUNT(*) as cant FROM mv_{gerencia_clean}_stock_propio GROUP BY 1
                        UNION ALL
                        SELECT 'INTERVENCIONES' as trata, COUNT(*) as cant FROM mv_{gerencia_clean}_intervenciones_stock GROUP BY 1
                    ),
                    current_subs AS (
                        SELECT trata, COUNT(*) as cant FROM mv_{gerencia_clean}_subsanaciones GROUP BY 1
                        UNION ALL
                        SELECT 'INTERVENCIONES' as trata, COUNT(*) as cant FROM mv_{gerencia_clean}_intervenciones_subs GROUP BY 1
                    )
                    SELECT 
                        et.trata as "COD TRATA", 
                        et.descripcion_trata as "DETALLE TRATA",
                        p.mes_label,
                        to_number(split_part(p.mes_label, '-', 1), '9999') as anio,
                        to_number(split_part(p.mes_label, '-', 2), '99') as mes,
                        COALESCE(i.cant, 0) as "ING",
                        COALESCE(ef.cant, 0) as "EGR_EF",
                        COALESCE(ne.cant, 0) as "EGR_NE",
                        CASE 
                            WHEN p.mes_label = to_char(now(), 'YYYY-MM')
                            THEN COALESCE(MAX(cs.cant), 0) 
                            ELSE COALESCE(SUM(s.stock_propio), 0) 
                        END as "STOCK_PROPIO",
                        CASE 
                            WHEN p.mes_label = to_char(now(), 'YYYY-MM')
                            THEN COALESCE(MAX(csub.cant), 0) 
                            ELSE COALESCE(SUM(s.stock_subs), 0) 
                        END as "STOCK_SUBS"
                    FROM periodos p
                    CROSS JOIN (
                        SELECT v.trata_code as trata,
                               COALESCE(
                                   (SELECT descripcion_trata FROM cfg_gestion_metas WHERE trata_reporte = v.trata_code AND gerencia = :g LIMIT 1),
                                   (SELECT descripcion_trata FROM cfg_gestion_metas WHERE v.trata_code = ANY(tratas_incluidas) AND gerencia = :g LIMIT 1),
                                   v.trata_code
                               ) as descripcion_trata
                        FROM (VALUES {", ".join([f"('{c}')" for c in trata_codes if c != 'INTERVENCIONES'])}) as v(trata_code)
                        UNION ALL
                        SELECT 'INTERVENCIONES', 'Intervenciones'
                    ) et
                    JOIN config_order o ON et.trata = o.trata_code
                    LEFT JOIN ing i ON i.mes_label = p.mes_label AND i.trata = et.trata
                    LEFT JOIN egr_ef ef ON ef.mes_label = p.mes_label AND ef.trata = et.trata
                    LEFT JOIN egr_ne ne ON ne.mes_label = p.mes_label AND ne.trata = et.trata
                    LEFT JOIN stock_data s ON s.mes_label = p.mes_label AND s.trata = et.trata
                    LEFT JOIN current_stock cs ON cs.trata = et.trata
                    LEFT JOIN current_subs csub ON csub.trata = et.trata
                    GROUP BY p.mes_label, 1, 2, 3, 4, o.ord, i.cant, ef.cant, ne.cant
                    ORDER BY o.ord, anio DESC, mes DESC
                """
                params = {"tratas_oficiales": [t for t in trata_codes if t != 'INTERVENCIONES'], "g": gerencia_clean}
            else:
                sql = f"""
                    WITH config_order AS (
                        SELECT * FROM (VALUES {", ".join([f"('{c}', {i})" for i, c in enumerate(trata_codes)])}) as t(trata_code, ord)
                    )
                    SELECT h.* FROM mvw_reporte_historico_{gerencia_clean} h
                    JOIN config_order o ON h."COD TRATA" = o.trata_code
                    WHERE (h.anio, h.mes) IN ({months_filter})
                    ORDER BY o.ord, h.anio DESC, h.mes DESC
                """
                params = {}

            result = conn.execute(text(sql), params)
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            expected_targets = {}
            try:
                mes_cal = '2026-07-01'
                month_res = conn.execute(text(f"SELECT mes_calendario FROM mv_plan_metas_{gerencia_clean} ORDER BY abs(extract(epoch from (mes_calendario::timestamp - CURRENT_TIMESTAMP))) ASC LIMIT 1")).fetchone()
                if month_res:
                    mes_cal = month_res[0]

                metas_query = f"SELECT TRIM(trata) as trata, egresos_totales_plan as nueva_meta_produccion FROM mv_plan_metas_{gerencia_clean} WHERE mes_calendario = :mes"
                res_metas = conn.execute(text(metas_query), {"mes": mes_cal})
                for row in res_metas:
                    r_dict = row._mapping
                    if r_dict["trata"]:
                        expected_targets[str(r_dict["trata"]).strip().upper()] = round(r_dict["nueva_meta_produccion"] or 0)
            except Exception as e:
                logger.warning(f"No se pudo consultar mv_metas_dinamicas_{gerencia_clean}, usando fallback: {e}")
                expected_targets = calculate_all_trata_expected_egresos_batch(conn, gerencia_clean, trata_codes + ['INTERVENCIONES'])

            if "INTERVENCIONES" not in expected_targets:
                expected_targets["INTERVENCIONES"] = round(calculate_trata_expected_egresos(conn, gerencia_clean, 'INTERVENCIONES'))

            config_for_g = TRAMITES_CONFIG.get(gerencia_clean, {})
            df["acronimos"] = df["COD TRATA"].apply(lambda x: config_for_g.get(x, {}).get("acronimos", ""))
            df["meta_egr_prom"] = df["COD TRATA"].apply(lambda x: expected_targets.get(str(x).strip().upper(), 0))
            
            result = df.to_dict(orient='records')
            set_cache(_ck, result)
            return result
    except Exception as e:
        logger.error(f"Error en consolidado: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/api/reporte/{gerencia}/metas")
async def get_metas_proyeccion(gerencia: str, trata: Optional[str] = None, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
    try:
        with engine.connect() as conn:
            interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos"
            
            trata_filter = "TRUE"
            egr_trata_filter = "TRUE"
            if trata:
                trata_clean = trata.strip()
                if trata_clean == 'INTERVENCIONES':
                    trata_filter = f"TRIM(trata) NOT IN (SELECT TRIM(unnest(tratas_incluidas)) FROM cfg_gestion_metas WHERE gerencia = '{gerencia_clean}')"
                    egr_trata_filter = "TRIM(trata) = 'INTERVENCIONES'"
                else:
                    trata_filter = f"TRIM(trata) = '{trata_clean}'"
                    egr_trata_filter = f"TRIM(trata) = '{trata_clean}'"

            sql_hist = f"""
                WITH ing AS (
                    SELECT to_char(fecha_ingreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                    FROM mv_{gerencia_clean}_ingresos_eventos
                    WHERE {trata_filter}
                    GROUP BY 1
                ),
                egr AS (
                    SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                    FROM (
                        SELECT fecha_egreso, trata FROM mv_{gerencia_clean}_gedos_egreso
                        UNION ALL
                        SELECT fecha_egreso, 'INTERVENCIONES' as trata FROM {interv_egr_table}
                    ) t_egr
                    WHERE {egr_trata_filter}
                    GROUP BY 1
                ),
                egr_ne AS (
                    SELECT to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_label, COUNT(*) as cant
                    FROM mv_{gerencia_clean}_egresos_no_efectivos
                    WHERE {trata_filter}
                    GROUP BY 1
                ),
                stock AS (
                    SELECT mes_label, 
                           SUM(CASE WHEN categoria = 'STOCK_PROPIO' THEN cant_expedientes ELSE 0 END) as stock_sector, 
                           SUM(CASE WHEN categoria = 'SUBSANACION' THEN cant_expedientes ELSE 0 END) as stock_corriente
                    FROM mv_{gerencia_clean}_stock_historico
                    WHERE {trata_filter}
                    GROUP BY 1
                )
                SELECT 
                    s.mes_label,
                    COALESCE(i.cant, 0) as ingresos,
                    COALESCE(e.cant, 0) + COALESCE(ne.cant, 0) as egresos_totales,
                    COALESCE(s.stock_sector, 0) as stock_sector,
                    COALESCE(s.stock_corriente, 0) as stock_corriente,
                    FALSE as es_proyeccion
                FROM stock s
                LEFT JOIN ing i ON i.mes_label = s.mes_label
                LEFT JOIN egr e ON e.mes_label = s.mes_label
                LEFT JOIN egr_ne ne ON ne.mes_label = s.mes_label
                ORDER BY s.mes_label ASC
            """
            
            result = conn.execute(text(sql_hist))
            hist_data = [dict(row._mapping) for row in result]
            
            if not hist_data:
                return {"history": [], "projection": [], "metas": {}}

            current_month_str = datetime.now().strftime('%Y-%m')
            complete_months = [d for d in hist_data if d['mes_label'] < current_month_str]
            recent = complete_months[-6:] if len(complete_months) >= 6 else complete_months
            
            def calculate_median(values):
                if not values:
                    return 0
                sorted_vals = sorted(values)
                n = len(sorted_vals)
                mid = n // 2
                if n % 2 == 1:
                    return sorted_vals[mid]
                else:
                    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0

            avg_ing = calculate_median([float(d['ingresos']) for d in recent])
            avg_egr = calculate_median([float(d['egresos_totales']) for d in recent])
            current_sector = float(hist_data[-1]['stock_sector'])
            current_corriente = float(hist_data[-1]['stock_corriente'])
            
            duracion_dias = 90.0
            if trata and trata != 'INTERVENCIONES':
                try:
                    dur_res = conn.execute(text(f"SELECT COALESCE(duracion_total_mediana, 90) FROM mv_tiempos_resolucion_{gerencia_clean} WHERE trata = :t LIMIT 1"), {"t": trata}).fetchone()
                    if dur_res:
                        duracion_dias = float(dur_res[0])
                except Exception as dur_err:
                    logger.warning(f"Error obteniendo duracion de resolucion: {dur_err}")
            
            healthy_corriente_target = avg_ing * (duracion_dias / 30.0)
            excess_corriente = max(0.0, current_corriente - healthy_corriente_target)
            
            meta_maint = avg_ing
            meta_clean_required = (current_sector / 6.0) + (excess_corriente / 3.0)
            
            db_expected_target = None
            db_ingresos_promedio = None
            try:
                mes_cal = '2026-07-01'
                month_res = conn.execute(text(f"SELECT mes_calendario FROM mv_plan_metas_{gerencia_clean} ORDER BY abs(extract(epoch from (mes_calendario::timestamp - CURRENT_TIMESTAMP))) ASC LIMIT 1")).fetchone()
                if month_res:
                    mes_cal = month_res[0]

                if trata and trata != 'INTERVENCIONES':
                    meta_res = conn.execute(text(f"SELECT COALESCE(egresos_totales_plan, 0), COALESCE(ingresos_promedio, 0) FROM mv_plan_metas_{gerencia_clean} WHERE TRIM(UPPER(trata)) = :t AND mes_calendario = :mes LIMIT 1"), {"t": trata.strip().upper(), "mes": mes_cal}).fetchone()
                    if meta_res:
                        db_expected_target = float(meta_res[0])
                        db_ingresos_promedio = float(meta_res[1])
                elif trata == 'INTERVENCIONES':
                    meta_res = conn.execute(text(f"SELECT COALESCE(egresos_totales_plan, 0), COALESCE(ingresos_promedio, 0) FROM mv_plan_metas_{gerencia_clean} WHERE TRIM(UPPER(trata)) = 'INTERVENCIONES' AND mes_calendario = :mes LIMIT 1"), {"mes": mes_cal}).fetchone()
                    if meta_res:
                        db_expected_target = float(meta_res[0])
                        db_ingresos_promedio = float(meta_res[1])
                    else:
                        db_expected_target = float(calculate_trata_expected_egresos(conn, gerencia_clean, 'INTERVENCIONES'))
                        db_ingresos_promedio = avg_ing
                else:
                    sum_res = conn.execute(text(f"SELECT SUM(COALESCE(egresos_totales_plan, 0)), SUM(COALESCE(ingresos_promedio, 0)) FROM mv_plan_metas_{gerencia_clean} WHERE mes_calendario = :mes"), {"mes": mes_cal}).fetchone()
                    if sum_res and sum_res[0] is not None:
                        db_expected_target = float(sum_res[0])
                        db_ingresos_promedio = float(sum_res[1])
                    
                    has_int = conn.execute(text(f"SELECT COUNT(*) FROM mv_plan_metas_{gerencia_clean} WHERE TRIM(UPPER(trata)) = 'INTERVENCIONES' AND mes_calendario = :mes"), {"mes": mes_cal}).scalar() or 0
                    if not has_int:
                        int_fallback = float(calculate_trata_expected_egresos(conn, gerencia_clean, 'INTERVENCIONES'))
                        db_expected_target = (db_expected_target or 0.0) + int_fallback
                        db_ingresos_promedio = (db_ingresos_promedio or 0.0) + avg_ing
            except Exception as meta_err:
                logger.warning(f"Error obteniendo egresos/ingresos de mv_plan_metas_{gerencia_clean}: {meta_err}")

            if db_ingresos_promedio is not None:
                avg_ing = db_ingresos_promedio
                meta_maint = avg_ing

            if db_expected_target is not None:
                meta_total_target = db_expected_target
            else:
                meta_total_target = max(meta_maint / 0.75, meta_clean_required / 0.25)
            
            meta_maint_allocated = meta_total_target * 0.75
            meta_clean_allocated = meta_total_target * 0.25
            
            projection_current = []
            projection_target = []
            
            if complete_months:
                projection_start_record = complete_months[-1]
            else:
                projection_start_record = hist_data[-1]

            proj_sector_start = float(projection_start_record['stock_sector'])
            proj_corriente_start = float(projection_start_record['stock_corriente'])

            try:
                last_date = datetime.strptime(projection_start_record['mes_label'], '%Y-%m')
            except:
                last_date = datetime.now()

            temp_sector_current = proj_sector_start
            temp_corriente_target = proj_corriente_start
            temp_sector_target = proj_sector_start
            
            for i in range(1, 8):
                next_month = last_date + timedelta(days=31*i)
                mes_label = next_month.strftime('%Y-%m')
                
                delta_current = avg_ing - avg_egr
                temp_sector_current = max(0, temp_sector_current + delta_current)
                projection_current.append({
                    "mes_label": mes_label,
                    "ingresos": round(avg_ing),
                    "egresos_totales": round(avg_egr),
                    "stock_sector": round(temp_sector_current),
                    "stock_corriente": round(proj_corriente_start),
                    "es_proyeccion": True,
                    "escenario": "actual"
                })
                
                monthly_target = meta_total_target
                
                if temp_sector_target > 0:
                    backlog_cleared = proj_sector_start / 6.0
                    temp_sector_target = max(0.0, temp_sector_target - backlog_cleared)
                else:
                    backlog_cleared = 0.0
                    temp_sector_target = 0.0
                
                flow_capacity = max(0.0, monthly_target - backlog_cleared)
                
                if proj_sector_start > 0:
                    efficiency_gain = (proj_sector_start - temp_sector_target) / proj_sector_start
                else:
                    efficiency_gain = 1.0
                
                target_optimized_duration = max(30.0, duracion_dias * 0.6)
                effective_duration = duracion_dias - (duracion_dias - target_optimized_duration) * efficiency_gain
                
                dynamic_healthy_corriente = avg_ing * (effective_duration / 30.0)
                
                temp_corriente_target = max(dynamic_healthy_corriente, temp_corriente_target + avg_ing - flow_capacity)
                
                projection_target.append({
                    "mes_label": mes_label,
                    "ingresos": round(avg_ing),
                    "egresos_totales": round(monthly_target),
                    "stock_sector": round(temp_sector_target),
                    "stock_corriente": round(temp_corriente_target),
                    "es_proyeccion": True,
                    "escenario": "objetivo"
                })

            projection_target_db = []
            try:
                plan_trata_filter = f"TRIM(trata) = '{trata}'" if trata and trata != 'INTERVENCIONES' else "TRUE"
                plan_sql = f"""
                    SELECT nro_mes, to_char(mes_calendario, 'YYYY-MM') as mes_label,
                           SUM(COALESCE(ingresos_promedio, 0)) as ingresos,
                           SUM(COALESCE(egresos_totales_plan, 0)) as egresos_totales,
                           SUM(COALESCE(stock_sector_fin, 0)) as stock_sector,
                           SUM(COALESCE(stock_corriente, 0)) as stock_corriente
                    FROM mv_plan_metas_{gerencia_clean}
                    WHERE {plan_trata_filter} AND mes_calendario >= '2026-06-01'
                    GROUP BY 1, 2
                    ORDER BY 1 ASC
                """
                plan_res = conn.execute(text(plan_sql))
                for row in plan_res:
                    r_dict = row._mapping
                    projection_target_db.append({
                        "mes_label": r_dict["mes_label"],
                        "ingresos": round(float(r_dict["ingresos"])),
                        "egresos_totales": round(float(r_dict["egresos_totales"])),
                        "stock_sector": round(float(r_dict["stock_sector"])),
                        "stock_corriente": round(float(r_dict["stock_corriente"])),
                        "es_proyeccion": True,
                        "escenario": "objetivo"
                    })
            except Exception as plan_err:
                logger.warning(f"No se pudo consultar mv_plan_metas_{gerencia_clean}, usando fallback matemático: {plan_err}")

            if projection_target_db:
                projection_target = projection_target_db

            capacidad_limpieza_actual = avg_egr * 0.25
            meses_barrido_estimado = current_sector / capacidad_limpieza_actual if capacidad_limpieza_actual > 0 else 999

            return {
                "history": hist_data,
                "projection_current": projection_current,
                "projection_target": projection_target,
                "metas": {
                    "avg_ing": round(avg_ing),
                    "avg_egr_actual": round(avg_egr),
                    "meta_mantenimiento": round(meta_maint_allocated),
                    "meta_limpieza_objetivo": round(meta_clean_allocated),
                    "meta_total_recomendada": round(meta_total_target),
                    "meses_barrido_actual": round(meses_barrido_estimado),
                    "duracion_resolucion": round(duracion_dias)
                }
            }
    except Exception as e:
        logger.error(f"Error en metas proyección: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/familia")
async def get_reporte_familia(
    trata: List[str] = Query(...), 
    current_user: User = Depends(get_current_user)
):
    _ck = f"familia_{'_'.join(sorted(trata))}"
    hit, data = cached_response(_ck, ttl_seconds=300)
    if hit:
        return data
    try:
        trata_to_gerencia = {}
        for g, cfg in TRAMITES_CONFIG.items():
            for t in cfg.keys():
                if t != 'INTERVENCIONES':
                    trata_to_gerencia[t.upper()] = g.lower()

        trata_overrides = {
            "MDUG3001A": "etapa_proyecto",
            "MDUG0104A": "etapa_proyecto",
            "MDUG1501J": "etapa_proyecto",
            "MDUG0142A": "etapa_proyecto",
            "MDUG4003A": "etapa_proyecto"
        }

        aggregated_history = {}
        total_ingresos_promedio = 0
        total_egresos_totales_plan = 0

        with engine.connect() as conn:
            for t_code in trata:
                t_upper = t_code.strip().upper()
                gerencia_clean = trata_overrides.get(t_upper) or trata_to_gerencia.get(t_upper)
                if not gerencia_clean:
                    continue

                try:
                    meta_res = conn.execute(text(f"""
                        SELECT COALESCE(egresos_totales_plan, 0), COALESCE(ingresos_promedio, 0) 
                        FROM mv_plan_metas_{gerencia_clean} 
                        WHERE TRIM(UPPER(trata)) = :t AND mes_calendario = '2026-06-01' LIMIT 1
                    """), {"t": t_upper}).fetchone()
                    if meta_res:
                        total_egresos_totales_plan += float(meta_res[0])
                        total_ingresos_promedio += float(meta_res[1])
                except Exception as meta_err:
                    logger.warning(f"Error fetching plan metas for {t_upper} in {gerencia_clean}: {meta_err}")

                try:
                    sql_hist = f"""
                        WITH periodos AS (
                            SELECT DISTINCT mes_label FROM mv_{gerencia_clean}_stock_historico
                            ORDER BY mes_label DESC LIMIT 12
                        ),
                        ing AS (
                            SELECT to_char(fecha_ingreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                            FROM mv_{gerencia_clean}_ingresos_eventos WHERE TRIM(trata) = :t
                            GROUP BY 1
                        ),
                        egr_ef AS (
                            SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                            FROM mv_{gerencia_clean}_gedos_egreso WHERE TRIM(trata) = :t
                            GROUP BY 1
                        ),
                        egr_ne AS (
                            SELECT to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_label, COUNT(*) as cant
                            FROM mv_{gerencia_clean}_egresos_no_efectivos WHERE TRIM(trata) = :t
                            GROUP BY 1
                        ),
                        stock_data AS (
                            SELECT mes_label, 
                                   SUM(CASE WHEN categoria = 'STOCK_PROPIO' THEN cant_expedientes ELSE 0 END) as stock_propio,
                                   SUM(CASE WHEN categoria = 'SUBSANACION' THEN cant_expedientes ELSE 0 END) as stock_subs
                            FROM mv_{gerencia_clean}_stock_historico WHERE TRIM(trata) = :t
                            GROUP BY 1
                        )
                        SELECT 
                            p.mes_label,
                            COALESCE(i.cant, 0) as "ING",
                            COALESCE(ef.cant, 0) as "EGR_EF",
                            COALESCE(ne.cant, 0) as "EGR_NE",
                            COALESCE(s.stock_propio, 0) as "STOCK_PROPIO",
                            COALESCE(s.stock_subs, 0) as "STOCK_SUBS"
                        FROM periodos p
                        LEFT JOIN ing i ON i.mes_label = p.mes_label
                        LEFT JOIN egr_ef ef ON ef.mes_label = p.mes_label
                        LEFT JOIN egr_ne ne ON ne.mes_label = p.mes_label
                        LEFT JOIN stock_data s ON s.mes_label = p.mes_label
                        ORDER BY p.mes_label DESC
                    """
                    res_hist = conn.execute(text(sql_hist), {"t": t_upper})
                    for row in res_hist:
                        r_dict = row._mapping
                        mes_label = r_dict["mes_label"]
                        if mes_label not in aggregated_history:
                            aggregated_history[mes_label] = {
                                "mes_label": mes_label,
                                "ING": 0,
                                "EGR_EF": 0,
                                "EGR_NE": 0,
                                "STOCK_PROPIO": 0,
                                "STOCK_SUBS": 0
                            }
                        aggregated_history[mes_label]["ING"] += int(r_dict["ING"])
                        aggregated_history[mes_label]["EGR_EF"] += int(r_dict["EGR_EF"])
                        aggregated_history[mes_label]["EGR_NE"] += int(r_dict["EGR_NE"])
                        aggregated_history[mes_label]["STOCK_PROPIO"] += int(r_dict["STOCK_PROPIO"])
                        aggregated_history[mes_label]["STOCK_SUBS"] += int(r_dict["STOCK_SUBS"])
                except Exception as hist_err:
                    logger.warning(f"Error fetching history for {t_upper} in {gerencia_clean}: {hist_err}")

        history_list = sorted(list(aggregated_history.values()), key=lambda x: x["mes_label"])
        
        formatted_history = []
        for h in history_list:
            parts = h["mes_label"].split('-')
            formatted_history.append({
                "anio": int(parts[0]),
                "mes": int(parts[1]),
                "ING": h["ING"],
                "EGR_EF": h["EGR_EF"],
                "EGR_NE": h["EGR_NE"],
                "STOCK_PROPIO": h["STOCK_PROPIO"],
                "STOCK_SUBS": h["STOCK_SUBS"]
            })

        result = {
            "history": formatted_history,
            "metas": {
                "ingresos_esperados": round(total_ingresos_promedio),
                "egresos_totales_plan": round(total_egresos_totales_plan)
            }
        }
        set_cache(_ck, result)
        return result
    except Exception as e:
        logger.error(f"Error en reporte familia: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/familias_overview")
async def get_reporte_familias_overview(current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            db_rows = conn.execute(text("SELECT nombre, tratas FROM public.cfg_tramites_familias ORDER BY id")).fetchall()
            FAMILIAS_CONFIG = {r[0]: r[1] for r in db_rows}
    except Exception as db_err:
        logger.error(f"Error reading families config from DB: {db_err}")
        FAMILIAS_CONFIG = {}
    
    trata_to_gerencia = {}
    for g, cfg in TRAMITES_CONFIG.items():
        for t in cfg.keys():
            if t != 'INTERVENCIONES':
                trata_to_gerencia[t.upper()] = g.lower()

    trata_overrides = {
        "MDUG3001A": "etapa_proyecto",
        "MDUG0104A": "etapa_proyecto",
        "MDUG1501J": "etapa_proyecto",
        "MDUG0142A": "etapa_proyecto",
        "MDUG4003A": "etapa_proyecto"
    }

    results = []
    
    try:
        with engine.connect() as conn:
            for family_name, tratas in FAMILIAS_CONFIG.items():
                total_target = 0
                total_actual = 0
                total_prev = 0
                
                for t_code in tratas:
                    t_upper = t_code.strip().upper()
                    gerencia_clean = trata_overrides.get(t_upper) or trata_to_gerencia.get(t_upper)
                    if not gerencia_clean:
                        continue
                        
                    try:
                        meta_res = conn.execute(text(f"""
                            SELECT COALESCE(egresos_totales_plan, 0)
                            FROM mv_plan_metas_{gerencia_clean} 
                            WHERE TRIM(UPPER(trata)) = :t AND mes_calendario = '2026-06-01' LIMIT 1
                        """), {"t": t_upper}).fetchone()
                        if meta_res:
                            total_target += float(meta_res[0])
                    except Exception:
                        pass
                        
                    try:
                        sql_months = f"""
                            SELECT DISTINCT mes_label FROM mv_{gerencia_clean}_stock_historico
                            ORDER BY mes_label DESC LIMIT 2
                        """
                        months_rows = conn.execute(text(sql_months)).fetchall()
                        if len(months_rows) >= 1:
                            mes_val = months_rows[0][0]
                            egr_ef_res = conn.execute(text(f"""
                                SELECT COUNT(*) FROM mv_{gerencia_clean}_gedos_egreso 
                                WHERE TRIM(trata) = :t AND to_char(fecha_egreso, 'YYYY-MM') = :m
                            """), {"t": t_upper, "m": mes_val}).fetchone()
                            
                            egr_ne_res = conn.execute(text(f"""
                                SELECT COUNT(*) FROM mv_{gerencia_clean}_egresos_no_efectivos
                                WHERE TRIM(trata) = :t AND to_char(fecha_ultimo_movimiento, 'YYYY-MM') = :m
                            """), {"t": t_upper, "m": mes_val}).fetchone()
                            
                            if egr_ef_res:
                                total_actual += int(egr_ef_res[0])
                            if egr_ne_res:
                                total_actual += int(egr_ne_res[0])
                                
                        if len(months_rows) >= 2:
                            mes_prev = months_rows[1][0]
                            egr_ef_prev = conn.execute(text(f"""
                                SELECT COUNT(*) FROM mv_{gerencia_clean}_gedos_egreso 
                                WHERE TRIM(trata) = :t AND to_char(fecha_egreso, 'YYYY-MM') = :m
                            """), {"t": t_upper, "m": mes_prev}).fetchone()
                            
                            egr_ne_prev = conn.execute(text(f"""
                                SELECT COUNT(*) FROM mv_{gerencia_clean}_egresos_no_efectivos
                                WHERE TRIM(trata) = :t AND to_char(fecha_ultimo_movimiento, 'YYYY-MM') = :m
                            """), {"t": t_upper, "m": mes_prev}).fetchone()
                            
                            if egr_ef_prev:
                                total_prev += int(egr_ef_prev[0])
                            if egr_ne_prev:
                                total_prev += int(egr_ne_prev[0])
                    except Exception:
                        pass
                
                progress_pct = round((total_actual / total_target) * 100) if total_target > 0 else 0
                
                variation_pct = 0.0
                if total_prev > 0:
                    variation_pct = round(((total_actual - total_prev) / total_prev) * 100, 1)
                
                descriptions = {
                    "Catastro": "14 trámites (Planos de mensura, PH, etc.)",
                    "Registros": "5 trámites (Inicio de obras, Model BA, etc.)",
                    "Incendio": "Prevención contra incendios",
                    "Conforme": "Conforme a obra civil",
                    "Instalaciones": "8 trámites (Sanitaria, Ventilación, Térmica, etc.)",
                    "Consultas de Usos": "5 trámites de localización y antenas",
                    "Permisos": "3 trámites (Permiso civil, Demoliciones, etc.)",
                    "Interpretaciones/Informe Urbanisitco": "Interpretación e informe urbanístico",
                    "Consultas Obligatorias": "APH y Catalogados / General",
                    "Otros": "9 trámites (Aviso de obra, Foguistas, etc.)"
                }
                
                results.append({
                    "family_name": family_name,
                    "actual_egr": round(total_actual),
                    "target_egr": round(total_target),
                    "progress_pct": progress_pct,
                    "variation_pct": variation_pct,
                    "trata_count": len(tratas),
                    "tratas": tratas,
                    "description": descriptions.get(family_name, f"{len(tratas)} trámites")
                })
                
        return results
    except Exception as e:
        logger.error(f"Error in families overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Specific endpoints for Público Privado and COPUA to handle row clicks and cell clicks ---

def get_analyst_history_data(analyst: str, cache_key: str) -> List[Dict[str, Any]]:
    now = datetime.now()
    months_list = []
    curr_y, curr_m = now.year, now.month
    for _ in range(12):
        months_list.append(f"{curr_y}-{str(curr_m).zfill(2)}")
        curr_m -= 1
        if curr_m == 0:
            curr_m = 12
            curr_y -= 1

    grid = {}
    for m_label in months_list:
        parts = m_label.split('-')
        grid[m_label] = {
            "anio": int(parts[0]),
            "mes": int(parts[1]),
            "DETALLE TRATA": analyst,
            "ING": 0,
            "EGR_EF": 0,
            "EGR_NE": 0,
            "STOCK_PROPIO": 0,
            "STOCK_SUBS": 0
        }

    try:
        with engine.connect() as conn:
            sql_ing = """
                WITH primer_ingreso AS (
                    SELECT id_expediente, destinatario, min(fecha) as min_fecha
                    FROM mvw_ee_pases_secgdu
                    WHERE destinatario = :analyst
                    GROUP BY id_expediente, destinatario
                )
                SELECT 
                    to_char(min_fecha, 'YYYY-MM') AS mes_label,
                    COUNT(*) as cant
                FROM primer_ingreso
                GROUP BY 1
            """
            res_ing = conn.execute(text(sql_ing), {"analyst": analyst}).fetchall()
            for r in res_ing:
                if r[0] in grid:
                    grid[r[0]]["ING"] = r[1]

            sql_egr = """
                SELECT 
                    to_char(fecha, 'YYYY-MM') AS mes_label,
                    COUNT(DISTINCT id_expediente) as cant
                FROM mvw_ee_pases_secgdu
                WHERE usuario = :analyst AND NOT (destinatario = :analyst)
                GROUP BY 1
            """
            res_egr = conn.execute(text(sql_egr), {"analyst": analyst}).fetchall()
            for r in res_egr:
                if r[0] in grid:
                    grid[r[0]]["EGR_NE"] = r[1]

            sql_stock_hist = """
                WITH fechas_corte AS (
                    SELECT (date_trunc('month', mes.mes) + '1 mon -1 days'::interval)::date AS fecha_corte
                    FROM generate_series(
                        date_trunc('month', CURRENT_DATE) - '11 mons'::interval,
                        date_trunc('month', CURRENT_DATE),
                        '1 mon'::interval
                    ) mes(mes)
                ),
                destinatario_por_corte AS (
                    SELECT DISTINCT ON (p.id_expediente, fc.fecha_corte)
                        p.id_expediente,
                        fc.fecha_corte,
                        p.destinatario AS destinatario_cierre
                    FROM fechas_corte fc
                    JOIN mvw_ee_pases_secgdu p ON p.fecha::date <= fc.fecha_corte
                    WHERE p.id_expediente IN (
                        SELECT DISTINCT id_expediente FROM mvw_ee_pases_secgdu WHERE destinatario = :analyst
                    )
                    ORDER BY p.id_expediente, fc.fecha_corte, p.fecha DESC
                ),
                subsanacion_abierta_al_cierre AS (
                    SELECT DISTINCT ON (dpc.id_expediente, dpc.fecha_corte)
                        dpc.id_expediente,
                        dpc.fecha_corte,
                        true AS tiene_subsanacion_abierta
                    FROM destinatario_por_corte dpc
                    JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = dpc.id_expediente 
                        AND a.usuario_alta = dpc.destinatario_cierre 
                        AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD' 
                        AND a.fecha_alta::date <= dpc.fecha_corte 
                        AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc.fecha_corte)
                    ORDER BY dpc.id_expediente, dpc.fecha_corte, a.fecha_alta DESC
                )
                SELECT 
                    to_char(dpc.fecha_corte, 'YYYY-MM') AS mes_label,
                    SUM(CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, false) THEN 0 ELSE 1 END) AS stock_propio,
                    SUM(CASE WHEN COALESCE(sac.tiene_subsanacion_abierta, false) THEN 1 ELSE 0 END) AS stock_subs
                FROM destinatario_por_corte dpc
                LEFT JOIN subsanacion_abierta_al_cierre sac ON sac.id_expediente = dpc.id_expediente AND sac.fecha_corte = dpc.fecha_corte
                WHERE dpc.destinatario_cierre = :analyst
                GROUP BY 1
            """
            res_stock = conn.execute(text(sql_stock_hist), {"analyst": analyst}).fetchall()
            for r in res_stock:
                if r[0] in grid:
                    grid[r[0]]["STOCK_PROPIO"] = int(r[1] or 0)
                    grid[r[0]]["STOCK_SUBS"] = int(r[2] or 0)

            curr_mes_label = now.strftime('%Y-%m')
            
            sql_stock_live = """
                SELECT COUNT(*) AS cant
                FROM mv_ultimo_pase up
                WHERE up.destinatario_actual = :analyst
                  AND NOT EXISTS (
                      SELECT 1 FROM mvw_ee_actividades_secgdu a
                      WHERE a.id_expediente = up.id_expediente
                        AND a.usuario_alta = up.destinatario_actual
                        AND a.estado = 'PENDIENTE'
                        AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                  )
            """
            res_stock_live = conn.execute(text(sql_stock_live), {"analyst": analyst}).fetchone()
            if res_stock_live and curr_mes_label in grid:
                grid[curr_mes_label]["STOCK_PROPIO"] = res_stock_live[0]

            sql_subs_live = """
                SELECT COUNT(*) AS cant
                FROM mv_ultimo_pase up
                JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = up.id_expediente AND a.usuario_alta = up.destinatario_actual
                WHERE up.destinatario_actual = :analyst
                  AND a.estado = 'PENDIENTE'
                  AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
            """
            res_subs_live = conn.execute(text(sql_subs_live), {"analyst": analyst}).fetchone()
            if res_subs_live and curr_mes_label in grid:
                grid[curr_mes_label]["STOCK_SUBS"] = res_subs_live[0]

    except Exception as e:
        logger.error(f"Error querying analyst history data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    result = []
    for m_label in months_list:
        result.append(grid[m_label])
    return result

def get_analyst_stock_detail_data(analyst: str) -> Dict[str, Any]:
    try:
        with engine.connect() as conn:
            sql = """
                SELECT 
                    up.id_expediente, 
                    ext.expediente as expediente,
                    ext.fecha_creacion_ee as fecha_ing,
                    up.fecha_ultimo_pase as fecha_ultimo_pase,
                    (CURRENT_DATE - up.fecha_ultimo_pase::date) as dias,
                    up.destinatario_actual as analista,
                    du.apellido_nombre as analista_nombre,
                    ext.trata,
                    ext.fecha_creacion_ee as caratula,
                    ext.descripcion_trata,
                    ext.descripcion,
                    up.estado_en_pase as estado_expediente,
                    (CURRENT_DATE - ext.fecha_creacion_ee::date) as dias_en_gerencia
                FROM mv_ultimo_pase up
                LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = up.id_expediente
                LEFT JOIN datos_usuario du ON up.destinatario_actual = du.usuario
                WHERE up.destinatario_actual = :analyst
                  AND NOT EXISTS (
                      SELECT 1 FROM mvw_ee_actividades_secgdu a
                      WHERE a.id_expediente = up.id_expediente
                        AND a.usuario_alta = up.destinatario_actual
                        AND a.estado = 'PENDIENTE'
                        AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                  )
            """
            result = conn.execute(text(sql), {"analyst": analyst})
            rows = [dict(r._mapping) for r in result.fetchall()]

            analyst_data = {}
            propio_month_counts = {}
            ranges = [(0, 15, "Menos de 15 dias"), (15, 30, "15 a 30 dias"), (30, 45, "30 a 45 dias"), (45, 60, "45 a 60 dias"), (60, 75, "60 a 75 dias"), (75, 90, "75 a 90 dias"), (90, 999999, "Mas de 90 dias")]
            
            for row in rows:
                analista = row.get('analista') or 'SIN ASIGNAR'
                analista_nombre = row.get('analista_nombre') or analista
                dias = row.get('dias') or 0
                f_pase = row.get('fecha_ultimo_pase')
                
                if f_pase and hasattr(f_pase, 'strftime'):
                    m_key = f_pase.strftime("%Y-%m")
                    propio_month_counts[m_key] = propio_month_counts.get(m_key, 0) + 1

                if analista not in analyst_data:
                    analyst_data[analista] = {"analista": analista, "analista_nombre": analista_nombre, "TOTAL": 0}
                    for _, _, r_name in ranges: analyst_data[analista][r_name] = 0
                
                analyst_data[analista]["TOTAL"] += 1
                for r_min, r_max, r_name in ranges:
                    if r_min <= dias < r_max:
                        analyst_data[analista][r_name] += 1
                        break
            
            month_dist = [{"periodo": m, "cantidad": propio_month_counts.get(m, 0)} for m in sorted(propio_month_counts.keys())]
            
            expedientes = []
            for r in rows[:1000]:
                expedientes.append({
                    "id_expediente": r.get("id_expediente"),
                    "expediente": r.get("expediente"),
                    "fecha_ing": r.get("fecha_ing").strftime("%Y-%m-%d %H:%M:%S") if r.get("fecha_ing") and hasattr(r.get("fecha_ing"), "strftime") else None,
                    "fecha_ultimo_pase": r.get("fecha_ultimo_pase").strftime("%Y-%m-%d %H:%M:%S") if r.get("fecha_ultimo_pase") and hasattr(r.get("fecha_ultimo_pase"), "strftime") else None,
                    "dias": r.get("dias") if r.get("dias") is not None else 0,
                    "analista": r.get("analista"),
                    "analista_nombre": r.get("analista_nombre") or r.get("analista"),
                    "trata": r.get("trata"),
                    "caratula": r.get("caratula").strftime("%Y-%m-%d %H:%M:%S") if r.get("caratula") and hasattr(r.get("caratula"), "strftime") else (str(r.get("caratula"))[:19] if r.get("caratula") else None),
                    "descripcion_trata": r.get("descripcion_trata"),
                    "descripcion": r.get("descripcion"),
                    "estado_expediente": r.get("estado_expediente"),
                    "dias_en_gerencia": r.get("dias_en_gerencia") if r.get("dias_en_gerencia") is not None else 0
                })

            return {
                "nombre_trata": analyst,
                "stock_propio_count": len(rows),
                "month_distribution": month_dist,
                "analyst_distribution": list(analyst_data.values()),
                "expedientes": expedientes
            }
    except Exception as e:
        logger.error(f"Error in analyst stock_detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_analyst_detalle_periodo_data(analyst: str, targets: List[str], period: str, metric: str) -> List[Dict[str, Any]]:
    periodo_norm = period
    if '-' in period:
        parts = period.split('-')
        if len(parts) == 2:
            try:
                year = int(parts[0])
                month = int(parts[1])
                periodo_norm = f"{year:04d}-{month:02d}"
            except ValueError:
                pass

    current_month_str = datetime.now().strftime('%Y-%m')
    is_current_month = (periodo_norm == current_month_str)

    import calendar
    try:
        p_parts = periodo_norm.split('-')
        p_year = int(p_parts[0])
        p_month = int(p_parts[1])
        p_last_day = calendar.monthrange(p_year, p_month)[1]
        cut_off_date = f"{p_year:04d}-{p_month:02d}-{p_last_day:02d}"
    except Exception:
        cut_off_date = datetime.now().strftime('%Y-%m-%d')

    sql = ""
    params = {
        "analyst": analyst,
        "periodo": periodo_norm,
        "cut_off_date": cut_off_date,
        "targets": targets
    }

    if metric in ['STOCK_PROPIO', 'STOCK_SUBS', 'STOCK_TOTAL'] and not is_current_month:
        if metric == 'STOCK_PROPIO':
            sql = """
                WITH destinatario_por_corte AS (
                    SELECT DISTINCT ON (p.id_expediente) 
                        p.id_expediente,
                        p.destinatario AS analista,
                        p.fecha AS fecha_recepcion_analista
                    FROM mvw_ee_pases_secgdu p
                    WHERE p.id_expediente IN (
                        SELECT DISTINCT id_expediente FROM mvw_ee_pases_secgdu WHERE destinatario = :analyst
                    ) AND CAST(p.fecha AS date) <= CAST(:cut_off_date AS date)
                    ORDER BY p.id_expediente, p.fecha DESC
                ),
                subsanacion_abierta AS (
                    SELECT DISTINCT ON (d.id_expediente) d.id_expediente, true AS tiene_subsanacion
                    FROM destinatario_por_corte d
                    JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = d.id_expediente 
                                                   AND a.usuario_alta = d.analista 
                                                   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'::text 
                                                   AND CAST(a.fecha_alta AS date) <= CAST(:cut_off_date AS date) 
                                                   AND (a.fecha_cierre IS NULL OR CAST(a.fecha_cierre AS date) > CAST(:cut_off_date AS date))
                    ORDER BY d.id_expediente, a.fecha_alta DESC
                )
                SELECT 
                    'OFICIAL' AS "TIPO TRAMITE",
                    ext.expediente AS "EXPEDIENTE",
                    ext.trata AS "TRAMITE",
                    to_char(ext.fecha_creacion_ee, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO",
                    to_char(d.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA",
                    (CAST(:cut_off_date AS date) - CAST(d.fecha_recepcion_analista AS date)) AS "DIAS EN PODER",
                    (CAST(:cut_off_date AS date) - CAST(ext.fecha_creacion_ee AS date)) AS "DIAS EN GERENCIA",
                    d.analista AS "ANALISTA",
                    du.apellido_nombre AS "ANALISTA NOMBRE",
                    ext.descripcion_trata AS "DESCRIPCION TRATA",
                    ext.descripcion AS "DESCRIPCION",
                    ext.estado_en_pase AS "ESTADO EXPEDIENTE"
                FROM destinatario_por_corte d
                JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = d.id_expediente
                LEFT JOIN datos_usuario du ON d.analista = du.usuario
                LEFT JOIN subsanacion_abierta sa ON sa.id_expediente = d.id_expediente
                WHERE d.analista = :analyst AND sa.tiene_subsanacion IS NOT TRUE
            """
        elif metric == 'STOCK_SUBS':
            sql = """
                WITH destinatario_por_corte AS (
                    SELECT DISTINCT ON (p.id_expediente) 
                        p.id_expediente,
                        p.destinatario AS analista,
                        p.fecha AS fecha_recepcion_analista
                    FROM mvw_ee_pases_secgdu p
                    WHERE p.id_expediente IN (
                        SELECT DISTINCT id_expediente FROM mvw_ee_pases_secgdu WHERE destinatario = :analyst
                    ) AND CAST(p.fecha AS date) <= CAST(:cut_off_date AS date)
                    ORDER BY p.id_expediente, p.fecha DESC
                ),
                subsanacion_abierta AS (
                    SELECT DISTINCT ON (d.id_expediente) d.id_expediente, true AS tiene_subsanacion
                    FROM destinatario_por_corte d
                    JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = d.id_expediente 
                                                   AND a.usuario_alta = d.analista 
                                                   AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'::text 
                                                   AND CAST(a.fecha_alta AS date) <= CAST(:cut_off_date AS date) 
                                                   AND (a.fecha_cierre IS NULL OR CAST(a.fecha_cierre AS date) > CAST(:cut_off_date AS date))
                    ORDER BY d.id_expediente, a.fecha_alta DESC
                )
                SELECT 
                    'OFICIAL' AS "TIPO TRAMITE",
                    ext.expediente AS "EXPEDIENTE",
                    ext.trata AS "TRAMITE",
                    to_char(ext.fecha_creacion_ee, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO",
                    to_char(d.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA",
                    (CAST(:cut_off_date AS date) - CAST(d.fecha_recepcion_analista AS date)) AS "DIAS EN PODER",
                    (CAST(:cut_off_date AS date) - CAST(ext.fecha_creacion_ee AS date)) AS "DIAS EN GERENCIA",
                    d.analista AS "ANALISTA",
                    du.apellido_nombre AS "ANALISTA NOMBRE",
                    ext.descripcion_trata AS "DESCRIPCION TRATA",
                    ext.descripcion AS "DESCRIPCION",
                    ext.estado_en_pase AS "ESTADO EXPEDIENTE"
                FROM destinatario_por_corte d
                JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = d.id_expediente
                LEFT JOIN datos_usuario du ON d.analista = du.usuario
                JOIN subsanacion_abierta sa ON sa.id_expediente = d.id_expediente
                WHERE d.analista = :analyst AND sa.tiene_subsanacion IS TRUE
            """
    elif metric == 'ING':
        sql = """
            WITH primer_ingreso AS (
                SELECT id_expediente, destinatario, min(fecha) as min_fecha
                FROM mvw_ee_pases_secgdu
                WHERE destinatario = :analyst
                GROUP BY id_expediente, destinatario
            )
            SELECT 
                'OFICIAL' AS "TIPO TRAMITE",
                ext.expediente AS "EXPEDIENTE",
                ext.trata AS "TRAMITE",
                to_char(pi.min_fecha, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO",
                to_char(up.fecha_ultimo_pase, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA",
                (CURRENT_DATE - up.fecha_ultimo_pase::date) AS "DIAS EN PODER",
                (CURRENT_DATE - ext.fecha_creacion_ee::date) AS "DIAS EN GERENCIA",
                up.destinatario_actual AS "ANALISTA",
                du.apellido_nombre AS "ANALISTA NOMBRE",
                ext.descripcion_trata AS "DESCRIPCION TRATA",
                ext.descripcion AS "DESCRIPCION",
                up.estado_en_pase AS "ESTADO EXPEDIENTE"
            FROM primer_ingreso pi
            JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = pi.id_expediente
            LEFT JOIN mv_ultimo_pase up ON up.id_expediente = pi.id_expediente
            LEFT JOIN datos_usuario du ON up.destinatario_actual = du.usuario
            WHERE to_char(pi.min_fecha, 'YYYY-MM') = :periodo
        """
    elif metric == 'EGR_NE':
        sql = """
            WITH egr_pases AS (
                SELECT DISTINCT ON (id_expediente) id_expediente, fecha, destinatario
                FROM mvw_ee_pases_secgdu
                WHERE usuario = :analyst AND NOT (destinatario = ANY(:targets))
                  AND to_char(fecha, 'YYYY-MM') = :periodo
                ORDER BY id_expediente, fecha DESC
            )
            SELECT 
                'OFICIAL' AS "TIPO TRAMITE",
                ext.expediente AS "EXPEDIENTE",
                ext.trata AS "TRAMITE",
                to_char(ext.fecha_creacion_ee, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO",
                to_char(ep.fecha, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA",
                (CURRENT_DATE - ep.fecha::date) AS "DIAS EN PODER",
                (CURRENT_DATE - ext.fecha_creacion_ee::date) AS "DIAS EN GERENCIA",
                ep.destinatario AS "ANALISTA",
                du.apellido_nombre AS "ANALISTA NOMBRE",
                ext.descripcion_trata AS "DESCRIPCION TRATA",
                ext.descripcion AS "DESCRIPCION",
                ext.estado_en_pase AS "ESTADO EXPEDIENTE"
            FROM egr_pases ep
            JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = ep.id_expediente
            LEFT JOIN datos_usuario du ON ep.destinatario = du.usuario
        """
    elif metric == 'STOCK_PROPIO' and is_current_month:
        sql = """
            SELECT 
                'OFICIAL' AS "TIPO TRAMITE",
                ext.expediente AS "EXPEDIENTE",
                ext.trata AS "TRAMITE",
                to_char(ext.fecha_creacion_ee, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO",
                to_char(up.fecha_ultimo_pase, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA",
                (CURRENT_DATE - up.fecha_ultimo_pase::date) AS "DIAS EN PODER",
                (CURRENT_DATE - ext.fecha_creacion_ee::date) AS "DIAS EN GERENCIA",
                up.destinatario_actual AS "ANALISTA",
                du.apellido_nombre AS "ANALISTA NOMBRE",
                ext.descripcion_trata AS "DESCRIPCION TRATA",
                ext.descripcion AS "DESCRIPCION",
                up.estado_en_pase AS "ESTADO EXPEDIENTE"
            FROM mv_ultimo_pase up
            JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = up.id_expediente
            LEFT JOIN datos_usuario du ON up.destinatario_actual = du.usuario
            WHERE up.destinatario_actual = :analyst
              AND NOT EXISTS (
                  SELECT 1 FROM mvw_ee_actividades_secgdu a
                  WHERE a.id_expediente = up.id_expediente
                    AND a.usuario_alta = up.destinatario_actual
                    AND a.estado = 'PENDIENTE'
                    AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
              )
        """
    elif metric == 'STOCK_SUBS' and is_current_month:
        sql = """
            SELECT 
                'OFICIAL' AS "TIPO TRAMITE",
                ext.expediente AS "EXPEDIENTE",
                ext.trata AS "TRAMITE",
                to_char(ext.fecha_creacion_ee, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO",
                to_char(up.fecha_ultimo_pase, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA",
                (CURRENT_DATE - up.fecha_ultimo_pase::date) AS "DIAS EN PODER",
                (CURRENT_DATE - ext.fecha_creacion_ee::date) AS "DIAS EN GERENCIA",
                up.destinatario_actual AS "ANALISTA",
                du.apellido_nombre AS "ANALISTA NOMBRE",
                ext.descripcion_trata AS "DESCRIPCION TRATA",
                ext.descripcion AS "DESCRIPCION",
                up.estado_en_pase AS "ESTADO EXPEDIENTE"
            FROM mv_ultimo_pase up
            JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = up.id_expediente
            LEFT JOIN datos_usuario du ON up.destinatario_actual = du.usuario
            JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = up.id_expediente AND a.usuario_alta = up.destinatario_actual
            WHERE up.destinatario_actual = :analyst
              AND a.estado = 'PENDIENTE'
              AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
        """

    if not sql:
        return []

    try:
        with engine.connect() as conn:
            res = conn.execute(text(sql), params)
            return [dict(r._mapping) for r in res.fetchall()]
    except Exception as e:
        logger.error(f"Error querying analyst detail period data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/publico_privado/tramite/{trata}")
def get_publico_privado_tramite(trata: str, current_user: User = Depends(get_current_user)):
    return get_analyst_history_data(trata, f"history_publico_privado_{trata}")

@router.get("/api/reporte/copua/tramite/{trata}")
def get_copua_tramite(trata: str, current_user: User = Depends(get_current_user)):
    return get_analyst_history_data(trata, f"history_copua_{trata}")

@router.get("/api/reporte/publico_privado/tramite/{trata}/stock_detail")
def get_publico_privado_stock_detail(trata: str, current_user: User = Depends(get_current_user)):
    return get_analyst_stock_detail_data(trata)

@router.get("/api/reporte/copua/tramite/{trata}/stock_detail")
def get_copua_stock_detail(trata: str, current_user: User = Depends(get_current_user)):
    return get_analyst_stock_detail_data(trata)

@router.get("/api/reporte/publico_privado/tramite/{trata}/detalle_periodo")
def get_publico_privado_detalle_periodo(trata: str, periodo: str, metrica: str, current_user: User = Depends(get_current_user)):
    targets = ["NDEFAVERI", "NARGANDONAJULIO", "DGIUR-GERENCIAPPP"]
    return get_analyst_detalle_periodo_data(trata, targets, periodo, metrica)

@router.get("/api/reporte/copua/tramite/{trata}/detalle_periodo")
def get_copua_detalle_periodo(trata: str, periodo: str, metrica: str, current_user: User = Depends(get_current_user)):
    targets = ["CAPUAM-02"]
    return get_analyst_detalle_periodo_data(trata, targets, periodo, metrica)

@router.get("/api/reporte/{gerencia}/tramite/{trata}")
async def get_reporte_tramite_historico(gerencia: str, trata: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
    try:
        now = datetime.now()
        months_list = []
        curr_y, curr_m = now.year, now.month
        for i in range(12):
            months_list.append(f"({curr_y}, {curr_m})")
            curr_m -= 1
            if curr_m == 0:
                curr_m = 12
                curr_y -= 1
        months_filter = ", ".join(months_list)

        with engine.connect() as conn:
            if trata == 'INTERVENCIONES':
                nombre_trata = "Intervenciones"
            else:
                trata_info = conn.execute(text("""
                    SELECT COALESCE(
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE trata_reporte = :t AND gerencia = :g LIMIT 1),
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE :t = ANY(tratas_incluidas) AND gerencia = :g LIMIT 1),
                        (SELECT descripcion_trata FROM vw_expedientes_maestro WHERE trata = :t LIMIT 1)
                    )
                """), {"t": trata, "g": gerencia_clean}).fetchone()
                nombre_trata = trata_info[0] if trata_info else trata

            if gerencia_clean in ['instalaciones', 'morfologia', 'contable', 'etapa_proyecto', 'catastro', 'aph', 'usos', 'regularizacion', 'aviso_obra']:
                trata_filter = f"trata = '{trata}'" if trata != 'INTERVENCIONES' else f"trata NOT IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = '{gerencia_clean}')"
                
                interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"
                egr_trata_where = "trata = 'INTERVENCIONES'" if trata == 'INTERVENCIONES' else f"trata = '{trata}'"

                sql = f"""
                    WITH periodos AS (
                        SELECT DISTINCT mes_label FROM mv_{gerencia_clean}_stock_historico
                        ORDER BY mes_label DESC LIMIT 12
                    ),
                    ing AS (
                        SELECT to_char(fecha_ingreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                        FROM mv_{gerencia_clean}_ingresos_eventos WHERE {trata_filter}
                        GROUP BY 1
                    ),
                    egr_ef AS (
                        SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_label, COUNT(*) as cant
                        FROM (
                            SELECT fecha_egreso, trata FROM mv_{gerencia_clean}_gedos_egreso
                            UNION ALL
                            SELECT fecha_egreso, 'INTERVENCIONES' as trata FROM {interv_egr_table}
                        ) t_egr
                        WHERE {egr_trata_where}
                        GROUP BY 1
                    ),
                    egr_ne AS (
                        SELECT to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_label, COUNT(*) as cant
                        FROM mv_{gerencia_clean}_egresos_no_efectivos WHERE {trata_filter}
                        GROUP BY 1
                    ),
                    stock_data AS (
                        SELECT mes_label, 
                               SUM(CASE WHEN categoria = 'STOCK_PROPIO' THEN cant_expedientes ELSE 0 END) as stock_propio,
                               SUM(CASE WHEN categoria = 'SUBSANACION' THEN cant_expedientes ELSE 0 END) as stock_subs
                        FROM mv_{gerencia_clean}_stock_historico WHERE {trata_filter}
                        GROUP BY 1
                    ),
                    current_stock AS (
                        SELECT COUNT(*) as cant FROM mv_{gerencia_clean}_stock_propio WHERE {trata_filter}
                        UNION ALL
                        SELECT COUNT(*) as cant FROM mv_{gerencia_clean}_intervenciones_stock WHERE {'1=1' if trata == 'INTERVENCIONES' else 'FALSE'}
                    ),
                    current_subs AS (
                        SELECT COUNT(*) as cant FROM mv_{gerencia_clean}_subsanaciones WHERE {trata_filter}
                        UNION ALL
                        SELECT COUNT(*) as cant FROM mv_{gerencia_clean}_intervenciones_subs WHERE {'1=1' if trata == 'INTERVENCIONES' else 'FALSE'}
                    )
                    SELECT 
                        split_part(p.mes_label, '-', 1)::int as anio,
                        split_part(p.mes_label, '-', 2)::int as mes,
                        '{nombre_trata}'::text as "DETALLE TRATA",
                        COALESCE(i.cant, 0) as "ING",
                        COALESCE(ef.cant, 0) as "EGR_EF",
                        COALESCE(ne.cant, 0) as "EGR_NE",
                        CASE 
                            WHEN p.mes_label = to_char(now(), 'YYYY-MM')
                            THEN COALESCE((SELECT SUM(cant) FROM current_stock), 0)
                            ELSE COALESCE(s.stock_propio, 0)
                        END as "STOCK_PROPIO",
                        CASE 
                            WHEN p.mes_label = to_char(now(), 'YYYY-MM')
                            THEN COALESCE((SELECT SUM(cant) FROM current_subs), 0)
                            ELSE COALESCE(s.stock_subs, 0)
                        END as "STOCK_SUBS"
                    FROM periodos p
                    LEFT JOIN ing i ON i.mes_label = p.mes_label
                    LEFT JOIN egr_ef ef ON ef.mes_label = p.mes_label
                    LEFT JOIN egr_ne ne ON ne.mes_label = p.mes_label
                    LEFT JOIN stock_data s ON s.mes_label = p.mes_label
                    ORDER BY anio DESC, mes DESC
                """
            elif trata == 'INTERVENCIONES':
                sql = f"""
                    SELECT anio, mes, "DETALLE TRATA", "ING", "EGR_EF", "EGR_NE", "STOCK_PROPIO", "STOCK_SUBS"
                    FROM mvw_reporte_historico_{gerencia_clean}
                    WHERE "COD TRATA" = 'INTERVENCIONES'
                      AND (anio, mes) IN ({months_filter})
                    ORDER BY anio DESC, mes DESC
                """
            else:
                sql = f"""
                    SELECT anio, mes, "DETALLE TRATA", "ING", "EGR_EF", "EGR_NE", "STOCK_PROPIO", "STOCK_SUBS"
                    FROM mvw_reporte_historico_{gerencia_clean}
                    WHERE "COD TRATA" = '{trata}'
                      AND (anio, mes) IN ({months_filter})
                    ORDER BY anio DESC, mes DESC
                """

            df_hist = pd.read_sql(sql, conn)
            
        if df_hist.empty: return []
        return df_hist.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error en histórico individual: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/{gerencia}/tramite/{trata}/stock_detail")
async def get_tramite_stock_detail(gerencia: str, trata: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
    if gerencia_clean not in TRAMITES_CONFIG: raise HTTPException(status_code=404, detail="Gerencia no encontrada.")

    try:
        with engine.connect() as conn:
            if trata == 'INTERVENCIONES':
                nombre_trata = "Intervenciones"
            else:
                trata_info = conn.execute(text("""
                    SELECT COALESCE(
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE trata_reporte = :t AND gerencia = :g LIMIT 1),
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE :t = ANY(tratas_incluidas) AND gerencia = :g LIMIT 1),
                        (SELECT descripcion_trata FROM vw_expedientes_maestro WHERE trata = :t LIMIT 1)
                    )
                """), {"t": trata, "g": gerencia_clean}).fetchone()
                nombre_trata = trata_info[0] if trata_info else trata

            if gerencia_clean in ['instalaciones', 'morfologia', 'contable', 'etapa_proyecto', 'catastro', 'aph', 'usos', 'regularizacion', 'aviso_obra']:
                trata_codes = list(TRAMITES_CONFIG[gerencia_clean].keys())
                is_official = trata in [t for t in trata_codes if t != 'INTERVENCIONES']
                view_name = f"mv_{gerencia_clean}_stock_propio" if is_official else f"mv_{gerencia_clean}_intervenciones_stock"
                
                sql = f"""
                    SELECT {view_name}.id_expediente, {view_name}.expediente, {view_name}.fecha_primer_ingreso_gerencia as fecha_ing, 
                           {view_name}.fecha_recepcion_analista as fecha_ultimo_pase, 
                           {view_name}.dias_en_poder_actual as dias, {view_name}.analista, du.apellido_nombre as analista_nombre, {view_name}.trata, 
                           ext.fecha_creacion as caratula,
                           ext.descripcion_trata, ext.descripcion, ext.estado as estado_expediente,
                           (CURRENT_DATE - {view_name}.fecha_primer_ingreso_gerencia::date) as dias_en_gerencia
                    FROM {view_name}
                    LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = {view_name}.id_expediente
                    LEFT JOIN datos_usuario du ON {view_name}.analista = du.usuario
                    WHERE {f"{view_name}.trata = '{trata}'" if trata != 'INTERVENCIONES' else '1=1'}
                """
                result = conn.execute(text(sql))
                rows = [dict(r._mapping) for r in result.fetchall()]

                analyst_data = {}
                propio_month_counts = {}
                ranges = [(0, 15, "Menos de 15 dias"), (15, 30, "15 a 30 dias"), (30, 45, "30 a 45 dias"), (45, 60, "45 a 60 dias"), (60, 75, "60 a 75 dias"), (75, 90, "75 a 90 dias"), (90, 999999, "Mas de 90 dias")]
                
                for row in rows:
                    analista = row.get('analista') or 'SIN ASIGNAR'
                    analista_nombre = row.get('analista_nombre') or analista
                    dias = row.get('dias') or 0
                    f_pase = row.get('fecha_ultimo_pase')
                    
                    if f_pase and hasattr(f_pase, 'strftime'):
                        m_key = f_pase.strftime("%Y-%m")
                        propio_month_counts[m_key] = propio_month_counts.get(m_key, 0) + 1

                    if analista not in analyst_data:
                        analyst_data[analista] = {"analista": analista, "analista_nombre": analista_nombre, "TOTAL": 0}
                        for _, _, r_name in ranges: analyst_data[analista][r_name] = 0
                    
                    analyst_data[analista]["TOTAL"] += 1
                    for r_min, r_max, r_name in ranges:
                        if r_min <= dias < r_max:
                            analyst_data[analista][r_name] += 1
                            break
                
                month_dist = [{"periodo": m, "cantidad": propio_month_counts.get(m, 0)} for m in sorted(propio_month_counts.keys())]
            else:
                cfg_query = text("""
                    SELECT buzones_ingreso, analistas_oficiales 
                    FROM cfg_gestion_metas 
                    WHERE gerencia = :g AND trata_reporte = :t
                """)
                trata_cfg_lookup = gerencia_clean.upper() if gerencia_clean in ['instalaciones', 'contable'] else trata
                cfg_res = conn.execute(cfg_query, {"g": gerencia_clean, "t": trata_cfg_lookup}).fetchone()
                
                if not cfg_res:
                    return {"nombre_trata": nombre_trata, "stock_propio_count": 0, "month_distribution": [], "analyst_distribution": [], "expedientes": []}
                
                sector_whitelist = (cfg_res[0] or []) + (cfg_res[1] or [])
                if not sector_whitelist:
                    return {"nombre_trata": nombre_trata, "stock_propio_count": 0, "month_distribution": [], "analyst_distribution": [], "expedientes": []}

                sql = f"""
                    SELECT id_expediente, expediente, fecha_ing, fecha_ultimo_pase, 
                           dias_stock as dias, analista_actual as analista, du.apellido_nombre as analista_nombre, trata,
                           fecha_creacion as caratula,
                           descripcion_trata,
                           descripcion,
                           estado as estado_expediente,
                           dias_stock as dias_en_gerencia
                    FROM mvw_stock_actual_detalle
                    LEFT JOIN datos_usuario du ON mvw_stock_actual_detalle.analista_actual = du.usuario
                    WHERE trata_reporte = :t 
                      AND gerencia = :g
                      AND is_subs = 0
                      AND analista_actual = ANY(:whitelist)
                """
                result = conn.execute(text(sql), {"t": trata, "g": gerencia_clean, "whitelist": sector_whitelist})
                rows = [dict(r._mapping) for r in result.fetchall()]

                query_month = text(f"SELECT anio || '-' || LPAD(mes::text, 2, '0') as periodo, COUNT(*) as cantidad FROM mvw_reporte_historico_{gerencia_clean} WHERE \"COD TRATA\" = :t GROUP BY 1 ORDER BY 1")
                res_month = conn.execute(query_month, {"t": trata})
                month_dist = [dict(row) for row in res_month.mappings()]
                
                analyst_data = {}
                ranges = [(0, 15, "Menos de 15 dias"), (15, 30, "15 a 30 dias"), (30, 45, "30 a 45 dias"), (45, 60, "45 a 60 dias"), (60, 75, "60 a 75 dias"), (75, 90, "75 a 90 dias"), (90, 999999, "Mas de 90 dias")]
                
                for row in rows:
                    analista = row.get('analista') or 'SIN ASIGNAR'
                    analista_nombre = row.get('analista_nombre') or analista
                    dias = row.get('dias') or 0
                    
                    if analista not in analyst_data:
                        analyst_data[analista] = {"analista": analista, "analista_nombre": analista_nombre, "TOTAL": 0}
                        for _, _, r_name in ranges: analyst_data[analista][r_name] = 0
                    
                    analyst_data[analista]["TOTAL"] += 1
                    for r_min, r_max, r_name in ranges:
                        if r_min <= dias < r_max:
                            analyst_data[analista][r_name] += 1
                            break
            
            return {
                "nombre_trata": nombre_trata,
                "stock_propio_count": len(rows),
                "month_distribution": month_dist,
                "analyst_distribution": list(analyst_data.values()),
                "expedientes": [
                    {
                        "id_expediente": r.get("id_expediente"),
                        "expediente": r.get("expediente"),
                        "fecha_ing": r.get("fecha_ing").strftime("%Y-%m-%d %H:%M:%S") if r.get("fecha_ing") and hasattr(r.get("fecha_ing"), "strftime") else None,
                        "fecha_ultimo_pase": r.get("fecha_ultimo_pase").strftime("%Y-%m-%d %H:%M:%S") if r.get("fecha_ultimo_pase") and hasattr(r.get("fecha_ultimo_pase"), "strftime") else None,
                        "dias": r.get("dias") if r.get("dias") is not None else 0,
                        "analista": r.get("analista"),
                        "analista_nombre": r.get("analista_nombre") or r.get("analista"),
                        "trata": r.get("trata"),
                        "caratula": r.get("caratula").strftime("%Y-%m-%d %H:%M:%S") if r.get("caratula") and hasattr(r.get("caratula"), "strftime") else (str(r.get("caratula"))[:19] if r.get("caratula") else None),
                        "descripcion_trata": r.get("descripcion_trata"),
                        "descripcion": r.get("descripcion"),
                        "estado_expediente": r.get("estado_expediente"),
                        "dias_en_gerencia": r.get("dias_en_gerencia") if r.get("dias_en_gerencia") is not None else 0
                    } 
                    for r in rows[:1000]
                ]
            }
    except Exception as e:
        logger.error(f"Error en stock_detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/{gerencia}/buzones")
async def get_gerencia_buzones(gerencia: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
    
    if gerencia_clean == 'secgdu_todos':
        try:
            with engine.connect() as conn:
                sql = """
                    SELECT 
                        buzon as username,
                        buzon as name,
                        total_expedientes as count,
                        egresados_efectivos,
                        egresados_no_efectivos,
                        pendientes_actividad
                    FROM public.mv_secgdu_buzones_resumen
                    ORDER BY total_expedientes DESC
                """
                result = conn.execute(text(sql))
                rows = [dict(r._mapping) for r in result.fetchall()]
                for r in rows:
                    r["expedientes"] = []
                return rows
        except Exception as e:
            logger.error(f"Error en get_gerencia_buzones (secgdu_todos): {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    if gerencia_clean == 'analisis_archivo':
        try:
            with engine.connect() as conn:
                sql = """
                    SELECT 
                        up.id_expediente, 
                        ext.expediente, 
                        up.fecha_ultimo_pase as fecha_primer_ingreso_gerencia, 
                        up.fecha_ultimo_pase as fecha_recepcion_analista, 
                        (CURRENT_DATE - up.fecha_ultimo_pase::date) as dias_en_poder_actual, 
                        up.destinatario_actual as analista, 
                        up.destinatario_actual as analista_nombre, 
                        ext.trata, 
                        ext.fecha_creacion,
                        ext.descripcion_trata, 
                        ext.descripcion, 
                        ext.estado as estado_expediente,
                        (CURRENT_DATE - up.fecha_ultimo_pase::date) as dias_en_gerencia,
                        'EGRESADO' as ubicacion
                    FROM mv_ultimo_pase up
                    JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = up.id_expediente
                    WHERE up.destinatario_actual IN (
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
                    )
                """
                result = conn.execute(text(sql))
                rows = [dict(r._mapping) for r in result.fetchall()]
                
                ids_by_gerencia = defaultdict(list)
                resolved_locations = {}
                trata_overrides = {
                    "MDUG3001A": "etapa_proyecto",
                    "MDUG0104A": "etapa_proyecto",
                    "MDUG1501J": "etapa_proyecto",
                    "MDUG0142A": "etapa_proyecto",
                    "MDUG4003A": "etapa_proyecto"
                }
                for r in rows:
                    id_exp = r["id_expediente"]
                    trata = r["trata"]
                    trata_upper = trata.strip().upper() if trata else ""
                    ger = None
                    if trata_upper in trata_overrides:
                        ger = trata_overrides[trata_upper]
                    else:
                        for g, config in TRAMITES_CONFIG.items():
                            if trata_upper in config:
                                ger = g
                                break
                    if ger:
                        ids_by_gerencia[ger].append(id_exp)
                    else:
                        resolved_locations[id_exp] = "FUERA DE TABLERO"

                for ger, ids in ids_by_gerencia.items():
                    if not ids:
                        continue
                    try:
                        sp_res = conn.execute(text(f"SELECT id_expediente FROM mv_{ger}_stock_propio WHERE id_expediente IN :ids"), {"ids": tuple(ids)}).fetchall()
                        for s_row in sp_res:
                            resolved_locations[s_row[0]] = "STOCK PROPIO"
                    except Exception:
                        pass
                    try:
                        sub_res = conn.execute(text(f"SELECT id_expediente FROM mv_{ger}_subsanaciones WHERE id_expediente IN :ids"), {"ids": tuple(ids)}).fetchall()
                        for s_row in sub_res:
                            resolved_locations[s_row[0]] = "SUBSANACION"
                    except Exception:
                        pass
                    try:
                        sp_int = conn.execute(text(f"SELECT id_expediente FROM mv_{ger}_intervenciones_stock WHERE id_expediente IN :ids"), {"ids": tuple(ids)}).fetchall()
                        for s_row in sp_int:
                            if s_row[0] not in resolved_locations:
                                resolved_locations[s_row[0]] = "STOCK PROPIO (INTERVENCION)"
                    except Exception:
                        pass
                    try:
                        sub_int = conn.execute(text(f"SELECT id_expediente FROM mv_{ger}_intervenciones_subs WHERE id_expediente IN :ids"), {"ids": tuple(ids)}).fetchall()
                        for s_row in sub_int:
                            if s_row[0] not in resolved_locations:
                                resolved_locations[s_row[0]] = "SUBSANACION (INTERVENCION)"
                    except Exception:
                        pass
                    try:
                        egr_ef = conn.execute(text(f"SELECT id_expediente FROM mv_{ger}_gedos_egreso WHERE id_expediente IN :ids"), {"ids": tuple(ids)}).fetchall()
                        for s_row in egr_ef:
                            resolved_locations[s_row[0]] = "EGRESADO"
                    except Exception:
                        pass
                    try:
                        egr_ne = conn.execute(text(f"SELECT id_expediente FROM mv_{ger}_egresos_no_efectivos WHERE id_expediente IN :ids"), {"ids": tuple(ids)}).fetchall()
                        for s_row in egr_ne:
                            resolved_locations[s_row[0]] = "EGRESADO (NO EFECTIVO)"
                    except Exception:
                        pass

                last_pase_motivos = {}
                try:
                    all_ids = [r["id_expediente"] for r in rows]
                    if all_ids:
                        motivos_res = conn.execute(text("""
                            SELECT DISTINCT ON (id_expediente) id_expediente, motivo
                            FROM mvw_ee_pases_secgdu
                            WHERE id_expediente IN :ids
                            ORDER BY id_expediente, fecha DESC
                        """), {"ids": tuple(all_ids)}).fetchall()
                        for m_row in motivos_res:
                            last_pase_motivos[m_row[0]] = m_row[1] or "Sin Motivo"
                except Exception as e:
                    logger.error(f"Error querying last pase motivos: {e}")

                archive_mailboxes = {
                    'ARCHIVODGTAL', 'DGSOCAI-ARCHIVO', 'MGEYA-ARCHIVO', 'PG-ARCHIVO',
                    'SECGDU-ARCHIVODESPACHO', 'SECLYT-ARCHIVO', 'SSGDU-ARCHIVODESPACHO', 'SSGU-ARCHIVODESPACHO',
                    'DGROC-ARCHIVO', 'DGROC-OBSOBRAPREARCHIVO'
                }
                
                allowed_mailboxes = None
                try:
                    res_user = conn.execute(text("SELECT buzones FROM public.cfg_buzones_analisis_acceso WHERE tipo_sujeto = 'usuario' AND nombre_sujeto = :n"), {"n": current_user.username}).fetchone()
                    if res_user:
                        allowed_mailboxes = set(res_user[0])
                    else:
                        res_role = conn.execute(text("SELECT buzones FROM public.cfg_buzones_analisis_acceso WHERE tipo_sujeto = 'rol' AND nombre_sujeto = :r"), {"r": current_user.role}).fetchone()
                        if res_role:
                            allowed_mailboxes = set(res_role[0])
                except Exception as db_err:
                    logger.error(f"Error checking allowed mailboxes: {db_err}")

                by_analyst = {}
                for r in rows:
                    username = r["analista"] or "SIN_ASIGNAR"
                    if allowed_mailboxes is not None and username not in allowed_mailboxes:
                        continue
                        
                    name = r["analista_nombre"] or "Sin Asignar"
                    
                    id_exp = r["id_expediente"]
                    if id_exp in resolved_locations:
                        ubic = resolved_locations[id_exp]
                    elif r["analista"] in archive_mailboxes:
                        ubic = "EGRESADO"
                    else:
                        ubic = "STOCK PROPIO"

                    fecha_ing = r["fecha_primer_ingreso_gerencia"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_primer_ingreso_gerencia"] and hasattr(r["fecha_primer_ingreso_gerencia"], "strftime") else (str(r["fecha_primer_ingreso_gerencia"])[:19] if r["fecha_primer_ingreso_gerencia"] else None)
                    fecha_pase = r["fecha_recepcion_analista"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_recepcion_analista"] and hasattr(r["fecha_recepcion_analista"], "strftime") else (str(r["fecha_recepcion_analista"])[:19] if r["fecha_recepcion_analista"] else None)
                    caratula = r["fecha_creacion"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_creacion"] and hasattr(r["fecha_creacion"], "strftime") else (str(r["fecha_creacion"])[:19] if r["fecha_creacion"] else None)
                    
                    exp_item = {
                        "id_expediente": r["id_expediente"],
                        "expediente": r["expediente"],
                        "fecha_ing": fecha_ing,
                        "fecha_ultimo_pase": fecha_pase,
                        "dias": r["dias_en_poder_actual"] if r["dias_en_poder_actual"] is not None else 0,
                        "trata": r["trata"],
                        "caratula": caratula,
                        "descripcion_trata": r["descripcion_trata"] or r["descripcion"] or "S/D",
                        "estado_expediente": r["estado_expediente"] or "S/D",
                        "dias_en_gerencia": r["dias_en_gerencia"] if r["dias_en_gerencia"] is not None else 0,
                        "estado_tablero": ubic,
                        "trata_en_tablero": (ubic != "FUERA DE TABLERO"),
                        "motivo_pase": last_pase_motivos.get(r["id_expediente"], "Sin Motivo")
                    }
                    
                    if username not in by_analyst:
                        by_analyst[username] = {
                            "username": username,
                            "name": name,
                            "count": 0,
                            "expedientes": []
                        }
                    by_analyst[username]["expedientes"].append(exp_item)
                    by_analyst[username]["count"] += 1
                
                requested_mailboxes = [
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
                ]
                for mb in requested_mailboxes:
                    if allowed_mailboxes is not None and mb not in allowed_mailboxes:
                        continue
                    if mb not in by_analyst:
                        by_analyst[mb] = {
                            "username": mb,
                            "name": mb,
                            "count": 0,
                            "expedientes": []
                        }
                return list(by_analyst.values())
        except Exception as e:
            logger.error(f"Error en get_gerencia_buzones (analisis_archivo): {e}")
            raise HTTPException(status_code=500, detail=str(e))

    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
        
    try:
        with engine.connect() as conn:
            sql = f"""
                SELECT 
                    s.id_expediente, 
                    s.expediente, 
                    s.fecha_primer_ingreso_gerencia, 
                    s.fecha_recepcion_analista, 
                    s.dias_en_poder_actual, 
                    s.analista, 
                    COALESCE(du.apellido_nombre, s.analista) as analista_nombre, 
                    s.trata, 
                    ext.fecha_creacion,
                    COALESCE(
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE trata_reporte = s.trata AND gerencia = :g LIMIT 1),
                        (SELECT descripcion_trata FROM cfg_gestion_metas WHERE s.trata = ANY(tratas_incluidas) AND gerencia = :g LIMIT 1),
                        ext.descripcion_trata
                    ) as descripcion_trata, 
                    ext.descripcion, 
                    ext.estado as estado_expediente,
                    (CURRENT_DATE - s.fecha_primer_ingreso_gerencia::date) as dias_en_gerencia,
                    s.ubicacion
                FROM (
                    SELECT id_expediente, expediente, fecha_primer_ingreso_gerencia, fecha_recepcion_analista, dias_en_poder_actual, analista, trata, 'STOCK PROPIO' as ubicacion
                    FROM mv_{gerencia_clean}_stock_propio
                    UNION ALL
                    SELECT id_expediente, expediente, fecha_primer_ingreso_gerencia, fecha_recepcion_analista, dias_en_poder_actual, analista, trata, 'INTERVENCION' as ubicacion
                    FROM mv_{gerencia_clean}_intervenciones_stock
                ) s
                LEFT JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = s.id_expediente
                LEFT JOIN datos_usuario du ON s.analista = du.usuario
            """
            result = conn.execute(text(sql), {"g": gerencia_clean})
            rows = [dict(r._mapping) for r in result.fetchall()]
            
            by_analyst = {}
            for r in rows:
                username = r["analista"] or "SIN_ASIGNAR"
                name = r["analista_nombre"] or "Sin Asignar"
                
                fecha_ing = r["fecha_primer_ingreso_gerencia"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_primer_ingreso_gerencia"] and hasattr(r["fecha_primer_ingreso_gerencia"], "strftime") else (str(r["fecha_primer_ingreso_gerencia"])[:19] if r["fecha_primer_ingreso_gerencia"] else None)
                fecha_pase = r["fecha_recepcion_analista"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_recepcion_analista"] and hasattr(r["fecha_recepcion_analista"], "strftime") else (str(r["fecha_recepcion_analista"])[:19] if r["fecha_recepcion_analista"] else None)
                caratula = r["fecha_creacion"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_creacion"] and hasattr(r["fecha_creacion"], "strftime") else (str(r["fecha_creacion"])[:19] if r["fecha_creacion"] else None)
                
                exp_item = {
                    "id_expediente": r["id_expediente"],
                    "expediente": r["expediente"],
                    "fecha_ing": fecha_ing,
                    "fecha_ultimo_pase": fecha_pase,
                    "dias": r["dias_en_poder_actual"] if r["dias_en_poder_actual"] is not None else 0,
                    "trata": r["trata"],
                    "caratula": caratula,
                    "descripcion_trata": r["descripcion_trata"] or r["descripcion"] or "S/D",
                    "estado_expediente": r["estado_expediente"] or "S/D",
                    "dias_en_gerencia": r["dias_en_gerencia"] if r["dias_en_gerencia"] is not None else 0,
                    "estado_tablero": r["ubicacion"]
                }
                
                if username not in by_analyst:
                    by_analyst[username] = {
                        "username": username,
                        "name": name,
                        "count": 0,
                        "expedientes": []
                    }
                by_analyst[username]["expedientes"].append(exp_item)
                by_analyst[username]["count"] += 1
                
            return sorted(list(by_analyst.values()), key=lambda x: x["count"], reverse=True)
    except Exception as e:
        logger.error(f"Error fetching gerencia buzones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/secgdu/buzones/{username}/expedientes")
async def get_secgdu_buzon_expedientes(username: str, current_user: User = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            sql = """
                SELECT 
                    up.id_expediente, 
                    ext.expediente, 
                    up.fecha_ultimo_pase as fecha_recepcion_analista,
                    up.fecha_ultimo_pase as fecha_primer_ingreso_gerencia, 
                    (CURRENT_DATE - up.fecha_ultimo_pase::date) as dias_en_poder_actual, 
                    ext.trata, 
                    ext.fecha_creacion,
                    ext.descripcion_trata, 
                    ext.descripcion, 
                    ext.estado as estado_expediente,
                    (CURRENT_DATE - up.fecha_ultimo_pase::date) as dias_en_gerencia
                FROM mv_ultimo_pase up
                JOIN mvw_expedientes_tratas_secgdu ext ON ext.id_expediente = up.id_expediente
                WHERE up.destinatario_actual = :u
            """
            result = conn.execute(text(sql), {"u": username})
            rows = [dict(r._mapping) for r in result.fetchall()]
            
            rules_sql = """
                SELECT DISTINCT 
                    UNNEST(tratas_incluidas) AS trata,
                    UNNEST(acronimos_egreso) AS acronimo,
                    firmantes_egreso
                FROM public.cfg_gestion_metas
                WHERE trata_reporte <> 'INTERVENCIONES'
            """
            rules_res = conn.execute(text(rules_sql)).fetchall()
            rules_by_trata = {}
            for r_trata, r_acro, r_firm in rules_res:
                if r_trata not in rules_by_trata:
                    rules_by_trata[r_trata] = []
                rules_by_trata[r_trata].append((r_acro, r_firm))

            ids = [r["id_expediente"] for r in rows]
            gedos_by_exp = {}
            if ids:
                gedo_sql = """
                    SELECT id_expediente, acronimo, usuario_creador
                    FROM public.mvw_datos_gedo_secgdu
                    WHERE id_expediente IN :ids
                """
                gedo_res = conn.execute(text(gedo_sql), {"ids": tuple(ids)}).fetchall()
                for g_id, g_acro, g_user in gedo_res:
                    if g_id not in gedos_by_exp:
                        gedos_by_exp[g_id] = []
                    gedos_by_exp[g_id].append((g_acro, g_user))

            pending_activities = set()
            if ids:
                act_sql = """
                    SELECT DISTINCT ON (id_expediente) id_expediente, estado
                    FROM public.mvw_ee_actividades_secgdu
                    WHERE id_expediente IN :ids
                    ORDER BY id_expediente, fecha_alta DESC
                """
                act_res = conn.execute(text(act_sql), {"ids": tuple(ids)}).fetchall()
                for a_id, a_est in act_res:
                    if a_est == 'PENDIENTE':
                        pending_activities.add(a_id)

            last_pase_motivos = {}
            if ids:
                motivos_res = conn.execute(text("""
                    SELECT DISTINCT ON (id_expediente) id_expediente, motivo
                    FROM mvw_ee_pases_secgdu
                    WHERE id_expediente IN :ids
                    ORDER BY id_expediente, fecha DESC
                """), {"ids": tuple(ids)}).fetchall()
                for m_row in motivos_res:
                    last_pase_motivos[m_row[0]] = m_row[1] or "Sin Motivo"

            expedientes = []
            for r in rows:
                id_exp = r["id_expediente"]
                trata = r["trata"]
                
                is_efectivo = False
                if trata in rules_by_trata and id_exp in gedos_by_exp:
                    for r_acro, r_firm in rules_by_trata[trata]:
                        for g_acro, g_user in gedos_by_exp[id_exp]:
                            if g_acro == r_acro:
                                if not r_firm or g_user in r_firm:
                                    is_efectivo = True
                                    break
                        if is_efectivo:
                            break
                
                is_no_efectivo = (r["estado_expediente"] == 'Guarda Temporal' and not is_efectivo)
                
                if is_efectivo:
                    ubic = "EGRESADO"
                elif is_no_efectivo:
                    ubic = "EGRESADO (NO EFECTIVO)"
                elif id_exp in pending_activities:
                    ubic = "PENDIENTE DE ACTIVIDAD"
                else:
                    ubic = "EN STOCK"
                
                fecha_ing = r["fecha_primer_ingreso_gerencia"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_primer_ingreso_gerencia"] and hasattr(r["fecha_primer_ingreso_gerencia"], "strftime") else (str(r["fecha_primer_ingreso_gerencia"])[:19] if r["fecha_primer_ingreso_gerencia"] else None)
                fecha_pase = r["fecha_recepcion_analista"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_recepcion_analista"] and hasattr(r["fecha_recepcion_analista"], "strftime") else (str(r["fecha_recepcion_analista"])[:19] if r["fecha_recepcion_analista"] else None)
                caratula = r["fecha_creacion"].strftime("%Y-%m-%d %H:%M:%S") if r["fecha_creacion"] and hasattr(r["fecha_creacion"], "strftime") else (str(r["fecha_creacion"])[:19] if r["fecha_creacion"] else None)
                
                exp_item = {
                    "id_expediente": id_exp,
                    "expediente": r["expediente"],
                    "fecha_ing": fecha_ing,
                    "fecha_ultimo_pase": fecha_pase,
                    "dias": r["dias_en_poder_actual"] if r["dias_en_poder_actual"] is not None else 0,
                    "trata": trata,
                    "caratula": caratula,
                    "descripcion_trata": r["descripcion_trata"] or r["descripcion"] or "S/D",
                    "estado_expediente": r["estado_expediente"] or "S/D",
                    "dias_en_gerencia": r["dias_en_gerencia"] if r["dias_en_gerencia"] is not None else 0,
                    "estado_tablero": ubic,
                    "trata_en_tablero": True,
                    "motivo_pase": last_pase_motivos.get(id_exp, "Sin Motivo")
                }
                expedientes.append(exp_item)
                
            return expedientes
    except Exception as e:
        logger.error(f"Error en get_secgdu_buzon_expedientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/{gerencia}/intervenciones/detalle")
async def get_intervenciones_detalle(gerencia: str, current_user: User = Depends(get_current_user)):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
    
    try:
        with engine.connect() as conn:
            if gerencia_clean in ['instalaciones', 'morfologia', 'contable', 'etapa_proyecto', 'catastro', 'aph', 'usos', 'regularizacion', 'aviso_obra']:
                sql = f"""
                    SELECT trata, descripcion_trata as detalle, dias_en_poder_actual as dias_stock
                    FROM mv_{gerencia_clean}_intervenciones_stock
                """
                result = conn.execute(text(sql))
            else:
                cfg_query = text("""
                    SELECT buzones_ingreso, analistas_oficiales 
                    FROM cfg_gestion_metas 
                    WHERE gerencia = :g AND trata_reporte = 'INTERVENCIONES'
                """)
                cfg_res = conn.execute(cfg_query, {"g": gerencia_clean}).fetchone()
                
                if not cfg_res: return []
                
                sector_whitelist = (cfg_res[0] or []) + (cfg_res[1] or [])
                if not sector_whitelist: return []

                sql = """
                    SELECT trata, descripcion as detalle, dias_ultimo_movimiento as dias_stock
                    FROM mvw_stock_actual_detalle
                    WHERE is_subs = 0 
                      AND gerencia = :g
                      AND trata_reporte = 'INTERVENCIONES'
                      AND analista_actual = ANY(:whitelist)
                """
                result = conn.execute(text(sql), {"g": gerencia_clean, "whitelist": sector_whitelist})
            
            rows = [dict(r._mapping) for r in result.fetchall()]
            if not rows: return []
            df = pd.DataFrame(rows)

            def get_range(d):
                if d < 15: return "Menos de 15 dias"
                if d <= 30: return "15 a 30 dias"
                if d <= 45: return "30 a 45 dias"
                if d <= 60: return "45 a 60 dias"
                if d <= 75: return "60 a 75 dias"
                if d <= 90: return "75 a 90 dias"
                return "Mas de 90 dias"

            df['rango'] = df['dias_stock'].apply(get_range)
            
            trata_nombres = df.groupby('trata')['detalle'].first().to_dict()
            
            pivot = df.groupby(['trata', 'rango']).size().unstack(fill_value=0)
            
            ranges = ["Menos de 15 dias", "15 a 30 dias", "30 a 45 dias", "45 a 60 dias", "60 a 75 dias", "75 a 90 dias", "Mas de 90 dias"]
            for r in ranges:
                if r not in pivot.columns: pivot[r] = 0
            
            pivot['TOTAL'] = pivot.sum(axis=1)
            pivot = pivot.reset_index()
            
            pivot['detalle'] = pivot['trata'].map(trata_nombres)
            
            return pivot.sort_values(by='TOTAL', ascending=False).to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error en intervenciones detalle: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/{gerencia}/tramite/{trata}/detalle_periodo")
async def get_tramite_detalle_periodo(
    gerencia: str, 
    trata: str, 
    periodo: str, 
    metrica: str, 
    current_user: User = Depends(get_current_user)
):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
        
    if gerencia_clean not in TRAMITES_CONFIG:
        raise HTTPException(status_code=404, detail="Gerencia no encontrada.")
        
    periodo_norm = periodo
    if '-' in periodo:
        parts = periodo.split('-')
        if len(parts) == 2:
            try:
                year = int(parts[0])
                month = int(parts[1])
                periodo_norm = f"{year:04d}-{month:02d}"
            except ValueError:
                pass
    try:
        with engine.connect() as conn:
            trata_codes = list(TRAMITES_CONFIG[gerencia_clean].keys())
            tratas_oficiales = [t for t in trata_codes if t != 'INTERVENCIONES']
            is_official = trata in tratas_oficiales
            
            # Determine if we should query live stock or historical stock
            from datetime import datetime
            current_month_str = datetime.now().strftime('%Y-%m')
            is_current_month = (periodo_norm == current_month_str)
            
            import calendar
            try:
                p_parts = periodo_norm.split('-')
                p_year = int(p_parts[0])
                p_month = int(p_parts[1])
                p_last_day = calendar.monthrange(p_year, p_month)[1]
                cut_off_date = f"{p_year:04d}-{p_month:02d}-{p_last_day:02d}"
            except Exception:
                cut_off_date = datetime.now().strftime('%Y-%m-%d')

            sql = ""
            params = {
                "periodo": periodo_norm,
                "trata": trata,
                "g": gerencia_clean,
                "cut_off_date": cut_off_date,
                "tratas_oficiales": tratas_oficiales
            }

            if metrica in ['STOCK_PROPIO', 'STOCK_SUBS', 'STOCK_TOTAL'] and not is_current_month:
                if metrica == 'STOCK_PROPIO':
                    sql = f"""
                        WITH cfg AS (
                            SELECT analistas_oficiales 
                            FROM cfg_gestion_metas 
                            WHERE gerencia = :g AND trata_reporte = 'INTERVENCIONES'
                        ),
                        destinatario_por_corte AS (
                            SELECT DISTINCT ON (u.id_expediente) 
                                u.id_expediente,
                                u.expediente,
                                u.trata,
                                u.descripcion_trata,
                                u.descripcion,
                                u.caratula,
                                u.estado_expediente,
                                u.fecha_primer_ingreso_gerencia,
                                p.destinatario AS analista,
                                p.fecha AS fecha_recepcion_analista
                            FROM mv_{gerencia_clean}_universo u
                            JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente AND CAST(p.fecha AS date) <= CAST(:cut_off_date AS date)
                            ORDER BY u.id_expediente, p.fecha DESC
                        ),
                        subsanacion_abierta AS (
                            SELECT DISTINCT ON (d.id_expediente) d.id_expediente, true AS tiene_subsanacion
                            FROM destinatario_por_corte d
                            JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = d.id_expediente 
                                                           AND a.usuario_alta = d.analista 
                                                           AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'::text 
                                                           AND CAST(a.fecha_alta AS date) <= CAST(:cut_off_date AS date) 
                                                           AND (a.fecha_cierre IS NULL OR CAST(a.fecha_cierre AS date) > CAST(:cut_off_date AS date))
                            ORDER BY d.id_expediente, a.fecha_alta DESC
                        )
                        SELECT 
                            CASE WHEN d.trata = ANY(:tratas_oficiales) THEN 'OFICIAL' ELSE 'INTERVENCION' END AS "TIPO TRAMITE",
                            d.expediente AS "EXPEDIENTE",
                            d.trata AS "TRAMITE",
                            to_char(d.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO",
                            to_char(d.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA",
                            (CAST(:cut_off_date AS date) - CAST(d.fecha_recepcion_analista AS date)) AS "DIAS EN PODER",
                            d.analista AS "ANALISTA",
                            d.descripcion_trata AS "DETALLE TRATA",
                            d.descripcion AS "DESCRIPCION",
                            d.estado_expediente AS "ESTADO"
                        FROM destinatario_por_corte d
                        CROSS JOIN cfg
                        LEFT JOIN subsanacion_abierta s ON s.id_expediente = d.id_expediente
                        WHERE d.analista = ANY(cfg.analistas_oficiales)
                          AND COALESCE(s.tiene_subsanacion, false) = false
                          AND (:trata = 'ALL' 
                               OR :trata = 'INTERVENCIONES' AND d.trata NOT IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = :g)
                               OR :trata != 'INTERVENCIONES' AND d.trata = :trata)
                        ORDER BY "DIAS EN PODER" DESC
                    """
                elif metrica == 'STOCK_SUBS':
                    sql = f"""
                        WITH cfg AS (
                            SELECT analistas_oficiales 
                            FROM cfg_gestion_metas 
                            WHERE gerencia = :g AND trata_reporte = 'INTERVENCIONES'
                        ),
                        destinatario_por_corte AS (
                            SELECT DISTINCT ON (u.id_expediente) 
                                u.id_expediente,
                                u.expediente,
                                u.trata,
                                u.descripcion_trata,
                                u.descripcion,
                                u.caratula,
                                u.estado_expediente,
                                u.fecha_primer_ingreso_gerencia,
                                p.destinatario AS analista,
                                p.fecha AS fecha_recepcion_analista
                            FROM mv_{gerencia_clean}_universo u
                            JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente AND CAST(p.fecha AS date) <= CAST(:cut_off_date AS date)
                            ORDER BY u.id_expediente, p.fecha DESC
                        ),
                        subsanacion_abierta AS (
                            SELECT DISTINCT ON (d.id_expediente) d.id_expediente, true AS tiene_subsanacion
                            FROM destinatario_por_corte d
                            JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = d.id_expediente 
                                                           AND a.usuario_alta = d.analista 
                                                           AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'::text 
                                                           AND CAST(a.fecha_alta AS date) <= CAST(:cut_off_date AS date) 
                                                           AND (a.fecha_cierre IS NULL OR CAST(a.fecha_cierre AS date) > CAST(:cut_off_date AS date))
                            ORDER BY d.id_expediente, a.fecha_alta DESC
                        )
                        SELECT 
                            CASE WHEN d.trata = ANY(:tratas_oficiales) THEN 'OFICIAL' ELSE 'INTERVENCION' END AS "TIPO TRAMITE",
                            d.expediente AS "EXPEDIENTE",
                            d.trata AS "TRAMITE",
                            to_char(d.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO",
                            to_char(d.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA",
                            (CAST(:cut_off_date AS date) - CAST(d.fecha_recepcion_analista AS date)) AS "DIAS EN PODER",
                            d.analista AS "ANALISTA",
                            d.descripcion_trata AS "DETALLE TRATA",
                            d.descripcion AS "DESCRIPCION",
                            d.estado_expediente AS "ESTADO"
                        FROM destinatario_por_corte d
                        CROSS JOIN cfg
                        JOIN subsanacion_abierta s ON s.id_expediente = d.id_expediente
                        WHERE d.analista = ANY(cfg.analistas_oficiales)
                          AND (:trata = 'ALL' 
                               OR :trata = 'INTERVENCIONES' AND d.trata NOT IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = :g)
                               OR :trata != 'INTERVENCIONES' AND d.trata = :trata)
                        ORDER BY "DIAS EN PODER" DESC
                    """
                elif metrica == 'STOCK_TOTAL':
                    sql = f"""
                        WITH cfg AS (
                            SELECT analistas_oficiales 
                            FROM cfg_gestion_metas 
                            WHERE gerencia = :g AND trata_reporte = 'INTERVENCIONES'
                        ),
                        destinatario_por_corte AS (
                            SELECT DISTINCT ON (u.id_expediente) 
                                u.id_expediente,
                                u.expediente,
                                u.trata,
                                u.descripcion_trata,
                                u.descripcion,
                                u.caratula,
                                u.estado_expediente,
                                u.fecha_primer_ingreso_gerencia,
                                p.destinatario AS analista,
                                p.fecha AS fecha_recepcion_analista
                            FROM mv_{gerencia_clean}_universo u
                            JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente AND CAST(p.fecha AS date) <= CAST(:cut_off_date AS date)
                            ORDER BY u.id_expediente, p.fecha DESC
                        ),
                        subsanacion_abierta AS (
                            SELECT DISTINCT ON (d.id_expediente) d.id_expediente, true AS tiene_subsanacion
                            FROM destinatario_por_corte d
                            JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = d.id_expediente 
                                                           AND a.usuario_alta = d.analista 
                                                           AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'::text 
                                                           AND CAST(a.fecha_alta AS date) <= CAST(:cut_off_date AS date) 
                                                           AND (a.fecha_cierre IS NULL OR CAST(a.fecha_cierre AS date) > CAST(:cut_off_date AS date))
                            ORDER BY d.id_expediente, a.fecha_alta DESC
                        )
                        SELECT 
                            CASE WHEN s.tiene_subsanacion = true THEN 'SUBSANACION' ELSE 'STOCK PROPIO' END AS "TIPO STOCK",
                            d.expediente AS "EXPEDIENTE",
                            d.trata AS "TRAMITE",
                            to_char(d.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO",
                            to_char(d.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA",
                            (CAST(:cut_off_date AS date) - CAST(d.fecha_recepcion_analista AS date)) AS "DIAS EN PODER",
                            d.analista AS "ANALISTA",
                            d.descripcion_trata AS "DETALLE TRATA",
                            d.estado_expediente AS "ESTADO"
                        FROM destinatario_por_corte d
                        CROSS JOIN cfg
                        LEFT JOIN subsanacion_abierta s ON s.id_expediente = d.id_expediente
                        WHERE d.analista = ANY(cfg.analistas_oficiales)
                          AND (:trata = 'ALL' 
                               OR :trata = 'INTERVENCIONES' AND d.trata NOT IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = :g)
                               OR :trata != 'INTERVENCIONES' AND d.trata = :trata)
                        ORDER BY "DIAS EN PODER" DESC
                    """
            else:
                if trata == 'ALL':
                    if metrica == 'ING':
                        sql = f"""
                            SELECT 
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_ingreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                                t.buzon AS "BUZON INGRESO",
                                e.usuario_modificador AS "ANALISTA",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.descripcion AS "DESCRIPCION", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_ingresos_eventos t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_ingreso, 'YYYY-MM') = :periodo
                            ORDER BY t.fecha_ingreso DESC
                        """
                    elif metrica == 'EGR_EF':
                        interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"
                        if gerencia_clean != 'contable':
                            sql = f"""
                                SELECT 
                                    'OFICIAL' AS "TIPO TRAMITE",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.documento_egreso AS "DOCUMENTO EGRESO/DESTINO", 
                                    t.acronimo_egreso AS "ACRONIMO EGRESO", 
                                    t.usuario_egreso AS "USUARIO EGRESO",
                                    e.descripcion_trata AS "DETALLE TRATA", 
                                    e.estado AS "ESTADO"
                                FROM mv_{gerencia_clean}_gedos_egreso t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                UNION ALL
                                SELECT 
                                    'INTERVENCION' AS "TIPO TRAMITE",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.destino_externo AS "DOCUMENTO EGRESO/DESTINO",
                                    '' AS "ACRONIMO EGRESO",
                                    t.usuario_que_envia AS "USUARIO EGRESO",
                                    t.descripcion_trata AS "DETALLE TRATA",
                                    e.estado AS "ESTADO"
                                FROM {interv_egr_table} t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                ORDER BY 4 DESC
                            """
                        else:
                            sql = f"""
                                SELECT 
                                    'OFICIAL' AS "TIPO TRAMITE",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.documento_egreso AS "DOCUMENTO EGRESO/DESTINO", 
                                    t.acronimo_egreso AS "ACRONIMO EGRESO", 
                                    t.usuario_egreso AS "USUARIO EGRESO",
                                    e.descripcion_trata AS "DETALLE TRATA", 
                                    e.estado AS "ESTADO"
                                FROM mv_{gerencia_clean}_gedos_egreso t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                UNION ALL
                                SELECT 
                                    'INTERVENCION' AS "TIPO TRAMITE",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.destino_actual AS "DOCUMENTO EGRESO/DESTINO",
                                    '' AS "ACRONIMO EGRESO",
                                    '' AS "USUARIO EGRESO",
                                    t.descripcion_trata AS "DETALLE TRATA",
                                    e.estado AS "ESTADO"
                                FROM {interv_egr_table} t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                ORDER BY 4 DESC
                            """
                    elif metrica == 'EGR_NE':
                        sql = f"""
                            SELECT 
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_ultimo_movimiento, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA ULTIMO PASO",
                                t.poseedor_actual AS "DESTINATARIO/BUZON",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.descripcion AS "DESCRIPCION", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_egresos_no_efectivos t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_ultimo_movimiento, 'YYYY-MM') = :periodo
                            ORDER BY t.fecha_ultimo_movimiento DESC
                        """
                    elif metrica == 'EGR_TOT':
                        interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"
                        if gerencia_clean != 'contable':
                            sql = f"""
                                SELECT 
                                    'EFECTIVO' AS "TIPO EGRESO",
                                    'OFICIAL' AS "TIPO TRAMITE",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.documento_egreso AS "DETALLE EGRESO (DOC/BUZON)",
                                    e.descripcion_trata AS "DETALLE TRATA", 
                                    e.estado AS "ESTADO"
                                FROM mv_{gerencia_clean}_gedos_egreso t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                UNION ALL
                                SELECT 
                                    'EFECTIVO' AS "TIPO EGRESO",
                                    'INTERVENCION' AS "TIPO TRAMITE",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.destino_externo AS "DETALLE EGRESO (DOC/BUZON)",
                                    t.descripcion_trata AS "DETALLE TRATA", 
                                    e.estado AS "ESTADO"
                                FROM {interv_egr_table} t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                UNION ALL
                                SELECT 
                                    'NO EFECTIVO' AS "TIPO EGRESO",
                                    CASE WHEN t.trata = ANY(:tratas_oficiales) THEN 'OFICIAL' ELSE 'INTERVENCION' END AS "TIPO TRAMITE",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_ultimo_movimiento, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.poseedor_actual AS "DETALLE EGRESO (DOC/BUZON)",
                                    e.descripcion_trata AS "DETALLE TRATA", 
                                    e.estado AS "ESTADO"
                                FROM mv_{gerencia_clean}_egresos_no_efectivos t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_ultimo_movimiento, 'YYYY-MM') = :periodo
                                ORDER BY 5 DESC
                            """
                        else:
                            sql = f"""
                                SELECT 
                                    'EFECTIVO' AS "TIPO EGRESO",
                                    'OFICIAL' AS "TIPO TRAMITE",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.documento_egreso AS "DETALLE EGRESO (DOC/BUZON)",
                                    e.descripcion_trata AS "DETALLE TRATA", 
                                    e.estado AS "ESTADO"
                                FROM mv_{gerencia_clean}_gedos_egreso t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                UNION ALL
                                SELECT 
                                    'EFECTIVO' AS "TIPO EGRESO",
                                    'INTERVENCION' AS "TIPO TRAMITE",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.destino_actual AS "DETALLE EGRESO (DOC/BUZON)",
                                    t.descripcion_trata AS "DETALLE TRATA", 
                                    e.estado AS "ESTADO"
                                FROM {interv_egr_table} t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                UNION ALL
                                SELECT 
                                    'NO EFECTIVO' AS "TIPO EGRESO",
                                    CASE WHEN t.trata = ANY(:tratas_oficiales) THEN 'OFICIAL' ELSE 'INTERVENCION' END AS "TIPO TRAMITE",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_ultimo_movimiento, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.poseedor_actual AS "DETALLE EGRESO (DOC/BUZON)",
                                    e.descripcion_trata AS "DETALLE TRATA", 
                                    e.estado AS "ESTADO"
                                FROM mv_{gerencia_clean}_egresos_no_efectivos t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_ultimo_movimiento, 'YYYY-MM') = :periodo
                                ORDER BY 5 DESC
                            """
                        params["tratas_oficiales"] = trata_codes
                    elif metrica == 'STOCK_PROPIO':
                        sql = f"""
                            SELECT 
                                'OFICIAL' AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                                to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                                t.dias_en_poder_actual AS "DIAS EN PODER", 
                                t.analista AS "ANALISTA",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.descripcion AS "DESCRIPCION", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_stock_propio t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            UNION ALL
                            SELECT 
                                'INTERVENCION' AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                                to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                                t.dias_en_poder_actual AS "DIAS EN PODER", 
                                t.analista AS "ANALISTA",
                                t.descripcion_trata AS "DETALLE TRATA", 
                                e.descripcion AS "DESCRIPCION", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_intervenciones_stock t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            ORDER BY "DIAS EN PODER" DESC
                        """
                    elif metrica == 'STOCK_SUBS':
                        sql = f"""
                            SELECT 
                                'OFICIAL' AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                                to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                                t.dias_en_poder_actual AS "DIAS EN PODER", 
                                t.analista AS "ANALISTA",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.descripcion AS "DESCRIPCION", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_subsanaciones t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            UNION ALL
                            SELECT 
                                'INTERVENCION' AS "TIPO TRAMITE",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                                to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                                t.dias_en_poder_actual AS "DIAS EN PODER", 
                                t.analista AS "ANALISTA",
                                t.descripcion_trata AS "DETALLE TRATA", 
                                e.descripcion AS "DESCRIPCION", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_intervenciones_subs t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            ORDER BY "DIAS EN PODER" DESC
                        """
                    elif metrica == 'STOCK_TOTAL':
                        stock_table = f"mv_{gerencia_clean}_stock_propio"
                        subs_table = f"mv_{gerencia_clean}_subsanaciones"
                        sql = f"""
                            SELECT 
                                'STOCK PROPIO' AS "TIPO STOCK",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                                to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                                t.dias_en_poder_actual AS "DIAS EN PODER", 
                                t.analista AS "ANALISTA",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM {stock_table} t
                            LEFT JOIN vw_expedientes_maestro e ON e.id_expediente = t.id_expediente
                            UNION ALL
                            SELECT 
                                'SUBSANACION' AS "TIPO STOCK",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                                to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                                t.dias_en_poder_actual AS "DIAS EN PODER", 
                                t.analista AS "ANALISTA",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM {subs_table} t
                            LEFT JOIN vw_expedientes_maestro e ON e.id_expediente = t.id_expediente
                            ORDER BY 6 DESC
                        """
                else:
                    if metrica == 'ING':
                        sql = f"""
                            SELECT 
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_ingreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                                t.buzon AS "BUZON INGRESO",
                                e.usuario_modificador AS "ANALISTA",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.descripcion AS "DESCRIPCION", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_ingresos_eventos t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_ingreso, 'YYYY-MM') = :periodo
                              AND (:trata = 'INTERVENCIONES' AND t.trata NOT IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = :g)
                                   OR :trata != 'INTERVENCIONES' AND t.trata = :trata)
                            ORDER BY t.fecha_ingreso DESC
                        """
                    elif metrica == 'EGR_EF':
                        if is_official:
                            sql = f"""
                                SELECT 
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.documento_egreso AS "DOCUMENTO EGRESO", 
                                    t.acronimo_egreso AS "ACRONIMO EGRESO", 
                                    t.usuario_egreso AS "USUARIO EGRESO",
                                    e.descripcion_trata AS "DETALLE TRATA", 
                                    e.descripcion AS "DESCRIPCION", 
                                    e.estado AS "ESTADO"
                                FROM mv_{gerencia_clean}_gedos_egreso t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                  AND t.trata = :trata
                                ORDER BY t.fecha_egreso DESC
                            """
                        else:
                            interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"
                            if gerencia_clean != 'contable':
                                sql = f"""
                                    SELECT 
                                        t.expediente AS "EXPEDIENTE", 
                                        t.trata AS "TRAMITE", 
                                        to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                        t.usuario_que_envia AS "USUARIO QUE ENVIA", 
                                        t.destino_externo AS "DESTINO EXTERNO",
                                        t.descripcion_trata AS "DETALLE TRATA",
                                        e.descripcion AS "DESCRIPCION", 
                                        e.estado AS "ESTADO"
                                    FROM {interv_egr_table} t
                                    LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                    WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                    ORDER BY t.fecha_egreso DESC
                                """
                            else:
                                sql = f"""
                                    SELECT 
                                        t.expediente AS "EXPEDIENTE", 
                                        t.trata AS "TRAMITE", 
                                        to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                        t.destino_actual AS "DESTINO ACTUAL", 
                                        t.dias_afuera AS "DIAS AFUERA",
                                        t.descripcion_trata AS "DETALLE TRATA",
                                        e.descripcion AS "DESCRIPCION", 
                                        e.estado AS "ESTADO"
                                    FROM {interv_egr_table} t
                                    LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                    WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                    ORDER BY t.fecha_egreso DESC
                                """
                    elif metrica == 'EGR_NE':
                        sql = f"""
                            SELECT 
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_ultimo_movimiento, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA ULTIMO PASO",
                                t.poseedor_actual AS "DESTINATARIO/BUZON",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.descripcion AS "DESCRIPCION", 
                                e.estado AS "ESTADO"
                            FROM mv_{gerencia_clean}_egresos_no_efectivos t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE to_char(t.fecha_ultimo_movimiento, 'YYYY-MM') = :periodo
                              AND (:trata = 'INTERVENCIONES' AND t.trata NOT IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = :g)
                                   OR :trata != 'INTERVENCIONES' AND t.trata = :trata)
                            ORDER BY t.fecha_ultimo_movimiento DESC
                        """
                    elif metrica == 'EGR_TOT':
                        if is_official:
                            sql = f"""
                                SELECT 
                                    'EFECTIVO' AS "TIPO EGRESO",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.documento_egreso AS "DOCUMENTO EGRESO",
                                    t.acronimo_egreso AS "ACRONIMO EGRESO",
                                    t.documento_egreso AS "DETALLE EGRESO (DOC/BUZON)",
                                    e.descripcion_trata AS "DETALLE TRATA", 
                                    e.estado AS "ESTADO"
                                FROM mv_{gerencia_clean}_gedos_egreso t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                  AND t.trata = :trata
                                UNION ALL
                                SELECT 
                                    'NO EFECTIVO' AS "TIPO EGRESO",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_ultimo_movimiento, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    '' AS "DOCUMENTO EGRESO",
                                    '' AS "ACRONIMO EGRESO",
                                    t.poseedor_actual AS "DETALLE EGRESO (DOC/BUZON)",
                                    e.descripcion_trata AS "DETALLE TRATA", 
                                    e.estado AS "ESTADO"
                                FROM mv_{gerencia_clean}_egresos_no_efectivos t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_ultimo_movimiento, 'YYYY-MM') = :periodo
                                  AND t.trata = :trata
                                ORDER BY 4 DESC
                            """
                        else:
                            interv_egr_table = f"mv_{gerencia_clean}_interv_egresos_eventos" if gerencia_clean != 'contable' else "mv_contable_intervenciones_egresadas"
                            sql = f"""
                                SELECT 
                                    'EFECTIVO' AS "TIPO EGRESO",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    t.descripcion_trata AS "DETALLE TRATA", 
                                    e.estado AS "ESTADO"
                                FROM {interv_egr_table} t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_egreso, 'YYYY-MM') = :periodo
                                UNION ALL
                                SELECT 
                                    'NO EFECTIVO' AS "TIPO EGRESO",
                                    t.expediente AS "EXPEDIENTE", 
                                    t.trata AS "TRAMITE", 
                                    to_char(t.fecha_ultimo_movimiento, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                                    e.descripcion_trata AS "DETALLE TRATA", 
                                    e.estado AS "ESTADO"
                                FROM mv_{gerencia_clean}_egresos_no_efectivos t
                                LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                                WHERE to_char(t.fecha_ultimo_movimiento, 'YYYY-MM') = :periodo
                                  AND t.trata NOT IN (SELECT unnest(tratas_incluidas) FROM cfg_gestion_metas WHERE gerencia = :g)
                                ORDER BY 4 DESC
                            """
                    elif metrica == 'STOCK_PROPIO':
                        stock_table = f"mv_{gerencia_clean}_stock_propio" if is_official else f"mv_{gerencia_clean}_intervenciones_stock"
                        sql = f"""
                            SELECT 
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                                to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                                t.dias_en_poder_actual AS "DIAS EN PODER", 
                                t.analista AS "ANALISTA",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.descripcion AS "DESCRIPCION", 
                                e.estado AS "ESTADO"
                            FROM {stock_table} t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE (:trata = 'INTERVENCIONES' OR t.trata = :trata)
                            ORDER BY t.dias_en_poder_actual DESC
                        """
                    elif metrica == 'STOCK_SUBS':
                        stock_table = f"mv_{gerencia_clean}_subsanaciones" if is_official else f"mv_{gerencia_clean}_intervenciones_subs"
                        sql = f"""
                            SELECT 
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                                to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                                t.dias_en_poder_actual AS "DIAS EN PODER", 
                                t.analista AS "ANALISTA",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.descripcion AS "DESCRIPCION", 
                                e.estado AS "ESTADO"
                            FROM {stock_table} t
                            LEFT JOIN mvw_expedientes_tratas_secgdu e ON e.id_expediente = t.id_expediente
                            WHERE (:trata = 'INTERVENCIONES' OR t.trata = :trata)
                            ORDER BY t.dias_en_poder_actual DESC
                        """
                    elif metrica == 'STOCK_TOTAL':
                        stock_table = f"mv_{gerencia_clean}_stock_propio"
                        subs_table = f"mv_{gerencia_clean}_subsanaciones"
                        sql = f"""
                            SELECT 
                                'STOCK PROPIO' AS "TIPO STOCK",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                                to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                                t.dias_en_poder_actual AS "DIAS EN PODER", 
                                t.analista AS "ANALISTA",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM {stock_table} t
                            LEFT JOIN vw_expedientes_maestro e ON e.id_expediente = t.id_expediente
                            WHERE (:trata = 'INTERVENCIONES' OR t.trata = :trata)
                            UNION ALL
                            SELECT 
                                'SUBSANACION' AS "TIPO STOCK",
                                t.expediente AS "EXPEDIENTE", 
                                t.trata AS "TRAMITE", 
                                to_char(t.fecha_primer_ingreso_gerencia, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA INGRESO", 
                                to_char(t.fecha_recepcion_analista, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA RECEPCION ANALISTA", 
                                t.dias_en_poder_actual AS "DIAS EN PODER", 
                                t.analista AS "ANALISTA",
                                e.descripcion_trata AS "DETALLE TRATA", 
                                e.estado AS "ESTADO"
                            FROM {subs_table} t
                            LEFT JOIN vw_expedientes_maestro e ON e.id_expediente = t.id_expediente
                            WHERE (:trata = 'INTERVENCIONES' OR t.trata = :trata)
                            ORDER BY 6 DESC
                        """

            result = conn.execute(text(sql), params)
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
    except Exception as e:
        logger.error(f"Error en detalle_periodo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/cierre_mes")
async def get_cierre_mes(mes: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"), current_user: User = Depends(get_current_user)):
    if not mes:
        now = datetime.now()
        prev_m = now.month - 1
        prev_y = now.year
        if prev_m == 0:
            prev_m = 12
            prev_y -= 1
        mes = f"{prev_y}-{str(prev_m).zfill(2)}"

    _ck = f"cierre_mes_{mes}"
    hit, data = cached_response(_ck, ttl_seconds=300)
    if hit:
        return data
    try:
        try:
            parts = mes.split('-')
            year = int(parts[0])
            month = int(parts[1])
            dt_first = date(year, month, 1)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato de mes inválido. Usar YYYY-MM")

        if dt_first.month == 1:
            prev_dt = date(dt_first.year - 1, 12, 1)
        else:
            prev_dt = date(dt_first.year, dt_first.month - 1, 1)
            
        prev_mes = f"{prev_dt.year}-{str(prev_dt.month).zfill(2)}"
        
        yoy_dt = date(dt_first.year - 1, dt_first.month, 1)
        yoy_mes = f"{yoy_dt.year}-{str(yoy_dt.month).zfill(2)}"
        
        target_date_str = f"{dt_first.year}-{str(dt_first.month).zfill(2)}-01"

        response_data = {
            "periodo": mes,
            "periodo_previo": prev_mes,
            "periodo_yoy": yoy_mes,
            "totales": {
                "ingresos": 0, "ingresos_prev": 0, "ingresos_yoy": 0,
                "egresos": 0, "egresos_prev": 0, "egresos_yoy": 0,
                "stock": 0, "stock_prev": 0, "stock_yoy": 0,
                "subsanaciones": 0, "subsanaciones_prev": 0, "subsanaciones_yoy": 0,
                "meta": 0, "cumplido": False
            },
            "gerencias": {}
        }

        with engine.connect() as conn:
            for g, config in TRAMITES_CONFIG.items():
                g_clean = g.lower()
                trata_codes = list(config.keys())
                tratas_oficiales = [t for t in trata_codes if t != 'INTERVENCIONES']
                interv_egr_table = f"mv_{g_clean}_interv_egresos_eventos" if g_clean != 'contable' else "mv_contable_intervenciones_egresadas"

                metas_plan = {}
                if mes >= '2026-05':
                    try:
                        meta_res = conn.execute(text(f"SELECT TRIM(trata) as trata, COALESCE(egresos_totales_plan, 0) FROM mv_plan_metas_{g_clean} WHERE mes_calendario = :target"), {"target": target_date_str}).fetchall()
                        for r in meta_res:
                            metas_plan[r[0].upper()] = float(r[1])
                    except Exception:
                        pass

                    if not metas_plan:
                        metas_plan = calculate_all_trata_expected_egresos_batch(conn, g_clean, trata_codes)

                ingresos = {}
                ingresos_prev = {}
                ingresos_yoy = {}
                try:
                    ing_res = conn.execute(text(f"""
                        SELECT 
                            CASE WHEN TRIM(trata) = ANY(:tratas_oficiales) THEN TRIM(trata) ELSE 'INTERVENCIONES' END as trata, 
                            to_char(fecha_ingreso, 'YYYY-MM') as mes_lbl, 
                            COUNT(*) 
                        FROM mv_{g_clean}_ingresos_eventos 
                        WHERE to_char(fecha_ingreso, 'YYYY-MM') IN (:m, :pm, :yoy) 
                        GROUP BY 1, 2
                    """), {"m": mes, "pm": prev_mes, "yoy": yoy_mes, "tratas_oficiales": tratas_oficiales}).fetchall()
                    for r in ing_res:
                        t_code = r[0].upper()
                        if r[1] == mes:
                            ingresos[t_code] = r[2]
                        elif r[1] == prev_mes:
                            ingresos_prev[t_code] = r[2]
                        elif r[1] == yoy_mes:
                            ingresos_yoy[t_code] = r[2]
                except Exception:
                    pass
 
                egr_ef = {}
                egr_ef_prev = {}
                egr_ef_yoy = {}
                try:
                    e_res = conn.execute(text(f"SELECT TRIM(trata) as trata, to_char(fecha_egreso, 'YYYY-MM') as mes_lbl, COUNT(*) FROM mv_{g_clean}_gedos_egreso WHERE to_char(fecha_egreso, 'YYYY-MM') IN (:m, :pm, :yoy) GROUP BY 1, 2"), {"m": mes, "pm": prev_mes, "yoy": yoy_mes}).fetchall()
                    for r in e_res:
                        t_code = r[0].upper()
                        if r[1] == mes:
                            egr_ef[t_code] = r[2]
                        elif r[1] == prev_mes:
                            egr_ef_prev[t_code] = r[2]
                        elif r[1] == yoy_mes:
                            egr_ef_yoy[t_code] = r[2]
                            
                    i_res = conn.execute(text(f"SELECT to_char(fecha_egreso, 'YYYY-MM') as mes_lbl, COUNT(*) FROM {interv_egr_table} WHERE to_char(fecha_egreso, 'YYYY-MM') IN (:m, :pm, :yoy) GROUP BY 1"), {"m": mes, "pm": prev_mes, "yoy": yoy_mes}).fetchall()
                    for r in i_res:
                        if r[0] == mes:
                            egr_ef['INTERVENCIONES'] = r[1]
                        elif r[0] == prev_mes:
                            egr_ef_prev['INTERVENCIONES'] = r[1]
                        elif r[0] == yoy_mes:
                            egr_ef_yoy['INTERVENCIONES'] = r[1]
                except Exception:
                    pass
 
                egr_ne = {}
                egr_ne_prev = {}
                egr_ne_yoy = {}
                try:
                    ne_res = conn.execute(text(f"""
                        SELECT 
                            CASE WHEN TRIM(trata) = ANY(:tratas_oficiales) THEN TRIM(trata) ELSE 'INTERVENCIONES' END as trata, 
                            to_char(fecha_ultimo_movimiento, 'YYYY-MM') as mes_lbl, 
                            COUNT(*) 
                        FROM mv_{g_clean}_egresos_no_efectivos 
                        WHERE to_char(fecha_ultimo_movimiento, 'YYYY-MM') IN (:m, :pm, :yoy) 
                        GROUP BY 1, 2
                    """), {"m": mes, "pm": prev_mes, "yoy": yoy_mes, "tratas_oficiales": tratas_oficiales}).fetchall()
                    for r in ne_res:
                        t_code = r[0].upper()
                        if r[1] == mes:
                            egr_ne[t_code] = r[2]
                        elif r[1] == prev_mes:
                            egr_ne_prev[t_code] = r[2]
                        elif r[1] == yoy_mes:
                            egr_ne_yoy[t_code] = r[2]
                except Exception:
                    pass
 
                stock = {}
                stock_prev = {}
                stock_yoy = {}
                subs = {}
                subs_prev = {}
                subs_yoy = {}
                try:
                    st_res = conn.execute(text(f"""
                        SELECT 
                            CASE WHEN TRIM(trata) = ANY(:tratas_oficiales) THEN TRIM(trata) ELSE 'INTERVENCIONES' END as trata, 
                            categoria, 
                            mes_label, 
                            SUM(cant_expedientes) 
                        FROM mv_{g_clean}_stock_historico 
                        WHERE mes_label IN (:m, :pm, :yoy)
                        GROUP BY 1, 2, 3
                    """), {"m": mes, "pm": prev_mes, "yoy": yoy_mes, "tratas_oficiales": tratas_oficiales}).fetchall()
                    for r in st_res:
                        t_code = r[0].upper()
                        cat = r[1].upper()
                        is_target = (r[2] == mes)
                        is_prev = (r[2] == prev_mes)
                        is_yoy = (r[2] == yoy_mes)
                        
                        val_num = int(r[3] or 0)
                        if cat == 'STOCK_PROPIO':
                            if is_target: stock[t_code] = val_num
                            elif is_prev: stock_prev[t_code] = val_num
                            elif is_yoy: stock_yoy[t_code] = val_num
                        elif cat == 'SUBSANACION':
                            if is_target: subs[t_code] = val_num
                            elif is_prev: subs_prev[t_code] = val_num
                            elif is_yoy: subs_yoy[t_code] = val_num
                except Exception:
                    pass

                g_detalles = []
                g_tot_ing = 0; g_tot_ing_p = 0; g_tot_ing_y = 0
                g_tot_egr = 0; g_tot_egr_p = 0; g_tot_egr_y = 0
                g_tot_st = 0; g_tot_st_p = 0; g_tot_st_y = 0
                g_tot_sb = 0; g_tot_sb_p = 0; g_tot_sb_y = 0
                g_tot_meta = 0

                for t_id in trata_codes:
                    t_upper = t_id.upper()
                    
                    t_ing = ingresos.get(t_upper, 0)
                    t_ing_p = ingresos_prev.get(t_upper, 0)
                    t_ing_y = ingresos_yoy.get(t_upper, 0)
                    
                    t_egr = egr_ef.get(t_upper, 0) + egr_ne.get(t_upper, 0)
                    t_egr_p = egr_ef_prev.get(t_upper, 0) + egr_ne_prev.get(t_upper, 0)
                    t_egr_y = egr_ef_yoy.get(t_upper, 0) + egr_ne_yoy.get(t_upper, 0)
                    if t_upper == 'INTERVENCIONES':
                        t_egr = 0
                        t_egr_p = 0
                        t_egr_y = 0
                        
                    t_st = stock.get(t_upper, 0)
                    t_st_p = stock_prev.get(t_upper, 0)
                    t_st_y = stock_yoy.get(t_upper, 0)
                    
                    t_sb = subs.get(t_upper, 0)
                    t_sb_p = subs_prev.get(t_upper, 0)
                    t_sb_y = subs_yoy.get(t_upper, 0)
                    
                    t_meta = metas_plan.get(t_upper, 0)

                    g_tot_ing += t_ing
                    g_tot_ing_p += t_ing_p
                    g_tot_ing_y += t_ing_y
                    
                    g_tot_egr += t_egr
                    g_tot_egr_p += t_egr_p
                    g_tot_egr_y += t_egr_y
                    
                    g_tot_st += t_st
                    g_tot_st_p += t_st_p
                    g_tot_st_y += t_st_y
                    
                    g_tot_sb += t_sb
                    g_tot_sb_p += t_sb_p
                    g_tot_sb_y += t_sb_y
                    
                    g_tot_meta += t_meta

                    g_detalles.append({
                        "trata": t_id,
                        "descripcion_trata": config[t_id]["nombre"] if t_id != 'INTERVENCIONES' else "Intervenciones Externas del Sector",
                        "ingresos": t_ing,
                        "ingresos_prev": t_ing_p,
                        "ingresos_yoy": t_ing_y,
                        "egresos": t_egr,
                        "egresos_prev": t_egr_p,
                        "egresos_yoy": t_egr_y,
                        "meta": t_meta,
                        "cumplio_meta": (t_egr >= t_meta) if t_meta > 0 else True,
                        "stock": t_st,
                        "stock_prev": t_st_p,
                        "stock_yoy": t_st_y,
                        "subsanaciones": t_sb,
                        "subsanaciones_prev": t_sb_p,
                        "subsanaciones_yoy": t_sb_y
                    })

                response_data["gerencias"][g_clean] = {
                    "totales": {
                        "ingresos": g_tot_ing, "ingresos_prev": g_tot_ing_p, "ingresos_yoy": g_tot_ing_y,
                        "egresos": g_tot_egr, "egresos_prev": g_tot_egr_p, "egresos_yoy": g_tot_egr_y,
                        "stock": g_tot_st, "stock_prev": g_tot_st_p, "stock_yoy": g_tot_st_y,
                        "subsanaciones": g_tot_sb, "subsanaciones_prev": g_tot_sb_p, "subsanaciones_yoy": g_tot_sb_y,
                        "meta": g_tot_meta,
                        "cumplido": (g_tot_egr >= g_tot_meta) if g_tot_meta > 0 else True
                    },
                    "detalles": g_detalles
                }

                response_data["totales"]["ingresos"] += g_tot_ing
                response_data["totales"]["ingresos_prev"] += g_tot_ing_p
                response_data["totales"]["ingresos_yoy"] += g_tot_ing_y
                
                response_data["totales"]["egresos"] += g_tot_egr
                response_data["totales"]["egresos_prev"] += g_tot_egr_p
                response_data["totales"]["egresos_yoy"] += g_tot_egr_y
                
                response_data["totales"]["stock"] += g_tot_st
                response_data["totales"]["stock_prev"] += g_tot_st_p
                response_data["totales"]["stock_yoy"] += g_tot_st_y
                
                response_data["totales"]["subsanaciones"] += g_tot_sb
                response_data["totales"]["subsanaciones_prev"] += g_tot_sb_p
                response_data["totales"]["subsanaciones_yoy"] += g_tot_sb_y
                
                response_data["totales"]["meta"] += g_tot_meta

            response_data["totales"]["cumplido"] = (response_data["totales"]["egresos"] >= response_data["totales"]["meta"]) if response_data["totales"]["meta"] > 0 else True

        set_cache(_ck, response_data)
        return response_data
    except Exception as e:
        logger.error(f"Error en cierre_mes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/sla")
async def get_sla_report(gerencia: Optional[str] = 'ALL', current_user: User = Depends(get_current_user)):
    _ck = f"sla_{gerencia or 'ALL'}"
    hit, data = cached_response(_ck, ttl_seconds=120)
    if hit:
        return data
    try:
        with engine.connect() as conn:
            gerencias_to_query = []
            if gerencia and gerencia != 'ALL':
                g_clean = gerencia.lower()
                if g_clean == 'conforme':
                    g_clean = 'regularizacion'
                gerencias_to_query = [g_clean]
            else:
                gerencias_to_query = list(TRAMITES_CONFIG.keys())

            records = []
            for g_clean in gerencias_to_query:
                try:
                    sql_tiempos = f"""
                        SELECT 
                            gerencia,
                            trata AS "COD TRATA",
                            tramite AS "DETALLE TRATA",
                            total_expedientes_egresados AS total_resueltos,
                            duracion_total_mediana AS duracion_total_mediana,
                            duracion_total_promedio AS duracion_total_promedio,
                            duracion_neta_mediana AS duracion_neta_mediana,
                            duracion_subsanaciones_mediana AS duracion_subsanaciones_mediana
                        FROM mv_tiempos_resolucion_{g_clean}
                    """
                    result = conn.execute(text(sql_tiempos))
                    for row in result:
                        row_dict = dict(row._mapping)
                        
                        row_dict["mediana_dias"] = float(row_dict.get("duracion_total_mediana") or 0.0)
                        row_dict["promedio_dias"] = float(row_dict.get("duracion_total_mediana") or 0.0)
                        row_dict["total_resueltos"] = int(row_dict.get("total_resueltos") or 0)
                        
                        g_cfg = TRAMITES_CONFIG.get(g_clean, {})
                        t_code = row_dict["COD TRATA"]
                        t_cfg = g_cfg.get(t_code, {})
                        row_dict["acronimos"] = t_cfg.get("acronimos", "")
                        if t_cfg.get("nombre"):
                            row_dict["DETALLE TRATA"] = t_cfg.get("nombre")
                            
                        records.append(row_dict)
                except Exception as e:
                    logger.warning(f"No se pudo consultar mv_tiempos_resolucion_{g_clean}, usando fallback: {e}")
                    sql_fallback = f"""
                        SELECT 
                            gerencia,
                            trata AS "COD TRATA",
                            descripcion_trata AS "DETALLE TRATA",
                            COUNT(*) AS total_resueltos,
                            ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dias_resolucion)::numeric, 1) AS mediana_dias,
                            ROUND(AVG(dias_resolucion)::numeric, 1) AS promedio_dias
                        FROM mvw_sla_tramites
                        WHERE gerencia = :g
                        GROUP BY gerencia, trata, descripcion_trata
                        ORDER BY trata
                    """
                    result = conn.execute(text(sql_fallback), {"g": g_clean})
                    for row in result:
                        row_dict = dict(row._mapping)
                        
                        row_dict["duracion_total_mediana"] = float(row_dict.get("mediana_dias") or 0.0)
                        row_dict["duracion_neta_mediana"] = float(row_dict.get("mediana_dias") or 0.0)
                        row_dict["duracion_subsanaciones_mediana"] = 0.0
                        row_dict["promedio_dias"] = float(row_dict.get("promedio_dias") or 0.0)
                        row_dict["total_resueltos"] = int(row_dict.get("total_resueltos") or 0)
                        
                        g_cfg = TRAMITES_CONFIG.get(g_clean, {})
                        t_code = row_dict["COD TRATA"]
                        t_cfg = g_cfg.get(t_code, {})
                        row_dict["acronimos"] = t_cfg.get("acronimos", "")
                        if t_cfg.get("nombre"):
                            row_dict["DETALLE TRATA"] = t_cfg.get("nombre")
                            
                        records.append(row_dict)
            set_cache(_ck, records)
            return records
    except Exception as e:
        logger.error(f"Error en reporte/sla: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reporte/sla/expedientes")
async def get_sla_expedientes(
    gerencia: str,
    trata: str,
    current_user: User = Depends(get_current_user)
):
    gerencia_clean = gerencia.lower()
    if gerencia_clean == 'conforme':
        gerencia_clean = 'regularizacion'
        
    try:
        with engine.connect() as conn:
            sql = f"""
                WITH subs_dias AS (
                    SELECT 
                        id_expediente,
                        CASE 
                            WHEN COUNT(*) > 20 THEN 0
                            ELSE COALESCE(SUM(
                                CASE 
                                    WHEN fecha_alta IS NULL OR fecha_alta < '2015-01-01'::date THEN 0
                                    WHEN fecha_cierre IS NOT NULL THEN (fecha_cierre::date - fecha_alta::date)
                                    ELSE (CURRENT_DATE - fecha_alta::date)
                                END
                            ), 0)
                        END AS dias_subs
                    FROM (
                        SELECT DISTINCT id_expediente, fecha_alta, fecha_cierre
                        FROM mvw_ee_actividades_secgdu
                        WHERE nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                    ) t
                    GROUP BY id_expediente
                )
                SELECT 
                    '{gerencia_clean}'::text AS gerencia,
                    u.expediente AS "EXPEDIENTE",
                    u.trata AS "TRAMITE",
                    u.descripcion_trata AS "DETALLE TRATA",
                    to_char(u.fecha_creacion_ee, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA CARATULA",
                    to_char(e.fecha_egreso, 'YYYY-MM-DD HH24:MI:SS') AS "FECHA EGRESO",
                    (e.fecha_egreso::date - u.fecha_creacion_ee::date) AS "DIAS BRUTOS",
                    COALESCE(s.dias_subs, 0) AS "DIAS SUBSANACION",
                    GREATEST(0, (e.fecha_egreso::date - u.fecha_creacion_ee::date) - COALESCE(s.dias_subs, 0)) AS "DIAS NETOS SLA"
                FROM mv_{gerencia_clean}_universo u
                INNER JOIN mv_{gerencia_clean}_egresos_efectivos e ON u.id_expediente = e.id_expediente
                LEFT JOIN subs_dias s ON u.id_expediente = s.id_expediente
                WHERE u.trata = :trata
                ORDER BY e.fecha_egreso DESC
            """
            result = conn.execute(text(sql), {"trata": trata})
            rows = [dict(row._mapping) for row in result.fetchall()]
            
            mapped_rows = []
            for r in rows:
                mapped_rows.append({
                    "gerencia": r["gerencia"],
                    "expediente": r["EXPEDIENTE"],
                    "trata": r["TRAMITE"],
                    "descripcion_trata": r["DETALLE TRATA"],
                    "fecha_caratula": r["FECHA CARATULA"],
                    "fecha_egreso": r["FECHA EGRESO"],
                    "dias_brutos": int(r["DIAS BRUTOS"] or 0),
                    "dias_subsanacion": int(r["DIAS SUBSANACION"] or 0),
                    "dias_netos_sla": int(r["DIAS NETOS SLA"] or 0)
                })
                
            return mapped_rows
    except Exception as e:
        logger.error(f"Error en reporte/sla/expedientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
