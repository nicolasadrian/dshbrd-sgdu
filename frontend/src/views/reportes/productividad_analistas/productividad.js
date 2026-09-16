import { state } from '../../../state.js';

export const PROD_GERENCIAS_CONFIG = {
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

let _cachedSectoresData = null;
let _selectedAnalystUser = null;
let _selectedAnalystName = null;
let _selectedAnalystSector = null;

// Instancias de gráficos para el modal (si se utiliza)
let _currentProdMixChart = null;
let _currentProdDiarioChart = null;
let _currentProdTimelineChart = null;

// Mapa de instancias de gráficos por gerencia: { [gerenciaKey]: { mix, diario, timeline } }
const _gerenciaCharts = {};

/**
 * Fetch sectores y analistas desde el backend
 */
async function fetchSectoresAnalistas() {
    const API_BASE = window.API_BASE || '/api';
    const token = state.authToken || localStorage.getItem('sgdu_token') || '';
    const url = `${API_BASE}/productividad/sectores-analistas`;
    if (window.def_fetch) {
        return await window.def_fetch(url);
    }
    return await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
}

/**
 * Hub Central de Productividad Analistas (#/productividad_analistas)
 */
export async function loadProductividadHubView() {
    const cardsContainer = document.getElementById('prod-hub-global-cards');
    const dgrocContainer = document.getElementById('prod-hub-cards-dgroc');
    const dgiurContainer = document.getElementById('prod-hub-cards-dgiur');
    const otrosContainer = document.getElementById('prod-hub-cards-otros');
    const otrosSection = document.getElementById('prod-hub-section-otros');

    if (cardsContainer) {
        cardsContainer.innerHTML = '<div style="text-align: center; padding: 2rem; grid-column: 1 / -1;"><span class="loader"></span><p style="margin-top: 0.5rem; color: #64748b;">Analizando analistas y sectores de productividad...</p></div>';
    }

    const user = state.currentUser || JSON.parse(localStorage.getItem('sgdu_user') || 'null');
    const perms = (user && user.permissions) || {};
    const isAdmin = !!(user && ['admin', 'administrador'].includes((user.role || '').toLowerCase()));
    const hasGlobal = isAdmin || !!perms['productividad_analistas'];

    try {
        const res = await fetchSectoresAnalistas();
        if (res && res.ok) {
            _cachedSectoresData = await res.json();
            window._cachedSectoresData = _cachedSectoresData;

            renderProdHubCards(_cachedSectoresData, perms, hasGlobal, isAdmin);
        } else {
            if (cardsContainer) {
                cardsContainer.innerHTML = '<div style="text-align: center; padding: 2rem; color: #ef4444; grid-column: 1 / -1;">Error al consultar sectores de productividad.</div>';
            }
        }
    } catch (err) {
        console.error("Error loading Productividad hub:", err);
        if (cardsContainer) {
            cardsContainer.innerHTML = '<div style="text-align: center; padding: 2rem; color: #ef4444; grid-column: 1 / -1;">Error de conexión con el servidor.</div>';
        }
    }
}

function renderProdHubCards(sectoresData, perms, hasGlobal, isAdmin) {
    const cardsContainer = document.getElementById('prod-hub-global-cards');
    const dgrocContainer = document.getElementById('prod-hub-cards-dgroc');
    const dgiurContainer = document.getElementById('prod-hub-cards-dgiur');
    const otrosContainer = document.getElementById('prod-hub-cards-otros');
    const otrosSection = document.getElementById('prod-hub-section-otros');

    let totalAgentes = 0;
    let totalAreas = 0;

    for (const k in sectoresData) {
        const count = (sectoresData[k] || []).length;
        if (count > 0) {
            totalAgentes += count;
            totalAreas++;
        }
    }

    if (cardsContainer) {
        cardsContainer.innerHTML = `
            <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 20px 24px; border-radius: 14px; display: flex; align-items: center; gap: 18px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);">
                <div style="width: 52px; height: 52px; border-radius: 12px; background: #eff6ff; color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 1.4rem;">
                    <i class="fa-solid fa-users-viewfinder"></i>
                </div>
                <div>
                    <span style="font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Analistas Asignados</span>
                    <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.8rem; color: var(--primary-dark);">${totalAgentes}</h3>
                </div>
            </div>
            <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 20px 24px; border-radius: 14px; display: flex; align-items: center; gap: 18px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);">
                <div style="width: 52px; height: 52px; border-radius: 12px; background: #f0fdf4; color: #16a34a; display: flex; align-items: center; justify-content: center; font-size: 1.4rem;">
                    <i class="fa-solid fa-sitemap"></i>
                </div>
                <div>
                    <span style="font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Gerencias y Áreas</span>
                    <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.8rem; color: #16a34a;">${totalAreas}</h3>
                </div>
            </div>
            <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 20px 24px; border-radius: 14px; display: flex; align-items: center; gap: 18px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);">
                <div style="width: 52px; height: 52px; border-radius: 12px; background: #faf5ff; color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 1.4rem;">
                    <i class="fa-solid fa-chart-line"></i>
                </div>
                <div>
                    <span style="font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Estado Auditoría</span>
                    <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.8rem; color: #7c3aed;">En Línea</h3>
                </div>
            </div>
        `;
    }

    const renderCard = (k) => {
        const conf = PROD_GERENCIAS_CONFIG[k];
        if (!conf) return '';

        const canAccess = hasGlobal || !!perms[`productividad_${k}`] || (k === 'conforme' && !!perms['productividad_regularizacion']);
        if (!canAccess) return '';

        let count = (sectoresData[k] || []).length;
        if (k === 'conforme' && count === 0) {
            count = (sectoresData['regularizacion'] || []).length;
        }

        return `
            <div class="prod-card-box" onclick="window.location.hash='#/productividad_analistas/${k}'" style="background: white; border: 1px solid #cbd5e1; border-radius: 14px; padding: 18px 20px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: all 0.2s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
                <div style="display: flex; align-items: center; gap: 14px;">
                    <div style="width: 44px; height: 44px; border-radius: 10px; background: ${conf.bg}; color: ${conf.color}; display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">
                        <i class="${conf.icon}"></i>
                    </div>
                    <div>
                        <h4 style="margin: 0; font-family: 'Outfit'; font-weight: 700; font-size: 1.05rem; color: var(--primary-dark);">${conf.name}</h4>
                        <span style="font-size: 0.82rem; color: #64748b;">${count} ${count === 1 ? 'analista activo' : 'analistas activos'}</span>
                    </div>
                </div>
                <div style="color: #94a3b8; font-size: 1.1rem;">
                    <i class="fa-solid fa-chevron-right"></i>
                </div>
            </div>
        `;
    };

    if (dgrocContainer) {
        let html = '';
        ['catastro', 'instalaciones', 'conforme', 'contable', 'etapa_proyecto', 'aviso_obra'].forEach(k => {
            html += renderCard(k);
        });
        dgrocContainer.innerHTML = html || '<p style="color:#64748b; grid-column:1/-1;">Sin gerencias asignadas en DGROC.</p>';
    }

    if (dgiurContainer) {
        let html = '';
        ['morfologia', 'aph', 'usos', 'publico_privado', 'copua', 'privada'].forEach(k => {
            html += renderCard(k);
        });
        dgiurContainer.innerHTML = html || '<p style="color:#64748b; grid-column:1/-1;">Sin gerencias asignadas en DGIUR.</p>';
    }

    if (otrosContainer) {
        let html = renderCard('otros');
        if (html) {
            if (otrosSection) otrosSection.style.display = 'block';
            otrosContainer.innerHTML = html;
        } else {
            if (otrosSection) otrosSection.style.display = 'none';
        }
    }
}

/**
 * Controller para Vista de Gerencia Independiente (#/productividad_analistas/:gerencia)
 * Rediseñado: Sin tarjetas innecesarias, con selector dropdown de analistas y reporte de productividad embebido.
 */
export async function loadProductividadGerenciaView(gerenciaKey) {
    const conf = PROD_GERENCIAS_CONFIG[gerenciaKey];
    if (!conf) {
        console.warn("Gerencia no configurada para productividad:", gerenciaKey);
        return;
    }

    const selectEl = document.getElementById(`prod-${gerenciaKey}-analyst-select`);
    const fromInput = document.getElementById(`prod-${gerenciaKey}-date-from`);
    const toInput = document.getElementById(`prod-${gerenciaKey}-date-to`);
    const loaderEl = document.getElementById(`prod-${gerenciaKey}-loader`);
    const emptyEl = document.getElementById(`prod-${gerenciaKey}-empty`);
    const dashboardEl = document.getElementById(`prod-${gerenciaKey}-dashboard`);

    // Inicializar fechas por defecto (últimos 90 días) si están vacías
    if (fromInput && !fromInput.value) {
        const ninetyDaysAgo = new Date();
        ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90);
        fromInput.value = ninetyDaysAgo.toISOString().substring(0, 10);
    }
    if (toInput && !toInput.value) {
        toInput.value = new Date().toISOString().substring(0, 10);
    }

    try {
        if (!_cachedSectoresData) {
            const res = await fetchSectoresAnalistas();
            if (res && res.ok) {
                _cachedSectoresData = await res.json();
                window._cachedSectoresData = _cachedSectoresData;
            }
        }

        let analysts = (_cachedSectoresData && _cachedSectoresData[gerenciaKey]) || [];
        if (analysts.length === 0 && gerenciaKey === 'conforme' && _cachedSectoresData) {
            analysts = _cachedSectoresData['regularizacion'] || [];
        }

        if (selectEl) {
            if (analysts.length === 0) {
                selectEl.innerHTML = '<option value="">Sin analistas asignados</option>';
                if (loaderEl) loaderEl.style.display = 'none';
                if (emptyEl) emptyEl.style.display = 'block';
                if (dashboardEl) dashboardEl.style.display = 'none';
                return;
            }

            let optionsHtml = '';
            analysts.forEach(a => {
                const displayName = a.nombre ? `${a.nombre} (${a.usuario})` : a.usuario;
                optionsHtml += `<option value="${a.usuario}" data-nombre="${a.nombre || a.usuario}">${displayName}</option>`;
            });
            selectEl.innerHTML = optionsHtml;

            // Seleccionar automáticamente el primer analista y cargar su reporte
            if (emptyEl) emptyEl.style.display = 'none';
            await loadProductividadGerenciaAnalistaData(gerenciaKey);
        }
    } catch (err) {
        console.error("Error loading gerencia productivity view:", err);
        if (selectEl) selectEl.innerHTML = '<option value="">Error al cargar analistas</option>';
    }
}

