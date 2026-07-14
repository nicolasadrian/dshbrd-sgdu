// Estado global de la aplicación (Tablero SGDU)
export const state = {
    currentUser: null,
    authToken: null,
    currentView: 'landing',
    familiasConfig: null
};

// Helpers para localStorage
export function loadAuthToken() {
    state.authToken = localStorage.getItem('sgdu_token') || localStorage.getItem('authToken');
    return state.authToken;
}

export function saveAuthToken(token) {
    state.authToken = token;
    localStorage.setItem('sgdu_token', token);
    localStorage.setItem('authToken', token);
}

export function clearAuthToken() {
    state.authToken = null;
    localStorage.removeItem('sgdu_token');
    localStorage.removeItem('authToken');
}
