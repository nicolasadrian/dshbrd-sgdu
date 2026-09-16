// Router Dinámico y Registro de Vistas Modulares - Tablero SGDU
import { state } from './state.js';

// Mapa de rutas y resolutores de componentes/templates
const VIEW_ROUTES = {
    // Landing
    'landing': () => import('./views/landing/landing.js'),

    // Seguimiento DGROC
    'dgroc': () => import('./views/seguimiento/dgroc/dgroc_hub.html?raw'),
    'catastro': () => import('./views/seguimiento/dgroc/catastro.html?raw'),
    'instalaciones': () => import('./views/seguimiento/dgroc/instalaciones.html?raw'),
    'conforme': () => import('./views/seguimiento/dgroc/conforme.html?raw'),
    'contable': () => import('./views/seguimiento/dgroc/contable.html?raw'),
    'etapa_proyecto': () => import('./views/seguimiento/dgroc/etapa_proyecto.html?raw'),
    'aviso_obra': () => import('./views/seguimiento/dgroc/aviso_obra.html?raw'),
    'trata_detail': () => import('./views/seguimiento/dgroc/trata_detail.html?raw'),

    // Seguimiento DGIUR
    'dgiur': () => import('./views/seguimiento/dgiur/dgiur_hub.html?raw'),
    'morfologia': () => import('./views/seguimiento/dgiur/morfologia.html?raw'),
    'aph': () => import('./views/seguimiento/dgiur/aph.html?raw'),
    'usos': () => import('./views/seguimiento/dgiur/usos.html?raw'),
    'publico_privado': () => import('./views/seguimiento/dgiur/publico_privado.html?raw'),
    'copua': () => import('./views/seguimiento/dgiur/copua.html?raw'),
    'privada': () => import('./views/seguimiento/dgiur/privada.html?raw'),

    // Buzones
    'buzones': () => import('./views/buzones/buzones_hub.html?raw'),
    'buzones_dgroc_hub': () => import('./views/buzones/buzones_dgroc_hub.html?raw'),
    'buzones_dgiur_hub': () => import('./views/buzones/buzones_dgiur_hub.html?raw'),
    'buzon-analista-detalle': () => import('./views/buzones/buzon_analista_detalle.html?raw'),

    // Reportes
    'seguimiento': () => import('./views/reportes/metas/metas.html?raw'),
    'metas': () => import('./views/reportes/metas/metas.html?raw'),
    'cierre': () => import('./views/reportes/cierre_mes/cierre.html?raw'),
    'sla': () => import('./views/reportes/tiempos_tramitacion/sla.html?raw'),
    'subsanaciones': () => import('./views/reportes/subsanaciones/subsanaciones.html?raw'),
    'productividad_analistas': () => import('./views/reportes/productividad_analistas/productividad_analistas.html?raw'),
    'reportes_rrhh': () => import('./views/reportes/reporte_rrhh/rrhh.js'),
    'universo_tratas': () => import('./views/reportes/universo_tratas/universo_tratas.html?raw'),
    'planificacion_nov_2026': () => import('./views/reportes/planificacion_nov_2026/planificacion_nov_2026.html?raw'),
    'familia_tramites': () => import('./views/reportes/family/family.html?raw'),
    'family': () => import('./views/reportes/family/family.html?raw'),

    // Analytics
    'analytics_estadistica': () => import('./views/analytics/estadistica/analytics_estadistica.html?raw'),
    'analytics_datasets': () => import('./views/analytics/datasets/analytics_datasets.html?raw'),
    'analytics_m2_permisados': () => import('./views/analytics/estadistica/analytics_m2_permisados.html?raw'),
    'analytics_avisos_obra': () => import('./views/analytics/estadistica/analytics_avisos_obra.html?raw'),

    // Ciudad 3D
    'ciudad3d_home': () => import('./views/ciudad3d/home/ciudad3d_home.html?raw'),
    'ciudad3d_troneras': () => import('./views/ciudad3d/extensiones_irregulares/c3d_extensiones_hub.html?raw'),
    'c3d_extensiones_hub': () => import('./views/ciudad3d/extensiones_irregulares/c3d_extensiones_hub.html?raw'),
    'c3d_extensiones_todas': () => import('./views/ciudad3d/extensiones_irregulares/c3d_extensiones_todas.html?raw'),
    'c3d_extensiones_mis_trazados': () => import('./views/ciudad3d/extensiones_irregulares/c3d_extensiones_mis_trazados.html?raw'),
    'c3d_extensiones_revision': () => import('./views/ciudad3d/extensiones_irregulares/c3d_extensiones_revision.html?raw'),
    'c3d_extensiones_equipo': () => import('./views/ciudad3d/extensiones_irregulares/c3d_extensiones_equipo.html?raw'),
    'c3d_extensiones_mapa': () => import('./views/ciudad3d/extensiones_irregulares/c3d_extensiones_mapa.html?raw'),
    'ciudad3d_manzanas_atipicas': () => import('./views/ciudad3d/manzanas_atipicas/ciudad3d_manzanas_atipicas.html?raw'),
    'ciudad3d_pdi': () => import('./views/ciudad3d/pdi/ciudad3d_pdi.html?raw'),
    'ciudad3d_pdi_validacion': () => import('./views/ciudad3d/pdi/ciudad3d_pdi_validacion.html?raw'),
    'ciudad3d_pdi_validacion_c3d': () => import('./views/ciudad3d/pdi/ciudad3d_pdi_validacion_c3d.html?raw'),

    // Contable
    'contable_plusvalia': () => import('./views/contable/calculadora/plusvalia/plusvalia.html?raw'),
    'contable_derechos': () => import('./views/contable/calculadora/derechos/derechos.html?raw'),
    'contable_seguimiento': () => import('./views/contable/calculadora/seguimiento/seguimiento.html?raw'),

    // Mis Expedientes
    'buscador': () => import('./views/mis_expedientes/buscador/buscador.html?raw'),
    'asignados-mi': () => import('./views/mis_expedientes/asignados_a_mi/asignados_mi.html?raw'),
    'favoritos': () => import('./views/mis_expedientes/marcadores/favoritos.html?raw'),
    'favoritos-seguimiento': () => import('./views/mis_expedientes/gestion_marcadores/favoritos_seguimiento.html?raw'),

    // Usuario y Backlog de Configuración
    'admin': () => import('./views/usuario/backlog/backlog_hub.html?raw'),
    'backlog': () => import('./views/usuario/backlog/backlog_hub.html?raw'),
    'backlog_hub': () => import('./views/usuario/backlog/backlog_hub.html?raw'),
    'backlog_users': () => import('./views/usuario/backlog/admin_users.html?raw'),
    'backlog_metas': () => import('./views/usuario/backlog/admin_metas.html?raw'),
    'backlog_roles': () => import('./views/usuario/backlog/admin_roles.html?raw'),
    'backlog_buzones': () => import('./views/usuario/backlog/admin_buzones.html?raw'),
    'backlog_familias': () => import('./views/usuario/backlog/admin_familias.html?raw'),
    'backlog_analistas': () => import('./views/usuario/backlog/admin_analistas.html?raw'),
    'mis_datos': () => import('./views/usuario/mis_datos/mis_datos.html?raw')
};

