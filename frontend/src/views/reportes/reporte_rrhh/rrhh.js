import { state } from '../../../state.js';

export const GERENCIAS_CONFIG = {
    // DGROC
    catastro: { key: 'catastro', name: 'Catastro', dir: 'DGROC', icon: 'fa-solid fa-map-location-dot', color: '#2563eb', bg: '#eff6ff' },
    instalaciones: { key: 'instalaciones', name: 'Instalaciones', dir: 'DGROC', icon: 'fa-solid fa-bolt', color: '#d97706', bg: '#fffbeb' },
    conforme: { key: 'conforme', name: 'Conforme', dir: 'DGROC', icon: 'fa-solid fa-clipboard-check', color: '#16a34a', bg: '#f0fdf4' },
    contable: { key: 'contable', name: 'Contable', dir: 'DGROC', icon: 'fa-solid fa-calculator', color: '#0284c7', bg: '#f0f9ff' },
    etapa_proyecto: { key: 'etapa_proyecto', name: 'Etapa Proyecto', dir: 'DGROC', icon: 'fa-solid fa-building-columns', color: '#7c3aed', bg: '#f5f3ff' },
    aviso_obra: { key: 'aviso_obra', name: 'Aviso de Obra', dir: 'DGROC', icon: 'fa-solid fa-hard-hat', color: '#db2777', bg: '#fdf2f8' },

    // DGIUR
    morfologia: { key: 'morfologia', name: 'Morfología Urbana', dir: 'DGIUR', icon: 'fa-solid fa-cubes', color: '#0891b2', bg: '#ecfeff' },
    aph: { key: 'aph', name: 'Área de Protección Histórica (APH)', dir: 'DGIUR', icon: 'fa-solid fa-landmark', color: '#b45309', bg: '#fef3c7' },
    usos: { key: 'usos', name: 'Usos del Suelo', dir: 'DGIUR', icon: 'fa-solid fa-shapes', color: '#0d9488', bg: '#f0fdfa' },
    publico_privado: { key: 'publico_privado', name: 'Público Privado', dir: 'DGIUR', icon: 'fa-solid fa-handshake', color: '#4f46e5', bg: '#eef2ff' },
    copua: { key: 'copua', name: 'COPUA', dir: 'DGIUR', icon: 'fa-solid fa-users-gear', color: '#3b82f6', bg: '#eff6ff' },
    privada: { key: 'privada', name: 'Privada', dir: 'DGIUR', icon: 'fa-solid fa-key', color: '#65a30d', bg: '#f7fee7' },

    // OTROS
    otros: { key: 'otros', name: 'Otras Áreas / General', dir: 'OTROS', icon: 'fa-solid fa-folder-tree', color: '#64748b', bg: '#f8fafc' }
};

let _currentReportData = null;
let _rrhhAgentLogs = [];
let _rrhhCurrentCuil = '';
let _rrhhCurrentName = '';
let _rrhhCurrentMonth = '';
let selectedRRHHFile = null;

/**
 * Helper to fetch RRHH report data from backend
 */
async function fetchRRHHData(monthVal = '', gerencia = '') {
    const API_BASE = window.API_BASE || '/api';
    let url = `${API_BASE}/rrhh/reporte`;
    const params = [];
    if (monthVal) params.push(`month=${encodeURIComponent(monthVal)}`);
    if (gerencia) params.push(`gerencia=${encodeURIComponent(gerencia)}`);
    if (params.length > 0) url += `?${params.join('&')}`;

    const token = state.authToken || localStorage.getItem('sgdu_token') || '';
    if (window.def_fetch) {
        return await window.def_fetch(url);
    }
    return await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
}

