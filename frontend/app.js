const API_BASE = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1') 
    ? "http://127.0.0.1:8000/api" 
    : "/api";

const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

// --- METADATOS DE AYUDA (Para el Modal de Metodología) ---
const BUZZERS_DOCS = {
    'catastro': 'DGROC-CIC, DGROC-COPIAPLANO, DGROC-DCATDES, DGROC-DCATPOL o DGROC-DCATTIT',
    'contable': 'DGROC-CONTABLE o DGROC-OBRASADMIN',
    'instalaciones': 'DGROC-ELECTRICAS, DGROC-ELEVADORES, DGROC-INCENDIO, DGROC-SANITARIAS o DGROC-TERMICAS',
    'regularizacion': 'DGROC-OBRASDEMO',
    'etapa_proyecto': 'DGROC-OBRASTECNICA',
    'aviso_obra': 'DGROC-AUTOMAT'
};

const ANALYSTS_DOCS = {
    'catastro': ["ACOSTAPA", "AFAHLER", "AGUSMAZZONI", "ALEALFONSIN", "ALEGREM", "ARGENTOES", "BARTROLIG", "CABRERAM", "CANALEAL", "CARBONELLIM", "CHIANETTAR", "CIOPKOG", "CISTERNACA", "COHENCAD", "CONTIL", "CONVERTID", "DELGADODE", "DIBIASEO", "DIEZGASTON", "DIHARCEP", "DURSIM", "ECIJAN", "FMARCHISELLA", "FOLLONIERLE", "FREIXASC", "GARCIASIL", "GILESJP", "GONZALEZAMA", "GONZALEZHORAC", "GUZMANO", "IGARZABALP", "JTIRADO", "LAGUNAMA", "LBELLY", "LOISIG", "LUCCIC", "M.NAPOLI", "MALATTOR", "MANNOP", "MARCHETTIJ", "MHOSBALIKCIYAN", "MOSCOVICHA", "NCITRANGOLO", "NOGUERAH", "NPONZO", "NQUINTERNO", "PONZOS", "ROLDANG", "SALGUEROM", "SORIAANDREA", "TARRUA", "TAVELLAE", "VEGAJ", "VILLAGI", "WVIRGILIO"],
    'regularizacion': ["AGUEROJO", "AKRACOFF", "ALVAREZ.M", "ARAOZLUIS", "ATENCIOAL", "DALBORAF", "ENCISOA", "EPARLATO", "ERDOCIAINA", "JBARRACO", "JLGARMENDIA", "JTERRILE", "MYUSHU", "S.SANCHEZPAZ", "SCAVALLARO"],
    'instalaciones': ["AQUINOLUCAS", "ARENAJ", "ARGUELLOJ", "BATALLANJ", "BENITOG", "BRIANMARTINEZ", "CORNAZM", "FICARRAR", "GAGLIARDIA", "LOPARDOC", "QUEIJASGUILLINP", "ROBLEDOJO", "ROLDANMI", "RUDAC", "SARIDISD", "TOLESANOA", "AURENA", "BATALLANGE", "BRITANP", "GUARDADOB", "JDECIMA", "PEREZGA", "RODRIGUEZESTEBAN", "RODRIGUEZNE", "SILESC", "VILLAGAB", "ABCRAGNO", "AGARCIAFIGUEROA", "CABRERAARI", "CAFELICE", "CAPOZZOG", "CSALGUERO", "DARANGURI", "DMOFFA", "FUHRY", "GONMAR", "J.OLIVERA", "LOPEZFE", "MARIANELAROCARO", "MBALDOME", "MLMAMONE", "MTRENQUE", "NIEVAL", "PCHERBENCO", "RADAA", "RIOSFE", "ROMANOFLA", "SANTACRUZ", "CANTARELLTORRES", "CIRIAE", "LOIACONOANA", "MCDIAMANTI", "POUSAF", "ARGUELLOSOL", "COSSM", "EIERACI", "HAMALAG", "RUIZMA", "BRITANG", "ENCISOROMERO", "PITTERIE", "WIERZBICKIIGOR"],
    'contable': ["AMONTEVERDE", "AMORINC", "CARLOSDUARTE", "CAROJAS", "COLOTTAP", "CPENDON", "DAS", "DASTUGUEO", "DEGODOY", "DIAZBAR", "DKRENZ", "EDEFEO", "FABIANSANTILLAN", "FMHERRERA", "FSPANTI", "GARCIASEBA", "HRICCIARDI", "JOSEMARIAORTIZ", "JPOMAR", "JULILOPARDO", "LAMORGIAKA", "LBARRIENTOS", "LICETB", "M.ROSSO", "MARQUEZMAR", "MARTINEZCLA", "MLAURITO", "MMALACALZA", "NMONTEVERDE", "NMORENO", "POVIEDO", "PRESAF", "PVACEVEDO", "RIVERAMA", "ROBLEDOE", "RODRIGUEZLEA", "RODRIGUEZMAGD", "ROSARIODECRIS", "SCHULERG", "SENING", "SMERMOZ", "SORIAD", "SPOSAROAL", "TATOJ", "TIRENDIC", "TOMIPITES", "VICSOLMORE", "VILLACRI"],
    'etapa_proyecto': ["A.PEREZ", "AGUSDEMARCO", "ANTOVERA", "BELOCURESJ", "COIROL", "DBECERRACURITIMA", "DIMASOM", "DNKAINSKY", "FORGIONEA", "GAILLURJP", "GARRIONDO", "JOSEFINA.P", "M.SANCHEZ", "MARCE.TOSONI", "MARCETOSONI", "MARCETOSONI1", "MBRISA", "MCANOGARAY", "MCARLUCCIO", "MGALLARDOC", "MSTIBERTI", "NLOPEZQUIROGA", "ROCABERTJ", "SPUET", "TALAMOM", "VERA"]
};

