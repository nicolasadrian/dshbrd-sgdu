const API_BASE = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1') 
    ? 'http://127.0.0.1:8000/api' 
    : 'https://api.geo-epesege.com.ar/api';

// --- ESTADO DE AUTENTICACIÓN ---
let authToken = localStorage.getItem('sgdu_token');
let currentUser = JSON.parse(localStorage.getItem('sgdu_user') || 'null');
let metasChart = null;
let permisosObraChart = null;
let currentIntervencionesData = null;
let seguimientoViewMode = localStorage.getItem('sgdu_seguimiento_view_mode') || 'list';
let activeComplianceFilter = null;
let currentGerenciaConfig = {};
let currentSearchResults = [];
let currentSearchPage = 1;
const SEARCH_PAGE_SIZE = 20;
let currentSearchSortField = null;
let currentSearchSortAsc = true;
let userFavorites = new Set();
let userFavoriteFolders = [];
let currentSelectedFolderId = 'all';
let currentFavoritosSeguimientoData = [];

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

async function loadUserFavorites() {
    if (!authToken) return;
    try {
        const res = await def_fetch(`${API_BASE}/expediente/favoritos`);
        if (res && res.ok) {
            const data = await res.json();
            userFavorites = new Set(data.map(f => f.expediente));
        }
    } catch (e) {
        console.error("Error cargando favoritos:", e);
    }
}