/**
 * Disparado al cambiar el dropdown del analista en una vista de gerencia
 */
export function onSelectAnalistaGerencia(gerenciaKey) {
    loadProductividadGerenciaAnalistaData(gerenciaKey);
}

/**
 * Carga y renderiza el reporte de productividad del analista seleccionado en la vista de gerencia
 */
export async function loadProductividadGerenciaAnalistaData(gerenciaKey) {
    const selectEl = document.getElementById(`prod-${gerenciaKey}-analyst-select`);
    const loaderEl = document.getElementById(`prod-${gerenciaKey}-loader`);
    const emptyEl = document.getElementById(`prod-${gerenciaKey}-empty`);
    const dashboardEl = document.getElementById(`prod-${gerenciaKey}-dashboard`);
    const fromInput = document.getElementById(`prod-${gerenciaKey}-date-from`);
    const toInput = document.getElementById(`prod-${gerenciaKey}-date-to`);

    if (!selectEl || !selectEl.value) {
        if (loaderEl) loaderEl.style.display = 'none';
        if (dashboardEl) dashboardEl.style.display = 'none';
        return;
    }

    const username = selectEl.value;
    const from = fromInput ? fromInput.value : '';
    const to = toInput ? toInput.value : '';

    if (loaderEl) loaderEl.style.display = 'block';
    if (dashboardEl) dashboardEl.style.display = 'none';
    if (emptyEl) emptyEl.style.display = 'none';

    const API_BASE = window.API_BASE || '/api';
    const token = state.authToken || localStorage.getItem('sgdu_token') || '';

    try {
        const url = `${API_BASE}/productividad/analista/${username}?date_from=${from}&date_to=${to}`;
        const resp = window.def_fetch 
            ? await window.def_fetch(url)
            : await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });

        if (!resp || !resp.ok) {
            console.error('Error al cargar la productividad del analista:', username);
            if (loaderEl) loaderEl.style.display = 'none';
            return;
        }

        const data = await resp.json();
        const kpis = data.kpis || {};

        // Rellenar KPIs
        const kpiTareas = document.getElementById(`prod-${gerenciaKey}-kpi-tareas`);
        const kpiDiario = document.getElementById(`prod-${gerenciaKey}-kpi-diario`);
        const kpiJornada = document.getElementById(`prod-${gerenciaKey}-kpi-jornada`);
        const kpiStock = document.getElementById(`prod-${gerenciaKey}-kpi-stock`);
        const kpiStockDetails = document.getElementById(`prod-${gerenciaKey}-kpi-stock-details`);
        const kpiFirmas = document.getElementById(`prod-${gerenciaKey}-kpi-firmas`);
        const kpiRechazoRate = document.getElementById(`prod-${gerenciaKey}-kpi-rechazo-rate`);

        if (kpiTareas) kpiTareas.textContent = kpis.tareas_totales ?? 0;
        if (kpiDiario) kpiDiario.textContent = kpis.promedio_diario ?? 0;
        if (kpiJornada) kpiJornada.textContent = `${kpis.jornada_media ?? 0}h`;
        if (kpiStock) kpiStock.textContent = kpis.stock_total ?? 0;
        if (kpiStockDetails) kpiStockDetails.textContent = `Propio: ${kpis.stock_propio ?? 0} | Subs: ${kpis.stock_subs ?? 0}`;
        if (kpiFirmas) kpiFirmas.textContent = `${kpis.firmados ?? 0} / ${kpis.rechazados ?? 0}`;
        if (kpiRechazoRate) kpiRechazoRate.textContent = `Tasa de rechazo: ${kpis.tasa_rechazo ?? 0}%`;

        // Renderizar Gráficos y Tablas para esta gerencia
        renderGerenciaMixChart(gerenciaKey, data.mix_tareas);
        renderGerenciaDailyChart(gerenciaKey, data.desglose_diario);
        renderGerenciaHorariosTable(gerenciaKey, data.detalles_jornada);
        renderGerenciaTimelineChart(gerenciaKey, data.detalles_jornada);

        if (loaderEl) loaderEl.style.display = 'none';
        if (dashboardEl) dashboardEl.style.display = 'flex';

    } catch (err) {
        console.error("Error fetching analista productivity data for gerencia:", err);
        if (loaderEl) loaderEl.style.display = 'none';
    }
}

