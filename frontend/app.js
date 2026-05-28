const API_BASE = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1') 
    ? "http://127.0.0.1:8000/api" 
    : "/api";

// --- ESTADO DE AUTENTICACIÓN ---
let authToken = localStorage.getItem('sgdu_token');
let currentUser = JSON.parse(localStorage.getItem('sgdu_user') || 'null');
let metasChart = null;
let currentIntervencionesData = null;
let seguimientoViewMode = localStorage.getItem('sgdu_seguimiento_view_mode') || 'list';
let activeComplianceFilter = null;
let currentGerenciaConfig = {};

// Helper para fetch con autenticación
// Helper para fetch con autenticación
async function def_fetch(url, options = {}) {
    if (!options.headers) options.headers = {};
    if (authToken) {
        options.headers['Authorization'] = `Bearer ${authToken}`;
    }
    
    try {
        const response = await fetch(url, options);
        if (response.status === 401) {
            logout();
            return null;
        }
        return response;
    } catch (error) {
        console.error("Fetch error:", error);
        return null;
    }
}

function initAuth() {
    const loginOverlay = document.getElementById('login-overlay');
    const authControls = document.getElementById('auth-controls');
    const displayFullName = document.getElementById('display-fullname');
    const displaySector = document.getElementById('display-sector');
    const adminBtn = document.getElementById('admin-btn');

    if (authToken && currentUser) {
        loginOverlay.style.display = 'none';
        authControls.style.display = 'flex';
        displayFullName.innerText = currentUser.full_name || currentUser.username;
        displaySector.innerText = currentUser.sector || "General";
        
        const role = (currentUser.role || "").toLowerCase();
        
        if (role === 'administrador' || role === 'admin') {
            adminBtn.style.display = 'block';
        } else {
            adminBtn.style.display = 'none';
        }

        const seguimientoBtn = document.getElementById('seguimiento-btn');
        if (seguimientoBtn) {
            if (role === 'administrador' || role === 'admin' || role === 'seguimiento') {
                seguimientoBtn.style.display = 'block';
            } else {
                seguimientoBtn.style.display = 'none';
            }
        }

        const slaBtn = document.getElementById('sla-btn');
        if (slaBtn) {
            if (role === 'administrador' || role === 'admin' || role === 'seguimiento') {
                slaBtn.style.display = 'block';
            } else {
                slaBtn.style.display = 'none';
            }
        }

        // Si necesita cambio de clave, forzar modal
        if (currentUser.needs_password_change) {
            document.getElementById('change-password-modal').style.display = 'flex';
        }
    } else {
        loginOverlay.style.display = 'flex';
        authControls.style.display = 'none';
    }
}

async function login(username, password) {
    const errorDiv = document.getElementById('login-error');
    if (errorDiv) errorDiv.style.display = 'none';

    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Error en el login");
        }

        const data = await response.json();
        authToken = data.access_token;
        currentUser = { 
            username: data.username, 
            role: data.role, 
            full_name: data.full_name,
            sector: data.sector,
            needs_password_change: data.needs_password_change
        };

        localStorage.setItem('sgdu_token', authToken);
        localStorage.setItem('sgdu_user', JSON.stringify(currentUser));

        initAuth();
        if (!currentUser.needs_password_change) {
            handleRouting();
        }
    } catch (error) {
        if (errorDiv) {
            errorDiv.innerText = error.message;
            errorDiv.style.display = 'block';
        } else {
            alert(error.message);
        }
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('sgdu_token');
    localStorage.removeItem('sgdu_user');
    window.location.hash = '#/landing';
    initAuth();
}

const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

// --- METADATOS DE AYUDA (Para el Modal de Metodología) ---
const BUZZERS_DOCS = {
    'catastro': 'DGROC-CIC, DGROC-COPIAPLANO, DGROC-DCATDES, DGROC-DCATPOL o DGROC-DCATTIT',
    'contable': 'DGROC-CONTABLE o DGROC-OBRASADMIN',
    'instalaciones': 'DGROC-ELECTRICAS, DGROC-ELEVADORES, DGROC-INCENDIO, DGROC-SANITARIAS o DGROC-TERMICAS',
    'conforme': 'DGROC-OBRASDEMO',
    'etapa_proyecto': 'DGROC-OBRASTECNICA',
    'aviso_obra': 'DGROC-AUTOMAT',
    'morfologia': 'DGIUR-03, DGIUR-ADMISIBILIDADMORFO, DGIUR-CONSULTASESPECIFICAS, DGIUR-CURVERIFICACION o DGIUR-DGIUR-PERMISO TEMPRANO',
    'aph': 'DGIUR-21',
    'usos': 'DGIUR-12'
};

const ANALYSTS_DOCS = {
    'catastro': ["ACOSTAPA", "AFAHLER", "AGUSMAZZONI", "ALEALFONSIN", "ALEGREM", "ARGENTOES", "BARTROLIG", "CABRERAM", "CANALEAL", "CARBONELLIM", "CHIANETTAR", "CIOPKOG", "CISTERNACA", "COHENCAD", "CONTIL", "CONVERTID", "DELGADODE", "DGROC-CIC", "DGROC-COPIAPLANO", "DGROC-DCATDES", "DGROC-DCATMEN", "DGROC-DCATPOL", "DGROC-DCATTIT", "DIBIASEO", "DIEZGASTON", "DIHARCEP", "DURSIM", "ECIJAN", "FMARCHISELLA", "FOLLONIERLE", "FREIXASC", "GARCIASIL", "GILESJP", "GONZALEZAMA", "GONZALEZHORAC", "GUZMANO", "IGARZABALP", "JTIRADO", "LAGUNAMA", "LBELLY", "LOISIG", "LUCCIC", "M.NAPOLI", "MALATTOR", "MANNOP", "MARCHETTIJ", "MHOSBALIKCIYAN", "MOSCOVICHA", "NCITRANGOLO", "NOGUERAH", "NPONZO", "NQUINTERNO", "PONZOS", "ROLDANG", "SALGUEROM", "SORIAANDREA", "TARRUA", "TAVELLAE", "VEGAJ", "VILLAGI", "WVIRGILIO"],
    'aph': ["CHANTIRRO", "CHEZOM", "DAMATOG", "DESANTISA", "DGIUR-21", "DGIUR-ADMISIBILIDADAPH", "DGIUR-ADMISIMIDIDADAPH", "GALAMA", "GONZALEZNIETOR", "HERENUFE", "LSANTINMOLINA", "MARIANALVAREZ", "NASALVATIERRA", "PIOLON", "SVC_DGIURADMAPH", "VASTAM"],
    'usos': ["ALEPABLOCASTRO", "ARVASR", "AUZONMJ", "BBORGIA", "BILLAUDL", "CLAUDIAVARELA", "DALUNNI", "DGIUR-12", "DGIUR-ADMISIBILIDADUSOS", "DGIUR-EGOUS", "DIMEGLIOA", "EDUARDODIAZ", "ELIANACABRERA", "FOVERDAGUER", "JBMENDY", "JLSCIA", "JLSCIARROTTA", "LASALAMI", "LTROLDAN", "MAYASTUY", "MERCADOEA", "MFALAPPA", "MIZONCA", "MOCANA", "MOURER", "MPSIMONI", "MYASTUY", "PGLEISS", "PORTAC", "ROCCOR", "SOFIAZANI", "SVC_DGIURUSOS", "VKAUFMAN"],
    'conforme': ["AGUEROJO", "AKRACOFF", "ALVAREZ.M", "ARAOZLUIS", "ATENCIOAL", "DALBORAF", "DGROC-ESPERAINSTALACIONES", "DGROC-OBRASDEMO", "ENCISOA", "EPARLATO", "ERDOCIAINA", "JBARRACO", "JLGARMENDIA", "JTERRILE", "MYUSHU", "S.SANCHEZPAZ", "SCAVALLARO"],
    'instalaciones': ["AQUINOLUCAS", "ARENAJ", "ARGUELLOJ", "BATALLANJ", "BENITOG", "BRIANMARTINEZ", "CORNAZM", "FICARRAR", "GAGLIARDIA", "LOPARDOC", "QUEIJASGUILLINP", "ROBLEDOJO", "ROLDANMI", "RUDAC", "SARIDISD", "TOLESANOA", "AURENA", "BATALLANGE", "BRITANP", "GUARDADOB", "JDECIMA", "PEREZGA", "RODRIGUEZESTEBAN", "RODRIGUEZNE", "SILESC", "VILLAGAB", "ABCRAGNO", "AGARCIAFIGUEROA", "CABRERAARI", "CAFELICE", "CAPOZZOG", "CSALGUERO", "DARANGURI", "DMOFFA", "FUHRY", "GONMAR", "J.OLIVERA", "LOPEZFE", "MARIANELAROCARO", "MBALDOME", "MLMAMONE", "MTRENQUE", "NIEVAL", "PCHERBENCO", "RADAA", "RIOSFE", "ROMANOFLA", "SANTACRUZ", "CANTARELLTORRES", "CIRIAE", "LOIACONOANA", "MCDIAMANTI", "POUSAF", "ARGUELLOSOL", "COSSM", "EIERACI", "HAMALAG", "RUIZMA", "BRITANG", "ENCISOROMERO", "PITTERIE", "WIERZBICKIIGOR"],
    'contable': ["AMONTEVERDE", "AMORINC", "CARLOSDUARTE", "CAROJAS", "COLOTTAP", "CPENDON", "DAS", "DASTUGUEO", "DEGODOY", "DIAZBAR", "DKRENZ", "EDEFEO", "FABIANSANTILLAN", "FMHERRERA", "FSPANTI", "GARCIASEBA", "HRICCIARDI", "JOSEMARIAORTIZ", "JPOMAR", "JULILOPARDO", "LAMORGIAKA", "LBARRIENTOS", "LICETB", "M.ROSSO", "MARQUEZMAR", "MARTINEZCLA", "MLAURITO", "MMALACALZA", "NMONTEVERDE", "NMORENO", "POVIEDO", "PRESAF", "PVACEVEDO", "RIVERAMA", "ROBLEDOE", "RODRIGUEZLEA", "RODRIGUEZMAGD", "ROSARIODECRIS", "SCHULERG", "SENING", "SMERMOZ", "SORIAD", "SPOSAROAL", "TATOJ", "TIRENDIC", "TOMIPITES", "VICSOLMORE", "VILLACRI"],
    'etapa_proyecto': ["A.PEREZ", "AGUSDEMARCO", "ANTOVERA", "BELOCURESJ", "COIROL", "DBECERRACURITIMA", "DGROC-OBRASTECNICA", "DIMASOM", "DNKAINSKY", "FORGIONEA", "GAILLURJP", "GARRIONDO", "JOSEFINA.P", "M.SANCHEZ", "MARCE.TOSONI", "MARCETOSONI", "MARCETOSONI1", "MBRISA", "MCANOGARAY", "MCARLUCCIO", "MGALLARDOC", "MSTIBERTI", "NLOPEZQUIROGA", "ROCABERTJ", "SPUET", "TALAMOM", "VERA"],
    'morfologia': ["A.GUZMAN", "AGARTEAGA", "ALANDAZURI", "ALFONSOGA", "CAROLINAPRADO", "CGAMARRA", "CGENTILINI", "DANCOLOMBO", "ECAYSSIALS", "EVELYNTORRES", "FORFANO", "FOTTOGALLI", "FRANGARAY", "GBERNASCONI", "GCABADGIUR", "IANELUSTONDO", "IVALDES", "LNSPERTINO", "M.SABATINO", "MANUELALVELO", "MILAGROSTOURON", "MILENAAZULMORENO", "MLOBIANCOCRIADO", "MPLANS1", "MREIDMAN", "MVOSKIAN", "NASILANES", "NCASALE", "OVERRINA", "PTEIGA", "ROCAM", "SBONDOREVSKY", "SCABANELLAS", "SDAVIDOVSKY", "TOSELLIR", "VVINICIUS"],
    'aph': ["CHANTIRRO", "CHEZOM", "DAMATOG", "DESANTISA", "GALAMA", "GONZALEZNIETOR", "HERENUFE", "LSANTINMOLINA", "MARIANALVAREZ", "NASALVATIERRA", "PIOLON", "VASTAM"],
    'usos': ["ALEPABLOCASTRO", "ARVASR", "AUZONMJ", "BBORGIA", "BILLAUDL", "CLAUDIAVARELA", "DALUNNI", "DIMEGLIOA", "EDUARDODIAZ", "ELIANACABRERA", "FOVERDAGUER", "JBMENDY", "JLSCIA", "JLSCIARROTTA", "LASALAMI", "LTROLDAN", "MAYASTUY", "MERCADOEA", "MFALAPPA", "MIZONCA", "MOCANA", "MOURER", "MPSIMONI", "MYASTUY", "PGLEISS", "PORTAC", "ROCCOR", "SOFIAZANI", "VKAUFMAN"],
    'aviso_obra': ["DGROC-AUTOMAT"]
};

function showView(viewId, updateHash = true) {
    const views = document.querySelectorAll('.view-container');
    const targetView = document.getElementById(viewId);
    if (!targetView) {
        console.error("View not found:", viewId);
        return;
    }

    const role = (currentUser?.role || "").toLowerCase();

    // Seguridad: Solo admin puede ver la vista de admin
    if (viewId === 'admin' && (role !== 'administrador' && role !== 'admin')) {
        showView('landing');
        return;
    }

    // Seguridad: Solo admin o seguimiento pueden ver la vista de seguimiento o SLA
    if ((viewId === 'seguimiento' || viewId === 'sla') && (role !== 'administrador' && role !== 'admin' && role !== 'seguimiento')) {
        showView('landing');
        return;
    }

    views.forEach(v => {
        v.classList.remove('active');
        v.style.display = 'none';
    });
    
    targetView.style.display = 'block';
    setTimeout(() => targetView.classList.add('active'), 10);
    
    if (updateHash) {
        window.location.hash = `#/${viewId}`;
    }

    if (viewId === 'admin') {
        loadUsers();
    }

    if (viewId === 'metas') {
        loadMetasData();
    }

    if (viewId === 'seguimiento') {
        loadSeguimientoData();
    }

    if (viewId === 'sla') {
        loadSLAReporte();
    }

    if (viewId === 'family') {
        backToFamilySelector();
    }

    // Carga de reportes si es una vista de gerencia
    const gerencias = ['catastro', 'instalaciones', 'conforme', 'contable', 'etapa_proyecto', 'aviso_obra', 'morfologia', 'aph', 'usos'];
    if (gerencias.includes(viewId)) {
        setTimeout(() => loadConsolidatedReport(viewId), 50);
    }
}

