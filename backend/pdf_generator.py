import io
from datetime import datetime, timedelta
from sqlalchemy import text

# Lazy imports — se cargan la primera vez que se usa el módulo
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    _HAS_MATPLOTLIB = True
except ImportError:
    _HAS_MATPLOTLIB = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfgen import canvas
    _HAS_REPORTLAB = True
except ImportError:
    _HAS_REPORTLAB = False

def _check_deps():
    """Verifica dependencias PDF antes de generar. Lanza error claro si faltan."""
    missing = []
    if not _HAS_MATPLOTLIB:
        missing.append("matplotlib")
    if not _HAS_REPORTLAB:
        missing.append("reportlab")
    if missing:
        raise ImportError(
            f"Dependencias faltantes para generación de PDF: {', '.join(missing)}. "
            f"Ejecutar en el servidor: pip install {' '.join(missing)}"
        )


# Palette DGROC / Modern (solo disponibles si reportlab está instalado)
if _HAS_REPORTLAB:
    C_PRIMARY = colors.HexColor("#1e3a8a")     # Deep blue
    C_SECONDARY = colors.HexColor("#0284c7")   # Sky blue
    C_SUCCESS = colors.HexColor("#10b981")     # Emerald green
    C_WARNING = colors.HexColor("#f59e0b")     # Amber orange
    C_DANGER = colors.HexColor("#ef4444")      # Rose red
    C_NEUTRAL = colors.HexColor("#475569")     # Slate gray
    C_BG_LIGHT = colors.HexColor("#f8fafc")    # Light slate

# Task colors for matplotlib
TASK_COLORS = {
    "OBSERVACIÓN DE EXPEDIENTE": "#1e3a8a",
    "PEDIDO DE PLANOS": "#0284c7",
    "VINCULACIÓN DE GEDO Y PASE A OBRAS ADMIN": "#10b981",
    "ENVÍO A FIRMA": "#6366f1",
    "OBSERVACIÓN EN SUBSANACIÓN": "#a855f7",
    "SUSPENSIÓN DE EXPEDIENTE": "#f59e0b"
}

if _HAS_REPORTLAB:
    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.pages = []

        def showPage(self):
            self.pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            page_count = len(self.pages)
            for page in self.pages:
                self.__dict__.update(page)
                self.draw_page_number(page_count)
                super().showPage()
            super().save()

        def draw_page_number(self, page_count):
            self.saveState()
            self.setFont("Helvetica", 9)
            self.setFillColor(colors.HexColor("#64748b"))
            self.drawRightString(612 - 54, 36, f"Pág. {self._pageNumber} de {page_count}")
            self.drawString(54, 36, "Tablero SGDU - Reporte de Productividad (SADE)")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 48, 612 - 54, 48)
            self.restoreState()
else:
    class NumberedCanvas:  # type: ignore
        pass


