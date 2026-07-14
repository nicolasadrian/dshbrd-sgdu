import { state, loadAuthToken } from './state.js';
import { renderLandingView } from './views/landing.js';
import { renderRRHHView } from './views/rrhh.js';

// Exponer renderers en window para ser consumidos por el router showView
window.renderLandingView = renderLandingView;
window.renderRRHHView = renderRRHHView;

// Sincronizar estado con las variables globales del layout heredado (app.js)
function syncState() {
    state.currentUser = window.currentUser || null;
    state.authToken = window.authToken || loadAuthToken();
}

// Sincronización continua
setInterval(syncState, 500);
syncState();

console.log("Tablero SGDU - Frontend Modular cargado correctamente.");
