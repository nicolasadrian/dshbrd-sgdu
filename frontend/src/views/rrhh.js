import { state } from '../state.js';
import rrhhHtml from './rrhh.html?raw';

export function renderRRHHView() {
    const container = document.getElementById('reportes_rrhh');
    if (container) {
        container.innerHTML = rrhhHtml;
    }
    initRRHHReportView();
}
let _rrhhCurrentCuil = '';
let _rrhhCurrentName = '';
let _rrhhCurrentMonth = '';
let selectedRRHHFile = null;

export function initRRHHReportView() {
    const monthInput = document.getElementById('rrhh-filter-month');
    if (monthInput && !monthInput.value) {
        const d = new Date();
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        monthInput.value = `${y}-${m}`;
    }

    // Toggle tab header visibility by permissions
    const tabCargaBtn = document.getElementById('tab-btn-rrhh-carga');
    if (tabCargaBtn) {
        const user = state.currentUser;
        const canUpload = !!(user && (user.permissions['carga_reportes_rrhh'] || ['admin', 'administrador'].includes((user.role || '').toLowerCase())));
        tabCargaBtn.style.display = canUpload ? 'inline-block' : 'none';
    }

    switchRRHHTab('reporte');
    loadRRHHReport();
}

export function switchRRHHTab(tab) {
    const reportTab = document.getElementById('rrhh-solapa-reporte');
    const uploadTab = document.getElementById('rrhh-solapa-carga');
    const btnReport = document.getElementById('tab-btn-rrhh-reporte');
    const btnCarga = document.getElementById('tab-btn-rrhh-carga');

    if (tab === 'reporte') {
        if (reportTab) reportTab.style.display = 'block';
        if (uploadTab) uploadTab.style.display = 'none';
        if (btnReport) {
            btnReport.className = 'tab-btn-premium active';
            btnReport.style.background = 'white';
            btnReport.style.color = 'var(--primary-dark)';
        }
        if (btnCarga) {
            btnCarga.className = 'tab-btn-premium';
            btnCarga.style.background = 'transparent';
            btnCarga.style.color = '#64748b';
        }
    } else {
        if (reportTab) reportTab.style.display = 'none';
        if (uploadTab) uploadTab.style.display = 'block';
        if (btnReport) {
            btnReport.className = 'tab-btn-premium';
            btnReport.style.background = 'transparent';
            btnReport.style.color = '#64748b';
        }
        if (btnCarga) {
            btnCarga.className = 'tab-btn-premium active';
            btnCarga.style.background = 'white';
            btnCarga.style.color = 'var(--primary-dark)';
        }
    }
}

