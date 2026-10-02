// Vista Modular Seguimiento MH (MDUG0131B)
// Métricas, Asignaciones, Historial y Validación de Tenencia SADE

let mhDashboardData = null;
let mhExpedientesList = [];
let mhSelectedExpedientes = new Set();
let mhCurrentOffset = 0;
const mhPageLimit = 50;
let mhSearchDebounceTimer = null;

export async function loadSeguimientoMHView() {
    mhSelectedExpedientes.clear();
    updateMHSelectedUI();
    checkMHUserPermissions();
    await Promise.all([
        loadSeguimientoMHDashboard(),
        loadSeguimientoMHExpedientes(0)
    ]);
}

function checkMHUserPermissions() {
    const user = window.currentUser || JSON.parse(localStorage.getItem('sgdu_user') || 'null');
    const role = (user && user.role ? user.role : '').toLowerCase();
    const perms = user && user.permissions ? user.permissions : {};

    const canAssign = (
        role === 'admin' ||
        role === 'administrador' ||
        !!perms['admin'] ||
        !!perms['seguimiento_mh_asignar']
    );

    const permBadge = document.getElementById('mh-assign-perm-badge');
    const bulkBox = document.getElementById('mh-bulk-actions-container');

    if (permBadge) {
        permBadge.style.display = canAssign ? 'flex' : 'none';
    }
    if (bulkBox) {
        bulkBox.style.display = canAssign ? 'flex' : 'none';
    }
}

export async function loadSeguimientoMHDashboard() {
    try {
        const resp = await def_fetch(`${API_BASE}/reportes/seguimiento-mh/dashboard`);
        if (!resp || !resp.ok) return;

        mhDashboardData = await resp.json();
        renderMHKPIs(mhDashboardData);
        renderMHMonthlyGoals(mhDashboardData.monthly_goals);
        renderMHTeams(mhDashboardData.agents_summary);
    } catch (err) {
        console.error("Error loading Seguimiento MH Dashboard:", err);
    }
}

function renderMHKPIs(data) {
    const kpiUniverso = document.getElementById('kpi-mh-universo');
    const kpiStock = document.getElementById('kpi-mh-stock');
    const kpiSubs = document.getElementById('kpi-mh-subsanacion');
    const kpiFlujo = document.getElementById('kpi-mh-flujo');
    const kpiEstancado = document.getElementById('kpi-mh-estancado');
    const kpiSlaDays = document.getElementById('kpi-mh-sla-days');
    const kpiAsignados = document.getElementById('kpi-mh-asignados');
    const kpiCoinciden = document.getElementById('kpi-mh-coinciden');
    const kpiDifieren = document.getElementById('kpi-mh-difieren');
    const kpiCumplidoOct = document.getElementById('kpi-mh-cumplido-octubre');
    const kpiBarOct = document.getElementById('kpi-mh-bar-octubre');

    if (kpiUniverso) kpiUniverso.textContent = data.stock.total_universo_activo;
    if (kpiStock) kpiStock.textContent = data.stock.stock_propio;
    if (kpiSubs) kpiSubs.textContent = data.stock.subsanaciones;
    if (kpiFlujo) kpiFlujo.textContent = data.stock.stock_flujo;
    if (kpiEstancado) kpiEstancado.textContent = `${data.stock.stock_estancado} exp`;
    if (kpiSlaDays) kpiSlaDays.textContent = data.dias_sla;

    if (kpiAsignados) kpiAsignados.textContent = data.asignaciones_resumen.total_asignados;
    if (kpiCoinciden) kpiCoinciden.textContent = `${data.asignaciones_resumen.total_coincidentes} (${data.asignaciones_resumen.porcentaje_coincidencia}%)`;
    if (kpiDifieren) kpiDifieren.textContent = data.asignaciones_resumen.total_no_coincidentes;

    const oct = data.monthly_goals['2026-10'] || { total: 0, meta_total: 118 };
    if (kpiCumplidoOct) kpiCumplidoOct.textContent = oct.total;
    if (kpiBarOct) {
        const pct = Math.min(100, Math.round((oct.total / (oct.meta_total || 1)) * 100));
        kpiBarOct.style.width = `${pct}%`;
    }
}