async function loadConsolidatedReport(gerencia) {
    const containerId = `consolidated-table-container-${gerencia}`;
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
        <div class="loading-overlay">
            <span class="loader"></span>
            <h2 style="margin-top: 1rem; color: var(--primary-dark);">Procesando Matriz de ${gerencia.toUpperCase()}...</h2>
            <p style="color: #64748b;">Sincronizando vistas materializadas...</p>
        </div>`;

    try {
        // Cargar configuración de gerencia dinámica (para tooltips / ayuda)
        try {
            const configResp = await def_fetch(`${API_BASE}/reporte/${gerencia}/config/all`);
            if (configResp && configResp.ok) {
                currentGerenciaConfig = await configResp.json();
            }
        } catch (err) {
            console.error("Error loading gerencia config:", err);
        }

        const response = await def_fetch(`${API_BASE}/reporte/${gerencia}/consolidado`);
        if (!response.ok) {
            if (response.status === 500) throw new Error("La estructura de datos se está actualizando. Por favor, reintenta en unos instantes.");
            throw new Error(`Error de conexión (Status: ${response.status})`);
        }
        const data = await response.json();
        
        if (!data || data.length === 0) {
            container.innerHTML = `
                <div class="error-message">
                    <div class="error-icon">ℹ️</div>
                    <h3>Sin datos para ${gerencia.toUpperCase()}</h3>
                    <p>No se encontraron registros en el periodo seleccionado o la vista está siendo procesada.</p>
                </div>`;
            return;
        }

        renderMatrixTable(container, data);
    } catch (error) {
        container.innerHTML = `
            <div class="error-message">
                <div class="error-icon">⚠️</div>
                <h3>Inconveniente en el Renderizado</h3>
                <p>${error.message}</p>
                <button class="btn-primary" style="margin-top:1rem; padding:8px 16px;" onclick="loadConsolidatedReport('${gerencia}')">Reintentar Carga</button>
            </div>`;
    }
}

function buildSummaryHTML(data, allMonths, gerencia) {
    const totals = {};
    allMonths.forEach(mk => { totals[mk] = { ING: 0, EGR_EF: 0, EGR_NE: 0, STOCK_PROPIO: 0, STOCK_SUBS: 0 }; });
    data.forEach(row => {
        const mk = `${row.anio}-${row.mes}`;
        if (totals[mk]) {
            totals[mk].ING          += row.ING ?? 0;
            totals[mk].EGR_EF       += row.EGR_EF ?? 0;
            totals[mk].EGR_NE       += row.EGR_NE ?? 0;
            totals[mk].STOCK_PROPIO += row.STOCK_PROPIO ?? 0;
            totals[mk].STOCK_SUBS   += row.STOCK_SUBS ?? 0;
        }
    });

    const metrics = [
        { label: 'Ingresos',              field: 'ING',          cls: 'sum-ing'     },
        { label: 'Egresos Efectivos',     field: 'EGR_EF',       cls: 'sum-egr-ef'  },
        { label: 'Egresos No Efectivos',  field: 'EGR_NE',       cls: 'sum-egr-ne'  },
        { label: 'Egresos Totales',       field: 'EGR_TOT',      cls: 'sum-egr-tot' },
        { label: 'Stock Propio',          field: 'STOCK_PROPIO', cls: 'sum-stock'   },
        { label: 'Subsanación Abierta',   field: 'STOCK_SUBS',   cls: 'sum-subs'    },
        { label: 'Stock Total',           field: 'STOCK_TOTAL',  cls: 'sum-stock-tot' }
    ];

    const fmt = n => n.toLocaleString('es-AR');

    let html = `<div class="summary-section">
        <h3 class="summary-title">Resumen Mensual Consolidado</h3>
        <div class="summary-wrapper">
            <table class="summary-table">
                <thead><tr>
                    <th class="sum-label-col">Indicador</th>
                    ${allMonths.map(mk => `<th>${MESES[parseInt(mk.split('-')[1])-1].substring(0,3).toUpperCase()}<br><span class="sum-year">${mk.split('-')[0]}</span></th>`).join('')}
                </tr></thead>
                <tbody>`;

    metrics.forEach(m => {
        html += `<tr class="${m.cls}"><td class="sum-label">${m.label}</td>`;
        allMonths.forEach(mk => {
            const t = totals[mk];
            let val = 0;
            if (m.field === 'EGR_TOT') val = (t.EGR_EF || 0) + (t.EGR_NE || 0);
            else if (m.field === 'STOCK_TOTAL') val = (t.STOCK_PROPIO || 0) + (t.STOCK_SUBS || 0);
            else val = t[m.field] || 0;
            
            const now = new Date();
            const currentMonthKey = `${now.getFullYear()}-${now.getMonth() + 1}`;
            const isCurrent = mk === currentMonthKey;
            
            const cellClass = isCurrent ? 'sum-val current-month-cell' : 'sum-val';
            const cellStyle = isCurrent 
                ? 'font-weight: 700 !important; background-color: rgba(0, 159, 227, 0.05) !important; border-left: 2px solid rgba(0, 159, 227, 0.15) !important; border-right: 2px solid rgba(0, 159, 227, 0.15) !important;' 
                : '';
                
            let cellHTML = val !== undefined && val !== '-' ? fmt(val) : '-';
            
            if (val !== undefined && val !== '-' && val !== 0 && val !== '0' && gerencia) {
                cellHTML = `
                    <div class="current-month-cell-content">
                        <span>${cellHTML}</span>
                        <button class="btn-cell-download" onclick="downloadCellDetail('${gerencia}', 'ALL', '${m.field}', '${mk}')" title="Descargar detalle en Excel">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
                        </button>
                    </div>
                `;
            }
            
            html += `<td class="${cellClass}" style="${cellStyle}">${cellHTML}</td>`;
        });
        html += `</tr>`;
    });

    html += `</tbody></table></div></div>`;
    return html;
}

function renderMatrixTable(container, data) {
    const groups = {};
    data.forEach(row => {
        const key = row["COD TRATA"];
        if (!groups[key]) {
            groups[key] = { 
                name: row["DETALLE TRATA"], 
                months: {}, 
                acronimos: row["acronimos"]
            };
        }
        const monthKey = `${row.anio}-${row.mes}`;
        groups[key].months[monthKey] = row;
    });

    const allMonths = [...new Set(data.map(r => `${r.anio}-${r.mes}`))].sort((a,b) => {
        const [y1, m1] = a.split('-').map(Number);
        const [y2, m2] = b.split('-').map(Number);
        return y1 === y2 ? m1 - m2 : y1 - y2;
    });

    const gerenciaKey = container.id.split('-').pop();
    let html = buildSummaryHTML(data, allMonths, gerenciaKey);

    html += `
    <div class="main-card-container">
        <div class="matrix-table-wrapper">
            <table class="matrix-table">
                <thead>
                    <tr>
                        <th style="min-width: 250px; text-align: left;">TRÁMITE / MÉTRICA</th>
                        ${allMonths.map(mk => `<th></th>`).join('')}
                    </tr>
                </thead>
                <tbody>`;

    const sortedTrataIds = Object.keys(groups).sort((a, b) => {
        if (a === 'INTERVENCIONES') return 1;
        if (b === 'INTERVENCIONES') return -1;
        return 0; 
    });

    sortedTrataIds.forEach(trataId => {
        const group = groups[trataId];
        const gerenciaKey = container.id.split('-').pop();
        const rawName = group.name || trataId;
        const groupName = rawName.toString().replace(/\r?\n|\r/g, ' ').trim();
        const safeName = groupName.replace(/'/g, "\\'").replace(/"/g, '&quot;');
        const safeAcronimos = (group.acronimos || '').toString().replace(/\r?\n|\r/g, ' ').replace(/'/g, '').replace(/"/g, '&quot;').trim();

        html += `
            <tr class="trata-group-header">
                <td style="background: var(--primary-dark); color: white; border-top-left-radius: 8px; border-bottom-left-radius: 8px;">
                    <div class="trata-title-wrapper">
                        <a href="#" class="trata-link" style="color: white;" onclick="event.preventDefault(); showTrataDetail('${gerenciaKey}', '${trataId}', '${safeName}')">
                            ${groupName.toUpperCase()}
                        </a>
                        <span class="info-icon" onclick="event.stopPropagation(); openHelpModal('${trataId}', '${gerenciaKey}', '${safeName}', '${safeAcronimos}')">i</span>
                        <span class="trata-id-tag" style="background: rgba(255,255,255,0.2); color: white;">${trataId}</span>
                    </div>
                </td>
                ${allMonths.map((mk, i) => {
                    const now = new Date();
                    const currentMonthKey = `${now.getFullYear()}-${now.getMonth() + 1}`;
                    const isCurrent = mk === currentMonthKey;
                    
                    const cellStyle = isCurrent 
                        ? 'background: var(--primary) !important; color: white !important; font-weight: 800; border-left: 2px solid rgba(255, 255, 255, 0.25); border-right: 2px solid rgba(255, 255, 255, 0.25);' 
                        : 'background: var(--primary-dark); color: rgba(255,255,255,0.7);';
                        
                    return `
                        <td style="${cellStyle} font-size: 0.75rem; text-align: center; vertical-align: middle; ${i === allMonths.length - 1 ? 'border-top-right-radius: 8px; border-bottom-right-radius: 8px;' : ''}">
                            ${MESES[parseInt(mk.split('-')[1])-1].substring(0,3).toUpperCase()}<br>${mk.split('-')[0]}
                        </td>
                    `;
                }).join('')}
            </tr>`;

        const metrics = [
            { label: 'INGRESOS',             field: 'ING',          rowCls: 'row-ing' },
            { label: 'EGRESOS EFECTIVOS',    field: 'EGR_EF',       rowCls: '' },
            { label: 'EGRESOS NO EFECTIVOS', field: 'EGR_NE',       rowCls: '' },
            { label: 'EGRESOS TOTALES',      field: 'EGR_TOT',      rowCls: 'row-egr-tot' },
            { label: 'STOCK PROPIO',         field: 'STOCK_PROPIO', rowCls: 'row-stock-p' },
            { label: 'SUBSANACIÓN ABIERTA',  field: 'STOCK_SUBS',   rowCls: 'row-stock-s' },
            { label: 'STOCK TOTAL',          field: 'STOCK_TOTAL',  rowCls: 'row-stock-tot' }
        ];

        metrics.forEach(metric => {
            html += `<tr class="metric-row ${metric.rowCls}">
                <td class="metric-label" style="${metric.label === 'INGRESOS' ? 'font-weight: 800;' : ''}">${metric.label}</td>`;
            
            allMonths.forEach(mk => {
                const row = group.months[mk];
                let val = '-';
                if (row) {
                    if (metric.field === 'EGR_TOT') val = (row.EGR_EF || 0) + (row.EGR_NE || 0);
                    else if (metric.field === 'STOCK_TOTAL') val = (row.STOCK_PROPIO || 0) + (row.STOCK_SUBS || 0);
                    else val = row[metric.field];
                }
                
                const now = new Date();
                const currentMonthKey = `${now.getFullYear()}-${now.getMonth() + 1}`;
                const isCurrent = mk === currentMonthKey;
                
                const cellClass = isCurrent ? 'metric-value current-month-cell' : 'metric-value';
                const cellStyle = isCurrent 
                    ? 'font-weight: 700 !important; background-color: rgba(0, 159, 227, 0.05) !important; border-left: 2px solid rgba(0, 159, 227, 0.15) !important; border-right: 2px solid rgba(0, 159, 227, 0.15) !important;' 
                    : '';
                
                let cellHTML = val !== undefined && val !== '-' ? val.toLocaleString('es-AR') : '-';
                
                if (val !== undefined && val !== '-' && val !== 0 && val !== '0') {
                    cellHTML = `
                        <div class="current-month-cell-content">
                            <span>${cellHTML}</span>
                            <button class="btn-cell-download" onclick="downloadCellDetail('${gerenciaKey}', '${trataId}', '${metric.field}', '${mk}')" title="Descargar detalle en Excel">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
                            </button>
                        </div>
                    `;
                }
                    
                html += `<td class="${cellClass}" style="${cellStyle}">${cellHTML}</td>`;
            });
            html += `</tr>`;
        });
    });

    html += `</tbody></table></div></div>`;
    container.innerHTML = html;
    gsap.from(".main-card-container", { opacity: 0, y: 20, duration: 0.5, ease: "power2.out" });
}

// Nueva función para manejar las rutas
async function handleRouting() {
    const hash = window.location.hash.substring(2); // Quitar "#/"
    if (!hash) {
        showView('landing', false);
        return;
    }

    const parts = hash.split('/');
    const viewId = parts[0];
    
    if (parts.length === 2) {
        // Detalle de trámite: #/gerencia/trataCode
        const gerencia = parts[0];
        const trataCode = parts[1];
        
        // Primero mostramos la vista base por si acaso
        showView(gerencia, false);
        
        // Intentamos obtener el nombre del trámite desde la configuración (o fallback)
        const trataName = "..."; 
        showTrataDetail(gerencia, trataCode, trataName, false);
    } else {
        showView(viewId, false);
    }
}

// Escuchar cambios en la URL
window.addEventListener('hashchange', handleRouting);

// Carga inicial
window.addEventListener('DOMContentLoaded', () => {
    initAuth();
    handleRouting();

    // Event listener para login
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const u = document.getElementById('login-username').value;
            const p = document.getElementById('login-password').value;
            login(u, p);
        });
    }

    // Event listener para crear usuario
    const createUserForm = document.getElementById('create-user-form');
    if (createUserForm) {
        createUserForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('new-username').value;
            const password = document.getElementById('new-password').value;
            const role = document.getElementById('new-role').value;
            const full_name = document.getElementById('new-fullname').value;
            const sector = document.getElementById('new-sector').value;
            const email = document.getElementById('new-email').value;
            
            try {
                const resp = await def_fetch(`${API_BASE}/admin/users`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password, role, full_name, sector, email })
                });
                if (resp && resp.ok) {
                    alert('Usuario creado correctamente');
                    createUserForm.reset();
                    loadUsers();
                } else {
                    const err = await resp.json();
                    alert('Error: ' + err.detail);
                }
            } catch (err) {
                alert('Error al crear usuario');
            }
        });
    }

    // Event listener para cambio de contraseña forzado
    const changePwdForm = document.getElementById('change-password-form');
    if (changePwdForm) {
        changePwdForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const p1 = document.getElementById('new-secure-password').value;
            const p2 = document.getElementById('confirm-secure-password').value;
            const errDiv = document.getElementById('change-password-error');
            
            if (p1 !== p2) {
                errDiv.innerText = "Las contraseñas no coinciden";
                return;
            }

            try {
                const resp = await def_fetch(`${API_BASE}/auth/change-password`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ new_password: p1 })
                });

                if (resp && resp.ok) {
                    alert('Contraseña actualizada. ¡Bienvenido!');
                    document.getElementById('change-password-modal').style.display = 'none';
                    currentUser.needs_password_change = false;
                    localStorage.setItem('sgdu_user', JSON.stringify(currentUser));
                    handleRouting();
                } else {
                    const err = await resp.json();
                    errDiv.innerText = err.detail;
                }
            } catch (err) {
                errDiv.innerText = "Error al conectar con el servidor";
            }
        });
    }

    // Event listener para editar usuario
    const editUserForm = document.getElementById('edit-user-form');
    if (editUserForm) {
        editUserForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('edit-username-hidden').value;
            const full_name = document.getElementById('edit-fullname').value;
            const role = document.getElementById('edit-role').value;
            const password = document.getElementById('edit-password').value;
            
            const data = { full_name, role };
            if (password) data.password = password;

            try {
                const resp = await def_fetch(`${API_BASE}/admin/users/${username}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (resp && resp.ok) {
                    alert('Usuario actualizado');
                    closeModal('edit-user-modal');
                    loadUsers();
                } else {
                    const err = await resp.json();
                    alert(err.detail);
                }
            } catch (err) {
                alert("Error al actualizar");
            }
        });
    }
});

let currentChart = null;
let currentStockAgeChart = null;
let currentStockData = { expedientes: [], trataName: "", trataCode: "" };
let currentGerencia = "";
let currentTrataCode = "";
let currentTrataName = "";