function showView(viewId, updateHash = true) {
    const views = document.querySelectorAll('.view-container');
    const targetView = document.getElementById(viewId);
    if (!targetView) return;

    views.forEach(v => {
        v.classList.remove('active');
        v.style.display = 'none';
    });

    targetView.style.display = 'block';
    targetView.classList.add('active');
    
    gsap.from(targetView, { opacity: 0, y: 20, duration: 0.4, ease: "power2.out" });

    // Actualizar URL si es necesario
    if (updateHash) {
        window.location.hash = `#/${viewId}`;
    }

    // Cargar reporte automáticamente si es una vista de gerencia
    const gerencias = ['catastro', 'instalaciones', 'obra', 'interpretacion', 'regularizacion', 'contable', 'etapa_proyecto', 'aviso_obra'];
    if (gerencias.includes(viewId)) {
        loadConsolidatedReport(viewId);
    }
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
        // Nota: En un sistema real, el nombre vendría de un catálogo o del consolidado ya cargado
        const trataName = trataCode; 
        showTrataDetail(gerencia, trataCode, trataName, false);
    } else {
        showView(viewId, false);
    }
}

// Escuchar cambios en la URL
window.addEventListener('hashchange', handleRouting);

// Carga inicial
window.addEventListener('DOMContentLoaded', () => {
    handleRouting();
});

let currentChart = null;
let currentStockAgeChart = null;
let currentStockData = { expedientes: [], trataName: "", trataCode: "" };

async function showTrataDetail(gerencia, trataCode, trataName, updateHash = true) {
    const views = document.querySelectorAll('.view-container');
    views.forEach(v => { v.classList.remove('active'); v.style.display = 'none'; });
    
    const detailView = document.getElementById('trata_detail');
    detailView.style.display = 'block';
    detailView.classList.add('active');
    
    if (updateHash) {
        window.location.hash = `#/${gerencia}/${trataCode}`;
    }
    
    if (currentChart) { currentChart.destroy(); currentChart = null; }
    if (currentStockAgeChart) { currentStockAgeChart.destroy(); currentStockAgeChart = null; }
    
    document.getElementById('analyst-table-container').innerHTML = '<div style="padding: 20px; text-align: center; color: #64748b;">Cargando análisis de stock...</div>';
    
    const mainChartCtx = document.getElementById('trata-chart');
    if (mainChartCtx) {
        mainChartCtx.parentElement.innerHTML = '<div id="main-chart-loading" style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%); color:#64748b;">Cargando evolución...</div><canvas id="trata-chart"></canvas>';
    }

    const ageChartCtx = document.getElementById('stock-age-chart');
    if (ageChartCtx) ageChartCtx.parentElement.innerHTML = '<canvas id="stock-age-chart"></canvas>';

    document.getElementById('trata_detail_title').innerText = trataName;
    document.getElementById('trata_detail_back').onclick = () => showView(gerencia);

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
        const response = await fetch(`${API_BASE}/reporte/${gerencia}/tramite/${trataCode}`);
        let data = await response.json();
        data = data.reverse();
        
        const labels = data.map(d => `${MESES[d.mes - 1]} ${d.anio}`);
        const ctx = document.getElementById('trata-chart').getContext('2d');
        if (document.getElementById('main-chart-loading')) document.getElementById('main-chart-loading').remove();

        currentChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Stock Propio', data: data.map(d => d.STOCK_PROPIO || 0), type: 'line', borderColor: '#F59E0B', backgroundColor: '#F59E0B', borderWidth: 3, tension: 0.3, pointRadius: 4, order: 0 },
                    { label: 'Stock Subsanaciones', data: data.map(d => d.STOCK_SUBS || 0), type: 'line', borderColor: '#EF4444', backgroundColor: '#EF4444', borderWidth: 3, tension: 0.3, pointRadius: 4, order: 1 },
                    { label: 'Ingresos', data: data.map(d => d.ING || 0), backgroundColor: '#002d47', borderRadius: 4, order: 2 },
                    { label: 'Egresos Efectivos', data: data.map(d => d.EGR_EF || 0), backgroundColor: '#0076bb', stack: 'egresos', borderRadius: 4, order: 3 },
                    { label: 'Egresos No Efectivos', data: data.map(d => d.EGR_NE || 0), backgroundColor: '#94A3B8', stack: 'egresos', order: 4 }
                ]
            },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
        });

        const stockResp = await fetch(`${API_BASE}/reporte/${gerencia}/tramite/${trataCode}/stock_detail`);
        if (stockResp.ok) {
            const stockData = await stockResp.json();
            currentStockData = { expedientes: stockData.expedientes || [], trataName, trataCode };
            renderStockAgeChart(stockData.month_distribution);
            renderAnalystTable(stockData.analyst_distribution);
        }
    } catch (error) { console.error(error); }
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
        const analistaEscaped = row.analista.replace(/'/g, "\\'");
        html += `<tr>
            <td class="clickable-analyst" onclick="openDrillDown('${analistaEscaped}')">${row.analista}</td>
            ${ranges.map(r => `<td>${row[r] || '-'}</td>`).join('')}
            <td style="font-weight:700;">${row.TOTAL}</td>
        </tr>`;
    });
    container.innerHTML = html + `</tbody></table>`;
}

