import { state, loadAuthToken } from './state.js';
import { mountView } from './router.js';
import { renderLandingView, loadLandingStats } from './views/landing/landing.js';
import { renderRRHHView, initRRHHReportView } from './views/reportes/reporte_rrhh/rrhh.js';

// Exponer en window para interoperabilidad total
window.renderLandingView = renderLandingView;
window.loadLandingStats = loadLandingStats;
window.renderRRHHView = renderRRHHView;
window.initRRHHReportView = initRRHHReportView;
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