export function getLastCompleteMonth() {
    const d = new Date();
    d.setDate(1);
    d.setMonth(d.getMonth() - 1);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}`;
}

export function populateRRHHMonthDropdown(selectEl, currentSelected, dbAvailableMonths = []) {
    if (!selectEl) return;

    const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
    const lastComplete = getLastCompleteMonth();
    
    // Always start with the last complete month as the 1st option
    const orderedMonths = [lastComplete];

    // Add previous 24 months in descending order
    const [lastY, lastM] = lastComplete.split('-').map(Number);
    for (let i = 1; i <= 24; i++) {
        const d = new Date(lastY, lastM - 1 - i, 1);
        const ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        if (!orderedMonths.includes(ym)) {
            orderedMonths.push(ym);
        }
    }

    // Add any database months that might not be in the list
    (dbAvailableMonths || []).forEach(ym => {
        if (!orderedMonths.includes(ym)) {
            orderedMonths.push(ym);
        }
    });

    const activeVal = currentSelected || selectEl.value || lastComplete;

    let optionsHtml = '';
    orderedMonths.forEach((ym, idx) => {
        const [y, m] = ym.split('-').map(Number);
        const name = MESES[m - 1] || ym;
        let label = `${name} ${y}`;
        if (idx === 0) {
            label = `${name} ${y} (Último mes completo)`;
        }
        const isSel = (ym === activeVal) ? 'selected' : '';
        optionsHtml += `<option value="${ym}" ${isSel}>${label}</option>`;
    });

    selectEl.innerHTML = optionsHtml;
    selectEl.value = activeVal;
}

/**
 * Controller for Hub View (#/reportes_rrhh)
 */
export async function loadRRHHHubView() {
    const monthSelect = document.getElementById('rrhh-hub-filter-month');
    const monthVal = monthSelect ? monthSelect.value : '';

    const btnCarga = document.getElementById('btn-goto-rrhh-carga');
    const user = state.currentUser || JSON.parse(localStorage.getItem('sgdu_user') || 'null');
    const perms = (user && user.permissions) || {};
    const isAdmin = !!(user && ['admin', 'administrador'].includes((user.role || '').toLowerCase()));
    const hasGlobal = isAdmin || !!perms['reportes_rrhh'];

    if (btnCarga) {
        const canUpload = !!(perms['carga_reportes_rrhh'] || isAdmin);
        btnCarga.style.display = canUpload ? 'inline-flex' : 'none';
    }

    const cardsContainer = document.getElementById('rrhh-hub-global-cards');
    if (cardsContainer) {
        cardsContainer.innerHTML = '<div style="text-align: center; padding: 2rem; grid-column: 1 / -1;"><span class="loader"></span><p style="margin-top: 0.5rem; color: #64748b;">Analizando control de asistencia general...</p></div>';
    }

    try {
        const res = await fetchRRHHData(monthVal);
        if (res && res.ok) {
            const data = await res.json();
            _currentReportData = data;
            window.currentRRHHReportData = data;

            if (monthSelect) {
                populateRRHHMonthDropdown(monthSelect, data.month, data.available_months);
            }

            renderHubCards(data, perms, hasGlobal);
        } else {
            if (cardsContainer) {
                cardsContainer.innerHTML = '<div style="text-align: center; padding: 2rem; color: #ef4444; grid-column: 1 / -1;">Error al consultar datos de RRHH.</div>';
            }
        }
    } catch (err) {
        console.error("Error loading RRHH hub view:", err);
        if (cardsContainer) {
            cardsContainer.innerHTML = '<div style="text-align: center; padding: 2rem; color: #ef4444; grid-column: 1 / -1;">Error de conexión con el servidor.</div>';
        }
    }
}

function renderHubCards(data, perms, hasGlobal) {
    const cardsContainer = document.getElementById('rrhh-hub-global-cards');
    const dgrocContainer = document.getElementById('rrhh-hub-cards-dgroc');
    const dgiurContainer = document.getElementById('rrhh-hub-cards-dgiur');
    const otrosContainer = document.getElementById('rrhh-hub-cards-otros');
    const otrosSection = document.getElementById('rrhh-hub-section-otros');

    const sectores = data.sectores || {};
    let totalAgentes = 0;
    let sumAsistencia = 0;
    let countAsistencia = 0;
    let totalMinutos = 0;
    let totalDiasHoras = 0;

    Object.values(sectores).forEach(s => {
        (s.agentes_list || []).forEach(a => {
            totalAgentes++;
            if (a.asistencia_pct !== '--' && typeof a.asistencia_pct === 'number' && !isNaN(a.asistencia_pct)) {
                sumAsistencia += a.asistencia_pct;
                countAsistencia++;
            }
            if (a.promedio_horas && a.promedio_horas !== '--') {
                const parts = a.promedio_horas.split(':');
                totalMinutos += parseInt(parts[0]) * 60 + parseInt(parts[1]);
                totalDiasHoras++;
            }
        });
    });

    const avgAsistencia = countAsistencia > 0 ? `${Math.round(sumAsistencia / countAsistencia)}%` : 'Sin planilla';
    const avgPromHoras = totalDiasHoras > 0
        ? (() => { const m = Math.round(totalMinutos / totalDiasHoras); return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`; })()
        : '--';

    if (cardsContainer) {
        cardsContainer.innerHTML = `
            <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 18px 22px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
                <div style="width: 50px; height: 50px; border-radius: 12px; background: #eff6ff; color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-users"></i></div>
                <div>
                    <span style="font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Total Agentes Evaluados</span>
                    <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: var(--primary-dark);">${totalAgentes}</h3>
                </div>
            </div>
            <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 18px 22px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
                <div style="width: 50px; height: 50px; border-radius: 12px; background: #ecfdf5; color: #10b981; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-calendar-check"></i></div>
                <div>
                    <span style="font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Asistencia Promedio General</span>
                    <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: #10b981;">${avgAsistencia}</h3>
                </div>
            </div>
            <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 18px 22px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
                <div style="width: 50px; height: 50px; border-radius: 12px; background: #fff7ed; color: #f97316; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-hourglass-half"></i></div>
                <div>
                    <span style="font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Promedio Horas Laboradas</span>
                    <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: #f97316;">${avgPromHoras} hs</h3>
                </div>
            </div>
        `;
    }

    const getSector = (gKey) => {
        const gClean = (gKey || '').toUpperCase().replace(/ /g, '_');
        for (const k in sectores) {
            if (k.toUpperCase().replace(/ /g, '_') === gClean) return sectores[k];
        }
        return null;
    };

    const renderCard = (gKey) => {
        const conf = GERENCIAS_CONFIG[gKey];
        if (!conf) return '';

        const hasPerm = hasGlobal || !!perms[`rrhh_${gKey}`];
        if (!hasPerm) return '';

        const sData = getSector(gKey);
        const agentesCount = sData ? (sData.agentes_list || []).length : 0;
        
        let secAsistencia = 0;
        let secMinutos = 0;
        let secDiasH = 0;
        let conAsistenciaCount = 0;
        if (sData && sData.agentes_list) {
            sData.agentes_list.forEach(a => {
                if (a.asistencia_pct !== '--' && typeof a.asistencia_pct === 'number') {
                    secAsistencia += a.asistencia_pct;
                    conAsistenciaCount++;
                }
                if (a.promedio_horas && a.promedio_horas !== '--') {
                    const parts = a.promedio_horas.split(':');
                    secMinutos += parseInt(parts[0]) * 60 + parseInt(parts[1]);
                    secDiasH++;
                }
            });
        }
        const pctAsistText = conAsistenciaCount > 0 ? `${Math.round(secAsistencia / conAsistenciaCount)}%` : 'Sin planilla';
        const promHsText = secDiasH > 0
            ? (() => { const m = Math.round(secMinutos / secDiasH); return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')} hs`; })()
            : '--';
        const franja = (sData && sData.earliest_ingreso && sData.latest_salida) ? `${sData.earliest_ingreso} - ${sData.latest_salida}` : '08:00 - 18:00';

        let colorAsist = '#10b981';
        if (conAsistenciaCount > 0) {
            const num = Math.round(secAsistencia / conAsistenciaCount);
            if (num < 80) colorAsist = '#ef4444';
            else if (num < 90) colorAsist = '#f59e0b';
        } else {
            colorAsist = '#94a3b8';
        }

        return `
            <div class="admin-card nav-card-rrhh" onclick="window.location.hash='#/reportes_rrhh/${gKey}'" style="background: white; border-radius: 14px; border: 1px solid #cbd5e1; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03); cursor: pointer; transition: all 0.25s ease; display: flex; flex-direction: column; justify-content: space-between; position: relative; overflow: hidden;"
                onmouseover="this.style.borderColor='${conf.color}'; this.style.transform='translateY(-3px)'; this.style.boxShadow='0 10px 15px -3px rgba(0,0,0,0.08)';"
                onmouseout="this.style.borderColor='#cbd5e1'; this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px -1px rgba(0,0,0,0.03)';">
                
                <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; background: ${conf.color};"></div>
                
                <div>
                    <!-- Header Card -->
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: ${conf.bg}; color: ${conf.color}; display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">
                                <i class="${conf.icon}"></i>
                            </div>
                            <div>
                                <h3 style="margin: 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.15rem; color: var(--primary-dark);">${conf.name}</h3>
                                <span style="font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase;">${conf.dir}</span>
                            </div>
                        </div>
                        <span style="background: ${conf.bg}; color: ${conf.color}; font-weight: 700; font-size: 0.75rem; padding: 3px 8px; border-radius: 6px;">
                            ${agentesCount} ${agentesCount === 1 ? 'analista' : 'analistas'}
                        </span>
                    </div>

                    <!-- Métricas resumidas -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px; background: #f8fafc; border: 1px solid #f1f5f9; padding: 10px 12px; border-radius: 8px;">
                        <div>
                            <span style="font-size: 0.72rem; color: #64748b; font-weight: 600; display: block;">Asistencia</span>
                            <strong style="font-size: 0.95rem; color: ${colorAsist}; font-family: 'Outfit';">${pctAsistText}</strong>
                        </div>
                        <div>
                            <span style="font-size: 0.72rem; color: #64748b; font-weight: 600; display: block;">Promedio Hs.</span>
                            <strong style="font-size: 0.95rem; color: #334155; font-family: 'Outfit';">${promHsText}</strong>
                        </div>
                    </div>
                </div>

                <!-- Footer Card / Botón de Acción -->
                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 12px;">
                    <span style="font-size: 0.75rem; color: #64748b;">
                        <i class="fa-solid fa-clock" style="color: #94a3b8; margin-right: 4px;"></i>${franja}
                    </span>
                    <span style="font-family: 'Outfit'; font-weight: 700; font-size: 0.82rem; color: ${conf.color}; display: flex; align-items: center; gap: 4px;">
                        Ir a la página <i class="fa-solid fa-arrow-right"></i>
                    </span>
                </div>
            </div>
        `;
    };

    let dgrocHtml = '';
    let dgiurHtml = '';
    let otrosHtml = '';

    ['catastro', 'instalaciones', 'conforme', 'contable', 'etapa_proyecto', 'aviso_obra'].forEach(k => {
        dgrocHtml += renderCard(k);
    });

    ['morfologia', 'aph', 'usos', 'publico_privado', 'copua', 'privada'].forEach(k => {
        dgiurHtml += renderCard(k);
    });

    const cardOtros = renderCard('otros');
    if (cardOtros) otrosHtml += cardOtros;

    if (dgrocContainer) dgrocContainer.innerHTML = dgrocHtml || '<p style="color: #94a3b8; font-style: italic; padding: 1rem;">Sin gerencias autorizadas en DGROC.</p>';
    if (dgiurContainer) dgiurContainer.innerHTML = dgiurHtml || '<p style="color: #94a3b8; font-style: italic; padding: 1rem;">Sin gerencias autorizadas en DGIUR.</p>';
    if (otrosContainer) otrosContainer.innerHTML = otrosHtml;
    if (otrosSection) otrosSection.style.display = (otrosHtml && getSector('otros')) ? 'block' : 'none';
}

/**
 * Controller for Individual Gerencia View (#/reportes_rrhh/:gerencia)
 */
export async function loadRRHHGerenciaView(gerenciaKey) {
    const cleanKey = (gerenciaKey || '').toLowerCase().trim();
    const conf = GERENCIAS_CONFIG[cleanKey] || {
        key: cleanKey,
        name: cleanKey.toUpperCase(),
        dir: 'Gerencia',
        icon: 'fa-solid fa-building',
        color: '#2563eb',
        bg: '#eff6ff'
    };

    const monthSelect = document.getElementById(`rrhh-${cleanKey}-filter-month`);
    const monthVal = monthSelect ? monthSelect.value : '';

    const cardsContainer = document.getElementById(`rrhh-${cleanKey}-cards`);
    const coverageContainer = document.getElementById(`rrhh-${cleanKey}-coverage-container`);
    const tbody = document.getElementById(`rrhh-${cleanKey}-table-body`);
    const countEl = document.getElementById(`rrhh-${cleanKey}-analistas-count`);
    const franjaText = document.getElementById(`rrhh-${cleanKey}-franja-text`);

    if (cardsContainer) {
        cardsContainer.innerHTML = '<div style="text-align: center; padding: 2rem; grid-column: 1 / -1;"><span class="loader"></span><p style="margin-top: 0.5rem; color: #64748b;">Consultando métricas de la gerencia...</p></div>';
    }

    try {
        const res = await fetchRRHHData(monthVal, cleanKey);
        if (res && res.ok) {
            const data = await res.json();
            if (monthSelect) {
                populateRRHHMonthDropdown(monthSelect, data.month, data.available_months);
            }

            const sectores = data.sectores || {};
            // Find matched sector
            let sData = null;
            const normReq = cleanKey.toUpperCase().replace(/ /g, '_');
            for (const k in sectores) {
                if (k.toUpperCase().replace(/ /g, '_') === normReq) {
                    sData = sectores[k];
                    break;
                }
            }

            if (!sData) {
                if (cardsContainer) cardsContainer.innerHTML = '<div style="text-align: center; padding: 2rem; color: #94a3b8; grid-column: 1 / -1;">No hay registros de analistas para esta gerencia en el mes seleccionado.</div>';
                if (coverageContainer) coverageContainer.innerHTML = '<p style="color: #94a3b8; font-style: italic; padding: 1rem; width: 100%; text-align: center;">Sin datos de cobertura horaria.</p>';
                if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2.5rem; color: #94a3b8;">No se encontraron registros de analistas.</td></tr>';
                if (countEl) countEl.innerText = '0 analistas registrados en este período.';
                if (franjaText) franjaText.innerText = 'Sin registros';
                return;
            }

            const agentesList = sData.agentes_list || [];
            const cleanStart = sData.earliest_ingreso || "08:00";
            const cleanEnd = sData.latest_salida || "18:00";

            if (franjaText) franjaText.innerText = `${cleanStart} - ${cleanEnd}`;
            if (countEl) countEl.innerText = `${agentesList.length} ${agentesList.length === 1 ? 'analista asignado' : 'analistas asignados'} a esta gerencia.`;

            let secAsistencia = 0;
            let secMinutos = 0;
            let secDiasH = 0;
            let conAsistenciaCount = 0;
            agentesList.forEach(a => {
                if (a.asistencia_pct !== '--' && typeof a.asistencia_pct === 'number') {
                    secAsistencia += a.asistencia_pct;
                    conAsistenciaCount++;
                }
                if (a.promedio_horas && a.promedio_horas !== '--') {
                    const parts = a.promedio_horas.split(':');
                    secMinutos += parseInt(parts[0]) * 60 + parseInt(parts[1]);
                    secDiasH++;
                }
            });

            const avgAsistenciaText = conAsistenciaCount > 0 ? `${Math.round(secAsistencia / conAsistenciaCount)}%` : 'Sin planilla';
            const avgPromHorasText = secDiasH > 0
                ? (() => { const m = Math.round(secMinutos / secDiasH); return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')} hs`; })()
                : '--';

            if (cardsContainer) {
                cardsContainer.innerHTML = `
                    <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 18px 22px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
                        <div style="width: 50px; height: 50px; border-radius: 12px; background: ${conf.bg}; color: ${conf.color}; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-users"></i></div>
                        <div>
                            <span style="font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Analistas Asignados</span>
                            <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: var(--primary-dark);">${agentesList.length}</h3>
                        </div>
                    </div>
                    <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 18px 22px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
                        <div style="width: 50px; height: 50px; border-radius: 12px; background: #ecfdf5; color: #10b981; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-calendar-check"></i></div>
                        <div>
                            <span style="font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Asistencia del Área</span>
                            <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: #10b981;">${avgAsistenciaText}</h3>
                        </div>
                    </div>
                    <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 18px 22px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
                        <div style="width: 50px; height: 50px; border-radius: 12px; background: #fff7ed; color: #f97316; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-hourglass-half"></i></div>
                        <div>
                            <span style="font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Promedio Horas Área</span>
                            <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: #f97316;">${avgPromHorasText}</h3>
                        </div>
                    </div>
                `;
            }

            // Hourly Coverage Bars
            let coverageBarsHtml = '';
            const hours = Object.keys(sData.hourly_coverage || {}).sort();
            const maxAgentsCount = Math.max(...Object.values(sData.hourly_coverage || {}), 1);

            hours.forEach(hr => {
                const count = sData.hourly_coverage[hr] || 0;
                const pctHeight = Math.round((count / maxAgentsCount) * 100);

                coverageBarsHtml += `
                    <div style="display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 35px; gap: 6px;">
                        <div title="${count} agentes activos a las ${hr}" style="width: 100%; height: 80px; background: #f1f5f9; border-radius: 4px; display: flex; align-items: flex-end; cursor: pointer;">
                            <div style="width: 100%; height: ${pctHeight}%; background: ${conf.color}; border-radius: 4px; transition: height 0.5s ease;"></div>
                        </div>
                        <span style="font-size: 0.72rem; color: #475569; font-weight: 700;">${hr}</span>
                        <span style="font-size: 0.68rem; color: #94a3b8; font-weight: 600;">${count}</span>
                    </div>
                `;
            });
            if (coverageContainer) coverageContainer.innerHTML = coverageBarsHtml;

            // Analyst Table Rows
            let agentsRows = '';
            agentesList.forEach(a => {
                let horasColor = '#94a3b8';
                let promHsDisplay = '--';
                if (a.promedio_horas && a.promedio_horas !== '--') {
                    promHsDisplay = `${a.promedio_horas} hs`;
                    const [hh, mm] = a.promedio_horas.split(':').map(Number);
                    const totalMin = hh * 60 + mm;
                    if (totalMin >= 420)       horasColor = '#10b981';
                    else if (totalMin >= 300)  horasColor = '#f59e0b';
                    else                       horasColor = '#ef4444';
                }

                let asistDisplay = '<span style="color: #94a3b8; font-size: 0.8rem; font-style: italic;">Sin planilla</span>';
                if (a.asistencia_pct !== '--' && typeof a.asistencia_pct === 'number') {
                    asistDisplay = `<span style="color: #10b981; font-weight: 800; font-size: 0.95rem;">${a.asistencia_pct}%</span>`;
                }

                let btnAction = `
                    <button type="button" disabled style="padding: 6px 12px; background: #f8fafc; color: #94a3b8; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.8rem; font-family: 'Outfit'; font-weight: 600; cursor: not-allowed; display: inline-flex; align-items: center; gap: 6px;">
                        <i class="fa-regular fa-clock"></i> Sin registros
                    </button>
                `;
                if (a.tiene_registros && a.cuil) {
                    btnAction = `
                        <button type="button" onclick="openRRHHAgentPage('${a.cuil}', '${encodeURIComponent(a.nombre)}', '${cleanKey}')" class="btn-action-view" style="padding: 7px 14px; background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; border-radius: 6px; cursor: pointer; font-size: 0.82rem; font-family: 'Outfit'; font-weight: 700; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px;">
                            <i class="fa-solid fa-calendar-days"></i> Ver Bitácora
                        </button>
                    `;
                }

                agentsRows += `
                    <tr class="rrhh-${cleanKey}-row" data-search="${(a.usuario + ' ' + a.nombre).toLowerCase()}" style="border-bottom: 1px solid #f1f5f9;">
                        <td style="padding: 12px 14px; font-weight: 700; color: var(--primary-dark); font-family: 'Outfit';">${(a.usuario || 'N/A').toUpperCase()}</td>
                        <td style="padding: 12px 14px; color: #334155; font-weight: 600;">${a.nombre}</td>
                        <td style="padding: 12px 14px; text-align: center; font-family: 'Outfit';">${asistDisplay}</td>
                        <td style="padding: 12px 14px; text-align: center; font-weight: 700; color: ${horasColor}; font-family: 'Outfit'; font-size: 0.95rem;">${promHsDisplay}</td>
                        <td style="padding: 12px 14px; text-align: center;">
                            ${btnAction}
                        </td>
                    </tr>
                `;
            });
            if (tbody) tbody.innerHTML = agentsRows || '<tr><td colspan="5" style="text-align: center; padding: 2.5rem; color: #94a3b8;">No se encontraron registros de analistas.</td></tr>';
        }
    } catch (err) {
        console.error(`Error in loadRRHHGerenciaView for ${cleanKey}:`, err);
        if (cardsContainer) cardsContainer.innerHTML = '<div style="text-align: center; padding: 2rem; color: #ef4444; grid-column: 1 / -1;">Error al consultar datos de la gerencia.</div>';
    }
}

export function filterRRHHGerenciaTable(gerenciaKey, query) {
    const q = (query || '').toLowerCase().trim();
    document.querySelectorAll(`.rrhh-${gerenciaKey}-row`).forEach(row => {
        const search = row.getAttribute('data-search') || '';
        if (!q || search.includes(q)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

/**
 * Controller for Excel Upload view (#/reportes_rrhh/carga)
 */
export function initRRHHCargaView() {
    clearRRHHFile();
}

/**
 * Modal: Agent Attendance Log / Calendar
 */
export function openRRHHAgentPage(cuil, nameEncoded, gerenciaKey = '') {
    _rrhhCurrentCuil  = cuil;
    _rrhhCurrentName  = decodeURIComponent(nameEncoded);
    
    let monthInput = null;
    if (gerenciaKey) {
        monthInput = document.getElementById(`rrhh-${gerenciaKey}-filter-month`);
    }
    if (!monthInput) {
        monthInput = document.getElementById('rrhh-hub-filter-month');
    }
    _rrhhCurrentMonth = monthInput?.value || new Date().toISOString().substring(0, 7);

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
        const token = state.authToken || localStorage.getItem('sgdu_token') || '';
        const url = `${API_BASE}/rrhh/reporte/detalle-agente?cuil=${_rrhhCurrentCuil}&month=${_rrhhCurrentMonth}`;
        const res = await (window.def_fetch ? window.def_fetch(url) : fetch(url, { headers: { 'Authorization': `Bearer ${token}` } }));
        if (!res || !res.ok) throw new Error('fetch failed');
        _rrhhAgentLogs = await res.json();
        _renderRRHHCalendar();
    } catch (e) {
        const grid = document.getElementById('rrhh-calendar-grid');
        if (grid) grid.innerHTML = '<p style="color:#ef4444;text-align:center;">Error al cargar los datos de la bitácora.</p>';
    }
}

function _renderRRHHCalendar() {
    const grid = document.getElementById('rrhh-calendar-grid');
    if (!grid) return;

    const [yStr, mStr] = _rrhhCurrentMonth.split('-');
    const year  = parseInt(yStr);
    const month = parseInt(mStr);

    const byDate = {};
    _rrhhAgentLogs.forEach(l => { byDate[l.fecha] = l; });

    const monthNames = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    const monthName  = monthNames[month - 1];

    const firstDay  = new Date(year, month - 1, 1).getDay();
    const daysInMonth = new Date(year, month, 0).getDate();
    const startOffset = (firstDay === 0) ? 6 : firstDay - 1;

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

    for (let i = 0; i < startOffset; i++) {
        calHTML += '<div></div>';
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr  = `${year}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
        const jsDate   = new Date(year, month - 1, day);
        const dayOfWeek = jsDate.getDay();
        const isWeekend = (dayOfWeek === 0 || dayOfWeek === 6);
        const log       = byDate[dateStr];

        let bgColor   = '#f1f5f9';
        let textColor = '#64748b';
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
        const token = state.authToken || localStorage.getItem('sgdu_token') || '';
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
            window.location.hash = '#/reportes_rrhh';
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

// Global exposures
window.loadRRHHHubView = loadRRHHHubView;
window.loadRRHHGerenciaView = loadRRHHGerenciaView;
window.filterRRHHGerenciaTable = filterRRHHGerenciaTable;
window.initRRHHCargaView = initRRHHCargaView;
window.openRRHHAgentPage = openRRHHAgentPage;
window.closeRRHHAgentPage = closeRRHHAgentPage;
window._rrhhShowDayDetail = _rrhhShowDayDetail;
window.handleRRHHDrop = handleRRHHDrop;
window.handleRRHHFileSelect = handleRRHHFileSelect;
window.clearRRHHFile = clearRRHHFile;
window.uploadRRHHExcel = uploadRRHHExcel;
