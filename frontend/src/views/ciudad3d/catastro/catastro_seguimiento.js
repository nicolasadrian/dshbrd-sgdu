// Lógica para Seguimiento Catastro - Ciudad 3D
let catastroCurrentPage = 1;
let catastroCurrentSearch = '';
let catastroCurrentTipo = 'TODOS';
let catastroCurrentEstado = 'TODOS';

function getAuthToken() {
    return localStorage.getItem('sgdu_token') || 
           localStorage.getItem('authToken') || 
           localStorage.getItem('token') || 
           (typeof window !== 'undefined' && window.authToken ? window.authToken : '');
}

export async function loadCatastroData(forceRefresh = false) {
    const refreshIcon = document.getElementById('catastro-refresh-icon');
    if (refreshIcon) refreshIcon.classList.add('fa-spin');

    try {
        await Promise.all([
            fetchCatastroDashboard(),
            fetchCatastroList(catastroCurrentPage)
        ]);
    } catch (e) {
        console.error('Error cargando catastro:', e);
    } finally {
        if (refreshIcon) refreshIcon.classList.remove('fa-spin');
    }
}

async function fetchCatastroDashboard() {
    try {
        const token = getAuthToken();
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        const url = token ? `/api/ciudad3d/catastro/dashboard?token=${encodeURIComponent(token)}` : '/api/ciudad3d/catastro/dashboard';
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error('Error al cargar dashboard de catastro');
        const data = await res.json();

        // KPIs
        const total = data.total || 0;
        const totalEl = document.getElementById('catastro-kpi-total');
        if (totalEl) totalEl.textContent = total.toLocaleString();

        const pub = data.por_estado?.['Publicado'] || 0;
        const pubEl = document.getElementById('catastro-kpi-publicado');
        if (pubEl) pubEl.textContent = pub.toLocaleString();
        const pubPct = document.getElementById('catastro-pct-publicado');
        if (pubPct && total > 0) pubPct.textContent = `${((pub / total) * 100).toFixed(1)}% del total`;

        const inn = data.por_estado?.['Innovacion'] || 0;
        const innEl = document.getElementById('catastro-kpi-innovacion');
        if (innEl) innEl.textContent = inn.toLocaleString();
        const innPct = document.getElementById('catastro-pct-innovacion');
        if (innPct && total > 0) innPct.textContent = `${((inn / total) * 100).toFixed(1)}% del total`;

        const rev = data.por_estado?.['Error/Revision'] || 0;
        const revEl = document.getElementById('catastro-kpi-revision');
        if (revEl) revEl.textContent = rev.toLocaleString();
        const revPct = document.getElementById('catastro-pct-revision');
        if (revPct && total > 0) revPct.textContent = `${((rev / total) * 100).toFixed(1)}% del total`;

        const proc = data.por_estado?.['En Proceso'] || 0;
        const procEl = document.getElementById('catastro-kpi-proceso');
        if (procEl) procEl.textContent = proc.toLocaleString();

        const ent = data.por_estado?.['Entregado'] || 0;
        const entEl = document.getElementById('catastro-kpi-entregado');
        if (entEl) entEl.textContent = ent.toLocaleString();
        const entPct = document.getElementById('catastro-pct-entregado');
        if (entPct && total > 0) entPct.textContent = `${((ent / total) * 100).toFixed(1)}% del total`;

        const pdi = data.por_estado?.['PDI'] || 0;
        const pdiEl = document.getElementById('catastro-kpi-pdi');
        if (pdiEl) pdiEl.textContent = pdi.toLocaleString();
        const pdiPct = document.getElementById('catastro-pct-pdi');
        if (pdiPct && total > 0) pdiPct.textContent = `${((pdi / total) * 100).toFixed(1)}% del total`;
    } catch (e) {
        console.error('Error fetching catastro dashboard:', e);
    }
}

