(function(){let e=document.createElement(`link`).relList;if(e&&e.supports&&e.supports(`modulepreload`))return;for(let e of document.querySelectorAll(`link[rel="modulepreload"]`))n(e);new MutationObserver(e=>{for(let t of e)if(t.type===`childList`)for(let e of t.addedNodes)e.tagName===`LINK`&&e.rel===`modulepreload`&&n(e)}).observe(document,{childList:!0,subtree:!0});function t(e){let t={};return e.integrity&&(t.integrity=e.integrity),e.referrerPolicy&&(t.referrerPolicy=e.referrerPolicy),e.crossOrigin===`use-credentials`?t.credentials=`include`:e.crossOrigin===`anonymous`?t.credentials=`omit`:t.credentials=`same-origin`,t}function n(e){if(e.ep)return;e.ep=!0;let n=t(e);fetch(e.href,n)}})();var e={currentUser:null,authToken:null,currentView:`landing`,familiasConfig:null};function t(){return e.authToken=localStorage.getItem(`sgdu_token`)||localStorage.getItem(`authToken`),e.authToken}var n=`<!-- Hero Banner -->
<div style="
    background: linear-gradient(135deg, var(--bg-card, #1e293b), var(--primary, #3b82f6));
    border-radius: 20px;
    padding: 36px 40px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
    min-height: 160px;
">
    <!-- Dark overlay for readability -->
    <div style="position: absolute; inset: 0; border-radius: 20px;
        background: linear-gradient(120deg, rgba(10,17,34,0.82) 0%, rgba(15,30,60,0.70) 55%, rgba(8,25,50,0.78) 100%);
        backdrop-filter: blur(1px);
    "></div>
    <!-- Subtle city-grid line overlay -->
    <div style="position: absolute; inset: 0; border-radius: 20px; opacity: 0.07;
        background-image: repeating-linear-gradient(0deg, transparent, transparent 39px, rgba(125,209,252,0.8) 40px),
                          repeating-linear-gradient(90deg, transparent, transparent 59px, rgba(125,209,252,0.8) 60px);
    "></div>

    <div style="position: relative; z-index: 1; display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 16px;">
        <div>
            <p style="margin: 0 0 6px 0; font-size: 0.82rem; color: #7dd3fc; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px;">Tablero Integral de Gestión</p>
            <h1 style="margin: 0 0 8px 0; font-family: 'Outfit'; font-weight: 800; font-size: 2rem; color: white; line-height: 1.2;" id="landing-greeting">Bienvenido al Tablero SGDU</h1>
            <p style="margin: 0; font-size: 0.92rem; color: #94a3b8;" id="landing-date-str">Cargando...</p>
        </div>
        <div style="text-align: right;">
            <div style="background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.12); border-radius: 14px; padding: 14px 20px; min-width: 200px;">
                <p style="margin: 0 0 4px 0; font-size: 0.75rem; color: #7dd3fc; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">Avance del mes</p>
                <p style="margin: 0 0 8px 0; font-family: 'Outfit'; font-weight: 800; font-size: 1.3rem; color: white;" id="landing-workdays-label">Cargando...</p>
                <div style="height: 6px; background: rgba(255,255,255,0.12); border-radius: 99px; overflow: hidden;">
                    <div id="landing-progress-bar" style="height: 100%; background: linear-gradient(90deg, #38bdf8, #818cf8); border-radius: 99px; width: 0%; transition: width 1s ease;"></div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- KPI Grid -->
<div style="
    display: grid;
    grid-template-columns: repeat(4, 1fr) 1.2fr;
    grid-template-rows: auto auto;
    gap: 16px;
    margin-bottom: 32px;
    align-items: stretch;
" id="landing-kpi-grid">
    <!-- Skeleton cards while loading: 8 normales + 1 tall -->
    <div class="landing-kpi-skeleton"></div>
    <div class="landing-kpi-skeleton"></div>
    <div class="landing-kpi-skeleton"></div>
    <div class="landing-kpi-skeleton"></div>
    <div class="landing-kpi-skeleton" style="grid-column: 5; grid-row: 1 / span 2;"></div>
    <div class="landing-kpi-skeleton"></div>
    <div class="landing-kpi-skeleton"></div>
    <div class="landing-kpi-skeleton"></div>
    <div class="landing-kpi-skeleton"></div>
</div>

<!-- Separador visual -->
<div style="display: flex; align-items: center; margin: 40px 0 24px 0; gap: 16px;">
    <div style="flex: 1; height: 1px; background: linear-gradient(90deg, transparent, #e2e8f0, #cbd5e1);"></div>
    <span style="font-family: 'Outfit'; font-weight: 800; font-size: 0.85rem; color: #475569; letter-spacing: 2px; text-transform: uppercase; background: #f1f5f9; padding: 4px 16px; border-radius: 99px; border: 1px solid #e2e8f0; display: flex; align-items: center; gap: 8px;">
        <i class="fa-solid fa-chart-pie" style="color: var(--primary);"></i> Desglose por Dirección General
    </span>
    <div style="flex: 1; height: 1px; background: linear-gradient(90deg, #cbd5e1, #e2e8f0, transparent);"></div>
</div>

<!-- Grilla DGROC vs DGIUR -->
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 28px; margin-bottom: 40px;">
    <!-- DGROC Column -->
    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 18px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02), 0 2px 4px -1px rgba(0,0,0,0.01);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; border-bottom: 2px solid #eff6ff; padding-bottom: 12px;">
            <h2 style="font-family: 'Outfit'; font-weight: 800; font-size: 1.35rem; color: #1e3a8a; margin: 0; display: flex; align-items: center; gap: 8px;">
                DGROC
            </h2>
            <span style="font-size: 0.72rem; font-weight: 700; color: #3b82f6; background: #eff6ff; padding: 3px 10px; border-radius: 99px; text-transform: uppercase; letter-spacing: 0.5px;">6 Gerencias</span>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;" id="landing-dgroc-grid">
            <div style="grid-column: span 2; text-align: center; padding: 2rem; color: #94a3b8;">
                <span class="loader" style="width: 24px; height: 24px; border-width: 2.5px;"></span>
                <p style="margin-top: 8px; font-size: 0.85rem;">Cargando métricas de DGROC...</p>
            </div>
        </div>
    </div>

    <!-- DGIUR Column -->
    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 18px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02), 0 2px 4px -1px rgba(0,0,0,0.01);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; border-bottom: 2px solid #f0fdf4; padding-bottom: 12px;">
            <h2 style="font-family: 'Outfit'; font-weight: 800; font-size: 1.35rem; color: #065f46; margin: 0; display: flex; align-items: center; gap: 8px;">
                DGIUR
            </h2>
            <span style="font-size: 0.72rem; font-weight: 700; color: #10b981; background: #f0fdf4; padding: 3px 10px; border-radius: 99px; text-transform: uppercase; letter-spacing: 0.5px;">3 Gerencias</span>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;" id="landing-dgiur-grid">
            <div style="grid-column: span 2; text-align: center; padding: 2rem; color: #94a3b8;">
                <span class="loader" style="width: 24px; height: 24px; border-width: 2.5px;"></span>
                <p style="margin-top: 8px; font-size: 0.85rem;">Cargando métricas de DGIUR...</p>
            </div>
        </div>
    </div>
</div>
`;function r(){let e=document.getElementById(`landing`);e&&(e.innerHTML=n),c()}function i({icon:e,iconBg:t,iconColor:n,label:r,value:i,sub:a,valueColor:o,gridStyle:s,tall:c}){let l=c?`2.8rem`:`1.75rem`,u=c?`56px`:`44px`;return`
        <div class="landing-kpi-card" style="${s||``}; ${c?`justify-content:center; align-items:center; text-align:center;`:``}">
            <div class="landing-kpi-icon" style="background:${t}; color:${n}; width:${u}; height:${u}; font-size:${c?`1.4rem`:`1.15rem`}; ${c?`margin: 0 auto 8px auto;`:``}">
                <i class="${e}"></i>
            </div>
            <span class="landing-kpi-label" style="${c?`text-align:center; margin-bottom:8px; display:block;`:``}">${r}</span>
            <span class="landing-kpi-value" style="color:${o||`#1e293b`}; font-size:${l};" data-target="${i}">${i.toLocaleString(`es-AR`)}</span>
            ${a?`<span class="landing-kpi-sub" style="${c?`text-align:center; font-size:0.9rem; margin-top:6px;`:``}">${a}</span>`:``}
        </div>
    `}function a({label:e,mesVal:t,acumVal:n,showAcum:r=!0,intVal:i=null,efVal:a=null,neVal:o=null}){return`
        <div class="landing-kpi-card" style="padding: 16px; display: flex; flex-direction: column; gap: 12px; transition: transform 0.2s, box-shadow 0.2s;">
            <div style="display: flex; align-items: center;">
                <span style="font-size: 0.8rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">${e}</span>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; border-top: 1px solid #f1f5f9; padding-top: 10px; margin-top: 4px;">
                <div>
                    <span style="font-size: 1.45rem; font-weight: 800; color: #1e293b; display: block;" class="landing-kpi-value" data-target="${t||0}">${(t||0).toLocaleString(`es-AR`)}</span>
                    <span style="font-size: 0.65rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.3px;">${i==null?`Mes`:`Total`}</span>
                </div>
                ${i==null?r?`
                <div style="border-left: 1px dashed #e2e8f0; padding-left: 12px;">
                    <span style="font-size: 1.45rem; font-weight: 800; color: var(--primary); display: block;" class="landing-kpi-value" data-target="${n||0}">${(n||0).toLocaleString(`es-AR`)}</span>
                    <span style="font-size: 0.65rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.3px;">Mar-Hoy</span>
                    ${a!=null&&o!=null?`
                    <span style="font-size: 0.6rem; font-weight: 600; color: #94a3b8; display: block; margin-top: 3px; line-height: 1.1;">
                        Ef: ${a.toLocaleString(`es-AR`)}<br>No Ef: ${o.toLocaleString(`es-AR`)}
                    </span>
                    `:``}
                </div>
                `:`
                <div style="border-left: 1px dashed #e2e8f0; padding-left: 12px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 0.68rem; font-weight: 600; color: #94a3b8; font-style: italic; text-transform: uppercase;">Stock vivo</span>
                </div>
                `:`
                <div style="border-left: 1px dashed #e2e8f0; padding-left: 12px;">
                    <span style="font-size: 1.45rem; font-weight: 800; color: #64748b; display: block;" class="landing-kpi-value" data-target="${i}">${i.toLocaleString(`es-AR`)}</span>
                    <span style="font-size: 0.65rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.3px;">Interv.</span>
                </div>
                `}
            </div>
        </div>
    `}function o(e){if(!e)return``;let[t,n]=e.split(`-`).map(Number);return`(${[`Ene`,`Feb`,`Mar`,`Abr`,`May`,`Jun`,`Jul`,`Ago`,`Sep`,`Oct`,`Nov`,`Dic`][n-1]} ${t})`}function s(e,t){let n=performance.now();function r(i){let a=i-n,o=Math.min(a/800,1),s=o*(2-o);e.textContent=Math.floor(s*t).toLocaleString(`es-AR`),o<1?requestAnimationFrame(r):e.textContent=t.toLocaleString(`es-AR`)}requestAnimationFrame(r)}async function c(){let t=new Date,n=t.getHours(),r=n<12?`Buenos días`:n<19?`Buenas tardes`:`Buenas noches`,c=e.currentUser?.nombre||e.currentUser?.username||``,l=document.getElementById(`landing-greeting`),u=document.getElementById(`landing-date-str`);l&&(l.textContent=c?`${r}, ${c}`:`Bienvenido al Tablero SGDU`),u&&(u.textContent=`${[`Domingo`,`Lunes`,`Martes`,`Miércoles`,`Jueves`,`Viernes`,`Sábado`][t.getDay()]} ${t.getDate()} de ${[`enero`,`febrero`,`marzo`,`abril`,`mayo`,`junio`,`julio`,`agosto`,`septiembre`,`octubre`,`noviembre`,`diciembre`][t.getMonth()]} de ${t.getFullYear()}`);try{let e=window.API_BASE||`/api`,t=await window.def_fetch(`${e}/landing/stats`);if(!t||!t.ok)throw Error(`fetch`);let n=await t.json(),r=document.getElementById(`landing-progress-bar`),c=document.getElementById(`landing-workdays-label`);c&&(c.textContent=`Día ${n.dia_actual} de ${n.dias_mes} · ${n.pct_mes}%`),r&&setTimeout(()=>{r.style.width=n.pct_mes+`%`},200);let l=[{icon:`fa-solid fa-file-lines`,iconBg:`#eff6ff`,iconColor:`#3b82f6`,label:`Trámites configurados`,value:n.tramites_total,sub:`tipos de trámite activos`},{icon:`fa-solid fa-users`,iconBg:`#f0fdf4`,iconColor:`#10b981`,label:`Analistas activos`,value:n.analistas_count,sub:`en el sistema`},{icon:`fa-solid fa-file-import`,iconBg:`#eff6ff`,iconColor:`#6366f1`,label:`Ingresados ${o(n.mes)}`,value:n.ingresos_mes,sub:`expedientes en el mes`},{icon:`fa-solid fa-circle-check`,iconBg:`#f0fdf4`,iconColor:`#10b981`,label:`Egresados efectivos ${o(n.mes)}`,value:n.egresos_efectivos_mes,sub:`resoluciones definitivas`,valueColor:`#10b981`},{icon:`fa-solid fa-circle-xmark`,iconBg:`#fff7ed`,iconColor:`#f97316`,label:`Egresados no efectivos ${o(n.mes)}`,value:n.egresos_no_efectivos_mes,sub:`desistimientos / rechazos`,valueColor:`#f97316`},{icon:`fa-solid fa-right-from-bracket`,iconBg:`#f8fafc`,iconColor:`#64748b`,label:`Total egresados ${o(n.mes)}`,value:n.egresos_total_mes,sub:`ef. + no ef.`},{icon:`fa-solid fa-layer-group`,iconBg:`#faf5ff`,iconColor:`#8b5cf6`,label:`Stock en trámite`,value:n.stock_total,sub:`expedientes activos hoy (incluye ${n.stock_intervenciones.toLocaleString(`es-AR`)} de intervenciones)`,valueColor:`#8b5cf6`},{icon:`fa-solid fa-triangle-exclamation`,iconBg:`#fef2f2`,iconColor:`#ef4444`,label:`Subsanaciones abiertas`,value:n.subs_abiertas,sub:`pendientes de respuesta`,valueColor:`#ef4444`},{icon:`fa-solid fa-fire-flame-curved`,iconBg:`#fef2f2`,iconColor:`#dc2626`,label:`Trámite con mayor stock`,value:n.top_trata_stock,sub:n.top_trata_nombre,valueColor:`#dc2626`}],u=document.getElementById(`landing-kpi-grid`);if(!u)return;u.innerHTML=l.slice(0,8).map(e=>i(e)).join(``)+i({...l[8],gridStyle:`grid-column: 5; grid-row: 1 / span 2;`,tall:!0});let d=document.getElementById(`landing-dgroc-grid`),f=document.getElementById(`landing-dgiur-grid`);d&&n.dgroc&&(d.innerHTML=[a({label:`Ingresos`,mesVal:n.dgroc.ingresos_mes,acumVal:n.dgroc.ingresos_acum}),a({label:`Egresos`,mesVal:n.dgroc.egresos_mes,acumVal:n.dgroc.egresos_acum,efVal:n.dgroc.egresos_efectivos_acum,neVal:n.dgroc.egresos_no_efectivos_acum}),a({label:`Stock`,mesVal:n.dgroc.stock,showAcum:!1,intVal:n.dgroc.stock_intervenciones}),a({label:`Subsanaciones`,mesVal:n.dgroc.subsanaciones,showAcum:!1,intVal:n.dgroc.subsanaciones_intervenciones})].join(``)),f&&n.dgiur&&(f.innerHTML=[a({label:`Ingresos`,mesVal:n.dgiur.ingresos_mes,acumVal:n.dgiur.ingresos_acum}),a({label:`Egresos`,mesVal:n.dgiur.egresos_mes,acumVal:n.dgiur.egresos_acum,efVal:n.dgiur.egresos_efectivos_acum,neVal:n.dgiur.egresos_no_efectivos_acum}),a({label:`Stock`,mesVal:n.dgiur.stock,showAcum:!1,intVal:n.dgiur.stock_intervenciones}),a({label:`Subsanaciones`,mesVal:n.dgiur.subsanaciones,showAcum:!1,intVal:n.dgiur.subsanaciones_intervenciones})].join(``)),[u,d,f].forEach(e=>{e&&e.querySelectorAll(`.landing-kpi-value[data-target]`).forEach(e=>{let t=parseInt(e.dataset.target,10);isNaN(t)||s(e,t)})})}catch(e){console.warn(`Landing stats error:`,e)}}var l=`<div class="breadcrumbs">
    <span onclick="showView('landing')">Inicio</span> / Reporte RRHH
</div>

<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 15px;">
    <h1 class="landing-title" style="margin: 0;">Reporte RRHH</h1>
    <div class="tabs-premium-container" style="display: flex; gap: 4px; background: #e2e8f0; padding: 4px; border-radius: 8px;">
        <button type="button" id="tab-btn-rrhh-reporte" class="tab-btn-premium active" onclick="switchRRHHTab('reporte')" style="padding: 8px 16px; border: none; background: white; border-radius: 6px; font-family: 'Outfit'; font-weight: 700; cursor: pointer; font-size: 0.9rem; color: var(--primary-dark); transition: all 0.2s;">Reporte</button>
        <button type="button" id="tab-btn-rrhh-carga" class="tab-btn-premium" onclick="switchRRHHTab('carga')" style="padding: 8px 16px; border: none; background: transparent; border-radius: 6px; font-family: 'Outfit'; font-weight: 700; cursor: pointer; font-size: 0.9rem; color: #64748b; transition: all 0.2s;">Carga de reportes</button>
    </div>
</div>

<!-- Solapa 1: Reporte y Analítica -->
<div id="rrhh-solapa-reporte">
    <!-- Filtros -->
    <div class="admin-card" style="background: white; padding: 15px 25px; border-radius: 12px; border: 1px solid #cbd5e1; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <label style="font-weight: 700; color: var(--primary-dark); font-family: 'Outfit'; font-size: 0.9rem;">Período:</label>
            <input type="month" id="rrhh-filter-month" onchange="loadRRHHReport()" style="padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-family: 'Outfit'; font-weight: bold; color: var(--primary-dark); outline: none;">
        </div>
        <button type="button" onclick="loadRRHHReport()" class="btn-primary" style="padding: 8px 16px; font-size: 0.88rem; font-weight: 700; border-radius: 6px; border: none; cursor: pointer; background: var(--primary); color: white; display: inline-flex; align-items: center; gap: 6px;">
            <i class="fa-solid fa-arrows-rotate"></i> Actualizar
        </button>
    </div>

    <!-- Resumen/Indicadores Globales -->
    <div class="metrics-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;" id="rrhh-global-cards">
        <!-- Dinámico -->
    </div>

    <!-- Grilla de Sectores / Análisis por Sector -->
    <h2 style="color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700; margin-bottom: 1.5rem; border-left: 5px solid var(--primary); padding-left: 10px;">Análisis Analítico por Sector</h2>

    <div id="rrhh-sectores-container" style="display: flex; flex-direction: column; gap: 2rem;">
        <!-- Se puebla dinámicamente -->
    </div>
</div>

<!-- Solapa 2: Carga de reportes -->
<div id="rrhh-solapa-carga" style="display: none;">
    <div class="admin-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; align-items: start;">
        <!-- Panel de Carga -->
        <div class="admin-card" style="background: white; padding: 30px; border-radius: 16px; border: 1px solid #cbd5e1; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <h3 style="margin-top: 0; margin-bottom: 1rem; color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700;">Subir Planilla de Control Asistencia</h3>
            <p style="color: #64748b; font-size: 0.88rem; line-height: 1.5; margin-bottom: 1.5rem;">Sube el archivo Excel conteniendo los registros mensuales de control de asistencia. El sistema validará y reemplazará automáticamente los datos de los días cargados para prevenir duplicidades.</p>

            <form id="rrhh-upload-form" onsubmit="uploadRRHHExcel(event)" style="display: flex; flex-direction: column; gap: 1.5rem;">
                <div style="border: 2px dashed #cbd5e1; border-radius: 12px; padding: 30px 20px; text-align: center; background: #f8fafc; cursor: pointer; transition: all 0.2s;" ondragover="event.preventDefault(); this.style.borderColor='var(--primary)';" ondragleave="this.style.borderColor='#cbd5e1';" ondrop="handleRRHHDrop(event)">
                    <i class="fa-solid fa-file-excel" style="font-size: 3rem; color: #16a34a; margin-bottom: 10px;"></i>
                    <p style="margin: 0; font-weight: 700; color: var(--primary-dark); font-size: 0.95rem;">Arrastra tu archivo aquí o haz clic para buscar</p>
                    <span style="font-size: 0.8rem; color: #64748b;">Formatos aceptados: .xlsx, .xls</span>
                    <input type="file" id="rrhh-file-input" accept=".xlsx, .xls" onchange="handleRRHHFileSelect(event)" style="display: none;">
                </div>

                <!-- Indicador de archivo seleccionado -->
                <div id="rrhh-file-info" style="display: none; align-items: center; justify-content: space-between; background: #e0f2fe; color: #0369a1; padding: 10px 14px; border-radius: 8px; font-size: 0.88rem; font-weight: bold;">
                    <span id="rrhh-filename">NombreArchivo.xlsx</span>
                    <button type="button" onclick="clearRRHHFile()" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 1.1rem;"><i class="fa-solid fa-circle-xmark"></i></button>
                </div>

                <button type="submit" class="btn-primary" style="padding: 12px; font-weight: 700; border-radius: 8px; border: none; cursor: pointer; background: var(--primary); color: white; display: flex; align-items: center; justify-content: center; gap: 6px; font-family: 'Outfit'; font-size: 1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <i class="fa-solid fa-cloud-arrow-up"></i> Cargar Planilla
                </button>
            </form>
        </div>

        <!-- Panel de Instrucciones -->
        <div class="admin-card" style="background: white; padding: 30px; border-radius: 16px; border: 1px solid #cbd5e1; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <h3 style="margin-top: 0; margin-bottom: 1rem; color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700;">Requisitos del Archivo Excel</h3>
            <p style="color: #64748b; font-size: 0.88rem; line-height: 1.5; margin-bottom: 1.5rem;">Para que la importación funcione correctamente, el archivo Excel debe estructurarse obligatoriamente con las siguientes columnas en este orden exacto:</p>

            <div style="display: flex; flex-direction: column; gap: 10px;">
                <div style="display: flex; gap: 10px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; font-size: 0.88rem;">
                    <strong style="width: 30px; color: var(--primary);">1.</strong>
                    <span><strong>Cuil</strong>: Número identificador (sin guiones o con guiones, ej. 20123456789).</span>
                </div>
                <div style="display: flex; gap: 10px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; font-size: 0.88rem;">
                    <strong style="width: 30px; color: var(--primary);">2.</strong>
                    <span><strong>Nombre y apellido</strong>: Nombre completo del analista.</span>
                </div>
                <div style="display: flex; gap: 10px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; font-size: 0.88rem;">
                    <strong style="width: 30px; color: var(--primary);">3.</strong>
                    <span><strong>Fecha</strong>: Fecha de registro del control (ej. YYYY-MM-DD).</span>
                </div>
                <div style="display: flex; gap: 10px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; font-size: 0.88rem;">
                    <strong style="width: 30px; color: var(--primary);">4.</strong>
                    <span><strong>Feriado</strong>: Indicador si la fecha corresponde a feriado (SI / NO).</span>
                </div>
                <div style="display: flex; gap: 10px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; font-size: 0.88rem;">
                    <strong style="width: 30px; color: var(--primary);">5.</strong>
                    <span><strong>Convocado</strong>: Indicador si el analista debió asistir (SI / NO).</span>
                </div>
                <div style="display: flex; gap: 10px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; font-size: 0.88rem;">
                    <strong style="width: 30px; color: var(--primary);">6.</strong>
                    <span><strong>Hora Ingreso (R)</strong>: Hora exacta de marcación de ingreso (ej. 08:30:00).</span>
                </div>
                <div style="display: flex; gap: 10px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; font-size: 0.88rem;">
                    <strong style="width: 30px; color: var(--primary);">7.</strong>
                    <span><strong>Hora Salida (R)</strong>: Hora exacta de marcación de egreso (ej. 17:00:00).</span>
                </div>
                <div style="display: flex; gap: 10px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; font-size: 0.88rem;">
                    <strong style="width: 30px; color: var(--primary);">8.</strong>
                    <span><strong>Cant Horas (R)</strong>: Cantidad de horas totales laboradas (ej. 08:30:00).</span>
                </div>
                <div style="display: flex; gap: 10px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; font-size: 0.88rem;">
                    <strong style="width: 30px; color: var(--primary);">9.</strong>
                    <span><strong>Estado Incidencia</strong>: Comentarios del sistema de accesos (ej. Llegada tarde).</span>
                </div>
                <div style="display: flex; gap: 10px; padding-bottom: 8px; font-size: 0.88rem;">
                    <strong style="width: 30px; color: var(--primary);">10.</strong>
                    <span><strong>Estado</strong>: Estado del agente en el día (ej. Presente / Ausente).</span>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Modal: Detalle Mensual del Analista -->
<div id="rrhh-detalle-agente-modal" class="modal-premium-overlay" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15,23,42,0.6); backdrop-filter: blur(4px); z-index: 2000; align-items: center; justify-content: center;">
    <div class="modal-premium-content" style="background: white; border-radius: 16px; width: 90%; max-width: 950px; max-height: 85vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); animation: modalFadeIn 0.3s ease-out;">
        <div style="padding: 20px 25px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; background: var(--primary-dark); color: white;">
            <div>
                <h3 id="rrhh-modal-agent-name" style="margin: 0; font-family: 'Outfit'; font-weight: 700; font-size: 1.25rem;">Nombre Analista</h3>
                <p id="rrhh-modal-agent-cuil" style="margin: 4px 0 0 0; font-size: 0.82rem; color: #cbd5e1; font-weight: bold;">CUIL: 20123456789</p>
            </div>
            <button type="button" onclick="closeRRHHAgentModal()" style="background: none; border: none; color: white; cursor: pointer; font-size: 1.5rem; transition: transform 0.2s;"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div style="padding: 25px; overflow-y: auto; flex-grow: 1;">
            <div class="table-container" style="max-height: 450px; overflow-y: auto;">
                <table class="table-premium" style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                    <thead>
                        <tr style="border-bottom: 2px solid #e2e8f0; text-align: left; background: #f8fafc; position: sticky; top: 0; z-index: 10;">
                            <th style="padding: 10px 12px; font-weight: 700; color: #475569;">Fecha</th>
                            <th style="padding: 10px 12px; font-weight: 700; color: #475569; text-align: center;">Feriado</th>
                            <th style="padding: 10px 12px; font-weight: 700; color: #475569; text-align: center;">Convocado</th>
                            <th style="padding: 10px 12px; font-weight: 700; color: #475569;">Hora Ingreso</th>
                            <th style="padding: 10px 12px; font-weight: 700; color: #475569;">Hora Salida</th>
                            <th style="padding: 10px 12px; font-weight: 700; color: #475569;">Cant Horas</th>
                            <th style="padding: 10px 12px; font-weight: 700; color: #475569;">Incidencia</th>
                            <th style="padding: 10px 12px; font-weight: 700; color: #475569;">Estado</th>
                        </tr>
                    </thead>
                    <tbody id="rrhh-agent-detail-table-body">
                        <!-- Dinámico -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