function renderMHMonthlyGoals(goals) {
    const container = document.getElementById('mh-monthly-goals-grid');
    if (!container || !goals) return;

    let html = '';
    const months = ['2026-10', '2026-11', '2026-12', '2027-01'];

    months.forEach(mKey => {
        const g = goals[mKey] || { label: mKey, meta_nuevos: 0, meta_existentes: 0, meta_total: 0, nuevos: 0, existentes: 0, total: 0 };
        const pct = g.meta_total > 0 ? Math.min(100, Math.round((g.total / g.meta_total) * 100)) : 0;
        const isCurrentMonth = mKey === '2026-10';

        html += `
            <div class="card-goal-month" style="background: ${isCurrentMonth ? '#eff6ff' : '#f8fafc'}; border: 1px solid ${isCurrentMonth ? '#bfdbfe' : '#e2e8f0'}; border-radius: 12px; padding: 1.1rem; position: relative;">
                ${isCurrentMonth ? '<span style="position: absolute; top: 10px; right: 10px; background: #2563eb; color: white; font-size: 0.68rem; font-weight: 800; padding: 2px 7px; border-radius: 6px; text-transform: uppercase;">En Curso</span>' : ''}
                <div style="font-size: 1rem; font-weight: 800; color: #0f172a; margin-bottom: 0.6rem;">
                    ${g.label}
                </div>

                <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.5rem;">
                    <span style="font-size: 1.45rem; font-weight: 800; color: #1e3a8a;">${g.total} <span style="font-size: 0.82rem; font-weight: 600; color: #64748b;">/ ${g.meta_total} reg</span></span>
                    <span style="font-size: 0.85rem; font-weight: 800; color: ${pct >= 100 ? '#15803d' : '#2563eb'};">${pct}%</span>
                </div>

                <div style="background: #e2e8f0; border-radius: 999px; height: 6px; overflow: hidden; margin-bottom: 0.75rem;">
                    <div style="background: ${pct >= 100 ? '#16a34a' : '#2563eb'}; width: ${pct}%; height: 100%;"></div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 0.75rem; background: white; padding: 8px; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <div>
                        <div style="color: #64748b; font-weight: 600;">Existentes</div>
                        <div style="font-weight: 800; color: #1e3a8a;">${g.existentes} / ${g.meta_existentes}</div>
                    </div>
                    <div>
                        <div style="color: #64748b; font-weight: 600;">Nuevos</div>
                        <div style="font-weight: 800; color: #15803d;">${g.nuevos} / ${g.meta_nuevos}</div>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function renderMHTeams(agents) {
    const tbodyExist = document.getElementById('mh-tbody-existing');
    const tbodyNew = document.getElementById('mh-tbody-new');
    if (!tbodyExist || !tbodyNew || !agents) return;

    let htmlExist = '';
    let htmlNew = '';

    agents.forEach(a => {
        const isMatch = a.coincidencia_tenencia > 0;
        const row = `
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 7px 10px; font-weight: 700; color: #1e293b;">
                    <i class="fa-solid fa-user" style="color: #94a3b8; margin-right: 5px; font-size: 0.75rem;"></i>${a.usuario}
                </td>
                <td style="padding: 7px 6px; text-align: center; font-weight: 800; color: #2563eb;">
                    ${a.asignados_activos}
                </td>
                <td style="padding: 7px 6px; text-align: center; font-weight: 700; color: #475569;">
                    ${a.en_poder_sade}
                </td>
                <td style="padding: 7px 6px; text-align: center;">
                    <span style="font-size: 0.75rem; font-weight: 800; padding: 2px 6px; border-radius: 6px; background: ${a.coincidencia_tenencia > 0 ? '#ecfdf5' : '#fef2f2'}; color: ${a.coincidencia_tenencia > 0 ? '#059669' : '#e11d48'};">
                        ${a.coincidencia_tenencia}
                    </span>
                </td>
                <td style="padding: 7px 6px; text-align: center; font-weight: 800; color: #0f172a;">
                    ${a.egresos_octubre}
                </td>
                <td style="padding: 7px 6px; text-align: center;">
                    <button onclick="filterByMHAgente('${a.usuario}')" title="Filtrar en tabla de expedientes" style="background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 3px 7px; cursor: pointer; color: #475569; font-size: 0.75rem;">
                        <i class="fa-solid fa-filter"></i>
                    </button>
                </td>
            </tr>
        `;

        if (a.tipo === 'existente') {
            htmlExist += row;
        } else {
            htmlNew += row;
        }
    });

    tbodyExist.innerHTML = htmlExist || '<tr><td colspan="6" style="text-align:center; padding:10px;">Sin datos</td></tr>';
    tbodyNew.innerHTML = htmlNew || '<tr><td colspan="6" style="text-align:center; padding:10px;">Sin datos</td></tr>';
}

export async function loadSeguimientoMHExpedientes(offset = 0) {
    mhCurrentOffset = offset;
    const tbody = document.getElementById('mh-expedientes-tbody');
    if (!tbody) return;

    tbody.innerHTML = `
        <tr>
            <td colspan="9" style="text-align: center; padding: 2.5rem; color: #64748b;">
                <i class="fa-solid fa-spinner fa-spin" style="font-size: 1.5rem; margin-bottom: 8px; color: #2563eb;"></i>
                <p style="margin: 0;">Consultando expedientes...</p>
            </td>
        </tr>
    `;

    const estado = document.getElementById('mh-filter-estado')?.value || '';
    const agente = document.getElementById('mh-filter-agente')?.value || '';
    const coincidencia = document.getElementById('mh-filter-coincidencia')?.value || '';
    const search = document.getElementById('mh-search-input')?.value || '';

    const params = new URLSearchParams({
        limit: mhPageLimit,
        offset: mhCurrentOffset
    });
    if (estado) params.append('filtro_estado', estado);
    if (agente) params.append('filtro_agente', agente);
    if (coincidencia) params.append('filtro_coincidencia', coincidencia);
    if (search) params.append('search', search);

    try {
        const resp = await def_fetch(`${API_BASE}/reportes/seguimiento-mh/expedientes?${params.toString()}`);
        if (!resp || !resp.ok) return;

        const data = await resp.json();
        mhExpedientesList = data.expedientes || [];
        renderMHExpedientesTable(data);
        renderMHPagination(data);
    } catch (err) {
        console.error("Error loading MH Expedientes:", err);
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:1.5rem; color:#ef4444;">Error al cargar expedientes</td></tr>`;
    }
}

function renderMHExpedientesTable(data) {
    const tbody = document.getElementById('mh-expedientes-tbody');
    if (!tbody) return;

    if (!data.expedientes || data.expedientes.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 3rem; color: #64748b;">
                    <i class="fa-solid fa-folder-open" style="font-size: 2rem; color: #cbd5e1; margin-bottom: 8px;"></i>
                    <p style="margin: 0; font-weight: 600;">No se encontraron expedientes con los filtros seleccionados.</p>
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    data.expedientes.forEach(exp => {
        const isChecked = mhSelectedExpedientes.has(exp.id_expediente);
        const isSubsanacion = exp.categoria_estado === 'SUBSANACION';
        const isFlujo = exp.tipo_flujo === 'FLUJO';
        const hasAssignment = !!exp.usuario_asignado;
        const matchesSade = exp.coincide_tenencia_sade === true;

        let badgeValidacion = '<span style="color: #94a3b8; font-size: 0.75rem;">Sin asignar</span>';
        if (hasAssignment) {
            if (matchesSade) {
                badgeValidacion = `<span style="background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; padding: 2px 7px; border-radius: 6px; font-size: 0.75rem; font-weight: 800; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-check"></i> En poder del agente</span>`;
            } else {
                badgeValidacion = `<span style="background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; padding: 2px 7px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-triangle-exclamation"></i> En ${exp.poseedor_sade || 'SADE'}</span>`;
            }
        }

        html += `
            <tr style="border-bottom: 1px solid #f1f5f9; transition: background 0.15s ease;" class="mh-table-row">
                <td style="padding: 8px 10px; text-align: center;" onclick="event.stopPropagation();">
                    <input type="checkbox" class="mh-exp-checkbox" data-id="${exp.id_expediente}" data-exp="${exp.expediente}" ${isChecked ? 'checked' : ''} onchange="toggleMHSelectRow(${exp.id_expediente}, '${exp.expediente}', this.checked)">
                </td>
                <td style="padding: 8px 12px; cursor: pointer;" onclick="openMHExpedienteModal(${exp.id_expediente})">
                    <div style="font-weight: 800; color: #1e3a8a; font-family: 'Outfit'; font-size: 0.88rem;">
                        ${exp.expediente}
                    </div>
                    <div style="font-size: 0.74rem; color: #64748b; max-width: 320px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        ${exp.descripcion || exp.caratula || 'Sin carátula'}
                    </div>
                </td>
                <td style="padding: 8px 8px; cursor: pointer;" onclick="openMHExpedienteModal(${exp.id_expediente})">
                    <div style="font-size: 0.76rem; font-weight: 700; color: #1e3a8a; margin-bottom: 2px;">
                        ${exp.trata} - ${exp.descripcion_trata || 'Plano de Propiedad Horizontal Nuevo'}
                    </div>
                    ${isSubsanacion 
                        ? `<span style="background: #fef3c7; color: #b45309; border: 1px solid #fde68a; padding: 2px 7px; border-radius: 6px; font-size: 0.72rem; font-weight: 800; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-clock-rotate-left"></i> Subsanación TAD (${exp.dias_subs_abierta || 0}d)</span>`
                        : `<span style="background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; padding: 2px 7px; border-radius: 6px; font-size: 0.72rem; font-weight: 800;">Stock Propio</span>`
                    }
                </td>
                <td style="padding: 8px 8px; cursor: pointer;" onclick="openMHExpedienteModal(${exp.id_expediente})">
                    <div style="font-weight: 700; color: ${isFlujo ? '#059669' : '#dc2626'}; font-size: 0.82rem;">
                        ${exp.dias_en_gerencia}d en gerencia
                    </div>
                    <div style="font-size: 0.72rem; color: #64748b;">
                        ${exp.dias_en_poder}d en destino
                    </div>
                </td>
                <td style="padding: 8px 8px; cursor: pointer;" onclick="openMHExpedienteModal(${exp.id_expediente})">
                    ${hasAssignment
                        ? `<div style="font-weight: 800; color: #0f172a;"><i class="fa-solid fa-user-tag" style="color: #2563eb; margin-right: 4px;"></i>${exp.usuario_asignado}</div><div style="font-size: 0.7rem; color: #64748b;">${exp.tipo_agente === 'existente' ? 'Existente' : 'Nuevo'}</div>`
                        : `<span style="color: #94a3b8; font-style: italic;">Sin asignar</span>`
                    }
                </td>
                <td style="padding: 8px 8px; cursor: pointer;" onclick="openMHExpedienteModal(${exp.id_expediente})">
                    <div style="font-weight: 700; color: #334155;">
                        ${exp.poseedor_sade || 'Desconocido'}
                    </div>
                </td>
                <td style="padding: 8px 8px; cursor: pointer;" onclick="openMHExpedienteModal(${exp.id_expediente})">
                    ${badgeValidacion}
                </td>
                <td style="padding: 8px 8px; font-size: 0.74rem; color: #64748b; cursor: pointer;" onclick="openMHExpedienteModal(${exp.id_expediente})">
                    <div>${exp.fecha_ultimo_pase ? exp.fecha_ultimo_pase.substring(0, 16).replace('T', ' ') : '-'}</div>
                    <div style="max-width: 180px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #475569;" title="${exp.motivo_ultimo_pase || ''}">
                        ${exp.motivo_ultimo_pase || 'Sin motivo'}
                    </div>
                </td>
                <td style="padding: 8px 8px; text-align: center;" onclick="event.stopPropagation();">
                    <button onclick="openMHExpedienteModal(${exp.id_expediente})" title="Ver detalle e historial" style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px 9px; cursor: pointer; color: #2563eb; font-weight: 700;">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

function renderMHPagination(data) {
    const info = document.getElementById('mh-pagination-info');
    const btnPrev = document.getElementById('mh-btn-prev');
    const btnNext = document.getElementById('mh-btn-next');

    const start = data.offset + 1;
    const end = Math.min(data.offset + data.limit, data.total);

    if (info) {
        info.textContent = data.total > 0 ? `Mostrando ${start} - ${end} de ${data.total} expedientes` : '0 expedientes';
    }

    if (btnPrev) {
        btnPrev.disabled = data.offset <= 0;
        btnPrev.style.opacity = data.offset <= 0 ? '0.5' : '1';
    }
    if (btnNext) {
        btnNext.disabled = end >= data.total;
        btnNext.style.opacity = end >= data.total ? '0.5' : '1';
    }
}

export function changeMHPage(direction) {
    const newOffset = Math.max(0, mhCurrentOffset + (direction * mhPageLimit));
    loadSeguimientoMHExpedientes(newOffset);
}

export function debounceMHSearch() {
    clearTimeout(mhSearchDebounceTimer);
    mhSearchDebounceTimer = setTimeout(() => {
        loadSeguimientoMHExpedientes(0);
    }, 350);
}

export function filterByMHAgente(usuario) {
    const select = document.getElementById('mh-filter-agente');
    if (select) {
        select.value = usuario;
        loadSeguimientoMHExpedientes(0);
    }
}

// ── Selección y Asignación Masiva ──
export function toggleMHSelectRow(id_expediente, expediente, checked) {
    if (checked) {
        mhSelectedExpedientes.add(JSON.stringify({ id_expediente, expediente }));
    } else {
        mhSelectedExpedientes.forEach(item => {
            const parsed = JSON.parse(item);
            if (parsed.id_expediente === id_expediente) {
                mhSelectedExpedientes.delete(item);
            }
        });
    }
    updateMHSelectedUI();
}

export function toggleMHSelectAll(checked) {
    if (checked) {
        mhExpedientesList.forEach(exp => {
            mhSelectedExpedientes.add(JSON.stringify({ id_expediente: exp.id_expediente, expediente: exp.expediente }));
        });
    } else {
        mhSelectedExpedientes.clear();
    }
    document.querySelectorAll('.mh-exp-checkbox').forEach(cb => {
        cb.checked = checked;
    });
    updateMHSelectedUI();
}

function updateMHSelectedUI() {
    const label = document.getElementById('mh-selected-count-label');
    if (label) {
        label.textContent = `${mhSelectedExpedientes.size} seleccionados`;
    }
}

export async function submitMHBulkAssignment() {
    if (mhSelectedExpedientes.size === 0) {
        alert("Seleccione al menos un expediente para asignar.");
        return;
    }

    const selectTarget = document.getElementById('mh-assign-target-select');
    const usuarioTarget = selectTarget ? selectTarget.value : '';
    if (!usuarioTarget) {
        alert("Seleccione el analista al que desea asignar.");
        return;
    }

    const expedientesArray = Array.from(mhSelectedExpedientes).map(item => JSON.parse(item));

    if (!confirm(`¿Confirmar asignación de ${expedientesArray.length} expediente(s) a ${usuarioTarget}?`)) {
        return;
    }

    try {
        const resp = await def_fetch(`${API_BASE}/reportes/seguimiento-mh/asignar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                expedientes: expedientesArray,
                usuario_asignado: usuarioTarget,
                observaciones: `Asignación interna desde panel Seguimiento MH (${new Date().toLocaleDateString()})`
            })
        });

        if (!resp || !resp.ok) {
            const err = await resp.json();
            alert(`Error al asignar: ${err.detail || 'Operación fallida'}`);
            return;
        }

        const resData = await resp.json();
        alert(resData.message || "Asignación exitosa");

        mhSelectedExpedientes.clear();
        updateMHSelectedUI();
        await Promise.all([
            loadSeguimientoMHDashboard(),
            loadSeguimientoMHExpedientes(mhCurrentOffset)
        ]);
    } catch (err) {
        console.error("Error submitting bulk assignment:", err);
        alert("Error al procesar la asignación.");
    }
}

