import { state } from '../../../state.js';
import rrhhHtml from './rrhh.html?raw';

export const GERENCIAS_CONFIG = {
    // DGROC
    catastro: { key: 'catastro', name: 'Catastro', dir: 'DGROC', icon: 'fa-solid fa-map-location-dot', color: '#2563eb', bg: '#eff6ff' },
    instalaciones: { key: 'instalaciones', name: 'Instalaciones', dir: 'DGROC', icon: 'fa-solid fa-bolt', color: '#d97706', bg: '#fffbeb' },
    conforme: { key: 'conforme', name: 'Conforme', dir: 'DGROC', icon: 'fa-solid fa-clipboard-check', color: '#16a34a', bg: '#f0fdf4' },
    contable: { key: 'contable', name: 'Contable', dir: 'DGROC', icon: 'fa-solid fa-calculator', color: '#0284c7', bg: '#f0f9ff' },
    etapa_proyecto: { key: 'etapa_proyecto', name: 'Etapa Proyecto', dir: 'DGROC', icon: 'fa-solid fa-building-columns', color: '#7c3aed', bg: '#f5f3ff' },
    aviso_obra: { key: 'aviso_obra', name: 'Aviso de Obra', dir: 'DGROC', icon: 'fa-solid fa-hard-hat', color: '#db2777', bg: '#fdf2f8' },

    // DGIUR
    morfologia: { key: 'morfologia', name: 'Morfología', dir: 'DGIUR', icon: 'fa-solid fa-cubes', color: '#0891b2', bg: '#ecfeff' },
    aph: { key: 'aph', name: 'APH', dir: 'DGIUR', icon: 'fa-solid fa-landmark', color: '#b45309', bg: '#fef3c7' },
    usos: { key: 'usos', name: 'Usos', dir: 'DGIUR', icon: 'fa-solid fa-shapes', color: '#0d9488', bg: '#f0fdfa' },
    publico_privado: { key: 'publico_privado', name: 'Público Privado', dir: 'DGIUR', icon: 'fa-solid fa-handshake', color: '#4f46e5', bg: '#eef2ff' },
    copua: { key: 'copua', name: 'COPUA', dir: 'DGIUR', icon: 'fa-solid fa-users-gear', color: '#3b82f6', bg: '#eff6ff' },
    privada: { key: 'privada', name: 'Privada', dir: 'DGIUR', icon: 'fa-solid fa-key', color: '#65a30d', bg: '#f7fee7' },

    // OTROS
    otros: { key: 'otros', name: 'Otros / General', dir: 'OTROS', icon: 'fa-solid fa-folder-tree', color: '#64748b', bg: '#f8fafc' }
};

let _currentRRHHGerencia = null;
let _currentReportData = null;
let _rrhhAgentLogs = [];
let _rrhhCurrentCuil = '';
let _rrhhCurrentName = '';
let _rrhhCurrentMonth = '';
let selectedRRHHFile = null;

export function renderRRHHView() {
    const container = document.getElementById('reportes_rrhh');
    if (container) {
        container.innerHTML = rrhhHtml;
    }
    initRRHHReportView();
}

export function initRRHHReportView(gerenciaKey = null) {
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
        const user = state.currentUser || JSON.parse(localStorage.getItem('sgdu_user') || 'null');
        const perms = (user && user.permissions) || {};
        const canUpload = !!(user && (perms['carga_reportes_rrhh'] || ['admin', 'administrador'].includes((user.role || '').toLowerCase())));
        tabCargaBtn.style.display = canUpload ? 'inline-block' : 'none';
    }

    if (gerenciaKey) {
        _currentRRHHGerencia = gerenciaKey.toLowerCase().trim();
    } else {
        // Detect from current hash if e.g. #/reportes_rrhh/catastro
        const hash = window.location.hash.substring(2);
        const parts = hash.split('/');
        if (parts[0] === 'reportes_rrhh' && parts[1]) {
            _currentRRHHGerencia = parts[1].toLowerCase().trim();
        } else {
            _currentRRHHGerencia = null;
        }
    }

    switchRRHHTab('reporte');
    loadRRHHReport();
}

