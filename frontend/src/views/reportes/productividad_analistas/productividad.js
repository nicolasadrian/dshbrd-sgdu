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

let _currentProdMixChart = null;
let _currentProdDiarioChart = null;
let _currentProdTimelineChart = null;

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
            <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 18px 22px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
                <div style="width: 50px; height: 50px; border-radius: 12px; background: #eff6ff; color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-users"></i></div>
                <div>
                    <span style="font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Total Analistas Activos</span>
                    <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: var(--primary-dark);">${totalAgentes}</h3>
                </div>
            </div>
            <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 18px 22px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
                <div style="width: 50px; height: 50px; border-radius: 12px; background: #ecfdf5; color: #10b981; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-sitemap"></i></div>
                <div>
                    <span style="font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Gerencias Monitoreadas</span>
                    <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: #10b981;">${totalAreas} Áreas</h3>
                </div>
            </div>
            <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 18px 22px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
                <div style="width: 50px; height: 50px; border-radius: 12px; background: #fdf2f8; color: #db2777; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-chart-line"></i></div>
                <div>
                    <span style="font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Nivel de Auditoría</span>
                    <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: #db2777;">Individual / SADE</h3>
                </div>
            </div>
        `;
    }

    const renderCard = (gKey) => {
        const conf = PROD_GERENCIAS_CONFIG[gKey];
        if (!conf) return '';

        const hasPerm = hasGlobal || !!perms[`productividad_${gKey}`] || (gKey === 'conforme' && !!perms['productividad_regularizacion']);
        if (!hasPerm) return '';

        let analysts = sectoresData[gKey] || [];
        if (analysts.length === 0 && gKey === 'conforme') analysts = sectoresData['regularizacion'] || [];

        const count = analysts.length;

        return `
            <div class="admin-card nav-card-prod" onclick="window.location.hash='#/productividad_analistas/${gKey}'" style="background: white; border-radius: 14px; border: 1px solid #cbd5e1; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03); cursor: pointer; transition: all 0.25s ease; display: flex; flex-direction: column; justify-content: space-between; position: relative; overflow: hidden;"
                onmouseover="this.style.borderColor='${conf.color}'; this.style.transform='translateY(-3px)'; this.style.boxShadow='0 10px 15px -3px rgba(0,0,0,0.08)';"
                onmouseout="this.style.borderColor='#cbd5e1'; this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px -1px rgba(0,0,0,0.03)';">
                
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 14px;">
                    <div style="width: 44px; height: 44px; border-radius: 10px; background: ${conf.bg}; color: ${conf.color}; display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">
                        <i class="${conf.icon}"></i>
                    </div>
                    <div>
                        <h4 style="margin: 0; color: var(--primary-dark); font-family: 'Outfit'; font-weight: 800; font-size: 1.05rem;">${conf.name}</h4>
                        <span style="font-size: 0.75rem; font-weight: 700; color: #94a3b8; text-transform: uppercase;">${conf.dir}</span>
                    </div>
                </div>

                <div style="background: #f8fafc; border-radius: 10px; padding: 12px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #e2e8f0; margin-bottom: 14px;">
                    <div>
                        <span style="font-size: 0.72rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Analistas</span>
                        <div style="font-family: 'Outfit'; font-weight: 800; font-size: 1.15rem; color: var(--primary-dark);">${count} activos</div>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 0.72rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Reporte</span>
                        <div style="font-family: 'Outfit'; font-weight: 700; font-size: 0.95rem; color: ${conf.color};">Detallado</div>
                    </div>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.82rem; font-weight: 700; color: ${conf.color};">
                    <span>Ver Productividad del Área</span>
                    <i class="fa-solid fa-arrow-right"></i>
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
 */