async function loadIntervencionesDetail(gerencia) {
    const wrapper = document.getElementById('intervenciones-table-wrapper');
    try {
        const response = await fetch(`${API_BASE}/reporte/${gerencia}/intervenciones/detalle`);
        const data = await response.json();
        if (!data || data.length === 0) { wrapper.innerHTML = '<div style="padding:20px; text-align:center;">Sin datos de intervención.</div>'; return; }
        const mesesSet = new Set();
        data.forEach(item => Object.keys(item.meses).forEach(m => mesesSet.add(m)));
        const sortedMeses = Array.from(mesesSet).sort((a, b) => b.localeCompare(a));
        let html = `<table class="matrix-table"><thead><tr><th>TRATA</th><th>DETALLE</th>${sortedMeses.map(m => `<th>${m}</th>`).join('')}</tr></thead><tbody>`;
        data.forEach(item => {
            html += `<tr><td>${item.trata}</td><td>${item.detalle}</td>${sortedMeses.map(m => `<td>${item.meses[m] || '-'}</td>`).join('')}</tr>`;
        });
        wrapper.innerHTML = html + '</tbody></table>';
    } catch (err) { wrapper.innerHTML = 'Error de carga.'; }
}

function openDrillDown(analista) {
    const modal = document.getElementById('stock-drilldown-modal');
    document.getElementById('modal-analyst-name').innerText = analista;
    document.getElementById('modal-trata-info').innerText = `Trámite: ${currentStockData.trataName}`;
    const filtered = currentStockData.expedientes.filter(e => e.analista === analista);
    let html = `<table class="matrix-table"><thead><tr><th>Expediente</th><th>ID</th><th>Fecha Ingreso</th><th>Días</th></tr></thead><tbody>`;
    filtered.forEach(e => { html += `<tr><td>${e.expediente}</td><td>${e.id_expediente}</td><td>${new Date(e.fecha_ing).toLocaleDateString()}</td><td>${e.dias}</td></tr>`; });
    document.getElementById('modal-table-container').innerHTML = html + `</tbody></table>`;
    document.getElementById('btn-download-csv').onclick = () => downloadCSV(analista, filtered);
    modal.style.display = 'flex';
}

function closeModal(id) { document.getElementById(id || 'stock-drilldown-modal').style.display = 'none'; }