async function fetchCatastroList(page = 1) {
    const tbody = document.getElementById('catastro-table-body');
    if (!tbody) return;

    tbody.innerHTML = `
        <tr>
            <td colspan="10" style="text-align: center; padding: 2.5rem; color: #64748b;">
                <i class="fa-solid fa-spinner fa-spin" style="font-size: 1.6rem; color: #2563eb; margin-bottom: 8px; display: block;"></i>
                Cargando registros...
            </td>
        </tr>
    `;

    try {
        const token = getAuthToken();
        const params = new URLSearchParams({
            page: page,
            page_size: 50
        });

        if (catastroCurrentSearch) params.append('search', catastroCurrentSearch);
        if (catastroCurrentTipo && catastroCurrentTipo !== 'TODOS') params.append('tipo', catastroCurrentTipo);
        if (catastroCurrentEstado && catastroCurrentEstado !== 'TODOS') params.append('ciudad_3d', catastroCurrentEstado);
        if (token) params.append('token', token);

        const res = await fetch(`/api/ciudad3d/catastro/listado?${params.toString()}`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });

        if (!res.ok) throw new Error('Error al listar trámites');
        const data = await res.json();

        catastroCurrentPage = data.page;
        renderCatastroTable(data.items);
        renderCatastroPagination(data);

        const countBadge = document.getElementById('catastro-count-badge');
        if (countBadge) countBadge.textContent = `${data.total.toLocaleString()} trámites`;

        const pagInfo = document.getElementById('catastro-pagination-info');
        if (pagInfo) pagInfo.textContent = `Página ${data.page} de ${Math.max(data.pages, 1)}`;
    } catch (e) {
        console.error('Error en fetchCatastroList:', e);
        tbody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 2rem; color: #ef4444;">
                    <i class="fa-solid fa-circle-exclamation" style="font-size: 1.5rem; margin-bottom: 8px; display: block;"></i>
                    Error al cargar los datos de catastro. Intente nuevamente.
                </td>
            </tr>
        `;
    }
}

function renderCatastroTable(items) {
    const tbody = document.getElementById('catastro-table-body');
    if (!tbody) return;

    if (!items || items.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 3rem; color: #64748b;">
                    <i class="fa-regular fa-folder-open" style="font-size: 2rem; color: #94a3b8; margin-bottom: 8px; display: block;"></i>
                    No se encontraron parcelas o mensuras que coincidan con la búsqueda.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = items.map(item => {
        // Badge Estado Ciudad 3D
        let estadoBadge = '';
        const st = (item.ciudad_3d || '').trim();
        if (st === 'Publicado') {
            estadoBadge = `<span style="background: #dcfce7; color: #15803d; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.78rem; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-check"></i> Publicado</span>`;
        } else if (st === 'Innovacion') {
            estadoBadge = `<span style="background: #ffedd5; color: #c2410c; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.78rem; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-lightbulb"></i> Innovación</span>`;
        } else if (st === 'Error/Revision') {
            estadoBadge = `<span style="background: #fee2e2; color: #b91c1c; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.78rem; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-triangle-exclamation"></i> Error/Rev</span>`;
        } else if (st === 'En Proceso') {
            estadoBadge = `<span style="background: #e0f2fe; color: #0369a1; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.78rem; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-clock"></i> En Proceso</span>`;
        } else if (st === 'Entregado') {
            estadoBadge = `<span style="background: #e0e7ff; color: #4338ca; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.78rem; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-truck-ramp-box"></i> Entregado</span>`;
        } else if (st === 'PDI') {
            estadoBadge = `<span style="background: #ede9fe; color: #6d28d9; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.78rem; display: inline-flex; align-items: center; gap: 4px;"><i class="fa-solid fa-layer-group"></i> PDI</span>`;
        } else {
            estadoBadge = `<span style="background: #f1f5f9; color: #64748b; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.78rem;">${st || 'Sin Estado'}</span>`;
        }

        // Badge Check Ciudad 3D
        let checkBadge = '';
        const chk = (item.check_c3d || '').toUpperCase().trim();
        if (chk === 'OK') {
            checkBadge = `<span style="background: #dcfce7; color: #15803d; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.78rem; display: inline-flex; align-items: center; gap: 4px;" title="Verificado en Ciudad 3D"><i class="fa-solid fa-circle-check"></i> Ok</span>`;
        } else if (chk === 'PARCIAL') {
            checkBadge = `<span style="background: #fef3c7; color: #b45309; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.78rem; display: inline-flex; align-items: center; gap: 4px;" title="Algunos SMPs no encontrados"><i class="fa-solid fa-circle-half-stroke"></i> Parcial</span>`;
        } else if (chk === 'ERROR') {
            checkBadge = `<span style="background: #fee2e2; color: #b91c1c; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.78rem; display: inline-flex; align-items: center; gap: 4px;" title="No encontrado en Ciudad 3D"><i class="fa-solid fa-circle-xmark"></i> Error</span>`;
        } else if (chk === 'SIN_SMP') {
            checkBadge = `<span style="background: #f1f5f9; color: #94a3b8; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.78rem;">Sin SMP</span>`;
        } else {
            checkBadge = `<span style="background: #f1f5f9; color: #64748b; padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 0.78rem;">Pendiente</span>`;
        }

        // SMP Surgente clickeable
        const smpSurgenteVal = item.smp_surgente || '-';
        const smpSurgenteHtml = item.smp_surgente ? `
            <a href="javascript:void(0)" onclick='openCatastroDetalleModal(${JSON.stringify(item).replace(/'/g, "&#39;")})'
               style="color: #2563eb; font-weight: 700; text-decoration: underline; text-underline-offset: 3px; display: inline-flex; align-items: center; gap: 5px;"
               title="Ver logs de verificación y detalles">
                <span>${smpSurgenteVal}</span>
                <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 0.72rem; opacity: 0.7;"></i>
            </a>
        ` : `<span style="color: #94a3b8;">-</span>`;

        return `
            <tr style="border-bottom: 1px solid #f1f5f9; transition: background 0.15s;" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='white'">
                <td style="padding: 12px 16px; white-space: nowrap; color: #334155;">${item.fecha || '-'}</td>
                <td style="padding: 12px 16px; font-weight: 700; color: #0f172a; white-space: nowrap;">${item.mensura || '-'}</td>
                <td style="padding: 12px 16px; color: #475569; font-size: 0.84rem;">${item.expediente || '-'}</td>
                <td style="padding: 12px 16px;"><span style="background: #f1f5f9; color: #1e293b; padding: 2px 8px; border-radius: 6px; font-weight: 600; font-size: 0.78rem;">${item.tipo || '-'}</span></td>
                <td style="padding: 12px 16px; color: #334155; font-size: 0.85rem; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${item.smp_origen || ''}">${item.smp_origen || '-'}</td>
                <td style="padding: 12px 16px; font-size: 0.88rem; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${smpSurgenteHtml}</td>
                <td style="padding: 12px 16px; color: #64748b; font-size: 0.82rem;">${item.if_registro || '-'}</td>
                <td style="padding: 12px 16px; text-align: center;">${estadoBadge}</td>
                <td style="padding: 12px 16px; text-align: center;">${checkBadge}</td>
                <td style="padding: 12px 16px; text-align: center; white-space: nowrap;">
                    <button onclick='openCatastroEditarModal(${JSON.stringify(item).replace(/'/g, "&#39;")})'
                        style="background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; padding: 5px 10px; border-radius: 8px; cursor: pointer; font-size: 0.82rem; font-weight: 600;"
                        title="Editar trámite">
                        <i class="fa-solid fa-pen-to-square"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function renderCatastroPagination(data) {
    const container = document.getElementById('catastro-pagination-controls');
    if (!container) return;

    const { page, pages } = data;
    if (pages <= 1) {
        container.innerHTML = '';
        return;
    }

    let buttons = [];
    if (page > 1) {
        buttons.push(`<button onclick="goToCatastroPage(${page - 1})" style="padding: 6px 12px; border-radius: 8px; border: 1px solid #cbd5e1; background: white; cursor: pointer;"><i class="fa-solid fa-chevron-left"></i></button>`);
    }

    // Ventana de páginas
    const start = Math.max(1, page - 2);
    const end = Math.min(pages, page + 2);

    for (let p = start; p <= end; p++) {
        const isActive = p === page;
        buttons.push(`
            <button onclick="goToCatastroPage(${p})" 
                style="padding: 6px 12px; border-radius: 8px; border: 1px solid ${isActive ? '#2563eb' : '#cbd5e1'}; background: ${isActive ? '#2563eb' : 'white'}; color: ${isActive ? 'white' : '#334155'}; font-weight: ${isActive ? '700' : '500'}; cursor: pointer;">
                ${p}
            </button>
        `);
    }

    if (page < pages) {
        buttons.push(`<button onclick="goToCatastroPage(${page + 1})" style="padding: 6px 12px; border-radius: 8px; border: 1px solid #cbd5e1; background: white; cursor: pointer;"><i class="fa-solid fa-chevron-right"></i></button>`);
    }

    container.innerHTML = buttons.join('');
}