async function showTrataDetail(gerencia, trataCode, trataName, updateHash = true, fromSeguimiento = false) {
    const views = document.querySelectorAll('.view-container');
    views.forEach(v => { v.classList.remove('active'); v.style.display = 'none'; });
    
    const detailView = document.getElementById('trata_detail');
    detailView.style.display = 'block';
    detailView.classList.add('active');
    
    currentGerencia = gerencia; // Guardar gerencia actual para el módulo de metas
    currentTrataCode = trataCode; // Guardar trata actual
    currentTrataName = trataName; // Guardar nombre actual
    
    // Resetear a sección STOCK
    switchTrataSection('stock');
    
    // Setear fecha de cabecera
    const now = new Date();
    // document.getElementById('header-stock-date').innerText = now.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit' }); // Ya no se usa segun el diseño de 2 tags
    document.getElementById('header-stock-propio').innerText = '0';
    document.getElementById('header-stock-subs').innerText = '0';

    // Control de permisos para la pestaña METAS
    const role = (currentUser?.role || "").toLowerCase();
    const canSeeMetas = role === 'administrador' || role === 'admin' || role === 'seguimiento';
    const metasTabBtn = document.querySelector('.tab-btn[onclick*="metas"]');
    if (metasTabBtn) {
        metasTabBtn.style.display = canSeeMetas ? 'block' : 'none';
    }
    
    if (updateHash) {
        window.location.hash = `#/${gerencia}/${trataCode}`;
    }
    
    if (currentChart) { currentChart.destroy(); currentChart = null; }
    if (currentStockAgeChart) { currentStockAgeChart.destroy(); currentStockAgeChart = null; }
    if (metasChart) { metasChart.destroy(); metasChart = null; }
    
    document.getElementById('analyst-table-container').innerHTML = '<div style="padding: 20px; text-align: center; color: #64748b;">Cargando análisis de stock...</div>';
    
    const mainChartCtx = document.getElementById('trata-chart');
    if (mainChartCtx) {
        mainChartCtx.parentElement.innerHTML = '<canvas id="trata-chart"></canvas>';
    }

    const ageChartCtx = document.getElementById('stock-age-chart');
    if (ageChartCtx) ageChartCtx.parentElement.innerHTML = '<canvas id="stock-age-chart"></canvas>';

    if (trataCode === 'INTERVENCIONES') {
        document.getElementById('trata_detail_title').innerText = 'INTERVENCIONES';
    } else {
        document.getElementById('trata_detail_title').innerText = trataName;
    }
    document.getElementById('trata_detail_subtitle').innerText = trataCode;

    // Determinar la dirección superior (DGROC o DGIUR)
    const dgiurGerencias = ['morfologia', 'aph', 'usos'];
    const isDGIUR = dgiurGerencias.includes(gerencia);
    const parentDir = isDGIUR ? 'dgiur' : 'dgroc';
    
    // Actualizar Breadcrumbs
    const parentLink = document.getElementById('trata_detail_parent_link');
    if (fromSeguimiento === 'sla') {
        parentLink.innerText = 'SLA';
        parentLink.onclick = () => showView('sla');
    } else if (fromSeguimiento) {
        parentLink.innerText = 'SEGUIMIENTO';
        parentLink.onclick = () => showView('seguimiento');
    } else {
        parentLink.innerText = parentDir.toUpperCase();
        parentLink.onclick = () => showView(parentDir);
    }

    const backBtn = document.getElementById('trata_detail_back');
    if (backBtn && gerencia) {
        if (fromSeguimiento === 'sla') {
            backBtn.innerText = 'Volver a SLA';
            backBtn.onclick = () => {
                showView('sla');
            };
        } else if (fromSeguimiento) {
            backBtn.innerText = 'Volver a Seguimiento';
            backBtn.onclick = () => {
                showView('seguimiento');
            };
        } else {
            const cleanGerencia = gerencia.charAt(0).toUpperCase() + gerencia.slice(1).replace('_', ' ');
            backBtn.innerText = cleanGerencia;
            backBtn.onclick = () => {
                window.location.hash = `#/${gerencia}`;
            };
        }
    }

    const intervContainer = document.getElementById('intervenciones-detail-container');
    if (intervContainer) {
        if (trataCode === 'INTERVENCIONES') {
            intervContainer.style.display = 'block';
            loadIntervencionesDetail(gerencia);
        } else {
            intervContainer.style.display = 'none';
        }
    }

    try {
        const response = await def_fetch(`${API_BASE}/reporte/${gerencia}/tramite/${trataCode}`);
        if (!response.ok) throw new Error(`Status ${response.status}`);
        
        const data = await response.json();
        
        if (!data || !Array.isArray(data) || data.length === 0) {
            return;
        }

        // --- VALORES DE STOCK EN CABECERA ---
        const latest = data[0]; 
        
        // Actualizar título real si no estaba disponible
        if (latest["DETALLE TRATA"]) {
            document.getElementById('trata_detail_title').innerText = latest["DETALLE TRATA"];
            document.getElementById('breadcrumb_trata_name').innerText = latest["DETALLE TRATA"];
        }

        animateValue('header-stock-propio', 0, latest.STOCK_PROPIO || 0, 1500);
        animateValue('header-stock-subs', 0, latest.STOCK_SUBS || 0, 1500);

        // --- TOTALES 12 MESES ---
        const totalIng = data.reduce((acc, d) => acc + (d.ING || 0), 0);
        const totalEgrEf = data.reduce((acc, d) => acc + (d.EGR_EF || 0), 0);
        const totalEgrNe = data.reduce((acc, d) => acc + (d.EGR_NE || 0), 0);

        animateValue('summary-total-ing', 0, totalIng, 1500);
        animateValue('summary-total-egr-ef', 0, totalEgrEf, 1500);
        animateValue('summary-total-egr-ne', 0, totalEgrNe, 1500);

        // --- LÓGICA DE SEMÁFORO (Sección Metas) ---
        let progress = 0;
        if (latest.ING > 0) {
            progress = Math.min(100, Math.round(((latest.EGR_EF || 0) / latest.ING) * 100));
        } else if (latest.EGR_EF > 0) {
            progress = 100;
        }
        animateSemaphore(progress);

        // Invertimos para el gráfico
        const chartData = [...data].reverse();
        
        const chartCanvas = document.getElementById('trata-chart');
        if (!chartCanvas) return;

        const ctx = chartCanvas.getContext('2d');
        currentChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: chartData.map(d => `${MESES[d.mes - 1]} ${d.anio}`),
                datasets: [
                    { label: 'Stock Propio', data: chartData.map(d => d.STOCK_PROPIO || 0), type: 'line', borderColor: '#EF4444', backgroundColor: '#EF4444', borderWidth: 3, tension: 0.3, pointRadius: 4, order: 0 },
                    { label: 'Subsanación Abierta', data: chartData.map(d => d.STOCK_SUBS || 0), type: 'line', borderColor: '#F59E0B', backgroundColor: '#F59E0B', borderWidth: 3, tension: 0.3, pointRadius: 4, order: 1 },
                    { label: 'Ingresos', data: chartData.map(d => d.ING || 0), backgroundColor: '#002d47', borderRadius: 4, order: 2 },
                    { label: 'Egresos Efectivos', data: chartData.map(d => d.EGR_EF || 0), backgroundColor: '#0076bb', stack: 'egresos', borderRadius: 4, order: 3 },
                    { label: 'Egresos No Efectivos', data: chartData.map(d => d.EGR_NE || 0), backgroundColor: '#94A3B8', stack: 'egresos', order: 4 }
                ]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false, 
                plugins: { legend: { position: 'bottom' } },
                scales: { y: { beginAtZero: true, grid: { color: '#f1f5f9' } }, x: { grid: { display: false } } } 
            }
        });

        // Cargar detalles de stock
        const stockResp = await def_fetch(`${API_BASE}/reporte/${gerencia}/tramite/${trataCode}/stock_detail`);
        if (stockResp.ok) {
            const stockData = await stockResp.json();
            currentStockData = { expedientes: stockData.expedientes || [], trataName, trataCode };
            renderStockAgeChart(stockData.month_distribution);
            renderAnalystTable(stockData.analyst_distribution);
        }
    } catch (error) { 
        console.warn("Error cargando detalle:", error.message);
    }
}

function switchTrataSection(sectionId) {
    const role = (currentUser?.role || "").toLowerCase();
    const canSeeMetas = role === 'administrador' || role === 'admin' || role === 'seguimiento';

    if (sectionId === 'metas' && !canSeeMetas) {
        alert("No tienes permisos para ver esta sección.");
        return;
    }

    // Ocultar todas las secciones
    document.querySelectorAll('.trata-section').forEach(s => s.classList.remove('active'));
    // Desactivar todos los botones
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    
    // Mostrar la seleccionada
    const targetSection = document.getElementById(`section-${sectionId}`);
    if (targetSection) targetSection.classList.add('active');
    
    // Activar botón (buscando por el texto o el onclick)
    const buttons = document.querySelectorAll('.tab-btn');
    buttons.forEach(btn => {
        const clickAttr = btn.getAttribute('onclick') || "";
        if (clickAttr.includes(`'${sectionId}'`)) {
            btn.classList.add('active');
        }
    });

    if (sectionId === 'metas') {
        loadMetasData();
    }
}

function animateValue(id, start, end, duration) {
    const obj = document.getElementById(id);
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start).toLocaleString('es-AR');
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

function animateSemaphore(targetPercent) {
    const fill = document.getElementById('meta-progress-fill');
    const label = document.getElementById('meta-percentage');
    
    if (fill) gsap.to(fill, { width: `${targetPercent}%`, duration: 1.5, ease: "power2.out" });
    
    if (label) {
        let counter = { val: 0 };
        gsap.to(counter, {
            val: targetPercent,
            duration: 1.5,
            onUpdate: function() {
                label.innerText = `${Math.round(counter.val)}%`;
            }
        });
    }
}

function renderStockAgeChart(monthDist) {
    const canvas = document.getElementById('stock-age-chart');
    if (!canvas) return;
    
    // Forzar redimensionamiento del canvas al contenedor
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    
    const ctx = canvas.getContext('2d');
    if (currentStockAgeChart) {
        currentStockAgeChart.destroy();
    }

    if (!monthDist || monthDist.length === 0) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = "16px 'Outfit', sans-serif";
        ctx.fillStyle = "#94a3b8";
        ctx.textAlign = "center";
        ctx.fillText("No hay stock propio registrado", canvas.width/2, canvas.height/2);
        return;
    }

    const labels = monthDist.map(d => { 
        if (!d.periodo || !d.periodo.includes('-')) return d.periodo;
        const [y, m] = d.periodo.split('-'); 
        return `${MESES[parseInt(m)-1]} ${y}`; 
    });

    currentStockAgeChart = new Chart(ctx, {
        type: 'bar',
        data: { 
            labels, 
            datasets: [{ 
                label: 'Stock Propio', 
                data: monthDist.map(d => d.cantidad), 
                backgroundColor: '#0076bb',
                hoverBackgroundColor: '#002d47',
                borderRadius: 6,
                maxBarThickness: 50
            }] 
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: false, 
            animation: { duration: 1000, easing: 'easeOutQuart' },
            scales: { 
                y: { 
                    beginAtZero: true, 
                    ticks: { stepSize: 1, color: '#64748b', font: { family: 'Outfit' } },
                    grid: { color: '#f1f5f9' }
                },
                x: { 
                    ticks: { color: '#64748b', font: { family: 'Outfit' } },
                    grid: { display: false } 
                }
            },
            plugins: { 
                legend: { display: false },
                tooltip: { 
                    backgroundColor: '#002d47',
                    padding: 12,
                    titleFont: { size: 14, family: 'Outfit' },
                    bodyFont: { size: 13, family: 'Outfit' }
                }
            } 
        }
    });
}

function renderAnalystTable(analystDist) {
    const container = document.getElementById('analyst-table-container');
    const ranges = ["Menos de 15 dias", "15 a 30 dias", "30 a 45 dias", "45 a 60 dias", "60 a 75 dias", "75 a 90 dias", "Mas de 90 dias"];
    let html = `<table class="matrix-table analyst-table"><thead><tr><th>ANALISTA</th>${ranges.map(r => `<th>${r.replace(' dias', 'd')}</th>`).join('')}<th>TOTAL</th></tr></thead><tbody>`;
    
    analystDist.forEach(row => {
        html += `<tr>
            <td>${row.analista}</td>
            ${ranges.map(r => `<td>${row[r] || '-'}</td>`).join('')}
            <td style="font-weight:700;">${row.TOTAL}</td>
        </tr>`;
    });
    container.innerHTML = html + `</tbody></table>`;
}

async function loadIntervencionesDetail(gerencia) {
    const wrapper = document.getElementById('intervenciones-table-wrapper');
    try {
        const response = await def_fetch(`${API_BASE}/reporte/${gerencia}/intervenciones/detalle`);
        const data = await response.json();
        currentIntervencionesData = data;
        currentGerencia = gerencia;
        if (!data || data.length === 0) { 
            wrapper.innerHTML = '<div style="padding:20px; text-align:center; color:#64748b;">No hay stock de intervenciones externas.</div>'; 
            return; 
        }

        const ranges = ["Menos de 15 dias", "15 a 30 dias", "30 a 45 dias", "45 a 60 dias", "60 a 75 dias", "75 a 90 dias", "Mas de 90 dias"];
        
        let html = `
            <table class="matrix-table analyst-table">
                <thead>
                    <tr>
                        <th style="width:120px;">TRATA</th>
                        <th>DETALLE</th>
                        ${ranges.map(r => `<th>${r.replace(' dias', 'd')}</th>`).join('')}
                        <th>TOTAL</th>
                    </tr>
                </thead>
                <tbody>`;

        data.forEach(item => {
            html += `
                <tr>
                    <td class="code-cell">${item.trata}</td>
                    <td>${item.detalle}</td>
                    ${ranges.map(r => `<td>${item[r] || '-'}</td>`).join('')}
                    <td style="font-weight:700;">${item.TOTAL}</td>
                </tr>`;
        });
        
        wrapper.innerHTML = html + '</tbody></table>';
    } catch (err) { 
        console.error(err);
        wrapper.innerHTML = '<div class="error-message">Error cargando desglose de intervenciones.</div>'; 
    }
}

function openDrillDown(analista) {
    const modal = document.getElementById('stock-drilldown-modal');
    document.getElementById('modal-analyst-name').innerText = `Analista: ${analista}`;
    document.getElementById('modal-trata-info').innerText = `Gestión de Stock: ${currentStockData.trataName}`;
    const filtered = currentStockData.expedientes.filter(e => e.analista === analista);
    let html = `<table class="matrix-table"><thead><tr><th>Expediente</th><th>ID</th><th>Fecha Ingreso</th><th>Días</th></tr></thead><tbody>`;
    filtered.forEach(e => { html += `<tr><td class="code-cell">${e.expediente}</td><td class="code-cell">${e.id_expediente}</td><td>${new Date(e.fecha_ing).toLocaleDateString()}</td><td>${e.dias}</td></tr>`; });
    document.getElementById('modal-table-container').innerHTML = html + `</tbody></table>`;
    modal.style.display = 'flex';
}

function openTrataDrillDown(trataCode) {
    const modal = document.getElementById('stock-drilldown-modal');
    document.getElementById('modal-analyst-name').innerText = `Trámite: ${trataCode}`;
    document.getElementById('modal-trata-info').innerText = `Desglose de Intervención de Terceros`;
    
    // Filtramos los expedientes por el código de trata (limpiando espacios)
    const filtered = currentStockData.expedientes.filter(e => (e.trata || '').trim() === trataCode.trim());
    
    let html = `<table class="matrix-table"><thead><tr><th>Expediente</th><th>ID</th><th>Analista</th><th>Días</th></tr></thead><tbody>`;
    filtered.forEach(e => { 
        html += `<tr><td class="code-cell">${e.expediente}</td><td class="code-cell">${e.id_expediente}</td><td>${e.analista || 'SIN ASIGNAR'}</td><td>${e.dias}</td></tr>`; 
    });
    
    document.getElementById('modal-table-container').innerHTML = html + `</tbody></table>`;
    modal.style.display = 'flex';
}

function closeModal(id) { document.getElementById(id || 'stock-drilldown-modal').style.display = 'none'; }