// Cache de templates cargados
const viewCache = new Map();

/**
 * Renderizador de vista modular
 */
export async function mountView(viewId) {
    const appContent = document.getElementById('app-content');
    if (!appContent) return;

    state.currentView = viewId;

    // Obtener o crear el contenedor <section id="viewId" class="view-container">
    let section = document.getElementById(viewId);
    if (!section) {
        section = document.createElement('section');
        section.id = viewId;
        section.className = 'view-container';
        appContent.appendChild(section);
    }

    // Ocultar otras vistas activas
    const allViews = appContent.querySelectorAll('.view-container');
    allViews.forEach(v => {
        v.classList.remove('active');
        v.style.display = 'none';
    });

    // Mostrar sección objetivo
    section.style.display = 'block';
    setTimeout(() => section.classList.add('active'), 10);

    // Cargar contenido HTML modular si aún no está cargado o si tiene loader
    if (!section.dataset.loaded) {
        const routeLoader = VIEW_ROUTES[viewId];
        if (routeLoader) {
            try {
                const mod = await routeLoader();
                if (typeof mod.renderLandingView === 'function') {
                    await mod.renderLandingView();
                } else if (typeof mod.renderRRHHView === 'function') {
                    await mod.renderRRHHView();
                } else {
                    const rawHtml = mod.default || mod;
                    section.innerHTML = rawHtml;
                }
                section.dataset.loaded = 'true';
            } catch (err) {
                console.error(`Error al cargar el módulo de la vista ${viewId}:`, err);
                section.innerHTML = `
                    <div style="padding: 3rem; text-align: center; color: #ef4444;">
                        <h3>Error al cargar la vista</h3>
                        <p>${err.message}</p>
                    </div>`;
            }
        }
    }

    // Disparar lógica de inicialización específica
    triggerViewInit(viewId);
}

/**
 * Disparador de controladores según la vista activa
 */