// Búsqueda y filtros
window.executeCatastroSearch = function () {
    const searchInp = document.getElementById('catastro-search-input');
    const tipoSel = document.getElementById('catastro-filter-tipo');
    const estadoSel = document.getElementById('catastro-filter-estado');

    catastroCurrentSearch = searchInp ? searchInp.value.trim() : '';
    catastroCurrentTipo = tipoSel ? tipoSel.value : 'TODOS';
    catastroCurrentEstado = estadoSel ? estadoSel.value : 'TODOS';
    catastroCurrentPage = 1;

    fetchCatastroList(1);
};

window.resetCatastroFilters = function () {
    const searchInp = document.getElementById('catastro-search-input');
    const tipoSel = document.getElementById('catastro-filter-tipo');
    const estadoSel = document.getElementById('catastro-filter-estado');

    if (searchInp) searchInp.value = '';
    if (tipoSel) tipoSel.value = 'TODOS';
    if (estadoSel) estadoSel.value = 'TODOS';

    catastroCurrentSearch = '';
    catastroCurrentTipo = 'TODOS';
    catastroCurrentEstado = 'TODOS';
    catastroCurrentPage = 1;

    fetchCatastroList(1);
};

window.filterCatastroByEstado = function (estado) {
    const estadoSel = document.getElementById('catastro-filter-estado');
    if (estadoSel) estadoSel.value = estado;
    catastroCurrentEstado = estado;
    catastroCurrentPage = 1;
    fetchCatastroList(1);
};