// --- FUNCIONES DESCARGA POR ANTIGÜEDAD DE STOCK ---
function openStockAgeDownloadModal() {
    if (!currentStockData || !currentStockData.expedientes || currentStockData.expedientes.length === 0) {
        alert("No hay expedientes en el stock de esta trata para descargar.");
        return;
    }
    
    // Obtener meses únicos de los expedientes actuales
    const monthsSet = new Set();
    currentStockData.expedientes.forEach(e => {
        if (e.fecha_ultimo_pase) {
            const m = e.fecha_ultimo_pase.substring(0, 7); // "YYYY-MM"
            monthsSet.add(m);
        }
    });
    
    const sortedMonths = Array.from(monthsSet).sort().reverse();
    
    const listContainer = document.getElementById('stock-age-months-list');
    listContainer.innerHTML = '';
    
    if (sortedMonths.length === 0) {
        listContainer.innerHTML = '<div style="color: #64748b; text-align: center; padding: 15px; font-size: 0.9rem;">No se encontraron períodos válidos de último movimiento.</div>';
        document.getElementById('stock-age-download-modal').style.display = 'flex';
        return;
    }
    
    sortedMonths.forEach(m => {
        const [y, mNum] = m.split('-');
        const labelText = `${MESES[parseInt(mNum)-1]} ${y}`;
        const itemHtml = `
            <label class="download-chk-card">
                <input type="checkbox" name="stock-age-month-chk" value="${m}" checked>
                <span>${labelText}</span>
            </label>
        `;
        listContainer.insertAdjacentHTML('beforeend', itemHtml);
    });
    
    const modal = document.getElementById('stock-age-download-modal');
    modal.style.display = 'flex';
    gsap.fromTo(modal.querySelector('.modal-content'), 
        { scale: 0.9, opacity: 0, y: 30 }, 
        { scale: 1, opacity: 1, y: 0, duration: 0.35, ease: "back.out(1.5)" }
    );
}

function toggleAllStockAgeMonths(checked) {
    const checkboxes = document.querySelectorAll('input[name="stock-age-month-chk"]');
    checkboxes.forEach(cb => cb.checked = checked);
}

function triggerStockAgeDownload() {
    const checkedBoxes = document.querySelectorAll('input[name="stock-age-month-chk"]:checked');
    const selectedMonths = Array.from(checkedBoxes).map(cb => cb.value);
    
    if (selectedMonths.length === 0) {
        alert("Debe seleccionar al menos un período para descargar.");
        return;
    }
    
    // Filtrar expedientes del stock que corresponden a los meses elegidos
    const filtered = currentStockData.expedientes.filter(e => {
        if (!e.fecha_ultimo_pase) return false;
        const m = e.fecha_ultimo_pase.substring(0, 7);
        return selectedMonths.includes(m);
    });
    
    if (filtered.length === 0) {
        alert("No hay expedientes en el stock para los períodos seleccionados.");
        return;
    }
    
    // Formatear datos legibles para el Excel consolidado
    const excelData = filtered.map(e => ({
        "EXPEDIENTE": e.expediente,
        "ID EXPEDIENTE": e.id_expediente,
        "TRATA": e.trata || currentStockData.trataCode,
        "TRAMITE (DESCRIPCION)": e.descripcion_trata || "S/D",
        "DETALLE (MOTIVO)": e.descripcion || "S/D",
        "ESTADO ACTUAL SADE": e.estado_expediente || "S/D",
        "FECHA CARATULACION": e.caratula ? e.caratula.substring(0, 10) : "S/D",
        "FECHA INGRESO A GERENCIA": e.fecha_ing ? e.fecha_ing.substring(0, 10) : "S/D",
        "FECHA ULTIMO PASE": e.fecha_ultimo_pase ? e.fecha_ultimo_pase.substring(0, 10) : "S/D",
        "DIAS EN PODER ACTUAL": e.dias,
        "DIAS ACUMULADOS EN GERENCIA": e.dias_en_gerencia || 0,
        "ANALISTA ASIGNADO": e.analista || "SIN ASIGNAR"
    }));
    
    const filename = `Stock_${currentStockData.trataCode}_Antiguedad_${selectedMonths.join('_')}`;
    downloadExcel(filename, excelData);
    closeModal('stock-age-download-modal');
}

function openStockAnalystDownloadModal() {
    if (!currentStockData || !currentStockData.expedientes || currentStockData.expedientes.length === 0) {
        alert("No hay expedientes en el stock de esta trata para descargar.");
        return;
    }
    
    // Obtener analistas únicos de los expedientes actuales
    const analystsSet = new Set();
    currentStockData.expedientes.forEach(e => {
        const name = e.analista || "SIN ASIGNAR";
        analystsSet.add(name);
    });
    
    const sortedAnalysts = Array.from(analystsSet).sort((a, b) => {
        if (a === "SIN ASIGNAR") return 1;
        if (b === "SIN ASIGNAR") return -1;
        return a.localeCompare(b);
    });
    
    const listContainer = document.getElementById('stock-analysts-list');
    listContainer.innerHTML = '';
    
    if (sortedAnalysts.length === 0) {
        listContainer.innerHTML = '<div style="color: #64748b; text-align: center; padding: 15px; font-size: 0.9rem;">No se encontraron analistas activos.</div>';
        document.getElementById('stock-analyst-download-modal').style.display = 'flex';
        return;
    }
    
    sortedAnalysts.forEach(analyst => {
        const itemHtml = `
            <label class="download-chk-card">
                <input type="checkbox" name="stock-analyst-chk" value="${analyst}" checked>
                <span>${analyst}</span>
            </label>
        `;
        listContainer.insertAdjacentHTML('beforeend', itemHtml);
    });
    
    const modal = document.getElementById('stock-analyst-download-modal');
    modal.style.display = 'flex';
    gsap.fromTo(modal.querySelector('.modal-content'), 
        { scale: 0.9, opacity: 0, y: 30 }, 
        { scale: 1, opacity: 1, y: 0, duration: 0.35, ease: "back.out(1.5)" }
    );
}

function toggleAllStockAnalysts(checked) {
    const checkboxes = document.querySelectorAll('input[name="stock-analyst-chk"]');
    checkboxes.forEach(cb => cb.checked = checked);
}

function triggerStockAnalystDownload() {
    const checkedBoxes = document.querySelectorAll('input[name="stock-analyst-chk"]:checked');
    const selectedAnalysts = Array.from(checkedBoxes).map(cb => cb.value);
    
    if (selectedAnalysts.length === 0) {
        alert("Debe seleccionar al menos un analista para descargar.");
        return;
    }
    
    // Filtrar expedientes del stock que corresponden a los analistas elegidos
    const filtered = currentStockData.expedientes.filter(e => {
        const name = e.analista || "SIN ASIGNAR";
        return selectedAnalysts.includes(name);
    });
    
    if (filtered.length === 0) {
        alert("No hay expedientes en el stock para los analistas seleccionados.");
        return;
    }
    
    // Formatear datos legibles para el Excel consolidado
    const excelData = filtered.map(e => ({
        "EXPEDIENTE": e.expediente,
        "ID EXPEDIENTE": e.id_expediente,
        "TRATA": e.trata || currentStockData.trataCode,
        "TRAMITE (DESCRIPCION)": e.descripcion_trata || "S/D",
        "DETALLE (MOTIVO)": e.descripcion || "S/D",
        "ESTADO ACTUAL SADE": e.estado_expediente || "S/D",
        "FECHA CARATULACION": e.caratula ? e.caratula.substring(0, 10) : "S/D",
        "FECHA INGRESO A GERENCIA": e.fecha_ing ? e.fecha_ing.substring(0, 10) : "S/D",
        "FECHA ULTIMO PASE": e.fecha_ultimo_pase ? e.fecha_ultimo_pase.substring(0, 10) : "S/D",
        "DIAS EN PODER ACTUAL": e.dias,
        "DIAS ACUMULADOS EN GERENCIA": e.dias_en_gerencia || 0,
        "ANALISTA ASIGNADO": e.analista || "SIN ASIGNAR"
    }));
    
    const filename = `Stock_${currentStockData.trataCode}_Analistas`;
    downloadExcel(filename, excelData);
    closeModal('stock-analyst-download-modal');
}

// --- FUNCIONES DESCARGA POR INTERVENCIONES ---
function openIntervencionesDownloadModal() {
    if (!currentIntervencionesData || currentIntervencionesData.length === 0) {
        alert("No hay datos de intervenciones disponibles para descargar.");
        return;
    }
    
    const listContainer = document.getElementById('stock-intervenciones-list');
    listContainer.innerHTML = '';
    
    currentIntervencionesData.forEach(item => {
        const itemHtml = `
            <label class="download-chk-card">
                <input type="checkbox" name="stock-intervencion-chk" value="${item.trata}" checked>
                <span><strong>${item.trata}</strong> - ${item.detalle}</span>
            </label>
        `;
        listContainer.insertAdjacentHTML('beforeend', itemHtml);
    });
    
    const modal = document.getElementById('stock-intervenciones-download-modal');
    modal.style.display = 'flex';
    gsap.fromTo(modal.querySelector('.modal-content'), 
        { scale: 0.9, opacity: 0, y: 30 }, 
        { scale: 1, opacity: 1, y: 0, duration: 0.35, ease: "back.out(1.5)" }
    );
}

function toggleAllIntervenciones(checked) {
    const checkboxes = document.querySelectorAll('input[name="stock-intervencion-chk"]');
    checkboxes.forEach(cb => cb.checked = checked);
}

function triggerIntervencionesDownload() {
    const checkedBoxes = document.querySelectorAll('input[name="stock-intervencion-chk"]:checked');
    const selectedTratas = Array.from(checkedBoxes).map(cb => cb.value);
    
    if (selectedTratas.length === 0) {
        alert("Debe seleccionar al menos una trata para descargar.");
        return;
    }
    
    // Filtrar expedientes individuales correspondientes a las tratas seleccionadas
    if (!currentStockData || !currentStockData.expedientes || currentStockData.expedientes.length === 0) {
        alert("No hay datos de expedientes individuales disponibles para descargar.");
        return;
    }
    
    const filtered = currentStockData.expedientes.filter(e => selectedTratas.includes(e.trata));
    
    if (filtered.length === 0) {
        alert("No hay expedientes individuales en el stock para las tratas seleccionadas.");
        return;
    }
    
    // Formatear columnas profesionales de forma legible para el Excel consolidado con el máximo detalle
    const excelData = filtered.map(e => ({
        "EXPEDIENTE": e.expediente,
        "ID EXPEDIENTE": e.id_expediente,
        "TRATA": e.trata || "S/D",
        "TRAMITE (DESCRIPCION)": e.descripcion_trata || "S/D",
        "DETALLE (MOTIVO)": e.descripcion || "S/D",
        "ESTADO ACTUAL SADE": e.estado_expediente || "S/D",
        "FECHA CARATULACION": e.caratula ? e.caratula.substring(0, 10) : "S/D",
        "FECHA INGRESO A GERENCIA": e.fecha_ing ? e.fecha_ing.substring(0, 10) : "S/D",
        "FECHA ULTIMO PASE": e.fecha_ultimo_pase ? e.fecha_ultimo_pase.substring(0, 10) : "S/D",
        "DIAS EN PODER ACTUAL": e.dias,
        "DIAS ACUMULADOS EN GERENCIA": e.dias_en_gerencia || 0,
        "ANALISTA ASIGNADO": e.analista || "SIN ASIGNAR"
    }));
    
    const cleanGerencia = (currentGerencia || "Intervenciones").toUpperCase();
    const filename = `Stock_Intervenciones_Detalle_${cleanGerencia}`;
    downloadExcel(filename, excelData);
    closeModal('stock-intervenciones-download-modal');
}