export async function loadProductividadGerenciaView(gerenciaKey) {
    const conf = PROD_GERENCIAS_CONFIG[gerenciaKey];
    if (!conf) {
        console.warn("Gerencia no configurada para productividad:", gerenciaKey);
        return;
    }

    const cardsContainer = document.getElementById(`prod-${gerenciaKey}-cards`);
    const tableBody = document.getElementById(`prod-${gerenciaKey}-table-body`);
    const countEl = document.getElementById(`prod-${gerenciaKey}-analistas-count`);
    const pdfBtn = document.getElementById(`prod-${gerenciaKey}-reporte-pdf-btn`);

    if (tableBody) {
        tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 2rem;"><span class="loader"></span><p style="margin-top: 0.5rem; color: #64748b;">Cargando analistas del sector...</p></td></tr>';
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

        if (countEl) {
            countEl.innerText = `${analysts.length} ${analysts.length === 1 ? 'analista activo asignado' : 'analistas activos asignados'} a esta gerencia.`;
        }

        if (pdfBtn) {
            pdfBtn.onclick = () => downloadSectorComparativePDF(gerenciaKey);
        }

        if (cardsContainer) {
            cardsContainer.innerHTML = `
                <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 18px 22px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
                    <div style="width: 50px; height: 50px; border-radius: 12px; background: ${conf.bg}; color: ${conf.color}; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-users"></i></div>
                    <div>
                        <span style="font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Analistas del Área</span>
                        <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: var(--primary-dark);">${analysts.length}</h3>
                    </div>
                </div>
                <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 18px 22px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
                    <div style="width: 50px; height: 50px; border-radius: 12px; background: #f0fdf4; color: #16a34a; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-shield-check"></i></div>
                    <div>
                        <span style="font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Estado de Planta</span>
                        <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: #16a34a;">Activo</h3>
                    </div>
                </div>
                <div class="metric-card-premium" style="background: white; border: 1px solid #cbd5e1; padding: 18px 22px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03);">
                    <div style="width: 50px; height: 50px; border-radius: 12px; background: #eff6ff; color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-file-pdf"></i></div>
                    <div>
                        <span style="font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Reporte Comparativo</span>
                        <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.6rem; color: #2563eb;">Exportable PDF</h3>
                    </div>
                </div>
            `;
        }

        if (tableBody) {
            if (analysts.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 2rem; color: #64748b;">No hay analistas asignados a esta gerencia.</td></tr>';
                return;
            }

            let rows = '';
            analysts.forEach(a => {
                const uEsc = (a.usuario || '').replace(/'/g, "\\'");
                const nEsc = (a.nombre || a.usuario || '').replace(/'/g, "\\'");
                rows += `
                    <tr class="prod-analista-row" style="border-bottom: 1px solid #f1f5f9; transition: background 0.15s;" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='transparent'">
                        <td style="padding: 12px 14px; font-weight: 700; color: var(--primary-dark);">${a.usuario}</td>
                        <td style="padding: 12px 14px; color: #334155;">${a.nombre}</td>
                        <td style="padding: 12px 14px; text-align: center;"><span class="badge-builtin" style="background: #f0fdf4; color: #16a34a; font-weight: 700; font-size: 0.75rem; padding: 3px 8px; border-radius: 6px;">Activo</span></td>
                        <td style="padding: 12px 14px; text-align: center;">
                            <button type="button" onclick="openProductividadModal('${uEsc}', '${nEsc}', '${gerenciaKey}')" style="padding: 6px 14px; background: var(--primary); color: white; border: none; border-radius: 6px; font-size: 0.82rem; font-family: 'Outfit'; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                                <i class="fa-solid fa-chart-pie"></i> Ver Productividad
                            </button>
                        </td>
                    </tr>
                `;
            });
            tableBody.innerHTML = rows;
        }
    } catch (err) {
        console.error("Error loading gerencia productivity view:", err);
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 2rem; color: #ef4444;">Error al cargar datos.</td></tr>';
        }
    }
}

/**
 * Filtro de tabla de analistas por gerencia
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
 * Modal / Detalle de Productividad Individual de un Analista
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