def generate_individual_pdf(conn, username, date_from=None, date_to=None):
    _check_deps()
    from backend.productivity_engine import get_analyst_productivity_data
    data = get_analyst_productivity_data(conn, username, date_from, date_to)
    kpis = data["kpis"]
    mix = data["mix_tareas"]
    
    # Load user full name and sector
    user_row = conn.execute(text("SELECT apellido_nombre, codigo_sector_interno FROM datos_usuario WHERE usuario = :u"), {"u": username}).fetchone()
    full_name = user_row[0] if user_row and user_row[0] else username
    sector = user_row[1] if user_row and user_row[1] else "SIN SECTOR"
    
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    style_title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=C_PRIMARY,
        spaceAfter=15
    )
    
    style_h2 = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=C_PRIMARY,
        spaceBefore=15,
        spaceAfter=10
    )
    
    style_body = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=C_NEUTRAL
    )
    
    style_body_bold = ParagraphStyle(
        "ReportBodyBold",
        parent=style_body,
        fontName="Helvetica-Bold"
    )

    story = []
    
    # PAGE 1: RESUMEN DE PRODUCTIVIDAD
    # Title & Metadata block
    story.append(Paragraph(f"Productividad Analista: {full_name} ({username})", style_title))
    
    meta_data = [
        [Paragraph(f"<b>Sector:</b> {sector}", style_body), Paragraph(f"<b>Período:</b> {date_from} al {date_to}", style_body)],
        [Paragraph("<b>Fuente:</b> SADE (Materializada)", style_body), Paragraph(f"<b>Días Hábiles:</b> {kpis['dias_habiles']}", style_body)]
    ]
    meta_table = Table(meta_data, colWidths=[250, 250])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_BG_LIGHT),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))
    
    # KPIs Grid
    story.append(Paragraph("KPIs de Gestión de Tareas", style_h2))
    kpi_data = [
        [
            Paragraph(f"<b>Total Tareas:</b><br/><font size=14 color='#1e3a8a'><b>{kpis['tareas_totales']}</b></font>", style_body),
            Paragraph(f"<b>Prom. Diario:</b><br/><font size=14 color='#1e3a8a'><b>{kpis['promedio_diario']}</b></font>", style_body),
            Paragraph(f"<b>Prom. Semanal:</b><br/><font size=14 color='#1e3a8a'><b>{kpis['promedio_semanal']}</b></font>", style_body),
            Paragraph(f"<b>Jornada Media:</b><br/><font size=14 color='#1e3a8a'><b>{kpis['jornada_media']}h</b></font>", style_body)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[125, 125, 125, 125])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 1, C_SECONDARY),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_BG_LIGHT),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 15))
    
    # Mix table & Donut chart in a side-by-side layout
    mix_headers = ["Tipo de Tarea", "Cantidad", "Porcentaje"]
    mix_rows = [[h for h in mix_headers]]
    for t_type, stats in mix.items():
        mix_rows.append([t_type, str(stats["cantidad"]), f"{stats['porcentaje']}%"])
        
    mix_table = Table(mix_rows, colWidths=[180, 60, 60])
    mix_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, C_BG_LIGHT]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    
    # Generate Donut chart in Matplotlib
    labels = [k[:15] + "..." if len(k) > 15 else k for k in mix.keys()]
    values = [stats["cantidad"] for stats in mix.values()]
    
    fig, ax = plt.subplots(figsize=(2.5, 2.5))
    if sum(values) > 0:
        colors_list = [TASK_COLORS.get(k, "#cccccc") for k in mix.keys()]
        wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.0f%%', startangle=90, colors=colors_list, 
                                          textprops=dict(color="black", size=6), pctdistance=0.75)
        plt.setp(autotexts, size=6, weight="bold")
        # Add center circle
        centre_circle = plt.Circle((0,0),0.55,fc='white')
        fig.gca().add_artist(centre_circle)
    else:
        ax.text(0.5, 0.5, "Sin Datos", ha='center', va='center')
        ax.set_axis_off()
        
    ax.axis('equal')  
    plt.tight_layout()
    
    chart_buffer = io.BytesIO()
    plt.savefig(chart_buffer, format='png', dpi=200, bbox_inches='tight')
    plt.close()
    chart_buffer.seek(0)
    chart_img = Image(chart_buffer, width=170, height=170)
    
    side_table = Table([[mix_table, chart_img]], colWidths=[310, 190])
    side_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(side_table)
    story.append(Spacer(1, 15))
    
    # Criteria and exclusions
    story.append(Paragraph("<b>Nota de Criterios y Exclusiones:</b>", style_body_bold))
    story.append(Paragraph(
        f"Se agruparon las acciones del analista usando el algoritmo oficial de SGDU. "
        f"Se excluyeron un total de <b>{data['exclusiones']['total']} acciones</b> por corresponder a pases únicos sueltos, "
        f"interconsultas, ochavas o consultas de antecedentes.",
        style_body
    ))
    
    # PAGE 2: DETALLE DIARIO
    story.append(PageBreak())
    story.append(Paragraph("Detalle Diario de Tareas", style_title))
    
    # Stacked bar chart
    days = sorted(data["desglose_diario"].keys())
    if days:
        fig, ax = plt.subplots(figsize=(6.5, 2.5))
        bottoms = np.zeros(len(days))
        for t_type in TASK_COLORS.keys():
            y_vals = [data["desglose_diario"][day].get(t_type, 0) for day in days]
            ax.bar(days, y_vals, bottom=bottoms, label=t_type[:15] + "...", color=TASK_COLORS[t_type])
            bottoms += y_vals
            
        ax.set_xticklabels(days, rotation=45, ha='right', fontsize=7)
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=6)
        plt.tight_layout()
        
        chart2_buffer = io.BytesIO()
        plt.savefig(chart2_buffer, format='png', dpi=200)
        plt.close()
        chart2_buffer.seek(0)
        story.append(Image(chart2_buffer, width=500, height=180))
        story.append(Spacer(1, 15))
        
    # Table Day x Type
    day_headers = ["Fecha"] + [k[:10] + "." for k in TASK_COLORS.keys()] + ["Total"]
    day_rows = [[h for h in day_headers]]
    
    for day in days[:15]:  # Limit to 15 days in pdf to fit page 2
        total_day_tasks = sum(data["desglose_diario"][day].values())
        day_rows.append([day] + [str(data["desglose_diario"][day].get(t, 0)) for t in TASK_COLORS.keys()] + [str(total_day_tasks)])
        
    day_table = Table(day_rows, colWidths=[65, 60, 55, 65, 55, 60, 60, 50])
    day_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, C_BG_LIGHT]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    story.append(day_table)
    
    # PAGE 3: HORARIOS Y PRODUCTIVIDAD SEMANAL
    story.append(PageBreak())
    story.append(Paragraph("Horarios y Carga Semanal", style_title))
    
    # Weekly breakdown
    story.append(Paragraph("Vista Semanal", style_h2))
    weeks_keys = sorted(data["desglose_semanal"].keys())
    
    if weeks_keys:
        fig, ax = plt.subplots(figsize=(6.5, 2.0))
        counts = [data["desglose_semanal"][wk] for wk in weeks_keys]
        ax.bar(weeks_keys, counts, color='#0284c7', width=0.4)
        ax.set_xticklabels(weeks_keys, fontsize=7)
        plt.tight_layout()
        
        chart3_buffer = io.BytesIO()
        plt.savefig(chart3_buffer, format='png', dpi=200)
        plt.close()
        chart3_buffer.seek(0)
        story.append(Image(chart3_buffer, width=450, height=140))
        story.append(Spacer(1, 10))
        
    # Active Hours Table
    story.append(Paragraph("Horario de Conexión y Duración de Jornada por Día", style_h2))
    horarios_headers = ["Fecha", "Primera Acción", "Última Acción", "Duración Jornada (h)"]
    horarios_rows = [[h for h in horarios_headers]]
    
    for row in data["detalles_jornada"][:12]: # limit to fit
        horarios_rows.append([row["fecha"], row["primera_accion"], row["ultima_accion"], f"{row['duracion']}h"])
        
    horarios_table = Table(horarios_rows, colWidths=[120, 120, 120, 120])
    horarios_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, C_BG_LIGHT]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    story.append(horarios_table)
    
    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