/**
 * Renderiza gráfico Mix para una vista de gerencia específica
 */
function renderGerenciaMixChart(gerenciaKey, mix) {
    const canvas = document.getElementById(`prod-${gerenciaKey}-chart-mix`);
    if (!canvas) return;

    if (!_gerenciaCharts[gerenciaKey]) _gerenciaCharts[gerenciaKey] = {};
    if (_gerenciaCharts[gerenciaKey].mix) {
        _gerenciaCharts[gerenciaKey].mix.destroy();
    }

    const ctx = canvas.getContext('2d');
    const labels = Object.keys(mix || {});
    const data = labels.map(k => mix[k].cantidad);
    const colors = [
        '#2563eb', '#10b981', '#f59e0b', '#ef4444', 
        '#8b5cf6', '#ec4899', '#06b6d4', '#64748b'
    ];

    _gerenciaCharts[gerenciaKey].mix = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, font: { family: 'Outfit', size: 11 } } },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const val = context.raw || 0;
                            const pct = mix[label] ? mix[label].porcentaje : 0;
                            return `${label}: ${val} (${pct}%)`;
                        }
                    }
                }
            },
            cutout: '65%'
        }
    });
}

/**
 * Renderiza gráfico de Actividad Diaria apilada para una vista de gerencia específica
 */