function openHelpModal(trataCode, gerencia, trataName, acronimosFromData) {
    const modal = document.getElementById('help-modal');
    const body = document.getElementById('help-modal-body');
    let content = '';

    const cleanGerencia = (gerencia || '').toLowerCase() === 'regularizacion' ? 'conforme' : (gerencia || '').toLowerCase();
    
    // Si tenemos configuración dinámica para esta trata específica cargada de la DB
    const dynConfig = currentGerenciaConfig && currentGerenciaConfig[trataCode];
    
    let buzonesArray = [];
    let analystsArray = [];
    let acronimosArray = [];
    
    if (dynConfig) {
        buzonesArray = dynConfig.buzones_ingreso || [];
        analystsArray = dynConfig.analistas_oficiales || [];
        acronimosArray = dynConfig.acronimos_egreso || [];
        // Si es INTERVENCIONES, podemos usar buzones_ingreso_intervenciones si está configurado en DB
        if (trataCode === 'INTERVENCIONES' && dynConfig.buzones_ingreso_intervenciones && dynConfig.buzones_ingreso_intervenciones.length > 0) {
            buzonesArray = dynConfig.buzones_ingreso_intervenciones;
        }
    } else {
        // Fallback a los datos hardcodeados históricos por gerencia
        const buzonesRaw = BUZZERS_DOCS[cleanGerencia] || '';
        buzonesArray = buzonesRaw 
            ? buzonesRaw.split(/, | o /).map(b => b.trim()).filter(b => b.length > 0)
            : [];
        analystsArray = ANALYSTS_DOCS[cleanGerencia] || [];
        acronimosArray = acronimosFromData 
            ? acronimosFromData.replace(/'/g, '').split(',').map(a => a.trim()).filter(a => a.length > 0)
            : [];
    }

    const buzonesHtml = buzonesArray.length > 0
        ? buzonesArray.map(b => `<span>${b}</span>`).join('')
        : '<span>No especificados para esta gerencia</span>';

    const analystsHtml = analystsArray.length > 0
        ? analystsArray.map(a => `<span>${a}</span>`).join('')
        : '<span>No hay analistas configurados</span>';

    if (trataCode === 'INTERVENCIONES') {
        content = `
            <div class="help-card">
                <div class="help-card-body">
                    <h4>Metodología de Ingreso</h4>
                    <p>Primer registro de recepción en la Gerencia (Trata Externa).</p>
                    <div class="help-list-box">
                        <div class="tag-grid">
                            ${buzonesHtml}
                        </div>
                    </div>
                </div>
            </div>
            <div class="help-card">
                <div class="help-card-body">
                    <h4>Lógica de Egreso (Pase Externo)</h4>
                    <p>Finalización por movimiento físico o pase fuera de la estructura de la Gerencia.</p>
                </div>
            </div>`;
    } else {
        // Egresos por acrónimo (Acto Administrativo)
        const acroHtml = acronimosArray.length > 0 
            ? acronimosArray.map(a => `<span class="acro-badge">${a}</span>`).join('')
            : '<span class="acro-badge" style="background: #e2e8f0; color: #64748b; font-weight: normal; padding: 6px 12px;">No requiere acrónimos (Egreso por pase físico u otra resolución)</span>';

        content = `
            <div class="help-card">
                <div class="help-card-body">
                    <h4>Puntos de Ingreso Oficiales</h4>
                    <p>Se marca el inicio del ciclo al tocar cualquiera de estos buzones:</p>
                    <div class="tag-grid">
                        ${buzonesHtml}
                    </div>
                </div>
            </div>
            <div class="help-card">
                <div class="help-card-body">
                    <h4>Egresos por Acto Administrativo</h4>
                    <p>Resolución mediante vinculación de documentos GEDO autorizados:</p>
                    <div class="acro-flex" style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px;">
                        ${acroHtml}
                    </div>
                </div>
            </div>
            <div class="help-card">
                <div class="help-card-body">
                    <h4>Nómina de Analistas Monitoreados</h4>
                    <p>El Stock consolidado incluye los expedientes en las bandejas de:</p>
                    <div class="analyst-grid-scroll">
                        ${analystsHtml}
                    </div>
                </div>
            </div>`;
    }

    body.innerHTML = `
        <div class="help-modal-header" style="padding: 25px 25px 15px 25px;">
            <div class="help-modal-title-box">
                <h2>${trataName}</h2>
                <span class="help-modal-code">Código: ${trataCode}</span>
            </div>
            <div class="help-modal-gerencia">${cleanGerencia.toUpperCase()}</div>
        </div>
        <div class="help-content-scroll" style="flex: 1; overflow-y: auto; padding: 0 25px 30px 25px;">
            ${content}
        </div>
    `;
    modal.style.display = 'flex';
}

function downloadExcel(filename, data) {
    if (!data || data.length === 0) return;
    
    // Obtener cabeceras dinámicamente de las llaves del primer objeto
    const headers = Object.keys(data[0]);
    
    let html = `
        <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
        <head>
            <meta charset="utf-8">
            <!--[if gte mso 9]>
            <xml>
                <x:ExcelWorkbook>
                    <x:ExcelWorksheets>
                        <x:ExcelWorksheet>
                            <x:Name>Reporte SGDU</x:Name>
                            <x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions>
                        </x:ExcelWorksheet>
                    </x:ExcelWorksheets>
                </x:ExcelWorkbook>
            </xml>
            <![endif]-->
            <style>
                table { border-collapse: collapse; }
                th { background-color: #0076bb; color: white; font-weight: bold; border: 1px solid #ccc; }
                td { border: 1px solid #ccc; }
            </style>
        </head>
        <body>
            <table>
                <thead>
                    <tr>${headers.map(h => `<th>${h.toUpperCase()}</th>`).join('')}</tr>
                </thead>
                <tbody>
                    ${data.map(row => `
                        <tr>
                            ${headers.map(h => `<td>${row[h] !== null ? row[h] : ''}</td>`).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </body>
        </html>`;

    const blob = new Blob([html], { type: 'application/vnd.ms-excel' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `${filename}.xls`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

async function downloadCellDetail(gerencia, trata, metrica, periodo) {
    const metricaLabelMap = {
        'ING': 'Ingresos',
        'EGR_EF': 'Egresos_Efectivos',
        'EGR_NE': 'Egresos_No_Efectivos',
        'EGR_TOT': 'Egresos_Totales',
        'STOCK_PROPIO': 'Stock_Propio',
        'STOCK_SUBS': 'Subsanacion_Abierta',
        'STOCK_TOTAL': 'Stock_Total'
    };
    const label = metricaLabelMap[metrica] || metrica;
    const filename = `Detalle_${gerencia.toUpperCase()}_${trata}_${label}_${periodo}`;
    
    // Cambiar temporalmente el botón a estado cargando
    const btn = event.currentTarget;
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="loader" style="width: 10px; height: 10px; border-width: 1.5px; border-color: var(--primary) transparent transparent transparent; display: inline-block;"></span>`;

    try {
        const response = await def_fetch(`${API_BASE}/reporte/${gerencia}/tramite/${trata}/detalle_periodo?periodo=${periodo}&metrica=${metrica}`);
        if (!response || !response.ok) {
            alert("No se pudo obtener el detalle de los expedientes.");
            return;
        }
        const data = await response.json();
        if (!data || data.length === 0) {
            alert("No hay expedientes registrados para este período y métrica.");
            return;
        }
        // Eliminar columna de estado para la descarga de detalle (si existe)
        const cleaned = data.map(row => {
            const copy = Object.assign({}, row);
            delete copy.ESTADO;
            delete copy.estado;
            delete copy['ESTADO ACTUAL SADE'];
            return copy;
        });
        downloadExcel(filename, cleaned);
    } catch (error) {
        console.error("Error al descargar detalle:", error);
        alert("Error al procesar la descarga.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}

window.onclick = function(e) { if (e.target.classList.contains('modal')) e.target.style.display = 'none'; }

// --- FUNCIONES ADMIN ---
async function loadUsers() {
    const container = document.getElementById('users-table-container');
    if (!container) return;

    container.innerHTML = '<div style="padding: 2rem; text-align: center;"><span class="loader"></span><p style="margin-top: 1rem; color: #64748b;">Sincronizando registro de usuarios...</p></div>';
    
    try {
        const resp = await def_fetch(`${API_BASE}/admin/users`);
        if (!resp || !resp.ok) return;
        
        const users = await resp.json();
        
        if (users.length === 0) {
            container.innerHTML = '<p style="padding: 2rem; text-align: center; color: #64748b;">No hay usuarios registrados.</p>';
            return;
        }

        let html = '<div class="users-list">';
        
        users.forEach(u => {
            const isMe = u.username === currentUser.username;
            const roleLabel = (u.role || "").toUpperCase();
            const roleClass = (u.role || "").toLowerCase() === 'administrador' ? 'role-admin' : 'role-user';

            html += `
                <div class="user-row">
                    <div class="user-info-main">
                        <div class="user-avatar ${roleClass}">
                            ${(u.full_name || u.username).substring(0, 1).toUpperCase()}
                        </div>
                        <div class="user-details">
                            <span class="user-name-full">
                                ${u.full_name || 'Sin nombre'} 
                                ${isMe ? '<span class="current-user-tag">TÚ</span>' : ''}
                            </span>
                            <span class="user-meta-sub">
                                <strong>@${u.username}</strong> • ${u.sector || 'S/D'} • 
                                <span class="badge-role ${roleClass}">${roleLabel}</span>
                            </span>
                        </div>
                    </div>
                    <div class="user-actions">
                        <button onclick="openEditUser('${u.username}', '${u.full_name}', '${u.role}')" class="btn-edit-user">Editar</button>
                        <button onclick="deleteUser('${u.username}')" class="btn-delete" ${isMe ? 'disabled' : ''}>
                            Eliminar
                        </button>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html + '</div>';
    } catch (error) {
        container.innerHTML = '<p style="padding: 2rem; color: #ef4444;">Error al cargar usuarios. Por favor, reintenta.</p>';
    }
}

async function deleteUser(username) {
    if (!confirm(`¿Estás seguro de eliminar al usuario ${username}?`)) return;
    
    try {
        const resp = await def_fetch(`${API_BASE}/admin/users/${username}`, {
            method: 'DELETE'
        });
        if (resp && resp.ok) {
            loadUsers();
        } else {
            const err = await resp.json();
            alert('Error: ' + err.detail);
        }
    } catch (error) {
        alert('Error al eliminar usuario');
    }
}

function openEditUser(username, fullname, role) {
    document.getElementById('edit-username-hidden').value = username;
    document.getElementById('edit-fullname').value = fullname !== 'null' ? fullname : '';
    document.getElementById('edit-role').value = role;
    document.getElementById('edit-password').value = '';
    document.getElementById('edit-user-modal').style.display = 'flex';
}

// --- METAS & PROYECCIONES ---
async function loadMetasData() {
    const gerencia = currentGerencia;
    if (!gerencia) return;
    
    const cards = document.querySelectorAll('.meta-card-value');
    
    // Reset cards to loading
    cards.forEach(c => c.innerText = "...");

    try {
        const trata = currentTrataCode;
        console.log("Cargando metas para:", gerencia, "Trata:", trata);
        
        let url = `${API_BASE}/reporte/${gerencia}/metas`;
        if (trata) url += `?trata=${trata}`;

        const response = await def_fetch(url);
        if (!response.ok) {
            const errBody = await response.json().catch(() => ({}));
            throw new Error(`Error ${response.status}: ${errBody.detail || 'Fallo en la API'}`);
        }
        const data = await response.json();
        console.log("Datos de metas recibidos:", data);

        if (!data || !data.metas || !data.history || !data.projection_target) {
            console.warn("No se recibieron datos completos de metas para", gerencia);
            return;
        }

        // 1. Update Cards
        const updateVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.innerText = val !== undefined ? val : '--';
        };

        const history = data.history || [];
        if (history.length > 0) {
            const avgIng = data.metas.avg_ing;
            const avgEgr = data.metas.avg_egr_actual;
            const lastMonth = history[history.length - 1];
            const lastIng = lastMonth.ingresos || 0;
            const lastEgr = lastMonth.egresos_totales || 0;

            const diffIng = lastIng - avgIng;
            const diffEgr = lastEgr - avgEgr;

            updateVal('meta-ing-prom-val', avgIng);
            updateVal('meta-egr-prom-val', avgEgr);
            updateVal('meta-ing-last-val', lastIng);
            updateVal('meta-egr-last-val', lastEgr);
            
            const ingDiffEl = document.getElementById('meta-ing-last-diff');
            if (ingDiffEl) {
                ingDiffEl.innerHTML = `${diffIng >= 0 ? '▲ +' : '▼ '}${diffIng} vs promedio`;
                ingDiffEl.style.color = diffIng > 0 ? '#ef4444' : '#10b981';
            }
            
            const egrDiffEl = document.getElementById('meta-egr-last-diff');
            if (egrDiffEl) {
                egrDiffEl.innerHTML = `${diffEgr >= 0 ? '▲ +' : '▼ '}${diffEgr} vs promedio`;
                egrDiffEl.style.color = diffEgr >= 0 ? '#10b981' : '#ef4444';
            }

            // --- Monitor de Avance Mensual (Real-time tracking of current month) ---
            try {
                const now = new Date();
                const currentDay = now.getDate();
                const totalDays = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
                const timeProgressPct = Math.round((currentDay / totalDays) * 100);
                
                // Actual egresos of the current month
                const actualEgr = lastEgr;
                const targetEgr = data.metas.meta_total_recomendada || avgEgr;
                const egrProgressPct = targetEgr > 0 ? Math.round((actualEgr / targetEgr) * 100) : 0;
                
                let perfClass = 'perf-mid';
                if (egrProgressPct >= timeProgressPct) {
                    perfClass = 'perf-high';
                } else if (egrProgressPct < timeProgressPct * 0.6) {
                    perfClass = 'perf-low';
                }
                
                // 1. Actualizar Relleno de Barra (Egresos)
                const egrBar = document.getElementById('meta-egr-progress-bar');
                if (egrBar) {
                    egrBar.style.width = `${Math.min(100, egrProgressPct)}%`;
                    egrBar.className = `meta-egr-bar-fill ${perfClass}`;
                }
                const egrLegendVal = document.getElementById('meta-egr-legend-val');
                if (egrLegendVal) {
                    egrLegendVal.innerText = `${egrProgressPct}% (${actualEgr} / ${targetEgr} exp)`;
                }
                
                // 2. Actualizar Aguja Vertical (Tiempo del Mes)
                const timeNeedle = document.getElementById('meta-time-needle');
                if (timeNeedle) {
                    timeNeedle.style.left = `${Math.min(100, timeProgressPct)}%`;
                }
                const timeLegendVal = document.getElementById('meta-time-legend-val');
                if (timeLegendVal) {
                    timeLegendVal.innerText = `${timeProgressPct}% (${currentDay} / ${totalDays} días)`;
                }
            } catch (progressErr) {
                console.error("Error actualizando Monitor de Avance:", progressErr);
            }

            // Bottom cards (Noviembre 2026)
            const maint = data.metas.meta_mantenimiento;
            const clean = data.metas.meta_limpieza_objetivo;
            const totalMeta = data.metas.meta_total_recomendada;
            const duracion = data.metas.duracion_resolucion;
            
            updateVal('meta-obj-ing-prom-val', avgIng);
            updateVal('meta-obj-duracion-val', duracion !== undefined ? `${duracion} días` : '--');
            updateVal('meta-obj-tot-val', totalMeta);

            const diffTotEgr = totalMeta - avgEgr;
            const totDiffEl = document.getElementById('meta-obj-tot-diff');
            if (totDiffEl) {
                totDiffEl.innerHTML = `Se requiere ${diffTotEgr >= 0 ? '▲ +' : '▼ '}${diffTotEgr} vs egreso promedio actual`;
                totDiffEl.style.color = diffTotEgr >= 0 ? '#f59e0b' : '#10b981';
            }
        }

        // 2. Render Chart
        renderMetasChart(data);
    } catch (err) {
        console.error("Error en loadMetasData:", err);
    }
}

function renderMetasChart(data) {
    const canvas = document.getElementById('metasProjectionChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (metasChart) metasChart.destroy();

    // Filtrar el histórico para el gráfico excluyendo el mes incompleto en curso
    const currentMonthStr = new Date().toISOString().substring(0, 7); // "YYYY-MM"
    const chartHistory = data.history.filter(d => d.mes_label < currentMonthStr);
    const historyDataForChart = chartHistory.length > 0 ? chartHistory : data.history;

    const labels = [...historyDataForChart.map(d => d.mes_label), ...data.projection_target.map(d => d.mes_label)];
    const historyCount = historyDataForChart.length;

    metasChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Ingresos / Ingresos Esperados',
                    data: [...historyDataForChart.map(d => d.ingresos), ...data.projection_target.map(d => d.ingresos)],
                    borderColor: '#38bdf8',
                    backgroundColor: (context) => {
                        const chart = context.chart;
                        const {ctx: chartCtx, chartArea} = chart;
                        if (!chartArea) return 'rgba(56, 189, 248, 0.1)';
                        const gradient = chartCtx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                        gradient.addColorStop(0, 'rgba(56, 189, 248, 0.18)');
                        gradient.addColorStop(1, 'rgba(56, 189, 248, 0.0)');
                        return gradient;
                    },
                    fill: true,
                    segment: {
                        borderDash: (ctx) => ctx.p0DataIndex >= historyCount - 1 ? [5, 5] : []
                    },
                    tension: 0.4,
                    pointRadius: (ctx) => ctx.dataIndex < historyCount ? 3 : 0
                },
                {
                    label: 'Egresos (Objetivo)',
                    data: [...historyDataForChart.map(d => d.egresos_totales), ...data.projection_target.map(d => d.egresos_totales)],
                    borderColor: '#f43f5e',
                    borderWidth: 3,
                    segment: {
                        borderDash: (ctx) => ctx.p0DataIndex >= historyCount - 1 ? [5, 5] : []
                    },
                    tension: 0.4,
                    pointRadius: (ctx) => ctx.dataIndex < historyCount ? 3 : 0
                },
                {
                    label: 'Stock Sector (Objetivo Cero)',
                    data: [...historyDataForChart.map(d => d.stock_sector), ...data.projection_target.map(d => d.stock_sector)],
                    borderColor: '#f59e0b',
                    borderWidth: 3,
                    backgroundColor: 'transparent',
                    tension: 0.4,
                    segment: {
                        borderDash: (ctx) => ctx.p0DataIndex >= historyCount - 1 ? [5, 5] : []
                    },
                    pointRadius: (ctx) => ctx.dataIndex < historyCount ? 3 : 0
                },
                {
                    label: 'Stock Corriente (<=3m)',
                    data: [...historyDataForChart.map(d => d.stock_corriente), ...data.projection_target.map(d => d.stock_corriente)],
                    borderColor: '#10b981',
                    backgroundColor: 'transparent',
                    tension: 0.4,
                    segment: {
                        borderDash: (ctx) => ctx.p0DataIndex >= historyCount - 1 ? [5, 5] : []
                    },
                    pointRadius: (ctx) => ctx.dataIndex < historyCount ? 3 : 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { family: 'Outfit', size: 11, weight: '600' }, color: '#64748b' }
                },
                y: {
                    title: { display: true, text: 'Volumen / Expedientes', font: { family: 'Outfit', weight: 'bold', size: 12 }, color: '#475569' },
                    beginAtZero: true,
                    grid: { color: 'rgba(226, 232, 240, 0.6)', drawBorder: false },
                    ticks: { font: { family: 'Outfit', size: 11 }, color: '#64748b' }
                }
            },
            plugins: {
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#ffffff',
                    bodyColor: '#f1f5f9',
                    titleFont: { family: 'Outfit', weight: 'bold', size: 13 },
                    bodyFont: { family: 'Outfit', size: 12 },
                    padding: 12,
                    cornerRadius: 8,
                    borderColor: '#e2e8f0',
                    borderWidth: 1,
                    displayColors: true,
                    boxPadding: 6
                },
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true, font: { family: 'Outfit', size: 12, weight: '600' }, color: '#475569' }
                },
                annotation: {
                    annotations: {
                        todayLine: {
                            type: 'line',
                            xMin: Math.max(0, historyCount - 1),
                            xMax: Math.max(0, historyCount - 1),
                            borderColor: '#94a3b8',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            label: {
                                display: true,
                                content: 'INICIO PROYECCIÓN',
                                position: 'start',
                                backgroundColor: '#475569',
                                color: 'white',
                                font: { family: 'Outfit', size: 10, weight: 'bold' },
                                padding: 6,
                                borderRadius: 4
                            }
                        }
                    }
                }
            }
        }
    });
}

// --- SEGUIMIENTO Y GESTIÓN DE TRATAS ---
let seguimientoTratasData = [];

async function loadSeguimientoData() {
    const container = document.getElementById('seguimiento-grid-container');
    if (!container) return;

    container.innerHTML = `
        <div class="loading-overlay" style="grid-column: 1 / -1;">
            <span class="loader"></span>
            <h2 style="margin-top: 1rem; color: var(--primary-dark);">Cargando panel de seguimiento...</h2>
            <p style="color: #64748b;">Consolidando avance físico y ritmos mensuales de todas las tratas...</p>
        </div>`;

    const gerencias = ['catastro', 'instalaciones', 'conforme', 'contable', 'etapa_proyecto', 'aviso_obra', 'morfologia', 'aph', 'usos'];
    
    try {
        // Cargar en paralelo todos los consolidados
        const promises = gerencias.map(g => 
            def_fetch(`${API_BASE}/reporte/${g}/consolidado`)
                .then(r => r && r.ok ? r.json() : [])
                .catch(() => [])
        );
        
        const results = await Promise.all(promises);
        
        seguimientoTratasData = [];
        const now = new Date();
        const currentYear = now.getFullYear();
        const currentMonth = now.getMonth() + 1; // 1-indexed
        const currentMonthStr = `${currentYear}-${currentMonth.toString().padStart(2, '0')}`;
        
        for (let idx = 0; idx < gerencias.length; idx++) {
            const g = gerencias[idx];
            const rawData = results[idx];
            if (!rawData || rawData.length === 0) continue;
            
            // Agrupar registros por trata
            const groups = {};
            rawData.forEach(row => {
                const key = row["COD TRATA"];
                if (!key) return;
                if (!groups[key]) {
                    groups[key] = {
                        trataCode: key,
                        trataName: row["DETALLE TRATA"] || key,
                        gerencia: g,
                        records: []
                    };
                }
                groups[key].records.push(row);
            });
            
            // Procesar cada trata para obtener el mes actual y medinas anteriores
            Object.values(groups).forEach(gTrata => {
                // Registro del mes actual
                const currentRecord = gTrata.records.find(r => r.anio === currentYear && r.mes === currentMonth);
                const actualEgr = currentRecord ? ((currentRecord.EGR_EF || 0) + (currentRecord.EGR_NE || 0)) : 0;
                
                // Obtener el valor de Egresos Promedio (mediana de 6 meses) del backend
                const firstRecord = gTrata.records[0];
                const targetEgr = firstRecord ? (firstRecord.meta_egr_prom || 0) : 0;
                const progressPct = targetEgr > 0 ? Math.round((actualEgr / targetEgr) * 100) : (actualEgr > 0 ? 100 : 0);
                
                // Para evitar duplicación, por ejemplo de INTERVENCIONES en varias gerencias
                // lo identificamos unívocamente combinándolo con su gerencia
                seguimientoTratasData.push({
                    trataCode: gTrata.trataCode,
                    trataName: gTrata.trataName.toString().replace(/\r?\n|\r/g, ' ').trim(),
                    gerencia: g,
                    actualEgr: actualEgr,
                    targetEgr: targetEgr,
                    progressPct: progressPct
                });
            });
        }
        
        filterAndRenderSeguimiento();
        setSeguimientoViewMode(seguimientoViewMode);
    } catch (err) {
        console.error("Error al cargar seguimiento:", err);
        container.innerHTML = `
            <div class="error-message" style="grid-column: 1 / -1;">
                <div class="error-icon">!</div>
                <h3>Error en la carga</h3>
                <p>No pudimos consolidar los datos de seguimiento. Por favor, reintenta.</p>
                <button class="btn-primary" style="margin-top:1rem;" onclick="loadSeguimientoData()">Reintentar Carga</button>
            </div>`;
    }
}

function filterAndRenderSeguimiento() {
    const searchVal = document.getElementById('seguimiento-search').value.toLowerCase().trim();
    const gerenciaFilter = document.getElementById('seguimiento-filter-gerencia').value;
    const sortVal = document.getElementById('seguimiento-sort').value;
    
    // 1. Filtrado (ocultando aquellas tratas donde el egreso esperado sea 0)
    let filtered = seguimientoTratasData.filter(t => {
        const matchesSearch = t.trataCode.toLowerCase().includes(searchVal) || t.trataName.toLowerCase().includes(searchVal);
        const matchesGerencia = gerenciaFilter === 'ALL' || t.gerencia === gerenciaFilter;
        return matchesSearch && matchesGerencia && t.targetEgr > 0;
    });
    
    // 2. Ordenamiento
    if (sortVal === 'PERF_DESC') {
        filtered.sort((a, b) => b.progressPct - a.progressPct);
    } else if (sortVal === 'PERF_ASC') {
        filtered.sort((a, b) => a.progressPct - b.progressPct);
    } else if (sortVal === 'NAME_ASC') {
        filtered.sort((a, b) => a.trataName.localeCompare(b.trataName));
    } else if (sortVal === 'CODE_ASC') {
        filtered.sort((a, b) => a.trataCode.localeCompare(b.trataCode));
    }
    
    // 2.5. Calcular contadores de cumplimiento por rangos (antes de aplicar el filtro de rango en sí para conservar los conteos generales)
    let count0_25 = 0;
    let count25_50 = 0;
    let count50_75 = 0;
    let count75Plus = 0;
    
    filtered.forEach(t => {
        if (t.progressPct < 25) {
            count0_25++;
        } else if (t.progressPct < 50) {
            count25_50++;
        } else if (t.progressPct < 75) {
            count50_75++;
        } else {
            count75Plus++;
        }
    });
    
    const el0_25 = document.getElementById('comp-count-0-25');
    const el25_50 = document.getElementById('comp-count-25-50');
    const el50_75 = document.getElementById('comp-count-50-75');
    const el75Plus = document.getElementById('comp-count-75-100');
    
    if (el0_25) el0_25.innerText = count0_25;
    if (el25_50) el25_50.innerText = count25_50;
    if (el50_75) el50_75.innerText = count50_75;
    if (el75Plus) el75Plus.innerText = count75Plus;

    // 2.7. Aplicar filtro de rango de cumplimiento (si está activo alguno)
    if (activeComplianceFilter) {
        filtered = filtered.filter(t => {
            if (activeComplianceFilter === '0-25') return t.progressPct < 25;
            if (activeComplianceFilter === '25-50') return t.progressPct >= 25 && t.progressPct < 50;
            if (activeComplianceFilter === '50-75') return t.progressPct >= 50 && t.progressPct < 75;
            if (activeComplianceFilter === '75-100') return t.progressPct >= 75;
            return true;
        });
    }

    // 2.8. Actualizar clases de enfoque activo/atenuado de las tarjetas
    const gridEl = document.querySelector('.compliance-summary-grid');
    if (gridEl) {
        if (activeComplianceFilter) {
            gridEl.classList.add('has-active');
        } else {
            gridEl.classList.remove('has-active');
        }
    }
    
    const ranges = ['0-25', '25-50', '50-75', '75-100'];
    ranges.forEach(r => {
        const el = document.getElementById(`card-comp-${r}`);
        if (el) {
            if (activeComplianceFilter === r) {
                el.classList.add('active');
            } else {
                el.classList.remove('active');
            }
        }
    });

    // 3. Renderizar
    const container = document.getElementById('seguimiento-grid-container');
    const summaryBadge = document.getElementById('seguimiento-summary-badge');
    
    if (summaryBadge) {
        summaryBadge.innerText = `${filtered.length} trámites encontrados`;
    }
    
    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="error-message" style="grid-column: 1 / -1; margin: 2rem auto; width: 100%;">
                <div class="error-icon">i</div>
                <h3>Sin trámites coincidentes</h3>
                <p>Modifica los filtros de búsqueda o gerencia para encontrar lo que buscas.</p>
            </div>`;
        return;
    }
    
    const now = new Date();
    const currentDay = now.getDate();
    const totalDays = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
    const timeProgressPct = Math.round((currentDay / totalDays) * 100);
    
    let html = '';
    filtered.forEach(t => {
        let perfClass = 'perf-mid';
        if (t.progressPct >= timeProgressPct) {
            perfClass = 'perf-high';
        } else if (t.progressPct < timeProgressPct * 0.6) {
            perfClass = 'perf-low';
        }
        
        const gerenciaDisplay = t.gerencia === 'etapa_proyecto' ? 'ETAPA PROYECTO' : (t.gerencia === 'aviso_obra' ? 'AVISO OBRA' : t.gerencia.toUpperCase());
        
        html += `
            <article class="trata-track-card" onclick="showTrataFromSeguimiento('${t.gerencia}', '${t.trataCode}', '${t.trataName.replace(/'/g, "\\'")}')" style="cursor: pointer;">
                <div class="trata-track-header">
                    <div class="trata-track-title-block">
                        <h3 class="trata-track-name">${t.trataName.toUpperCase()}</h3>
                        <span class="trata-track-code">${t.trataCode}</span>
                    </div>
                    <span class="badge-gerencia ${t.gerencia}">${gerenciaDisplay}</span>
                </div>
                
                <div class="trata-track-metrics">
                    <div class="metric-mini-box">
                        <span class="metric-mini-label">Egresados</span>
                        <span class="metric-mini-value">${t.actualEgr}</span>
                    </div>
                    <div class="metric-mini-box">
                        <span class="metric-mini-label">Esperado</span>
                        <span class="metric-mini-value">${t.targetEgr}</span>
                    </div>
                    <div class="metric-mini-box">
                        <span class="metric-mini-label">Avance</span>
                        <span class="metric-mini-value ${perfClass}">${t.progressPct}%</span>
                    </div>
                </div>
                
                <div class="trata-track-progress-block">
                    <div class="progress-track-bar">
                        <div class="progress-track-fill ${perfClass}" style="width: ${Math.min(100, t.progressPct)}%;"></div>
                        <div class="progress-track-needle" style="left: ${Math.min(100, timeProgressPct)}%;"></div>
                    </div>
                    <div class="progress-track-labels">
                        <span>Avance: ${t.progressPct}%</span>
                        <span>Mes: ${timeProgressPct}%</span>
                    </div>
                </div>
            </article>
        `;
    });
    
    container.innerHTML = html;
    gsap.from(".trata-track-card", { opacity: 0, scale: 0.95, duration: 0.4, stagger: 0.03, ease: "power2.out" });
}

function showTrataFromSeguimiento(gerencia, trataCode, trataName) {
    window.open(`#/${gerencia}/${trataCode}`, '_blank');
}

function setSeguimientoViewMode(mode) {
    seguimientoViewMode = mode;
    localStorage.setItem('sgdu_seguimiento_view_mode', mode);

    const container = document.getElementById('seguimiento-grid-container');
    if (container) {
        if (mode === 'grid') {
            container.classList.add('view-grid');
        } else {
            container.classList.remove('view-grid');
        }
    }

    const btnList = document.getElementById('btn-view-list');
    const btnGrid = document.getElementById('btn-view-grid');

    if (btnList && btnGrid) {
        if (mode === 'grid') {
            btnGrid.classList.add('active');
            btnGrid.style.background = 'white';
            btnGrid.style.color = 'var(--primary-dark)';
            btnGrid.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';

            btnList.classList.remove('active');
            btnList.style.background = 'transparent';
            btnList.style.color = '#64748b';
            btnList.style.boxShadow = 'none';
        } else {
            btnList.classList.add('active');
            btnList.style.background = 'white';
            btnList.style.color = 'var(--primary-dark)';
            btnList.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';

            btnGrid.classList.remove('active');
            btnGrid.style.background = 'transparent';
            btnGrid.style.color = '#64748b';
            btnGrid.style.boxShadow = 'none';
        }
    }
}

function toggleComplianceFilter(range) {
    if (activeComplianceFilter === range) {
        activeComplianceFilter = null;
    } else {
        activeComplianceFilter = range;
    }
    filterAndRenderSeguimiento();
}

// --- SLA TIEMPOS DE TRAMITACIÓN ---
let slaReporteData = [];
let activeSlaRangeFilter = null;

async function loadSLAReporte() {
    const container = document.getElementById('sla-grid-container');
    if (!container) return;

    container.innerHTML = `
        <div class="loading-overlay" style="grid-column: 1 / -1;">
            <span class="loader"></span>
            <h2 style="margin-top: 1rem; color: var(--primary-dark);">Analizando tiempos de resolución (SLA)...</h2>
            <p style="color: #64748b;">Consolidando carátulas y egresos efectivos de todas las gerencias...</p>
        </div>`;

    const gerenciaFilter = document.getElementById('sla-filter-gerencia').value;

    try {
        const response = await def_fetch(`${API_BASE}/reporte/sla?gerencia=${gerenciaFilter}`);
        if (!response || !response.ok) throw new Error("Fallo al conectar con la API de SLA");
        
        slaReporteData = await response.json();
        filterAndRenderSLA();
    } catch (err) {
        console.error("Error al cargar SLA:", err);
        container.innerHTML = `
            <div class="error-message" style="grid-column: 1 / -1;">
                <div class="error-icon">⚠️</div>
                <h3>Error en la carga</h3>
                <p>No pudimos consolidar los datos de SLA. Por favor, reintenta.</p>
                <button class="btn-primary" style="margin-top:1rem;" onclick="loadSLAReporte()">Reintentar Carga</button>
            </div>`;
    }
}

function filterAndRenderSLA() {
    const searchVal = document.getElementById('sla-search').value.toLowerCase().trim();
    const sortVal = document.getElementById('sla-sort').value;
    
    // 1. Filtrar por búsqueda
    let filtered = slaReporteData.filter(t => {
        const name = (t["DETALLE TRATA"] || '').toLowerCase();
        const code = (t["COD TRATA"] || '').toLowerCase();
        return code.includes(searchVal) || name.includes(searchVal);
    });
    
    // 2. Ordenar
    if (sortVal === 'AVG_DESC') {
        filtered.sort((a, b) => {
            const valA = a.duracion_total_mediana !== undefined ? a.duracion_total_mediana : (a.promedio_dias || 0);
            const valB = b.duracion_total_mediana !== undefined ? b.duracion_total_mediana : (b.promedio_dias || 0);
            return valB - valA;
        });
    } else if (sortVal === 'AVG_ASC') {
        filtered.sort((a, b) => {
            const valA = a.duracion_total_mediana !== undefined ? a.duracion_total_mediana : (a.promedio_dias || 0);
            const valB = b.duracion_total_mediana !== undefined ? b.duracion_total_mediana : (b.promedio_dias || 0);
            return valA - valB;
        });
    } else if (sortVal === 'RESOLVED_DESC') {
        filtered.sort((a, b) => (b.total_resueltos || 0) - (a.total_resueltos || 0));
    } else if (sortVal === 'NAME_ASC') {
        filtered.sort((a, b) => (a["DETALLE TRATA"] || '').localeCompare(b["DETALLE TRATA"] || ''));
    }
    
    // 3. Contar rangos de SLA basados en duracion_total_mediana
    let countFast = 0;
    let countNormal = 0;
    let countSlow = 0;
    let countDelayed = 0;
    
    filtered.forEach(t => {
        const val = t.duracion_total_mediana !== undefined ? t.duracion_total_mediana : (t.promedio_dias || 0);
        if (val <= 15) countFast++;
        else if (val <= 45) countNormal++;
        else if (val <= 90) countSlow++;
        else countDelayed++;
    });
    
    const elFast = document.getElementById('sla-count-fast');
    const elNormal = document.getElementById('sla-count-normal');
    const elSlow = document.getElementById('sla-count-slow');
    const elDelayed = document.getElementById('sla-count-delayed');
    
    if (elFast) elFast.innerText = countFast;
    if (elNormal) elNormal.innerText = countNormal;
    if (elSlow) elSlow.innerText = countSlow;
    if (elDelayed) elDelayed.innerText = countDelayed;
    
    // 4. Aplicar filtro por rango de SLA si está activo
    if (activeSlaRangeFilter) {
        filtered = filtered.filter(t => {
            const val = t.duracion_total_mediana !== undefined ? t.duracion_total_mediana : (t.promedio_dias || 0);
            if (activeSlaRangeFilter === 'fast') return val <= 15;
            if (activeSlaRangeFilter === 'normal') return val > 15 && val <= 45;
            if (activeSlaRangeFilter === 'slow') return val > 45 && val <= 90;
            if (activeSlaRangeFilter === 'delayed') return val > 90;
            return true;
        });
    }
    
    // 5. Actualizar la visualización de los botones de rango (active / has-active)
    const gridEl = document.querySelector('#sla .compliance-summary-grid');
    if (gridEl) {
        if (activeSlaRangeFilter) {
            gridEl.classList.add('has-active');
        } else {
            gridEl.classList.remove('has-active');
        }
    }
    
    const ranges = ['fast', 'normal', 'slow', 'delayed'];
    ranges.forEach(r => {
        const el = document.getElementById(`card-sla-${r}`);
        if (el) {
            if (activeSlaRangeFilter === r) {
                el.classList.add('active');
            } else {
                el.classList.remove('active');
            }
        }
    });
    
    // 6. Renderizar las tarjetas
    const container = document.getElementById('sla-grid-container');
    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="error-message" style="grid-column: 1 / -1; margin: 2rem auto; width: 100%;">
                <div class="error-icon">i</div>
                <h3>Sin trámites coincidentes</h3>
                <p>Modifica los filtros de búsqueda o de área para encontrar lo que buscas.</p>
            </div>`;
        return;
    }
    
    let html = '';
    filtered.forEach(t => {
        const totalMed = (t.duracion_total_mediana !== undefined && t.duracion_total_mediana !== null) ? t.duracion_total_mediana : 0;
        const netaMed = (t.duracion_neta_mediana !== undefined && t.duracion_neta_mediana !== null) ? t.duracion_neta_mediana : 0;
        const subsMed = (t.duracion_subsanaciones_mediana !== undefined && t.duracion_subsanaciones_mediana !== null) ? t.duracion_subsanaciones_mediana : 0;
        
        const totalMedStr = `${totalMed}d`;
        const netaMedStr = `${netaMed}d`;
        const subsMedStr = subsMed > 0 ? `${subsMed}d` : 'Sin subs.';
        
        let perfClass = 'perf-mid';
        if (totalMed <= 15) {
            perfClass = 'perf-high';
        } else if (totalMed > 45) {
            perfClass = 'perf-low';
        }
        
        const gerenciaDisplay = t.gerencia === 'etapa_proyecto' ? 'ETAPA PROYECTO' : (t.gerencia === 'aviso_obra' ? 'AVISO OBRA' : t.gerencia.toUpperCase());
        
        html += `
            <article class="trata-track-card" onclick="showTrataFromSla('${t.gerencia}', '${t["COD TRATA"]}', '${(t["DETALLE TRATA"] || t["COD TRATA"]).replace(/'/g, "\\'")}')" style="cursor: pointer; padding: 1.5rem;">
                <div class="trata-track-header" style="margin-bottom: 1.2rem; display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
                    <div class="trata-track-title-block" style="flex: 1;">
                        <h3 class="trata-track-name" style="font-size: 1.05rem; font-weight: 700; color: var(--primary-dark); line-height: 1.2;">${(t["DETALLE TRATA"] || t["COD TRATA"]).toUpperCase()}</h3>
                        <div style="margin-top: 6px; display: flex; align-items: center; gap: 6px;">
                            <span class="trata-track-code" style="font-size: 0.75rem; color: #64748b; font-weight: 600; background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">${t["COD TRATA"]}</span>
                            <span style="font-size: 0.75rem; color: #0284c7; font-weight: 600; background: #f0f9ff; padding: 2px 6px; border-radius: 4px;">${t.total_resueltos} resueltos</span>
                        </div>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 8px;">
                        <span class="badge-gerencia ${t.gerencia}">${gerenciaDisplay}</span>
                        <button class="btn-cell-download" onclick="exportSlaCardDetail(event, '${t.gerencia}', '${t["COD TRATA"]}')" title="Descargar validación Excel" style="background: rgba(0, 118, 187, 0.05); border: none; padding: 4px 8px; border-radius: 6px; display: inline-flex; align-items: center; justify-content: center; color: var(--primary); cursor: pointer; transition: all 0.2s; font-size: 0.7rem; font-weight: 700; gap: 4px;">
                            Excel
                        </button>
                    </div>
                </div>
                
                <div class="trata-track-metrics" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; border-top: 1px solid #f1f5f9; padding-top: 1rem;">
                    <div class="metric-mini-box" style="display: flex; flex-direction: column; gap: 4px;">
                        <span class="metric-mini-label" style="font-size: 0.65rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px;">Duración Trámite</span>
                        <span class="metric-mini-value" style="font-size: 1.25rem; font-weight: 800; color: #334155;">${totalMedStr}</span>
                    </div>
                    <div class="metric-mini-box" style="display: flex; flex-direction: column; gap: 4px;">
                        <span class="metric-mini-label" style="font-size: 0.65rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px;">En Gerencia</span>
                        <span class="metric-mini-value ${perfClass}" style="font-size: 1.25rem; font-weight: 800;">${netaMedStr}</span>
                    </div>
                    <div class="metric-mini-box" style="display: flex; flex-direction: column; gap: 4px;">
                        <span class="metric-mini-label" style="font-size: 0.65rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px;">En Subsanación</span>
                        <span class="metric-mini-value" style="font-size: 1.25rem; font-weight: 800; color: #475569;">${subsMedStr}</span>
                    </div>
                </div>
            </article>
        `;
    });
    
    container.innerHTML = html;
    gsap.from("#sla-grid-container .trata-track-card", { opacity: 0, scale: 0.95, duration: 0.4, stagger: 0.03, ease: "power2.out" });
}

function showTrataFromSla(gerencia, trataCode, trataName) {
    window.open(`#/${gerencia}/${trataCode}`, '_blank');
}

function toggleSlaRangeFilter(range) {
    if (activeSlaRangeFilter === range) {
        activeSlaRangeFilter = null;
    } else {
        activeSlaRangeFilter = range;
    }
    filterAndRenderSLA();
}

async function exportSlaCardDetail(event, gerencia, trataCode) {
    event.stopPropagation(); // Evita navegar a la vista detalle de la trata
    
    const btn = event.currentTarget;
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="loader" style="width: 10px; height: 10px; border-width: 1.5px; border-color: var(--primary) transparent transparent transparent; display: inline-block;"></span>`;
    
    try {
        const response = await def_fetch(`${API_BASE}/reporte/sla/expedientes?gerencia=${gerencia}&trata=${trataCode}`);
        if (!response || !response.ok) {
            alert("No se pudo obtener el detalle de los expedientes.");
            return;
        }
        const data = await response.json();
        if (!data || data.length === 0) {
            alert("No hay expedientes resueltos registrados en el último año para este trámite.");
            return;
        }
        
        // Formatear datos para exportación clara
        const cleanData = data.map(r => ({
            'Gerencia': r.gerencia.toUpperCase(),
            'Expediente': r.expediente,
            'Trámite (Trata)': r.trata,
            'Descripción Trámite': r.descripcion_trata,
            'Fecha Carátula': r.fecha_caratula,
            'Fecha Egreso': r.fecha_egreso,
            'Días Brutos': r.dias_brutos,
            'Días Subsanación (Descontados)': r.dias_subsanacion,
            'Días Netos (SLA)': r.dias_netos_sla
        }));
        
        const filename = `Val_SLA_${gerencia.toUpperCase()}_${trataCode}`;
        downloadExcel(filename, cleanData);
    } catch (err) {
        console.error("Error al exportar SLA:", err);
        alert("Error al procesar la exportación.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}


// --- FAMILIAS DE TRÁMITES ---
const FAMILIAS_CONFIG = {
    "Catastro": ["MDUG0134N", "MDUG0146A", "MDUG0131B", "MDUG0115B", "MDUG1501H", "MDUG0135A", "MDUG0131A", "MDUG0115F", "MDUG0134C", "MDUG0134E", "MDUG1501L", "MDUG0115E", "MDUG0115G", "MDUG0115C"],
    "Registros": ["MDUG3001A", "MDUG0104A", "MDUG1502A", "MDUG0142A", "MDUG4003A"],
    "Incendio": ["MDUG2101A"],
    "Conforme": ["MDUG0141A"],
    "Instalaciones": ["MDUG2901A", "MDUG2301A", "MDUG2201A", "MDUG3301A", "MDUG2601A", "MDUG2401A", "MDUG2501A", "MDUG2701A"],
    "Otros": ["MDUG0901A", "MDUG0120A", "MDUG0102B", "MDUG0107A", "MJGG1601A", "MDUG0904A", "MDUG3801A", "MJGG1701A", "MDUG1802A"],
    "Consultas de Usos": ["MDUG4001A", "MDUG4102A", "MJGG0302A", "MDUG0136B", "MJGG0303A"],
    "Permisos": ["MDUG1501J", "MDUG1501K", "MDUG3402A"],
    "Interpretaciones/Informe Urbanisitco": ["MDUG3601A", "MDUG1801A"],
    "Consultas Obligatorias": ["MDUG3701A", "MDUG3501A"]
};

const TRATA_NAMES_LOOKUP = {
    "MDUG0134N": "Constitución De Estado Parcelario",
    "MDUG3001A": "P. Obra E. Proy. / Conforme / R. Obras En Contra",
    "MDUG0146A": "Solicitud De Copia De Plano",
    "MDUG2101A": "Registro De Proyecto De Prevención Contra Incendios",
    "MDUG0141A": "Registro De Plano Conforme A Obra Civil",
    "MDUG2901A": "Registro De Proyecto De Elementos Guiados De Transporte",
    "MDUG2301A": "Registro De Proyecto De Instalación Térmica",
    "MDUG0104A": "Regularización De Obra En Contravención Ley 6478",
    "MDUG0131B": "Plano De Propiedad Horizontal Nuevo",
    "MDUG2201A": "Registro De Proyecto De Instalación Ventilación Mecánica",
    "MDUG0901A": "Inscripción Al Registro De Profesionales De DGROC",
    "MDUG4001A": "Consulta De Usos",
    "MDUG0115B": "Plano De Mensura Particular",
    "MDUG0120A": "Examen De Foguista",
    "MDUG1501J": "Permiso De Ejecución De Obra Civil",
    "MDUG3601A": "Interpretación Urbanística",
    "MDUG1501H": "Certificado Catastral",
    "MDUG0135A": "Solicitud De Consideración A La Dirección De Catastro",
    "MDUG4102A": "Solicitud De Consulta De Usos",
    "MDUG0102B": "Trámite Aviso De Obra",
    "MDUG3301A": "Registro De Proyecto De Salas De Máquinas",
    "MDUG0107A": "Fijación Línea De Frente Interno",
    "MDUG2601A": "Registro De Proyecto De Instalación Sanitaria",
    "MDUG2401A": "Registro De Proyecto De Instalación Electromecánica",
    "MDUG3701A": "Consulta Obligatoria Para Inmuebles En APH O Catal",
    "MDUG1501K": "Permiso De Demolición",
    "MDUG0131A": "Plano De Propiedad Horizontal Modificatorio",
    "MDUG3501A": "Consulta Obligatoria General",
    "MDUG2501A": "Registro De Proyecto De Instalaciones Inflamables",
    "MDUG2701A": "Registro De Proyecto De Instalación Eléctrica",
    "MDUG3402A": "Permiso Temprano De Ejecución De Obra Civil",
    "MJGG0302A": "Consulta De Uso No Conforme",
    "MDUG0115F": "Plano De Mensura De Objeto Territorial",
    "MDUG1502A": "Inicio De Obra Bajo Responsabilidad Profesional",
    "MDUG0136B": "Consulta De Emplazamiento De Estructuras Soportes De Antenas",
    "MJGG1601A": "Registro De Plano De Homologación De Equipos",
    "MJGG0303A": "Consulta De Usos Con Intervención Del Consejo",
    "MDUG0904A": "Ascenso De Categoría De Foguistas",
    "MDUG0134C": "Solicitud De Certificado De Numeración Domiciliaria",
    "MDUG0134E": "Solicitud De Certificado De Fijación De Línea",
    "MDUG3801A": "Solicitudes Especiales Para Inmuebles En APH O Cat",
    "MDUG0142A": "Modificación De Obra En Curso Bajo Responsabilidad Profesional",
    "MDUG1501L": "Certificado De Cota De Parcela Nivel Cero",
    "MDUG0115E": "Corrección Plano De Mensura",
    "MDUG1801A": "Informe Urbanístico",
    "MDUG0115G": "Determinación Del Límite En Altura En Zona Afectada Al Cinturón",
    "MDUG0115C": "Anulación Plano De Mensura",
    "MJGG1701A": "Transferencia De Titularidad De Instalación",
    "MDUG4003A": "Registro Etapa Proyecto - Model BA",
    "MDUG1802A": "Consulta No Obligatoria De Capacidad Constructiva Adicional Proyecto Emisor"
};

let familyChart = null;
let currentFamily = "";

function enterFamily(familyName) {
    currentFamily = familyName;
    
    // Ocultar selector, mostrar dashboard
    document.getElementById('family-selector-container').style.display = 'none';
    document.getElementById('family-dashboard-container').style.display = 'block';
    
    // Cambiar título del dashboard
    document.getElementById('family-dashboard-title').innerText = familyName;
    
    // Generar checkboxes para la familia
    const tratas = FAMILIAS_CONFIG[familyName] || [];
    const container = document.getElementById('family-tratas-checkboxes');
    if (container) {
        container.innerHTML = tratas.map(t => {
            const desc = TRATA_NAMES_LOOKUP[t] || "Trámite Especial";
            return `
                <label style="display: flex; align-items: center; gap: 8px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 8px 12px; border-radius: 8px; cursor: pointer; transition: background 0.2s; font-size: 0.82rem; font-weight: 600; color: #334155; user-select: none;">
                    <input type="checkbox" value="${t}" checked onchange="loadFamilyData()" style="width: 15px; height: 15px; accent-color: var(--primary);">
                    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${t} - ${desc}">
                        <strong>${t}</strong> - ${desc}
                    </span>
                </label>
            `;
        }).join('');
    }
    
    loadFamilyData();
}

async function backToFamilySelector() {
    // Mostrar selector, ocultar dashboard
    document.getElementById('family-selector-container').style.display = 'block';
    document.getElementById('family-dashboard-container').style.display = 'none';
    
    // Limpiar gráficos
    if (familyChart) {
        familyChart.destroy();
        familyChart = null;
    }

    const grid = document.getElementById('family-landing-grid');
    if (!grid) return;

    grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 3rem;">
            <span class="loader"></span>
            <p style="margin-top: 1rem; color: #64748b; font-family: 'Outfit';">Consolidando métricas de familias...</p>
        </div>
    `;

    try {
        const response = await def_fetch(`${API_BASE}/reporte/familias_overview`);
        if (!response || !response.ok) throw new Error("Error fetching families overview.");
        
        const data = await response.json();
        
        const now = new Date();
        const currentDay = now.getDate();
        const totalDays = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
        const timeProgressPct = Math.round((currentDay / totalDays) * 100);

        let html = '';
        data.forEach(f => {
            let perfClass = 'perf-mid';
            if (f.progress_pct >= timeProgressPct) {
                perfClass = 'perf-high';
            } else if (f.progress_pct < timeProgressPct * 0.6) {
                perfClass = 'perf-low';
            }

            html += `
                <article class="trata-track-card" onclick="enterFamily('${f.family_name}')" style="cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;">
                    <div class="trata-track-header" style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div class="trata-track-title-block">
                            <h3 class="trata-track-name" style="font-family: 'Outfit'; font-weight: 700; color: var(--primary-dark); font-size: 1.1rem; margin: 0;">${f.family_name.toUpperCase()}</h3>
                            <span class="trata-track-code" style="font-size: 0.72rem; color: #64748b; font-weight: 600;">${f.trata_count} TRÁMITES</span>
                        </div>
                        <span style="font-size: 0.72rem; font-weight: 800; color: ${f.variation_pct >= 0 ? '#10b981' : '#ef4444'}; display: inline-flex; align-items: center; gap: 4px; background: ${f.variation_pct >= 0 ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)'}; padding: 4px 8px; border-radius: 6px; font-family: 'Outfit';">
                            ${f.variation_pct >= 0 ? '▲ +' : '▼ '}${f.variation_pct}% vs mes anterior
                        </span>
                    </div>
                    
                    <p style="font-size: 0.8rem; color: #64748b; margin: 8px 0 16px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${f.description}">${f.description}</p>
                    
                    <div class="trata-track-metrics" style="background: #f8fafc; border-radius: 8px; padding: 8px 12px; margin-bottom: 16px; border: 1px solid #f1f5f9;">
                        <div class="metric-mini-box">
                            <span class="metric-mini-label">Egresos</span>
                            <span class="metric-mini-value" style="font-size: 0.95rem;">${f.actual_egr.toLocaleString('es-AR')} <span style="font-size: 0.72rem; font-weight: 500; color: #64748b;">exp.</span></span>
                        </div>
                        <div class="metric-mini-box">
                            <span class="metric-mini-label">Esperado</span>
                            <span class="metric-mini-value" style="font-size: 0.95rem;">${f.target_egr.toLocaleString('es-AR')} <span style="font-size: 0.72rem; font-weight: 500; color: #64748b;">exp.</span></span>
                        </div>
                        <div class="metric-mini-box">
                            <span class="metric-mini-label">Avance</span>
                            <span class="metric-mini-value ${perfClass}">${f.progress_pct}%</span>
                        </div>
                    </div>
                    
                    <div class="trata-track-progress-block">
                        <div class="progress-track-bar" style="height: 6px; background: #e2e8f0; border-radius: 3px; position: relative; margin-bottom: 8px;">
                            <div class="progress-track-fill ${perfClass}" style="width: ${Math.min(100, f.progress_pct)}%; height: 100%; border-radius: 3px;"></div>
                            <div class="progress-track-needle" style="left: ${Math.min(100, timeProgressPct)}%; height: 12px; width: 2px; background: #000; position: absolute; top: -3px; z-index: 2;"></div>
                        </div>
                        <div class="progress-track-labels" style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #64748b; font-weight: 600;">
                            <span>Avance: ${f.progress_pct}%</span>
                            <span>Mes: ${timeProgressPct}%</span>
                        </div>
                    </div>
                </article>
            `;
        });
        
        grid.innerHTML = html;
        if (window.gsap) {
            gsap.from(".trata-track-card", { opacity: 0, y: 15, duration: 0.4, stagger: 0.05, ease: "power2.out" });
        }
    } catch (err) {
        console.error("Error loading families overview:", err);
        grid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: #ef4444; font-family: 'Outfit';">
                <p>Error cargando el resumen de familias.</p>
                <button class="btn-primary" onclick="backToFamilySelector()" style="margin-top: 1rem;">Reintentar</button>
            </div>
        `;
    }
}

function selectFamilyTratas(checked) {
    const checkboxes = document.querySelectorAll('#family-tratas-checkboxes input[type="checkbox"]');
    checkboxes.forEach(cb => {
        cb.checked = checked;
    });
    loadFamilyData();
}

function toggleFamilyDropdown(event) {
    if (event) event.stopPropagation();
    const panel = document.getElementById('family-dropdown-panel');
    const arrow = document.getElementById('family-dropdown-arrow');
    if (!panel) return;
    if (panel.style.display === 'none' || !panel.style.display) {
        panel.style.display = 'flex';
        if (arrow) arrow.style.transform = 'rotate(180deg)';
    } else {
        panel.style.display = 'none';
        if (arrow) arrow.style.transform = 'rotate(0deg)';
    }
}

// Cerrar desplegable de familias al hacer clic fuera
document.addEventListener('click', function(e) {
    const wrapper = document.querySelector('.family-filter-wrapper');
    const panel = document.getElementById('family-dropdown-panel');
    const arrow = document.getElementById('family-dropdown-arrow');
    if (wrapper && panel && !wrapper.contains(e.target)) {
        panel.style.display = 'none';
        if (arrow) arrow.style.transform = 'rotate(0deg)';
    }
});

async function loadFamilyData() {
    // Obtener los trámites que tienen el checkbox tildado
    const checkboxes = document.querySelectorAll('#family-tratas-checkboxes input[type="checkbox"]:checked');
    const allCheckboxes = document.querySelectorAll('#family-tratas-checkboxes input[type="checkbox"]');
    const checkedTratas = Array.from(checkboxes).map(c => c.value);
    
    const dropdownText = document.getElementById('family-dropdown-text');
    if (dropdownText) {
        dropdownText.innerText = `${checkedTratas.length} de ${allCheckboxes.length} seleccionados`;
    }
    
    if (checkedTratas.length === 0) {
        // Ninguno seleccionado, limpiar widgets
        document.getElementById('family-meta-ing-prom-val').innerText = '--';
        document.getElementById('family-meta-obj-tot-val').innerText = '--';
        document.getElementById('family-meta-avance-pct').innerText = '--';
        document.getElementById('family-egr-progress-bar').style.width = '0%';
        document.getElementById('family-egr-legend-val').innerText = '0% (0 / 0 exp)';
        document.getElementById('family-table-container').innerHTML = `<p style="text-align: center; color: #64748b; padding: 2rem;">Seleccione al menos un trámite para ver el resumen consolidado.</p>`;
        if (familyChart) {
            familyChart.destroy();
            familyChart = null;
        }
        return;
    }

    try {
        const queryParams = checkedTratas.map(t => `trata=${t}`).join('&');
        const response = await def_fetch(`${API_BASE}/reporte/familia?${queryParams}`);
        if (!response.ok) throw new Error("Error cargando datos de familia.");
        
        const data = await response.json();
        
        // 1. Tarjetas de metas
        const targetEgr = data.metas.egresos_totales_plan || 0;
        const targetIng = data.metas.ingresos_esperados || 0;
        
        document.getElementById('family-meta-ing-prom-val').innerText = targetIng.toLocaleString('es-AR');
        document.getElementById('family-meta-obj-tot-val').innerText = targetEgr.toLocaleString('es-AR');
        
        // Egresos del mes actual
        const history = data.history || [];
        let actualEgr = 0;
        let actualIng = 0;
        
        if (history.length > 0) {
            const lastMonth = history[history.length - 1];
            actualEgr = (lastMonth.EGR_EF || 0) + (lastMonth.EGR_NE || 0);
            actualIng = lastMonth.ING || 0;
        }
        
        // Avance
        const avancePct = targetEgr > 0 ? Math.round((actualEgr / targetEgr) * 100) : 0;
        document.getElementById('family-meta-avance-pct').innerText = `${avancePct}%`;

        // Calcular variación MoM (mes actual vs anterior en base a la historia de la familia)
        let variationPct = 0;
        let showVariation = false;
        if (history.length >= 2) {
            const currentMonth = history[history.length - 1];
            const prevMonth = history[history.length - 2];
            const currentEgr = (currentMonth.EGR_EF || 0) + (currentMonth.EGR_NE || 0);
            const prevEgr = (prevMonth.EGR_EF || 0) + (prevMonth.EGR_NE || 0);
            
            if (prevEgr > 0) {
                variationPct = parseFloat((((currentEgr - prevEgr) / prevEgr) * 100).toFixed(1));
                showVariation = true;
            }
        }
        
        const varCardVal = document.getElementById('family-meta-variation-val');
        const varCardSub = document.getElementById('family-meta-variation-sub');
        const varCard = document.getElementById('family-meta-variation-card');
        
        if (varCardVal && varCardSub) {
            if (showVariation) {
                const isPositive = variationPct >= 0;
                varCardVal.innerText = `${isPositive ? '+' : ''}${variationPct}%`;
                varCardVal.style.color = isPositive ? '#10b981' : '#ef4444';
                varCardSub.innerText = `vs mes anterior (${isPositive ? 'Crecimiento ▲' : 'Decrecimiento ▼'})`;
                if (varCard) varCard.style.borderLeft = `4px solid ${isPositive ? '#10b981' : '#ef4444'}`;
            } else {
                varCardVal.innerText = '--';
                varCardVal.style.color = 'var(--text-main)';
                varCardSub.innerText = 'vs mes anterior (Sin datos)';
                if (varCard) varCard.style.borderLeft = 'none';
            }
        }
        
        // 2. Monitor de ritmo y avance
        const now = new Date();
        const currentDay = now.getDate();
        const totalDays = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
        const timeProgressPct = Math.round((currentDay / totalDays) * 100);
        
        const egrProgressPct = targetEgr > 0 ? Math.round((actualEgr / targetEgr) * 100) : 0;
        
        let perfClass = 'perf-mid';
        if (egrProgressPct >= timeProgressPct) {
            perfClass = 'perf-high';
        } else if (egrProgressPct < timeProgressPct * 0.6) {
            perfClass = 'perf-low';
        }
        
        const egrBar = document.getElementById('family-egr-progress-bar');
        if (egrBar) {
            egrBar.style.width = `${Math.min(100, egrProgressPct)}%`;
            egrBar.className = `meta-egr-bar-fill ${perfClass}`;
        }
        
        const egrLegendVal = document.getElementById('family-egr-legend-val');
        if (egrLegendVal) {
            egrLegendVal.innerText = `${egrProgressPct}% (${actualEgr} / ${targetEgr} exp)`;
        }
        
        const timeNeedle = document.getElementById('family-time-needle');
        if (timeNeedle) {
            timeNeedle.style.left = `${Math.min(100, timeProgressPct)}%`;
        }
        
        const timeLegendVal = document.getElementById('family-time-legend-val');
        if (timeLegendVal) {
            timeLegendVal.innerText = `${timeProgressPct}% (${currentDay} / ${totalDays} días)`;
        }
        
        // 3. Tabla resumen consolidado (mes en curso + último semestre = últimas 7 entradas)
        const slicedHistory = history.slice(-7);
        const tableContainer = document.getElementById('family-table-container');
        if (tableContainer) {
            tableContainer.innerHTML = buildFamilySummaryTable(slicedHistory);
        }
        
        // 4. Gráfico
        renderFamilyChart(slicedHistory);

    } catch (err) {
        console.error("Error en loadFamilyData:", err);
    }
}

function buildFamilySummaryTable(history) {
    const fmt = n => n.toLocaleString('es-AR');
    const allMonths = history.map(h => `${h.anio}-${h.mes}`);
    
    const metrics = [
        { label: 'INGRESOS',             field: 'ING',          cls: 'row-ing' },
        { label: 'EGRESOS EFECTIVOS',    field: 'EGR_EF',       cls: '' },
        { label: 'EGRESOS NO EFECTIVOS', field: 'EGR_NE',       cls: '' },
        { label: 'EGRESOS TOTALES',      field: 'EGR_TOT',      cls: 'row-egr-tot' },
        { label: 'STOCK PROPIO',         field: 'STOCK_PROPIO', cls: 'row-stock-p' },
        { label: 'SUBSANACIÓN ABIERTA',  field: 'STOCK_SUBS',   cls: 'row-stock-s' },
        { label: 'STOCK TOTAL',          field: 'STOCK_TOTAL',  cls: 'row-stock-tot' }
    ];

    let html = `<div class="summary-section" style="margin-top: 2rem;">
        <h3 class="summary-title">Resumen Histórico Consolidado (Familia)</h3>
        <div class="summary-wrapper">
            <table class="summary-table">
                <thead><tr>
                    <th class="sum-label-col">Indicador</th>
                    ${allMonths.map(mk => `<th>${MESES[parseInt(mk.split('-')[1])-1].substring(0,3).toUpperCase()}<br><span class="sum-year">${mk.split('-')[0]}</span></th>`).join('')}
                </tr></thead>
                <tbody>`;

    metrics.forEach(m => {
        html += `<tr class="${m.cls}"><td class="sum-label">${m.label}</td>`;
        history.forEach(h => {
            const mk = `${h.anio}-${h.mes}`;
            let val = 0;
            if (m.field === 'EGR_TOT') val = (h.EGR_EF || 0) + (h.EGR_NE || 0);
            else if (m.field === 'STOCK_TOTAL') val = (h.STOCK_PROPIO || 0) + (h.STOCK_SUBS || 0);
            else val = h[m.field] || 0;
            
            const now = new Date();
            const currentMonthKey = `${now.getFullYear()}-${now.getMonth() + 1}`;
            const isCurrent = mk === currentMonthKey;
            
            const cellClass = isCurrent ? 'sum-val current-month-cell' : 'sum-val';
            const cellStyle = isCurrent 
                ? 'font-weight: 700 !important; background-color: rgba(0, 159, 227, 0.05) !important; border-left: 2px solid rgba(0, 159, 227, 0.15) !important; border-right: 2px solid rgba(0, 159, 227, 0.15) !important;' 
                : '';
                
            let cellHTML = val !== undefined && val !== '-' ? fmt(val) : '-';
            html += `<td class="${cellClass}" style="${cellStyle}">${cellHTML}</td>`;
        });
        html += `</tr>`;
    });

    html += `</tbody></table></div></div>`;
    return html;
}

function renderFamilyChart(history) {
    const canvas = document.getElementById('familyProjectionChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (familyChart) familyChart.destroy();
    
    const sorted = [...history];
    
    familyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sorted.map(h => `${MESES[h.mes - 1].substring(0,3).toUpperCase()} ${h.anio}`),
            datasets: [
                { label: 'Stock Propio', data: sorted.map(d => d.STOCK_PROPIO || 0), type: 'line', borderColor: '#EF4444', backgroundColor: '#EF4444', borderWidth: 3, tension: 0.3, pointRadius: 4, order: 0 },
                { label: 'Subsanación Abierta', data: sorted.map(d => d.STOCK_SUBS || 0), type: 'line', borderColor: '#F59E0B', backgroundColor: '#F59E0B', borderWidth: 3, tension: 0.3, pointRadius: 4, order: 1 },
                { label: 'Ingresos', data: sorted.map(d => d.ING || 0), backgroundColor: '#002d47', borderRadius: 4, order: 2 },
                { label: 'Egresos Efectivos', data: sorted.map(d => d.EGR_EF || 0), backgroundColor: '#0076bb', stack: 'egresos', borderRadius: 4, order: 3 },
                { label: 'Egresos No Efectivos', data: sorted.map(d => d.EGR_NE || 0), backgroundColor: '#94A3B8', stack: 'egresos', order: 4 }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { font: { family: 'Outfit', size: 12 } } }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                x: { grid: { display: false } }
            }
        }
    });
}