function triggerViewInit(viewId) {
    // Si la función de controlador global existe en window / app.js, invocarla
    if (viewId === 'landing' && typeof window.loadLandingStats === 'function') {
        window.loadLandingStats();
    } else if (viewId === 'metas' && typeof window.loadMetasData === 'function') {
        window.loadMetasData();
    } else if (viewId === 'seguimiento' && typeof window.loadSeguimientoData === 'function') {
        window.loadSeguimientoData();
    } else if (viewId === 'cierre' && typeof window.loadCierreMesData === 'function') {
        window.loadCierreMesData();
    } else if (viewId === 'sla' && typeof window.loadSLAReporte === 'function') {
        window.loadSLAReporte();
    } else if (viewId === 'subsanaciones' && typeof window.loadSubsanacionesReport === 'function') {
        window.loadSubsanacionesReport();
    } else if (viewId === 'productividad_analistas' && typeof window.loadProductividadAnalistasView === 'function') {
        window.loadProductividadAnalistasView();
    } else if (viewId === 'universo_tratas') {
        if (typeof window.loadUniversoTratas === 'function') {
            if (window._universoCurrentTab === 'buzones' && typeof window.loadUniversoBuzones === 'function') {
                window.loadUniversoBuzones();
            } else {
                window.loadUniversoTratas();
            }
        }
    } else if (viewId === 'planificacion_nov_2026' && typeof window.loadPlanificacionNov2026Data === 'function') {
        window.loadPlanificacionNov2026Data();
    } else if (viewId === 'admin' || viewId === 'backlog' || viewId === 'backlog_hub') {
        // Backlog Hub
    } else if (viewId === 'backlog_users' && typeof window.loadUsers === 'function') {
        if (typeof window.showUsersListView === 'function') window.showUsersListView();
        window.loadUsers();
    } else if (viewId === 'backlog_metas' && typeof window.loadAdminMetas === 'function') {
        if (typeof window.showMetasList === 'function') window.showMetasList();
        window.loadAdminMetas();
    } else if (viewId === 'backlog_roles' && typeof window.loadAdminRoles === 'function') {
        window.loadAdminRoles();
    } else if (viewId === 'backlog_buzones' && typeof window.loadBuzonesAccesoConfig === 'function') {
        window.loadBuzonesAccesoConfig();
    } else if (viewId === 'backlog_familias' && typeof window.loadAdminFamilias === 'function') {
        window.loadAdminFamilias();
    } else if (viewId === 'backlog_analistas' && typeof window.loadAdminAnalistas === 'function') {
        window.loadAdminAnalistas();
    } else if (viewId === 'backlog_universo_tratas' && typeof window.loadBacklogUniversoTratas === 'function') {
        window.loadBacklogUniversoTratas();
    } else if ((viewId === 'familia_tramites' || viewId === 'family') && typeof window.backToFamilySelector === 'function') {
        window.backToFamilySelector();
    } else if (viewId === 'analytics_estadistica' && typeof window.switchAnalyticsTab === 'function') {
        window.switchAnalyticsTab('landing');
    } else if (viewId === 'analytics_datasets' && typeof window.loadAnalyticsDatasets === 'function') {
        window.loadAnalyticsDatasets();
    } else if (viewId === 'analytics_m2_permisados' && typeof window.loadM2Permisados === 'function') {
        window.loadM2Permisados(true);
    } else if (viewId === 'analytics_avisos_obra' && typeof window.loadAvisosObra === 'function') {
        window.loadAvisosObra(true);
    } else if (viewId === 'ciudad3d_home' && typeof window.loadCiudad3DStats === 'function') {
        window.loadCiudad3DStats();
    } else if ((viewId === 'ciudad3d_troneras' || viewId === 'c3d_extensiones_todas' || viewId === 'c3d_extensiones_mis_trazados' || viewId === 'c3d_extensiones_revision' || viewId === 'c3d_extensiones_equipo' || viewId === 'c3d_extensiones_mapa') && typeof window.loadCiudad3DTroneras === 'function') {
        window.loadCiudad3DTroneras().then(() => {
            if (viewId === 'c3d_extensiones_mapa' && typeof window.initLFIMap === 'function') {
                setTimeout(() => window.initLFIMap(), 150);
            }
        });
    } else if (viewId === 'ciudad3d_manzanas_atipicas' && typeof window.loadCiudad3DManzanasAtipicas === 'function') {
        window.loadCiudad3DManzanasAtipicas();
    } else if (viewId === 'ciudad3d_pdi' && typeof window.loadCiudad3DPDI === 'function') {
        window.loadCiudad3DPDI();
    } else if (viewId === 'ciudad3d_pdi_validacion' && typeof window.loadPDIValidations === 'function') {
        window.loadPDIValidations();
    } else if (viewId === 'ciudad3d_pdi_validacion_c3d' && typeof window.loadCiudad3DSecciones === 'function') {
        window.loadCiudad3DSecciones();
    } else if (viewId === 'buscador') {
        const yearInput = document.getElementById('search-anio');
        if (yearInput && !yearInput.value) yearInput.value = new Date().getFullYear();
        const rulesContainer = document.getElementById('search-rules-list-container');
        if (rulesContainer && rulesContainer.children.length === 0 && typeof window.addSearchRuleRow === 'function') {
            window.addSearchRuleRow();
        }
    } else if (viewId === 'favoritos' && typeof window.loadFavoritesView === 'function') {
        window.loadFavoritesView();
    } else if (viewId === 'asignados-mi' && typeof window.loadAsignadosMiView === 'function') {
        window.loadAsignadosMiView();
    } else if (viewId === 'favoritos-seguimiento' && typeof window.loadFavoritosSeguimientoView === 'function') {
        window.loadFavoritosSeguimientoView();
    } else if (viewId === 'mis_datos') {
        renderMisDatosView();
    } else if (viewId === 'buzones' && typeof window.updateBuzonesViewHeader === 'function') {
        window.updateBuzonesViewHeader();
    }

    // Carga de reportes si es gerencia de seguimiento
    if (viewId === 'publico_privado') {
        if (typeof window.loadGenericGerenciaProdView === 'function') {
            setTimeout(() => window.loadGenericGerenciaProdView('publico_privado'), 50);
        } else if (typeof window.loadPublicoPrivadoView === 'function') {
            setTimeout(() => window.loadPublicoPrivadoView(), 50);
        }
    } else if (viewId === 'copua' || viewId === 'privada') {
        if (typeof window.loadGenericGerenciaProdView === 'function') {
            setTimeout(() => window.loadGenericGerenciaProdView(viewId), 50);
        }
    } else {
        const gerencias = ['catastro', 'instalaciones', 'conforme', 'contable', 'etapa_proyecto', 'aviso_obra', 'morfologia', 'aph', 'usos'];
        if (gerencias.includes(viewId) && typeof window.loadConsolidatedReport === 'function') {
            setTimeout(() => window.loadConsolidatedReport(viewId), 50);
        }
    }
}