function renderGerenciaDailyChart(gerenciaKey, desglose) {
    const canvas = document.getElementById(`prod-${gerenciaKey}-chart-diario`);
    if (!canvas) return;

    if (!_gerenciaCharts[gerenciaKey]) _gerenciaCharts[gerenciaKey] = {};
    if (_gerenciaCharts[gerenciaKey].diario) {
        _gerenciaCharts[gerenciaKey].diario.destroy();
    }

    const ctx = canvas.getContext('2d');
    const dates = Object.keys(desglose || {}).sort();
    const taskTypes = [
        "OBSERVACIÓN DE EXPEDIENTE", 
        "PEDIDO DE PLANOS", 
        "VINCULACIÓN DE GEDO Y PASE A OBRAS ADMIN", 
        "ENVÍO A FIRMA", 
        "OBSERVACIÓN EN SUBSANACIÓN", 
        "SUSPENSIÓN DE EXPEDIENTE"
    ];

    const colors = {
        "OBSERVACIÓN DE EXPEDIENTE": '#f59e0b',
        "PEDIDO DE PLANOS": '#3b82f6',
        "VINCULACIÓN DE GEDO Y PASE A OBRAS ADMIN": '#6366f1',
        "ENVÍO A FIRMA": '#10b981',
        "OBSERVACIÓN EN SUBSANACIÓN": '#ec4899',
        "SUSPENSIÓN DE EXPEDIENTE": '#ef4444'
    };

    const datasets = taskTypes.map(t => ({
        label: t,
        data: dates.map(d => (desglose[d] && desglose[d][t]) || 0),
        backgroundColor: colors[t] || '#94a3b8',
        borderRadius: 4
    }));

    _gerenciaCharts[gerenciaKey].diario = new Chart(ctx, {
        type: 'bar',
        data: { labels: dates, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { stacked: true, grid: { display: false }, ticks: { font: { family: 'Outfit', size: 10 } } },
                y: { stacked: true, beginAtZero: true, ticks: { font: { family: 'Outfit', size: 11 } } }
            },
            plugins: {
                legend: { position: 'top', labels: { boxWidth: 10, font: { family: 'Outfit', size: 10 } } }
            }
        }
    });
}