window.goToCatastroPage = function (p) {
    catastroCurrentPage = p;
    fetchCatastroList(p);
};

// Modal de Carga / Edición
window.openCatastroNuevoModal = function () {
    document.getElementById('modal-catastro-title').textContent = 'Nueva Parcela / Mensura';
    document.getElementById('catastro-form-id').value = '';
    document.getElementById('form-c-fecha').value = new Date().toISOString().split('T')[0];
    document.getElementById('form-c-tipo').value = 'UNIFICACION';
    document.getElementById('form-c-mensura').value = '';
    document.getElementById('form-c-expediente').value = '';
    document.getElementById('form-c-smp-origen').value = '';
    document.getElementById('form-c-smp-surgente').value = '';
    document.getElementById('form-c-if-registro').value = '';
    document.getElementById('form-c-registro').value = '';
    document.getElementById('form-c-ciudad3d').value = 'Innovacion';
    document.getElementById('form-c-tad').value = '';

    const modal = document.getElementById('modal-catastro-form');
    if (modal) modal.style.display = 'flex';
};

window.openCatastroEditarModal = function (item) {
    document.getElementById('modal-catastro-title').textContent = `Editar Trámite: ${item.mensura || 'ID ' + item.id}`;
    document.getElementById('catastro-form-id').value = item.id;
    document.getElementById('form-c-fecha').value = item.fecha || '';
    document.getElementById('form-c-tipo').value = item.tipo || 'UNIFICACION';
    document.getElementById('form-c-mensura').value = item.mensura || '';
    document.getElementById('form-c-expediente').value = item.expediente || '';
    document.getElementById('form-c-smp-origen').value = item.smp_origen || '';
    document.getElementById('form-c-smp-surgente').value = item.smp_surgente || '';
    document.getElementById('form-c-if-registro').value = item.if_registro || '';
    document.getElementById('form-c-registro').value = item.registro || '';
    document.getElementById('form-c-ciudad3d').value = item.ciudad_3d || 'Innovacion';
    document.getElementById('form-c-tad').value = item.tad || '';

    const modal = document.getElementById('modal-catastro-form');
    if (modal) modal.style.display = 'flex';
};