// ── Modal de Historial y Detalle de Expediente ──
export async function openMHExpedienteModal(id_expediente) {
    const modal = document.getElementById('mh-expediente-modal');
    if (!modal) return;

    modal.style.display = 'flex';
    switchMHTab('asig');

    const title = document.getElementById('mh-modal-exp-title');
    const caratula = document.getElementById('mh-modal-exp-caratula');
    const asigText = document.getElementById('mh-modal-asig-actual-text');
    const asigMeta = document.getElementById('mh-modal-asig-meta');
    const tbodyAsig = document.getElementById('mh-modal-asig-tbody');
    const tbodyPases = document.getElementById('mh-modal-pases-tbody');

    if (title) title.textContent = "Cargando expediente...";
    if (tbodyAsig) tbodyAsig.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:1.5rem;">Cargando...</td></tr>`;
    if (tbodyPases) tbodyPases.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:1.5rem;">Cargando...</td></tr>`;

    try {
        const resp = await def_fetch(`${API_BASE}/reportes/seguimiento-mh/expediente/${id_expediente}/historial`);
        if (!resp || !resp.ok) return;

        const data = await resp.json();
        const exp = data.expediente;

        if (title) title.innerHTML = `${exp.expediente} <span style="font-size: 0.8rem; font-weight: 600; color: #38bdf8; margin-left: 8px;">(${exp.trata} - ${exp.descripcion_trata || 'Plano de Propiedad Horizontal Nuevo'})</span>`;
        if (caratula) caratula.textContent = exp.descripcion || exp.caratula || 'Sin descripción';

        // Asignación Actual
        if (data.asignacion_actual) {
            const a = data.asignacion_actual;
            if (asigText) asigText.innerHTML = `<span style="color: #2563eb;">${a.usuario_asignado}</span> (${a.tipo_agente === 'existente' ? 'Agente Existente' : 'Agente Nuevo'})`;
            if (asigMeta) asigMeta.innerHTML = `Asignado por: <strong>${a.asignado_por}</strong><br>Fecha: ${a.fecha_asignacion ? a.fecha_asignacion.substring(0, 16).replace('T', ' ') : '-'}`;
        } else {
            if (asigText) asigText.textContent = "Sin asignar actualmente";
            if (asigMeta) asigMeta.textContent = "";
        }

        // Tabla de Asignaciones
        if (tbodyAsig) {
            if (!data.historial_asignaciones || data.historial_asignaciones.length === 0) {
                tbodyAsig.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:1.5rem; color:#64748b;">No registra asignaciones previas</td></tr>`;
            } else {
                tbodyAsig.innerHTML = data.historial_asignaciones.map(h => `
                    <tr style="border-bottom: 1px solid #f1f5f9;">
                        <td style="padding: 7px 10px; font-weight: 600;">${h.fecha ? h.fecha.substring(0, 16).replace('T', ' ') : '-'}</td>
                        <td style="padding: 7px 10px;">
                            <span style="font-size:0.75rem; font-weight:800; padding:2px 6px; border-radius:4px; background:${h.accion === 'ASIGNACION' ? '#ecfdf5' : h.accion === 'REASIGNACION' ? '#eff6ff' : '#fef2f2'}; color:${h.accion === 'ASIGNACION' ? '#059669' : h.accion === 'REASIGNACION' ? '#2563eb' : '#dc2626'};">
                                ${h.accion}
                            </span>
                        </td>
                        <td style="padding: 7px 10px; font-weight: 800; color:#1e3a8a;">${h.usuario_asignado}</td>
                        <td style="padding: 7px 10px; color:#64748b;">${h.usuario_anterior || '-'}</td>
                        <td style="padding: 7px 10px; font-weight: 600;">${h.asignado_por}</td>
                        <td style="padding: 7px 10px; color:#475569; font-size:0.78rem;">${h.observaciones || '-'}</td>
                    </tr>
                `).join('');
            }
        }

        // Tabla de Pases SADE
        if (tbodyPases) {
            if (!data.historial_pases || data.historial_pases.length === 0) {
                tbodyPases.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:1.5rem; color:#64748b;">No registra pases en SADE</td></tr>`;
            } else {
                tbodyPases.innerHTML = data.historial_pases.map(p => `
                    <tr style="border-bottom: 1px solid #f1f5f9;">
                        <td style="padding: 7px 10px; white-space: nowrap;">${p.fecha ? p.fecha.substring(0, 16).replace('T', ' ') : '-'}</td>
                        <td style="padding: 7px 10px; font-weight: 700; color:#334155;">${p.usuario}</td>
                        <td style="padding: 7px 10px;">${p.operacion}</td>
                        <td style="padding: 7px 10px;">
                            <span style="font-size:0.75rem; font-weight:700; padding:2px 6px; border-radius:4px; background:#f1f5f9;">${p.estado}</span>
                        </td>
                        <td style="padding: 7px 10px; font-weight: 700; color:#2563eb;">${p.destinatario}</td>
                        <td style="padding: 7px 10px; font-size:0.78rem; color:#475569;">${p.motivo || '-'}</td>
                    </tr>
                `).join('');
            }
        }

    } catch (err) {
        console.error("Error loading expediente history:", err);
    }
}