export function showRRHHHub() {
    _currentRRHHGerencia = null;
    window.location.hash = '#/reportes_rrhh';
    updateBreadcrumbsAndTitles();
    renderActiveView();
}

export function showRRHHGerenciaView(gerenciaKey) {
    _currentRRHHGerencia = (gerenciaKey || '').toLowerCase().trim();
    window.location.hash = `#/reportes_rrhh/${_currentRRHHGerencia}`;
    updateBreadcrumbsAndTitles();
    renderActiveView();
}

function updateBreadcrumbsAndTitles() {
    const sep = document.getElementById('rrhh-bc-sep');
    const bcGerencia = document.getElementById('rrhh-bc-gerencia');
    const toggleActions = document.getElementById('rrhh-view-toggle-actions');
    const mainTitle = document.getElementById('rrhh-main-title');
    const mainSubtitle = document.getElementById('rrhh-main-subtitle');

    if (_currentRRHHGerencia) {
        const gConfig = GERENCIAS_CONFIG[_currentRRHHGerencia] || { name: _currentRRHHGerencia.toUpperCase(), dir: 'Gerencia' };
        if (sep) sep.style.display = 'inline';
        if (bcGerencia) {
            bcGerencia.innerText = gConfig.name;
            bcGerencia.style.display = 'inline';
        }
        if (toggleActions) toggleActions.style.display = 'block';
        if (mainTitle) mainTitle.innerText = `${gConfig.name} — Reporte RRHH`;
        if (mainSubtitle) mainSubtitle.innerText = `Control de asistencia y cobertura horaria para la Gerencia de ${gConfig.name} (${gConfig.dir}).`;
    } else {
        if (sep) sep.style.display = 'none';
        if (bcGerencia) bcGerencia.style.display = 'none';
        if (toggleActions) toggleActions.style.display = 'none';
        if (mainTitle) mainTitle.innerText = `Reporte RRHH`;
        if (mainSubtitle) mainSubtitle.innerText = `Control de asistencia, puntualidad y cobertura horaria del personal por gerencia.`;
    }
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
    const hubContainer = document.getElementById('rrhh-hub-container');
    const detailContainer = document.getElementById('rrhh-gerencia-detail-container');
    const cardsContainer = document.getElementById('rrhh-global-cards');
    const monthEl = document.getElementById('rrhh-filter-month');
    const monthVal = monthEl ? monthEl.value : '';

    if (cardsContainer) cardsContainer.innerHTML = '<div style="text-align: center; padding: 2rem; grid-column: 1 / -1;"><span class="loader"></span><p style="margin-top: 0.5rem; color: #64748b;">Cargando datos de asistencia...</p></div>';

    try {
        const API_BASE = window.API_BASE || '/api';
        const url = monthVal ? `${API_BASE}/rrhh/reporte?month=${monthVal}` : `${API_BASE}/rrhh/reporte`;
        const res = await (window.def_fetch ? window.def_fetch(url) : fetch(url, { headers: { 'Authorization': `Bearer ${state.authToken || localStorage.getItem('sgdu_token') || ''}` } }));

        if (res && res.ok) {
            const data = await res.json();
            _currentReportData = data;
            window.currentRRHHReportData = data;

            if (data.month && monthEl) {
                monthEl.value = data.month;
            }

            updateBreadcrumbsAndTitles();
            renderActiveView();
        } else {
            if (cardsContainer) cardsContainer.innerHTML = '<div style="text-align: center; padding: 2rem; color: #ef4444; grid-column: 1 / -1;">Error al cargar datos del reporte de asistencia.</div>';
        }
    } catch (err) {
        console.error("Error loading RRHH report:", err);
        if (cardsContainer) cardsContainer.innerHTML = '<div style="text-align: center; padding: 2rem; color: #ef4444; grid-column: 1 / -1;">Error de red al conectar con el servidor.</div>';
    }
}