window.closeCatastroModal = function () {
    const modal = document.getElementById('modal-catastro-form');
    if (modal) modal.style.display = 'none';
};

window.saveCatastroForm = async function (e) {
    e.preventDefault();
    const btn = document.getElementById('btn-save-catastro');
    if (btn) btn.disabled = true;

    const id = document.getElementById('catastro-form-id').value;
    const isEdit = !!id;

    const payload = {
        fecha: document.getElementById('form-c-fecha').value || null,
        tipo: document.getElementById('form-c-tipo').value || null,
        mensura: document.getElementById('form-c-mensura').value || null,
        expediente: document.getElementById('form-c-expediente').value || null,
        smp_origen: document.getElementById('form-c-smp-origen').value || null,
        smp_surgente: document.getElementById('form-c-smp-surgente').value || null,
        if_registro: document.getElementById('form-c-if-registro').value || null,
        registro: document.getElementById('form-c-registro').value || null,
        ciudad_3d: document.getElementById('form-c-ciudad3d').value || null,
        tad: document.getElementById('form-c-tad').value || null
    };

    try {
        const token = getAuthToken();
        const baseEndpoint = isEdit ? `/api/ciudad3d/catastro/${id}` : '/api/ciudad3d/catastro/crear';
        const url = token ? `${baseEndpoint}?token=${encodeURIComponent(token)}` : baseEndpoint;
        const method = isEdit ? 'PUT' : 'POST';

        const res = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { 'Authorization': `Bearer ${token}` } : {})
            },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Error al guardar');
        }

        closeCatastroModal();
        await loadCatastroData(true);
    } catch (err) {
        alert(`Error al guardar trámite: ${err.message}`);
    } finally {
        if (btn) btn.disabled = false;
    }
};

// -------------------------------------------------------------------------
// Modal de Detalle de SMP Surgente & Logs de Verificación
// -------------------------------------------------------------------------
let currentDetalleItem = null;

window.openCatastroDetalleModal = function (item) {
    currentDetalleItem = item;

    document.getElementById('det-smp-mensura').textContent = item.mensura || '-';
    document.getElementById('det-smp-expediente').textContent = item.expediente || '-';
    document.getElementById('det-smp-tipo').textContent = item.tipo || '-';
    document.getElementById('det-smp-origen').textContent = item.smp_origen || '-';
    document.getElementById('det-smp-surgente-val').textContent = item.smp_surgente || '-';

    const fechaTxt = item.check_c3d_fecha ? `${item.check_c3d_fecha}` : 'Sin verificar aún';
    document.getElementById('det-smp-fecha').textContent = `Última verificación: ${fechaTxt}`;

    renderDetalleSmpsList(item.check_c3d_detalle, item.smp_surgente, item.check_c3d);

    const modal = document.getElementById('modal-catastro-detalle-smp');
    if (modal) modal.style.display = 'flex';
};

window.closeCatastroDetalleModal = function () {
    const modal = document.getElementById('modal-catastro-detalle-smp');
    if (modal) modal.style.display = 'none';
    currentDetalleItem = null;
};

