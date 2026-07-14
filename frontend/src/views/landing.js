import { state } from '../state.js';
import landingHtml from './landing.html?raw';

export function renderLandingView() {
    const container = document.getElementById('landing');
    if (container) {
        container.innerHTML = landingHtml;
    }
    loadLandingStats();
}

// KPI Card template helper
function _kpiCard({ icon, iconBg, iconColor, label, value, sub, valueColor, gridStyle, tall }) {
    const valFontSize = tall ? '2.8rem' : '1.75rem';
    const iconSize    = tall ? '56px'  : '44px';
    const iconFontSz  = tall ? '1.4rem': '1.15rem';
    return `
        <div class="landing-kpi-card" style="${gridStyle || ''}; ${tall ? 'justify-content:center; align-items:center; text-align:center;' : ''}">
            <div class="landing-kpi-icon" style="background:${iconBg}; color:${iconColor}; width:${iconSize}; height:${iconSize}; font-size:${iconFontSz}; ${tall ? 'margin: 0 auto 8px auto;' : ''}">
                <i class="${icon}"></i>
            </div>
            <span class="landing-kpi-label" style="${tall ? 'text-align:center; margin-bottom:8px; display:block;' : ''}">${label}</span>
            <span class="landing-kpi-value" style="color:${valueColor || '#1e293b'}; font-size:${valFontSize};" data-target="${value}">${value.toLocaleString('es-AR')}</span>
            ${sub ? `<span class="landing-kpi-sub" style="${tall ? 'text-align:center; font-size:0.9rem; margin-top:6px;' : ''}">${sub}</span>` : ''}
        </div>
    `;
}

// Direction KPI Card helper (DGROC vs DGIUR)
function _directionCard({ label, mesVal, acumVal, showAcum = true, intVal = null, efVal = null, neVal = null }) {
    return `
        <div class="landing-kpi-card" style="padding: 16px; display: flex; flex-direction: column; gap: 12px; transition: transform 0.2s, box-shadow 0.2s;">
            <div style="display: flex; align-items: center;">
                <span style="font-size: 0.8rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">${label}</span>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; border-top: 1px solid #f1f5f9; padding-top: 10px; margin-top: 4px;">
                <div>
                    <span style="font-size: 1.45rem; font-weight: 800; color: #1e293b; display: block;" class="landing-kpi-value" data-target="${mesVal || 0}">${(mesVal || 0).toLocaleString('es-AR')}</span>
                    <span style="font-size: 0.65rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.3px;">${intVal !== null && intVal !== undefined ? 'Total' : 'Mes'}</span>
                </div>
                ${intVal !== null && intVal !== undefined ? `
                <div style="border-left: 1px dashed #e2e8f0; padding-left: 12px;">
                    <span style="font-size: 1.45rem; font-weight: 800; color: #64748b; display: block;" class="landing-kpi-value" data-target="${intVal}">${intVal.toLocaleString('es-AR')}</span>
                    <span style="font-size: 0.65rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.3px;">Interv.</span>
                </div>
                ` : showAcum ? `
                <div style="border-left: 1px dashed #e2e8f0; padding-left: 12px;">
                    <span style="font-size: 1.45rem; font-weight: 800; color: var(--primary); display: block;" class="landing-kpi-value" data-target="${acumVal || 0}">${(acumVal || 0).toLocaleString('es-AR')}</span>
                    <span style="font-size: 0.65rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.3px;">Mar-Hoy</span>
                    ${(efVal !== null && efVal !== undefined && neVal !== null && neVal !== undefined) ? `
                    <span style="font-size: 0.6rem; font-weight: 600; color: #94a3b8; display: block; margin-top: 3px; line-height: 1.1;">
                        Ef: ${efVal.toLocaleString('es-AR')}<br>No Ef: ${neVal.toLocaleString('es-AR')}
                    </span>
                    ` : ''}
                </div>
                ` : `
                <div style="border-left: 1px dashed #e2e8f0; padding-left: 12px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 0.68rem; font-weight: 600; color: #94a3b8; font-style: italic; text-transform: uppercase;">Stock vivo</span>
                </div>
                `}
            </div>
        </div>
    `;
}

function _mesLabel(mesStr) {
    if (!mesStr) return '';
    const [y, m] = mesStr.split('-').map(Number);
    const meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
    return `(${meses[m - 1]} ${y})`;
}

// Animate numbers
function _animateCount(el, target) {
    let start = 0;
    const duration = 800; 
    const startTime = performance.now();

    function update(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // easeOutQuad
        const ease = progress * (2 - progress);
        const current = Math.floor(ease * target);
        
        el.textContent = current.toLocaleString('es-AR');
        
        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            el.textContent = target.toLocaleString('es-AR');
        }
    }
    requestAnimationFrame(update);
}

