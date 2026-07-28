import os
import io
import logging
from datetime import datetime
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

logger = logging.getLogger("pdf_generator")

# Dimensiones A3 Landscape en puntos (1 mm = 2.83464567 pt)
# A3 Landscape: Ancho = 1190.55 pt (420 mm), Alto = 841.89 pt (297 mm)
PAGE_WIDTH, PAGE_HEIGHT = landscape(A3)
MARGIN_CM = 0.5
MARGIN_PT = MARGIN_CM * 28.3465  # 0.5 cm = 14.17 pt

# Ruta al logo oficial del Gobierno de la Ciudad
ESCUDO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "img", "Nuevo_escudo_de_la_Ciudad_de_Buenos_Aires.png"))

# Registrar fuentes Google Sans para ReportLab
FONTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fonts"))
google_sans_reg = os.path.join(FONTS_DIR, "GoogleSans-Regular.ttf")
google_sans_bold = os.path.join(FONTS_DIR, "GoogleSans-Bold.ttf")

FONT_REG = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

if os.path.exists(google_sans_reg):
    try:
        pdfmetrics.registerFont(TTFont("GoogleSans-Regular", google_sans_reg))
        FONT_REG = "GoogleSans-Regular"
    except Exception as e:
        logger.warning(f"No se pudo registrar GoogleSans-Regular en ReportLab: {e}")

if os.path.exists(google_sans_bold):
    try:
        pdfmetrics.registerFont(TTFont("GoogleSans-Bold", google_sans_bold))
        FONT_BOLD = "GoogleSans-Bold"
    except Exception as e:
        logger.warning(f"No se pudo registrar GoogleSans-Bold en ReportLab: {e}")

def extract_lines_from_geom(geom):
    """Extrae líneas de polígonos o multipolígonos de Shapely."""
    if geom is None or geom.is_empty:
        return []
    gtype = geom.geom_type
    lines = []
    if gtype == 'Polygon':
        lines.append(geom.exterior.xy)
        for hole in geom.interiors:
            lines.append(hole.xy)
    elif gtype == 'MultiPolygon':
        for poly in geom.geoms:
            lines.extend(extract_lines_from_geom(poly))
    elif gtype in ('LineString', 'MultiLineString'):
        if gtype == 'LineString':
            lines.append(geom.xy)
        else:
            for ls in geom.geoms:
                lines.append(ls.xy)
    return lines

