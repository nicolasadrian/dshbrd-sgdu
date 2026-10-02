import { state, loadAuthToken } from './state.js';
import { mountView } from './router.js';
import { renderLandingView, loadLandingStats } from './views/landing/landing.js';
import { 
    loadRRHHHubView, 
    loadRRHHGerenciaView, 
    filterRRHHGerenciaTable, 
    initRRHHCargaView, 
    openRRHHAgentPage, 
    closeRRHHAgentPage 
} from './views/reportes/reporte_rrhh/rrhh.js';
import {
    loadProductividadHubView,
    loadProductividadGerenciaView,
    onSelectAnalistaGerencia,
    loadProductividadGerenciaAnalistaData,
    downloadIndividualPDFGerencia,
    filterProductividadGerenciaTable,
    openProductividadModal,
    closeProductividadModal,
    loadProductividadAnalistaData,
    downloadIndividualPDF,
    downloadSectorComparativePDF
} from './views/reportes/productividad_analistas/productividad.js';
import {
    loadSeguimientoMHView,
    refreshSeguimientoMH,
    loadSeguimientoMHExpedientes,
    changeMHPage,
    debounceMHSearch,
    filterByMHAgente,
    toggleMHSelectRow,
    toggleMHSelectAll,
    submitMHBulkAssignment,
    openMHExpedienteModal,
    closeMHExpedienteModal,
    switchMHTab
} from './views/reportes/seguimiento_mh/seguimiento_mh.js';

// Exponer en window para interoperabilidad total
window.renderLandingView = renderLandingView;
window.loadLandingStats = loadLandingStats;
window.loadRRHHHubView = loadRRHHHubView;
window.loadRRHHGerenciaView = loadRRHHGerenciaView;
window.filterRRHHGerenciaTable = filterRRHHGerenciaTable;
window.initRRHHCargaView = initRRHHCargaView;
window.openRRHHAgentPage = openRRHHAgentPage;
window.closeRRHHAgentPage = closeRRHHAgentPage;

window.loadProductividadHubView = loadProductividadHubView;
window.loadProductividadGerenciaView = loadProductividadGerenciaView;
window.onSelectAnalistaGerencia = onSelectAnalistaGerencia;
window.loadProductividadGerenciaAnalistaData = loadProductividadGerenciaAnalistaData;
window.downloadIndividualPDFGerencia = downloadIndividualPDFGerencia;
window.filterProductividadGerenciaTable = filterProductividadGerenciaTable;
window.openProductividadModal = openProductividadModal;
window.closeProductividadModal = closeProductividadModal;
window.downloadIndividualPDF = downloadIndividualPDF;
window.downloadSectorComparativePDF = downloadSectorComparativePDF;

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

window.mountView = mountView;

// Sincronizar estado con variables globales del layout heredado (app.js)
function syncState() {
    state.currentUser = window.currentUser || JSON.parse(localStorage.getItem('sgdu_user') || 'null');
    state.authToken = window.authToken || loadAuthToken();
}

// Sincronización periódica
setInterval(syncState, 500);
syncState();

console.log("Tablero SGDU - Frontend Modular cargado y Router Activo.");
