import re
import math
from datetime import datetime, timedelta
from sqlalchemy import text

# Task Types
T_OBSERVACION = "OBSERVACIÓN DE EXPEDIENTE"
T_PLANOS = "PEDIDO DE PLANOS"
T_VINCULACION = "VINCULACIÓN DE GEDO Y PASE A OBRAS ADMIN"
T_FIRMA = "ENVÍO A FIRMA"
T_SUBSANACION = "OBSERVACIÓN EN SUBSANACIÓN"
T_SUSPENSION = "SUSPENSIÓN DE EXPEDIENTE"
T_EXCLUIDO = "EXCLUIDO"

GERENCIAS = ['catastro', 'instalaciones', 'regularizacion', 'contable', 'etapa_proyecto', 'aviso_obra', 'morfologia', 'aph', 'usos']

def classify_action(ref, tipo_origen, tipo_actividad):
    ref_upper = (ref or "").upper().strip()
    act_upper = (tipo_actividad or "").upper().strip()
    
    # Exclusions (Section 6)
    if any(k in ref_upper for k in ["CANCELACION DE ACTIVIDAD", "CANCELADA"]):
        return T_EXCLUIDO, "Cancelación de actividad"
    if "INTERCONSULTA" in ref_upper:
        return T_EXCLUIDO, "Interconsulta"
    if "OCHAVA" in ref_upper:
        return T_EXCLUIDO, "Solicitud de certificado de ochava"
    if "CONSULTA" in ref_upper:
        return T_EXCLUIDO, "Consulta"
    if "VALIDACION DE ANTECEDENTE" in ref_upper or "VALIDACIÓN DE ANTECEDENTE" in ref_upper:
        return T_EXCLUIDO, "Solicitud de validación de antecedente"
    if "ANTECEDENTE EN PDF" in ref_upper:
        return T_EXCLUIDO, "Pedido de antecedente en PDF"
    if ref_upper == "MMM":
        return T_EXCLUIDO, "Entrada inválida"
        
    # SUSPENSIÓN DE EXPEDIENTE
    if any(k in ref_upper for k in ["SUSPENSION", "SUSPENSIÓN", "AVISO DE SUSPENSION"]):
        return T_SUSPENSION, None
        
    # PEDIDO DE PLANOS
    if any(k in ref_upper for k in ["SOLICITUD DE PLANOS", "PEDIDO DE PLANOS", "SOL. DE PLANOS"]):
        return T_PLANOS, None
    if "PLANOS" in ref_upper and any(k in ref_upper for k in ["OBSERVACIONES", "C/OBS", "REGISTRO/FIRMA"]):
        return T_PLANOS, None
        
    # ENVÍO A FIRMA
    if any(k in ref_upper for k in [
        "PROCESO DE REVISIÓN Y EVENTUAL REGISTRO", 
        "PROCESO DE REVISION Y EVENTUAL REGISTRO",
        "ENVÍO A REVISIÓN", "ENVIO A REVISION",
        "ENVIADO A REVISIÓN", "ENVIADO A REVISION",
        "REVISIÓN Y EVENTUAL REGISTRO", "REVISION Y EVENTUAL REGISTRO",
        "INFORME (P/ REGISTRO) ELEVADO A LA SUPERIORIDAD",
        "INFORME (P/REGISTRO) ELEVADO"
    ]):
        return T_FIRMA, None
        
    # OBSERVACIÓN DE EXPEDIENTE
    if any(k in ref_upper for k in ["OBSERVACIONES", "OBSERVACIÓN", "OBSERVADO", "OBS. 0"]):
        return T_OBSERVACION, None
    if re.search(r'\bOBS\d+\b', ref_upper):
        return T_OBSERVACION, None
    if ref_upper.startswith("ADECUAR") or ref_upper.startswith("AGREGAR"):
        return T_OBSERVACION, None
    if "DOMICILIO" in ref_upper:
        return T_OBSERVACION, None
    if re.search(r'^[A-ZÁÉÍÓÚ\s\.]+\d+$', ref_upper) and len(ref_upper) < 80:
        return T_OBSERVACION, None
        
    # OBSERVACIÓN EN SUBSANACIÓN
    if any(k in ref_upper for k in ["SUBSANACIÓN", "SUBSANACION"]) or act_upper in ["SOLICITUD_SUBSANACION_TAD", "SUBSANACION"]:
        return T_SUBSANACION, None
        
    # VINCULACIÓN DE GEDO Y PASE A OBRAS ADMIN (default for pases)
    if tipo_origen == "pase":
        return T_VINCULACION, None
        
    return None, "Indeterminado"