function openHelpModal(trataCode, gerencia, trataName, acronimosFromData) {
    const modal = document.getElementById('help-modal');
    const body = document.getElementById('help-modal-body');
    const buzzers = BUZZERS_DOCS[gerencia] || 'Buzones oficiales del área';
    
    // Si no vienen acrónimos del consolidado (ej. vista de detalle directo), intentamos un fallback o mensaje genérico
    const acros = acronimosFromData || 'Documentos de resolución oficiales autorizados para este sector';
    const analystsList = (ANALYSTS_DOCS[gerencia] || []).join(', ');
    
    let content = '';

    if (trataCode === 'INTERVENCIONES') {
        content = `
            <div class="help-section">
                <h3><span class="help-badge badge-ing">Lógica de Ingresos</span></h3>
                <p>Se registra un ingreso cuando un expediente con un <strong>código de trata externo</strong> (distinto a los habituales de la gerencia) entra a uno de los buzones oficiales:</p>
                <div class="acronym-list">${buzzers}</div>
            </div>
            <div class="help-section">
                <h3><span class="help-badge badge-egr">Lógica de Egresos (Pase Efectivo)</span></h3>
                <p>Al no existir un documento GEDO de cierre único para intervenciones, el egreso se mide por movimiento:</p>
                <p><strong>• Egreso Contabilizado:</strong> Cuando un analista realiza un <strong>Pase a Destinatario Externo</strong> (fuera de la gerencia).</p>
                <p><strong>• Exclusión:</strong> Los pases internos o hacia buzones del mismo sector no cuentan como egresos; el trámite sigue en stock.</p>
            </div>
            <div class="help-section">
                <h3><span class="help-badge badge-stk">Stock de Intervenciones</span></h3>
                <p>Representa expedientes de otras áreas que requieren opinión o acción técnica de este sector. Se considera stock mientras el expediente esté en manos de un analista oficial del área.</p>
                <p style="font-size:0.85rem; color:#64748b; margin-top:10px;"><strong>Analistas Oficiales:</strong> ${analystsList}</p>
            </div>`;
    } else {
        content = `
            <div class="help-section">
                <h3><span class="help-badge badge-ing">Metodología de Ingresos</span></h3>
                <p>Se contabiliza el ingreso cuando el expediente (Código <strong>${trataCode}</strong>) toca por primera vez cualquiera de los buzones oficiales:</p>
                <div class="acronym-list">${buzzers}</div>
            </div>
            <div class="help-section">
                <h3><span class="help-badge badge-egr">Metodología de Egresos</span></h3>
                <p><strong>• Egreso Efectivo:</strong> Se produce cuando el analista genera un documento <strong>GEDO</strong> con fecha posterior al ingreso y con alguno de estos acrónimos autorizados:</p>
                <div class="acronym-list" style="background:#f0fdf4; border-color:#bbf7d0; color:#166534;">${acros}</div>
                <p><strong>• Egreso No Efectivo:</strong> Cuando el trámite se envía a <strong>Guarda Temporal</strong> finalizando su ciclo operativo sin resolución.</p>
            </div>
            <div class="help-section">
                <h3><span class="help-badge badge-stk">Cálculo de Stock ACTUAL</span></h3>
                <p><strong>• Stock Propio:</strong> Expedientes ingresados sin egreso, cuya ubicación actual es la bandeja de un <strong>Analista Oficial</strong> o un Buzón de Entrada del sector.</p>
                <p style="font-size:0.85rem; color:#64748b; margin:10px 0;"><strong>Usuarios considerados en el análisis:</strong> ${analystsList}</p>
                <p><strong>• Subsanaciones (Excluidas):</strong> Expedientes en estado de subsanación. Aunque pertenecen al área, se visualizan solo en el gráfico de evolución histórica para no afectar la antigüedad de gestión directa.</p>
            </div>`;
    }

    body.innerHTML = `
        <div style="margin-bottom:20px; border-bottom:2px solid #0076bb; padding-bottom:15px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <h2 style="color:#002d47; font-size:1.4rem; margin:0;">${trataName}</h2>
                    <p style="color:#64748b; margin:5px 0 0 0;">Metodología de Gestión</p>
                </div>
                <div style="text-align:right;">
                    <span class="trata-id-tag" style="font-size:1rem; padding:5px 12px; background:#002d47; color:white;">Código: ${trataCode}</span>
                    <div style="margin-top:8px;">
                        <span class="trata-id-tag" style="background:#e0f2fe; color:#075985;">${gerencia.toUpperCase()}</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="help-content-scroll" style="max-height: 50vh; overflow-y: auto; padding-right: 10px;">
            ${content}
        </div>
    `;
    modal.style.display = 'flex';
}

function downloadCSV(analista, data) {
    const headers = ["EXPEDIENTE", "ID", "FECHA", "DIAS"];
    let csv = "\uFEFF" + headers.join(";") + "\n";
    data.forEach(e => csv += [e.expediente, e.id_expediente, e.fecha_ing, e.dias].join(";") + "\n");
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `Stock_${analista}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

window.onclick = function(e) { if (e.target.classList.contains('modal')) e.target.style.display = 'none'; }