function initAuth() {
    const loginOverlay = document.getElementById('login-overlay');
    const authControls = document.getElementById('auth-controls');
    const displayFullName = document.getElementById('display-fullname');
    const displaySector = document.getElementById('display-sector');
    const adminLink = document.getElementById('admin-link');

    if (authToken && currentUser) {
        if (!initAuth._refreshed) {
            initAuth._refreshed = true;
            def_fetch(`${API_BASE}/auth/me`)
                .then(r => r ? r.json() : null)
                .then(data => {
                    if (data) {
                        currentUser = { ...currentUser, ...data };
                        localStorage.setItem('sgdu_user', JSON.stringify(currentUser));
                        initAuth();
                    }
                })
                .catch(e => console.error("Error refreshing permissions:", e));
        }
        loginOverlay.style.display = 'none';
        authControls.style.display = 'flex';
        loadUserFavorites();
        displayFullName.innerText = currentUser.full_name || currentUser.username;
        displaySector.innerText = currentUser.sector || "General";

        const perms = currentUser.permissions || {};

        if (adminLink) {
            adminLink.style.display = perms.admin ? 'block' : 'none';
        }

        // Toggles for Seguimiento dropdown and its contents
        const hasSeguimientoAccess = perms.dgroc || perms.dgiur || perms.family;
        const navSeguimiento = document.getElementById('nav-dropdown-seguimiento');
        if (navSeguimiento) navSeguimiento.style.display = hasSeguimientoAccess ? 'inline-block' : 'none';

        const linkDgroc = document.querySelector('a[onclick*="showView(\'dgroc\')"]');
        if (linkDgroc) linkDgroc.style.display = perms.dgroc ? 'block' : 'none';
        const linkDgiur = document.querySelector('a[onclick*="showView(\'dgiur\')"]');
        if (linkDgiur) linkDgiur.style.display = perms.dgiur ? 'block' : 'none';
        const linkFamily = document.querySelector('a[onclick*="showView(\'family\')"]');
        if (linkFamily) linkFamily.style.display = perms.family ? 'block' : 'none';

        // Toggles for Reportes dropdown and its contents
        const hasReportesAccess = perms.seguimiento || perms.cierre || perms.sla || perms.subsanaciones || perms.pendientes_asociacion;
        const reportesDropdown = document.getElementById('nav-dropdown-reportes');
        if (reportesDropdown) reportesDropdown.style.display = hasReportesAccess ? 'inline-block' : 'none';

        const linkSeg = document.querySelector('a[onclick*="showView(\'seguimiento\')"]');
        if (linkSeg) linkSeg.style.display = perms.seguimiento ? 'block' : 'none';

        const cierreLink = document.getElementById('cierre-link');
        if (cierreLink) cierreLink.style.display = perms.cierre ? 'block' : 'none';

        const slaLink = document.getElementById('sla-link');
        if (slaLink) slaLink.style.display = perms.sla ? 'block' : 'none';

        const linkSub = document.querySelector('a[onclick*="showView(\'subsanaciones\')"]');
        if (linkSub) linkSub.style.display = perms.subsanaciones ? 'block' : 'none';

        const pendientesAsocLink = document.getElementById('pendientes-asoc-link');
        if (pendientesAsocLink) pendientesAsocLink.style.display = perms.pendientes_asociacion ? 'block' : 'none';

        // Toggles for Analytics dropdown and its contents
        const hasAnalyticsAccess = perms.analytics_estadistica || perms.analytics_datasets;
        const navAnalytics = document.getElementById('nav-dropdown-analytics');
        if (navAnalytics) navAnalytics.style.display = hasAnalyticsAccess ? 'inline-block' : 'none';

        const linkEstadistica = document.querySelector('a[onclick*="showView(\'analytics_estadistica\')"]');
        if (linkEstadistica) linkEstadistica.style.display = perms.analytics_estadistica ? 'block' : 'none';
        const linkDatasets = document.querySelector('a[onclick*="showView(\'analytics_datasets\')"]');
        if (linkDatasets) linkDatasets.style.display = perms.analytics_datasets ? 'block' : 'none';

        // Toggles for Mis Expedientes dropdown and its contents
        const hasExpedientesAccess = perms.buscador || perms.favoritos;
        const navExpedientes = document.getElementById('nav-dropdown-expedientes');
        if (navExpedientes) navExpedientes.style.display = hasExpedientesAccess ? 'inline-block' : 'none';

        const linkBuscador = document.querySelector('a[onclick*="showView(\'buscador\')"]');
        if (linkBuscador) linkBuscador.style.display = perms.buscador ? 'block' : 'none';
        const linkFavoritos = document.querySelector('a[onclick*="showView(\'favoritos\')"]');
        if (linkFavoritos) linkFavoritos.style.display = perms.favoritos ? 'block' : 'none';
        const linkAsignadosMi = document.querySelector('a[onclick*="showView(\'asignados-mi\')"]');
        if (linkAsignadosMi) linkAsignadosMi.style.display = perms['asignados-mi'] ? 'block' : 'none';
        const linkFavSeg = document.querySelector('a[onclick*="showView(\'favoritos-seguimiento\')"]');
        if (linkFavSeg) linkFavSeg.style.display = perms['favoritos-seguimiento'] ? 'block' : 'none';

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
            needs_password_change: data.needs_password_change,
            permissions: data.permissions
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

    // Seguridad: Validar contra los permisos dinámicos del usuario
    if (currentUser && currentUser.permissions) {
        // Mapeos para sub-vistas de gerencias
        const dgrocViews = ['catastro', 'instalaciones', 'conforme', 'contable', 'etapa_proyecto', 'aviso_obra', 'regularizacion'];
        const dgiurViews = ['morfologia', 'aph', 'usos'];
        
        let hasPermission = !!currentUser.permissions[viewId];
        if (viewId === 'asignados-mi') {
            hasPermission = !!currentUser.permissions['asignados-mi'];
        } else if (dgrocViews.includes(viewId)) {
            hasPermission = !!currentUser.permissions['dgroc'];
        } else if (dgiurViews.includes(viewId)) {
            hasPermission = !!currentUser.permissions['dgiur'];
        } else if (viewId === 'buzones' || viewId === 'buzon-analista-detalle') {
            hasPermission = !!(currentUser.permissions['dgroc'] || currentUser.permissions['dgiur']);
        }

        // Si no tiene permiso para la vista solicitada, redirigir a 'landing'
        if (viewId !== 'landing' && !hasPermission) {
            console.warn(`Acceso denegado a la vista ${viewId} para el usuario ${currentUser.username}`);
            showView('landing');
            return;
        }
    } else {
        const role = (currentUser?.role || "").toLowerCase();
        // Seguridad fallback: Solo admin puede ver la vista de admin
        if (viewId === 'admin' && (role !== 'administrador' && role !== 'admin')) {
            showView('landing');
            return;
        }
        // Seguridad fallback: Solo admin o seguimiento pueden ver la vista de seguimiento, SLA o Cierre
        if ((viewId === 'seguimiento' || viewId === 'sla' || viewId === 'cierre') && (role !== 'administrador' && role !== 'admin' && role !== 'seguimiento')) {
            showView('landing');
            return;
        }
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
        showBacklogMenu();
    }

    if (viewId === 'metas') {
        loadMetasData();
    }

    if (viewId === 'analytics_estadistica') {
        loadAnalyticsEstadistica();
    }

    if (viewId === 'analytics_datasets') {
        loadAnalyticsDatasets();
    }

    if (viewId === 'seguimiento') {
        loadSeguimientoData();
    }

    if (viewId === 'sla') {
        loadSLAReporte();
    }

    if (viewId === 'cierre') {
        loadCierreMesData();
    }

    if (viewId === 'subsanaciones') {
        loadSubsanacionesReport();
    }

    if (viewId === 'pendientes_asociacion') {
        loadPendientesAsociacionData();
    }

    if (viewId === 'family') {
        backToFamilySelector();
    }

    if (viewId === 'favoritos') {
        loadFavoritesView();
    }

    if (viewId === 'asignados-mi') {
        loadAsignadosMiView();
    }

    if (viewId === 'favoritos-seguimiento') {
        loadFavoritosSeguimientoView();
    }

    if (viewId === 'buscador') {
        const yearInput = document.getElementById('search-anio');
        if (yearInput && !yearInput.value) {
            yearInput.value = new Date().getFullYear();
        }
        const rulesContainer = document.getElementById('search-rules-list-container');
        if (rulesContainer && rulesContainer.children.length === 0) {
            addSearchRuleRow();
        }
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
            const codTrata = (row["COD TRATA"] || '').toUpperCase();
            if (codTrata !== 'INTERVENCIONES' && codTrata !== 'INTERVENCION') {
                totals[mk].ING += row.ING ?? 0;
                totals[mk].EGR_EF += row.EGR_EF ?? 0;
                totals[mk].EGR_NE += row.EGR_NE ?? 0;
                totals[mk].STOCK_PROPIO += row.STOCK_PROPIO ?? 0;
                totals[mk].STOCK_SUBS += row.STOCK_SUBS ?? 0;
            }
        }
    });

    const metrics = [
        { label: 'Ingresos', field: 'ING', cls: 'sum-ing' },
        { label: 'Egresos Efectivos', field: 'EGR_EF', cls: 'sum-egr-ef' },
        { label: 'Egresos No Efectivos', field: 'EGR_NE', cls: 'sum-egr-ne' },
        { label: 'Egresos Totales', field: 'EGR_TOT', cls: 'sum-egr-tot' },
        { label: 'Stock Propio', field: 'STOCK_PROPIO', cls: 'sum-stock' },
        { label: 'Subsanación Abierta', field: 'STOCK_SUBS', cls: 'sum-subs' },
        { label: 'Stock Total', field: 'STOCK_TOTAL', cls: 'sum-stock-tot' }
    ];

    const fmt = n => n.toLocaleString('es-AR');

    let html = `<div class="summary-section">
        <h3 class="summary-title">Resumen Mensual Consolidado <span style="font-size: 0.9rem; color: #64748b; font-weight: 500; margin-left: 6px;">(No incluye Intervenciones)</span></h3>
        <div class="summary-wrapper">
            <table class="summary-table">
                <thead><tr>
                    <th class="sum-label-col">Indicador</th>
                    ${allMonths.map(mk => `<th>${MESES[parseInt(mk.split('-')[1]) - 1].substring(0, 3).toUpperCase()}<br><span class="sum-year">${mk.split('-')[0]}</span></th>`).join('')}
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

    const allMonths = [...new Set(data.map(r => `${r.anio}-${r.mes}`))].sort((a, b) => {
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
                            ${MESES[parseInt(mk.split('-')[1]) - 1].substring(0, 3).toUpperCase()}<br>${mk.split('-')[0]}
                        </td>
                    `;
        }).join('')}
            </tr>`;

        const metrics = [
            { label: 'INGRESOS', field: 'ING', rowCls: 'row-ing' },
            { label: 'EGRESOS EFECTIVOS', field: 'EGR_EF', rowCls: '' },
            { label: 'EGRESOS NO EFECTIVOS', field: 'EGR_NE', rowCls: '' },
            { label: 'EGRESOS TOTALES', field: 'EGR_TOT', rowCls: 'row-egr-tot' },
            { label: 'STOCK PROPIO', field: 'STOCK_PROPIO', rowCls: 'row-stock-p' },
            { label: 'SUBSANACIÓN ABIERTA', field: 'STOCK_SUBS', rowCls: 'row-stock-s' },
            { label: 'STOCK TOTAL', field: 'STOCK_TOTAL', rowCls: 'row-stock-tot' }
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

            // Collect checked permissions from #new-user-perms-grid
            const permissions = {};
            document.querySelectorAll('#new-user-perms-grid .user-perm-checkbox').forEach(cb => {
                const permKey = cb.getAttribute('data-permission');
                permissions[permKey] = cb.checked;
            });

            try {
                // First POST to create the basic user credentials
                const resp = await def_fetch(`${API_BASE}/admin/users`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password, role })
                });

                if (resp && resp.ok) {
                    // Immediately PUT to save extra details (fullname, sector, email, permissions)
                    const updateResp = await def_fetch(`${API_BASE}/admin/users/${username}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ full_name, sector, email, permissions })
                    });

                    if (updateResp && updateResp.ok) {
                        alert('Usuario creado correctamente');
                        createUserForm.reset();
                        showUsersListView();
                        loadUsers();
                    } else {
                        const err = await updateResp.json();
                        alert('Usuario creado pero hubo un error al guardar detalles: ' + err.detail);
                        showUsersListView();
                        loadUsers();
                    }
                } else {
                    const err = await resp.json();
                    alert('Error: ' + err.detail);
                }
            } catch (err) {
                alert('Error al crear usuario');
            }
        });
    }

    // Event listener para crear rol
    const createRoleForm = document.getElementById('create-role-form');
    if (createRoleForm) {
        createRoleForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const role_name = document.getElementById('new-role-name').value.trim();
            if (!role_name) return;

            try {
                const resp = await def_fetch(`${API_BASE}/admin/roles`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ role_name })
                });

                if (resp && resp.ok) {
                    alert('Rol creado correctamente');
                    createRoleForm.reset();
                    loadAdminRoles();
                } else {
                    const err = await resp.json();
                    alert('Error: ' + err.detail);
                }
            } catch (err) {
                alert('Error al crear el rol');
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
            const sector = document.getElementById('edit-sector').value;
            const role = document.getElementById('edit-role').value;
            const password = document.getElementById('edit-password').value;

            // Collect permissions from #edit-user-perms-grid
            const permissions = {};
            document.querySelectorAll('#edit-user-perms-grid .user-perm-checkbox').forEach(cb => {
                const permKey = cb.getAttribute('data-permission');
                permissions[permKey] = cb.checked;
            });

            const data = { full_name, sector, role, permissions };
            if (password) data.password = password;

            try {
                const resp = await def_fetch(`${API_BASE}/admin/users/${username}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (resp && resp.ok) {
                    alert('Usuario actualizado');
                    showUsersListView();
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

    // Event listener para editar metas (configuración de metas)
    const editMetaForm = document.getElementById('edit-meta-form');
    if (editMetaForm) {
        editMetaForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const metaId = document.getElementById('edit-meta-id-hidden').value;
            const activo = document.getElementById('edit-meta-activo').checked;

            const parseCommaList = (id) => {
                const val = document.getElementById(id).value;
                return val ? val.split(',').map(s => s.trim()).filter(Boolean) : [];
            };

            const tratas_incluidas = parseCommaList('edit-meta-tratas-incluidas');
            const buzones_ingreso = parseCommaList('edit-meta-buzones-ingreso');
            const acronimos_egreso = parseCommaList('edit-meta-acronimos-egreso');
            const buzones_ingreso_intervenciones = parseCommaList('edit-meta-buzones-intervenciones');

            const descVal = document.getElementById('edit-meta-descripciones').value;
            const descripciones_validas = descVal ? descVal.split('\n').map(s => s.trim()).filter(Boolean) : [];

            const descripcion_trata = document.getElementById('edit-meta-descripcion-trata').value.trim();

            const analistas_oficiales = currentSadeChips.analistas.map(item => item.usuario);
            const firmantes_egreso = currentSadeChips.firmantes.map(item => item.usuario);

            const data = {
                tratas_incluidas,
                buzones_ingreso,
                analistas_oficiales,
                acronimos_egreso,
                activo,
                firmantes_egreso,
                buzones_ingreso_intervenciones,
                descripciones_validas,
                descripcion_trata
            };

            try {
                const resp = await def_fetch(`${API_BASE}/admin/metas/${metaId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (resp && resp.ok) {
                    alert('Configuración de meta actualizada correctamente');
                    showMetasList();
                    loadAdminMetas();
                } else {
                    const err = await resp.json();
                    alert('Error: ' + err.detail);
                }
            } catch (err) {
                console.error(err);
                alert("Error al actualizar la configuración");
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
            const cleanGerencia = gerencia.toLowerCase() === 'aph' ? 'APH' : (gerencia.charAt(0).toUpperCase() + gerencia.slice(1).replace('_', ' '));
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
            onUpdate: function () {
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
        ctx.fillText("No hay stock propio registrado", canvas.width / 2, canvas.height / 2);
        return;
    }

    const labels = monthDist.map(d => {
        if (!d.periodo || !d.periodo.includes('-')) return d.periodo;
        const [y, m] = d.periodo.split('-');
        return `${MESES[parseInt(m) - 1]} ${y}`;
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
        const displayName = row.analista_nombre || row.analista;
        html += `<tr>
            <td>
                <a href="javascript:void(0)" onclick="openDrillDown('${row.analista}', '${displayName.replace(/'/g, "\\'")}')" style="font-weight: 700; color: #1e40af; text-decoration: none; border-bottom: 1px dashed #1e40af; padding: 2px 6px; border-radius: 4px; display: inline-block; background-color: #eff6ff; margin: 1px 0;">
                    ${displayName}
                </a>
            </td>
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

function openDrillDown(analista, displayName) {
    const modal = document.getElementById('stock-drilldown-modal');
    const titleText = displayName && displayName !== analista
        ? `Analista: ${displayName} (${analista})`
        : `Analista: ${analista}`;
    document.getElementById('modal-analyst-name').innerText = titleText;
    const currentTrataNameResolved = document.getElementById('trata_detail_title')?.innerText || currentTrataCode;
    document.getElementById('modal-trata-info').innerText = `Gestión de Stock: ${currentTrataNameResolved} (${currentTrataCode})`;
    const filtered = currentStockData.expedientes.filter(e => e.analista === analista);
    let html = `<table class="matrix-table"><thead><tr><th>Expediente</th><th>ID</th><th>Fecha Ingreso</th><th>Días</th></tr></thead><tbody>`;
    filtered.forEach(e => { html += `<tr><td class="code-cell">${e.expediente}</td><td class="code-cell">${e.id_expediente}</td><td>${e.fecha_ing ? new Date(e.fecha_ing).toLocaleDateString('es-AR') : '-'}</td><td>${e.dias}</td></tr>`; });
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
        const labelText = `${MESES[parseInt(mNum) - 1]} ${y}`;
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

    // Si la librería SheetJS está disponible, generar un archivo .xlsx real y limpio
    if (typeof XLSX !== 'undefined') {
        try {
            const worksheet = XLSX.utils.json_to_sheet(data);
            const workbook = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(workbook, worksheet, "Reporte SGDU");
            XLSX.writeFile(workbook, `${filename}.xlsx`);
            return;
        } catch (error) {
            console.error("Error al exportar con SheetJS, usando fallback:", error);
        }
    }

    // Fallback: Generar el archivo pseudo-Excel HTML si no está disponible SheetJS
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

window.onclick = function (e) { if (e.target.classList.contains('modal')) e.target.style.display = 'none'; }

// --- FUNCIONES ADMIN ---
// --- FUNCIONES ADMIN ---
const PERMISSION_KEYS = {
    dgroc: "Seguimiento DGROC",
    dgiur: "Seguimiento DGIUR",
    family: "Familia de Trámites",
    seguimiento: "Reporte Metas",
    cierre: "Cierre de Mes",
    sla: "Tiempos de tramitación (SLA)",
    subsanaciones: "Subsanaciones",
    pendientes_asociacion: "Pendientes Asociación",
    buscador: "Buscador de Expedientes",
    favoritos: "Marcadores",
    'favoritos-seguimiento': "Gestión de Marcadores",
    'asignados-mi': "Asignados a Mí",
    analytics_estadistica: "Analytics (Estadística)",
    analytics_datasets: "Analytics (Datasets)",
    admin: "Backlog (Administración)"
};

let allAdminRoles = [];
let allAdminUsers = [];

function loadRolesDropdowns(roles) {
    const editRoleSelect = document.getElementById('edit-role');
    const newRoleSelect = document.getElementById('new-role');
    if (!editRoleSelect || !newRoleSelect) return;

    let html = '';
    roles.forEach(r => {
        const label = r.role_name.toUpperCase();
        html += `<option value="${r.role_name}">${label}</option>`;
    });

    editRoleSelect.innerHTML = html;
    newRoleSelect.innerHTML = html;
}

function toggleUserPermsOverrideUI() {
    const overrideToggle = document.getElementById('user-override-perms-toggle');
    const grid = document.getElementById('user-override-perms-grid');
    if (overrideToggle && grid) {
        grid.style.display = overrideToggle.checked ? 'grid' : 'none';
        if (overrideToggle.checked && grid.innerHTML === '') {
            let html = '';
            for (const key in PERMISSION_KEYS) {
                html += `
                    <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; font-weight: normal; margin: 2px 0;">
                        <input type="checkbox" class="user-override-checkbox" data-permission="${key}">
                        ${PERMISSION_KEYS[key]}
                    </label>
                `;
            }
            grid.innerHTML = html;
        }
    }
}

async function loadUsers() {
    const container = document.getElementById('users-table-container');
    if (!container) return;

    container.innerHTML = '<div style="padding: 2rem; text-align: center;"><span class="loader"></span><p style="margin-top: 1rem; color: #64748b;">Sincronizando registro de usuarios...</p></div>';

    try {
        // dynamic roles load
        const rolesResp = await def_fetch(`${API_BASE}/admin/roles`);
        if (rolesResp && rolesResp.ok) {
            allAdminRoles = await rolesResp.json();
            loadRolesDropdowns(allAdminRoles);

            // Auto initialize the new user role check boxes on load
            const newRoleSelect = document.getElementById('new-role');
            if (newRoleSelect && newRoleSelect.value) {
                handleRoleSelectionChange('new', newRoleSelect.value);
            }
        }

        const resp = await def_fetch(`${API_BASE}/admin/users`);
        if (!resp || !resp.ok) return;

        allAdminUsers = await resp.json();

        if (allAdminUsers.length === 0) {
            container.innerHTML = '<p style="padding: 2rem; text-align: center; color: #64748b;">No hay usuarios registrados.</p>';
            return;
        }

        let html = '<div class="users-grid">';

        allAdminUsers.forEach(u => {
            const isMe = u.username === currentUser.username;
            const roleLabel = (u.role || "").toUpperCase();
            const roleClass = (u.role || "").toLowerCase() === 'administrador' ? 'role-admin' : 'role-user';

            html += `
                <div class="user-card-premium">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div class="user-avatar ${roleClass}" style="width: 46px; height: 46px; border-radius: 12px; font-weight: 800; font-size: 1.1rem; color: white; display: flex; align-items: center; justify-content: center;">
                            ${(u.full_name || u.username).substring(0, 1).toUpperCase()}
                        </div>
                        <div style="overflow: hidden;">
                            <div style="font-weight: 700; color: var(--primary-dark); font-size: 1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${u.full_name || 'Sin nombre'}">
                                ${u.full_name || 'Sin nombre'}
                                ${isMe ? '<span class="current-user-tag" style="background: var(--primary); color: white; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; font-weight: 700; margin-left: 4px;">TÚ</span>' : ''}
                            </div>
                            <div style="font-size: 0.8rem; color: #64748b; font-weight: 600;">@${u.username}</div>
                        </div>
                    </div>
                    
                    <div style="font-size: 0.85rem; color: #475569; display: flex; flex-direction: column; gap: 4px; border-top: 1px solid #f1f5f9; padding-top: 12px;">
                        <div><strong>Sector:</strong> ${u.sector || 'S/D'}</div>
                        <div><strong>Rol:</strong> <span class="badge-role ${roleClass}">${roleLabel}</span></div>
                    </div>
                    
                    <div style="display: flex; gap: 8px; margin-top: auto; border-top: 1px solid #f1f5f9; padding-top: 12px;">
                        <button onclick="openEditUser('${u.username}')" class="btn-edit-user" style="flex: 1; padding: 8px; border-radius: 6px; cursor: pointer; border: 1px solid #cbd5e1; background: white;">Editar</button>
                        <button onclick="deleteUser('${u.username}')" class="btn-delete" ${isMe ? 'disabled' : ''} style="flex: 1; padding: 8px; border-radius: 6px; cursor: pointer;">Eliminar</button>
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

function openEditUser(username) {
    const user = allAdminUsers.find(u => u.username === username);
    if (!user) return;

    document.getElementById('edit-username-hidden').value = user.username;
    document.getElementById('edit-fullname').value = user.full_name || '';
    document.getElementById('edit-sector').value = user.sector || '';
    document.getElementById('edit-role').value = user.role;
    document.getElementById('edit-password').value = '';

    // Set edit view title header
    const editHeader = document.getElementById('edit-user-title-header');
    if (editHeader) {
        editHeader.innerText = `Editar Usuario: @${user.username}`;
    }

    // If permissions are null or undefined, load the default role permissions
    let perms = user.permissions;
    if (perms === null || perms === undefined) {
        const roleObj = allAdminRoles.find(r => r.role_name === user.role);
        perms = roleObj ? roleObj.permissions : {};
    }

    populatePermsCheckboxes('edit-user-perms-grid', perms);

    showEditUserView();
}

async function loadAdminRoles() {
    const container = document.getElementById('roles-list-container');
    if (!container) return;

    container.innerHTML = '<div style="padding: 2rem; text-align: center;"><span class="loader"></span><p style="margin-top: 1rem; color: #64748b;">Cargando roles y permisos...</p></div>';

    try {
        const resp = await def_fetch(`${API_BASE}/admin/roles`);
        if (!resp || !resp.ok) return;

        allAdminRoles = await resp.json();

        let html = '';
        allAdminRoles.forEach(r => {
            const isBuiltin = ['admin', 'administrador', 'seguimiento', 'usuario', 'user'].includes(r.role_name.toLowerCase());

            let permGrid = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin-top: 15px; background: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0;">';
            for (const key in PERMISSION_KEYS) {
                const hasPerm = !!r.permissions[key];
                const checked = hasPerm ? 'checked' : '';
                permGrid += `
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="font-size: 0.88rem; color: #334155; font-weight: 500;">${PERMISSION_KEYS[key]}</span>
                        <label class="switch-premium" style="position: relative; display: inline-block; width: 44px; height: 22px;">
                            <input type="checkbox" onchange="toggleRolePermission('${r.role_name}', '${key}', this.checked)" ${checked} style="opacity: 0; width: 0; height: 0;">
                            <span class="slider-premium"></span>
                        </label>
                    </div>
                `;
            }
            permGrid += '</div>';

            html += `
                <div class="admin-card" style="padding: 20px; border: 1px solid #cbd5e1; border-radius: 12px; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.02); background: white;">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <h4 style="margin: 0; font-size: 1.15rem; color: var(--primary-dark); font-weight: 700;">${r.role_name.toUpperCase()}</h4>
                            ${isBuiltin ? '<span style="background: #e0f2fe; color: #0369a1; font-size: 0.75rem; padding: 2px 8px; border-radius: 12px; font-weight: bold;">Sistema</span>' : ''}
                        </div>
                        ${!isBuiltin ? `<button onclick="deleteRole('${r.role_name}')" style="background: #fee2e2; color: #ef4444; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-family: 'Outfit'; font-weight: 600; font-size: 0.85rem;"><i class="fa-solid fa-trash"></i> Eliminar Rol</button>` : ''}
                    </div>
                    ${permGrid}
                </div>
            `;
        });

        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = '<p style="padding: 2rem; color: #ef4444; text-align: center;">Error al cargar los roles.</p>';
    }
}

async function toggleRolePermission(roleName, permissionKey, isChecked) {
    const role = allAdminRoles.find(r => r.role_name === roleName);
    if (!role) return;

    const updatedPerms = { ...role.permissions, [permissionKey]: isChecked };

    try {
        const resp = await def_fetch(`${API_BASE}/admin/roles/${roleName}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ permissions: updatedPerms })
        });
        if (resp && resp.ok) {
            role.permissions = updatedPerms;
        } else {
            alert("Error al actualizar permisos del rol");
        }
    } catch (err) {
        console.error("Error toggling role permission:", err);
    }
}

async function deleteRole(roleName) {
    if (!confirm(`¿Estás seguro de eliminar el rol "${roleName.toUpperCase()}"? Los usuarios con este rol perderán sus permisos predeterminados.`)) return;
    try {
        const resp = await def_fetch(`${API_BASE}/admin/roles/${roleName}`, {
            method: 'DELETE'
        });
        if (resp && resp.ok) {
            loadAdminRoles();
        } else {
            const err = await resp.json();
            alert("Error: " + err.detail);
        }
    } catch (err) {
        alert("Error al eliminar el rol");
    }
}

// --- GESTIÓN DE CONFIGURACIÓN DE METAS (ADMIN) ---
let currentMetaId = null;
let currentSadeChips = {
    analistas: [],
    firmantes: []
};
let allAdminMetas = [];

function showBacklogMenu() {
    document.querySelectorAll('.admin-tab-content').forEach(el => el.style.display = 'none');
    const subBread = document.getElementById('backlog-sub-breadcrumb');
    if (subBread) subBread.style.display = 'none';
    const cards = document.getElementById('backlog-cards-container');
    if (cards) cards.style.display = 'grid';
    const title = document.getElementById('backlog-title');
    if (title) title.style.display = 'block';
    showMetasList();
}

function enterBacklogSection(sectionName) {
    const cards = document.getElementById('backlog-cards-container');
    if (cards) cards.style.display = 'none';
    const title = document.getElementById('backlog-title');
    if (title) title.style.display = 'none';

    const activeContent = document.getElementById(`admin-tab-${sectionName}`);
    if (activeContent) {
        activeContent.style.display = 'block';
    }

    const subBread = document.getElementById('backlog-sub-breadcrumb');
    if (subBread) {
        if (sectionName === 'users') {
            subBread.innerText = ' / Usuarios del Sistema';
        } else if (sectionName === 'metas') {
            subBread.innerText = ' / Configuración de Metas';
        } else if (sectionName === 'roles') {
            subBread.innerText = ' / Configuración de Roles';
        }
        subBread.style.display = 'inline';
    }

    if (sectionName === 'users') {
        showUsersListView();
        loadUsers();
    } else if (sectionName === 'metas') {
        showMetasList();
        loadAdminMetas();
    } else if (sectionName === 'roles') {
        loadAdminRoles();
    }
}

function showMetasList() {
    const listC = document.getElementById('metas-list-container');
    if (listC) listC.style.display = 'block';
    const editC = document.getElementById('metas-edit-container');
    if (editC) editC.style.display = 'none';
}

async function loadAdminMetas() {
    const tableBody = document.getElementById('metas-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 2rem;"><span class="loader"></span><p style="margin-top: 0.5rem; color: #64748b;">Cargando configuración de metas...</p></td></tr>';

    try {
        const resp = await def_fetch(`${API_BASE}/admin/metas`);
        if (!resp || !resp.ok) {
            tableBody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: #ef4444; padding: 1.5rem;">Error al cargar configuraciones</td></tr>';
            return;
        }

        allAdminMetas = await resp.json();
        renderAdminMetasTable(allAdminMetas);
    } catch (e) {
        console.error("Error loading metas:", e);
        tableBody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: #ef4444; padding: 1.5rem;">Error de conexión con el servidor</td></tr>';
    }
}

function renderAdminMetasTable(metas) {
    const tableBody = document.getElementById('metas-table-body');
    if (!tableBody) return;

    if (metas.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: #64748b; padding: 1.5rem;">No se encontraron registros</td></tr>';
        return;
    }

    let html = '';
    metas.forEach(m => {
        const descText = m.descripcion_trata || '<span style="color: #94a3b8; font-style: italic;">Sin descripción disponible</span>';

        html += `
            <tr onclick="openEditMetaModal(${m.id})" style="border-bottom: 1px solid #e2e8f0; font-family: 'Outfit'; font-size: 0.95rem; cursor: pointer; transition: background-color 0.15s;" onmouseover="this.style.backgroundColor='#f8fafc'" onmouseout="this.style.backgroundColor='transparent'">
                <td style="padding: 14px 10px; font-weight: 600; text-transform: uppercase; color: var(--primary-dark);">${m.gerencia}</td>
                <td style="padding: 14px 10px; font-weight: 700; color: var(--primary);">${m.trata_reporte}</td>
                <td style="padding: 14px 10px; color: #475569;">${descText}</td>
            </tr>
        `;
    });

    tableBody.innerHTML = html;
}

function filterAdminMetas() {
    const query = document.getElementById('search-metas-input').value.toLowerCase().trim();
    if (!query) {
        renderAdminMetasTable(allAdminMetas);
        return;
    }

    const filtered = allAdminMetas.filter(m =>
        m.gerencia.toLowerCase().includes(query) ||
        m.trata_reporte.toLowerCase().includes(query) ||
        (m.descripcion_trata || '').toLowerCase().includes(query)
    );
    renderAdminMetasTable(filtered);
}

function openEditMetaModal(metaId) {
    const meta = allAdminMetas.find(m => m.id === metaId);
    if (!meta) return;

    currentMetaId = metaId;

    document.getElementById('analistas-search-input').value = '';
    document.getElementById('firmantes-search-input').value = '';
    document.getElementById('analistas-suggestions').style.display = 'none';
    document.getElementById('firmantes-suggestions').style.display = 'none';

    document.getElementById('edit-meta-id-hidden').value = meta.id;
    document.getElementById('edit-meta-subtitle').innerText = `${meta.gerencia.toUpperCase()} • Trata: ${meta.trata_reporte}`;
    document.getElementById('edit-meta-activo').checked = !!meta.activo;

    document.getElementById('edit-meta-tratas-incluidas').value = (meta.tratas_incluidas || []).join(', ');
    document.getElementById('edit-meta-buzones-ingreso').value = (meta.buzones_ingreso || []).join(', ');
    document.getElementById('edit-meta-acronimos-egreso').value = (meta.acronimos_egreso || []).join(', ');
    document.getElementById('edit-meta-buzones-intervenciones').value = (meta.buzones_ingreso_intervenciones || []).join(', ');
    document.getElementById('edit-meta-descripciones').value = (meta.descripciones_validas || []).join('\n');
    document.getElementById('edit-meta-descripcion-trata').value = meta.descripcion_trata || '';

    currentSadeChips.analistas = (meta.analistas_oficiales || []).map(u => ({ usuario: u, apellido_nombre: u }));
    currentSadeChips.firmantes = (meta.firmantes_egreso || []).map(u => ({ usuario: u, apellido_nombre: u }));

    renderSadeChips('analistas');
    renderSadeChips('firmantes');

    // Switch inline views
    document.getElementById('metas-list-container').style.display = 'none';
    document.getElementById('metas-edit-container').style.display = 'block';
}

function renderSadeChips(type) {
    const container = document.getElementById(`${type}-chips-container`);
    if (!container) return;

    const list = currentSadeChips[type];
    if (list.length === 0) {
        container.innerHTML = `<span style="font-size: 0.85rem; color: #94a3b8; font-style: italic; padding: 4px;">Sin ${type === 'analistas' ? 'analistas' : 'firmantes'} asignados</span>`;
        return;
    }

    let html = '';
    list.forEach(item => {
        const displayLabel = item.apellido_nombre && item.apellido_nombre !== item.usuario
            ? `${item.apellido_nombre} (${item.usuario})`
            : item.usuario;

        html += `
            <span class="sade-chip">
                <span>${displayLabel}</span>
                <span class="remove-chip-btn" onclick="removeSadeChip('${item.usuario}', '${type}')">&times;</span>
            </span>
        `;
    });

    container.innerHTML = html;
}

function removeSadeChip(usuario, type) {
    currentSadeChips[type] = currentSadeChips[type].filter(item => item.usuario !== usuario);
    renderSadeChips(type);
}

let sadeSearchTimeout = null;
function handleSadeSearch(event, type) {
    const query = event.target.value.trim();
    const suggestionsDiv = document.getElementById(`${type}-suggestions`);
    if (!suggestionsDiv) return;

    if (query.length < 2) {
        suggestionsDiv.innerHTML = '';
        suggestionsDiv.style.display = 'none';
        return;
    }

    clearTimeout(sadeSearchTimeout);
    sadeSearchTimeout = setTimeout(async () => {
        try {
            const resp = await def_fetch(`${API_BASE}/admin/sade_users/search?q=${encodeURIComponent(query)}`);
            if (!resp || !resp.ok) return;

            const results = await resp.json();
            if (results.length === 0) {
                suggestionsDiv.innerHTML = '<div style="padding: 10px; font-size: 0.85rem; color: #64748b; font-style: italic;">No se encontraron usuarios</div>';
                suggestionsDiv.style.display = 'block';
                return;
            }

            let html = '';
            results.forEach(user => {
                html += `
                    <div class="suggestion-item" onclick="selectSadeUser('${user.usuario}', '${user.apellido_nombre.replace(/'/g, "\\'")}', '${type}')">
                        <div>
                            <span class="suggestion-username">${user.usuario}</span> - <span>${user.apellido_nombre}</span>
                        </div>
                        <span class="suggestion-sector">${user.codigo_sector_interno || 'S/D'}</span>
                    </div>
                `;
            });
            suggestionsDiv.innerHTML = html;
            suggestionsDiv.style.display = 'block';
        } catch (e) {
            console.error("Error searching SADE users:", e);
        }
    }, 300);
}

function selectSadeUser(usuario, apellido_nombre, type) {
    const list = currentSadeChips[type];
    if (!list.some(item => item.usuario === usuario)) {
        list.push({ usuario, apellido_nombre });
        renderSadeChips(type);
    }

    document.getElementById(`${type}-search-input`).value = '';
    document.getElementById(`${type}-suggestions`).style.display = 'none';
}

// Dismiss suggestion boxes on click outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('#analistas-search-input') && !e.target.closest('#analistas-suggestions')) {
        const el = document.getElementById('analistas-suggestions');
        if (el) el.style.display = 'none';
    }
    if (!e.target.closest('#firmantes-search-input') && !e.target.closest('#firmantes-suggestions')) {
        const el = document.getElementById('firmantes-suggestions');
        if (el) el.style.display = 'none';
    }
});

// Expose functions to global scope
window.enterBacklogSection = enterBacklogSection;
window.showBacklogMenu = showBacklogMenu;
window.showMetasList = showMetasList;
window.filterAdminMetas = filterAdminMetas;
window.handleSadeSearch = handleSadeSearch;
window.selectSadeUser = selectSadeUser;
window.removeSadeChip = removeSadeChip;
window.openEditMetaModal = openEditMetaModal;

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
                    egrLegendVal.innerText = `${Math.min(100, egrProgressPct)}% (${actualEgr} / ${targetEgr} exp)`;
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
                        const { ctx: chartCtx, chartArea } = chart;
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
                        <span class="metric-mini-value ${perfClass}">${Math.min(100, t.progressPct)}%</span>
                    </div>
                </div>
                
                <div class="trata-track-progress-block">
                    <div class="progress-track-bar">
                        <div class="progress-track-fill ${perfClass}" style="width: ${Math.min(100, t.progressPct)}%;"></div>
                        <div class="progress-track-needle" style="left: ${Math.min(100, timeProgressPct)}%;"></div>
                    </div>
                    <div class="progress-track-labels">
                        <span>Avance: ${Math.min(100, t.progressPct)}%</span>
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
    "Registros": ["MDUG3001A", "MDUG1502A", "MDUG0142A", "MDUG4003A"],
    "Incendio": ["MDUG2101A"],
    "Conforme": ["MDUG0141A", "MDUG0104A"],
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

        // Calcular dinámicamente el nombre del mes anterior
        const prevMonthDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        const prevMonthName = MESES[prevMonthDate.getMonth()];

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
                            <span class="metric-mini-value ${perfClass}">${Math.min(100, f.progress_pct)}%</span>
                        </div>
                    </div>
                    
                    <div class="trata-track-progress-block">
                        <div class="progress-track-bar" style="height: 6px; background: #e2e8f0; border-radius: 3px; position: relative; margin-bottom: 8px;">
                            <div class="progress-track-fill ${perfClass}" style="width: ${Math.min(100, f.progress_pct)}%; height: 100%; border-radius: 3px;"></div>
                            <div class="progress-track-needle" style="left: ${Math.min(100, timeProgressPct)}%; height: 12px; width: 2px; background: #000; position: absolute; top: -3px; z-index: 2;"></div>
                        </div>
                        <div class="progress-track-labels" style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #64748b; font-weight: 600;">
                            <span>Avance: ${Math.min(100, f.progress_pct)}%</span>
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
document.addEventListener('click', function (e) {
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
        document.getElementById('family-meta-avance-pct').innerText = `${Math.min(100, avancePct)}%`;

        // Calcular variación MoM (mes actual vs anterior en base a la historia de la familia)
        let variationPct = 0;
        let showVariation = false;
        let prevMonthName = "";
        if (history.length >= 2) {
            const currentMonth = history[history.length - 1];
            const prevMonth = history[history.length - 2];
            const currentEgr = (currentMonth.EGR_EF || 0) + (currentMonth.EGR_NE || 0);
            const prevEgr = (prevMonth.EGR_EF || 0) + (prevMonth.EGR_NE || 0);

            if (prevEgr > 0) {
                variationPct = parseFloat((((currentEgr - prevEgr) / prevEgr) * 100).toFixed(1));
                showVariation = true;
                prevMonthName = MESES[prevMonth.mes - 1];
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
                varCardSub.innerText = `vs ${prevMonthName} (${isPositive ? 'Crecimiento ▲' : 'Decrecimiento ▼'})`;
                if (varCard) varCard.style.borderLeft = `4px solid ${isPositive ? '#10b981' : '#ef4444'}`;
            } else {
                varCardVal.innerText = '--';
                varCardVal.style.color = 'var(--text-main)';
                varCardSub.innerText = `vs ${prevMonthName || 'mes anterior'} (Sin datos)`;
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
            egrLegendVal.innerText = `${Math.min(100, egrProgressPct)}% (${actualEgr} / ${targetEgr} exp)`;
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
        { label: 'INGRESOS', field: 'ING', cls: 'row-ing' },
        { label: 'EGRESOS EFECTIVOS', field: 'EGR_EF', cls: '' },
        { label: 'EGRESOS NO EFECTIVOS', field: 'EGR_NE', cls: '' },
        { label: 'EGRESOS TOTALES', field: 'EGR_TOT', cls: 'row-egr-tot' },
        { label: 'STOCK PROPIO', field: 'STOCK_PROPIO', cls: 'row-stock-p' },
        { label: 'SUBSANACIÓN ABIERTA', field: 'STOCK_SUBS', cls: 'row-stock-s' },
        { label: 'STOCK TOTAL', field: 'STOCK_TOTAL', cls: 'row-stock-tot' }
    ];

    let html = `<div class="summary-section" style="margin-top: 2rem;">
        <h3 class="summary-title">Resumen Histórico Consolidado (Familia)</h3>
        <div class="summary-wrapper">
            <table class="summary-table">
                <thead><tr>
                    <th class="sum-label-col">Indicador</th>
                    ${allMonths.map(mk => `<th>${MESES[parseInt(mk.split('-')[1]) - 1].substring(0, 3).toUpperCase()}<br><span class="sum-year">${mk.split('-')[0]}</span></th>`).join('')}
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
            labels: sorted.map(h => `${MESES[h.mes - 1].substring(0, 3).toUpperCase()} ${h.anio}`),
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

// --- FUNCIONES PARA VISTA CIERRE DE MES ---
let currentCierreMes = '2026-05';

function changeCierreMes(mes) {
    loadCierreMesData(mes);
}

async function loadCierreMesData(mes) {
    if (!mes) {
        const select = document.getElementById('cierre-mes-select');
        mes = select ? select.value : '2026-05';
    }
    currentCierreMes = mes;

    const banner = document.getElementById('cierre-general-banner');
    const tableWrapper = document.getElementById('cierre-table-wrapper');

    // Reset indicator elements
    document.getElementById('cierre-val-ingresos').innerText = '--';
    document.getElementById('cierre-delta-ingresos').innerHTML = '--';
    document.getElementById('cierre-val-egresos').innerText = '--';
    document.getElementById('cierre-delta-egresos').innerHTML = '--';
    document.getElementById('cierre-val-stock').innerText = '--';
    document.getElementById('cierre-delta-stock').innerHTML = '--';
    document.getElementById('cierre-val-subsanaciones').innerText = '--';
    document.getElementById('cierre-delta-subsanaciones').innerHTML = '--';

    if (banner) {
        banner.style.display = 'none';
    }

    if (tableWrapper) {
        tableWrapper.innerHTML = `
            <div class="loading-overlay" style="position: static; padding: 3rem 0; background: transparent; box-shadow: none;">
                <span class="loader"></span>
                <h3 style="margin-top: 1rem; color: var(--primary-dark); font-family: 'Outfit';">Procesando Cierre de Mes ${mes}...</h3>
            </div>
        `;
    }

    const fmt = n => n.toLocaleString('es-AR');

    try {
        const response = await def_fetch(`${API_BASE}/reporte/cierre_mes?mes=${mes}`);
        if (!response || !response.ok) {
            throw new Error("No se pudo cargar el reporte de cierre.");
        }
        const data = await response.json();

        // 1. Población de KPIs y MoM
        function renderKpiAndDelta(valId, deltaId, val, valPrev, lowerIsBetter = false) {
            const valEl = document.getElementById(valId);
            const deltaEl = document.getElementById(deltaId);
            if (!valEl || !deltaEl) return;

            valEl.innerText = fmt(val);

            const delta = val - valPrev;
            const pct = valPrev > 0 ? ((delta / valPrev) * 100).toFixed(1) : '0';

            let deltaClass = 'cierre-delta-neutral';
            let arrow = '•';

            if (delta > 0) {
                deltaClass = lowerIsBetter ? 'cierre-delta-down' : 'cierre-delta-up';
                arrow = '↑';
            } else if (delta < 0) {
                deltaClass = lowerIsBetter ? 'cierre-delta-up' : 'cierre-delta-down';
                arrow = '↓';
            }

            const pctAbs = Math.abs(pct);
            const deltaAbs = Math.abs(delta);
            const labelText = delta > 0 ? `incremento` : `reducción`;

            if (delta !== 0) {
                deltaEl.className = `cierre-delta-indicator ${deltaClass}`;
                deltaEl.innerHTML = `${arrow} ${pctAbs}% (${labelText} de ${fmt(deltaAbs)} vs mes anterior)`;
            } else {
                deltaEl.className = 'cierre-delta-indicator cierre-delta-neutral';
                deltaEl.innerHTML = `• 0% (sin cambios vs mes anterior)`;
            }
        }

        // --- Cálculo de Trámites Automatizados vs Manuales ---
        let autoIng = 0;
        let autoIngPrev = 0;
        let autoEgr = 0;
        let autoEgrPrev = 0;

        const autoCodes = ['MDUG0146A', 'MDUG0102B']; // Copia de plano y Aviso de obra

        if (data.gerencias) {
            for (const gk in data.gerencias) {
                const gData = data.gerencias[gk];
                if (gData && gData.detalles) {
                    gData.detalles.forEach(t => {
                        const code = t.trata.toUpperCase();
                        if (autoCodes.includes(code)) {
                            autoIng += t.ingresos || 0;
                            autoIngPrev += t.ingresos_prev || 0;
                            autoEgr += t.egresos || 0;
                            autoEgrPrev += t.egresos_prev || 0;
                        }
                    });
                }
            }
        }

        const manualIng = Math.max(0, data.totales.ingresos - autoIng);
        const manualIngPrev = Math.max(0, data.totales.ingresos_prev - autoIngPrev);
        const manualEgr = Math.max(0, data.totales.egresos - autoEgr);
        const manualEgrPrev = Math.max(0, data.totales.egresos_prev - autoEgrPrev);

        // Renderizar Manuales
        renderKpiAndDelta('cierre-val-ingresos', 'cierre-delta-ingresos', manualIng, manualIngPrev);
        renderKpiAndDelta('cierre-val-egresos', 'cierre-delta-egresos', manualEgr, manualEgrPrev);

        // Renderizar Automatizados
        function renderAutoKpiAndDelta(valId, deltaId, val, valPrev) {
            const valEl = document.getElementById(valId);
            const deltaEl = document.getElementById(deltaId);
            if (!valEl || !deltaEl) return;

            valEl.innerText = fmt(val);

            const delta = val - valPrev;
            const pct = valPrev > 0 ? ((delta / valPrev) * 100).toFixed(1) : '0';

            let color = '#64748b'; // slate
            let arrow = '•';

            if (delta > 0) {
                color = '#166534'; // green
                arrow = '↑';
            } else if (delta < 0) {
                color = '#991b1b'; // red
                arrow = '↓';
            }

            const pctAbs = Math.abs(pct);
            if (delta !== 0) {
                deltaEl.style.color = color;
                deltaEl.innerHTML = `${arrow} ${pctAbs}%`;
            } else {
                deltaEl.style.color = '#64748b';
                deltaEl.innerHTML = `• 0%`;
            }
        }

        renderAutoKpiAndDelta('cierre-val-ingresos-auto', 'cierre-delta-ingresos-auto', autoIng, autoIngPrev);
        renderAutoKpiAndDelta('cierre-val-egresos-auto', 'cierre-delta-egresos-auto', autoEgr, autoEgrPrev);

        // Renderizar Stock y Subsanaciones
        renderKpiAndDelta('cierre-val-stock', 'cierre-delta-stock', data.totales.stock, data.totales.stock_prev, true);
        renderKpiAndDelta('cierre-val-subsanaciones', 'cierre-delta-subsanaciones', data.totales.subsanaciones, data.totales.subsanaciones_prev, true);

        // Helper para resolver la clase CSS del semáforo por nivel de cumplimiento
        function getSemaforoClass(pctVal) {
            if (pctVal < 25) return 'meta-badge-critico';      // 0 - 24%
            if (pctVal < 50) return 'meta-badge-bajo';         // 25 - 49%
            if (pctVal < 75) return 'meta-badge-medio';        // 50 - 74%
            if (pctVal < 100) return 'meta-badge-alto';        // 75 - 99%
            return 'meta-badge-perfecto';                      // 100% o más
        }

        // Badge especial de meta para Egresos (KPI Card)
        const valEgresosContainer = document.getElementById('cierre-card-egresos');
        if (valEgresosContainer) {
            const oldBadge = valEgresosContainer.querySelector('.meta-compliance-badge');
            if (oldBadge) oldBadge.remove();

            const badge = document.createElement('span');
            badge.className = 'meta-compliance-badge';
            if (data.totales.meta > 0) {
                const rawPct = (data.totales.egresos / data.totales.meta) * 100;
                const roundedPct = Math.round(rawPct);
                const cappedPct = Math.min(100, roundedPct);

                badge.className += ' ' + getSemaforoClass(roundedPct);
                badge.innerText = `Meta: ${fmt(data.totales.meta)} | ${cappedPct}% Cumplimiento`;
            } else {
                badge.className += ' meta-badge-no-aplica';
                badge.innerText = `Meta: N/A`;
            }
            badge.style.marginTop = '0.5rem';
            const deltaEgr = document.getElementById('cierre-delta-egresos');
            if (deltaEgr) {
                deltaEgr.parentNode.insertBefore(badge, deltaEgr.nextSibling);
            } else {
                valEgresosContainer.appendChild(badge);
            }
        }

        // 2. Banner general (mantener el % real en el texto pero reflejando el estado de cumplimiento)
        if (banner) {
            banner.style.display = 'flex';
            if (data.totales.meta > 0) {
                const rawPct = (data.totales.egresos / data.totales.meta) * 100;
                if (data.totales.cumplido) {
                    banner.style.backgroundColor = '#d1fae5';
                    banner.style.color = '#065f46';
                    banner.style.border = '1px solid #a7f3d0';
                    banner.innerHTML = `
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0; margin-right: 8px;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                        <span>¡Meta de gestión general cumplida para el mes de ${formatMesLabel(mes)}! Se registraron ${fmt(data.totales.egresos)} egresos frente a un objetivo unificado de ${fmt(data.totales.meta)} (${rawPct.toFixed(1)}% de cumplimiento).</span>
                    `;
                } else {
                    banner.style.backgroundColor = '#fee2e2';
                    banner.style.color = '#991b1b';
                    banner.style.border = '1px solid #fca5a5';
                    banner.style.color = '#991b1b';
                    banner.innerHTML = `
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0; margin-right: 8px;"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>
                        <span>Meta de gestión general no alcanzada para el mes de ${formatMesLabel(mes)}. Se registraron ${fmt(data.totales.egresos)} egresos frente a una meta planificada de ${fmt(data.totales.meta)} (${rawPct.toFixed(1)}% de avance).</span>
                    `;
                }
            } else {
                banner.style.backgroundColor = '#f1f5f9';
                banner.style.color = '#475569';
                banner.style.border = '1px solid #cbd5e1';
                banner.innerHTML = `
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink: 0; margin-right: 8px;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
                    <span>Cierre de mes de ${formatMesLabel(mes)}. No se definieron metas de planificación general para este período.</span>
                `;
            }
        }

        // 3. Renderizar tabla detallada agrupada por Familia de Trámites
        let tableHTML = `
            <table class="cierre-table">
                <thead>
                    <tr>
                        <th style="width: 30%;">Familia / Trámite</th>
                        <th style="width: 12%;">Ingresos</th>
                        <th style="width: 12%;">Egresos</th>
                        <th style="width: 20%;">Meta</th>
                        <th style="width: 13%;">Stock al Cierre</th>
                        <th style="width: 13%;">Subsanaciones</th>
                    </tr>
                </thead>
                <tbody>
        `;

        // Mapear todas las tratas a sus familias
        const trataToFamily = {};
        for (const [familyName, tratas] of Object.entries(FAMILIAS_CONFIG)) {
            tratas.forEach(t => {
                trataToFamily[t.toUpperCase()] = familyName;
            });
        }

        // Agrupar todos los detalles por Familia
        const familyGroups = {};
        const unassignedDetalles = [];

        const gerenciasKeys = Object.keys(data.gerencias).sort();
        for (const gk of gerenciasKeys) {
            const gData = data.gerencias[gk];

            gData.detalles.forEach(t => {
                const tUpper = t.trata.toUpperCase();
                const familyName = trataToFamily[tUpper];

                if (familyName) {
                    if (!familyGroups[familyName]) {
                        familyGroups[familyName] = {
                            ingresos: 0, ingresos_prev: 0, ingresos_yoy: 0,
                            egresos: 0, egresos_prev: 0, egresos_yoy: 0,
                            meta: 0, stock: 0, stock_prev: 0, stock_yoy: 0,
                            subsanaciones: 0, subsanaciones_prev: 0, subsanaciones_yoy: 0,
                            detalles: []
                        };
                    }
                    const group = familyGroups[familyName];
                    group.ingresos += t.ingresos;
                    group.ingresos_prev += t.ingresos_prev;
                    group.ingresos_yoy += t.ingresos_yoy || 0;
                    group.egresos += t.egresos;
                    group.egresos_prev += t.egresos_prev;
                    group.egresos_yoy += t.egresos_yoy || 0;
                    group.meta += t.meta;
                    group.stock += t.stock;
                    group.stock_prev += t.stock_prev;
                    group.stock_yoy += t.stock_yoy || 0;
                    group.subsanaciones += t.subsanaciones;
                    group.subsanaciones_prev += t.subsanaciones_prev;
                    group.subsanaciones_yoy += t.subsanaciones_yoy || 0;
                    group.detalles.push(t);
                } else {
                    unassignedDetalles.push(t);
                }
            });
        }

        // No auto-asignar trámites huérfanos a la familia "Otros" para mantener consistencia estricta.
        // Solo los trámites declarados en FAMILIAS_CONFIG["Otros"] pertenecerán a dicha familia.
        // Cualquier otro trámite no mapeado se descarta del desglose familiar.

        const parts = mes.split('-');
        const year = parseInt(parts[0], 10);
        const monthIdx = parseInt(parts[1], 10) - 1;
        const prevMonthIdx = (monthIdx - 1 + 12) % 12;
        const labelMoM = `vs ${MESES[prevMonthIdx]}`;
        const labelYoY = `vs ${MESES[monthIdx]} ${year - 1}`;

        function getComparisonText(val, prevVal, lowerIsBetter = false) {
            const delta = val - prevVal;
            if (delta === 0) return `<span class="cierre-table-cell-comparison">• ${labelMoM}: 0%</span>`;
            const pct = prevVal > 0 ? ((delta / prevVal) * 100).toFixed(0) : '';
            const arrow = delta > 0 ? '↑' : '↓';

            let cls = 'cierre-delta-neutral';
            if (delta > 0) {
                cls = lowerIsBetter ? 'cierre-delta-down' : 'cierre-delta-up';
            } else if (delta < 0) {
                cls = lowerIsBetter ? 'cierre-delta-up' : 'cierre-delta-down';
            }

            const pctStr = pct ? `${arrow} ${Math.abs(pct)}%` : `${arrow} ${Math.abs(delta)} exp`;
            return `<span class="cierre-table-cell-comparison ${cls}">${labelMoM}: ${pctStr}</span>`;
        }

        function getYoYComparisonText(val, yoyVal, lowerIsBetter = false) {
            const delta = val - yoyVal;
            if (delta === 0) return `<span class="cierre-table-cell-comparison" style="margin-left: 0; display: block; margin-top: 1px;">• ${labelYoY}: 0%</span>`;
            const pct = yoyVal > 0 ? ((delta / yoyVal) * 100).toFixed(0) : '';
            const arrow = delta > 0 ? '↑' : '↓';

            let cls = 'cierre-delta-neutral';
            if (delta > 0) {
                cls = lowerIsBetter ? 'cierre-delta-down' : 'cierre-delta-up';
            } else if (delta < 0) {
                cls = lowerIsBetter ? 'cierre-delta-up' : 'cierre-delta-down';
            }

            const pctStr = pct ? `${arrow} ${Math.abs(pct)}%` : `${arrow} ${Math.abs(delta)} exp`;
            return `<span class="cierre-table-cell-comparison ${cls}" style="margin-left: 0; display: block; margin-top: 1px;">${labelYoY}: ${pctStr}</span>`;
        }

        // Renderizar las familias y sus filas hijas
        let familyIndex = 0;
        const sortedFamilyNames = Object.keys(familyGroups).sort();

        for (const familyName of sortedFamilyNames) {
            const fData = familyGroups[familyName];
            familyIndex++;

            let familyCompBadge = '';
            if (fData.meta > 0) {
                const rawPct = (fData.egresos / fData.meta) * 100;
                const roundedPct = Math.round(rawPct);
                const cappedPct = Math.min(100, roundedPct);

                familyCompBadge = `<span class="meta-compliance-badge ${getSemaforoClass(roundedPct)}" style="display: inline-block; margin-left: 8px;">${cappedPct}% Cumplimiento</span>`;
            } else {
                familyCompBadge = `<span class="meta-compliance-badge meta-badge-no-aplica" style="display: inline-block; margin-left: 8px;">N/A</span>`;
            }

            // Fila de Cabecera de Familia (Collapsible sin el prefijo "Familia" - Colapsada por defecto)
            tableHTML += `
                <tr class="cierre-family-row collapsed" data-family-target="family-${familyIndex}" onclick="toggleCierreFamily(this)">
                    <td>
                        <div style="display: flex; align-items: flex-start; gap: 8px;">
                            <span class="family-toggle-icon" style="transform: rotate(-90deg); margin-top: 3px;">▼</span>
                            <div style="display: flex; flex-direction: column; gap: 2px;">
                                <span style="font-weight: 800; text-transform: uppercase; font-size: 0.95rem;">${familyName}</span>
                                <span class="family-tag-pill" style="width: max-content; margin-left: 0; font-size: 0.65rem; padding: 1px 6px;">${fData.detalles.length} trámites</span>
                            </div>
                        </div>
                    </td>
                    <td>
                        <span class="cierre-table-cell-val">${fmt(fData.ingresos)}</span>
                        ${getComparisonText(fData.ingresos, fData.ingresos_prev)}
                        ${getYoYComparisonText(fData.ingresos, fData.ingresos_yoy)}
                    </td>
                    <td>
                        <span class="cierre-table-cell-val">${fmt(fData.egresos)}</span>
                        ${getComparisonText(fData.egresos, fData.egresos_prev)}
                        ${getYoYComparisonText(fData.egresos, fData.egresos_yoy)}
                    </td>
                    <td>
                        <span class="cierre-table-cell-val">${fData.meta > 0 ? fmt(fData.meta) : '-'}</span>
                        ${familyCompBadge}
                    </td>
                    <td>
                        <span class="cierre-table-cell-val">${fmt(fData.stock)}</span>
                        ${getComparisonText(fData.stock, fData.stock_prev, true)}
                        ${getYoYComparisonText(fData.stock, fData.stock_yoy, true)}
                    </td>
                    <td>
                        <span class="cierre-table-cell-val">${fmt(fData.subsanaciones)}</span>
                        ${getComparisonText(fData.subsanaciones, fData.subsanaciones_prev, true)}
                        ${getYoYComparisonText(fData.subsanaciones, fData.subsanaciones_yoy, true)}
                    </td>
                </tr>
            `;

            // Filas Hijas (Individuales - Ocultas por defecto con la clase 'hidden')
            fData.detalles.forEach(t => {
                let compBadge = '';
                if (t.meta > 0) {
                    const rawPct = (t.egresos / t.meta) * 100;
                    const roundedPct = Math.round(rawPct);
                    const cappedPct = Math.min(100, roundedPct);

                    compBadge = `<span class="meta-compliance-badge ${getSemaforoClass(roundedPct)}" style="display: block; width: max-content; margin-top: 4px;">${cappedPct}% Cumplimiento</span>`;
                } else {
                    compBadge = `<span class="meta-compliance-badge meta-badge-no-aplica" style="display: block; width: max-content; margin-top: 4px;">N/A</span>`;
                }

                tableHTML += `
                    <tr class="cierre-child-row family-${familyIndex} hidden">
                        <td style="padding-left: 2.5rem; border-left: 3px solid var(--primary);">
                            <div style="font-weight: 700; color: var(--primary-dark); font-size: 0.88rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 280px;" title="${t.descripcion_trata}">${t.descripcion_trata}</div>
                            <div style="color: #64748b; font-size: 0.76rem;">${t.trata}</div>
                        </td>
                        <td>
                            <span class="cierre-table-cell-val">${fmt(t.ingresos)}</span>
                            ${getComparisonText(t.ingresos, t.ingresos_prev)}
                            ${getYoYComparisonText(t.ingresos, t.ingresos_yoy)}
                        </td>
                        <td>
                            <span class="cierre-table-cell-val">${fmt(t.egresos)}</span>
                            ${getComparisonText(t.egresos, t.egresos_prev)}
                            ${getYoYComparisonText(t.egresos, t.egresos_yoy)}
                        </td>
                        <td>
                            <span class="cierre-table-cell-val">${t.meta > 0 ? fmt(t.meta) : '-'}</span>
                            ${compBadge}
                        </td>
                        <td>
                            <span class="cierre-table-cell-val">${fmt(t.stock)}</span>
                            ${getComparisonText(t.stock, t.stock_prev, true)}
                            ${getYoYComparisonText(t.stock, t.stock_yoy, true)}
                        </td>
                        <td>
                            <span class="cierre-table-cell-val">${fmt(t.subsanaciones)}</span>
                            ${getComparisonText(t.subsanaciones, t.subsanaciones_prev, true)}
                            ${getYoYComparisonText(t.subsanaciones, t.subsanaciones_yoy, true)}
                        </td>
                    </tr>
                `;
            });
        }

        tableHTML += `
                </tbody>
            </table>
        `;
        tableWrapper.innerHTML = tableHTML;

        // Inyectar función global de toggle si no existe
        if (!window.toggleCierreFamily) {
            window.toggleCierreFamily = function (row) {
                const targetClass = row.getAttribute('data-family-target');
                const children = document.querySelectorAll(`.${targetClass}`);
                const isCollapsed = row.classList.toggle('collapsed');

                children.forEach(child => {
                    if (isCollapsed) {
                        child.classList.add('hidden');
                    } else {
                        child.classList.remove('hidden');
                    }
                });
            };
        }

    } catch (err) {
        console.error(err);
        if (tableWrapper) {
            tableWrapper.innerHTML = `
                <div style="padding: 3rem; text-align: center; color: #ef4444; font-weight: 700; font-family: 'Outfit';">
                    ✗ Error: No se pudieron cargar los datos de cierre para el periodo seleccionado.
                </div>
            `;
        }
    }
}

function formatMesLabel(mes) {
    const parts = mes.split('-');
    const mIdx = parseInt(parts[1]) - 1;
    return `${MESES[mIdx]} ${parts[0]}`;
}

// --- EXPORTAR PRESENTACIÓN EN PDF (DIAPOSITIVAS 16:10 DE ALTO IMPACTO VISUAL) ---
window.exportPresentationPDF = async function () {
    const mesSelect = document.getElementById('cierre-mes-select');
    const mes = mesSelect ? mesSelect.value : '2026-05';
    const mesLabel = formatMesLabel(mes);

    // Activar loader en el botón
    const btn = document.querySelector('button[onclick="exportPresentationPDF()"]');
    if (!btn) return;
    const oldText = btn.innerHTML;
    btn.innerHTML = `<span class="loader" style="width: 14px; height: 14px; border-width: 2px; margin-right: 8px; display: inline-block; vertical-align: middle;"></span> Generando PDF...`;
    btn.disabled = true;

    try {
        const response = await def_fetch(`${API_BASE}/reporte/cierre_mes?mes=${mes}`);
        if (!response || !response.ok) throw new Error("No se pudo obtener el reporte de cierre.");
        const data = await response.json();

        const fmt = n => n.toLocaleString('es-AR');

        // Mapear todas las tratas a sus familias
        const trataToFamily = {};
        for (const [familyName, tratas] of Object.entries(FAMILIAS_CONFIG)) {
            tratas.forEach(t => { trataToFamily[t.toUpperCase()] = familyName; });
        }

        // Agrupar todos los detalles por Familia
        const familyGroups = {};
        for (const gk in data.gerencias) {
            const gData = data.gerencias[gk];
            if (gData && gData.detalles) {
                gData.detalles.forEach(t => {
                    const familyName = trataToFamily[t.trata.toUpperCase()];
                    if (familyName) {
                        if (!familyGroups[familyName]) {
                            familyGroups[familyName] = {
                                ingresos: 0, ingresos_prev: 0,
                                egresos: 0, egresos_prev: 0,
                                meta: 0, stock: 0, stock_prev: 0,
                                subsanaciones: 0, subsanaciones_prev: 0,
                                detalles: []
                            };
                        }
                        const g = familyGroups[familyName];
                        g.ingresos += t.ingresos;
                        g.ingresos_prev += t.ingresos_prev;
                        g.egresos += t.egresos;
                        g.egresos_prev += t.egresos_prev;
                        g.meta += t.meta;
                        g.stock += t.stock;
                        g.stock_prev += t.stock_prev;
                        g.subsanaciones += t.subsanaciones;
                        g.subsanaciones_prev += t.subsanaciones_prev;
                        g.detalles.push(t);
                    }
                });
            }
        }

        // Helper para resolver la clase del semáforo
        function getSemaforoClassLocal(pctVal) {
            if (pctVal < 25) return 'meta-badge-critico';
            if (pctVal < 50) return 'meta-badge-bajo';
            if (pctVal < 75) return 'meta-badge-medio';
            if (pctVal < 100) return 'meta-badge-alto';
            return 'meta-badge-perfecto';
        }

        // --- CONSTRUIR EL TEMPLATE HTML DE LAS DIAPOSITIVAS ---
        let slidesHTML = `
        <div style="font-family: 'Outfit', 'Segoe UI', sans-serif; background: #ffffff; color: #0f172a; margin: 0; padding: 0; width: 16in; height: auto; box-sizing: border-box;">
            
            <!-- Estilos CSS Embebidos para la Impresión del PDF -->
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
                
                html, body {
                    margin: 0 !important;
                    padding: 0 !important;
                    background: #ffffff;
                }
                
                .slide {
                    width: 16in;
                    height: 9.9in; /* Ligeramente menor a 10in para evitar desbordes decimales accidentales */
                    box-sizing: border-box;
                    padding: 0.6in 0.8in;
                    position: relative;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    background: #ffffff;
                    color: #0f172a;
                    overflow: hidden;
                    margin: 0 !important;
                }
                
                .slide:not(.first-slide) {
                    page-break-before: always;
                }
                
                .meta-compliance-badge {
                    display: inline-block;
                    font-size: 0.65rem;
                    padding: 3px 8px;
                    border-radius: 6px;
                    font-weight: 800;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                .meta-badge-critico { background-color: #fef2f2 !important; color: #991b1b !important; border: 1px solid #fee2e2 !important; }
                .meta-badge-bajo { background-color: #fff7ed !important; color: #c2410c !important; border: 1px solid #ffedd5 !important; }
                .meta-badge-medio { background-color: #fefce8 !important; color: #854d0e !important; border: 1px solid #fef9c3 !important; }
                .meta-badge-alto { background-color: #f7fee7 !important; color: #4d7c0f !important; border: 1px solid #d9f99d !important; }
                .meta-badge-perfecto { background-color: #d1fae5 !important; color: #065f46 !important; border: 1px solid #a7f3d0 !important; }
                .meta-badge-no-aplica { background-color: #f1f5f9 !important; color: #475569 !important; border: 1px solid #cbd5e1 !important; }
            </style>

            <!-- ==================== DIAPOSITIVA 1: PORTADA ==================== -->
            <div class="slide first-slide" style="background: radial-gradient(circle at 80% 20%, #1e293b, #0f172a); color: white; justify-content: center; align-items: center; text-align: center;">
                <div style="position: absolute; top: 0.6in; left: 0.8in; font-weight: 800; font-size: 1.25rem; color: #facc15; letter-spacing: 1px;">
                    BUENOS AIRES CIUDAD
                </div>
                <div style="max-width: 950px; margin-top: -30px;">
                    <h1 style="font-size: 3.6rem; font-weight: 800; line-height: 1.15; margin-bottom: 1.8rem; letter-spacing: -1.2px; color: #ffffff; font-family: 'Outfit';">
                        INFORME MENSUAL DE GESTIÓN Y OPERACIONES
                    </h1>
                    <div style="display: inline-block; background: #eab308; color: #0f172a; padding: 10px 28px; border-radius: 99px; font-weight: 800; font-size: 1.45rem; text-transform: uppercase; margin-bottom: 2rem; box-shadow: 0 10px 15px -3px rgba(234, 179, 8, 0.3);">
                        Periodo: ${mesLabel}
                    </div>
                    <p style="color: #94a3b8; font-size: 1.3rem; margin: 0; font-weight: 500;">
                        Secretaría de Gobierno y Desarrollo Urbano (SGDU)
                    </p>
                    <p style="color: #64748b; font-size: 1rem; margin-top: 1rem;">
                        Subsecretaría de Gestión del Desarrollo Urbano
                    </p>
                </div>
                <div style="position: absolute; bottom: 0.6in; color: #475569; font-size: 0.85rem; font-weight: 600; letter-spacing: 0.5px;">
                    CONFIDENCIAL • GENERADO AUTOMÁTICAMENTE DESDE EL TABLERO SGDU
                </div>
            </div>

            <!-- ==================== DIAPOSITIVA 2: STATUS GENERAL DE LA SECRETARIA ==================== -->
            <div class="slide">
                <div>
                    <!-- Header -->
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f1f5f9; padding-bottom: 15px; margin-bottom: 25px;">
                        <div>
                            <h2 style="font-size: 1.85rem; font-weight: 800; margin: 0; color: #0f172a; text-transform: uppercase; letter-spacing: -0.5px; font-family: 'Outfit';">Status General de la Secretaría</h2>
                            <p style="color: #64748b; font-size: 0.95rem; margin: 0; margin-top: 2px;">Consolidado general de producción por Familias de Trámites unificadas</p>
                        </div>
                        <span style="font-weight: 800; color: #0369a1; font-size: 0.95rem; letter-spacing: 0.5px;">SGDU • DIAPOSITIVA 2</span>
                    </div>

                    <!-- Tabla General -->
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-family: 'Outfit';">
                        <thead>
                            <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1; font-size: 0.78rem; text-transform: uppercase; color: #475569; font-weight: 800;">
                                <th style="padding: 12px 15px; width: 30%;">Familia de Trámites</th>
                                <th style="padding: 12px 15px; width: 11%;">Ingresos</th>
                                <th style="padding: 12px 15px; width: 11%;">Egresos</th>
                                <th style="padding: 12px 15px; width: 11%;">Meta</th>
                                <th style="padding: 12px 15px; text-align: center; width: 16%;">Cumplimiento</th>
                                <th style="padding: 12px 15px; width: 10%;">Stock</th>
                                <th style="padding: 12px 15px; width: 11%;">Subsanaciones</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        // Generar filas para el slide 2
        Object.entries(familyGroups).sort((a, b) => b[1].egresos - a[1].egresos).forEach(([name, g]) => {
            const pct = g.meta > 0 ? Math.round((g.egresos / g.meta) * 100) : 0;
            const cappedPct = Math.min(100, pct);
            const badgeClass = g.meta > 0 ? getSemaforoClassLocal(pct) : 'meta-badge-no-aplica';
            const badgeText = g.meta > 0 ? `${cappedPct}%` : 'N/A';

            slidesHTML += `
                <tr style="border-bottom: 1px solid #e2e8f0; font-size: 0.82rem;">
                    <td style="padding: 10px 15px; font-weight: 800; color: #0f172a; text-transform: uppercase;">${name}</td>
                    <td style="padding: 10px 15px; font-weight: 600;">${fmt(g.ingresos)}</td>
                    <td style="padding: 10px 15px; font-weight: 600;">${fmt(g.egresos)}</td>
                    <td style="padding: 10px 15px; font-weight: 600;">${g.meta > 0 ? fmt(g.meta) : '-'}</td>
                    <td style="padding: 10px 15px; font-weight: 600; text-align: center;">
                        <span class="meta-compliance-badge ${badgeClass}" style="display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 800;">${badgeText}</span>
                    </td>
                    <td style="padding: 10px 15px; font-weight: 600;">${fmt(g.stock)}</td>
                    <td style="padding: 10px 15px; font-weight: 600;">${fmt(g.subsanaciones)}</td>
                </tr>
            `;
        });

        slidesHTML += `
                        </tbody>
                    </table>
                </div>

                <!-- Footer -->
                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 15px; font-size: 0.8rem; color: #94a3b8; font-weight: 600;">
                    <span>GOBIERNO DE LA CIUDAD DE BUENOS AIRES</span>
                    <span>SECGDU • SGDU</span>
                </div>
            </div>
        `;

        // ==================== SLIDES 3 a 12: 1 DIAPOSITIVA POR FAMILIA ====================
        let slideIndex = 3;
        Object.entries(familyGroups).forEach(([name, g]) => {
            const familyPct = g.meta > 0 ? Math.round((g.egresos / g.meta) * 100) : 0;
            const cappedFamilyPct = Math.min(100, familyPct);
            const familyBadgeClass = g.meta > 0 ? getSemaforoClassLocal(familyPct) : 'meta-badge-no-aplica';
            const familyBadgeText = g.meta > 0 ? `${cappedFamilyPct}%` : 'N/A';

            // Generar filas de los trámites individuales
            let childRowsHTML = '';
            g.detalles.forEach(t => {
                const childPct = t.meta > 0 ? Math.round((t.egresos / t.meta) * 100) : 0;
                const cappedChildPct = Math.min(100, childPct);
                const childBadgeClass = t.meta > 0 ? getSemaforoClassLocal(childPct) : 'meta-badge-no-aplica';
                const childBadgeText = t.meta > 0 ? `${cappedChildPct}%` : 'N/A';

                childRowsHTML += `
                    <tr style="border-bottom: 1px solid #f1f5f9; font-size: 0.76rem;">
                        <td style="padding: 8px 10px;">
                            <div style="font-weight: 700; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 250px;" title="${t.descripcion_trata}">${t.descripcion_trata}</div>
                            <div style="color: #64748b; font-size: 0.65rem;">${t.trata}</div>
                        </td>
                        <td style="padding: 8px 10px; font-weight: 600;">${fmt(t.ingresos)}</td>
                        <td style="padding: 8px 10px; font-weight: 600;">${fmt(t.egresos)}</td>
                        <td style="padding: 8px 10px; font-weight: 600;">${t.meta > 0 ? fmt(t.meta) : '-'}</td>
                        <td style="padding: 8px 10px; font-weight: 600; text-align: center;">
                            <span class="meta-compliance-badge ${childBadgeClass}" style="display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: 800;">${childBadgeText}</span>
                        </td>
                        <td style="padding: 8px 10px; font-weight: 600;">${fmt(t.stock)}</td>
                        <td style="padding: 8px 10px; font-weight: 600;">${fmt(t.subsanaciones)}</td>
                    </tr>
                `;
            });

            slidesHTML += `
            <!-- Diapositiva Familia: ${name} -->
            <div class="slide">
                <div>
                    <!-- Header -->
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f1f5f9; padding-bottom: 15px; margin-bottom: 25px;">
                        <div>
                            <h2 style="font-size: 1.85rem; font-weight: 800; margin: 0; color: #0f172a; text-transform: uppercase; letter-spacing: -0.5px; font-family: 'Outfit';">Familia: ${name}</h2>
                            <p style="color: #64748b; font-size: 0.95rem; margin: 0; margin-top: 2px;">Detalle analítico e indicadores individuales de trámites asociados</p>
                        </div>
                        <span style="font-weight: 800; color: #0369a1; font-size: 0.95rem; letter-spacing: 0.5px;">SGDU • DIAPOSITIVA ${slideIndex}</span>
                    </div>

                    <!-- Layout split: Métricas agregadas de familia + Grilla de Trámites -->
                    <div style="display: grid; grid-template-columns: 1fr 2.2fr; gap: 30px;">
                        <!-- Columna Izquierda: Tarjeta consolidada de la familia -->
                        <div style="display: flex; flex-direction: column; gap: 15px;">
                            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.01);">
                                <span style="font-size: 0.72rem; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; display: block;">Ingresos Familia</span>
                                <span style="font-size: 1.8rem; font-weight: 800; color: #0f172a; font-family: 'Outfit'; display: block; margin-top: 5px;">${fmt(g.ingresos)}</span>
                            </div>

                            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.01);">
                                <span style="font-size: 0.72rem; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; display: block;">Egresos Familia</span>
                                <span style="font-size: 1.8rem; font-weight: 800; color: #0f172a; font-family: 'Outfit'; display: block; margin-top: 5px;">${fmt(g.egresos)}</span>
                            </div>

                            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.01); display: flex; flex-direction: column; align-items: center; justify-content: center;">
                                <span style="font-size: 0.72rem; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 5px;">Cumplimiento Meta</span>
                                <span class="meta-compliance-badge ${familyBadgeClass}" style="display: inline-block; padding: 4px 12px; border-radius: 6px; font-size: 0.95rem; font-weight: 800;">${familyBadgeText}</span>
                            </div>

                            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.01); display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                <div>
                                    <span style="font-size: 0.65rem; font-weight: 800; color: #64748b; text-transform: uppercase; display: block;">Stock</span>
                                    <span style="font-size: 1.3rem; font-weight: 800; color: #f59e0b; display: block; margin-top: 2px;">${fmt(g.stock)}</span>
                                </div>
                                <div>
                                    <span style="font-size: 0.65rem; font-weight: 800; color: #64748b; text-transform: uppercase; display: block;">Subs.</span>
                                    <span style="font-size: 1.3rem; font-weight: 800; color: #6366f1; display: block; margin-top: 2px;">${fmt(g.subsanaciones)}</span>
                                </div>
                            </div>
                        </div>

                        <!-- Columna Derecha: Tabla detallada de trámites individuales -->
                        <div style="border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; background: white; max-height: 480px; overflow-y: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-family: 'Outfit';">
                                <thead>
                                    <tr style="border-bottom: 2px solid #cbd5e1; font-size: 0.68rem; text-transform: uppercase; color: #475569; font-weight: 800;">
                                        <th style="padding: 8px 10px; width: 35%;">Trámite / Acrónimo</th>
                                        <th style="padding: 8px 10px; width: 10%;">Ing.</th>
                                        <th style="padding: 8px 10px; width: 10%;">Egr.</th>
                                        <th style="padding: 8px 10px; width: 10%;">Meta</th>
                                        <th style="padding: 8px 10px; text-align: center; width: 15%;">Cump.</th>
                                        <th style="padding: 8px 10px; width: 10%;">Stock</th>
                                        <th style="padding: 8px 10px; width: 10%;">Subs.</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${childRowsHTML}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 15px; font-size: 0.8rem; color: #94a3b8; font-weight: 600;">
                    <span>GOBIERNO DE LA CIUDAD DE BUENOS AIRES</span>
                    <span>SECGDU • SGDU</span>
                </div>
            </div>
            `;
            slideIndex++;
        });

        // ==================== DIAPOSITIVA FINAL: GRACIAS ====================
        slidesHTML += `
            <!-- Diapositiva final: Cierre -->
            <div class="slide" style="background: radial-gradient(circle at 80% 20%, #1e293b, #0f172a); color: white; justify-content: center; align-items: center; text-align: center;">
                <div style="position: absolute; top: 0.6in; left: 0.8in; font-weight: 800; font-size: 1.25rem; color: #facc15; letter-spacing: 1px;">
                    BUENOS AIRES CIUDAD
                </div>
                <div style="max-width: 800px;">
                    <h1 style="font-size: 4.8rem; font-weight: 800; line-height: 1; margin-bottom: 2rem; letter-spacing: -2px; color: #ffffff; font-family: 'Outfit';">
                        ¡Muchas Gracias!
                    </h1>
                    <p style="color: #94a3b8; font-size: 1.4rem; font-weight: 500; line-height: 1.5; margin: 0;">
                        Secretaría de Gobierno y Desarrollo Urbano (SGDU)
                    </p>
                    <div style="width: 150px; height: 3px; background: #eab308; margin: 30px auto; border-radius: 99px;"></div>
                    <p style="color: #64748b; font-size: 0.95rem; font-weight: 500; text-transform: uppercase; letter-spacing: 1px;">
                        Fin del Reporte Operativo Mensual
                    </p>
                </div>
                <div style="position: absolute; bottom: 0.6in; color: #475569; font-size: 0.85rem; font-weight: 600; letter-spacing: 0.5px;">
                    GOBIERNO DE LA CIUDAD DE BUENOS AIRES • 2026
                </div>
            </div>

        </div>
        `;

        // CONFIGURACIÓN DE IMPRESIÓN DEL PDF (WIDESCREEN 16:10 EXACTA)
        const opt = {
            margin: 0,
            filename: 'Presentacion_SGDU_Gestion_' + mes + '.pdf',
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2, useCORS: true, letterRendering: true, logging: false },
            jsPDF: { unit: 'in', format: [16, 10], orientation: 'landscape' }
        };

        // Generar e iniciar descarga directamente de la cadena HTML
        await html2pdf().set(opt).from(slidesHTML).save();

    } catch (err) {
        console.error(err);
        alert("Ocurrió un error al generar la presentación PDF. Por favor, intente de nuevo.");
    } finally {
        btn.innerHTML = oldText;
        btn.disabled = false;
    }
};

async function buscarExpediente() {
    const anio = document.getElementById('search-anio').value.trim();
    const numero = document.getElementById('search-numero').value.trim();
    const reparticion = document.getElementById('search-reparticion').value;

    const resultsContainer = document.getElementById('search-results-container');
    const statusContainer = document.getElementById('search-status-container');

    if (!anio || !numero || !reparticion) {
        alert("Por favor complete todos los campos de búsqueda.");
        return;
    }

    // Ocultar resultados previos, mostrar loading
    resultsContainer.style.display = 'none';
    statusContainer.style.display = 'block';
    statusContainer.innerHTML = `
        <span class="loader" style="width: 28px; height: 28px; border-width: 3px; display: inline-block;"></span>
        <h3 style="margin-top: 1rem; color: var(--primary-dark); font-family: 'Outfit';">Buscando Expediente...</h3>
        <p style="color: #64748b; font-family: 'Outfit';">Consultando bases de datos y estados de stock...</p>
    `;

    try {
        const response = await def_fetch(`${API_BASE}/expediente/buscar?anio=${anio}&numero=${numero}&reparticion=${reparticion}`);
        if (!response || !response.ok) {
            throw new Error(`Error en la consulta (Status: ${response ? response.status : 'desconocido'})`);
        }

        const data = await response.json();
        statusContainer.style.display = 'none';

        if (!data || data.length === 0) {
            statusContainer.style.display = 'block';
            statusContainer.innerHTML = `
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">ℹ️</div>
                <h3 style="color: var(--primary-dark); margin: 0; font-family: 'Outfit';">No se encontraron resultados</h3>
                <p style="color: #64748b; margin: 0.5rem 0 0 0; font-family: 'Outfit';">Verifique los parámetros ingresados e intente nuevamente.</p>
            `;
            return;
        }

        // Guardar resultados y renderizar primer página
        currentSearchResults = data;
        currentSearchPage = 1;
        currentSearchSortField = null;
        currentSearchSortAsc = true;
        renderSearchResultsPage();

        resultsContainer.style.display = 'block';
        gsap.from(resultsContainer, { opacity: 0, y: 15, duration: 0.4, ease: "power2.out" });

    } catch (error) {
        statusContainer.style.display = 'block';
        statusContainer.innerHTML = `
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚠️</div>
            <h3 style="color: #ef4444; margin: 0; font-family: 'Outfit';">Error en la búsqueda</h3>
            <p style="color: #64748b; margin: 0.5rem 0 0 0; font-family: 'Outfit';">${error.message}</p>
        `;
    }
}

function switchBuscadorTab(tabId) {
    document.querySelectorAll('#buscador .tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('#buscador .buscador-tab-content').forEach(content => {
        content.classList.remove('active');
        content.style.display = 'none';
    });

    const activeBtn = document.getElementById(`btn-buscador-tab-${tabId}`);
    const activeContent = document.getElementById(`buscador-tab-${tabId}`);
    if (activeBtn) activeBtn.classList.add('active');
    if (activeContent) {
        activeContent.classList.add('active');
        activeContent.style.display = 'block';
    }

    const resultsContainer = document.getElementById('search-results-container');
    const statusContainer = document.getElementById('search-status-container');
    if (resultsContainer) resultsContainer.style.display = 'none';
    if (statusContainer) statusContainer.style.display = 'none';
}

function addSearchRuleRow() {
    const container = document.getElementById('search-rules-list-container');
    if (!container) return;

    const row = document.createElement('div');
    row.className = 'search-rule-row';

    row.innerHTML = `
        <div class="form-group" style="margin-bottom: 0;">
            <select class="rule-field" onchange="handleRuleFieldChange(this)" style="width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-family: 'Outfit'; font-size: 0.9rem; background: white;">
                <option value="analista">Analista</option>
                <option value="dias_stock">Días en Stock</option>
                <option value="gerencia">Gerencia / Dirección</option>
                <option value="trata">Código de Trámite (Trata)</option>
                <option value="is_subs">Tipo de Stock</option>
            </select>
        </div>
        <div class="form-group" style="margin-bottom: 0;">
            <select class="rule-operator" style="width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-family: 'Outfit'; font-size: 0.9rem; background: white;">
                <option value="like">Contiene</option>
                <option value="eq">Es igual a</option>
            </select>
        </div>
        <div class="form-group rule-value-container" style="margin-bottom: 0;">
            <input type="text" class="rule-value" placeholder="Ej: ACOSTAPA" required style="width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-family: 'Outfit'; font-size: 0.9rem;">
        </div>
        <button type="button" class="btn-remove-rule" onclick="removeSearchRuleRow(this)" title="Eliminar condición">&times;</button>
    `;

    container.appendChild(row);
}

function removeSearchRuleRow(button) {
    const container = document.getElementById('search-rules-list-container');
    if (!container) return;

    if (container.children.length > 1) {
        button.closest('.search-rule-row').remove();
    } else {
        alert("Debe haber al menos una condición de búsqueda.");
    }
}

function handleRuleFieldChange(selectElement) {
    const row = selectElement.closest('.search-rule-row');
    const operatorSelect = row.querySelector('.rule-operator');
    const valueContainer = row.querySelector('.rule-value-container');
    const field = selectElement.value;

    let operatorsHTML = '';
    let valueHTML = '';

    if (field === 'analista') {
        operatorsHTML = `
            <option value="like">Contiene</option>
            <option value="eq">Es igual a</option>
        `;
        valueHTML = `<input type="text" class="rule-value" placeholder="Ej: ACOSTAPA" required style="width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-family: 'Outfit'; font-size: 0.9rem;">`;
    } else if (field === 'dias_stock') {
        operatorsHTML = `
            <option value="gt">Es mayor que (>)</option>
            <option value="gte">Es mayor o igual que (>=)</option>
            <option value="lt">Es menor que (<)</option>
            <option value="lte">Es menor o igual que (<=)</option>
            <option value="eq">Es igual a (=)</option>
        `;
        valueHTML = `<input type="number" class="rule-value" placeholder="Ej: 30" min="0" required style="width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-family: 'Outfit'; font-size: 0.9rem;">`;
    } else if (field === 'gerencia') {
        operatorsHTML = `<option value="eq">Es igual a</option>`;
        valueHTML = `
            <select class="rule-value" style="width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-family: 'Outfit'; font-size: 0.9rem; background: white;">
                <option value="catastro">Catastro (DGROC)</option>
                <option value="instalaciones">Instalaciones (DGROC)</option>
                <option value="conforme">Conforme (DGROC)</option>
                <option value="contable">Contable (DGROC)</option>
                <option value="etapa_proyecto">Etapa Proyecto (DGROC)</option>
                <option value="aviso_obra">Aviso de Obra (DGROC)</option>
                <option value="morfologia">Morfología Urbana (DGIUR)</option>
                <option value="aph">Protección Histórica APH (DGIUR)</option>
                <option value="usos">Usos del Suelo (DGIUR)</option>
            </select>
        `;
    } else if (field === 'trata') {
        operatorsHTML = `
            <option value="eq">Es igual a</option>
            <option value="like">Contiene</option>
        `;
        valueHTML = `<input type="text" class="rule-value" placeholder="Ej: MDUG0134N" required style="width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-family: 'Outfit'; font-size: 0.9rem;">`;
    } else if (field === 'is_subs') {
        operatorsHTML = `<option value="eq">Es igual a</option>`;
        valueHTML = `
            <select class="rule-value" style="width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-family: 'Outfit'; font-size: 0.9rem; background: white;">
                <option value="0">Stock Propio</option>
                <option value="1">Subsanación</option>
            </select>
        `;
    }

    operatorSelect.innerHTML = operatorsHTML;
    valueContainer.innerHTML = valueHTML;
}

async function buscarPorCondiciones() {
    const conjunction = document.getElementById('search-conjunction').value;
    const ruleRows = document.querySelectorAll('#search-rules-list-container .search-rule-row');

    const resultsContainer = document.getElementById('search-results-container');
    const resultsTbody = document.getElementById('search-results-tbody');
    const statusContainer = document.getElementById('search-status-container');

    const rules = [];
    let isValid = true;

    ruleRows.forEach(row => {
        const field = row.querySelector('.rule-field').value;
        const operator = row.querySelector('.rule-operator').value;
        const valueElement = row.querySelector('.rule-value');
        const value = valueElement.value.trim();

        if (!value) {
            isValid = false;
            valueElement.style.borderColor = '#ef4444';
        } else {
            valueElement.style.borderColor = '#cbd5e1';
            rules.push({ field, operator, value });
        }
    });

    if (!isValid) {
        alert("Por favor complete todos los campos de valores para las condiciones.");
        return;
    }

    resultsContainer.style.display = 'none';
    statusContainer.style.display = 'block';
    statusContainer.innerHTML = `
        <span class="loader" style="width: 28px; height: 28px; border-width: 3px; display: inline-block;"></span>
        <h3 style="margin-top: 1rem; color: var(--primary-dark); font-family: 'Outfit';">Buscando Expedientes por Condiciones...</h3>
        <p style="color: #64748b; font-family: 'Outfit';">Filtrando base de datos según criterios...</p>
    `;

    try {
        const response = await def_fetch(`${API_BASE}/expediente/buscar_avanzado`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ conjunction, rules })
        });

        if (!response || !response.ok) {
            throw new Error(`Error en la consulta (Status: ${response ? response.status : 'desconocido'})`);
        }

        const data = await response.json();
        statusContainer.style.display = 'none';

        if (!data || data.length === 0) {
            statusContainer.style.display = 'block';
            statusContainer.innerHTML = `
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">ℹ️</div>
                <h3 style="color: var(--primary-dark); margin: 0; font-family: 'Outfit';">No se encontraron resultados</h3>
                <p style="color: #64748b; margin: 0.5rem 0 0 0; font-family: 'Outfit';">Ningún expediente cumple con los criterios indicados.</p>
            `;
            return;
        }

        // Guardar resultados y renderizar primer página
        currentSearchResults = data;
        currentSearchPage = 1;
        currentSearchSortField = null;
        currentSearchSortAsc = true;
        renderSearchResultsPage();

        resultsContainer.style.display = 'block';
        gsap.from(resultsContainer, { opacity: 0, y: 15, duration: 0.4, ease: "power2.out" });

    } catch (error) {
        statusContainer.style.display = 'block';
        statusContainer.innerHTML = `
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚠️</div>
            <h3 style="color: #ef4444; margin: 0; font-family: 'Outfit';">Error en la búsqueda</h3>
            <p style="color: #64748b; margin: 0.5rem 0 0 0; font-family: 'Outfit';">${error.message}</p>
        `;
    }
}

function renderSearchResultsPage() {
    updateSearchHeaderSortIndicators();
    const resultsContainer = document.getElementById('search-results-container');
    const resultsTbody = document.getElementById('search-results-tbody');
    const totalPages = Math.ceil(currentSearchResults.length / SEARCH_PAGE_SIZE) || 1;

    // Bounds check
    if (currentSearchPage < 1) currentSearchPage = 1;
    if (currentSearchPage > totalPages) currentSearchPage = totalPages;

    const startIndex = (currentSearchPage - 1) * SEARCH_PAGE_SIZE;
    const endIndex = Math.min(startIndex + SEARCH_PAGE_SIZE, currentSearchResults.length);
    const pageData = currentSearchResults.slice(startIndex, endIndex);

    resultsTbody.innerHTML = '';
    pageData.forEach(r => {
        const tr = document.createElement('tr');

        let badgeClass = 'badge-status-flujo';
        if (r.ubicacion === 'STOCK PROPIO' || r.ubicacion === 'STOCK PROPIO (INTERVENCION)') {
            badgeClass = 'badge-status-propio';
        } else if (r.ubicacion === 'SUBSANACION' || r.ubicacion === 'SUBSANACION (INTERVENCION)') {
            badgeClass = 'badge-status-subs';
        } else if (r.ubicacion.startsWith('EGRESADO')) {
            badgeClass = 'badge-status-egresado';
        }

        const cleanGerencia = r.gerencia ? (r.gerencia.toLowerCase() === 'aph' ? 'APH' : r.gerencia.charAt(0).toUpperCase() + r.gerencia.slice(1).replace('_', ' ')) : '-';

        const isFav = userFavorites.has(r.expediente);
        tr.innerHTML = `
            <td style="padding: 12px 16px; text-align: center; vertical-align: middle;">
                <span class="favorite-star ${isFav ? 'active' : ''}" data-expediente="${r.expediente}" onclick="toggleFavorite('${r.expediente}')">${isFav ? '★' : '☆'}</span>
            </td>
            <td style="padding: 12px 16px; font-weight: 700; color: #334155; font-family: inherit;">${r.expediente}</td>
            <td style="padding: 12px 16px; font-weight: 600;">${r.descripcion_trata || r.trata || ''}</td>
            <td style="padding: 12px 16px; font-weight: 600;">${cleanGerencia}</td>
            <td style="padding: 12px 16px;"><span class="badge-status ${badgeClass}">${r.ubicacion}</span></td>
            <td style="padding: 12px 16px; font-weight: 600; color: #475569;">${r.analista || 'SIN ASIGNAR'}</td>
            <td style="padding: 12px 16px; font-weight: 600; color: #475569;">${r.dias_tramitacion ?? 0}d</td>
            <td style="padding: 12px 16px; font-weight: 600; color: #475569;">${r.dias_subsanacion ?? 0}d</td>
            <td style="padding: 12px 16px; font-weight: 600; color: #475569;">${r.cant_subsanaciones ?? 0}</td>
            <td style="padding: 12px 16px; font-weight: 600; color: #475569;">${r.dias_stock ?? 0}d</td>
            <td style="padding: 12px 16px; font-size: 0.85rem; color: #64748b;">
                <div>${r.fecha_ultimo_pase || '-'}</div>
                <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 2px;">Creado: ${r.fecha_creacion || '-'}</div>
            </td>
        `;
        resultsTbody.appendChild(tr);
    });

    // Update pagination controls
    const infoSpan = document.getElementById('search-pagination-info');
    const controlsContainer = document.getElementById('search-pagination-controls');
    const paginationContainer = document.getElementById('search-pagination-container');

    if (currentSearchResults.length > 0) {
        infoSpan.innerText = `Mostrando ${startIndex + 1}-${endIndex} de ${currentSearchResults.length} resultados`;
        paginationContainer.style.display = 'flex';

        // Generar controles de paginación
        controlsContainer.innerHTML = '';

        // Botón Anterior
        const prevBtn = document.createElement('button');
        prevBtn.className = 'pagination-btn';
        prevBtn.innerHTML = '&laquo;';
        prevBtn.disabled = (currentSearchPage === 1);
        prevBtn.onclick = () => changeSearchPage(-1);
        controlsContainer.appendChild(prevBtn);

        // Lógica de páginas a mostrar para evitar lista eterna
        const pagesToDraw = [];

        if (totalPages <= 7) {
            for (let i = 1; i <= totalPages; i++) pagesToDraw.push(i);
        } else {
            // Siempre mostrar la primera página
            pagesToDraw.push(1);

            let start = Math.max(2, currentSearchPage - 1);
            let end = Math.min(totalPages - 1, currentSearchPage + 1);

            if (currentSearchPage <= 3) {
                end = 4;
            } else if (currentSearchPage >= totalPages - 2) {
                start = totalPages - 3;
            }

            if (start > 2) {
                pagesToDraw.push('...');
            }

            for (let i = start; i <= end; i++) {
                pagesToDraw.push(i);
            }

            if (end < totalPages - 1) {
                pagesToDraw.push('...');
            }

            // Siempre mostrar la última página
            pagesToDraw.push(totalPages);
        }

        // Renderizar los botones de número o puntos suspensivos
        pagesToDraw.forEach(p => {
            if (p === '...') {
                const el = document.createElement('span');
                el.className = 'pagination-ellipsis';
                el.innerText = '...';
                controlsContainer.appendChild(el);
            } else {
                const btn = document.createElement('button');
                btn.className = 'pagination-btn';
                if (p === currentSearchPage) btn.classList.add('active');
                btn.innerText = p;
                btn.onclick = () => {
                    currentSearchPage = p;
                    renderSearchResultsPage();
                };
                controlsContainer.appendChild(btn);
            }
        });

        // Botón Siguiente
        const nextBtn = document.createElement('button');
        nextBtn.className = 'pagination-btn';
        nextBtn.innerHTML = '&raquo;';
        nextBtn.disabled = (currentSearchPage === totalPages);
        nextBtn.onclick = () => changeSearchPage(1);
        controlsContainer.appendChild(nextBtn);

    } else {
        paginationContainer.style.display = 'none';
    }
}

function changeSearchPage(direction) {
    currentSearchPage += direction;
    renderSearchResultsPage();
}

function exportSearchResultsExcel() {
    if (!currentSearchResults || currentSearchResults.length === 0) {
        alert("No hay resultados de búsqueda para descargar.");
        return;
    }

    const excelData = currentSearchResults.map(r => ({
        "EXPEDIENTE": r.expediente,
        "TRATA": r.trata,
        "DESCRIPCION TRAMITE": r.descripcion_trata || "S/D",
        "GERENCIA": r.gerencia || "-",
        "ESTADO ACTUAL SADE": r.estado || "INICIACION",
        "UBICACION / STOCK": r.ubicacion,
        "ANALISTA ASIGNADO": r.analista || "SIN ASIGNAR",
        "DIAS TRAMITACION": r.dias_tramitacion ?? 0,
        "DIAS SUBSANACION": r.dias_subsanacion ?? 0,
        "CANT SUBSANACIONES": r.cant_subsanaciones ?? 0,
        "DIAS STOCK": r.dias_stock ?? 0,
        "FECHA ULTIMO PASE": r.fecha_ultimo_pase || "-",
        "FECHA CREACION": r.fecha_creacion || "-"
    }));

    const now = new Date();
    const dateStr = now.toISOString().substring(0, 10);
    const filename = `Busqueda_Expedientes_${dateStr}`;
    downloadExcel(filename, excelData);
}
window.exportSearchResultsExcel = exportSearchResultsExcel;

function sortSearchResults(field) {
    if (currentSearchSortField === field) {
        currentSearchSortAsc = !currentSearchSortAsc;
    } else {
        currentSearchSortField = field;
        currentSearchSortAsc = true;
    }

    currentSearchResults.sort((a, b) => {
        let valA = a[field];
        let valB = b[field];

        // Tratar nulos o vacíos
        if (valA === undefined || valA === null) valA = '';
        if (valB === undefined || valB === null) valB = '';

        // Comparación especial si son numéricos
        if (typeof valA === 'number' && typeof valB === 'number') {
            return currentSearchSortAsc ? valA - valB : valB - valA;
        }

        // Si no son números, comparar como string insensible a mayúsculas
        const strA = String(valA).toLowerCase().trim();
        const strB = String(valB).toLowerCase().trim();

        // Intentar parsear números que vienen como string (como días o cantidad)
        const numA = parseFloat(strA);
        const numB = parseFloat(strB);
        if (!isNaN(numA) && !isNaN(numB)) {
            return currentSearchSortAsc ? numA - numB : numB - numA;
        }

        if (strA < strB) return currentSearchSortAsc ? -1 : 1;
        if (strA > strB) return currentSearchSortAsc ? 1 : -1;
        return 0;
    });

    currentSearchPage = 1;
    renderSearchResultsPage();
}
window.sortSearchResults = sortSearchResults;

function updateSearchHeaderSortIndicators() {
    const fields = [
        'expediente', 'descripcion_trata', 'gerencia', 'ubicacion', 'analista',
        'dias_tramitacion', 'dias_subsanacion', 'cant_subsanaciones', 'dias_stock', 'fecha_ultimo_pase'
    ];

    fields.forEach(f => {
        const el = document.getElementById(`sort-indicator-${f}`);
        if (el) {
            if (currentSearchSortField === f) {
                el.innerText = currentSearchSortAsc ? '▲' : '▼';
                el.style.color = 'var(--primary)';
            } else {
                el.innerText = '⇅';
                el.style.color = '#94a3b8';
            }
        }
    });
}

async function toggleFavorite(expediente) {
    const isFav = userFavorites.has(expediente);

    // Si se intenta QUITAR un favorito que está asignado al usuario actual, bloquearlo
    if (isFav && currentUser) {
        const rec = currentFavoritesData.find(f => f.expediente === expediente);
        if (rec && rec.ficha_responsable === currentUser.username) {
            alert('Este expediente te fue asignado y no puede quitarse de marcadores desde esta pantalla.\nPara cambiar la asignación, usá la sección "Gestión de Marcadores".');
            return;
        }
    }
    const url = `${API_BASE}/expediente/favorito` + (isFav ? `/${encodeURIComponent(expediente)}` : '');
    const method = isFav ? 'DELETE' : 'POST';
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    if (!isFav) {
        options.body = JSON.stringify({ expediente: expediente });
    }

    try {
        const res = await def_fetch(url, options);
        if (res && res.ok) {
            if (isFav) {
                userFavorites.delete(expediente);
            } else {
                userFavorites.add(expediente);
            }
            updateFavoriteStars(expediente);

            // Si estamos en la vista de favoritos, refrescarla
            const targetView = document.getElementById('favoritos');
            if (targetView && targetView.style.display !== 'none') {
                loadFavoritesView();
            }
        } else {
            console.error("Error al guardar/eliminar favorito");
        }
    } catch (e) {
        console.error("Error toggleFavorite:", e);
    }
}
window.toggleFavorite = toggleFavorite;

function updateFavoriteStars(expediente) {
    const isFav = userFavorites.has(expediente);
    const stars = document.querySelectorAll(`.favorite-star[data-expediente="${expediente}"]`);
    stars.forEach(star => {
        if (isFav) {
            star.classList.add('active');
            star.innerText = '★';
        } else {
            star.classList.remove('active');
            star.innerText = '☆';
        }
    });
}
window.updateFavoriteStars = updateFavoriteStars;

let currentFavoritesData = [];

async function loadFavoritesView() {
    currentSelectedFolderId = 'all';
    const container = document.getElementById('favoritos-container');
    if (!container) return;

    // Mostrar estado de carga directamente en el container
    container.innerHTML = `
        <div style="text-align: center; padding: 3rem; color: #64748b; font-family: 'Outfit';">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 1.5rem; margin-bottom: 1rem; display: block; color: var(--primary);"></i>
            Cargando marcadores...
        </div>
    `;

    try {
        await loadFolders();

        const res = await def_fetch(`${API_BASE}/expediente/favoritos`);
        if (!res || !res.ok) {
            throw new Error("No se pudo obtener la lista de marcadores.");
        }

        currentFavoritesData = await res.json();
        userFavorites = new Set(currentFavoritesData.map(f => f.expediente));

        renderFavoritesContent();
    } catch (error) {
        container.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: #ef4444; font-family: 'Outfit'; font-weight: 600;">
                <i class="fa-solid fa-triangle-exclamation" style="font-size: 1.5rem; margin-bottom: 0.75rem; display: block;"></i>
                Error al cargar marcadores: ${error.message}
            </div>
        `;
    }
}

function copyToClipboard(text, element) {
    navigator.clipboard.writeText(text).then(() => {
        const originalHTML = element.innerHTML;
        element.innerHTML = '<i class="fa-solid fa-check" style="color: #28a745;"></i>';
        setTimeout(() => {
            element.innerHTML = originalHTML;
        }, 1500);
    }).catch(err => {
        console.error('Error al copiar al portapapeles: ', err);
    });
}

async function loadFolders() {
    try {
        const res = await def_fetch(`${API_BASE}/expediente/favoritos/carpetas`);
        if (res && res.ok) {
            userFavoriteFolders = await res.json();
        }
    } catch (e) {
        console.error("Error loading folders:", e);
    }
}

function renderFoldersSidebar() {
    const listEl = document.getElementById('favorites-folders-list');
    if (!listEl) return;

    const totalFavs = currentFavoritesData.length;
    const generalFavsCount = currentFavoritesData.filter(f => f.folder_id === null).length;

    let html = `
        <div onclick="selectFolder('all')" style="padding: 8px 16px; border-radius: 30px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; font-size: 0.85rem; font-family: 'Outfit'; font-weight: ${currentSelectedFolderId === 'all' ? '600' : '500'}; background: ${currentSelectedFolderId === 'all' ? 'var(--primary)' : '#f8fafc'}; border: 1px solid ${currentSelectedFolderId === 'all' ? 'var(--primary)' : '#e2e8f0'}; color: ${currentSelectedFolderId === 'all' ? 'white' : '#475569'}; transition: all 0.2s ease; user-select: none;" onmouseover="if(currentSelectedFolderId !== 'all') { this.style.background='#f1f5f9'; this.style.borderColor='#cbd5e1'; }" onmouseout="if(currentSelectedFolderId !== 'all') { this.style.background='#f8fafc'; this.style.borderColor='#e2e8f0'; }">
            <span><i class="${currentSelectedFolderId === 'all' ? 'fa-regular fa-folder-open' : 'fa-regular fa-folder'}" style="margin-right: 6px;"></i>Todos</span>
            <span style="font-size: 0.75rem; background: ${currentSelectedFolderId === 'all' ? 'rgba(255,255,255,0.25)' : '#e2e8f0'}; color: ${currentSelectedFolderId === 'all' ? 'white' : '#475569'}; padding: 2px 8px; border-radius: 20px; font-weight: 700;">${totalFavs}</span>
        </div>
        <div onclick="selectFolder('null')" style="padding: 8px 16px; border-radius: 30px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; font-size: 0.85rem; font-family: 'Outfit'; font-weight: ${currentSelectedFolderId === 'null' ? '600' : '500'}; background: ${currentSelectedFolderId === 'null' ? 'var(--primary)' : '#f8fafc'}; border: 1px solid ${currentSelectedFolderId === 'null' ? 'var(--primary)' : '#e2e8f0'}; color: ${currentSelectedFolderId === 'null' ? 'white' : '#475569'}; transition: all 0.2s ease; user-select: none;" onmouseover="if(currentSelectedFolderId !== 'null') { this.style.background='#f1f5f9'; this.style.borderColor='#cbd5e1'; }" onmouseout="if(currentSelectedFolderId !== 'null') { this.style.background='#f8fafc'; this.style.borderColor='#e2e8f0'; }">
            <span><i class="${currentSelectedFolderId === 'null' ? 'fa-regular fa-folder-open' : 'fa-regular fa-folder'}" style="margin-right: 6px;"></i>General</span>
            <span style="font-size: 0.75rem; background: ${currentSelectedFolderId === 'null' ? 'rgba(255,255,255,0.25)' : '#e2e8f0'}; color: ${currentSelectedFolderId === 'null' ? 'white' : '#475569'}; padding: 2px 8px; border-radius: 20px; font-weight: 700;">${generalFavsCount}</span>
        </div>
    `;

    userFavoriteFolders.forEach(folder => {
        const isSelected = currentSelectedFolderId == folder.id;
        html += `
            <div onclick="selectFolder(${folder.id})" style="padding: 8px 16px; border-radius: 30px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; font-size: 0.85rem; font-family: 'Outfit'; font-weight: ${isSelected ? '600' : '500'}; background: ${isSelected ? 'var(--primary)' : '#f8fafc'}; border: 1px solid ${isSelected ? 'var(--primary)' : '#e2e8f0'}; color: ${isSelected ? 'white' : '#475569'}; transition: all 0.2s ease; user-select: none;" onmouseover="if(currentSelectedFolderId != ${folder.id}) { this.style.background='#f1f5f9'; this.style.borderColor='#cbd5e1'; }" onmouseout="if(currentSelectedFolderId != ${folder.id}) { this.style.background='#f8fafc'; this.style.borderColor='#e2e8f0'; }">
                <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 140px;" title="${folder.name}"><i class="${isSelected ? 'fa-regular fa-folder-open' : 'fa-regular fa-folder'}" style="margin-right: 6px;"></i>${folder.name}</span>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="font-size: 0.75rem; background: ${isSelected ? 'rgba(255,255,255,0.25)' : '#e2e8f0'}; color: ${isSelected ? 'white' : '#475569'}; padding: 2px 8px; border-radius: 20px; font-weight: 700;">${folder.count}</span>
                    <span onclick="event.stopPropagation(); deleteFolder(${folder.id})" style="font-size: 0.85rem; color: ${isSelected ? 'rgba(255,255,255,0.8)' : '#ef4444'}; padding: 2px; cursor: pointer; display: inline-block; transition: transform 0.1s;" onmouseover="this.style.transform='scale(1.25)'" onmouseout="this.style.transform='scale(1)'" title="Eliminar Carpeta"><i class="fa-regular fa-trash-can"></i></span>
                </div>
            </div>
        `;
    });

    listEl.innerHTML = html;
}

function selectFolder(folderId) {
    currentSelectedFolderId = folderId;
    renderFavoritesContent();
}

function renderFavoritesContent() {
    renderFoldersSidebar();

    const container = document.getElementById('favoritos-container');
    if (!container) return;

    let folderTitle = "";
    if (currentSelectedFolderId === 'null') {
        folderTitle = "General (Sin carpeta)";
    } else if (currentSelectedFolderId !== 'all') {
        const folder = userFavoriteFolders.find(f => f.id == currentSelectedFolderId);
        if (folder) folderTitle = `Carpeta: ${folder.name}`;
    }

    let filteredData = [];
    if (currentSelectedFolderId === 'all') {
        filteredData = currentFavoritesData;
    } else if (currentSelectedFolderId === 'null') {
        filteredData = currentFavoritesData.filter(f => f.folder_id === null);
    } else {
        filteredData = currentFavoritesData.filter(f => f.folder_id == currentSelectedFolderId);
    }

    const headerRestHTML = `
        <tr>
            <th style="padding: 8px 10px; text-align: center; font-size: 0.72rem; width: 40px;">★</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Expediente</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Trámite</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Área</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Ubicación</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Analista</th>
            <th style="padding: 8px 6px; text-align: left; font-size: 0.72rem; width: 60px; line-height: 1.2;">Días<br>Tram.</th>
            <th style="padding: 8px 6px; text-align: left; font-size: 0.72rem; width: 60px; line-height: 1.2;">Días<br>Subs.</th>
            <th style="padding: 8px 6px; text-align: left; font-size: 0.72rem; width: 55px; line-height: 1.2;">Cant.<br>Subs.</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Días Stock</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Último Pase</th>
            <th style="padding: 8px 10px; text-align: center; font-size: 0.72rem; width: 60px;">Notas</th>
            <th style="padding: 8px 10px; text-align: center; font-size: 0.72rem; width: 120px;">Carpeta</th>
        </tr>
    `;

    function getRowHTML(r, includeReunion, isAssignedToMe) {
        let badgeClass = 'badge-status-flujo';
        if (r.ubicacion === 'STOCK PROPIO' || r.ubicacion === 'STOCK PROPIO (INTERVENCION)') {
            badgeClass = 'badge-status-propio';
        } else if (r.ubicacion === 'SUBSANACION' || r.ubicacion === 'SUBSANACION (INTERVENCION)') {
            badgeClass = 'badge-status-subs';
        } else if (r.ubicacion.startsWith('EGRESADO')) {
            badgeClass = 'badge-status-egresado';
        }

        const cleanGerencia = r.gerencia ? (r.gerencia.toLowerCase() === 'aph' ? 'APH' : r.gerencia.charAt(0).toUpperCase() + r.gerencia.slice(1).replace('_', ' ')) : '-';

        let folderOptionsHtml = `<option value="null" ${r.folder_id === null ? 'selected' : ''}>General</option>`;
        userFavoriteFolders.forEach(folder => {
            folderOptionsHtml += `<option value="${folder.id}" ${r.folder_id == folder.id ? 'selected' : ''}>${folder.name}</option>`;
        });

        // Si el expediente me fue asignado, la estrella es no-clickeable
        const starCell = isAssignedToMe
            ? `<span title="Asignado a vos — no puede quitarse desde aquí" style="font-size: 1.1rem; color: #f59e0b; cursor: not-allowed; display: inline-block;" data-expediente="${r.expediente}"><i class="fa-solid fa-user-lock" style="font-size: 0.9rem; color: #f59e0b;"></i></span>`
            : `<span class="favorite-star active" data-expediente="${r.expediente}" onclick="toggleFavorite('${r.expediente}')">★</span>`;

        return `
            <tr>
                <td style="padding: 8px 10px; text-align: center; vertical-align: middle;">
                    ${starCell}
                </td>
                <td style="padding: 8px 10px; font-weight: 700; color: #334155; font-family: inherit; white-space: nowrap;">
                    <span onclick="openDetalleExpedienteModal('${r.expediente}')" style="cursor: pointer; color: #1e293b; font-weight: 700; transition: color 0.15s, border-color 0.15s; border-bottom: 1px dashed #cbd5e1; padding-bottom: 1px;" onmouseover="this.style.color='var(--primary)'; this.style.borderColor='var(--primary)';" onmouseout="this.style.color='#1e293b'; this.style.borderColor='#cbd5e1';">${r.expediente}</span>
                    <span onclick="copyToClipboard('${r.expediente}', this)" style="cursor: pointer; margin-left: 6px; font-size: 0.8rem; color: #94a3b8; transition: color 0.2s; display: inline-block; vertical-align: middle;" onmouseover="this.style.color='var(--primary)'" onmouseout="this.style.color='#94a3b8'" title="Copiar Expediente">
                        <i class="fa-regular fa-copy"></i>
                    </span>
                </td>
                <td style="padding: 8px 10px; font-weight: 600; font-size: 0.82rem;">${r.descripcion_trata || r.trata || ''}</td>
                <td style="padding: 8px 10px; font-weight: 600; font-size: 0.82rem;">${cleanGerencia}</td>
                <td style="padding: 8px 10px;"><span class="badge-status ${badgeClass}" style="font-size: 0.75rem;">${r.ubicacion}</span></td>
                <td style="padding: 8px 10px; font-weight: 600; color: #475569; font-size: 0.82rem;">${r.analista || 'SIN ASIGNAR'}</td>
                <td style="padding: 8px 6px; font-weight: 600; color: #475569; font-size: 0.82rem;">${r.dias_tramitacion ?? 0}d</td>
                <td style="padding: 8px 6px; font-weight: 600; color: #475569; font-size: 0.82rem;">${r.dias_subsanacion ?? 0}d</td>
                <td style="padding: 8px 6px; font-weight: 600; color: #475569; font-size: 0.82rem;">${r.cant_subsanaciones ?? 0}</td>
                <td style="padding: 8px 10px; font-weight: 600; color: #475569; font-size: 0.82rem;">${r.dias_stock ?? 0}d</td>
                <td style="padding: 8px 10px; font-size: 0.78rem; color: #64748b;">
                    <div>${r.fecha_ultimo_pase || '-'}</div>
                    <div style="font-size: 0.72rem; color: #94a3b8; margin-top: 2px;">Creado: ${r.fecha_creacion || '-'}</div>
                </td>
                <td style="padding: 8px 10px; text-align: center; vertical-align: middle;">
                    <button onclick="openFavoriteNotesModal('${r.expediente}')" style="background: none; border: none; cursor: pointer; position: relative; padding: 4px 6px; display: inline-flex; align-items: center; justify-content: center; transition: all 0.2s;" title="Ver/Agregar Anotaciones" onmouseover="this.style.transform='scale(1.15)'" onmouseout="this.style.transform='scale(1)'">
                        <i class="fa-regular fa-comment-dots" style="font-size: 1.1rem; color: ${r.cant_notas > 0 ? 'var(--primary)' : '#94a3b8'};"></i>
                        ${r.cant_notas > 0 ? `<span style="position: absolute; top: -4px; right: -4px; background: #ef4444; color: white; font-size: 0.65rem; font-weight: 700; border-radius: 50%; width: 15px; height: 15px; display: flex; align-items: center; justify-content: center; border: 2px solid white;">${r.cant_notas}</span>` : ''}
                    </button>
                </td>
                <td style="padding: 8px 10px; text-align: center; vertical-align: middle;">
                    <select onchange="moveFavoriteToFolder('${r.expediente}', this.value)" style="padding: 3px 6px; border-radius: 6px; border: 1px solid #cbd5e1; outline: none; font-size: 0.76rem; font-family: 'Outfit'; cursor: pointer; max-width: 115px;">
                        ${folderOptionsHtml}
                    </select>
                </td>
            </tr>
        `;
    }

    const filteredFavs = filteredData.filter(r => !currentUser || r.ficha_responsable !== currentUser.username);

    container.innerHTML = `
        ${folderTitle ? `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 10px;">
            <h3 id="current-folder-title" style="color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700; margin: 0; border-left: 4px solid var(--primary); padding-left: 0.75rem;">${folderTitle}</h3>
        </div>
        ` : ''}

        ${filteredFavs.length === 0 ? `
            <div id="favoritos-empty-state" style="text-align: center; padding: 3rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem; color: #94a3b8;"><i class="fa-regular fa-folder-open"></i></div>
                <h3 style="color: #64748b; margin: 0; font-family: 'Outfit';">Esta carpeta está vacía</h3>
                <p style="color: #94a3b8; margin: 0.5rem 0 0 0; font-family: 'Outfit';">Mueva expedientes aquí desde otras carpetas o marque nuevos expedientes.</p>
            </div>
        ` : `
            <div style="background: white; border-radius: 16px; border: 2px solid #e2e8f0; box-shadow: 0 4px 16px rgba(0,0,0,0.05); padding: 1.5rem;">
                <div style="overflow-x: auto; width: 100%;">
                    <table class="matrix-table" style="margin-top: 0; width: 100%;">
                        <thead>${headerRestHTML}</thead>
                        <tbody>
                            ${filteredFavs.map(r => getRowHTML(r, false, false)).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `}
    `;
}

async function updateFichaProximaReunion(expediente, value) {
    const isSi = (value === 'si');
    const r = currentFavoritesData.find(f => f.expediente === expediente);
    if (!r) return;
    
    try {
        const payload = {
            direccion: r.ficha_direccion || "",
            responsable: r.ficha_responsable || "",
            estado: r.ficha_estado || "",
            prioridad: r.ficha_prioridad || "",
            proxima_reunion: isSi,
            notas_internas: ""
        };
        const res = await def_fetch(`${API_BASE}/expediente/ficha/${encodeURIComponent(expediente)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res && res.ok) {
            r.ficha_proxima_reunion = isSi;
            if (typeof currentFavoritosSeguimientoData !== 'undefined') {
                const rSeg = currentFavoritosSeguimientoData.find(f => f.expediente === expediente);
                if (rSeg) rSeg.ficha_proxima_reunion = isSi;
            }
            const targetAsignadosView = document.getElementById('asignados-mi');
            if (targetAsignadosView && targetAsignadosView.style.display !== 'none') {
                renderAsignadosMiContent(currentFavoritesData);
            } else {
                renderFavoritesContent();
            }
        } else {
            const errData = await res.json();
            alert("Error al actualizar la próxima reunión: " + (errData.detail || "Error desconocido"));
        }
    } catch (e) {
        console.error(e);
        alert("Error de conexión al actualizar la próxima reunión.");
    }
}

let selectedAsignadosUsuario = null;

async function loadAsignadosMiView() {
    const container = document.getElementById('asignados-mi-container');
    if (!container) return;

    container.innerHTML = `
        <div style="text-align: center; padding: 3rem; color: #64748b; font-family: 'Outfit';">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 1.5rem; margin-bottom: 1rem; display: block; color: var(--primary);"></i>
            Cargando expedientes asignados...
        </div>
    `;

    try {
        await loadFolders();

        const res = await def_fetch(`${API_BASE}/expediente/favoritos`);
        if (!res || !res.ok) {
            throw new Error("No se pudo obtener la lista de expedientes.");
        }

        currentFavoritesData = await res.json();
        userFavorites = new Set(currentFavoritesData.map(f => f.expediente));

        if (!selectedAsignadosUsuario && currentUser) {
            selectedAsignadosUsuario = currentUser.username;
        }

        renderAsignadosMiContent(currentFavoritesData);
    } catch (error) {
        container.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: #ef4444; font-family: 'Outfit'; font-weight: 600;">
                <i class="fa-solid fa-triangle-exclamation" style="font-size: 1.5rem; margin-bottom: 0.75rem; display: block;"></i>
                Error al cargar expedientes asignados: ${error.message}
            </div>
        `;
    }
}

function handleAsignadosUsuarioFilterChange(val) {
    selectedAsignadosUsuario = val;
    renderAsignadosMiContent(currentFavoritesData);
}
window.handleAsignadosUsuarioFilterChange = handleAsignadosUsuarioFilterChange;

function renderAsignadosMiContent(data) {
    const container = document.getElementById('asignados-mi-container');
    if (!container) return;

    if (!selectedAsignadosUsuario && currentUser) {
        selectedAsignadosUsuario = currentUser.username;
    }

    // Populate dropdown dynamically
    const selectEl = document.getElementById('filter-asignados-usuario');
    if (selectEl) {
        const uniqueUsers = [...new Set(data.map(r => r.ficha_responsable).filter(Boolean))];
        if (currentUser && !uniqueUsers.includes(currentUser.username)) {
            uniqueUsers.push(currentUser.username);
        }
        uniqueUsers.sort();

        let optionsHtml = `<option value="all" ${selectedAsignadosUsuario === 'all' ? 'selected' : ''}>[Todos]</option>`;
        uniqueUsers.forEach(u => {
            optionsHtml += `<option value="${u}" ${selectedAsignadosUsuario === u ? 'selected' : ''}>${u === currentUser?.username ? `${u} (Yo)` : u}</option>`;
        });
        selectEl.innerHTML = optionsHtml;
    }

    // Update Title & Subtitle in DOM
    const titleEl = document.getElementById('asignados-mi-title');
    const subtitleEl = document.getElementById('asignados-mi-subtitle');
    if (titleEl && subtitleEl) {
        if (selectedAsignadosUsuario === 'all') {
            titleEl.innerText = "Todos los Expedientes Asignados";
            subtitleEl.innerText = "Todos los expedientes con responsable de ficha asignado.";
        } else if (selectedAsignadosUsuario === currentUser?.username) {
            titleEl.innerText = "Expedientes Asignados a Mí";
            subtitleEl.innerText = "Expedientes en los cuales figurás como responsable de ficha.";
        } else {
            titleEl.innerText = `Expedientes Asignados a ${selectedAsignadosUsuario}`;
            subtitleEl.innerText = `Expedientes en los cuales ${selectedAsignadosUsuario} figura como responsable de ficha.`;
        }
    }

    const filteredData = selectedAsignadosUsuario === 'all'
        ? data
        : data.filter(r => r.ficha_responsable === selectedAsignadosUsuario);

    const headerAssignedToMeHTML = `
        <tr>
            <th style="padding: 8px 10px; text-align: center; font-size: 0.72rem; width: 40px;">★</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Expediente</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Trámite</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Área</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Ubicación</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Analista</th>
            <th style="padding: 8px 6px; text-align: left; font-size: 0.72rem; width: 60px; line-height: 1.2;">Días<br>Tram.</th>
            <th style="padding: 8px 6px; text-align: left; font-size: 0.72rem; width: 60px; line-height: 1.2;">Días<br>Subs.</th>
            <th style="padding: 8px 6px; text-align: left; font-size: 0.72rem; width: 55px; line-height: 1.2;">Cant.<br>Subs.</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Días Stock</th>
            <th style="padding: 8px 10px; text-align: left; font-size: 0.72rem;">Último Pase</th>
            <th style="padding: 8px 10px; text-align: center; font-size: 0.72rem; width: 110px;">Próx. Reunión</th>
            <th style="padding: 8px 10px; text-align: center; font-size: 0.72rem; width: 60px;">Notas</th>
            <th style="padding: 8px 10px; text-align: center; font-size: 0.72rem; width: 120px;">Carpeta</th>
        </tr>
    `;

    function getRowHTML(r) {
        let badgeClass = 'badge-status-flujo';
        if (r.ubicacion === 'STOCK PROPIO' || r.ubicacion === 'STOCK PROPIO (INTERVENCION)') {
            badgeClass = 'badge-status-propio';
        } else if (r.ubicacion === 'SUBSANACION' || r.ubicacion === 'SUBSANACION (INTERVENCION)') {
            badgeClass = 'badge-status-subs';
        } else if (r.ubicacion.startsWith('EGRESADO')) {
            badgeClass = 'badge-status-egresado';
        }

        const cleanGerencia = r.gerencia ? (r.gerencia.toLowerCase() === 'aph' ? 'APH' : r.gerencia.charAt(0).toUpperCase() + r.gerencia.slice(1).replace('_', ' ')) : '-';

        let folderOptionsHtml = `<option value="null" ${r.folder_id === null ? 'selected' : ''}>General</option>`;
        userFavoriteFolders.forEach(folder => {
            folderOptionsHtml += `<option value="${folder.id}" ${r.folder_id == folder.id ? 'selected' : ''}>${folder.name}</option>`;
        });

        // La estrella es no-clickeable por estar asignado
        const starCell = `<span title="Asignado a ${r.ficha_responsable || 'alguien'} — no puede quitarse desde aquí" style="font-size: 1.1rem; color: #f59e0b; cursor: not-allowed; display: inline-block;"><i class="fa-solid fa-user-lock" style="font-size: 0.9rem; color: #f59e0b;"></i></span>`;

        return `
            <tr>
                <td style="padding: 8px 10px; text-align: center; vertical-align: middle;">
                    ${starCell}
                </td>
                <td style="padding: 8px 10px; font-weight: 700; color: #334155; font-family: inherit; white-space: nowrap;">
                    <span onclick="openDetalleExpedienteModal('${r.expediente}')" style="cursor: pointer; color: #1e293b; font-weight: 700; transition: color 0.15s, border-color 0.15s; border-bottom: 1px dashed #cbd5e1; padding-bottom: 1px;" onmouseover="this.style.color='var(--primary)'; this.style.borderColor='var(--primary)';" onmouseout="this.style.color='#1e293b'; this.style.borderColor='#cbd5e1';">${r.expediente}</span>
                    <span onclick="copyToClipboard('${r.expediente}', this)" style="cursor: pointer; margin-left: 6px; font-size: 0.8rem; color: #94a3b8; transition: color 0.2s; display: inline-block; vertical-align: middle;" onmouseover="this.style.color='var(--primary)'" onmouseout="this.style.color='#94a3b8'" title="Copiar Expediente">
                        <i class="fa-regular fa-copy"></i>
                    </span>
                </td>
                <td style="padding: 8px 10px; font-weight: 600; font-size: 0.82rem;">${r.descripcion_trata || r.trata || ''}</td>
                <td style="padding: 8px 10px; font-weight: 600; font-size: 0.82rem;">${cleanGerencia}</td>
                <td style="padding: 8px 10px;"><span class="badge-status ${badgeClass}" style="font-size: 0.75rem;">${r.ubicacion}</span></td>
                <td style="padding: 8px 10px; font-weight: 600; color: #475569; font-size: 0.82rem;">${r.analista || 'SIN ASIGNAR'}</td>
                <td style="padding: 8px 6px; font-weight: 600; color: #475569; font-size: 0.82rem;">${r.dias_tramitacion ?? 0}d</td>
                <td style="padding: 8px 6px; font-weight: 600; color: #475569; font-size: 0.82rem;">${r.dias_subsanacion ?? 0}d</td>
                <td style="padding: 8px 6px; font-weight: 600; color: #475569; font-size: 0.82rem;">${r.cant_subsanaciones ?? 0}</td>
                <td style="padding: 8px 10px; font-weight: 600; color: #475569; font-size: 0.82rem;">${r.dias_stock ?? 0}d</td>
                <td style="padding: 8px 10px; font-size: 0.78rem; color: #64748b;">
                    <div>${r.fecha_ultimo_pase || '-'}</div>
                    <div style="font-size: 0.72rem; color: #94a3b8; margin-top: 2px;">Creado: ${r.fecha_creacion || '-'}</div>
                </td>
                <td style="padding: 8px 10px; text-align: center; vertical-align: middle;">
                    <select onchange="updateFichaProximaReunion('${r.expediente}', this.value)" style="padding: 3px 6px; border-radius: 6px; border: 1px solid #cbd5e1; outline: none; font-size: 0.76rem; font-family: 'Outfit'; cursor: pointer; background: ${r.ficha_proxima_reunion ? '#dcfce7' : '#f1f5f9'}; color: ${r.ficha_proxima_reunion ? '#15803d' : '#475569'}; font-weight: 600;">
                        <option value="si" ${r.ficha_proxima_reunion ? 'selected' : ''}>Sí</option>
                        <option value="no" ${!r.ficha_proxima_reunion ? 'selected' : ''}>No</option>
                    </select>
                </td>
                <td style="padding: 8px 10px; text-align: center; vertical-align: middle;">
                    <button onclick="openFavoriteNotesModal('${r.expediente}')" style="background: none; border: none; cursor: pointer; position: relative; padding: 4px 6px; display: inline-flex; align-items: center; justify-content: center; transition: all 0.2s;" title="Ver/Agregar Anotaciones" onmouseover="this.style.transform='scale(1.15)'" onmouseout="this.style.transform='scale(1)'">
                        <i class="fa-regular fa-comment-dots" style="font-size: 1.1rem; color: ${r.cant_notas > 0 ? 'var(--primary)' : '#94a3b8'};"></i>
                        ${r.cant_notas > 0 ? `<span style="position: absolute; top: -4px; right: -4px; background: #ef4444; color: white; font-size: 0.65rem; font-weight: 700; border-radius: 50%; width: 15px; height: 15px; display: flex; align-items: center; justify-content: center; border: 2px solid white;">${r.cant_notas}</span>` : ''}
                    </button>
                </td>
                <td style="padding: 8px 10px; text-align: center; vertical-align: middle;">
                    <select onchange="moveFavoriteToFolder('${r.expediente}', this.value)" style="padding: 3px 6px; border-radius: 6px; border: 1px solid #cbd5e1; outline: none; font-size: 0.76rem; font-family: 'Outfit'; cursor: pointer; max-width: 115px;">
                        ${folderOptionsHtml}
                    </select>
                </td>
            </tr>
        `;
    }

    container.innerHTML = `
        ${filteredData.length === 0 ? `
            <div style="text-align: center; padding: 3rem; background: white; border-radius: 16px; border: 2px dashed #c7d2fe; color: #6366f1; font-family: 'Outfit';">
                <i class="fa-regular fa-user" style="font-size: 3rem; display: block; margin-bottom: 1rem; opacity: 0.5;"></i>
                <h3 style="margin: 0; font-family: 'Outfit';">No hay expedientes asignados</h3>
                <p style="color: #94a3b8; margin: 0.5rem 0 0 0; font-family: 'Outfit';">No se encontraron expedientes asignados para el filtro seleccionado.</p>
            </div>
        ` : `
            <div style="background: white; border-radius: 16px; border: 2px solid #e0e7ff; box-shadow: 0 4px 16px rgba(99,102,241,0.08); padding: 1.5rem;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1.25rem; padding-bottom: 0.9rem; border-bottom: 1px solid #e0e7ff;">
                    <div style="width: 36px; height: 36px; background: linear-gradient(135deg, #6366f1, #818cf8); border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        <i class="fa-solid fa-user-check" style="color: white; font-size: 0.9rem;"></i>
                    </div>
                    <div>
                        <h4 style="color: #4338ca; font-family: 'Outfit'; font-weight: 700; margin: 0; font-size: 1.05rem;">
                            ${selectedAsignadosUsuario === 'all' ? 'Todos los Expedientes Asignados' : (selectedAsignadosUsuario === currentUser?.username ? 'Expedientes Asignados a Mí' : `Expedientes Asignados a ${selectedAsignadosUsuario}`)}
                        </h4>
                        <span style="font-size: 0.8rem; color: #6366f1; font-family: 'Outfit';">${filteredData.length} expediente${filteredData.length !== 1 ? 's' : ''}</span>
                    </div>
                </div>
                <div style="overflow-x: auto; width: 100%;">
                    <table class="matrix-table" style="margin-top: 0; width: 100%;">
                        <thead>
                            ${headerAssignedToMeHTML}
                        </thead>
                        <tbody>
                            ${filteredData.map(r => getRowHTML(r)).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `}
    `;
}

function openCreateFolderModal() {
    document.getElementById('folder-name-input').value = '';
    document.getElementById('create-folder-modal').style.display = 'flex';
}

async function handleCreateFolderSubmit(event) {
    event.preventDefault();
    const folderName = document.getElementById('folder-name-input').value.trim();
    if (!folderName) return;
    
    try {
        const res = await def_fetch(`${API_BASE}/expediente/favoritos/carpetas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: folderName })
        });
        if (res && res.ok) {
            closeModal('create-folder-modal');
            await loadFavoritesView();
        } else {
            alert("Error al crear carpeta.");
        }
    } catch (e) {
        console.error(e);
        alert("Error de conexión al crear carpeta.");
    }
}

async function deleteFolder(folderId) {
    if (!confirm("¿Estás seguro de que deseas eliminar esta carpeta? Los expedientes marcados no se borrarán, sino que volverán a la carpeta General.")) return;
    
    try {
        const res = await def_fetch(`${API_BASE}/expediente/favoritos/carpetas/${folderId}`, {
            method: 'DELETE'
        });
        if (res && res.ok) {
            if (currentSelectedFolderId == folderId) {
                currentSelectedFolderId = 'all';
            }
            await loadFavoritesView();
        } else {
            alert("Error al eliminar carpeta.");
        }
    } catch (e) {
        console.error(e);
    }
}

async function moveFavoriteToFolder(expediente, folderIdVal) {
    const folderId = folderIdVal === 'null' ? null : parseInt(folderIdVal);
    
    try {
        const res = await def_fetch(`${API_BASE}/expediente/favorito/mover`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ expediente, folder_id: folderId })
        });
        if (res && res.ok) {
            const fav = currentFavoritesData.find(f => f.expediente === expediente);
            if (fav) fav.folder_id = folderId;
            
            await loadFolders();
            const targetAsignadosView = document.getElementById('asignados-mi');
            if (targetAsignadosView && targetAsignadosView.style.display !== 'none') {
                renderAsignadosMiContent(currentFavoritesData);
            } else {
                renderFavoritesContent();
            }
        } else {
            alert("Error al mover el expediente.");
        }
    } catch (e) {
        console.error(e);
    }
}

let currentNotesExpediente = null;

async function openFavoriteNotesModal(expediente) {
    currentNotesExpediente = expediente;
    document.getElementById('notes-modal-expediente').innerText = expediente;
    document.getElementById('note-text-input').value = '';
    
    const listContainer = document.getElementById('notes-list-container');
    listContainer.innerHTML = '<div style="text-align: center; color: #64748b; padding: 1.5rem;"><i class="fa-solid fa-circle-notch fa-spin"></i> Cargando anotaciones...</div>';
    
    document.getElementById('favorite-notes-modal').style.display = 'flex';
    
    await loadFavoriteNotesList(expediente);
}

async function loadFavoriteNotesList(expediente) {
    const listContainer = document.getElementById('notes-list-container');
    try {
        const res = await def_fetch(`${API_BASE}/expediente/favorito/${encodeURIComponent(expediente)}/notas`);
        if (!res || !res.ok) {
            throw new Error("Error al obtener notas.");
        }
        const notes = await res.json();

        if (notes.length === 0) {
            listContainer.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: #94a3b8; font-family: 'Outfit';">
                    <i class="fa-regular fa-comment" style="font-size: 2.5rem; margin-bottom: 0.75rem; display: block; color: #cbd5e1;"></i>
                    No hay anotaciones para este expediente aún.
                </div>
            `;
            return;
        }

    let html = '';
    notes.forEach(note => {
        let formattedDate = note.created_at;
        try {
            const dt = new Date(note.created_at.replace(' ', 'T'));
            if (!isNaN(dt.getTime())) {
                const day = String(dt.getDate()).padStart(2, '0');
                const month = String(dt.getMonth() + 1).padStart(2, '0');
                const year = dt.getFullYear();
                const hours = String(dt.getHours()).padStart(2, '0');
                const minutes = String(dt.getMinutes()).padStart(2, '0');
                formattedDate = `${day}/${month}/${year} ${hours}:${minutes}`;
            }
        } catch (e) {
            console.error("Error formatting date:", e);
        }

        html += `
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; transition: transform 0.2s;">
                    <div style="flex-grow: 1; min-width: 0;">
                        <p style="margin: 0; font-size: 0.88rem; color: #334155; font-family: 'Outfit'; font-weight: 500; line-height: 1.4; word-break: break-word; white-space: pre-line;">${note.note_text}</p>
                        <span style="font-size: 0.72rem; color: #94a3b8; display: block; margin-top: 6px; font-weight: 600; font-family: 'Outfit';">
                            <i class="fa-regular fa-user" style="margin-right: 4px;"></i>${note.author_name} (${note.author_sector}) &nbsp;•&nbsp; <i class="fa-regular fa-clock" style="margin-right: 4px; margin-left: 2px;"></i>${formattedDate}
                        </span>
                    </div>
                    ${note.is_owner ? `
                    <button onclick="deleteFavoriteNote(${note.id})" style="background: none; border: none; color: #94a3b8; cursor: pointer; padding: 4px; border-radius: 4px; display: inline-flex; align-items: center; justify-content: center; transition: all 0.2s;" onmouseover="this.style.color='#ef4444'; this.style.background='#fee2e2';" onmouseout="this.style.color='#94a3b8'; this.style.background='none';" title="Eliminar Anotación">
                        <i class="fa-regular fa-trash-can" style="font-size: 0.95rem;"></i>
                    </button>
                    ` : ''}
                </div>
            `;
    });
    listContainer.innerHTML = html;
} catch (error) {
    listContainer.innerHTML = `<div style="text-align: center; color: #ef4444; padding: 1.5rem; font-weight: 600;">Error: ${error.message}</div>`;
}
}

async function handleAddNoteSubmit(event) {
    event.preventDefault();
    if (!currentNotesExpediente) return;

    const noteTextInput = document.getElementById('note-text-input');
    const noteText = noteTextInput.value.trim();
    if (!noteText) return;

    try {
        const res = await def_fetch(`${API_BASE}/expediente/favorito/${encodeURIComponent(currentNotesExpediente)}/notas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ note_text: noteText })
        });
        if (res && res.ok) {
            noteTextInput.value = '';
            await loadFavoriteNotesList(currentNotesExpediente);
            await reloadFavoritesSilent();
        } else {
            const errData = await res.json();
            alert(errData.detail || "Error al guardar la nota.");
        }
    } catch (e) {
        console.error(e);
        alert("Error al conectar con el servidor.");
    }
}

async function deleteFavoriteNote(noteId) {
    if (!confirm("¿Estás seguro de que deseas eliminar esta anotación?")) return;

    try {
        const res = await def_fetch(`${API_BASE}/expediente/favorito/notas/${noteId}`, {
            method: 'DELETE'
        });
        if (res && res.ok) {
            await loadFavoriteNotesList(currentNotesExpediente);
            await reloadFavoritesSilent();
        } else {
            alert("Error al eliminar la nota.");
        }
    } catch (e) {
        console.error(e);
    }
}

async function reloadFavoritesSilent() {
    try {
        const res = await def_fetch(`${API_BASE}/expediente/favoritos`);
        if (res && res.ok) {
            currentFavoritesData = await res.json();
            userFavorites = new Set(currentFavoritesData.map(f => f.expediente));
            const targetAsignadosView = document.getElementById('asignados-mi');
            if (targetAsignadosView && targetAsignadosView.style.display !== 'none') {
                renderAsignadosMiContent(currentFavoritesData);
            } else {
                renderFavoritesContent();
            }
        }
    } catch (e) {
        console.error("Error reloading favorites silently:", e);
    }
}

window.openCreateFolderModal = openCreateFolderModal;
window.handleCreateFolderSubmit = handleCreateFolderSubmit;
window.deleteFolder = deleteFolder;
window.moveFavoriteToFolder = moveFavoriteToFolder;
window.selectFolder = selectFolder;
window.openFavoriteNotesModal = openFavoriteNotesModal;
window.handleAddNoteSubmit = handleAddNoteSubmit;
window.deleteFavoriteNote = deleteFavoriteNote;
window.updateFichaProximaReunion = updateFichaProximaReunion;

window.loadFavoritesView = loadFavoritesView;
window.loadAsignadosMiView = loadAsignadosMiView;

let currentSubsanacionesData = [];
let currentSelectedSubTrata = null;
let currentSelectedSubAnalyst = null;
let currentSubsanacionesExpedientesData = [];

async function loadSubsanacionesReport() {
    // Force main view when reloading report data
    showSubsanacionesMainView();

    const container = document.getElementById('subsanaciones-grid-container');
    if (!container) return;

    container.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 3rem; text-align: center;">
            <div class="loader" style="margin: 0 auto 1.5rem auto;"></div>
            <h3 style="color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700;">Cargando Reporte de Subsanaciones...</h3>
            <p style="color: #64748b;">Esto puede tardar unos segundos mientras consultamos el histórico.</p>
        </div>
    `;

    const gerencia = document.getElementById('subsanaciones-filter-gerencia')?.value || 'ALL';
    try {
        const res = await def_fetch(`${API_BASE}/reporte/subsanaciones?gerencia=${gerencia}`);
        if (!res || !res.ok) {
            throw new Error("Error en la respuesta del servidor");
        }
        currentSubsanacionesData = await res.json();
        filterAndRenderSubsanaciones();
    } catch (e) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; padding: 3rem; text-align: center; color: #ef4444; font-weight: 600;">
                Error al cargar el reporte de subsanaciones: ${e.message}
                <br>
                <button class="btn-primary" style="margin-top: 1.5rem; padding: 8px 16px;" onclick="loadSubsanacionesReport()">Reintentar Carga</button>
            </div>
        `;
    }
}

function filterAndRenderSubsanaciones() {
    const searchVal = document.getElementById('subsanaciones-search')?.value.toLowerCase() || '';
    const sortVal = document.getElementById('subsanaciones-sort')?.value || 'COUNT_DESC';
    const container = document.getElementById('subsanaciones-grid-container');
    if (!container) return;

    const GERENCIA_LABELS = {
        catastro: "Catastro (DGROC)",
        instalaciones: "Instalaciones (DGROC)",
        regularizacion: "Regularización y Conforme (DGROC)",
        contable: "Contable (DGROC)",
        etapa_proyecto: "Etapa Proyecto (DGROC)",
        aviso_obra: "Aviso de Obra (DGROC)",
        morfologia: "Morfología Urbana (DGIUR)",
        aph: "Protección Histórica APH (DGIUR)",
        usos: "Usos del Suelo (DGIUR)"
    };

    // Filter
    let filtered = currentSubsanacionesData.filter(d => {
        const matchesSearch = d.trata.toLowerCase().includes(searchVal) ||
            (d.descripcion_trata || '').toLowerCase().includes(searchVal);
        return matchesSearch;
    });

    // Sort
    filtered.sort((a, b) => {
        if (sortVal === 'COUNT_DESC') {
            return b.total_expedientes - a.total_expedientes;
        } else if (sortVal === 'QTY_DESC') {
            return b.mediana_cant - a.mediana_cant;
        } else if (sortVal === 'TIME_DESC') {
            return b.mediana_dias - a.mediana_dias;
        } else if (sortVal === 'NAME_ASC') {
            return (a.descripcion_trata || '').localeCompare(b.descripcion_trata || '');
        }
        return 0;
    });

    if (filtered.length === 0) {
        container.innerHTML = `
            <div style="padding: 3rem; text-align: center; color: #64748b; background: white; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: var(--card-shadow);">
                No se encontraron trámites con subsanaciones que coincidan con la búsqueda.
            </div>
        `;
        return;
    }

    // Group by gerencia
    const groups = {};
    filtered.forEach(d => {
        const gKey = d.gerencia ? d.gerencia.toLowerCase() : 'otros';
        if (!groups[gKey]) {
            groups[gKey] = [];
        }
        groups[gKey].push(d);
    });

    container.innerHTML = '';

    // Render groups
    Object.keys(groups).forEach(gKey => {
        const groupItems = groups[gKey];
        const gLabel = GERENCIA_LABELS[gKey] || gKey.toUpperCase().replace('_', ' ');

        const groupDiv = document.createElement('div');
        groupDiv.className = 'subsanaciones-group-container';
        groupDiv.style.background = 'white';
        groupDiv.style.borderRadius = '16px';
        groupDiv.style.border = '1px solid #e2e8f0';
        groupDiv.style.boxShadow = 'var(--card-shadow)';
        groupDiv.style.overflow = 'hidden';

        // Header
        const headerDiv = document.createElement('div');
        headerDiv.className = 'subsanaciones-group-header';
        headerDiv.style.display = 'flex';
        headerDiv.style.justify = 'space-between';
        headerDiv.style.alignItems = 'center';
        headerDiv.style.padding = '14px 20px';
        headerDiv.style.background = '#f8fafc';
        headerDiv.style.cursor = 'pointer';
        headerDiv.style.userSelect = 'none';
        headerDiv.style.borderBottom = '1px solid #e2e8f0';
        headerDiv.onclick = () => toggleSubsanacionesGroup(gKey);

        headerDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px;">
                <span id="sub-chevron-${gKey}" style="font-size: 0.9rem; color: #64748b; transition: transform 0.2s;"><i class="fa-solid fa-chevron-down"></i></span>
                <span style="font-size: 1rem; font-weight: 700; color: var(--primary-dark); font-family: 'Outfit'; text-transform: uppercase;">${gLabel}</span>
            </div>
            <span class="badge-status-propio" style="font-size: 0.8rem; padding: 4px 10px; border-radius: 12px; font-weight: 700; background: #e0f2fe; color: #0369a1;">${groupItems.length} Trámite${groupItems.length !== 1 ? 's' : ''}</span>
        `;
        groupDiv.appendChild(headerDiv);

        // Content (Table)
        const contentDiv = document.createElement('div');
        contentDiv.id = `sub-content-${gKey}`;
        contentDiv.className = 'subsanaciones-group-content';
        contentDiv.style.display = 'block';
        contentDiv.style.overflowX = 'auto';

        let rowsHtml = '';
        groupItems.forEach(d => {
            rowsHtml += `
                <tr style="cursor: pointer; transition: background-color 0.15s ease;" 
                    onclick="showTrataSubsanacionesDetail('${d.trata}')"
                    onmouseover="this.style.backgroundColor='#f8fafc'" 
                    onmouseout="this.style.backgroundColor=''">
                    <td style="padding: 12px 16px; font-weight: 700; color: var(--primary-dark); font-family: 'Outfit'; font-size: 0.88rem;">${d.trata}</td>
                    <td style="padding: 12px 16px; font-weight: 600; color: #475569; font-family: 'Outfit'; font-size: 0.85rem;">${d.descripcion_trata}</td>
                    <td style="padding: 12px 16px; text-align: center; font-weight: 700; color: #1e293b; font-family: 'Outfit'; font-size: 0.88rem;">${d.total_expedientes}</td>
                    <td style="padding: 12px 16px; text-align: center; font-weight: 700; color: var(--primary); font-family: 'Outfit'; font-size: 0.88rem;">${d.mediana_cant.toFixed(1)}</td>
                    <td style="padding: 12px 16px; text-align: center; font-weight: 700; color: #6366f1; font-family: 'Outfit'; font-size: 0.88rem;">${d.mediana_dias.toFixed(1)}d</td>
                    <td style="padding: 12px 16px; text-align: center; vertical-align: middle;">
                        <button class="btn-primary" style="padding: 6px 12px; font-size: 0.78rem; border-radius: 6px; font-family: 'Outfit'; font-weight: 700; background: var(--primary); border: none; color: white; cursor: pointer;">
                            Ver Analistas <i class="fa-solid fa-arrow-right" style="margin-left: 4px;"></i>
                        </button>
                    </td>
                </tr>
            `;
        });

        contentDiv.innerHTML = `
            <table class="matrix-table" style="margin-top: 0; width: 100%; border: none; border-radius: 0; box-shadow: none;">
                <thead>
                    <tr>
                        <th style="padding: 12px 16px; text-align: left; font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase;">Trámite (Trata)</th>
                        <th style="padding: 12px 16px; text-align: left; font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase;">Descripción Trámite</th>
                        <th style="padding: 12px 16px; text-align: center; font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase; width: 130px;">Expedientes</th>
                        <th style="padding: 12px 16px; text-align: center; font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase; width: 140px;">Med. Cantidad</th>
                        <th style="padding: 12px 16px; text-align: center; font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase; width: 120px;">Med. Días</th>
                        <th style="padding: 12px 16px; text-align: center; font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase; width: 150px;">Acción</th>
                    </tr>
                </thead>
                <tbody>
                    ${rowsHtml}
                </tbody>
            </table>
        `;
        groupDiv.appendChild(contentDiv);
        container.appendChild(groupDiv);
    });

    // Premium micro-animation
    gsap.from('#subsanaciones-grid-container .subsanaciones-group-container', {
        opacity: 0,
        y: 15,
        duration: 0.4,
        stagger: 0.05,
        ease: "power2.out"
    });
}

function toggleSubsanacionesGroup(gKey) {
    const content = document.getElementById(`sub-content-${gKey}`);
    const chevron = document.getElementById(`sub-chevron-${gKey}`);
    if (!content || !chevron) return;

    if (content.style.display === 'none') {
        content.style.display = 'block';
        chevron.style.transform = 'rotate(0deg)';
    } else {
        content.style.display = 'none';
        chevron.style.transform = 'rotate(-90deg)';
    }
}
window.toggleSubsanacionesGroup = toggleSubsanacionesGroup;

function showSubsanacionesMainView() {
    document.getElementById('subsanaciones-main-container').style.display = 'block';
    document.getElementById('subsanaciones-detail-container').style.display = 'none';
    document.getElementById('subsanaciones-expedientes-container').style.display = 'none';

    // Reset headers
    document.getElementById('subsanaciones-title').innerText = "Reporte de Subsanaciones";
    document.getElementById('subsanaciones-subtitle').innerText = "Mediana de cantidad de subsanaciones y tiempo de resolución de subsanación por trámite y analista.";

    // Reset breadcrumbs
    document.getElementById('subsanaciones-breadcrumbs').innerHTML = `
        <span onclick="showSubsanacionesMainView()" style="cursor: pointer; text-decoration: underline;">Inicio</span> / Reporte de Subsanaciones
    `;
}

function showTrataSubsanacionesDetail(trataId) {
    const data = currentSubsanacionesData.find(d => d.trata === trataId);
    if (!data) return;

    currentSelectedSubTrata = data;

    // Set Header Info
    document.getElementById('sub-trata-title').innerText = data.trata;
    document.getElementById('sub-trata-desc').innerText = data.descripcion_trata;
    document.getElementById('sub-trata-total').innerText = data.total_expedientes;
    document.getElementById('sub-trata-mediana-cant').innerText = data.mediana_cant.toFixed(1);
    document.getElementById('sub-trata-mediana-dias').innerText = data.mediana_dias.toFixed(1) + "d";

    // Build Analyst Cards
    const analystsGrid = document.getElementById('subsanaciones-analysts-grid');
    analystsGrid.innerHTML = '';

    if (data.analistas && data.analistas.length > 0) {
        // Sort analysts by total_expedientes desc
        const sortedAnalysts = [...data.analistas].sort((x, y) => y.total_expedientes - x.total_expedientes);
        sortedAnalysts.forEach(an => {
            const card = document.createElement('div');
            card.className = 'analyst-card-premium';
            card.style.cursor = 'pointer';
            card.onclick = () => showAnalystSubsanacionesDetail(an.analista, an.nombre, an.sector, an.total_expedientes, an.mediana_cant, an.mediana_dias);

            const displayName = an.nombre || an.analista;
            const initial = displayName ? displayName.trim().charAt(0).toUpperCase() : '?';

            card.innerHTML = `
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div class="analyst-avatar-initial">${initial}</div>
                            <div>
                                <span style="font-size: 1.05rem; font-weight: 800; color: var(--primary-dark); font-family: 'Outfit'; display: block; line-height: 1.25;">${displayName}</span>
                                <span style="font-size: 0.72rem; color: #64748b; font-weight: 600;">SADE: ${an.analista}</span>
                            </div>
                        </div>
                        <span style="font-size: 0.65rem; font-weight: 700; color: #4f46e5; background: #e0e7ff; padding: 3px 8px; border-radius: 6px; text-transform: uppercase;">${an.sector || 'Analista'}</span>
                    </div>
                    
                    <div class="subsanaciones-metric-grid" style="margin-bottom: 1rem;">
                        <div class="subsanaciones-metric-item">
                            <span class="subsanaciones-metric-label">Expedientes</span>
                            <span class="subsanaciones-metric-val" style="font-size: 1.05rem;">${an.total_expedientes}</span>
                        </div>
                        <div class="subsanaciones-metric-item">
                            <span class="subsanaciones-metric-label">Med. Cant.</span>
                            <span class="subsanaciones-metric-val" style="font-size: 1.05rem; color: var(--primary);">${an.mediana_cant.toFixed(1)}</span>
                        </div>
                        <div class="subsanaciones-metric-item">
                            <span class="subsanaciones-metric-label">Med. Días</span>
                            <span class="subsanaciones-metric-val" style="font-size: 1.05rem; color: #6366f1;">${an.mediana_dias.toFixed(1)}d</span>
                        </div>
                    </div>
                </div>

                <button class="analyst-card-btn" style="width: 100%;">
                    <span>Ver Expedientes</span>
                    <span>→</span>
                </button>
            `;
            analystsGrid.appendChild(card);
        });
    } else {
        analystsGrid.innerHTML = `
            <div style="grid-column: 1 / -1; padding: 2rem; text-align: center; color: #64748b; font-style: italic;">
                No se registraron analistas para este trámite.
            </div>
        `;
    }

    // Toggle Views
    document.getElementById('subsanaciones-main-container').style.display = 'none';
    const detailContainer = document.getElementById('subsanaciones-detail-container');
    detailContainer.style.display = 'block';
    document.getElementById('subsanaciones-expedientes-container').style.display = 'none';

    // Premium micro-animations for detail view
    gsap.from(detailContainer, { opacity: 0, y: 15, duration: 0.35, ease: "power2.out" });
    gsap.from('#subsanaciones-analysts-grid .analyst-card-premium', {
        opacity: 0,
        y: 15,
        duration: 0.4,
        stagger: 0.04,
        ease: "power2.out"
    });

    // Update breadcrumbs
    document.getElementById('subsanaciones-breadcrumbs').innerHTML = `
        <span onclick="showSubsanacionesMainView()" style="cursor: pointer; text-decoration: underline;">Inicio</span> / 
        <span onclick="showSubsanacionesMainView()" style="cursor: pointer; text-decoration: underline;">Reporte de Subsanaciones</span> / 
        ${data.trata}
    `;
}

async function showAnalystSubsanacionesDetail(analistaUser, analistaName, sectorName, totalExp, medianaCant, medianaDias) {
    currentSelectedSubAnalyst = analistaUser;

    // Set Header Info
    document.getElementById('sub-analyst-title').innerText = `Analista: ${analistaName || analistaUser}`;
    document.getElementById('sub-analyst-subtitle').innerText = `${currentSelectedSubTrata.trata} - ${currentSelectedSubTrata.descripcion_trata} | Sector: ${sectorName || '-'}`;
    document.getElementById('sub-analyst-total').innerText = totalExp;
    document.getElementById('sub-analyst-mediana-cant').innerText = medianaCant.toFixed(1);
    document.getElementById('sub-analyst-mediana-dias').innerText = medianaDias.toFixed(1) + "d";

    const tbody = document.getElementById('subsanaciones-expedientes-tbody');
    tbody.innerHTML = `
        <tr>
            <td colspan="6" style="text-align: center; padding: 3rem;">
                <div class="loader" style="margin: 0 auto 1.5rem auto;"></div>
                <span style="font-weight: 600; color: #64748b;">Cargando listado de expedientes...</span>
            </td>
        </tr>
    `;

    // Toggle Views
    document.getElementById('subsanaciones-main-container').style.display = 'none';
    document.getElementById('subsanaciones-detail-container').style.display = 'none';
    const expContainer = document.getElementById('subsanaciones-expedientes-container');
    expContainer.style.display = 'block';
    gsap.from(expContainer, { opacity: 0, y: 15, duration: 0.35, ease: "power2.out" });

    // Update breadcrumbs
    document.getElementById('subsanaciones-breadcrumbs').innerHTML = `
        <span onclick="showSubsanacionesMainView()" style="cursor: pointer; text-decoration: underline;">Inicio</span> / 
        <span onclick="showSubsanacionesMainView()" style="cursor: pointer; text-decoration: underline;">Reporte de Subsanaciones</span> / 
        <span onclick="backToTrataDetail()" style="cursor: pointer; text-decoration: underline;">${currentSelectedSubTrata.trata}</span> / 
        ${analistaName || analistaUser}
    `;

    try {
        const url = `${API_BASE}/reporte/subsanaciones/expedientes?gerencia=${currentSelectedSubTrata.gerencia}&trata=${currentSelectedSubTrata.trata}&analista=${analistaUser}`;
        const res = await def_fetch(url);
        if (!res || !res.ok) throw new Error("Error obteniendo expedientes");

        currentSubsanacionesExpedientesData = await res.json();

        tbody.innerHTML = '';
        if (currentSubsanacionesExpedientesData.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 2rem; color: #64748b; font-style: italic;">
                        No se encontraron expedientes subsanados para este analista.
                    </td>
                </tr>
            `;
            return;
        }

        currentSubsanacionesExpedientesData.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="padding: 12px 16px; font-weight: 700; color: #334155;">${r.expediente}</td>
                <td style="padding: 12px 16px; font-weight: 600;">${r.descripcion_trata}</td>
                <td style="padding: 12px 16px; font-weight: 800; text-align: center; color: var(--primary);">${r.cant_subsanaciones}</td>
                <td style="padding: 12px 16px; font-weight: 800; text-align: center; color: #6366f1;">${r.dias_subsanacion}d</td>
                <td style="padding: 12px 16px; font-weight: 600; color: #475569;">${r.analista}</td>
                <td style="padding: 12px 16px; color: #64748b;">${r.fecha_creacion || '-'}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 2rem; color: #ef4444; font-weight: 600;">
                    Error al cargar listado: ${err.message}
                </td>
            </tr>
        `;
    }
}

function backToTrataDetail() {
    if (currentSelectedSubTrata) {
        showTrataSubsanacionesDetail(currentSelectedSubTrata.trata);
    } else {
        showSubsanacionesMainView();
    }
}

function exportSubsanacionesExpedientesExcel() {
    if (!currentSubsanacionesExpedientesData || currentSubsanacionesExpedientesData.length === 0) {
        alert("No hay datos para exportar");
        return;
    }

    try {
        const worksheet = XLSX.utils.json_to_sheet(currentSubsanacionesExpedientesData.map(r => ({
            "Expediente": r.expediente,
            "Código Trámite": r.trata,
            "Detalle Trámite": r.descripcion_trata,
            "Cantidad de Subsanaciones": r.cant_subsanaciones,
            "Días de Subsanación": r.dias_subsanacion,
            "Analista": r.analista,
            "Fecha Creación": r.fecha_creacion
        })));

        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, "Expedientes");

        const filename = `Subsanaciones_${currentSelectedSubTrata.trata}_${currentSelectedSubAnalyst}.xlsx`;
        XLSX.writeFile(workbook, filename);
    } catch (e) {
        alert("Error exportando a Excel: " + e.message);
    }
}

window.loadSubsanacionesReport = loadSubsanacionesReport;
window.filterAndRenderSubsanaciones = filterAndRenderSubsanaciones;
window.showSubsanacionesMainView = showSubsanacionesMainView;
window.showTrataSubsanacionesDetail = showTrataSubsanacionesDetail;
window.showAnalystSubsanacionesDetail = showAnalystSubsanacionesDetail;
window.backToTrataDetail = backToTrataDetail;
window.exportSubsanacionesExpedientesExcel = exportSubsanacionesExpedientesExcel;

window.toggleUserPermsOverrideUI = toggleUserPermsOverrideUI;
window.toggleRolePermission = toggleRolePermission;
window.deleteRole = deleteRole;

window.showCreateUserView = showCreateUserView;
window.showUsersListView = showUsersListView;
window.showEditUserView = showEditUserView;
window.handleRoleSelectionChange = handleRoleSelectionChange;
window.openEditUser = openEditUser;

window.loadFavoritosSeguimientoView = loadFavoritosSeguimientoView;
window.toggleFavoriteSeguimiento = toggleFavoriteSeguimiento;
window.openFichaModal = openFichaModal;
window.handleFichaSubmit = handleFichaSubmit;
window.filterAndRenderFavoritosSeguimiento = filterAndRenderFavoritosSeguimiento;
window.openDetalleExpedienteModal = openDetalleExpedienteModal;

function showCreateUserView() {
    const list = document.getElementById('users-list-view');
    const create = document.getElementById('users-create-view');
    const edit = document.getElementById('users-edit-view');
    if (list) list.style.display = 'none';
    if (create) {
        create.style.display = 'block';
        // Auto populate permissions checkboxes with default role if not already done
        const newRoleSelect = document.getElementById('new-role');
        if (newRoleSelect && newRoleSelect.value) {
            handleRoleSelectionChange('new', newRoleSelect.value);
        }
    }
    if (edit) edit.style.display = 'none';
}

function showUsersListView() {
    const list = document.getElementById('users-list-view');
    const create = document.getElementById('users-create-view');
    const edit = document.getElementById('users-edit-view');
    if (list) list.style.display = 'block';
    if (create) create.style.display = 'none';
    if (edit) edit.style.display = 'none';
}

function showEditUserView() {
    const list = document.getElementById('users-list-view');
    const create = document.getElementById('users-create-view');
    const edit = document.getElementById('users-edit-view');
    if (list) list.style.display = 'none';
    if (create) create.style.display = 'none';
    if (edit) edit.style.display = 'block';
}

function populatePermsCheckboxes(containerId, permissionsObj) {
    const grid = document.getElementById(containerId);
    if (!grid) return;

    const resolvedPerms = permissionsObj || {};
    let html = '';
    for (const key in PERMISSION_KEYS) {
        const checked = resolvedPerms[key] ? 'checked' : '';
        html += `
            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; font-weight: normal; margin: 2px 0;">
                <input type="checkbox" class="user-perm-checkbox" data-permission="${key}" ${checked}>
                ${PERMISSION_KEYS[key]}
            </label>
        `;
    }
    grid.innerHTML = html;
}

function handleRoleSelectionChange(mode, roleName) {
    const roleObj = allAdminRoles.find(r => r.role_name === roleName);
    const perms = roleObj ? roleObj.permissions : {};
    const containerId = mode === 'new' ? 'new-user-perms-grid' : 'edit-user-perms-grid';
    populatePermsCheckboxes(containerId, perms);
}

async function loadFavoritosSeguimientoView() {
    // Clear search and filter controls
    const searchInput = document.getElementById('fav-seg-search');
    const filterGerencia = document.getElementById('fav-seg-filter-gerencia');
    const filterSade = document.getElementById('fav-seg-filter-sade');
    const filterEstado = document.getElementById('fav-seg-filter-estado');
    const filterPrioridad = document.getElementById('fav-seg-filter-prioridad');
    const filterReunion = document.getElementById('fav-seg-filter-reunion');
    if (searchInput) searchInput.value = '';
    if (filterGerencia) filterGerencia.value = 'ALL';
    if (filterSade) filterSade.value = 'ALL';
    if (filterEstado) filterEstado.value = 'ALL';
    if (filterPrioridad) filterPrioridad.value = 'ALL';
    if (filterReunion) filterReunion.value = 'ALL';

    const tbody = document.getElementById('fav-seg-tbody');
    const container = document.getElementById('fav-seg-container');
    const emptyState = document.getElementById('fav-seg-empty-state');
    if (!tbody || !container || !emptyState) return;

    const table = container.querySelector('table');

    tbody.innerHTML = '<tr><td colspan="12" style="text-align: center; padding: 2rem; color: #64748b;">Cargando marcadores...</td></tr>';
    table.style.display = 'table';
    emptyState.style.display = 'none';

    try {
        const res = await def_fetch(`${API_BASE}/expediente/favoritos`);
        if (!res || !res.ok) {
            throw new Error("No se pudo obtener la lista de marcadores.");
        }

        currentFavoritosSeguimientoData = await res.json();
        userFavorites = new Set(currentFavoritosSeguimientoData.map(f => f.expediente));

        renderFavoritosSeguimientoContent(currentFavoritosSeguimientoData);
    } catch (error) {
        tbody.innerHTML = `
            <tr>
                <td colspan="12" style="text-align: center; padding: 2rem; color: #ef4444; font-weight: 600;">
                    Error al cargar marcadores: ${error.message}
                </td>
            </tr>
        `;
    }
}

function filterAndRenderFavoritosSeguimiento() {
    const searchVal = document.getElementById('fav-seg-search')?.value.trim().toLowerCase() || '';
    const gerenciaFilter = document.getElementById('fav-seg-filter-gerencia')?.value || 'ALL';
    const sadeFilter = document.getElementById('fav-seg-filter-sade')?.value || 'ALL';
    const estadoFilter = document.getElementById('fav-seg-filter-estado')?.value || 'ALL';
    const prioridadFilter = document.getElementById('fav-seg-filter-prioridad')?.value || 'ALL';
    const reunionFilter = document.getElementById('fav-seg-filter-reunion')?.value || 'ALL';

    const filtered = currentFavoritosSeguimientoData.filter(r => {
        // 1. Gerencia Filter
        if (gerenciaFilter !== 'ALL') {
            if (r.gerencia.toUpperCase() !== gerenciaFilter) return false;
        }

        // 2. Estado SADE Filter
        if (sadeFilter !== 'ALL') {
            if (sadeFilter === 'STOCK PROPIO') {
                if (r.ubicacion !== 'STOCK PROPIO' && r.ubicacion !== 'STOCK PROPIO (INTERVENCION)') return false;
            } else if (sadeFilter === 'SUBSANACION') {
                if (r.ubicacion !== 'SUBSANACION' && r.ubicacion !== 'SUBSANACION (INTERVENCION)') return false;
            } else if (sadeFilter === 'EN FLUJO') {
                if (r.ubicacion !== 'EN FLUJO') return false;
            }
        }

        // 3. Estado Ficha Filter
        if (estadoFilter !== 'ALL') {
            if (estadoFilter === 'NONE') {
                if (r.ficha_estado) return false;
            } else {
                if (r.ficha_estado !== estadoFilter) return false;
            }
        }

        // 4. Prioridad Filter
        if (prioridadFilter !== 'ALL') {
            if (prioridadFilter === 'NONE') {
                if (r.ficha_prioridad) return false;
            } else {
                if (r.ficha_prioridad !== prioridadFilter) return false;
            }
        }

        // 5. Reunión Filter
        if (reunionFilter !== 'ALL') {
            const isReunion = reunionFilter === 'true';
            if (r.ficha_proxima_reunion !== isReunion) return false;
        }

        // 6. Global Search
        if (searchVal) {
            const matchText = [
                r.expediente || '',
                r.descripcion_trata || '',
                r.trata || '',
                r.gerencia || '',
                r.ubicacion || '',
                r.analista || '',
                r.ficha_direccion || '',
                r.ficha_responsable || '',
                r.ficha_responsable_name || '',
                r.ficha_estado || '',
                r.ficha_prioridad || '',
                r.ficha_notas_internas || '',
                r.ultima_nota_favorito || ''   // Buscar en Nota del favorito
            ].join(' ').toLowerCase();

            if (!matchText.includes(searchVal)) return false;
        }

        return true;
    });

    renderFavoritosSeguimientoContent(filtered);
}

function exportFavSegExcel() {
    const data = currentFavoritosSeguimientoData;
    if (!data || data.length === 0) {
        alert('No hay datos para exportar.');
        return;
    }

    // Definir columnas y sus etiquetas
    const columns = [
        { key: 'expediente',              label: 'Expediente' },
        { key: 'trata',                   label: 'Código Trámite' },
        { key: 'descripcion_trata',       label: 'Trámite' },
        { key: 'gerencia',                label: 'Área / Gerencia' },
        { key: 'ubicacion',               label: 'Ubicación / Stock' },
        { key: 'analista',                label: 'Analista Asignado' },
        { key: 'dias_tramitacion',        label: 'Días Tramitación' },
        { key: 'dias_subsanacion',        label: 'Días Subsanación' },
        { key: 'cant_subsanaciones',      label: 'Cant. Subsanaciones' },
        { key: 'dias_stock',              label: 'Días Stock' },
        { key: 'fecha_ultimo_pase',       label: 'Último Pase' },
        { key: 'fecha_creacion',          label: 'Fecha Creación' },
        { key: 'cant_notas',              label: 'Cant. Notas' },
        { key: 'ultima_nota_favorito',    label: 'Última Nota' },
        { key: 'ficha_direccion',         label: 'Dirección (Ficha)' },
        { key: 'ficha_responsable_name',  label: 'Responsable (Ficha)' },
        { key: 'ficha_estado',            label: 'Estado (Ficha)' },
        { key: 'ficha_prioridad',         label: 'Prioridad (Ficha)' },
        { key: 'ficha_proxima_reunion',   label: 'Próxima Reunión' },
        { key: 'ficha_notas_internas',    label: 'Notas Internas (Ficha)' },
        { key: 'ficha_notas_internas_author', label: 'Autor Nota Interna' },
        { key: 'ficha_notas_internas_date',   label: 'Fecha Nota Interna' },
    ];

    try {
        // Crear las filas de datos con las columnas indicadas
        const rows = data.map(r => {
            const rowObj = {};
            columns.forEach(c => {
                let val = r[c.key];
                if (typeof val === 'boolean') {
                    val = val ? 'Sí' : 'No';
                }
                rowObj[c.label] = val ?? '';
            });
            return rowObj;
        });

        // Crear la hoja de cálculo
        const worksheet = XLSX.utils.json_to_sheet(rows, { header: columns.map(c => c.label) });

        // Ajustar automáticamente el ancho de las columnas
        const colWidths = columns.map(col => {
            let maxLen = col.label.length;
            data.forEach(r => {
                let val = r[col.key];
                if (typeof val === 'boolean') val = val ? 'Sí' : 'No';
                const strVal = val !== null && val !== undefined ? String(val) : '';
                if (strVal.length > maxLen) {
                    maxLen = strVal.length;
                }
            });
            return { wch: Math.min(Math.max(maxLen + 3, 10), 50) };
        });
        worksheet['!cols'] = colWidths;

        // Crear el libro de trabajo y añadir la hoja
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, "Gestión de Marcadores");

        // Guardar el archivo XLSX
        const today = new Date().toISOString().slice(0, 10);
        XLSX.writeFile(workbook, `gestion_marcadores_${today}.xlsx`);
    } catch (e) {
        alert("Error exportando a Excel: " + e.message);
    }
}
window.exportFavSegExcel = exportFavSegExcel;

async function renderFavoritosSeguimientoContent(dataToRender) {
    const tbody = document.getElementById('fav-seg-tbody');
    const container = document.getElementById('fav-seg-container');
    const emptyState = document.getElementById('fav-seg-empty-state');
    if (!tbody || !container || !emptyState) return;

    const table = container.querySelector('table');

    if (dataToRender.length === 0) {
        table.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }

    table.style.display = 'table';
    emptyState.style.display = 'none';
    tbody.innerHTML = '';

    dataToRender.forEach(r => {
        const tr = document.createElement('tr');

        let badgeClass = 'badge-status-flujo';
        if (r.ubicacion === 'STOCK PROPIO' || r.ubicacion === 'STOCK PROPIO (INTERVENCION)') {
            badgeClass = 'badge-status-propio';
        } else if (r.ubicacion === 'SUBSANACION' || r.ubicacion === 'SUBSANACION (INTERVENCION)') {
            badgeClass = 'badge-status-subs';
        } else if (r.ubicacion.startsWith('EGRESADO')) {
            badgeClass = 'badge-status-egresado';
        }

        const cleanGerencia = r.gerencia ? (r.gerencia.toLowerCase() === 'aph' ? 'APH' : r.gerencia.charAt(0).toUpperCase() + r.gerencia.slice(1).replace('_', ' ')) : '-';

        const cleanNota = r.ultima_nota_favorito ? (r.ultima_nota_favorito.length > 50 ? r.ultima_nota_favorito.substring(0, 47) + '...' : r.ultima_nota_favorito) : '-';
        const cleanNotaInterna = r.ficha_notas_internas ? (r.ficha_notas_internas.length > 50 ? r.ficha_notas_internas.substring(0, 47) + '...' : r.ficha_notas_internas) : '-';

        let estadoBadge = '-';
        if (r.ficha_estado) {
            let stateClass = '';
            if (r.ficha_estado === 'Finalizado') stateClass = 'background: #dcfce7; color: #15803d;';
            else if (r.ficha_estado === 'En Proceso') stateClass = 'background: #dbeafe; color: #1d4ed8;';
            else if (r.ficha_estado === 'En Pausa') stateClass = 'background: #fef3c7; color: #d97706;';
            else if (r.ficha_estado === 'Subsanación') stateClass = 'background: #fee2e2; color: #dc2626;';

            estadoBadge = `<span style="padding: 4px 8px; border-radius: 12px; font-size: 0.78rem; font-weight: 700; display: inline-block; ${stateClass}">${r.ficha_estado}</span>`;
        }

        tr.innerHTML = `
            <td style="padding: 12px 16px; text-align: center; vertical-align: middle;">
                <span class="favorite-star active" data-expediente="${r.expediente}" onclick="toggleFavoriteSeguimiento('${r.expediente}')">★</span>
            </td>
            <td style="padding: 12px 16px; font-weight: 700; color: #334155; font-family: inherit; white-space: nowrap;">
                <span onclick="openDetalleExpedienteModal('${r.expediente}')" style="cursor: pointer; color: #1e293b; font-weight: 700; transition: color 0.15s, border-color 0.15s; border-bottom: 1px dashed #cbd5e1; padding-bottom: 1px;" onmouseover="this.style.color='var(--primary)'; this.style.borderColor='var(--primary)';" onmouseout="this.style.color='#1e293b'; this.style.borderColor='#cbd5e1';">${r.expediente}</span>
                <span onclick="copyToClipboard('${r.expediente}', this)" style="cursor: pointer; margin-left: 6px; font-size: 0.85rem; color: #94a3b8; transition: color 0.2s; display: inline-block; vertical-align: middle;" onmouseover="this.style.color='var(--primary)'" onmouseout="this.style.color='#94a3b8'" title="Copiar Expediente">
                    <i class="fa-regular fa-copy"></i>
                </span>
            </td>
            <td style="padding: 12px 16px; font-weight: 600;">${cleanGerencia}</td>
            <td style="padding: 12px 16px; font-weight: 600; color: #475569;">${r.ficha_direccion || '-'}</td>
            <td style="padding: 12px 16px; color: #64748b; font-size: 0.88rem; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${r.ultima_nota_favorito || ''}">${cleanNota}</td>
            <td style="padding: 12px 16px; color: #64748b; font-size: 0.88rem; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${r.ficha_notas_internas || ''}">${cleanNotaInterna}</td>
            <td style="padding: 12px 16px; font-weight: 600; color: #475569;">${r.ficha_responsable_name || '-'}</td>
            <td style="padding: 12px 16px;">${estadoBadge}</td>
            <td style="padding: 12px 16px; text-align: center; vertical-align: middle;">
                <button onclick="openFichaModal('${r.expediente}')" style="background: #2563eb; color: white; padding: 6px 12px; font-size: 0.8rem; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; border: none; font-weight: 600; transition: background 0.2s;" onmouseover="this.style.background='#1d4ed8'" onmouseout="this.style.background='#2563eb'">
                    <i class="fa-regular fa-pen-to-square"></i> Ficha
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function toggleFavoriteSeguimiento(expediente) {
    await toggleFavorite(expediente);
    loadFavoritosSeguimientoView();
}

async function openDetalleExpedienteModal(expediente) {
    document.getElementById('detalle-modal-expediente-title').innerText = expediente;
    const body = document.getElementById('detalle-modal-body');
    if (!body) return;

    body.innerHTML = `
        <div style="grid-column: span 2; text-align: center; padding: 3rem; color: #64748b;">
            <i class="fa-solid fa-circle-notch fa-spin" style="font-size: 2.5rem; margin-bottom: 1rem; color: var(--primary);"></i>
            <p>Cargando información del expediente...</p>
        </div>
    `;

    document.getElementById('detalle-expediente-modal').style.display = 'flex';

    // Find item
    let r = currentFavoritosSeguimientoData.find(x => x.expediente === expediente) ||
        currentFavoritesData.find(x => x.expediente === expediente);

    if (!r) {
        try {
            const fetchRes = await def_fetch(`${API_BASE}/expediente/favoritos`);
            if (fetchRes && fetchRes.ok) {
                const favs = await fetchRes.json();
                r = favs.find(x => x.expediente === expediente);
            }
        } catch (e) {
            console.error("Error fetching fallback details:", e);
        }
    }

    if (!r) {
        body.innerHTML = `
            <div style="grid-column: span 2; text-align: center; padding: 3rem; color: #ef4444;">
                <p>No se encontró información para el expediente ${expediente}.</p>
            </div>
        `;
        return;
    }

    let notesHtml = '';
    try {
        const notesRes = await def_fetch(`${API_BASE}/expediente/favorito/${encodeURIComponent(expediente)}/notas`);
        if (notesRes && notesRes.ok) {
            const notes = await notesRes.json();
            if (notes.length === 0) {
                notesHtml = `
                    <div style="text-align: center; padding: 2rem; color: #94a3b8; font-style: italic;">
                        Sin anotaciones en este expediente.
                    </div>
                `;
            } else {
                notes.forEach(n => {
                    const cleanDate = n.created_at ? n.created_at.substring(0, 19).replace('T', ' ') : '-';
                    notesHtml += `
                        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 12px; font-family: 'Outfit';">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 0.8rem; color: #64748b;">
                                <span style="font-weight: 700; color: var(--primary);"><i class="fa-regular fa-user" style="margin-right: 4px;"></i>${n.author_name} (${n.author_sector})</span>
                                <span>${cleanDate}</span>
                            </div>
                            <div style="font-size: 0.9rem; color: #334155; white-space: pre-wrap; line-height: 1.4;">${n.note_text}</div>
                        </div>
                    `;
                });
            }
        } else {
            notesHtml = `<div style="text-align: center; color: #ef4444; padding: 1rem;">Error al cargar las anotaciones.</div>`;
        }
    } catch (err) {
        console.error("Error loading notes for detail modal:", err);
        notesHtml = `<div style="text-align: center; color: #ef4444; padding: 1rem;">Error de conexión al cargar anotaciones.</div>`;
    }

    let intNotesHtml = '';
    try {
        const intNotesRes = await def_fetch(`${API_BASE}/expediente/ficha/${expediente}/notas_internas`);
        if (intNotesRes && intNotesRes.ok) {
            const intNotes = await intNotesRes.json();
            if (intNotes.length === 0) {
                intNotesHtml = '<span style="color: #94a3b8; font-style: italic; font-size: 0.9rem; padding: 5px;">Sin notas internas cargadas.</span>';
            } else {
                intNotes.forEach(n => {
                    const cleanDate = n.created_at ? n.created_at.substring(0, 19).replace('T', ' ') : '-';
                    const escapedText = n.note_text.replace(/'/g, "\\'").replace(/"/g, '&quot;').replace(/\n/g, '\\n');
                    const actionsHtml = n.is_owner ? `
                        <div style="display: flex; gap: 8px;">
                            <button onclick="editFichaNota(${n.id}, '${escapedText}', '${expediente}')" style="background: none; border: none; cursor: pointer; color: #64748b; font-size: 0.85rem; padding: 2px 4px; display: inline-flex; align-items: center;" title="Editar"><i class="fa-solid fa-pen" style="font-size: 0.8rem;"></i></button>
                            <button onclick="deleteFichaNota(${n.id}, '${expediente}')" style="background: none; border: none; cursor: pointer; color: #ef4444; font-size: 0.85rem; padding: 2px 4px; display: inline-flex; align-items: center;" title="Eliminar"><i class="fa-solid fa-trash" style="font-size: 0.8rem;"></i></button>
                        </div>
                    ` : '';
                    intNotesHtml += `
                        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 8px; font-family: 'Outfit';">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 0.8rem; color: #64748b;">
                                <span style="font-weight: 700; color: var(--primary);"><i class="fa-regular fa-user" style="margin-right: 4px;"></i>${n.author_name}</span>
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span>${cleanDate}</span>
                                    ${actionsHtml}
                                </div>
                            </div>
                            <div style="font-size: 0.9rem; color: #334155; white-space: pre-wrap; line-height: 1.4;">${n.note_text}</div>
                        </div>
                    `;
                });
            }
        } else {
            intNotesHtml = '<div style="color: #ef4444; font-style: italic; font-size: 0.9rem; padding: 5px;">Error al cargar las notas internas.</div>';
        }
    } catch (err) {
        console.error("Error loading internal notes for detail modal:", err);
        intNotesHtml = '<div style="color: #ef4444; font-style: italic; font-size: 0.9rem; padding: 5px;">Error de conexión al cargar notas internas.</div>';
    }

    let badgeClass = 'badge-status-flujo';
    if (r.ubicacion === 'STOCK PROPIO' || r.ubicacion === 'STOCK PROPIO (INTERVENCION)') {
        badgeClass = 'badge-status-propio';
    } else if (r.ubicacion === 'SUBSANACION' || r.ubicacion === 'SUBSANACION (INTERVENCION)') {
        badgeClass = 'badge-status-subs';
    } else if (r.ubicacion.startsWith('EGRESADO')) {
        badgeClass = 'badge-status-egresado';
    }

    const cleanGerencia = r.gerencia ? (r.gerencia.toLowerCase() === 'aph' ? 'APH' : r.gerencia.charAt(0).toUpperCase() + r.gerencia.slice(1).replace('_', ' ')) : '-';

    let estadoBadge = '<span style="color: #94a3b8; font-style: italic;">Sin Estado</span>';
    if (r.ficha_estado) {
        let stateClass = '';
        if (r.ficha_estado === 'Finalizado') stateClass = 'background: #dcfce7; color: #15803d;';
        else if (r.ficha_estado === 'En Proceso') stateClass = 'background: #dbeafe; color: #1d4ed8;';
        else if (r.ficha_estado === 'En Pausa') stateClass = 'background: #fef3c7; color: #d97706;';
        else if (r.ficha_estado === 'Subsanación') stateClass = 'background: #fee2e2; color: #dc2626;';
        estadoBadge = `<span style="padding: 4px 10px; border-radius: 12px; font-size: 0.78rem; font-weight: 700; ${stateClass}">${r.ficha_estado}</span>`;
    }

    let prioridadBadge = '<span style="color: #94a3b8; font-style: italic;">Sin Prioridad</span>';
    if (r.ficha_prioridad) {
        let prioClass = '';
        if (r.ficha_prioridad === 'Alta') prioClass = 'background: #fee2e2; color: #dc2626; border: 1px solid #fecaca;';
        else if (r.ficha_prioridad === 'Media') prioClass = 'background: #fef3c7; color: #d97706; border: 1px solid #fde68a;';
        else if (r.ficha_prioridad === 'Baja') prioClass = 'background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0;';
        prioridadBadge = `<span style="padding: 4px 10px; border-radius: 12px; font-size: 0.78rem; font-weight: 700; ${prioClass}">${r.ficha_prioridad}</span>`;
    }

    body.innerHTML = `
        <!-- Card 1: Información SADE -->
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <h3 style="margin-top: 0; margin-bottom: 15px; font-family: 'Outfit'; font-weight: 700; color: var(--primary-dark); font-size: 1.1rem; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">
                <i class="fa-solid fa-circle-info" style="color: var(--primary); margin-right: 8px;"></i> Información General (SADE)
            </h3>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; font-family: 'Outfit'; font-size: 0.9rem;">
                <div>
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Trámite</strong>
                    <div style="font-weight: 600; color: #1e293b; margin-top: 2px;">${r.descripcion_trata || r.trata || '-'} <span style="font-size: 0.8rem; color: #94a3b8; font-weight: normal;">(${r.trata})</span></div>
                </div>
                <div>
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Gerencia / Área</strong>
                    <div style="font-weight: 600; color: #1e293b; margin-top: 2px;">${cleanGerencia}</div>
                </div>
                <div>
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Ubicación / Stock</strong>
                    <div style="margin-top: 4px;"><span class="badge-status ${badgeClass}" style="margin: 0; font-size: 0.75rem;">${r.ubicacion}</span></div>
                </div>
                <div>
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Analista Asignado</strong>
                    <div style="font-weight: 600; color: #1e293b; margin-top: 2px;">${r.analista || 'SIN ASIGNAR'}</div>
                </div>
                <div>
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Días Tramitación</strong>
                    <div style="font-weight: 700; color: #1e293b; margin-top: 2px; font-size: 1.05rem;">${r.dias_tramitacion ?? 0} <span style="font-size: 0.8rem; font-weight: normal; color: #64748b;">días</span></div>
                </div>
                <div>
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Días en Stock</strong>
                    <div style="font-weight: 700; color: #1e293b; margin-top: 2px; font-size: 1.05rem;">${r.dias_stock ?? 0} <span style="font-size: 0.8rem; font-weight: normal; color: #64748b;">días</span></div>
                </div>
                <div>
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Días Subsanación</strong>
                    <div style="font-weight: 700; color: #1e293b; margin-top: 2px; font-size: 1.05rem;">${r.dias_subsanacion ?? 0} <span style="font-size: 0.8rem; font-weight: normal; color: #64748b;">días</span></div>
                </div>
                <div>
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Cant. Subsanaciones</strong>
                    <div style="font-weight: 700; color: #1e293b; margin-top: 2px; font-size: 1.05rem;">${r.cant_subsanaciones ?? 0}</div>
                </div>
                <div style="grid-column: span 4;">
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Fechas del Trámite</strong>
                    <div style="color: #475569; margin-top: 4px; display: flex; gap: 40px; font-weight: 600;">
                        <div>Último Pase: <span style="color: #1e293b;">${r.fecha_ultimo_pase || '-'}</span></div>
                        <div>Fecha Creación: <span style="color: #1e293b;">${r.fecha_creacion || '-'}</span></div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Card 2: Ficha de Expediente -->
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <h3 style="margin-top: 0; margin-bottom: 15px; font-family: 'Outfit'; font-weight: 700; color: var(--primary-dark); font-size: 1.1rem; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">
                <i class="fa-regular fa-clipboard" style="color: var(--primary); margin-right: 8px;"></i> Personalización & Ficha de Seguimiento
            </h3>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; font-family: 'Outfit'; font-size: 0.9rem;">
                <div style="grid-column: span 2;">
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Dirección</strong>
                    <div style="font-weight: 600; color: #1e293b; margin-top: 2px;">${r.ficha_direccion || '-'}</div>
                </div>
                <div>
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Responsable</strong>
                    <div style="font-weight: 600; color: #1e293b; margin-top: 2px;">${r.ficha_responsable_name || '-'}</div>
                </div>
                <div>
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Próxima Reunión</strong>
                    <div style="font-weight: 600; color: #1e293b; margin-top: 2px;">${r.ficha_proxima_reunion ? 'Sí' : 'No'}</div>
                </div>
                <div>
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Estado Ficha</strong>
                    <div style="margin-top: 4px;">${estadoBadge}</div>
                </div>
                <div>
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Prioridad Ficha</strong>
                    <div style="margin-top: 4px;">${prioridadBadge}</div>
                </div>
                <div style="grid-column: span 4; border-top: 1px solid #f1f5f9; padding-top: 12px; margin-top: 5px;">
                    <strong style="color: #64748b; font-size: 0.8rem; text-transform: uppercase;">Nota Interna de Ficha</strong>
                    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-top: 6px; max-height: 250px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;">
                        ${intNotesHtml}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Card 3: Anotaciones de Favorito -->
        <div style="display: flex; flex-direction: column; background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <h3 style="margin-top: 0; margin-bottom: 15px; font-family: 'Outfit'; font-weight: 700; color: var(--primary-dark); font-size: 1.1rem; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <span><i class="fa-regular fa-comment-dots" style="color: var(--primary); margin-right: 8px;"></i> Historial de Anotaciones (${r.cant_notas})</span>
                <button onclick="closeModal('detalle-expediente-modal'); openFavoriteNotesModal('${r.expediente}')" style="background: none; border: none; color: var(--primary); font-size: 0.85rem; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 4px; font-family: 'Outfit';" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">
                    <i class="fa-solid fa-plus"></i> Agregar Nota
                </button>
            </h3>
            <div style="padding-right: 5px;">
                ${notesHtml}
            </div>
        </div>
    `;
}

async function openFichaModal(expediente) {
    const hiddenInput = document.getElementById('ficha-expediente-hidden');
    const modalTitle = document.getElementById('ficha-modal-expediente-title');
    const respSelect = document.getElementById('ficha-responsable');
    const historyContainer = document.getElementById('ficha-notas-history-container');
    if (!hiddenInput || !modalTitle || !respSelect) return;

    hiddenInput.value = expediente;
    modalTitle.innerText = expediente;

    // Clear fields
    document.getElementById('ficha-direccion').value = '';
    document.getElementById('ficha-estado').value = '';
    document.getElementById('ficha-prioridad').value = '';
    document.getElementById('ficha-proxima-reunion').value = 'false';
    document.getElementById('ficha-notas-internas').value = '';
    if (historyContainer) {
        historyContainer.innerHTML = '<div style="color: #94a3b8; font-style: italic; font-size: 0.85rem; text-align: center; padding: 5px;">Cargando historial...</div>';
    }

    try {
        // Load users for the responsible dropdown
        const usersRes = await def_fetch(`${API_BASE}/usuarios-tablero`);
        if (usersRes && usersRes.ok) {
            const users = await usersRes.json();
            let optHtml = '<option value="">Seleccionar Responsable</option>';
            users.forEach(u => {
                optHtml += `<option value="${u.username}">${u.full_name} (@${u.username})</option>`;
            });
            respSelect.innerHTML = optHtml;
        }

        // Fetch current Ficha data
        const fichaRes = await def_fetch(`${API_BASE}/expediente/ficha/${expediente}`);
        if (fichaRes && fichaRes.ok) {
            const data = await fichaRes.json();
            document.getElementById('ficha-direccion').value = data.direccion || '';
            document.getElementById('ficha-responsable').value = data.responsable || '';
            document.getElementById('ficha-estado').value = data.estado || '';
            document.getElementById('ficha-prioridad').value = data.prioridad || '';
            document.getElementById('ficha-proxima-reunion').value = data.proxima_reunion ? 'true' : 'false';
        }

        // Fetch internal notes history
        if (historyContainer) {
            const intNotesRes = await def_fetch(`${API_BASE}/expediente/ficha/${expediente}/notas_internas`);
            if (intNotesRes && intNotesRes.ok) {
                const intNotes = await intNotesRes.json();
                if (intNotes.length === 0) {
                    historyContainer.innerHTML = '<div style="color: #94a3b8; font-style: italic; font-size: 0.85rem; text-align: center; padding: 5px;">Sin notas anteriores.</div>';
                } else {
                    let hHtml = '';
                    intNotes.forEach(n => {
                        const cleanDate = n.created_at ? n.created_at.substring(0, 19).replace('T', ' ') : '-';
                        const escapedText = n.note_text.replace(/'/g, "\\'").replace(/"/g, '&quot;').replace(/\n/g, '\\n');
                        const actionsHtml = n.is_owner ? `
                            <div style="display: flex; gap: 8px;">
                                <button type="button" onclick="editFichaNota(${n.id}, '${escapedText}', '${expediente}')" style="background: none; border: none; cursor: pointer; color: #64748b; font-size: 0.8rem; padding: 2px 4px; display: inline-flex; align-items: center;" title="Editar"><i class="fa-solid fa-pen" style="font-size: 0.75rem;"></i></button>
                                <button type="button" onclick="deleteFichaNota(${n.id}, '${expediente}')" style="background: none; border: none; cursor: pointer; color: #ef4444; font-size: 0.8rem; padding: 2px 4px; display: inline-flex; align-items: center;" title="Eliminar"><i class="fa-solid fa-trash" style="font-size: 0.75rem;"></i></button>
                            </div>
                        ` : '';
                        hHtml += `
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 10px; font-size: 0.85rem; font-family: 'Outfit'; margin-bottom: 5px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; font-size: 0.75rem; color: #64748b;">
                                    <span style="font-weight: 700; color: var(--primary);"><i class="fa-regular fa-user" style="margin-right: 4px;"></i>${n.author_name}</span>
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <span>${cleanDate}</span>
                                        ${actionsHtml}
                                    </div>
                                </div>
                                <div style="color: #334155; white-space: pre-wrap; line-height: 1.4;">${n.note_text}</div>
                            </div>
                        `;
                    });
                    historyContainer.innerHTML = hHtml;
                }
            } else {
                historyContainer.innerHTML = '<div style="color: #ef4444; font-style: italic; font-size: 0.85rem; text-align: center; padding: 5px;">Error al cargar historial.</div>';
            }
        }

        document.getElementById('ficha-expediente-modal').style.display = 'flex';
    } catch (err) {
        console.error("Error opening Ficha modal:", err);
        alert("Error al cargar la ficha del expediente.");
    }
}

async function handleFichaSubmit(event) {
    event.preventDefault();
    const expediente = document.getElementById('ficha-expediente-hidden').value;
    if (!expediente) return;

    const direccion = document.getElementById('ficha-direccion').value.trim();
    const responsable = document.getElementById('ficha-responsable').value;
    const estado = document.getElementById('ficha-estado').value;
    const prioridad = document.getElementById('ficha-prioridad').value;
    const proxima_reunion = document.getElementById('ficha-proxima-reunion').value === 'true';
    const notas_internas = document.getElementById('ficha-notas-internas').value.trim();

    try {
        const res = await def_fetch(`${API_BASE}/expediente/ficha/${expediente}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                direccion,
                responsable,
                estado,
                prioridad,
                proxima_reunion,
                notas_internas
            })
        });

        if (res && res.ok) {
            alert("Ficha de expediente guardada exitosamente.");
            closeModal('ficha-expediente-modal');

            // Re-fetch updated list
            const fetchRes = await def_fetch(`${API_BASE}/expediente/favoritos`);
            if (fetchRes && fetchRes.ok) {
                currentFavoritosSeguimientoData = await fetchRes.json();
            }
            filterAndRenderFavoritosSeguimiento();
        } else {
            const err = await res.json();
            alert("Error al guardar la ficha: " + err.detail);
        }
    } catch (e) {
        console.error("Error submitting Ficha form:", e);
        alert("Error al guardar la ficha.");
    }
}

async function editFichaNota(noteId, currentText, expediente) {
    const newText = prompt("Editar nota interna:", currentText);
    if (newText === null) return; // User cancelled
    const trimmed = newText.trim();
    if (!trimmed) {
        alert("La nota no puede estar vacía.");
        return;
    }
    
    try {
        const res = await def_fetch(`${API_BASE}/expediente/ficha/nota/${noteId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ note_text: trimmed })
        });
        
        if (res && res.ok) {
            const fichaModal = document.getElementById('ficha-expediente-modal');
            const detailModal = document.getElementById('detalle-expediente-modal');
            
            if (fichaModal && fichaModal.style.display === 'flex') {
                openFichaModal(expediente);
            }
            if (detailModal && detailModal.style.display === 'flex') {
                openDetalleExpedienteModal(expediente);
            }
        } else {
            const errData = res ? await res.json() : {};
            alert("Error al editar la nota: " + (errData.detail || "Error desconocido"));
        }
    } catch (e) {
        console.error("Error editing note:", e);
        alert("Error de conexión al intentar editar la nota.");
    }
}

async function deleteFichaNota(noteId, expediente) {
    if (!confirm("¿Estás seguro de que deseas eliminar esta nota interna?")) return;
    
    try {
        const res = await def_fetch(`${API_BASE}/expediente/ficha/nota/${noteId}`, {
            method: 'DELETE'
        });
        
        if (res && res.ok) {
            const fichaModal = document.getElementById('ficha-expediente-modal');
            const detailModal = document.getElementById('detalle-expediente-modal');
            
            if (fichaModal && fichaModal.style.display === 'flex') {
                openFichaModal(expediente);
            }
            if (detailModal && detailModal.style.display === 'flex') {
                openDetalleExpedienteModal(expediente);
            }
        } else {
            const errData = res ? await res.json() : {};
            alert("Error al eliminar la nota: " + (errData.detail || "Error desconocido"));
        }
    } catch (e) {
        console.error("Error deleting note:", e);
        alert("Error de conexión al intentar eliminar la nota.");
    }
}

window.editFichaNota = editFichaNota;
window.deleteFichaNota = deleteFichaNota;

// --- SECCIÓN BUZONES ---
let currentBuzonesArea = '';
let currentBuzonesGerencia = '';
let currentBuzonesData = [];
let currentActiveBuzonAnalyst = null;

const BUZONES_GERENCIAS = {
    dgroc: [
        { id: 'catastro', label: 'Catastro' },
        { id: 'instalaciones', label: 'Instalaciones' },
        { id: 'conforme', label: 'Conforme' },
        { id: 'contable', label: 'Contable' },
        { id: 'etapa_proyecto', label: 'Etapa Proyecto' },
        { id: 'aviso_obra', label: 'Aviso de Obra' }
    ],
    dgiur: [
        { id: 'morfologia', label: 'Morfología' },
        { id: 'aph', label: 'APH' },
        { id: 'usos', label: 'Usos' }
    ]
};

async function showBuzonesView(area) {
    currentBuzonesArea = area.toLowerCase();
    const titleEl = document.getElementById('buzones-title');
    const subtitleEl = document.getElementById('buzones-subtitle');
    const breadcrumbArea = document.getElementById('buzones-breadcrumbs-area');
    const tabsContainer = document.getElementById('buzones-tabs');
    const tableContainer = document.getElementById('buzones-analysts-table-container');
    const emptyState = document.getElementById('buzones-empty-state');
    
    if (!titleEl || !subtitleEl || !breadcrumbArea || !tabsContainer) return;

    // Reset view
    if (tableContainer) tableContainer.style.display = 'none';
    if (emptyState) emptyState.style.display = 'none';

    // Set title and breadcrumbs based on area
    const uppercaseArea = area.toUpperCase();
    titleEl.innerText = `Buzones ${uppercaseArea}`;
    breadcrumbArea.innerText = uppercaseArea;

    // Render Gerencias Tabs
    const gerencias = BUZONES_GERENCIAS[currentBuzonesArea] || [];
    let tabsHtml = '';
    gerencias.forEach((g, idx) => {
        const activeClass = idx === 0 ? 'active' : '';
        tabsHtml += `
            <button class="buzones-tab-btn ${activeClass}" data-gerencia="${g.id}" onclick="loadBuzonesData('${g.id}')">
                ${g.label}
            </button>
        `;
    });
    tabsContainer.innerHTML = tabsHtml;

    // Show view
    showView('buzones');

    // Load first gerencia by default
    if (gerencias.length > 0) {
        await loadBuzonesData(gerencias[0].id);
    }
}

async function loadBuzonesData(gerencia) {
    currentBuzonesGerencia = gerencia;
    
    // Clear analyst search input
    const searchInput = document.getElementById('buzones-analyst-search');
    if (searchInput) searchInput.value = '';
    
    // Update active tab styling
    const tabs = document.querySelectorAll('.buzones-tab-btn');
    tabs.forEach(btn => {
        if (btn.getAttribute('data-gerencia') === gerencia) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    const loader = document.getElementById('buzones-loader');
    const tableContainer = document.getElementById('buzones-analysts-table-container');
    const emptyState = document.getElementById('buzones-empty-state');

    if (loader) loader.style.display = 'block';
    if (tableContainer) tableContainer.style.display = 'none';
    if (emptyState) emptyState.style.display = 'none';

    try {
        const res = await def_fetch(`${API_BASE}/reporte/${gerencia}/buzones`);
        if (res && res.ok) {
            currentBuzonesData = await res.json();
            renderBuzonesAnalysts(currentBuzonesData, gerencia);
        } else {
            throw new Error("No se pudo obtener el stock de analistas.");
        }
    } catch (e) {
        console.error("Error loading buzones data:", e);
        const tbody = document.getElementById('buzones-analysts-tbody');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: #ef4444; padding: 2rem; font-weight: 600;">Error al cargar datos: ${e.message}</td></tr>`;
        }
        if (tableContainer) tableContainer.style.display = 'block';
    } finally {
        if (loader) loader.style.display = 'none';
    }
}

function renderBuzonesAnalysts(analysts, gerencia) {
    const tableContainer = document.getElementById('buzones-analysts-table-container');
    const emptyState = document.getElementById('buzones-empty-state');
    const tbody = document.getElementById('buzones-analysts-tbody');
    
    if (!tableContainer || !emptyState || !tbody) return;
    
    tbody.innerHTML = '';
    
    if (!analysts || analysts.length === 0) {
        emptyState.style.display = 'block';
        tableContainer.style.display = 'none';
        return;
    }

    tableContainer.style.display = 'block';
    emptyState.style.display = 'none';

    analysts.forEach(an => {
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.style.transition = 'background-color 0.15s ease';
        tr.onmouseover = () => { tr.style.backgroundColor = '#f8fafc'; };
        tr.onmouseout = () => { tr.style.backgroundColor = ''; };
        tr.onclick = () => showBuzonAnalystDetail(an.username);
        
        // Calculate median of days in stock
        const dias = (an.expedientes || []).map(e => e.dias || 0);
        let median = 0;
        if (dias.length > 0) {
            const sorted = [...dias].sort((a, b) => a - b);
            const half = Math.floor(sorted.length / 2);
            if (sorted.length % 2 !== 0) {
                median = sorted[half];
            } else {
                median = Math.round((sorted[half - 1] + sorted[half]) / 2);
            }
        }
        
        tr.innerHTML = `
            <td style="padding: 18px 20px; font-weight: 700; color: #1e293b; font-family: 'Outfit'; line-height: 1.5;">
                <span class="analyst-name-link" style="border-bottom: 1px dashed #cbd5e1; padding-bottom: 2px;">
                    ${an.name.toUpperCase()}
                </span>
            </td>
            <td style="padding: 18px 20px; color: #64748b; font-family: 'Outfit'; line-height: 1.5;">@${an.username}</td>
            <td style="padding: 18px 20px; text-align: center; font-weight: 800; color: #475569; font-family: 'Outfit'; font-size: 1.02rem; line-height: 1.5;">${median}d</td>
            <td style="padding: 18px 20px; text-align: center; font-weight: 800; color: var(--primary); font-family: 'Outfit'; font-size: 1.05rem; line-height: 1.5;">${an.count}</td>
        `;
        tbody.appendChild(tr);
    });
}

function showBuzonAnalystDetail(username) {
    const analyst = currentBuzonesData.find(a => a.username === username);
    if (!analyst) return;

    currentActiveBuzonAnalyst = analyst;

    // Set Breadcrumbs
    const bcArea = document.getElementById('buzon-analista-breadcrumbs-area');
    const bcGerencia = document.getElementById('buzon-analista-breadcrumbs-gerencia');
    const bcName = document.getElementById('buzon-analista-breadcrumbs-name');
    
    if (bcArea) bcArea.innerText = currentBuzonesArea.toUpperCase();
    if (bcGerencia) {
        // Resolve gerencia label
        const gerenciasList = BUZONES_GERENCIAS[currentBuzonesArea] || [];
        const gObj = gerenciasList.find(g => g.id === currentBuzonesGerencia);
        bcGerencia.innerText = gObj ? gObj.label : currentBuzonesGerencia.toUpperCase();
    }
    if (bcName) bcName.innerText = analyst.name.toUpperCase();

    // Set Presentation Block
    const nameHeader = document.getElementById('buzon-analista-header-name');
    const sadeHeader = document.getElementById('buzon-analista-header-sade');
    const countBadge = document.getElementById('buzon-analista-header-count');

    if (nameHeader) nameHeader.innerText = analyst.name.toUpperCase();
    if (sadeHeader) sadeHeader.innerText = `Usuario SADE: @${analyst.username}`;
    if (countBadge) {
        countBadge.innerText = `${analyst.count} ${analyst.count === 1 ? 'Expediente en Stock' : 'Expedientes en Stock'}`;
    }

    // Populate Detailed Table
    const tbody = document.getElementById('buzon-analista-tbody');
    if (tbody) {
        tbody.innerHTML = '';
        analyst.expedientes.forEach(exp => {
            const tr = document.createElement('tr');
            
            const isFav = userFavorites.has(exp.expediente);
            const starSpan = `<span class="favorite-star ${isFav ? 'active' : ''}" data-expediente="${exp.expediente}" onclick="event.stopPropagation(); toggleFavorite('${exp.expediente}')" style="cursor: pointer; font-size: 1.35rem; transition: transform 0.15s ease; display: inline-block; user-select: none;">${isFav ? '★' : '☆'}</span>`;
            
            const expLink = `<a href="#" style="font-weight: 700; color: #1e293b; border-bottom: 1px dashed #cbd5e1; text-decoration: none;" onclick="event.preventDefault(); openDetalleExpedienteModal('${exp.expediente}')">${exp.expediente}</a>`;
            const copySpan = `<span onclick="copyToClipboard('${exp.expediente}', this)" style="cursor: pointer; margin-left: 6px; font-size: 0.85rem; color: #94a3b8; transition: color 0.2s; display: inline-block; vertical-align: middle;" onmouseover="this.style.color='var(--primary)'" onmouseout="this.style.color='#94a3b8'" title="Copiar Expediente"><i class="fa-regular fa-copy"></i></span>`;
            
            tr.innerHTML = `
                <td style="padding: 16px 20px; text-align: center; vertical-align: middle;">${starSpan}</td>
                <td style="padding: 16px 20px; vertical-align: middle; line-height: 1.5; white-space: nowrap;">${expLink}${copySpan}</td>
                <td style="padding: 16px 20px; font-weight: 600; color: #475569; vertical-align: middle; line-height: 1.5;">${exp.trata}</td>
                <td style="padding: 16px 20px; color: #475569; vertical-align: middle; font-size: 0.9rem; line-height: 1.5;">${exp.descripcion_trata}</td>
                <td style="padding: 16px 20px; text-align: center; font-weight: 800; color: var(--primary); vertical-align: middle; font-size: 0.95rem; line-height: 1.5;">${exp.dias}d</td>
                <td style="padding: 16px 20px; text-align: center; font-weight: 800; color: #6366f1; vertical-align: middle; font-size: 0.95rem; line-height: 1.5;">${exp.dias_en_gerencia}d</td>
                <td style="padding: 16px 20px; color: #64748b; vertical-align: middle; font-size: 0.85rem; line-height: 1.5;">${exp.fecha_ultimo_pase || '-'}</td>
                <td style="padding: 16px 20px; vertical-align: middle; line-height: 1.5;">
                    <span class="badge-status-flujo" style="font-size: 0.78rem; font-weight: 700; background: #e0f2fe; color: #0369a1; padding: 6px 12px; border-radius: 12px;">${exp.estado_expediente}</span>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Switch View
    showView('buzon-analista-detalle');
}

function backToBuzonGerencia() {
    showView('buzones');
}

function filterBuzonesAnalysts() {
    const searchInput = document.getElementById('buzones-analyst-search');
    if (!searchInput) return;
    const query = searchInput.value.toLowerCase().trim();
    
    if (!query) {
        renderBuzonesAnalysts(currentBuzonesData, currentBuzonesGerencia);
        return;
    }
    
    const filtered = currentBuzonesData.filter(an => 
        (an.name && an.name.toLowerCase().includes(query)) || 
        (an.username && an.username.toLowerCase().includes(query))
    );
    renderBuzonesAnalysts(filtered, currentBuzonesGerencia);
}

window.showBuzonesView = showBuzonesView;
window.loadBuzonesData = loadBuzonesData;
window.showBuzonAnalystDetail = showBuzonAnalystDetail;
window.backToBuzonGerencia = backToBuzonGerencia;
window.filterBuzonesAnalysts = filterBuzonesAnalysts;

function exportBuzonAnalistaExcel() {
    if (!currentActiveBuzonAnalyst || !currentActiveBuzonAnalyst.expedientes || currentActiveBuzonAnalyst.expedientes.length === 0) {
        alert("No hay expedientes para exportar.");
        return;
    }
    
    const columns = [
        { key: 'expediente', label: 'Expediente' },
        { key: 'trata', label: 'Trata' },
        { key: 'descripcion_trata', label: 'Descripción Trata' },
        { key: 'dias', label: 'Días Stock' },
        { key: 'dias_en_gerencia', label: 'Días en Gerencia' },
        { key: 'fecha_ultimo_pase', label: 'Último Pase' },
        { key: 'estado_expediente', label: 'Estado' }
    ];
    
    try {
        const rows = currentActiveBuzonAnalyst.expedientes.map(exp => {
            const rowObj = {};
            columns.forEach(c => {
                rowObj[c.label] = exp[c.key] ?? '';
            });
            return rowObj;
        });
        
        const worksheet = XLSX.utils.json_to_sheet(rows, { header: columns.map(c => c.label) });
        
        // Auto-fit columns
        const colWidths = columns.map(col => {
            let maxLen = col.label.length;
            currentActiveBuzonAnalyst.expedientes.forEach(exp => {
                const val = exp[col.key];
                const strVal = val !== null && val !== undefined ? String(val) : '';
                if (strVal.length > maxLen) maxLen = strVal.length;
            });
            return { wch: Math.min(Math.max(maxLen + 3, 10), 50) };
        });
        worksheet['!cols'] = colWidths;
        
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, "Stock Analista");
        
        const nameClean = currentActiveBuzonAnalyst.name.replace(/\s+/g, '_').toLowerCase();
        XLSX.writeFile(workbook, `stock_${nameClean}_${currentBuzonesGerencia}.xlsx`);
    } catch (e) {
        alert("Error exportando a Excel: " + e.message);
    }
}
window.exportBuzonAnalistaExcel = exportBuzonAnalistaExcel;

// --- REPORT PENDIENTES ASOCIACION ---
let currentPendientesAsociacionData = null;
let expandedPendientesArea = null;
let expandedPendientesTrata = null;

async function loadPendientesAsociacionData() {
    const container = document.getElementById('pendientes-content-container');
    if (!container) return;

    container.innerHTML = `
        <div style="padding: 3rem; text-align: center;">
            <div class="loader" style="margin: 0 auto 1.5rem auto;"></div>
            <h3 style="color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700;">Cargando Pendientes de Asociación...</h3>
            <p style="color: #64748b;">Consultando los GEDOs de egreso pendientes en el servidor...</p>
        </div>
    `;

    try {
        const res = await def_fetch(`${API_BASE}/reporte/pendientes_asociacion`);
        if (!res || !res.ok) {
            throw new Error("Error en la respuesta del servidor");
        }
        currentPendientesAsociacionData = await res.json();
        renderPendientesAsociacion();
    } catch (e) {
        container.innerHTML = `
            <div style="padding: 3rem; text-align: center; color: #ef4444; font-weight: 600;">
                Error al cargar el reporte: ${e.message}
                <br>
                <button class="btn-primary" style="margin-top: 1.5rem; padding: 8px 16px;" onclick="loadPendientesAsociacionData()">Reintentar Carga</button>
            </div>
        `;
    }
}
window.loadPendientesAsociacionData = loadPendientesAsociacionData;

function renderPendientesAsociacion() {
    const container = document.getElementById('pendientes-content-container');
    if (!container) return;

    if (!currentPendientesAsociacionData || Object.keys(currentPendientesAsociacionData).length === 0) {
        container.innerHTML = `
            <div style="padding: 3rem; text-align: center; color: #64748b; background: white; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: var(--card-shadow);">
                🎉 No hay GEDOs de egreso pendientes de asociación en este momento.
            </div>
        `;
        return;
    }

    const searchVal = document.getElementById('pendientes-search')?.value.toLowerCase() || '';

    // Filtrar y agrupar los datos según la búsqueda
    let hasData = false;
    let html = `
        <div class="pendientes-areas-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
    `;

    const GERENCIA_TITLES = {
        catastro: "Catastro",
        instalaciones: "Instalaciones",
        regularizacion: "Regularización",
        contable: "Contable",
        etapa_proyecto: "Etapa Proyecto",
        morfologia: "Morfología",
        aph: "Protección Histórica APH",
        usos: "Usos del Suelo",
        aviso_obra: "Aviso de Obra"
    };

    Object.keys(currentPendientesAsociacionData).forEach(areaKey => {
        const area = currentPendientesAsociacionData[areaKey];
        let totalPendingInArea = 0;
        const filteredTratas = {};

        Object.keys(area.tratas).forEach(trataCode => {
            const trata = area.tratas[trataCode];
            const filteredExps = trata.expedientes.filter(exp => {
                return exp.expediente.toLowerCase().includes(searchVal) ||
                       trataCode.toLowerCase().includes(searchVal) ||
                       trata.trata_nombre.toLowerCase().includes(searchVal) ||
                       exp.gedo.toLowerCase().includes(searchVal) ||
                       (exp.usuario_creador || '').toLowerCase().includes(searchVal);
            });

            if (filteredExps.length > 0) {
                filteredTratas[trataCode] = {
                    ...trata,
                    expedientes: filteredExps
                };
                totalPendingInArea += filteredExps.length;
            }
        });

        if (totalPendingInArea > 0) {
            hasData = true;
            const areaTitle = GERENCIA_TITLES[areaKey] || area.area_nombre;
            const isExpanded = expandedPendientesArea === areaKey;

            html += `
                <div class="analyst-card-premium area-card-item" onclick="togglePendientesArea('${areaKey}')" style="cursor: pointer; padding: 25px; display: flex; flex-direction: column; gap: 15px; border: ${isExpanded ? '2px solid var(--primary)' : '1px solid #cbd5e1'}; border-radius: 16px; transition: all 0.2s; background: ${isExpanded ? '#f0f9ff' : 'white'}; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="width: 50px; height: 50px; border-radius: 12px; background: ${isExpanded ? 'var(--primary)' : '#eff6ff'}; color: ${isExpanded ? 'white' : '#1d4ed8'}; display: flex; align-items: center; justify-content: center; font-size: 1.5rem;">
                            <i class="fa-solid fa-folder-open"></i>
                        </div>
                        <span class="badge" style="background: ${isExpanded ? 'var(--primary-dark)' : 'var(--primary)'}; color: white; padding: 4px 10px; border-radius: 9999px; font-weight: bold; font-size: 0.8rem;">
                            ${totalPendingInArea} GEDOs
                        </span>
                    </div>
                    <div>
                        <h3 style="margin: 0; color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700; font-size: 1.25rem;">${areaTitle}</h3>
                        <p style="margin: 6px 0 0 0; color: #64748b; font-size: 0.85rem;">Gerencia de ${areaTitle}</p>
                    </div>
                    <div style="margin-top: auto; display: flex; align-items: center; gap: 6px; color: var(--primary); font-weight: 700; font-size: 0.9rem;">
                        ${isExpanded ? 'Contraer' : 'Ver Detalles'} <i class="fa-solid ${isExpanded ? 'fa-chevron-up' : 'fa-chevron-down'}"></i>
                    </div>
                </div>
            `;
        }
    });

    html += `</div>`;

    // Renderizar detalles si hay un área expandida
    if (expandedPendientesArea && currentPendientesAsociacionData[expandedPendientesArea]) {
        const area = currentPendientesAsociacionData[expandedPendientesArea];
        const areaTitle = GERENCIA_TITLES[expandedPendientesArea] || area.area_nombre;
        
        let tratasHtml = `
            <div class="pendientes-details-wrapper" style="background: white; border-radius: 16px; border: 1px solid #e2e8f0; padding: 2rem; box-shadow: var(--card-shadow); margin-top: 1.5rem;">
                <h3 style="color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700; margin-top: 0; margin-bottom: 1.5rem; border-left: 4px solid var(--primary); padding-left: 0.75rem;">
                    Trámites de Gerencia: ${areaTitle}
                </h3>
                <div style="display: flex; flex-direction: column; gap: 1rem;">
        `;

        let activeTrataFound = false;

        Object.keys(area.tratas).forEach(trataCode => {
            const trata = area.tratas[trataCode];
            
            // Aplicar búsqueda al listado interno
            const filteredExps = trata.expedientes.filter(exp => {
                return exp.expediente.toLowerCase().includes(searchVal) ||
                       trataCode.toLowerCase().includes(searchVal) ||
                       trata.trata_nombre.toLowerCase().includes(searchVal) ||
                       exp.gedo.toLowerCase().includes(searchVal) ||
                       (exp.usuario_creador || '').toLowerCase().includes(searchVal);
            });

            if (filteredExps.length > 0) {
                const isTrataExpanded = expandedPendientesTrata === trataCode;
                if (isTrataExpanded) activeTrataFound = true;

                tratasHtml += `
                    <div style="border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden;">
                        <div onclick="togglePendientesTrata('${trataCode}')" style="background: #f8fafc; padding: 12px 18px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; user-select: none;">
                            <div>
                                <span style="font-weight: 700; color: var(--primary-dark); font-family: 'Outfit'; font-size: 1rem;">${trataCode}</span>
                                <span style="color: #64748b; font-size: 0.9rem; margin-left: 10px;">${trata.trata_nombre}</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="background: #e2e8f0; color: #475569; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold;">
                                    ${filteredExps.length} pend.
                                </span>
                                <i class="fa-solid ${isTrataExpanded ? 'fa-chevron-up' : 'fa-chevron-down'}" style="color: #64748b; font-size: 0.85rem;"></i>
                            </div>
                        </div>
                `;

                if (isTrataExpanded) {
                    tratasHtml += `
                        <div style="padding: 1rem; border-top: 1px solid #e2e8f0; overflow-x: auto;">
                            <div style="display: flex; justify-content: flex-end; margin-bottom: 0.75rem;">
                                <button class="btn-download-excel" onclick="exportPendientesExcel('${expandedPendientesArea}', '${trataCode}')" style="padding: 6px 12px; font-size: 0.8rem; display: inline-flex; align-items: center; gap: 4px; border: 1px solid #cbd5e1; background: #f1f5f9; color: #334155; cursor: pointer; border-radius: 6px; font-weight: bold;">
                                    <i class="fa-solid fa-file-excel"></i> Exportar Trámite
                                </button>
                            </div>
                            <table class="minimal-table" style="width: 100%; margin-top: 0;">
                                <thead>
                                    <tr>
                                        <th style="padding: 10px; text-align: left; font-size: 0.75rem;">Expediente</th>
                                        <th style="padding: 10px; text-align: left; font-size: 0.75rem;">Documento GEDO de Egreso</th>
                                        <th style="padding: 10px; text-align: left; font-size: 0.75rem;">Usuario Creador</th>
                                        <th style="padding: 10px; text-align: left; font-size: 0.75rem;">Fecha Creación</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;

                    filteredExps.forEach(exp => {
                        tratasHtml += `
                            <tr>
                                <td style="padding: 10px; font-weight: 600; color: #1e293b; font-size: 0.85rem;">${exp.expediente}</td>
                                <td style="padding: 10px; font-family: monospace; color: var(--primary-dark); font-size: 0.85rem;">${exp.gedo}</td>
                                <td style="padding: 10px; color: #475569; font-size: 0.85rem;">${exp.usuario_creador || '-'}</td>
                                <td style="padding: 10px; color: #64748b; font-size: 0.85rem;">${exp.fecha_creacion}</td>
                            </tr>
                        `;
                    });

                    tratasHtml += `
                                </tbody>
                            </table>
                        </div>
                    `;
                }

                tratasHtml += `</div>`;
            }
        });

        tratasHtml += `
                </div>
            </div>
        `;

        html += tratasHtml;
        
        // Reset expanded trata if it doesn't exist anymore under the search/filter
        if (!activeTrataFound) {
            expandedPendientesTrata = null;
        }
    }

    if (!hasData) {
        container.innerHTML = `
            <div style="padding: 3rem; text-align: center; color: #64748b; background: white; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: var(--card-shadow);">
                No se encontraron pendientes de asociación que coincidan con la búsqueda.
            </div>
        `;
        return;
    }

    container.innerHTML = html;
    
    // Quick GSAP Entry animation
    gsap.from(".area-card-item", { opacity: 0, y: 10, stagger: 0.05, duration: 0.3, ease: "power2.out" });
}
window.renderPendientesAsociacion = renderPendientesAsociacion;

function filterPendientes() {
    renderPendientesAsociacion();
}
window.filterPendientes = filterPendientes;

function togglePendientesArea(areaKey) {
    if (expandedPendientesArea === areaKey) {
        expandedPendientesArea = null;
        expandedPendientesTrata = null;
    } else {
        expandedPendientesArea = areaKey;
        expandedPendientesTrata = null; // Reset nested selection
    }
    renderPendientesAsociacion();
}
window.togglePendientesArea = togglePendientesArea;

function togglePendientesTrata(trataCode) {
    if (expandedPendientesTrata === trataCode) {
        expandedPendientesTrata = null;
    } else {
        expandedPendientesTrata = trataCode;
    }
    renderPendientesAsociacion();
}
window.togglePendientesTrata = togglePendientesTrata;

function exportPendientesExcel(areaKey, trataCode) {
    try {
        if (!currentPendientesAsociacionData || !currentPendientesAsociacionData[areaKey]) return;
        const trata = currentPendientesAsociacionData[areaKey].tratas[trataCode];
        if (!trata || !trata.expedientes) return;

        const rows = trata.expedientes.map(exp => ({
            "Expediente": exp.expediente,
            "Documento GEDO": exp.gedo,
            "Usuario Creador": exp.usuario_creador || '',
            "Fecha Creación": exp.fecha_creacion
        }));

        const worksheet = XLSX.utils.json_to_sheet(rows);
        const workbook = XLSX.utils.book_new();
        Xlimits = XLSX.utils.book_append_sheet(workbook, worksheet, "Pendientes");

        // Auto-fit column widths
        const colWidths = [
            { wch: 30 },
            { wch: 35 },
            { wch: 20 },
            { wch: 25 }
        ];
        worksheet['!cols'] = colWidths;

        XLSX.writeFile(workbook, `pendientes_asociacion_${trataCode}.xlsx`);
    } catch (e) {
        alert("Error exportando a Excel: " + e.message);
    }
}
window.exportPendientesExcel = exportPendientesExcel;

// ==========================================
// SECCIÓN: ANALYTICS (ESTADÍSTICAS & DATASETS)
// ==========================================

let selectedAnalyticsUsuario = 'all';
let selectedDatasetsUsuario = 'all';

function handleAnalyticsUsuarioFilterChange(val) {
    selectedAnalyticsUsuario = val;
    loadAnalyticsEstadistica();
}
window.handleAnalyticsUsuarioFilterChange = handleAnalyticsUsuarioFilterChange;

function handleDatasetsUsuarioFilterChange(val) {
    selectedDatasetsUsuario = val;
    loadAnalyticsDatasets();
}
window.handleDatasetsUsuarioFilterChange = handleDatasetsUsuarioFilterChange;

async function loadAnalyticsEstadistica() {
    const kpiContainer = document.getElementById('permisos-kpi-cards');
    if (kpiContainer) {
        kpiContainer.innerHTML = `
            <div class="loading-overlay" style="grid-column: 1/-1; min-height: 100px;">
                <span class="loader"></span>
                <p style="margin-top: 0.5rem; color: #64748b; font-size: 0.9rem;">Cargando estadísticas de permisos...</p>
            </div>
        `;
    }

    try {
        const res = await def_fetch(`${API_BASE}/analytics/permisos-obra`);
        if (!res || !res.ok) {
            throw new Error("Error cargando los datos del servidor");
        }
        const data = await res.json();

        // Populate dropdown
        const selectEl = document.getElementById('filter-analytics-usuario');
        if (selectEl) {
            const uniqueUsers = [...new Set(data.monthly_data.map(item => item.usuario).filter(Boolean))];
            uniqueUsers.sort();
            
            let optionsHtml = `<option value="all" ${selectedAnalyticsUsuario === 'all' ? 'selected' : ''}>[Todos]</option>`;
            uniqueUsers.forEach(u => {
                optionsHtml += `<option value="${u}" ${selectedAnalyticsUsuario === u ? 'selected' : ''}>${u === currentUser?.username ? `${u} (Yo)` : u}</option>`;
            });
            selectEl.innerHTML = optionsHtml;
        }

        // Filter or Aggregate monthly_data based on user selection
        let monthly_data = [];
        if (selectedAnalyticsUsuario && selectedAnalyticsUsuario !== 'all') {
            monthly_data = data.monthly_data.filter(item => item.usuario === selectedAnalyticsUsuario);
        } else {
            // Aggregate/sum cant by (anio, mes, trata, descripcion_trata)
            const aggMap = {};
            data.monthly_data.forEach(item => {
                const key = `${item.anio}-${item.mes}-${item.trata}`;
                if (!aggMap[key]) {
                    aggMap[key] = {
                        anio: item.anio,
                        mes: item.mes,
                        trata: item.trata,
                        descripcion_trata: item.descripcion_trata,
                        cant: 0
                    };
                }
                aggMap[key].cant += item.cant;
            });
            monthly_data = Object.values(aggMap);
        }

        // 1. Preparar variables y periodos
        let maxAnio = 2022;
        let maxMes = 1;
        if (monthly_data && monthly_data.length > 0) {
            monthly_data.forEach(item => {
                if (item.anio > maxAnio) {
                    maxAnio = item.anio;
                    maxMes = item.mes;
                } else if (item.anio === maxAnio && item.mes > maxMes) {
                    maxMes = item.mes;
                }
            });
        } else {
            const now = new Date();
            maxAnio = now.getFullYear();
            maxMes = now.getMonth() + 1;
        }

        const periods = [];
        let currY = 2022;
        let currM = 1;
        while (currY < maxAnio || (currY === maxAnio && currM <= maxMes)) {
            periods.push({ anio: currY, mes: currM });
            currM++;
            if (currM > 12) {
                currM = 1;
                currY++;
            }
        }

        const labels = periods.map(p => `${MESES[p.mes - 1].substring(0, 3)} ${p.anio}`);

        const trataMap = {};
        if (monthly_data) {
            monthly_data.forEach(item => {
                if (!trataMap[item.trata]) {
                    trataMap[item.trata] = item.descripcion_trata || item.trata;
                }
            });
        }

        const uniqueTratas = Object.keys(trataMap);

        const colors = {
            'MDUG3001A': '#002d47',
            'MDUG1501J': '#0076bb',
            'MDUG3402A': '#0ea5e9'
        };
        const defaultColors = ['#002d47', '#0076bb', '#0ea5e9', '#64748b'];

        const chartDatasets = uniqueTratas.map((trataCode, idx) => {
            const dataValues = periods.map(p => {
                const match = monthly_data.find(item => item.anio === p.anio && item.mes === p.mes && item.trata === trataCode);
                return match ? match.cant : 0;
            });

            return {
                label: trataMap[trataCode] || trataCode,
                data: dataValues,
                backgroundColor: colors[trataCode] || defaultColors[idx % defaultColors.length],
                borderRadius: 4,
                borderWidth: 0,
                trataCode: trataCode
            };
        });

        // Función para recalcular y re-renderizar las KPI Cards año a año según las tratas visibles
        function updateKPICards() {
            if (!kpiContainer) return;

            const visibleTratas = [];
            if (permisosObraChart) {
                permisosObraChart.data.datasets.forEach((dataset, idx) => {
                    if (permisosObraChart.isDatasetVisible(idx)) {
                        visibleTratas.push(dataset.trataCode);
                    }
                });
            } else {
                // Por defecto al cargar, todas visibles
                visibleTratas.push(...uniqueTratas);
            }

            const yearlySums = {};
            const activeYears = [...new Set(periods.map(p => p.anio))];
            activeYears.forEach(y => { yearlySums[y] = 0; });

            if (monthly_data) {
                monthly_data.forEach(item => {
                    if (visibleTratas.includes(item.trata)) {
                        if (yearlySums[item.anio] !== undefined) {
                            yearlySums[item.anio] += item.cant;
                        }
                    }
                });
            }

            kpiContainer.innerHTML = '';
            const sortedYears = activeYears.sort((a, b) => b - a);
            sortedYears.forEach(year => {
                const count = yearlySums[year] || 0;
                const kpiCard = document.createElement('div');
                kpiCard.className = 'meta-card';
                kpiCard.style.minHeight = '140px';
                kpiCard.style.padding = '20px 24px';

                kpiCard.innerHTML = `
                    <div class="meta-card-label">Permisos Año ${year}</div>
                    <div class="meta-card-value" style="font-size: 2.5rem;">${count.toLocaleString('es-AR')}</div>
                    <div class="meta-card-sub">${year === 2026 ? 'Año en curso (acumulado)' : 'Permisos aprobados (egreso)'}</div>
                `;
                kpiContainer.appendChild(kpiCard);
            });
        }

        // 2. Renderizar gráfico de barras mensual y registrar evento del legend
        const chartCanvas = document.getElementById('permisosObraChart');
        if (chartCanvas) {
            const ctx = chartCanvas.getContext('2d');
            
            if (permisosObraChart) {
                permisosObraChart.destroy();
            }

            permisosObraChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: chartDatasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            onClick: function(e, legendItem, legend) {
                                // Alternar visibilidad de la serie (comportamiento base de Chart.js)
                                const index = legendItem.datasetIndex;
                                const ci = legend.chart;
                                if (ci.isDatasetVisible(index)) {
                                    ci.hide(index);
                                    legendItem.hidden = true;
                                } else {
                                    ci.show(index);
                                    legendItem.hidden = false;
                                }
                                // Actualizar dinámicamente los totales anuales de las tarjetas
                                updateKPICards();
                            },
                            labels: {
                                font: {
                                    family: 'Outfit',
                                    size: 11
                                }
                            }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    return `${context.dataset.label}: ${context.parsed.y.toLocaleString('es-AR')}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            stacked: true,
                            grid: {
                                display: true,
                                drawOnChartArea: true,
                                drawTicks: false,
                                color: function(context) {
                                    const index = context.index;
                                    if (index > 0 && index < periods.length) {
                                        const currYear = periods[index].anio;
                                        const prevYear = periods[index - 1].anio;
                                        if (currYear !== prevYear) {
                                            return '#cbd5e1';
                                        }
                                    }
                                    return 'transparent';
                                },
                                lineWidth: function(context) {
                                    const index = context.index;
                                    if (index > 0 && index < periods.length) {
                                        const currYear = periods[index].anio;
                                        const prevYear = periods[index - 1].anio;
                                        if (currYear !== prevYear) {
                                            return 1.5;
                                        }
                                    }
                                    return 0;
                                },
                                borderDash: [4, 4]
                            },
                            ticks: {
                                font: {
                                    family: 'Outfit',
                                    size: 11
                                }
                            }
                        },
                        y: {
                            stacked: true,
                            beginAtZero: true,
                            grid: {
                                color: '#f1f5f9'
                            },
                            ticks: {
                                font: {
                                    family: 'Outfit',
                                    size: 11
                                }
                            }
                        }
                    }
                }
            });

            // Llamar inicialmente para poblar las KPI Cards
            updateKPICards();
        }

    } catch (err) {
        if (kpiContainer) {
            kpiContainer.innerHTML = `
                <div class="error-message" style="grid-column: 1/-1;">
                    <p>Error cargando estadísticas: ${err.message}</p>
                </div>
            `;
        }
    }
}

function switchAnalyticsTab(tabId) {
    document.querySelectorAll('.analytics-tab-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    document.querySelectorAll('.analytics-panel').forEach(p => p.classList.remove('active'));
    const targetPanel = document.getElementById(`analytics-panel-${tabId}`);
    if (targetPanel) targetPanel.classList.add('active');
}

async function loadAnalyticsDatasets() {
    const selectEl = document.getElementById('filter-datasets-usuario');
    if (!selectEl) return;
    
    try {
        const res = await def_fetch(`${API_BASE}/analytics/permisos-obra`);
        if (res && res.ok) {
            const data = await res.json();
            const uniqueUsers = [...new Set(data.monthly_data.map(item => item.usuario).filter(Boolean))];
            uniqueUsers.sort();
            
            let optionsHtml = `<option value="all" ${selectedDatasetsUsuario === 'all' ? 'selected' : ''}>[Todos]</option>`;
            uniqueUsers.forEach(u => {
                optionsHtml += `<option value="${u}" ${selectedDatasetsUsuario === u ? 'selected' : ''}>${u === currentUser?.username ? `${u} (Yo)` : u}</option>`;
            });
            selectEl.innerHTML = optionsHtml;
        }
    } catch (e) {
        console.error("Error loading datasets users:", e);
    }
}

async function downloadDataset(datasetId) {
    try {
        if (datasetId === 'permisos_obra') {
            const res = await def_fetch(`${API_BASE}/analytics/permisos-obra`);
            if (!res || !res.ok) throw new Error("No se pudo obtener el dataset");
            const data = await res.json();
            
            let filteredData = [];
            if (selectedDatasetsUsuario && selectedDatasetsUsuario !== 'all') {
                filteredData = data.monthly_data.filter(item => item.usuario === selectedDatasetsUsuario);
            } else {
                // Sum up by trata and period
                const aggMap = {};
                data.monthly_data.forEach(item => {
                    const key = `${item.anio}-${item.mes}-${item.trata}`;
                    if (!aggMap[key]) {
                        aggMap[key] = {
                            anio: item.anio,
                            mes: item.mes,
                            trata: item.trata,
                            descripcion_trata: item.descripcion_trata,
                            cant: 0
                        };
                    }
                    aggMap[key].cant += item.cant;
                });
                filteredData = Object.values(aggMap);
            }

            const rows = filteredData.map(item => ({
                "Año": item.anio,
                "Mes": MESES[item.mes - 1],
                "Acrónimo": "IFPDO",
                "Descripción": item.descripcion_trata || "Permiso de Obra (Egresos Efectivos)",
                "Cantidad Otorgados": item.cant
            }));
            
            const worksheet = XLSX.utils.json_to_sheet(rows);
            const workbook = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(workbook, worksheet, "Permisos de Obra");
            
            worksheet['!cols'] = [{ wch: 10 }, { wch: 15 }, { wch: 15 }, { wch: 35 }, { wch: 20 }];
            
            const fileName = selectedDatasetsUsuario === 'all' 
                ? "dataset_permisos_obra_IFPDO_TODOS.xlsx"
                : `dataset_permisos_obra_IFPDO_${selectedDatasetsUsuario}.xlsx`;

            XLSX.writeFile(workbook, fileName);
        } else if (datasetId === 'egresos_transacciones') {
            alert("Preparando descarga del dataset de Egresos...");
            const res = await def_fetch(`${API_BASE}/reporte/cierre_mes`);
            if (!res || !res.ok) throw new Error("No se pudieron consultar los datos");
            const data = await res.json();
            
            const rows = [];
            Object.keys(data).forEach(ger => {
                const gerData = data[ger];
                if (gerData && Array.isArray(gerData)) {
                    gerData.forEach(row => {
                        rows.push({
                            "Gerencia": ger.toUpperCase(),
                            "Trata": row.trata,
                            "Detalle": row.trata_nombre || '',
                            "Año": row.anio,
                            "Mes": MESES[row.mes - 1],
                            "Egresos Efectivos": row.egresos_efectivos || 0,
                            "Egresos No Efectivos": row.egresos_no_efectivos || 0
                        });
                    });
                }
            });
            
            const worksheet = XLSX.utils.json_to_sheet(rows);
            const workbook = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(workbook, worksheet, "Consolidado Egresos");
            XLSX.writeFile(workbook, "dataset_egresos_consolidados.xlsx");
        }
    } catch (e) {
        alert("Error al descargar dataset: " + e.message);
    }
}

// Exponer funciones globales
window.loadAnalyticsEstadistica = loadAnalyticsEstadistica;
window.switchAnalyticsTab = switchAnalyticsTab;
window.loadAnalyticsDatasets = loadAnalyticsDatasets;
window.downloadDataset = downloadDataset;