function renderActiveView() {
    if (!_currentReportData) return;

    if (_currentRRHHGerencia) {
        renderGerenciaDetailView(_currentRRHHGerencia);
    } else {
        renderHubView();
    }
}

function getSectorData(gerenciaKey) {
    if (!_currentReportData || !_currentReportData.sectores) return null;
    const gClean = (gerenciaKey || '').toUpperCase().replace(/ /g, '_');
    
    // Direct or normalized lookup
    for (const k in _currentReportData.sectores) {
        const norm = k.toUpperCase().replace(/ /g, '_');
        if (norm === gClean) return _currentReportData.sectores[k];
    }
    return null;
}

function renderHubView() {
    const hubContainer = document.getElementById('rrhh-hub-container');
    const detailContainer = document.getElementById('rrhh-gerencia-detail-container');
    const cardsContainer = document.getElementById('rrhh-global-cards');

    if (hubContainer) hubContainer.style.display = 'block';
    if (detailContainer) detailContainer.style.display = 'none';

    const user = state.currentUser || JSON.parse(localStorage.getItem('sgdu_user') || 'null');
    const perms = (user && user.permissions) || {};
    const isAdmin = !!(user && ['admin', 'administrador'].includes((user.role || '').toLowerCase()));
    const hasGlobal = isAdmin || !!perms['reportes_rrhh'];

    // Calculate Global Totals
    let totalAgentes = 0;
    let sumAsistencia = 0;
    let totalMinutos = 0;
    let totalDiasHoras = 0;

    const sectores = _currentReportData.sectores || {};
    Object.values(sectores).forEach(s => {
        (s.agentes_list || []).forEach(a => {
            totalAgentes++;
            sumAsistencia += a.asistencia_pct;
            if (a.promedio_horas && a.promedio_horas !== '--') {
                const parts = a.promedio_horas.split(':');
                totalMinutos += parseInt(parts[0]) * 60 + parseInt(parts[1]);
                totalDiasHoras++;
            }
        });
    });

    const avgAsistencia = totalAgentes > 0 ? Math.round(sumAsistencia / totalAgentes) : 100;
    const avgPromHoras = totalDiasHoras > 0
        ? (() => { const m = Math.round(totalMinutos / totalDiasHoras); return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`; })()
        : '--';

    // Render Global KPI Cards
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
                    <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: #10b981;">${avgAsistencia}%</h3>
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

    const dgrocContainer = document.getElementById('rrhh-cards-dgroc');
    const dgiurContainer = document.getElementById('rrhh-cards-dgiur');
    const otrosContainer = document.getElementById('rrhh-cards-otros');
    const otrosSection = document.getElementById('rrhh-section-otros');

    let dgrocHtml = '';
    let dgiurHtml = '';
    let otrosHtml = '';
    let dgrocVisible = 0;
    let dgiurVisible = 0;

    const renderCard = (gKey) => {
        const conf = GERENCIAS_CONFIG[gKey];
        if (!conf) return '';

        const hasPerm = hasGlobal || !!perms[`rrhh_${gKey}`];
        if (!hasPerm) return '';

        const sData = getSectorData(gKey);
        const agentesCount = sData ? (sData.agentes_list || []).length : 0;
        
        let secAsistencia = 0;
        let secMinutos = 0;
        let secDiasH = 0;
        if (sData && sData.agentes_list) {
            sData.agentes_list.forEach(a => {
                secAsistencia += a.asistencia_pct;
                if (a.promedio_horas && a.promedio_horas !== '--') {
                    const parts = a.promedio_horas.split(':');
                    secMinutos += parseInt(parts[0]) * 60 + parseInt(parts[1]);
                    secDiasH++;
                }
            });
        }
        const pctAsist = agentesCount > 0 ? Math.round(secAsistencia / agentesCount) : 100;
        const promHs = secDiasH > 0
            ? (() => { const m = Math.round(secMinutos / secDiasH); return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`; })()
            : '--';
        const franja = (sData && sData.earliest_ingreso && sData.latest_salida) ? `${sData.earliest_ingreso} - ${sData.latest_salida}` : '08:00 - 18:00';

        let colorAsist = '#10b981';
        if (pctAsist < 80) colorAsist = '#ef4444';
        else if (pctAsist < 90) colorAsist = '#f59e0b';

        return `
            <div class="admin-card nav-card-rrhh" onclick="showRRHHGerenciaView('${gKey}')" style="background: white; border-radius: 14px; border: 1px solid #cbd5e1; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03); cursor: pointer; transition: all 0.25s ease; display: flex; flex-direction: column; justify-content: space-between; position: relative; overflow: hidden;"
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
                                <h3 style="margin: 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.2rem; color: var(--primary-dark);">${conf.name}</h3>
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
                            <strong style="font-size: 1rem; color: ${colorAsist}; font-family: 'Outfit';">${pctAsist}%</strong>
                        </div>
                        <div>
                            <span style="font-size: 0.72rem; color: #64748b; font-weight: 600; display: block;">Promedio Hs.</span>
                            <strong style="font-size: 1rem; color: #334155; font-family: 'Outfit';">${promHs} hs</strong>
                        </div>
                    </div>
                </div>

                <!-- Footer Card / Botón de Acción -->
                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 12px;">
                    <span style="font-size: 0.75rem; color: #64748b;">
                        <i class="fa-solid fa-clock" style="color: #94a3b8; margin-right: 4px;"></i>${franja}
                    </span>
                    <span style="font-family: 'Outfit'; font-weight: 700; font-size: 0.82rem; color: ${conf.color}; display: flex; align-items: center; gap: 4px;">
                        Ver Detalle <i class="fa-solid fa-arrow-right"></i>
                    </span>
                </div>
            </div>
        `;
    };

    // DGROC Gerencias
    ['catastro', 'instalaciones', 'conforme', 'contable', 'etapa_proyecto', 'aviso_obra'].forEach(k => {
        const card = renderCard(k);
        if (card) {
            dgrocHtml += card;
            dgrocVisible++;
        }
    });

    // DGIUR Gerencias
    ['morfologia', 'aph', 'usos', 'publico_privado', 'copua', 'privada'].forEach(k => {
        const card = renderCard(k);
        if (card) {
            dgiurHtml += card;
            dgiurVisible++;
        }
    });

    // OTROS Gerencias (si existen registros)
    const cardOtros = renderCard('otros');
    if (cardOtros) {
        otrosHtml += cardOtros;
    }

    if (dgrocContainer) dgrocContainer.innerHTML = dgrocHtml || '<p style="color: #94a3b8; font-style: italic; padding: 1rem;">Sin gerencias autorizadas en DGROC.</p>';
    if (dgiurContainer) dgiurContainer.innerHTML = dgiurHtml || '<p style="color: #94a3b8; font-style: italic; padding: 1rem;">Sin gerencias autorizadas en DGIUR.</p>';
    if (otrosContainer) otrosContainer.innerHTML = otrosHtml;

    if (otrosSection) {
        otrosSection.style.display = (otrosHtml && getSectorData('otros')) ? 'block' : 'none';
    }
}