/**
 * Renderizador de Mis Datos de Usuario
 */
function renderMisDatosView() {
    const container = document.getElementById('mis-datos-container');
    if (!container) return;
    const user = state.currentUser || JSON.parse(localStorage.getItem('sgdu_user') || '{}');
    container.innerHTML = `
        <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 25px; padding-bottom: 20px; border-bottom: 1px solid #e2e8f0;">
            <div style="width: 64px; height: 64px; border-radius: 50%; background: linear-gradient(135deg, var(--primary), #1e293b); color: white; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; font-weight: 700;">
                ${(user.full_name || user.username || 'U')[0].toUpperCase()}
            </div>
            <div>
                <h2 style="margin: 0; color: var(--primary-dark); font-size: 1.4rem;">${user.full_name || user.username || 'Usuario'}</h2>
                <p style="margin: 4px 0 0 0; color: #64748b; font-size: 0.95rem;">${user.username ? '@' + user.username : ''} &bull; Sector: <strong>${user.sector || 'General'}</strong> &bull; Rol: <strong>${user.role || 'Usuario'}</strong></p>
            </div>
        </div>
        <div style="margin-bottom: 20px;">
            <h3 style="font-size: 1.1rem; color: #1e293b; margin-bottom: 12px;">Permisos de Acceso Asignados</h3>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                ${Object.entries(user.permissions || {}).filter(([k, v]) => !!v).map(([perm]) => `
                    <span style="background: #f1f5f9; color: #334155; padding: 6px 12px; border-radius: 8px; font-size: 0.85rem; font-weight: 600; border: 1px solid #e2e8f0;">
                        <i class="fa-solid fa-check-circle" style="color: #10b981; margin-right: 6px;"></i>${perm}
                    </span>
                `).join('') || '<span style="color: #94a3b8; font-style: italic;">Sin permisos especiales asignados.</span>'}
            </div>
        </div>
        <div style="display: flex; justify-content: flex-end; margin-top: 30px; border-top: 1px solid #e2e8f0; padding-top: 20px;">
            <button type="button" class="btn-primary" onclick="document.getElementById('change-password-modal').style.display='flex'" style="display: flex; align-items: center; gap: 8px;">
                <i class="fa-solid fa-key"></i> Cambiar mi Contraseña
            </button>
        </div>
    `;
}