/**
 * Renderiza la tabla de Horarios Activos para una vista de gerencia específica
 */
function renderGerenciaHorariosTable(gerenciaKey, detalles) {
    const tbody = document.getElementById(`prod-${gerenciaKey}-table-horarios`);
    if (!tbody) return;

    const sorted = [...(detalles || [])].sort((a,b) => b.fecha.localeCompare(a.fecha));

    if (sorted.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="padding:15px; color:#94a3b8; text-align:center;">Sin actividad registrada</td></tr>';
        return;
    }

    let html = '';
    sorted.forEach(d => {
        let badgeColor = '#10b981';
        if (d.duracion < 4) badgeColor = '#ef4444';
        else if (d.duracion < 6) badgeColor = '#f59e0b';

        html += `
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 8px 10px; font-weight: 600; font-size: 0.82rem;">${d.fecha}</td>
                <td style="padding: 8px 10px; color: #64748b; font-size: 0.82rem;">${d.primera_accion}</td>
                <td style="padding: 8px 10px; color: #64748b; font-size: 0.82rem;">${d.ultima_accion}</td>
                <td style="padding: 8px 10px;">
                    <span style="background: ${badgeColor}15; color: ${badgeColor}; padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 0.8rem;">
                        ${d.duracion}h
                    </span>
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

/**
 * Renderiza gráfico Timeline de conexión para una vista de gerencia específica
 */
function renderGerenciaTimelineChart(gerenciaKey, detalles) {
    const canvas = document.getElementById(`prod-${gerenciaKey}-chart-timeline`);
    if (!canvas) return;

    if (!_gerenciaCharts[gerenciaKey]) _gerenciaCharts[gerenciaKey] = {};
    if (_gerenciaCharts[gerenciaKey].timeline) {
        _gerenciaCharts[gerenciaKey].timeline.destroy();
    }

    const ctx = canvas.getContext('2d');
    const sorted = [...(detalles || [])].sort((a,b) => a.fecha.localeCompare(b.fecha));
    const labels = sorted.map(d => d.fecha.substring(5)); // MM-DD

    const timeToDecimal = (tStr) => {
        if (!tStr) return 0;
        const [h, m] = tStr.split(':').map(Number);
        return h + m/60.0;
    };

    const dataStart = sorted.map(d => timeToDecimal(d.primera_accion));
    const dataEnd = sorted.map(d => timeToDecimal(d.ultima_accion));

    _gerenciaCharts[gerenciaKey].timeline = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Rango Activo (Horario)',
                data: sorted.map((d, i) => [dataStart[i], dataEnd[i]]),
                backgroundColor: 'rgba(37, 99, 235, 0.45)',
                borderColor: '#2563eb',
                borderWidth: 1,
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 6,
                    max: 22,
                    ticks: {
                        stepSize: 2,
                        callback: val => `${Math.floor(val)}:00`,
                        font: { family: 'Outfit', size: 10 }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { font: { family: 'Outfit', size: 10 } }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const index = context.dataIndex;
                            const item = sorted[index];
                            return `Conectado: ${item.primera_accion} - ${item.ultima_accion} (${item.duracion}h)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Descarga de reporte individual PDF desde la barra superior de la gerencia
 */
export function downloadIndividualPDFGerencia(gerenciaKey) {
    const selectEl = document.getElementById(`prod-${gerenciaKey}-analyst-select`);
    const fromInput = document.getElementById(`prod-${gerenciaKey}-date-from`);
    const toInput = document.getElementById(`prod-${gerenciaKey}-date-to`);

    if (!selectEl || !selectEl.value) {
        alert('Por favor selecciona un analista para descargar su reporte PDF.');
        return;
    }

    const username = selectEl.value;
    const from = fromInput ? fromInput.value : '';
    const to = toInput ? toInput.value : '';
    const API_BASE = window.API_BASE || '/api';
    const token = state.authToken || localStorage.getItem('sgdu_token') || '';

    window.open(`${API_BASE}/productividad/pdf/individual?username=${encodeURIComponent(username)}&date_from=${from}&date_to=${to}&token=${token}`, '_blank');
}

/**
 * Filtro de tabla de analistas por gerencia (mantenido por compatibilidad)
 */
export function filterProductividadGerenciaTable(gerenciaKey, query) {
    const q = (query || '').toLowerCase().trim();
    const rows = document.querySelectorAll(`#prod-${gerenciaKey}-table-body .prod-analista-row`);
    rows.forEach(r => {
        const text = r.textContent.toLowerCase();
        r.style.display = text.includes(q) ? 'table-row' : 'none';
    });
}

/**
 * Modal / Detalle de Productividad Individual de un Analista (mantenido por compatibilidad)
 */
export async function openProductividadModal(username, fullname, sector) {
    _selectedAnalystUser = username;
    _selectedAnalystName = fullname;
    _selectedAnalystSector = sector;

    const modal = document.getElementById('prod-analyst-modal');
    if (!modal) return;

    modal.style.display = 'flex';
    document.getElementById('prod-modal-loader').style.display = 'block';
    document.getElementById('prod-modal-dashboard-content').style.display = 'none';

    // Fechas por defecto si están vacías (últimos 90 días)
    const fromInput = document.getElementById('prod-modal-date-from');
    const toInput = document.getElementById('prod-modal-date-to');
    if (fromInput && !fromInput.value) {
        const ninetyDaysAgo = new Date();
        ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90);
        fromInput.value = ninetyDaysAgo.toISOString().substring(0, 10);
        toInput.value = new Date().toISOString().substring(0, 10);
    }

    await loadProductividadAnalistaData();
}

export function closeProductividadModal() {
    const modal = document.getElementById('prod-analyst-modal');
    if (modal) modal.style.display = 'none';
}

export async function loadProductividadAnalistaData() {
    if (!_selectedAnalystUser) return;

    const from = document.getElementById('prod-modal-date-from').value;
    const to = document.getElementById('prod-modal-date-to').value;
    const API_BASE = window.API_BASE || '/api';
    const token = state.authToken || localStorage.getItem('sgdu_token') || '';

    try {
        const url = `${API_BASE}/productividad/analista/${_selectedAnalystUser}?date_from=${from}&date_to=${to}`;
        const resp = window.def_fetch 
            ? await window.def_fetch(url)
            : await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });

        if (!resp || !resp.ok) {
            alert('Error al cargar la productividad del analista.');
            document.getElementById('prod-modal-loader').style.display = 'none';
            return;
        }

        const data = await resp.json();
        const kpis = data.kpis;

        // Render header details
        document.getElementById('prod-modal-analyst-name').textContent = _selectedAnalystName;
        document.getElementById('prod-modal-analyst-meta').textContent = `Usuario: ${_selectedAnalystUser} | Sector: ${_selectedAnalystSector.toUpperCase()}`;

        // Fill KPIs
        document.getElementById('prod-modal-kpi-tareas').textContent = kpis.tareas_totales;
        document.getElementById('prod-modal-kpi-diario').textContent = kpis.promedio_diario;
        document.getElementById('prod-modal-kpi-jornada').textContent = `${kpis.jornada_media}h`;
        document.getElementById('prod-modal-kpi-stock').textContent = kpis.stock_total;
        document.getElementById('prod-modal-kpi-stock-details').textContent = `Propio: ${kpis.stock_propio} | Subs: ${kpis.stock_subs}`;
        document.getElementById('prod-modal-kpi-firmas').textContent = `${kpis.firmados} / ${kpis.rechazados}`;
        document.getElementById('prod-modal-kpi-rechazo-rate').textContent = `Tasa de rechazo: ${kpis.tasa_rechazo}%`;

        // Render Mix donut chart
        renderProdMixChart(data.mix_tareas);

        // Render Daily stacked bar chart
        renderProdDailyChart(data.desglose_diario);

        // Render Horarios table & Timeline Chart
        renderProdHorariosTable(data.detalles_jornada);
        renderProdTimelineChart(data.detalles_jornada);

        document.getElementById('prod-modal-loader').style.display = 'none';
        document.getElementById('prod-modal-dashboard-content').style.display = 'flex';

    } catch (err) {
        console.error("Error fetching analista productivity data:", err);
        alert('Error de conexión con el servidor.');
        document.getElementById('prod-modal-loader').style.display = 'none';
    }
}