function renderDetalleSmpsList(detalles, smpSurgenteRaw, overallStatus) {
    const container = document.getElementById('det-smp-lista-container');
    if (!container) return;

    if (!detalles || (Array.isArray(detalles) && detalles.length === 0)) {
        container.innerHTML = `
            <div style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 12px; padding: 1.5rem; text-align: center; color: #64748b;">
                <i class="fa-solid fa-clock-rotate-left" style="font-size: 1.5rem; margin-bottom: 6px; display: block; color: #94a3b8;"></i>
                Este trámite no tiene un log de verificación guardado todavía.<br>
                Haga clic en <b>"Rechequear Ahora"</b> para consultar la API de Ciudad 3D.
            </div>
        `;
        return;
    }

    // Asegurarse de que detalles sea una lista de objetos
    let items = Array.isArray(detalles) ? detalles : [detalles];

    container.innerHTML = items.map((d, idx) => {
        const isOk = d.status === 'OK';
        const bg = isOk ? '#f0fdf4' : '#fef2f2';
        const border = isOk ? '#bbf7d0' : '#fecaca';
        const iconColor = isOk ? '#16a34a' : '#dc2626';
        const icon = isOk ? 'fa-circle-check' : 'fa-circle-xmark';
        const tagText = isOk ? 'EXISTE EN CIUDAD 3D' : (d.mensaje || 'NO ENCONTRADO');

        return `
            <div style="background: ${bg}; border: 1px solid ${border}; border-radius: 12px; padding: 1rem 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <i class="fa-solid ${icon}" style="color: ${iconColor}; font-size: 1.2rem;"></i>
                        <span style="font-weight: 800; font-size: 1.05rem; color: #0f172a; font-family: monospace;">${d.smp || smpSurgenteRaw}</span>
                    </div>
                    <span style="font-weight: 700; font-size: 0.8rem; background: white; padding: 3px 10px; border-radius: 20px; color: ${iconColor}; border: 1px solid ${border};">
                        ${isOk ? 'OK' : 'ERROR'}
                    </span>
                </div>
                <div style="font-size: 0.86rem; color: #334155; margin-top: 4px;">
                    <b>Respuesta API:</b> ${tagText}
                </div>
                ${isOk && d.superficie_parcela ? `
                    <div style="display: flex; gap: 15px; font-size: 0.8rem; color: #64748b; margin-top: 6px;">
                        <span><b>Superficie:</b> ${d.superficie_parcela} m²</span>
                        ${d.unidad_edificabilidad ? `<span><b>Unidad:</b> ${JSON.stringify(d.unidad_edificabilidad)}</span>` : ''}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

window.recheckSmpCiudad3D = async function () {
    if (!currentDetalleItem || !currentDetalleItem.id) return;

    const btn = document.getElementById('btn-recheck-c3d');
    const icon = document.getElementById('icon-recheck-c3d');
    if (btn) btn.disabled = true;
    if (icon) icon.classList.add('fa-spin');

    try {
        const token = getAuthToken();
        const baseEndpoint = `/api/ciudad3d/catastro/verificar/${currentDetalleItem.id}`;
        const url = token ? `${baseEndpoint}?token=${encodeURIComponent(token)}` : baseEndpoint;

        const res = await fetch(url, {
            method: 'POST',
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Error al rechequear');
        }

        const data = await res.json();

        // Actualizar item local y modal
        currentDetalleItem.check_c3d = data.check_c3d;
        if (data.ciudad_3d) {
            currentDetalleItem.ciudad_3d = data.ciudad_3d;
        }
        currentDetalleItem.check_c3d_fecha = 'Recién verificado';
        currentDetalleItem.check_c3d_detalle = data.check_c3d_detalle;

        document.getElementById('det-smp-fecha').textContent = 'Última verificación: Recién verificado';
        renderDetalleSmpsList(data.check_c3d_detalle, currentDetalleItem.smp_surgente, data.check_c3d);

        // Recargar la tabla y KPIs del dashboard
        fetchCatastroList(catastroCurrentPage);
        fetchCatastroDashboard();
    } catch (e) {
        alert(`Error al rechequear: ${e.message}`);
    } finally {
        if (btn) btn.disabled = false;
        if (icon) icon.classList.remove('fa-spin');
    }
};

window.loadCatastroSeguimiento = loadCatastroData;