export function switchMHTab(tab) {
    const btnAsig = document.getElementById('mh-tab-btn-asig');
    const btnPases = document.getElementById('mh-tab-btn-pases');
    const contentAsig = document.getElementById('mh-tab-content-asig');
    const contentPases = document.getElementById('mh-tab-content-pases');

    if (tab === 'asig') {
        if (btnAsig) {
            btnAsig.style.border = '1px solid #cbd5e1';
            btnAsig.style.background = 'white';
            btnAsig.style.color = '#1e293b';
        }
        if (btnPases) {
            btnPases.style.border = '1px solid transparent';
            btnPases.style.background = 'transparent';
            btnPases.style.color = '#64748b';
        }
        if (contentAsig) contentAsig.style.display = 'block';
        if (contentPases) contentPases.style.display = 'none';
    } else {
        if (btnPases) {
            btnPases.style.border = '1px solid #cbd5e1';
            btnPases.style.background = 'white';
            btnPases.style.color = '#1e293b';
        }
        if (btnAsig) {
            btnAsig.style.border = '1px solid transparent';
            btnAsig.style.background = 'transparent';
            btnAsig.style.color = '#64748b';
        }
        if (contentAsig) contentAsig.style.display = 'none';
        if (contentPases) contentPases.style.display = 'block';
    }
}

export function closeMHExpedienteModal() {
    const modal = document.getElementById('mh-expediente-modal');
    if (modal) modal.style.display = 'none';
}

export function refreshSeguimientoMH() {
    loadSeguimientoMHView();
}

// Exponer en window para binding desde HTML
window.loadSeguimientoMHView = loadSeguimientoMHView;
window.refreshSeguimientoMH = refreshSeguimientoMH;
window.loadSeguimientoMHExpedientes = loadSeguimientoMHExpedientes;
window.changeMHPage = changeMHPage;
window.debounceMHSearch = debounceMHSearch;
window.filterByMHAgente = filterByMHAgente;
window.toggleMHSelectRow = toggleMHSelectRow;
window.toggleMHSelectAll = toggleMHSelectAll;
window.submitMHBulkAssignment = submitMHBulkAssignment;
window.openMHExpedienteModal = openMHExpedienteModal;
window.closeMHExpedienteModal = closeMHExpedienteModal;
window.switchMHTab = switchMHTab;