def group_actions(actions):
    # Sort by date
    actions = sorted(actions, key=lambda x: x['fecha'])
    
    expediente_groups = {}
    for a in actions:
        exp = a['expediente'] or 'SIN_EXPEDIENTE'
        if exp not in expediente_groups:
            expediente_groups[exp] = []
        expediente_groups[exp].append(a)
        
    tasks = []
    exclusions = []
    
    for exp, exp_actions in expediente_groups.items():
        current_task = None
        for a in exp_actions:
            ref = a['referencia']
            to = a['tipo_origen']
            ta = a['tipo_actividad']
            
            category, reason = classify_action(ref, to, ta)
            
            if category == T_EXCLUIDO:
                exclusions.append({
                    "fecha": a['fecha'],
                    "referencia": ref,
                    "expediente": exp,
                    "reason": reason
                })
                continue
                
            if category is None:
                exclusions.append({
                    "fecha": a['fecha'],
                    "referencia": ref,
                    "expediente": exp,
                    "reason": "Indeterminado"
                })
                continue
                
            if current_task is None:
                current_task = {
                    "tipo_tarea": category,
                    "expediente": exp,
                    "fecha_inicio": a['fecha'],
                    "fecha_fin": a['fecha'],
                    "acciones": [a]
                }
            else:
                is_anchor = category in [T_OBSERVACION, T_PLANOS, T_FIRMA, T_SUBSANACION, T_SUSPENSION]
                
                if is_anchor:
                    tasks.append(current_task)
                    current_task = {
                        "tipo_tarea": category,
                        "expediente": exp,
                        "fecha_inicio": a['fecha'],
                        "fecha_fin": a['fecha'],
                        "acciones": [a]
                    }
                else:
                    # Pase suelto/transfer -> absorb into current task
                    current_task["acciones"].append(a)
                    current_task["fecha_fin"] = a['fecha']
                    
        if current_task:
            tasks.append(current_task)
            
    # Apply special unifications (e.g. consecutive subsanaciones on same expediente)
    refined_tasks = []
    for exp, exp_actions in expediente_groups.items():
        exp_tasks = [t for t in tasks if t['expediente'] == exp]
        if not exp_tasks:
            continue
        
        # Sort exp_tasks by start date
        exp_tasks = sorted(exp_tasks, key=lambda x: x['fecha_inicio'])
        
        i = 0
        while i < len(exp_tasks):
            t = exp_tasks[i]
            # If it is a Subsanación task, unify consecutive Subsanación tasks
            if t['tipo_tarea'] == T_SUBSANACION:
                j = i + 1
                while j < len(exp_tasks) and exp_tasks[j]['tipo_tarea'] == T_SUBSANACION:
                    t['acciones'].extend(exp_tasks[j]['acciones'])
                    t['fecha_fin'] = exp_tasks[j]['fecha_fin']
                    j += 1
                refined_tasks.append(t)
                i = j
            else:
                refined_tasks.append(t)
                i += 1
                
    return refined_tasks, exclusions

