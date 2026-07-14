import logging
import calendar as _calendar
from datetime import date as _date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

# Import config, database, auth and cache utilities
from config import TRAMITES_CONFIG
from database import engine
from schemas import User
from auth_utils import get_current_user
from cache_utils import cached_response, set_cache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Landing Stats"])

@router.get("/api/landing/stats")
async def get_landing_stats():
    """Endpoint de métricas globales para el landing del tablero."""
    _ck = "landing_stats"
    hit, data = cached_response(_ck, ttl_seconds=120)
    if hit:
        return data
    try:
        today = _date.today()
        mes_actual = f"{today.year}-{str(today.month).zfill(2)}"

        # % avance del mes (días naturales)
        days_in_month = _calendar.monthrange(today.year, today.month)[1]
        pct_mes = round((today.day / days_in_month) * 100)

        with engine.connect() as conn:
            # 1. Cantidad de trámites configurados (oficiales, excluye INTERVENCIONES)
            tramites_total = sum(
                len([t for t in cfg.keys() if t != 'INTERVENCIONES'])
                for cfg in TRAMITES_CONFIG.values()
            )

            # 2. Analistas configurados en cfg_gestion_metas
            try:
                analistas_count = conn.execute(text("""
                    SELECT COUNT(DISTINCT TRIM(unnest_val))
                    FROM (
                        SELECT unnest(analistas_oficiales) as unnest_val
                        FROM cfg_gestion_metas
                        WHERE analistas_oficiales IS NOT NULL
                    ) t
                    WHERE TRIM(unnest_val) != ''
                """)).scalar() or 0
            except Exception:
                analistas_count = 0

            # 3. Métricas por gerencia (incluyendo intervenciones)
            ingresos_mes     = 0
            egresos_ef_mes   = 0
            egresos_no_ef_mes = 0
            stock_total      = 0
            stock_intervenciones = 0
            subs_abiertas    = 0
            top_trata_nombre = "-"
            top_trata_stock  = 0

            for g, cfg in TRAMITES_CONFIG.items():
                g_clean = g.lower()
                tratas_oficiales = [t for t in cfg.keys() if t != 'INTERVENCIONES']
                if not tratas_oficiales:
                    continue

                # Ingresos mes actual (mv_{g}_ingresos_eventos, fecha_ingreso)
                try:
                    r = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_ingresos_eventos
                        WHERE to_char(fecha_ingreso, 'YYYY-MM') = :m
                          AND TRIM(trata) = ANY(:tratas)
                    """), {"m": mes_actual, "tratas": tratas_oficiales}).scalar()
                    ingresos_mes += (r or 0)
                except Exception:
                    pass

                # Egresos efectivos mes actual (mv_{g}_gedos_egreso, fecha_egreso)
                try:
                    r = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_gedos_egreso
                        WHERE to_char(fecha_egreso, 'YYYY-MM') = :m
                          AND TRIM(trata) = ANY(:tratas)
                    """), {"m": mes_actual, "tratas": tratas_oficiales}).scalar()
                    egresos_ef_mes += (r or 0)
                except Exception:
                    pass

                # Egresos no efectivos mes actual (mv_{g}_egresos_no_efectivos, fecha_ultimo_movimiento)
                try:
                    r = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_egresos_no_efectivos
                        WHERE to_char(fecha_ultimo_movimiento, 'YYYY-MM') = :m
                          AND TRIM(trata) = ANY(:tratas)
                    """), {"m": mes_actual, "tratas": tratas_oficiales}).scalar()
                    egresos_no_ef_mes += (r or 0)
                except Exception:
                    pass

                # Stock actual (mv_{g}_stock_propio + mv_{g}_intervenciones_stock)
                try:
                    r = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_stock_propio
                        WHERE TRIM(trata) = ANY(:tratas)
                    """), {"tratas": tratas_oficiales}).scalar() or 0
                    stock_total += int(r)
                except Exception:
                    pass
                try:
                    r_int = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_intervenciones_stock
                    """)).scalar() or 0
                    stock_total += int(r_int)
                    stock_intervenciones += int(r_int)
                except Exception:
                    pass

                # Subsanaciones actual (mv_{g}_subsanaciones + mv_{g}_intervenciones_subs)
                try:
                    r = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_subsanaciones
                        WHERE TRIM(trata) = ANY(:tratas)
                    """), {"tratas": tratas_oficiales}).scalar() or 0
                    subs_abiertas += int(r)
                except Exception:
                    pass
                try:
                    r_int = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_intervenciones_subs
                    """)).scalar() or 0
                    subs_abiertas += int(r_int)
                except Exception:
                    pass

                # Top trámite por stock en esta gerencia (query simple sin subquery)
                try:
                    top_res = conn.execute(text(f"""
                        SELECT TRIM(trata), COUNT(*) as cnt
                        FROM mv_{g_clean}_stock_propio
                        WHERE TRIM(trata) = ANY(:tratas)
                        GROUP BY 1
                        ORDER BY cnt DESC
                        LIMIT 1
                    """), {"tratas": tratas_oficiales}).fetchone()
                    if top_res and (top_res[1] or 0) > top_trata_stock:
                        top_trata_stock = int(top_res[1])
                        trata_code = top_res[0]
                        try:
                            desc_res = conn.execute(text("""
                                SELECT TRIM(descripcion_trata)
                                FROM cfg_gestion_metas
                                WHERE TRIM(trata_reporte) = :trata
                                   OR :trata = ANY(tratas_incluidas)
                                LIMIT 1
                            """), {"trata": trata_code}).scalar()
                            top_trata_nombre = desc_res if desc_res else trata_code
                        except Exception:
                            top_trata_nombre = trata_code
                except Exception:
                    pass

            # 4. Desglose DGROC vs DGIUR (acumulado desde febrero 2026)
            dgroc_stats = {
                "ingresos_mes": 0, "ingresos_acum": 0,
                "egresos_mes": 0, "egresos_acum": 0,
                "egresos_efectivos_acum": 0, "egresos_no_efectivos_acum": 0,
                "stock": 0, "stock_intervenciones": 0,
                "subsanaciones": 0, "subsanaciones_intervenciones": 0
            }
            dgiur_stats = {
                "ingresos_mes": 0, "ingresos_acum": 0,
                "egresos_mes": 0, "egresos_acum": 0,
                "egresos_efectivos_acum": 0, "egresos_no_efectivos_acum": 0,
                "stock": 0, "stock_intervenciones": 0,
                "subsanaciones": 0, "subsanaciones_intervenciones": 0
            }

            dgroc_list = ["catastro", "instalaciones", "regularizacion", "contable", "etapa_proyecto", "aviso_obra"]
            dgiur_list = ["morfologia", "aph", "usos"]

            for g, cfg in TRAMITES_CONFIG.items():
                g_clean = g.lower()
                tratas_oficiales = [t for t in cfg.keys() if t != 'INTERVENCIONES']
                if not tratas_oficiales:
                    continue

                is_dgroc = (g_clean in dgroc_list)
                stats_ref = dgroc_stats if is_dgroc else dgiur_stats

                # A. Ingresos
                # ... (rest of code stays the same) ...
                try:
                    r = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_ingresos_eventos
                        WHERE to_char(fecha_ingreso, 'YYYY-MM') = :m
                          AND TRIM(trata) = ANY(:tratas)
                    """), {"m": mes_actual, "tratas": tratas_oficiales}).scalar() or 0
                    stats_ref["ingresos_mes"] += r
                except Exception:
                    pass
                try:
                    r = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_ingresos_eventos
                        WHERE fecha_ingreso >= '2026-03-01'::date
                          AND TRIM(trata) = ANY(:tratas)
                    """), {"tratas": tratas_oficiales}).scalar() or 0
                    stats_ref["ingresos_acum"] += r
                except Exception:
                    pass

                # B. Egresos (Efectivos + No Efectivos)
                try:
                    ef = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_gedos_egreso
                        WHERE to_char(fecha_egreso, 'YYYY-MM') = :m
                          AND TRIM(trata) = ANY(:tratas)
                    """), {"m": mes_actual, "tratas": tratas_oficiales}).scalar() or 0
                    ne = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_egresos_no_efectivos
                        WHERE to_char(fecha_ultimo_movimiento, 'YYYY-MM') = :m
                          AND TRIM(trata) = ANY(:tratas)
                    """), {"m": mes_actual, "tratas": tratas_oficiales}).scalar() or 0
                    stats_ref["egresos_mes"] += (ef + ne)
                except Exception:
                    pass
                try:
                    ef_ac = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_gedos_egreso
                        WHERE fecha_egreso >= '2026-03-01'::date
                          AND TRIM(trata) = ANY(:tratas)
                    """), {"tratas": tratas_oficiales}).scalar() or 0
                    ne_ac = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_egresos_no_efectivos
                        WHERE fecha_ultimo_movimiento >= '2026-03-01'::date
                          AND TRIM(trata) = ANY(:tratas)
                    """), {"tratas": tratas_oficiales}).scalar() or 0
                    stats_ref["egresos_acum"] += (ef_ac + ne_ac)
                    stats_ref["egresos_efectivos_acum"] += ef_ac
                    stats_ref["egresos_no_efectivos_acum"] += ne_ac
                except Exception:
                    pass

                # C. Stock (Oficial + Intervenciones)
                try:
                    r = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_stock_propio
                        WHERE TRIM(trata) = ANY(:tratas)
                    """), {"tratas": tratas_oficiales}).scalar() or 0
                    stats_ref["stock"] += int(r)
                except Exception:
                    pass
                try:
                    r_int = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_intervenciones_stock
                    """)).scalar() or 0
                    stats_ref["stock"] += int(r_int)
                    stats_ref["stock_intervenciones"] += int(r_int)
                except Exception:
                    pass

                # D. Subsanaciones (Oficial + Intervenciones)
                try:
                    r = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_subsanaciones
                        WHERE TRIM(trata) = ANY(:tratas)
                    """), {"tratas": tratas_oficiales}).scalar() or 0
                    stats_ref["subsanaciones"] += int(r)
                except Exception:
                    pass
                try:
                    r_int = conn.execute(text(f"""
                        SELECT COUNT(*) FROM mv_{g_clean}_intervenciones_subs
                    """)).scalar() or 0
                    stats_ref["subsanaciones"] += int(r_int)
                    stats_ref["subsanaciones_intervenciones"] += int(r_int)
                except Exception:
                    pass

            result = {
                "mes": mes_actual,
                "pct_mes": pct_mes,
                "dia_actual": today.day,
                "dias_mes": days_in_month,
                "tramites_total": tramites_total,
                "analistas_count": analistas_count,
                "ingresos_mes": ingresos_mes,
                "egresos_efectivos_mes": egresos_ef_mes,
                "egresos_no_efectivos_mes": egresos_no_ef_mes,
                "egresos_total_mes": egresos_ef_mes + egresos_no_ef_mes,
                "stock_total": stock_total,
                "stock_intervenciones": stock_intervenciones,
                "subs_abiertas": subs_abiertas,
                "top_trata_nombre": top_trata_nombre,
                "top_trata_stock": top_trata_stock,
                "dgroc": dgroc_stats,
                "dgiur": dgiur_stats
            }
            set_cache(_ck, result)
            return result
    except Exception as e:
        logger.error(f"Error en landing/stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