export async function loadLandingStats() {
    if (!localStorage.getItem('sgdu_token')) return;
    // Greeting & date
    const now    = new Date();
    const hour   = now.getHours();
    const greet  = hour < 12 ? 'Buenos días' : hour < 19 ? 'Buenas tardes' : 'Buenas noches';
    const user   = (state.currentUser?.nombre || state.currentUser?.username || '');
    const gEl    = document.getElementById('landing-greeting');
    const dEl    = document.getElementById('landing-date-str');
    if (gEl) gEl.textContent = user ? `${greet}, ${user}` : 'Bienvenido al Tablero SGDU';
    if (dEl) {
        const dias  = ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];
        const meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
        dEl.textContent = `${dias[now.getDay()]} ${now.getDate()} de ${meses[now.getMonth()]} de ${now.getFullYear()}`;
    }

    try {
        const API_BASE = window.API_BASE || '/api';
        const res = await window.def_fetch(`${API_BASE}/landing/stats`);
        if (!res || !res.ok) throw new Error('fetch');
        const d   = await res.json();

        // Progress bar
        const pctBar  = document.getElementById('landing-progress-bar');
        const wdLabel = document.getElementById('landing-workdays-label');
        if (wdLabel) wdLabel.textContent = `Día ${d.dia_actual} de ${d.dias_mes} · ${d.pct_mes}%`;
        if (pctBar) setTimeout(() => { pctBar.style.width = d.pct_mes + '%'; }, 200);

        // KPI cards
        const cards = [
            { icon: 'fa-solid fa-file-lines',       iconBg: '#eff6ff', iconColor: '#3b82f6',
              label: 'Trámites configurados',        value: d.tramites_total,            sub: 'tipos de trámite activos' },
            { icon: 'fa-solid fa-users',             iconBg: '#f0fdf4', iconColor: '#10b981',
              label: 'Analistas activos',            value: d.analistas_count,           sub: 'en el sistema' },
            { icon: 'fa-solid fa-file-import',          iconBg: '#eff6ff', iconColor: '#6366f1',
              label: `Ingresados ${_mesLabel(d.mes)}`, value: d.ingresos_mes,            sub: 'expedientes en el mes' },
            { icon: 'fa-solid fa-circle-check',      iconBg: '#f0fdf4', iconColor: '#10b981',
              label: `Egresados efectivos ${_mesLabel(d.mes)}`, value: d.egresos_efectivos_mes, sub: 'resoluciones definitivas', valueColor: '#10b981' },
            { icon: 'fa-solid fa-circle-xmark',      iconBg: '#fff7ed', iconColor: '#f97316',
              label: `Egresados no efectivos ${_mesLabel(d.mes)}`, value: d.egresos_no_efectivos_mes, sub: 'desistimientos / rechazos', valueColor: '#f97316' },
            { icon: 'fa-solid fa-right-from-bracket', iconBg: '#f8fafc', iconColor: '#64748b',
              label: `Total egresados ${_mesLabel(d.mes)}`, value: d.egresos_total_mes, sub: 'ef. + no ef.' },
            { icon: 'fa-solid fa-layer-group',       iconBg: '#faf5ff', iconColor: '#8b5cf6',
              label: 'Stock en trámite',             value: d.stock_total,               sub: `expedientes activos hoy (incluye ${d.stock_intervenciones.toLocaleString('es-AR')} de intervenciones)`, valueColor: '#8b5cf6' },
            { icon: 'fa-solid fa-triangle-exclamation', iconBg: '#fef2f2', iconColor: '#ef4444',
              label: 'Subsanaciones abiertas',       value: d.subs_abiertas,            sub: 'pendientes de respuesta', valueColor: '#ef4444' },
            { icon: 'fa-solid fa-fire-flame-curved', iconBg: '#fef2f2', iconColor: '#dc2626',
              label: 'Trámite con mayor stock',      value: d.top_trata_stock,          sub: d.top_trata_nombre, valueColor: '#dc2626' },
        ];

        const grid = document.getElementById('landing-kpi-grid');
        if (!grid) return;

        const first8 = cards.slice(0, 8).map(c => _kpiCard(c)).join('');
        const lastCard = _kpiCard({
            ...cards[8],
            gridStyle: 'grid-column: 5; grid-row: 1 / span 2;',
            tall: true
        });
        grid.innerHTML = first8 + lastCard;

        // Render DGROC and DGIUR grids
        const dgrocGrid = document.getElementById('landing-dgroc-grid');
        const dgiurGrid = document.getElementById('landing-dgiur-grid');
        
        if (dgrocGrid && d.dgroc) {
            dgrocGrid.innerHTML = [
                _directionCard({ label: 'Ingresos', mesVal: d.dgroc.ingresos_mes, acumVal: d.dgroc.ingresos_acum }),
                _directionCard({ label: 'Egresos', mesVal: d.dgroc.egresos_mes, acumVal: d.dgroc.egresos_acum, efVal: d.dgroc.egresos_efectivos_acum, neVal: d.dgroc.egresos_no_efectivos_acum }),
                _directionCard({ label: 'Stock', mesVal: d.dgroc.stock, showAcum: false, intVal: d.dgroc.stock_intervenciones }),
                _directionCard({ label: 'Subsanaciones', mesVal: d.dgroc.subsanaciones, showAcum: false, intVal: d.dgroc.subsanaciones_intervenciones })
            ].join('');
        }

        if (dgiurGrid && d.dgiur) {
            dgiurGrid.innerHTML = [
                _directionCard({ label: 'Ingresos', mesVal: d.dgiur.ingresos_mes, acumVal: d.dgiur.ingresos_acum }),
                _directionCard({ label: 'Egresos', mesVal: d.dgiur.egresos_mes, acumVal: d.dgiur.egresos_acum, efVal: d.dgiur.egresos_efectivos_acum, neVal: d.dgiur.egresos_no_efectivos_acum }),
                _directionCard({ label: 'Stock', mesVal: d.dgiur.stock, showAcum: false, intVal: d.dgiur.stock_intervenciones }),
                _directionCard({ label: 'Subsanaciones', mesVal: d.dgiur.subsanaciones, showAcum: false, intVal: d.dgiur.subsanaciones_intervenciones })
            ].join('');
        }

        // Animate counters
        const allGrids = [grid, dgrocGrid, dgiurGrid];
        allGrids.forEach(g => {
            if (g) {
                g.querySelectorAll('.landing-kpi-value[data-target]').forEach(el => {
                    const target = parseInt(el.dataset.target, 10);
                    if (!isNaN(target)) _animateCount(el, target);
                });
            }
        });

    } catch (e) {
        console.warn('Landing stats error:', e);
    }
}