def render_dxf_or_geometry_to_image(seccion, manzana, file_path=None):
    """
    Renderiza el dibujo morfológico a PNG de Ultra Alta Definición (600 DPI - 168 Megapíxeles) para el plano A3.
    - Utiliza fuentes Google Sans para renderizado tipográfico si están disponibles.
    - Garantiza resolución ultra-nítida al hacer zoom sin pixelado en visor PDF.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import json
    from shapely.geometry import shape
    
    if os.path.exists(google_sans_bold):
        try:
            fm.fontManager.addfont(google_sans_bold)
        except Exception:
            pass
    if os.path.exists(google_sans_reg):
        try:
            fm.fontManager.addfont(google_sans_reg)
        except Exception:
            pass

    matplotlib.rcParams['font.sans-serif'] = ['Google Sans', 'Arial', 'Helvetica', 'sans-serif']
    matplotlib.rcParams['font.family'] = 'sans-serif'

    img_buf = io.BytesIO()
    
    # 1. Si existe archivo DXF subido, procesar y renderizar con ezdxf a ULTRA RESOLUCIÓN (600 DPI)
    if file_path and os.path.exists(file_path) and file_path.lower().endswith('.dxf'):
        try:
            import ezdxf
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.config import Configuration, LinePolicy
            from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
            
            doc = ezdxf.readfile(file_path)
            
            if 'DASHED' not in doc.linetypes:
                try:
                    doc.linetypes.new('DASHED', dxfattribs={'description': 'Dashed line - - -', 'pattern': [5.0, 3.0, -3.0]})
                except Exception:
                    pass
            
            msp = doc.modelspace()
            for entity in msp:
                layer_name = (entity.dxf.layer or "").lower()
                
                # Ocultar capas de tejido urbano / volumetría / edificabilidad
                if any(k in layer_name for k in ['tejido', 'edificab', 'volumetria', 'tej']):
                    entity.dxf.invisible = 1
                    continue
                    
                # Banda Mínima: LÍNEA CORTADA (DASHED)
                if any(k in layer_name for k in ['banda', 'bm', 'afec']):
                    entity.dxf.linetype = 'DASHED'
                    entity.dxf.color = 1  # Rojo
                    
                # Texto / MText / Etiquetas: COLOR NEGRO (#000000)
                if entity.dxftype() in ('TEXT', 'MTEXT') or any(k in layer_name for k in ['texto', 'text', 'calle', 'parc', 'nom', 'smp', 'etiqueta']):
                    entity.dxf.color = 7
                    try:
                        entity.rgb = (0, 0, 0)
                    except Exception:
                        pass
            
            fig = plt.figure(figsize=(24, 19.5), dpi=600)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.set_axis_off()
            
            config = Configuration(
                line_policy=LinePolicy.ACCURATE,
                min_lineweight=1.5
            )
            ctx = RenderContext(doc)
            out = MatplotlibBackend(ax)
            frontend = Frontend(ctx, out, config=config)
            frontend.draw_layout(msp, finalize=True)
            
            # Forzar todas las etiquetas de texto a COLOR NEGRO ABSOLUTO (#000000) con Google Sans
            for txt in ax.texts:
                txt.set_color('#000000')
                txt.set_fontweight('bold')
                txt.set_fontsize(11.0)
                txt.set_bbox(dict(boxstyle='square,pad=0.18', facecolor='white', edgecolor='none', alpha=0.92))
                
            fig.savefig(img_buf, format='png', bbox_inches='tight', pad_inches=0.01, facecolor='white')
            plt.close(fig)
            img_buf.seek(0)
            return img_buf
        except Exception as e:
            logger.warning(f"No se pudo renderizar DXF con ezdxf ({e}). Generando plano desde base de datos...")

    # 2. Render vectorial estructurado en ULTRA RESOLUCIÓN (600 DPI) desde PostGIS (geo_engine)
    try:
        try:
            from backend.database import get_geo_mdr_engine
        except ImportError:
            from database import get_geo_mdr_engine
        from sqlalchemy import text
        
        geo_engine = get_geo_mdr_engine()
        with geo_engine.connect() as conn:
            s_clean = seccion.strip().zfill(3)
            m_clean = manzana.strip()
            
            # A. Manzana (Contorno principal)
            q_mza = "SELECT ST_AsGeoJSON(geom) FROM public.manzanas WHERE (TRIM(seccion) = :s OR LPAD(TRIM(seccion), 3, '0') = :s) AND TRIM(manzana) = :m LIMIT 1"
            mza_json = conn.execute(text(q_mza), {"s": s_clean, "m": m_clean}).scalar()
            
            # B. Parcelas de la manzana con número y centroide
            q_parc = """
                SELECT parcela, smp, ST_AsGeoJSON(geom), ST_X(ST_Centroid(geom)), ST_Y(ST_Centroid(geom))
                FROM public.cur_parcelas_ok 
                WHERE (TRIM(seccion) = :s OR LPAD(TRIM(seccion), 3, '0') = :s) AND TRIM(manzana) = :m
            """
            parc_rows = conn.execute(text(q_parc), {"s": s_clean, "m": m_clean}).fetchall()
            
            # C. LFI
            q_lfi = "SELECT ST_AsGeoJSON(geom) FROM public.mdr_lineadefrenteinterno WHERE (TRIM(seccion) = :s OR LPAD(TRIM(seccion), 3, '0') = :s) AND TRIM(manzana) = :m"
            lfi_rows = [r[0] for r in conn.execute(text(q_lfi), {"s": s_clean, "m": m_clean}).fetchall() if r[0]]
            
            # D. LIB (Basamento)
            q_lib = "SELECT ST_AsGeoJSON(geom) FROM public.mdr_lineadebasamento WHERE (TRIM(seccion) = :s OR LPAD(TRIM(seccion), 3, '0') = :s) AND TRIM(manzana) = :m"
            lib_rows = [r[0] for r in conn.execute(text(q_lib), {"s": s_clean, "m": m_clean}).fetchall() if r[0]]
            
            # E. Troneras
            q_tron = "SELECT irregular, ST_AsGeoJSON(geom) FROM public.mdr_troneras WHERE (TRIM(seccion) = :s OR LPAD(TRIM(seccion), 3, '0') = :s) AND TRIM(manzana) = :m"
            tron_rows = conn.execute(text(q_tron), {"s": s_clean, "m": m_clean}).fetchall()
            
            # F. Banda Mínima (LÍNEA CORTADA)
            q_bm = """
                SELECT ST_AsGeoJSON(bm.geom) 
                FROM public.mdr_banda_minima bm 
                INNER JOIN public.cur_parcelas_ok p ON bm.smp = p.smp 
                WHERE (TRIM(p.seccion) = :s OR LPAD(TRIM(p.seccion), 3, '0') = :s) AND TRIM(p.manzana) = :m AND bm.geom IS NOT NULL
            """
            bm_rows = [r[0] for r in conn.execute(text(q_bm), {"s": s_clean, "m": m_clean}).fetchall() if r[0]]
            
            calles_rows = []
            if mza_json:
                try:
                    import geopandas as gpd
                    mza_shape = shape(json.loads(mza_json))
                    query_calles = "SELECT nomoficial, geom FROM public.calles WHERE geom IS NOT NULL AND nomoficial IS NOT NULL AND TRIM(nomoficial) <> ''"
                    gdf_calles = gpd.read_postgis(query_calles, con=conn, geom_col="geom", crs="EPSG:22186")
                    if not gdf_calles.empty:
                        calles_bbox = gdf_calles[gdf_calles.intersects(mza_shape.buffer(120))]
                        seen_calles = set()
                        for idx, r_calle in calles_bbox.iterrows():
                            nom = r_calle.get('nomoficial')
                            if not nom or nom in seen_calles or str(nom) == 'nan':
                                continue
                            c_geom = r_calle['geom']
                            if c_geom and not c_geom.is_empty:
                                nearest_pt = c_geom.interpolate(c_geom.project(mza_shape.centroid))
                                dist = nearest_pt.distance(mza_shape)
                                if dist <= 120:
                                    seen_calles.add(nom)
                                    calles_rows.append((str(nom).strip().upper(), nearest_pt.x, nearest_pt.y))
                except Exception as e_c:
                    logger.warning(f"No se pudieron consultar calles: {e_c}")
            
            fig, ax = plt.subplots(figsize=(24, 19.5), dpi=600)
            ax.set_facecolor("white")
            
            # 1. Dibujar Contorno de Manzana
            if mza_json:
                m_geom = shape(json.loads(mza_json))
                for x, y in extract_lines_from_geom(m_geom):
                    ax.plot(x, y, color='#404040', linewidth=2.8, zorder=2)
                    
            # 2. Dibujar Parcelas y ETIQUETAS DE PARCELA EN COLOR NEGRO (#000000)
            if parc_rows:
                for p_num, smp, p_json, cx, cy in parc_rows:
                    if p_json:
                        p_geom = shape(json.loads(p_json))
                        for x, y in extract_lines_from_geom(p_geom):
                            ax.plot(x, y, color='#606060', linewidth=1.5, zorder=3)
                        
                        # ETIQUETA DE PARCELA (COLOR NEGRO ABSOLUTO #000000, GOOGLE SANS BOLD)
                        if p_num and cx and cy:
                            p_clean = str(p_num).strip()
                            ax.text(cx, cy, p_clean, color='#000000', fontsize=10.0, fontweight='bold',
                                    ha='center', va='center', zorder=20,
                                    bbox=dict(boxstyle='round,pad=0.18', facecolor='white', edgecolor='none', alpha=0.9))

            # 3. Dibujar Basamento (LIB) - Amarillo #ffd306
            for l_json in lib_rows:
                l_geom = shape(json.loads(l_json))
                for x, y in extract_lines_from_geom(l_geom):
                    ax.plot(x, y, color='#ffd306', linewidth=2.8, zorder=5)

            # 4. Dibujar LFI - Azul #3579b1
            for l_json in lfi_rows:
                l_geom = shape(json.loads(l_json))
                for x, y in extract_lines_from_geom(l_geom):
                    ax.plot(x, y, color='#3579b1', linewidth=3.2, zorder=6)

            # 5. Dibujar Troneras (SI = Irregular Rojo #e41a1c, NO = Regular Azul #3579b1)
            for irr_val, t_json in tron_rows:
                if t_json:
                    t_geom = shape(json.loads(t_json))
                    t_color = '#e41a1c' if str(irr_val).upper() == 'SI' else '#3579b1'
                    t_lw = 3.5 if str(irr_val).upper() == 'SI' else 2.8
                    for x, y in extract_lines_from_geom(t_geom):
                        ax.plot(x, y, color=t_color, linewidth=t_lw, zorder=7)

            # 6. DIBUJAR BANDA MÍNIMA COMO LÍNEA CORTADA / DASHED RED LINE (#e41a1c)
            for bm_j in bm_rows:
                bm_geom = shape(json.loads(bm_j))
                for x, y in extract_lines_from_geom(bm_geom):
                    ax.plot(x, y, color='#e41a1c', linestyle='--', linewidth=3.5, dashes=(20, 10), dash_capstyle='round', zorder=12)

            # 7. DIBUJAR ETIQUETAS DE NOMBRES DE CALLES EN COLOR NEGRO ABSOLUTO (#000000)
            if calles_rows:
                for c_nom, cx, cy in calles_rows:
                    if c_nom and cx and cy:
                        c_clean = str(c_nom).strip().upper()
                        ax.text(cx, cy, c_clean, color='#000000', fontsize=11.5, fontweight='bold',
                                ha='center', va='center', zorder=25,
                                bbox=dict(boxstyle='square,pad=0.28', facecolor='#ffffff', edgecolor='#cbd5e1', linewidth=1.0, alpha=0.95))
                        
            ax.set_aspect('equal')
            ax.grid(False)
            ax.set_axis_off()
            
            fig.savefig(img_buf, format='png', bbox_inches='tight', pad_inches=0.02, facecolor='white')
            plt.close(fig)
            img_buf.seek(0)
            return img_buf

    except Exception as e:
        logger.error(f"Error generando gráfico matplotlib de respaldo: {e}")
        fig, ax = plt.subplots(figsize=(16, 13), dpi=600)
        ax.text(0.5, 0.5, f"Trazado Sección {seccion} - Manzana {manzana}", ha='center', va='center', fontsize=22, color='#000000')
        ax.axis('off')
        fig.savefig(img_buf, format='png', bbox_inches='tight')
        plt.close(fig)
        img_buf.seek(0)
        return img_buf

def generate_lfi_a3_pdf(seccion, manzana, barrio="", comuna="", disposicion="", estado="En curso", analista="", file_path=None):
    """
    Genera un archivo PDF formato A3 Horizontal con márgenes de 0.5 cm (5 mm) y fuente Google Sans.
    - Banda Mínima renderizada como LÍNEA CORTADA / DASHED RED LINE (#e41a1c).
    - Nombres de calles y parcelas visibles en COLOR NEGRO ABSOLUTO (#000000) en Ultra Alta Definición (600 DPI).
    - Tipografía oficial Google Sans aplicada al PDF y encabezados ampliados.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A3))
    
    x_min = MARGIN_PT
    y_min = MARGIN_PT
    x_max = PAGE_WIDTH - MARGIN_PT
    y_max = PAGE_HEIGHT - MARGIN_PT
    
    width_bounded = x_max - x_min
    height_bounded = y_max - y_min
    
    # 1. Dibujar Marco Exterior General (Márgenes de 0.5 cm)
    c.setLineWidth(1.8)
    c.setStrokeColor(colors.HexColor("#000000"))
    c.rect(x_min, y_min, width_bounded, height_bounded)
    
    # Panel lateral derecho (ancho 190.0 pt / ~67 mm)
    panel_width = 190.0
    drawing_width = width_bounded - panel_width
    x_split = x_max - panel_width
    
    # Línea divisoria vertical principal
    c.setLineWidth(1.8)
    c.line(x_split, y_min, x_split, y_max)
    
    # --- RECUADRO PRINCIPAL (DIBUJO CAD / PLANO ULTRA HD 600 DPI) ---
    img_buf = render_dxf_or_geometry_to_image(seccion, manzana, file_path)
    if img_buf:
        img_reader = ImageReader(img_buf)
        pad = 2.0
        img_x = x_min + pad
        img_y = y_min + pad
        img_w = drawing_width - (pad * 2.0)
        img_h = height_bounded - (pad * 2.0)
        
        c.drawImage(img_reader, img_x, img_y, width=img_w, height=img_h, preserveAspectRatio=True, anchor='c')
    
    # --- PANEL LATERAL DERECHO (CARÁTULA) ---
    h_r1 = 220.0
    h_r2 = 100.0
    h_r3 = 115.0
    
    y_r1_bottom = y_max - h_r1
    y_r2_bottom = y_r1_bottom - h_r2
    y_r3_bottom = y_r2_bottom - h_r3
    
    # Dibujar líneas horizontales divisoras
    c.setLineWidth(1.4)
    c.line(x_split, y_r1_bottom, x_max, y_r1_bottom)
    c.line(x_split, y_r2_bottom, x_max, y_r2_bottom)
    c.line(x_split, y_r3_bottom, x_max, y_r3_bottom)
    
    x_center = x_split + (panel_width / 2.0)
    
    # RECUADRO 1: ESCUDO + TEXTO INSTITUCIONAL CENTRADOS (TIPOGRAFÍA MÁS GRANDE)
    y_r1_center = y_max - (h_r1 / 2.0)
    escudo_w = 78.0
    escudo_h = 78.0
    gap = 14.0
    
    escudo_top = y_r1_center + 70.0
    escudo_y = escudo_top - escudo_h
    escudo_x = x_center - (escudo_w / 2.0)
    
    if os.path.exists(ESCUDO_PATH):
        try:
            escudo_img = ImageReader(ESCUDO_PATH)
            c.drawImage(escudo_img, escudo_x, escudo_y, width=escudo_w, height=escudo_h, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            logger.error(f"Error al cargar imagen del escudo: {e}")

    c.setFillColor(colors.HexColor("#000000"))
    c.setFont(FONT_BOLD, 12.0)
    
    text_start_y = escudo_y - gap
    c.drawCentredString(x_center, text_start_y, "GOBIERNO DE LA CIUDAD")
    c.drawCentredString(x_center, text_start_y - 15.0, "AUTÓNOMA DE BUENOS AIRES")
    
    c.setFont(FONT_BOLD, 10.0)
    c.drawCentredString(x_center, text_start_y - 33.0, "SECRETARÍA DE GESTIÓN Y")
    c.drawCentredString(x_center, text_start_y - 46.0, "DESARROLLO URBANO")

    # RECUADRO 2: TÍTULO DEL TIPO DE PLANO (CENTRADO Y AMPLIADO)
    c.setFont(FONT_BOLD, 13.0)
    c.setFillColor(colors.HexColor("#000000"))
    y_r2_center = y_r1_bottom - (h_r2 / 2.0) + 8.0
    c.drawCentredString(x_center, y_r2_center, "EXTENSIÓN DE ESPACIO")
    c.drawCentredString(x_center, y_r2_center - 17.0, "LIBRE DE MANZANA")

    # RECUADRO 3: VALOR DE SECCIÓN - MANZANA (SM) AMPLIALO EN TAMAÑO
    c.setFont(FONT_BOLD, 10.5)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawCentredString(x_center, y_r2_bottom - 22.0, "SECCIÓN - MANZANA (SM)")
    
    sec_str = str(seccion).strip().zfill(3)
    mza_str = str(manzana).strip().zfill(3)
    sm_value = f"{sec_str}-{mza_str}"
    
    c.setFont(FONT_BOLD, 32.0)
    c.setFillColor(colors.HexColor("#000000"))
    c.drawCentredString(x_center, y_r2_bottom - 68.0, sm_value)

    # RECUADRO 4: REFERENCIAS GRÁFICAS DEL PLANO
    c.setFont(FONT_BOLD, 11.0)
    c.setFillColor(colors.HexColor("#000000"))
    c.drawString(x_split + 12.0, y_r3_bottom - 22.0, "REFERENCIAS GRÁFICAS")
    
    c.setLineWidth(1.0)
    c.line(x_split + 12.0, y_r3_bottom - 27.0, x_max - 12.0, y_r3_bottom - 27.0)
    
    y_ref = y_r3_bottom - 52.0
    ref_items = [
        ("#3579b1", "— — —", "Línea de Frente Interno"),
        ("#e41a1c", "━━━━", "Extensión Irregular"),
        ("#ffd306", "━━━━", "Línea de Basamento"),
        ("#e41a1c", "- - - -", "Banda Mínima Afec."),
        ("#606060", "━━━━", "Límite Parcelario")
    ]
    
    for color_hex, sym, label in ref_items:
        c.setFont(FONT_BOLD, 10.0)
        c.setFillColor(colors.HexColor(color_hex))
        c.drawString(x_split + 14.0, y_ref, sym)
        
        c.setFont(FONT_REG, 9.5)
        c.setFillColor(colors.HexColor("#1e293b"))
        c.drawString(x_split + 55.0, y_ref, label)
        y_ref -= 22.0
        
    c.showPage()
    c.save()
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