function renderProdMixChart(mix) {
    const canvas = document.getElementById('prod-modal-chart-mix');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (_currentProdMixChart) _currentProdMixChart.destroy();

    const labels = Object.keys(mix || {});
    const data = labels.map(k => mix[k].cantidad);
    const colors = [
        '#2563eb', '#10b981', '#f59e0b', '#ef4444', 
        '#8b5cf6', '#ec4899', '#06b6d4', '#64748b'
    ];

    _currentProdMixChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, font: { family: 'Outfit', size: 11 } } },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const val = context.raw || 0;
                            const pct = mix[label] ? mix[label].porcentaje : 0;
                            return `${label}: ${val} (${pct}%)`;
                        }
                    }
                }
            },
            cutout: '65%'
        }
    });
}

function renderProdDailyChart(desglose) {
    const canvas = document.getElementById('prod-modal-chart-diario');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (_currentProdDiarioChart) _currentProdDiarioChart.destroy();

    const dates = Object.keys(desglose || {}).sort();
    const taskTypes = [
        "OBSERVACIÓN DE EXPEDIENTE", 
        "PEDIDO DE PLANOS", 
        "VINCULACIÓN DE GEDO Y PASE A OBRAS ADMIN", 
        "ENVÍO A FIRMA", 
        "OBSERVACIÓN EN SUBSANACIÓN", 
        "SUSPENSIÓN DE EXPEDIENTE"
    ];

    const colors = {
        "OBSERVACIÓN DE EXPEDIENTE": '#f59e0b',
        "PEDIDO DE PLANOS": '#3b82f6',
        "VINCULACIÓN DE GEDO Y PASE A OBRAS ADMIN": '#6366f1',
        "ENVÍO A FIRMA": '#10b981',
        "OBSERVACIÓN EN SUBSANACIÓN": '#ec4899',
        "SUSPENSIÓN DE EXPEDIENTE": '#ef4444'
    };

    const datasets = taskTypes.map(t => ({
        label: t,
        data: dates.map(d => desglose[d][t] || 0),
        backgroundColor: colors[t] || '#94a3b8',
        borderRadius: 4
    }));

    _currentProdDiarioChart = new Chart(ctx, {
        type: 'bar',
        data: { labels: dates, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { stacked: true, grid: { display: false }, ticks: { font: { family: 'Outfit', size: 10 } } },
                y: { stacked: true, beginAtZero: true, ticks: { font: { family: 'Outfit', size: 11 } } }
            },
            plugins: {
                legend: { position: 'top', labels: { boxWidth: 10, font: { family: 'Outfit', size: 10 } } }
            }
        }
    });
}