export async function loadRRHHReport() {
    const container = document.getElementById('rrhh-sectores-container');
    const cardsContainer = document.getElementById('rrhh-global-cards');
    const monthEl = document.getElementById('rrhh-filter-month');
    const monthVal = monthEl ? monthEl.value : '';

    if (!container) return;

    container.innerHTML = '<div style="text-align: center; padding: 3rem;"><span class="loader"></span><p style="margin-top: 0.5rem; color: #64748b;">Analizando control de asistencia del sector...</p></div>';
    if (cardsContainer) cardsContainer.innerHTML = '';

    try {
        const API_BASE = window.API_BASE || '/api';
        const url = monthVal ? `${API_BASE}/rrhh/reporte?month=${monthVal}` : `${API_BASE}/rrhh/reporte`;
        const res = await window.def_fetch(url);
        if (res && res.ok) {
            const data = await res.json();
            window.currentRRHHReportData = data;

            if (data.month && monthEl) {
                monthEl.value = data.month;
            }

            if (!data.sectores || Object.keys(data.sectores).length === 0) {
                container.innerHTML = '<div style="text-align: center; padding: 3rem; color: #64748b; font-style: italic;">No hay registros importados para el mes seleccionado.</div>';
                return;
            }

            // Calculate global statistics
            let totalPresentes = 0;
            let totalAusentes = 0;
            let totalAgentes = 0;
            let sumAsistencia = 0;
            let totalMinutos = 0;
            let totalDiasHoras = 0;

            const sectorKeys = Object.keys(data.sectores);
            sectorKeys.forEach(sec => {
                const s = data.sectores[sec];
                s.agentes_list.forEach(a => {
                    totalAgentes++;
                    sumAsistencia += a.asistencia_pct;
                    if (a.ausentes > 0) totalAusentes += a.ausentes;
                    totalPresentes += a.presentes;
                });
            });

            const avgAsistencia = totalAgentes > 0 ? Math.round(sumAsistencia / totalAgentes) : 100;

            // Calcular promedio global de horas desde sectores
            sectorKeys.forEach(sec => {
                data.sectores[sec].agentes_list.forEach(a => {
                    if (a.promedio_horas && a.promedio_horas !== '--') {
                        const parts = a.promedio_horas.split(':');
                        totalMinutos += parseInt(parts[0]) * 60 + parseInt(parts[1]);
                        totalDiasHoras++;
                    }
                });
            });
            const avgPromHoras = totalDiasHoras > 0
                ? (() => { const m = Math.round(totalMinutos / totalDiasHoras); return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`; })()
                : '--';

            // Render Global KPI Cards
            if (cardsContainer) {
                cardsContainer.innerHTML = `
                    <div class="metric-card-premium" style="background: white; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                        <div style="width: 50px; height: 50px; border-radius: 50%; background: #eff6ff; color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-users"></i></div>
                        <div>
                            <span style="font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Agentes Analizados</span>
                            <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 700; font-size: 1.5rem; color: var(--primary-dark);">${totalAgentes}</h3>
                        </div>
                    </div>
                    <div class="metric-card-premium" style="background: white; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                        <div style="width: 50px; height: 50px; border-radius: 50%; background: #ecfdf5; color: #10b981; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-calendar-check"></i></div>
                        <div>
                            <span style="font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Asistencia Promedio</span>
                            <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 700; font-size: 1.5rem; color: #10b981;">${avgAsistencia}%</h3>
                        </div>
                    </div>
                    <div class="metric-card-premium" style="background: white; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                        <div style="width: 50px; height: 50px; border-radius: 50%; background: #fff7ed; color: #f97316; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-hourglass-half"></i></div>
                        <div>
                            <span style="font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Prom. Horas Realizadas</span>
                            <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 700; font-size: 1.5rem; color: #f97316;">${avgPromHoras} hs</h3>
                        </div>
                    </div>
                `;
            }

            // Render Sectores Accordions
            let sectorHtml = '';
            sectorKeys.forEach(secName => {
                const s = data.sectores[secName];
                const cleanStart = s.earliest_ingreso || "08:00";
                const cleanEnd = s.latest_salida || "18:00";

                // Generate Hourly Coverage distribution map HTML
                let coverageBarsHtml = '';
                const hours = Object.keys(s.hourly_coverage).sort();
                
                // Get max value in hour coverage to scale the bars nicely
                const maxAgentsCount = Math.max(...Object.values(s.hourly_coverage), 1);
                
                hours.forEach(hr => {
                    const count = s.hourly_coverage[hr];
                    const pctHeight = Math.round((count / maxAgentsCount) * 100);

                    coverageBarsHtml += `
                        <div style="display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 35px; gap: 6px;">
                            <div style="width: 100%; height: 80px; background: #f1f5f9; border-radius: 4px; display: flex; align-items: flex-end;">
                                <div style="width: 100%; height: ${pctHeight}%; background: var(--primary); border-radius: 4px; transition: height 0.5s ease;"></div>
                            </div>
                            <span style="font-size: 0.7rem; color: #64748b; font-weight: 600;">${hr}</span>
                        </div>
                    `;
                });

                // Generate agents table rows
                let agentsRows = '';
                s.agentes_list.forEach(a => {
                    // Color semafórico para promedio de horas
                    let horasColor = '#94a3b8'; // gris para '--'
                    if (a.promedio_horas && a.promedio_horas !== '--') {
                        const [hh, mm] = a.promedio_horas.split(':').map(Number);
                        const totalMin = hh * 60 + mm;
                        if (totalMin >= 420)       horasColor = '#10b981'; // verde  > 7h
                        else if (totalMin >= 300)  horasColor = '#f59e0b'; // amarillo 5–7h
                        else                       horasColor = '#ef4444'; // rojo  < 5h
                    }
                    agentsRows += `
                        <tr style="border-bottom: 1px solid #f1f5f9;">
                            <td style="padding: 10px 12px; font-weight: 700; color: var(--primary-dark);">${a.usuario.toUpperCase()}</td>
                            <td style="padding: 10px 12px; color: #334155;">${a.nombre}</td>
                            <td style="padding: 10px 12px; text-align: center; font-weight: 600; color: #10b981;">${a.asistencia_pct}%</td>
                            <td style="padding: 10px 12px; text-align: center; font-weight: 700; color: ${horasColor}; font-family: 'Outfit'; font-size: 0.95rem;">${a.promedio_horas} hs</td>
                            <td style="padding: 10px 12px; text-align: center;">
                                <button type="button" onclick="openRRHHAgentPage('${a.cuil}', '${encodeURIComponent(a.nombre)}')" class="btn-action-view" style="padding: 6px 12px; background: #eff6ff; color: #2563eb; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-family: 'Outfit'; font-weight: 700; transition: all 0.2s;">
                                    <i class="fa-solid fa-calendar-days"></i> Ver Bitácora
                                </button>
                            </td>
                        </tr>
                    `;
                });

                sectorHtml += `
                    <div class="admin-card" style="background: white; border-radius: 16px; border: 1px solid #cbd5e1; padding: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
                            <div>
                                <h3 style="margin: 0; color: var(--primary-dark); font-family: 'Outfit'; font-weight: 800; font-size: 1.3rem; text-transform: uppercase;">
                                    Sector: ${secName}
                                </h3>
                                <p style="margin: 4px 0 0 0; font-size: 0.82rem; color: #64748b;">Análisis de jornada, puntualidad y distribución de turnos por horario.</p>
                            </div>
                            <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 12px; display: inline-flex; align-items: center; gap: 8px; font-family: 'Outfit'; font-size: 0.85rem;">
                                <i class="fa-solid fa-business-time" style="color: var(--primary);"></i>
                                <span style="font-weight: 600; color: #334155;">Franja Horaria Cubierta:</span>
                                <strong style="color: var(--primary-dark);">${cleanStart} - ${cleanEnd}</strong>
                            </div>
                        </div>

                        <!-- 1. Mapa de Cobertura Horaria -->
                        <div style="margin-bottom: 2rem;">
                            <h4 style="margin: 0 0 1rem 0; color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700; font-size: 0.95rem;">Mapa de Cobertura Horaria (Agentes activos por hora)</h4>
                            <div style="display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 12px;">
                                ${coverageBarsHtml}
                            </div>
                        </div>

                        <!-- 2. Tabla de Analistas -->
                        <div>
                            <h4 style="margin: 0 0 1rem 0; color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700; font-size: 0.95rem;">Personal Asignado y Desempeño</h4>
                            <div class="table-responsive">
                                <table class="report-table" style="width: 100%; border-collapse: collapse;">
                                    <thead>
                                        <tr style="border-bottom: 2px solid #cbd5e1; background: #f8fafc; text-align: left; font-size: 0.82rem;">
                                            <th style="padding: 10px 12px; font-weight: 700; color: #475569;">Usuario</th>
                                            <th style="padding: 10px 12px; font-weight: 700; color: #475569;">Nombre y Apellido</th>
                                            <th style="padding: 10px 12px; font-weight: 700; color: #475569; text-align: center;">Asistencia</th>
                                            <th style="padding: 10px 12px; font-weight: 700; color: #475569; text-align: center;">Prom. Horas</th>
                                            <th style="padding: 10px 12px; font-weight: 700; color: #475569; text-align: center;">Acción</th>
                                        </tr>
                                    </thead>
                                    <tbody style="font-size: 0.85rem;">
                                        ${agentsRows}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                `;
            });
            container.innerHTML = sectorHtml;
        } else {
            container.innerHTML = '<div style="text-align: center; padding: 3rem; color: #ef4444;">Error al cargar datos del reporte.</div>';
        }
    } catch (err) {
        console.error("Error loading RRHH report:", err);
        container.innerHTML = '<div style="text-align: center; padding: 3rem; color: #ef4444;">Error de red al conectar con el servidor.</div>';
    }
}

export function openRRHHAgentPage(cuil, nameEncoded) {
    _rrhhCurrentCuil  = cuil;
    _rrhhCurrentName  = decodeURIComponent(nameEncoded);
    _rrhhCurrentMonth = document.getElementById('rrhh-filter-month')?.value || '';

    // Crear modal si no existe
    let modal = document.getElementById('rrhh-agent-calendar-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'rrhh-agent-calendar-modal';
        modal.style.cssText = [
            'display:none',
            'position:fixed',
            'inset:0',
            'z-index:9999',
            'background:rgba(15,23,42,0.55)',
            'backdrop-filter:blur(4px)',
            'align-items:center',
            'justify-content:center',
            'padding:20px'
        ].join(';');
        // Cerrar al hacer click en el backdrop
        modal.addEventListener('click', e => { if (e.target === modal) closeRRHHAgentPage(); });
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <div style="
            background: #f8fafc;
            border-radius: 20px;
            width: 100%;
            max-width: 1100px;
            max-height: 90vh;
            overflow-y: auto;
            padding: 28px;
            box-shadow: 0 25px 60px rgba(0,0,0,0.25);
            position: relative;
        ">
            <!-- Header -->
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
                <div>
                    <h2 style="margin: 0 0 4px 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.35rem; color: var(--primary-dark);">${_rrhhCurrentName}</h2>
                    <span style="font-size: 0.82rem; color: #64748b;">CUIL: ${_rrhhCurrentCuil} &nbsp;|&nbsp; Mes: ${_rrhhCurrentMonth}</span>
                </div>
                <button onclick="closeRRHHAgentPage()" style="background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 10px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 1rem; color: #475569; flex-shrink: 0;">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>

            <!-- Leyenda -->
            <div style="display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 20px; padding: 12px 18px; background: white; border: 1px solid #e2e8f0; border-radius: 10px;">
                <div style="display: flex; align-items: center; gap: 6px;"><span style="width: 12px; height: 12px; border-radius: 50%; background: #10b981; display: inline-block;"></span><span style="font-size: 0.8rem; color: #475569; font-weight: 600;">Presente</span></div>
                <div style="display: flex; align-items: center; gap: 6px;"><span style="width: 12px; height: 12px; border-radius: 50%; background: #ef4444; display: inline-block;"></span><span style="font-size: 0.8rem; color: #475569; font-weight: 600;">Ausente</span></div>
                <div style="display: flex; align-items: center; gap: 6px;"><span style="width: 12px; height: 12px; border-radius: 50%; background: #3b82f6; display: inline-block;"></span><span style="font-size: 0.8rem; color: #475569; font-weight: 600;">No convocado</span></div>
                <div style="display: flex; align-items: center; gap: 6px;"><span style="width: 12px; height: 12px; border-radius: 50%; background: #cbd5e1; display: inline-block;"></span><span style="font-size: 0.8rem; color: #475569; font-weight: 600;">Fin de semana / Feriado</span></div>
            </div>

            <!-- Contenido: calendario + detalle -->
            <div style="display: grid; grid-template-columns: 1fr 300px; gap: 20px; align-items: start;">
                <div id="rrhh-calendar-grid" style="background: white; border: 1px solid #e2e8f0; border-radius: 14px; padding: 18px;">
                    <div style="text-align: center; padding: 3rem;"><span class="loader"></span></div>
                </div>
                <div id="rrhh-day-detail" style="background: white; border: 1px solid #e2e8f0; border-radius: 14px; padding: 18px; display: none;">
                    <h4 style="margin: 0 0 14px 0; font-family: 'Outfit'; font-weight: 700; color: var(--primary-dark); font-size: 0.95rem;">Detalle del día</h4>
                    <div id="rrhh-day-detail-body"></div>
                </div>
            </div>
        </div>
    `;

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    _loadRRHHAgentCalendar();
}

async function _loadRRHHAgentCalendar() {
    try {
        const API_BASE = window.API_BASE || '/api';
        const res = await window.def_fetch(`${API_BASE}/rrhh/reporte/detalle-agente?cuil=${_rrhhCurrentCuil}&month=${_rrhhCurrentMonth}`);
        if (!res || !res.ok) throw new Error('fetch failed');
        _rrhhAgentLogs = await res.json();
        _renderRRHHCalendar();
    } catch (e) {
        const grid = document.getElementById('rrhh-calendar-grid');
        if (grid) grid.innerHTML = '<p style="color:#ef4444;text-align:center;">Error al cargar los datos.</p>';
    }
}

function _renderRRHHCalendar() {
    const grid = document.getElementById('rrhh-calendar-grid');
    if (!grid) return;

    const [yStr, mStr] = _rrhhCurrentMonth.split('-');
    const year  = parseInt(yStr);
    const month = parseInt(mStr);  // 1-based

    // Mapear logs por fecha 'YYYY-MM-DD'
    const byDate = {};
    _rrhhAgentLogs.forEach(l => { byDate[l.fecha] = l; });

    // Nombre del mes
    const monthNames = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    const monthName  = monthNames[month - 1];

    // Primer día y días del mes
    const firstDay  = new Date(year, month - 1, 1).getDay(); // 0=Dom
    const daysInMonth = new Date(year, month, 0).getDate();
    const startOffset = (firstDay === 0) ? 6 : firstDay - 1; // lunes primero

    const dayHeaders = ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'];

    let calHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <h3 style="margin: 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.15rem; color: var(--primary-dark);">${monthName} ${year}</h3>
        </div>
        <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 8px;">
    `;

    dayHeaders.forEach(d => {
        calHTML += `<div style="text-align: center; font-size: 0.72rem; font-weight: 700; color: #94a3b8; padding: 6px 0; text-transform: uppercase;">${d}</div>`;
    });
    calHTML += '</div><div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px;">';

    // Celdas vacías del inicio
    for (let i = 0; i < startOffset; i++) {
        calHTML += '<div></div>';
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr  = `${year}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
        const jsDate   = new Date(year, month - 1, day);
        const dayOfWeek = jsDate.getDay(); // 0=Dom, 6=Sáb
        const isWeekend = (dayOfWeek === 0 || dayOfWeek === 6);
        const log       = byDate[dateStr];

        let bgColor   = '#f1f5f9';   // sin datos
        let textColor = '#64748b';
        let cursor    = 'default';
        let title     = '';
        let clickable = false;

        if (log) {
            const isFeriado  = log.feriado  && log.feriado.toUpperCase()  === 'SI';
            const isConvocado = log.convocado && log.convocado.toUpperCase() === 'SI';
            const fromTime   = t => t && t !== '00:00:00' && t !== '00:00';
            const ingresaValido = fromTime(log.hora_ingreso);
            const esPresente = (log.estado && log.estado.toUpperCase().includes('PRESENTE')) || ingresaValido;

            if (isFeriado || isWeekend) {
                bgColor = '#cbd5e1'; textColor = '#475569'; title = isFeriado ? 'Feriado' : 'Fin de semana';
            } else if (!isConvocado) {
                bgColor = '#3b82f6'; textColor = '#fff'; title = 'No convocado';
            } else if (esPresente) {
                bgColor = '#10b981'; textColor = '#fff'; title = 'Presente'; clickable = true;
            } else {
                bgColor = '#ef4444'; textColor = '#fff'; title = 'Ausente'; clickable = true;
            }
        } else if (isWeekend) {
            bgColor = '#cbd5e1'; textColor = '#475569'; title = 'Fin de semana';
        }

        const clickAttr = clickable || log ? `onclick="_rrhhShowDayDetail('${dateStr}')"` : '';
        const hoverStyle = (clickable || log) ? 'cursor:pointer;' : '';

        calHTML += `
            <div ${clickAttr}
                 title="${title}"
                 style="
                    background: ${bgColor};
                    color: ${textColor};
                    border-radius: 10px;
                    padding: 10px 4px;
                    text-align: center;
                    font-family: 'Outfit';
                    font-weight: 700;
                    font-size: 0.9rem;
                    min-height: 48px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: opacity 0.15s, transform 0.15s;
                    ${hoverStyle}
                 "
                 onmouseover="this.style.opacity='0.82'; this.style.transform='scale(1.07)';"
                 onmouseout="this.style.opacity='1'; this.style.transform='scale(1)';"
            >${day}</div>
        `;
    }

    calHTML += '</div>';
    grid.innerHTML = calHTML;
}

export function _rrhhShowDayDetail(dateStr) {
    const log    = _rrhhAgentLogs.find(l => l.fecha === dateStr);
    const panel  = document.getElementById('rrhh-day-detail');
    const body   = document.getElementById('rrhh-day-detail-body');
    if (!panel || !body) return;

    panel.style.display = 'block';

    if (!log) {
        body.innerHTML = `<p style="color:#94a3b8; font-style:italic; font-size:0.9rem;">Sin registro para este día.</p>`;
        return;
    }

    const fromTime = t => t && t !== '00:00:00' && t !== '00:00';
    const ingresaValido = fromTime(log.hora_ingreso);
    const esPresente = (log.estado && log.estado.toUpperCase().includes('PRESENTE')) || ingresaValido;
    const estadoColor = esPresente ? '#10b981' : '#ef4444';

    // Formatear fecha larga
    const [y, m, d] = dateStr.split('-').map(Number);
    const dias   = ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];
    const meses  = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    const jsDate = new Date(y, m - 1, d);
    const fechaLarga = `${dias[jsDate.getDay()]} ${d} de ${meses[m - 1]} de ${y}`;

    const field = (label, value, color = '#334155') => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f1f5f9;">
            <span style="font-size: 0.82rem; color: #64748b; font-weight: 600;">${label}</span>
            <span style="font-size: 0.85rem; font-weight: 700; color: ${color};">${value || '-'}</span>
        </div>
    `;

    body.innerHTML = `
        <p style="font-size: 0.9rem; font-weight: 800; color: var(--primary-dark); margin: 0 0 16px 0; font-family: 'Outfit';">${fechaLarga}</p>
        ${field('Estado', log.estado || '-', estadoColor)}
        ${field('Convocado', log.convocado || '-')}
        ${field('Feriado',   log.feriado   || '-')}
        ${field('Ingreso',   ingresaValido ? log.hora_ingreso.substring(0,5) : '-')}
        ${field('Salida',    fromTime(log.hora_salida) ? log.hora_salida.substring(0,5) : '-')}
        ${field('Hs. realizadas', fromTime(log.cant_horas) ? log.cant_horas.substring(0,5) : '-', '#f97316')}
        ${field('Incidencia', log.estado_incidencia || '-', '#dc2626')}
    `;
}

export function closeRRHHAgentPage() {
    const modal = document.getElementById('rrhh-agent-calendar-modal');
    if (modal) modal.style.display = 'none';
    document.body.style.overflow = '';
    _rrhhAgentLogs = [];
}

export function handleRRHHDrop(e) {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        setRRHHFile(file);
    }
}

export function handleRRHHFileSelect(e) {
    if (e.target.files && e.target.files.length > 0) {
        const file = e.target.files[0];
        setRRHHFile(file);
    }
}

export function setRRHHFile(file) {
    selectedRRHHFile = file;
    const infoPanel = document.getElementById('rrhh-file-info');
    const nameSpan = document.getElementById('rrhh-filename');
    if (infoPanel && nameSpan) {
        nameSpan.innerText = file.name;
        infoPanel.style.display = 'flex';
    }
}

export function clearRRHHFile() {
    selectedRRHHFile = null;
    const input = document.getElementById('rrhh-file-input');
    if (input) input.value = '';
    const infoPanel = document.getElementById('rrhh-file-info');
    if (infoPanel) infoPanel.style.display = 'none';
}

export async function uploadRRHHExcel(e) {
    if (e) e.preventDefault();

    if (!selectedRRHHFile) {
        alert("Por favor, seleccione un archivo Excel antes de continuar.");
        return;
    }

    const formData = new FormData();
    formData.append("file", selectedRRHHFile);

    const submitBtn = document.querySelector('#rrhh-upload-form button[type="submit"]');
    if (!submitBtn) return;
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span class="loader" style="width: 16px; height: 16px; border-width: 2px;"></span> Procesando planilla...';
    submitBtn.disabled = true;

    try {
        const API_BASE = window.API_BASE || '/api';
        const token = state.authToken;
        const res = await fetch(`${API_BASE}/rrhh/upload?token=${encodeURIComponent(token || '')}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token || ''}`
            },
            body: formData
        });

        if (res.ok) {
            const ans = await res.json();
            alert(ans.message || "Excel cargado con éxito.");
            clearRRHHFile();
            switchRRHHTab('reporte');
            await loadRRHHReport();
        } else {
            const err = await res.json();
            alert(`Error de carga: ${err.detail || "No se pudo procesar la planilla"}`);
        }
    } catch (err) {
        console.error("Error uploading excel:", err);
        alert("Ocurrió un error de red al intentar subir el archivo.");
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}