def get_analyst_productivity_data(conn, username, date_from=None, date_to=None):
    if not date_from:
        date_from = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')
        
    # 1. Fetch SADE actions from materialized view mvw_sade_acciones
    sql = """
        SELECT id_expediente, expediente, fecha, usuario, referencia, tipo_origen, tipo_actividad 
        FROM mvw_sade_acciones 
        WHERE usuario = :u AND fecha >= :fd AND fecha <= :fh
        ORDER BY fecha ASC
    """
    result = conn.execute(text(sql), {"u": username, "fd": f"{date_from} 00:00:00", "fh": f"{date_to} 23:59:59"})
    actions = [{
        "id_expediente": row[0],
        "expediente": row[1],
        "fecha": row[2],
        "usuario": row[3],
        "referencia": row[4],
        "tipo_origen": row[5],
        "tipo_actividad": row[6]
    } for row in result.fetchall()]
    
    # Run grouping engine
    tasks, exclusions = group_actions(actions)
    
    # 2. Query stock metrics from mvw_stock_actual_detalle
    stock_sql = """
        SELECT COUNT(*) as total_stock, 
               COALESCE(SUM(CASE WHEN is_subs = 0 THEN 1 ELSE 0 END), 0) as stock_propio,
               COALESCE(SUM(CASE WHEN is_subs = 1 THEN 1 ELSE 0 END), 0) as stock_subs
        FROM mvw_stock_actual_detalle 
        WHERE analista_actual = :u
    """
    stock_row = conn.execute(text(stock_sql), {"u": username}).fetchone()
    total_stock = stock_row[0] if stock_row else 0
    stock_propio = stock_row[1] if stock_row else 0
    stock_subs = stock_row[2] if stock_row else 0
    
    # 3. Query firmados (egresos efectivos) and rechazados (egresos no efectivos) across all gerencias
    total_firmados = 0
    total_rechazados = 0
    
    for ger in GERENCIAS:
        try:
            firm_sql = f"SELECT COUNT(*) FROM mv_{ger}_gedos_egreso WHERE usuario_egreso = :u AND fecha_egreso >= :fd AND fecha_egreso <= :fh"
            firm_count = conn.execute(text(firm_sql), {"u": username, "fd": f"{date_from} 00:00:00", "fh": f"{date_to} 23:59:59"}).scalar()
            total_firmados += firm_count or 0
        except Exception:
            pass
            
        try:
            rech_sql = f"SELECT COUNT(*) FROM mv_{ger}_egresos_no_efectivos WHERE poseedor_actual = :u AND fecha_ultimo_movimiento >= :fd AND fecha_ultimo_movimiento <= :fh"
            rech_count = conn.execute(text(rech_sql), {"u": username, "fd": f"{date_from} 00:00:00", "fh": f"{date_to} 23:59:59"}).scalar()
            total_rechazados += rech_count or 0
        except Exception:
            pass
            
    # Calculate working days and helper dates
    d_start = datetime.strptime(date_from, '%Y-%m-%d')
    d_end = datetime.strptime(date_to, '%Y-%m-%d')
    delta_days = (d_end - d_start).days + 1
    
    # Count only weekdays (Mon-Fri) as working days approximation
    working_days = 0
    for day_offset in range(delta_days):
        day = d_start + timedelta(days=day_offset)
        if day.weekday() < 5: # Monday is 0, Friday is 4
            working_days += 1
    working_days = max(1, working_days)
    weeks = max(1.0, delta_days / 7.0)
    
    # Calculate daily task breakdown
    daily_breakdown = {}
    for t in tasks:
        day_str = t['fecha_inicio'].strftime('%Y-%m-%d')
        if day_str not in daily_breakdown:
            daily_breakdown[day_str] = {T_OBSERVACION: 0, T_PLANOS: 0, T_VINCULACION: 0, T_FIRMA: 0, T_SUBSANACION: 0, T_SUSPENSION: 0}
        daily_breakdown[day_str][t['tipo_tarea']] += 1
        
    # Calculate active hours per day (jornada)
    daily_actions = {}
    for a in actions:
        day_str = a['fecha'].strftime('%Y-%m-%d')
        if day_str not in daily_actions:
            daily_actions[day_str] = []
        daily_actions[day_str].append(a['fecha'])
        
    jornada_durations = []
    jornada_details = []
    for day_str, times in daily_actions.items():
        min_time = min(times)
        max_time = max(times)
        duration_hours = (max_time - min_time).total_seconds() / 3600.0
        jornada_durations.append(duration_hours)
        jornada_details.append({
            "fecha": day_str,
            "primera_accion": min_time.strftime('%H:%M:%S'),
            "ultima_accion": max_time.strftime('%H:%M:%S'),
            "duracion": round(duration_hours, 2)
        })
        
    avg_jornada = round(sum(jornada_durations) / len(jornada_durations), 2) if jornada_durations else 0.0
    
    # Calculate totals and mix
    task_counts = {T_OBSERVACION: 0, T_PLANOS: 0, T_VINCULACION: 0, T_FIRMA: 0, T_SUBSANACION: 0, T_SUSPENSION: 0}
    for t in tasks:
        task_counts[t['tipo_tarea']] += 1
        
    total_tasks = len(tasks)
    task_mix = {}
    for t_type, count in task_counts.items():
        task_mix[t_type] = {
            "cantidad": count,
            "porcentaje": round((count / total_tasks) * 100, 2) if total_tasks > 0 else 0.0
        }
        
    # Rejection rate
    rejections_total = total_firmados + total_rechazados
    rejection_rate = round((total_rechazados / rejections_total) * 100, 2) if rejections_total > 0 else 0.0
    
    # Firmas per day
    firmas_por_dia = round(total_firmados / working_days, 2)
    
    # Days to clear stock
    dias_para_agotar = round(stock_propio / firmas_por_dia, 1) if firmas_por_dia > 0 else None
    
    # Plan metas (30, 45, 60 days)
    plan_metas = {}
    for horizon in [30, 45, 60]:
        target_firma = round(stock_propio / horizon, 2)
        brecha = round(target_firma - firmas_por_dia, 2)
        plan_metas[str(horizon)] = {
            "meta_diaria": target_firma,
            "brecha": brecha
        }
        
    # Weekly breakdown
    weekly_breakdown = {}
    for t in tasks:
        # Get ISO week
        year, week, _ = t['fecha_inicio'].isocalendar()
        week_key = f"{year}-W{week:02d}"
        weekly_breakdown[week_key] = weekly_breakdown.get(week_key, 0) + 1
        
    return {
        "kpis": {
            "tareas_totales": total_tasks,
            "promedio_diario": round(total_tasks / working_days, 2),
            "promedio_semanal": round(total_tasks / weeks, 2),
            "jornada_media": avg_jornada,
            "stock_total": total_stock,
            "stock_propio": stock_propio,
            "stock_subs": stock_subs,
            "firmados": total_firmados,
            "rechazados": total_rechazados,
            "tasa_rechazo": rejection_rate,
            "firma_dia": firmas_por_dia,
            "dias_para_agotar": dias_para_agotar,
            "dias_habiles": working_days
        },
        "mix_tareas": task_mix,
        "desglose_diario": daily_breakdown,
        "desglose_semanal": weekly_breakdown,
        "detalles_jornada": sorted(jornada_details, key=lambda x: x['fecha']),
        "plan_metas": plan_metas,
        "exclusiones": {
            "total": len(exclusions),
            "detalles": exclusions[:100]  # Cap at 100 for size
        }
    }