def generate_comparative_pdf(conn, sector, date_from=None, date_to=None):
    _check_deps()
    from backend.productivity_engine import get_analyst_productivity_data
    if not date_from:
        date_from = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')
        
    # Get all analysts in the sector (from cfg_gestion_metas)
    user_query = text("""
        SELECT DISTINCT a.analista, COALESCE(du.apellido_nombre, a.analista) 
        FROM (
            SELECT unnest(analistas_oficiales) as analista
            FROM cfg_gestion_metas
            WHERE gerencia = :sec
        ) a
        LEFT JOIN datos_usuario du ON a.analista = du.usuario
    """)
    users = conn.execute(user_query, {"sec": sector}).fetchall()
    
    analysts_data = []
    for u in users:
        u_name = u[0]
        u_full = u[1] or u_name
        try:
            prod = get_analyst_productivity_data(conn, u_name, date_from, date_to)
            analysts_data.append({
                "usuario": u_name,
                "nombre": u_full,
                "data": prod
            })
        except Exception:
            pass
            
    # Sort analysts by total tasks descending
    analysts_data = sorted(analysts_data, key=lambda x: x["data"]["kpis"]["tareas_totales"], reverse=True)
    
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    style_title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=C_PRIMARY,
        spaceAfter=15
    )
    
    style_h2 = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=C_PRIMARY,
        spaceBefore=15,
        spaceAfter=10
    )
    
    style_body = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=C_NEUTRAL
    )

    story = []
    
    story.append(Paragraph(f"Reporte Comparativo de Sector: {sector}", style_title))
    story.append(Paragraph(f"<b>Período:</b> {date_from} al {date_to} | <b>Fuente:</b> SADE (Materializada)", style_body))
    story.append(Spacer(1, 15))
    
    # Part 1: Productividad Global Table
    story.append(Paragraph("Productividad y Rendimiento por Analista", style_h2))
    
    headers = ["Analista", "Días Trab.", "Total Tareas", "Tareas/Día", "Jornada Med.", "Stock"]
    rows = [[h for h in headers]]
    
    for a in analysts_data:
        k = a["data"]["kpis"]
        rows.append([
            a["nombre"],
            str(k["dias_habiles"]),
            str(k["tareas_totales"]),
            str(k["promedio_diario"]),
            f"{k['jornada_media']}h",
            str(k["stock_total"])
        ])
        
    table1 = Table(rows, colWidths=[150, 70, 70, 70, 70, 70])
    table1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, C_BG_LIGHT]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    story.append(table1)
    story.append(Spacer(1, 15))
    
    # Part 2: Stock y Resultados
    story.append(PageBreak())
    story.append(Paragraph("Stock Actual y Resultados de Egresos", style_h2))
    
    stock_headers = ["Analista", "Stock Propio", "Stock Subs.", "Firmados", "Rechazados", "Tasa Rechazo"]
    stock_rows = [[h for h in stock_headers]]
    
    for a in analysts_data:
        k = a["data"]["kpis"]
        stock_rows.append([
            a["nombre"],
            str(k["stock_propio"]),
            str(k["stock_subs"]),
            str(k["firmados"]),
            str(k["rechazados"]),
            f"{k['tasa_rechazo']}%"
        ])
        
    table2 = Table(stock_rows, colWidths=[150, 75, 75, 75, 75, 80])
    table2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, C_BG_LIGHT]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    story.append(table2)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("<b>Recomendaciones de Gestión:</b>", style_body))
    story.append(Paragraph(
        "1. Priorizar el stock propio frente al de subsanación para acelerar las firmas directas.<br/>"
        "2. Evaluar desvíos en analistas con tasas de rechazo superiores al promedio del sector para homogeneizar criterios.<br/>"
        "3. Revisar la carga de trabajo diaria de aquellos analistas cuya jornada activa promedio sea menor a las 4 horas.",
        style_body
    ))
    
    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()