`;function u(){let e=document.getElementById(`reportes_rrhh`);e&&(e.innerHTML=l),d()}function d(){let t=document.getElementById(`rrhh-filter-month`);if(t&&!t.value){let e=new Date;t.value=`${e.getFullYear()}-${String(e.getMonth()+1).padStart(2,`0`)}`}let n=document.getElementById(`tab-btn-rrhh-carga`);if(n){let t=e.currentUser,r=!!(t&&(t.permissions.carga_reportes_rrhh||[`admin`,`administrador`].includes((t.role||``).toLowerCase())));n.style.display=r?`inline-block`:`none`}f(`reporte`),p()}function f(e){let t=document.getElementById(`rrhh-solapa-reporte`),n=document.getElementById(`rrhh-solapa-carga`),r=document.getElementById(`tab-btn-rrhh-reporte`),i=document.getElementById(`tab-btn-rrhh-carga`);e===`reporte`?(t&&(t.style.display=`block`),n&&(n.style.display=`none`),r&&(r.className=`tab-btn-premium active`,r.style.background=`white`,r.style.color=`var(--primary-dark)`),i&&(i.className=`tab-btn-premium`,i.style.background=`transparent`,i.style.color=`#64748b`)):(t&&(t.style.display=`none`),n&&(n.style.display=`block`),r&&(r.className=`tab-btn-premium`,r.style.background=`transparent`,r.style.color=`#64748b`),i&&(i.className=`tab-btn-premium active`,i.style.background=`white`,i.style.color=`var(--primary-dark)`))}async function p(){let e=document.getElementById(`rrhh-sectores-container`),t=document.getElementById(`rrhh-global-cards`),n=document.getElementById(`rrhh-filter-month`),r=n?n.value:``;if(e){e.innerHTML=`<div style="text-align: center; padding: 3rem;"><span class="loader"></span><p style="margin-top: 0.5rem; color: #64748b;">Analizando control de asistencia del sector...</p></div>`,t&&(t.innerHTML=``);try{let i=window.API_BASE||`/api`,a=r?`${i}/rrhh/reporte?month=${r}`:`${i}/rrhh/reporte`,o=await window.def_fetch(a);if(o&&o.ok){let r=await o.json();if(window.currentRRHHReportData=r,r.month&&n&&(n.value=r.month),!r.sectores||Object.keys(r.sectores).length===0){e.innerHTML=`<div style="text-align: center; padding: 3rem; color: #64748b; font-style: italic;">No hay registros importados para el mes seleccionado.</div>`;return}let i=0,a=0,s=0,c=0,l=0,u=0,d=Object.keys(r.sectores);d.forEach(e=>{r.sectores[e].agentes_list.forEach(e=>{s++,c+=e.asistencia_pct,e.ausentes>0&&(a+=e.ausentes),i+=e.presentes})});let f=s>0?Math.round(c/s):100;d.forEach(e=>{r.sectores[e].agentes_list.forEach(e=>{if(e.promedio_horas&&e.promedio_horas!==`--`){let t=e.promedio_horas.split(`:`);l+=parseInt(t[0])*60+parseInt(t[1]),u++}})});let p=u>0?(()=>{let e=Math.round(l/u);return`${String(Math.floor(e/60)).padStart(2,`0`)}:${String(e%60).padStart(2,`0`)}`})():`--`;t&&(t.innerHTML=`
                    <div class="metric-card-premium" style="background: white; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                        <div style="width: 50px; height: 50px; border-radius: 50%; background: #eff6ff; color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-users"></i></div>
                        <div>
                            <span style="font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Agentes Analizados</span>
                            <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 700; font-size: 1.5rem; color: var(--primary-dark);">${s}</h3>
                        </div>
                    </div>
                    <div class="metric-card-premium" style="background: white; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                        <div style="width: 50px; height: 50px; border-radius: 50%; background: #ecfdf5; color: #10b981; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-calendar-check"></i></div>
                        <div>
                            <span style="font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Asistencia Promedio</span>
                            <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 700; font-size: 1.5rem; color: #10b981;">${f}%</h3>
                        </div>
                    </div>
                    <div class="metric-card-premium" style="background: white; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                        <div style="width: 50px; height: 50px; border-radius: 50%; background: #fff7ed; color: #f97316; display: flex; align-items: center; justify-content: center; font-size: 1.3rem;"><i class="fa-solid fa-hourglass-half"></i></div>
                        <div>
                            <span style="font-size: 0.8rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Prom. Horas Realizadas</span>
                            <h3 style="margin: 2px 0 0 0; font-family: 'Outfit'; font-weight: 700; font-size: 1.5rem; color: #f97316;">${p} hs</h3>
                        </div>
                    </div>
                `);let m=``;d.forEach(e=>{let t=r.sectores[e],n=t.earliest_ingreso||`08:00`,i=t.latest_salida||`18:00`,a=``,o=Object.keys(t.hourly_coverage).sort(),s=Math.max(...Object.values(t.hourly_coverage),1);o.forEach(e=>{let n=t.hourly_coverage[e],r=Math.round(n/s*100);a+=`
                        <div style="display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 35px; gap: 6px;">
                            <div style="width: 100%; height: 80px; background: #f1f5f9; border-radius: 4px; display: flex; align-items: flex-end;">
                                <div style="width: 100%; height: ${r}%; background: var(--primary); border-radius: 4px; transition: height 0.5s ease;"></div>
                            </div>
                            <span style="font-size: 0.7rem; color: #64748b; font-weight: 600;">${e}</span>
                        </div>
                    `});let c=``;t.agentes_list.forEach(e=>{let t=`#94a3b8`;if(e.promedio_horas&&e.promedio_horas!==`--`){let[n,r]=e.promedio_horas.split(`:`).map(Number),i=n*60+r;t=i>=420?`#10b981`:i>=300?`#f59e0b`:`#ef4444`}c+=`
                        <tr style="border-bottom: 1px solid #f1f5f9;">
                            <td style="padding: 10px 12px; font-weight: 700; color: var(--primary-dark);">${e.usuario.toUpperCase()}</td>
                            <td style="padding: 10px 12px; color: #334155;">${e.nombre}</td>
                            <td style="padding: 10px 12px; text-align: center; font-weight: 600; color: #10b981;">${e.asistencia_pct}%</td>
                            <td style="padding: 10px 12px; text-align: center; font-weight: 700; color: ${t}; font-family: 'Outfit'; font-size: 0.95rem;">${e.promedio_horas} hs</td>
                            <td style="padding: 10px 12px; text-align: center;">
                                <button type="button" onclick="openRRHHAgentPage('${e.cuil}', '${encodeURIComponent(e.nombre)}')" class="btn-action-view" style="padding: 6px 12px; background: #eff6ff; color: #2563eb; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-family: 'Outfit'; font-weight: 700; transition: all 0.2s;">
                                    <i class="fa-solid fa-calendar-days"></i> Ver Bitácora
                                </button>
                            </td>
                        </tr>
                    `}),m+=`
                    <div class="admin-card" style="background: white; border-radius: 16px; border: 1px solid #cbd5e1; padding: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
                            <div>
                                <h3 style="margin: 0; color: var(--primary-dark); font-family: 'Outfit'; font-weight: 800; font-size: 1.3rem; text-transform: uppercase;">
                                    Sector: ${e}
                                </h3>
                                <p style="margin: 4px 0 0 0; font-size: 0.82rem; color: #64748b;">Análisis de jornada, puntualidad y distribución de turnos por horario.</p>
                            </div>
                            <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 12px; display: inline-flex; align-items: center; gap: 8px; font-family: 'Outfit'; font-size: 0.85rem;">
                                <i class="fa-solid fa-business-time" style="color: var(--primary);"></i>
                                <span style="font-weight: 600; color: #334155;">Franja Horaria Cubierta:</span>
                                <strong style="color: var(--primary-dark);">${n} - ${i}</strong>
                            </div>
                        </div>

                        <!-- 1. Mapa de Cobertura Horaria -->
                        <div style="margin-bottom: 2rem;">
                            <h4 style="margin: 0 0 1rem 0; color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700; font-size: 0.95rem;">Mapa de Cobertura Horaria (Agentes activos por hora)</h4>
                            <div style="display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 12px;">
                                ${a}
                            </div>
                        </div>

                        <!-- 2. Tabla de Analistas -->
                        <div>
                            <h4 style="margin: 0 0 1rem 0; color: var(--primary-dark); font-family: 'Outfit'; font-weight: 700; font-size: 0.95rem;">Personal Asignado y Desempeño</h4>
                            <div class="table-responsive">
                                <table class="report-table" style="width: 100%; border-collapse: collapse;">
                                    <thead>
                                        <tr style="border-bottom: 2px solid #cbd5e1; background: #f8fafc; text-align: left; font-size: 0.82rem;">
                                            <th style="padding: 10px 12px; font-weight: 700; color: #475569;">Usuario</th>
                                            <th style="padding: 10px 12px; font-weight: 700; color: #475569;">Nombre y Apellido</th>
                                            <th style="padding: 10px 12px; font-weight: 700; color: #475569; text-align: center;">Asistencia</th>
                                            <th style="padding: 10px 12px; font-weight: 700; color: #475569; text-align: center;">Prom. Horas</th>
                                            <th style="padding: 10px 12px; font-weight: 700; color: #475569; text-align: center;">Acción</th>
                                        </tr>
                                    </thead>
                                    <tbody style="font-size: 0.85rem;">
                                        ${c}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                `}),e.innerHTML=m}else e.innerHTML=`<div style="text-align: center; padding: 3rem; color: #ef4444;">Error al cargar datos del reporte.</div>`}catch(t){console.error(`Error loading RRHH report:`,t),e.innerHTML=`<div style="text-align: center; padding: 3rem; color: #ef4444;">Error de red al conectar con el servidor.</div>`}}}window.renderLandingView=r,window.renderRRHHView=u;function m(){e.currentUser=window.currentUser||null,e.authToken=window.authToken||t()}setInterval(m,500),m(),console.log(`Tablero SGDU - Frontend Modular cargado correctamente.`);