function renderProdHorariosTable(detalles) {
    const tbody = document.getElementById('prod-modal-table-horarios');
    if (!tbody) return;
    const sorted = [...(detalles || [])].sort((a,b) => b.fecha.localeCompare(a.fecha));

    if (sorted.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="padding:15px; color:#94a3b8; text-align:center;">Sin actividad registrada</td></tr>';
        return;
    }

    let html = '';
    sorted.forEach(d => {
        let badgeColor = '#10b981';
        if (d.duracion < 4) badgeColor = '#ef4444';
        else if (d.duracion < 6) badgeColor = '#f59e0b';

        html += `
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 8px 10px; font-weight: 600; font-size: 0.82rem;">${d.fecha}</td>
                <td style="padding: 8px 10px; color: #64748b; font-size: 0.82rem;">${d.primera_accion}</td>
                <td style="padding: 8px 10px; color: #64748b; font-size: 0.82rem;">${d.ultima_accion}</td>
                <td style="padding: 8px 10px;">
                    <span style="background: ${badgeColor}15; color: ${badgeColor}; padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 0.8rem;">
                        ${d.duracion}h
                    </span>
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

function renderProdTimelineChart(detalles) {
    const canvas = document.getElementById('prod-modal-chart-timeline');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (_currentProdTimelineChart) _currentProdTimelineChart.destroy();

    const sorted = [...(detalles || [])].sort((a,b) => a.fecha.localeCompare(b.fecha));
    const labels = sorted.map(d => d.fecha.substring(5)); // MM-DD

    const timeToDecimal = (tStr) => {
        if (!tStr) return 0;
        const [h, m] = tStr.split(':').map(Number);
        return h + m/60.0;
    };

    const dataStart = sorted.map(d => timeToDecimal(d.primera_accion));
    const dataEnd = sorted.map(d => timeToDecimal(d.ultima_accion));

    _currentProdTimelineChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Rango Activo (Horario)',
                data: sorted.map((d, i) => [dataStart[i], dataEnd[i]]),
                backgroundColor: 'rgba(37, 99, 235, 0.45)',
                borderColor: '#2563eb',
                borderWidth: 1,
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 6,
                    max: 22,
                    ticks: {
                        stepSize: 2,
                        callback: val => `${Math.floor(val)}:00`,
                        font: { family: 'Outfit', size: 10 }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { font: { family: 'Outfit', size: 10 } }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const index = context.dataIndex;
                            const item = sorted[index];
                            return `Conectado: ${item.primera_accion} - ${item.ultima_accion} (${item.duracion}h)`;
                        }
                    }
                }
            }
        }
    });
}

export function downloadIndividualPDF() {
    if (!_selectedAnalystUser) return;
    const from = document.getElementById('prod-modal-date-from').value;
    const to = document.getElementById('prod-modal-date-to').value;
    const API_BASE = window.API_BASE || '/api';
    const token = state.authToken || localStorage.getItem('sgdu_token') || '';
    window.open(`${API_BASE}/productividad/pdf/individual?username=${_selectedAnalystUser}&date_from=${from}&date_to=${to}&token=${token}`, '_blank');
}

export function downloadSectorComparativePDF(sector) {
    const today = new Date().toISOString().substring(0, 10);
    const ninetyDaysAgo = new Date(Date.now() - 90*86400000).toISOString().substring(0, 10);
    const API_BASE = window.API_BASE || '/api';
    const token = state.authToken || localStorage.getItem('sgdu_token') || '';
    window.open(`${API_BASE}/productividad/pdf/comparativo?sector=${encodeURIComponent(sector)}&date_from=${ninetyDaysAgo}&date_to=${today}&token=${token}`, '_blank');
}