function renderGerenciaDetailView(gerenciaKey) {
    const hubContainer = document.getElementById('rrhh-hub-container');
    const detailContainer = document.getElementById('rrhh-gerencia-detail-container');
    const content = document.getElementById('rrhh-gerencia-content');
    const cardsContainer = document.getElementById('rrhh-global-cards');

    if (hubContainer) hubContainer.style.display = 'none';
    if (detailContainer) detailContainer.style.display = 'block';

    const conf = GERENCIAS_CONFIG[gerenciaKey] || {
        key: gerenciaKey,
        name: gerenciaKey.toUpperCase(),
        dir: 'Gerencia',
        icon: 'fa-solid fa-building',
        color: 'var(--primary)',
        bg: '#eff6ff'
    };

    const sData = getSectorData(gerenciaKey);

    if (!sData) {
        if (cardsContainer) cardsContainer.innerHTML = '';
        if (content) {
            content.innerHTML = `
                <div class="admin-card" style="background: white; border-radius: 14px; border: 1px solid #cbd5e1; padding: 40px; text-align: center;">
                    <div style="font-size: 3rem; color: #94a3b8; margin-bottom: 1rem;"><i class="fa-solid fa-users-slash"></i></div>
                    <h3 style="color: var(--primary-dark); margin: 0 0 8px 0; font-family: 'Outfit'; font-weight: 800;">No hay datos para la gerencia ${conf.name}</h3>
                    <p style="color: #64748b; margin: 0 0 20px 0;">No se registran marcaciones ni analistas vinculados para el período seleccionado.</p>
                    <button type="button" onclick="showRRHHHub()" class="btn-primary" style="padding: 10px 20px; font-weight: 700; border-radius: 8px; border: none; cursor: pointer; background: var(--primary); color: white;">
                        <i class="fa-solid fa-arrow-left"></i> Volver a Todas las Gerencias
                    </button>
                </div>
            `;
        }
        return;
    }

    const agentesList = sData.agentes_list || [];
    const cleanStart = sData.earliest_ingreso || "08:00";
    const cleanEnd = sData.latest_salida || "18:00";

    let secAsistencia = 0;
    let secMinutos = 0;
    let secDiasH = 0;
    agentesList.forEach(a => {
        secAsistencia += a.asistencia_pct;
        if (a.promedio_horas && a.promedio_horas !== '--') {
            const parts = a.promedio_horas.split(':');
            secMinutos += parseInt(parts[0]) * 60 + parseInt(parts[1]);
            secDiasH++;
        }
    });

    const avgAsistencia = agentesList.length > 0 ? Math.round(secAsistencia / agentesList.length) : 100;
    const avgPromHoras = secDiasH > 0
        ? (() => { const m = Math.round(secMinutos / secDiasH); return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`; })()
        : '--';

    // Sector Specific KPI Cards in Global Container
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
                    <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: #10b981;">${avgAsistencia}%</h3>
                </div>
            </div>
            <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 18px 22px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
                <div style="width: 50px; height: 50px; border-radius: 12px; background: #fff7ed; color: #f97316; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-hourglass-half"></i></div>
                <div>
                    <span style="font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Promedio Horas Área</span>
                    <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: #f97316;">${avgPromHoras} hs</h3>
                </div>
            </div>
        `;
    }

    // Generate Hourly Coverage distribution map HTML
    let coverageBarsHtml = '';
    const hours = Object.keys(sData.hourly_coverage || {}).sort();
    const maxAgentsCount = Math.max(...Object.values(sData.hourly_coverage || {}), 1);

    hours.forEach(hr => {
        const count = sData.hourly_coverage[hr] || 0;
        const pctHeight = Math.round((count / maxAgentsCount) * 100);

        coverageBarsHtml += `
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 35px; gap: 6px;">
                <div title="${count} agentes a las ${hr}" style="width: 100%; height: 80px; background: #f1f5f9; border-radius: 4px; display: flex; align-items: flex-end; cursor: pointer;">
                    <div style="width: 100%; height: ${pctHeight}%; background: ${conf.color}; border-radius: 4px; transition: height 0.5s ease;"></div>
                </div>
                <span style="font-size: 0.72rem; color: #475569; font-weight: 700;">${hr}</span>
                <span style="font-size: 0.68rem; color: #94a3b8; font-weight: 600;">${count}</span>
            </div>
        `;
    });

    // Generate agents table rows
    let agentsRows = '';
    agentesList.forEach(a => {
        let horasColor = '#94a3b8';
        if (a.promedio_horas && a.promedio_horas !== '--') {
            const [hh, mm] = a.promedio_horas.split(':').map(Number);
            const totalMin = hh * 60 + mm;
            if (totalMin >= 420)       horasColor = '#10b981';
            else if (totalMin >= 300)  horasColor = '#f59e0b';
            else                       horasColor = '#ef4444';
        }

        agentsRows += `
            <tr class="rrhh-agent-row" data-search="${(a.usuario + ' ' + a.nombre).toLowerCase()}" style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 12px 14px; font-weight: 700; color: var(--primary-dark); font-family: 'Outfit';">${(a.usuario || 'N/A').toUpperCase()}</td>
                <td style="padding: 12px 14px; color: #334155; font-weight: 600;">${a.nombre}</td>
                <td style="padding: 12px 14px; text-align: center; font-weight: 700; color: #10b981; font-family: 'Outfit'; font-size: 0.95rem;">${a.asistencia_pct}%</td>
                <td style="padding: 12px 14px; text-align: center; font-weight: 700; color: ${horasColor}; font-family: 'Outfit'; font-size: 0.95rem;">${a.promedio_horas} hs</td>
                <td style="padding: 12px 14px; text-align: center;">
                    <button type="button" onclick="openRRHHAgentPage('${a.cuil}', '${encodeURIComponent(a.nombre)}')" class="btn-action-view" style="padding: 7px 14px; background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; border-radius: 6px; cursor: pointer; font-size: 0.82rem; font-family: 'Outfit'; font-weight: 700; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px;">
                        <i class="fa-solid fa-calendar-days"></i> Ver Bitácora
                    </button>
                </td>
            </tr>
        `;
    });

    if (content) {
        content.innerHTML = `
            <div class="admin-card" style="background: white; border-radius: 16px; border: 1px solid #cbd5e1; padding: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.04); margin-bottom: 2rem;">
                <!-- Header de Gerencia -->
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 14px; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 48px; height: 48px; border-radius: 12px; background: ${conf.bg}; color: ${conf.color}; display: flex; align-items: center; justify-content: center; font-size: 1.4rem;">
                            <i class="${conf.icon}"></i>
                        </div>
                        <div>
                            <h2 style="margin: 0; color: var(--primary-dark); font-family: 'Outfit'; font-weight: 800; font-size: 1.4rem;">
                                Gerencia de ${conf.name}
                            </h2>
                            <p style="margin: 2px 0 0 0; font-size: 0.82rem; color: #64748b;">${conf.dir} &bull; Análisis de jornada, puntualidad y cobertura horaria.</p>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                        <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 14px; display: inline-flex; align-items: center; gap: 8px; font-family: 'Outfit'; font-size: 0.85rem;">
                            <i class="fa-solid fa-business-time" style="color: ${conf.color};"></i>
                            <span style="font-weight: 600; color: #334155;">Franja Cubierta:</span>
                            <strong style="color: var(--primary-dark);">${cleanStart} - ${cleanEnd}</strong>
                        </div>
                        <button type="button" onclick="showRRHHHub()" class="btn-secondary" style="padding: 8px 14px; font-size: 0.85rem; font-weight: 700; border-radius: 8px; border: 1px solid #cbd5e1; cursor: pointer; background: white; color: #334155; display: inline-flex; align-items: center; gap: 6px;">
                            <i class="fa-solid fa-arrow-left"></i> Volver a Gerencias
                        </button>
                    </div>
                </div>

                <!-- 1. Mapa de Cobertura Horaria -->
                <div style="margin-bottom: 2.2rem;">
                    <h4 style="margin: 0 0 1rem 0; color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700; font-size: 1rem; display: flex; align-items: center; gap: 8px;">
                        <i class="fa-solid fa-chart-simple" style="color: ${conf.color};"></i> Cobertura Horaria (Agentes activos por franja de hora)
                    </h4>
                    <div style="display: flex; gap: 8px; overflow-x: auto; padding: 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px;">
                        ${coverageBarsHtml}
                    </div>
                </div>

                <!-- 2. Tabla de Analistas -->
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 12px;">
                        <h4 style="margin: 0; color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700; font-size: 1rem; display: flex; align-items: center; gap: 8px;">
                            <i class="fa-solid fa-user-check" style="color: ${conf.color};"></i> Personal Asignado y Desempeño (${agentesList.length})
                        </h4>
                        <div style="position: relative; width: 260px;">
                            <i class="fa-solid fa-magnifying-glass" style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: #94a3b8; font-size: 0.85rem;"></i>
                            <input type="text" id="rrhh-agent-search" placeholder="Buscar analista o usuario..." oninput="filterRRHHAgentRows(this.value)" style="width: 100%; padding: 7px 10px 7px 30px; border: 1px solid #cbd5e1; border-radius: 6px; font-family: 'Outfit'; font-size: 0.85rem; outline: none;">
                        </div>
                    </div>
                    <div class="table-responsive" style="border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden;">
                        <table class="report-table" style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="border-bottom: 2px solid #cbd5e1; background: #f8fafc; text-align: left; font-size: 0.82rem;">
                                    <th style="padding: 12px 14px; font-weight: 700; color: #475569;">Usuario SADE</th>
                                    <th style="padding: 12px 14px; font-weight: 700; color: #475569;">Nombre y Apellido</th>
                                    <th style="padding: 12px 14px; font-weight: 700; color: #475569; text-align: center;">Asistencia</th>
                                    <th style="padding: 12px 14px; font-weight: 700; color: #475569; text-align: center;">Promedio Horas</th>
                                    <th style="padding: 12px 14px; font-weight: 700; color: #475569; text-align: center;">Acción</th>
                                </tr>
                            </thead>
                            <tbody style="font-size: 0.88rem;">
                                ${agentsRows || '<tr><td colspan="5" style="text-align: center; padding: 2rem; color: #94a3b8;">No hay analistas registrados en este sector.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
}

export function filterRRHHAgentRows(query) {
    const q = (query || '').toLowerCase().trim();
    document.querySelectorAll('.rrhh-agent-row').forEach(row => {
        const search = row.getAttribute('data-search') || '';
        if (!q || search.includes(q)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
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
        const res = await (window.def_fetch ? window.def_fetch(`${API_BASE}/rrhh/reporte/detalle-agente?cuil=${_rrhhCurrentCuil}&month=${_rrhhCurrentMonth}`) : fetch(`${API_BASE}/rrhh/reporte/detalle-agente?cuil=${_rrhhCurrentCuil}&month=${_rrhhCurrentMonth}`, { headers: { 'Authorization': `Bearer ${state.authToken || localStorage.getItem('sgdu_token') || ''}` } }));
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

// Global exposures
window.showRRHHHub = showRRHHHub;
window.showRRHHGerenciaView = showRRHHGerenciaView;
window.initRRHHReportView = initRRHHReportView;
window.loadRRHHReport = loadRRHHReport;
window.switchRRHHTab = switchRRHHTab;
window.filterRRHHAgentRows = filterRRHHAgentRows;
window.openRRHHAgentPage = openRRHHAgentPage;
window.closeRRHHAgentPage = closeRRHHAgentPage;
window._rrhhShowDayDetail = _rrhhShowDayDetail;
window.handleRRHHDrop = handleRRHHDrop;
window.handleRRHHFileSelect = handleRRHHFileSelect;
window.clearRRHHFile = clearRRHHFile;
window.uploadRRHHExcel = uploadRRHHExcel;
