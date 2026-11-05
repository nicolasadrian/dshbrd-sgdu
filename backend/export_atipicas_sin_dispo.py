import os
import shutil
import pandas as pd
from sqlalchemy import text
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from database import geo_engine

def export_sin_dispo_ambos():
    sql = """
        WITH lfi_agg AS (
            SELECT sm, COUNT(*) as cant_lfi FROM public.cur_lfi_particularizadas WHERE sm IS NOT NULL GROUP BY sm
        ),
        lib_agg AS (
            SELECT sm, COUNT(*) as cant_lib FROM public.cur_lib_particularizadas WHERE sm IS NOT NULL GROUP BY sm
        ),
        barrios_agg AS (
            SELECT sm, MAX(barrio) as barrio FROM public.cur_parcelas_ok GROUP BY sm
        )
        SELECT 
            m.sm as "SM",
            m.seccion as "Sección",
            m.manzana as "Manzana",
            COALESCE(p.barrio, 'SIN BARRIO') as "Barrio",
            m.comuna as "Comuna",
            COALESCE(m.disposicio, '') as "Disposición C3D",
            COALESCE(m.trazado, '') as "Trazado C3D",
            COALESCE(bm.disposicion, '') as "Disposición Morfo",
            COALESCE(bm.trazado, '') as "Trazado Morfo",
            'Sin Disposición en Ambos' as "Alerta Disposición",
            COALESCE(l.cant_lfi, 0) as "Cant. LFI",
            COALESCE(b.cant_lib, 0) as "Cant. LIB",
            CASE 
                WHEN UPPER(TRIM(COALESCE(m.trazado, ''))) = 'NO' THEN 'No requiere'
                WHEN UPPER(TRIM(COALESCE(m.trazado, ''))) = 'SI' THEN
                    CASE
                        WHEN COALESCE(l.cant_lfi, 0) > 0 AND COALESCE(b.cant_lib, 0) > 0 THEN 'Ambas (LFI + LIB)'
                        WHEN COALESCE(l.cant_lfi, 0) > 0 THEN 'Solo LFI'
                        WHEN COALESCE(b.cant_lib, 0) > 0 THEN 'Solo LIB'
                        ELSE 'Faltante (Ninguna)'
                    END
                ELSE 'No especifica'
            END as "Estado Trazado"
        FROM public.cur_manzanasatipicas m
        LEFT JOIN public.atipicas_base_morfo bm ON m.sm = bm.sm
        LEFT JOIN lfi_agg l ON m.sm = l.sm
        LEFT JOIN lib_agg b ON m.sm = b.sm
        LEFT JOIN barrios_agg p ON m.sm = p.sm
        WHERE UPPER(TRIM(m.mz_tipo)) = 'ATIPICA'
          AND ((m.disposicio IS NULL OR TRIM(m.disposicio) = '') AND (bm.disposicion IS NULL OR TRIM(bm.disposicion) = ''))
        ORDER BY m.seccion ASC, m.manzana ASC
    """
    
    with geo_engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    
    print(f"Total registros obtenidos: {len(df)}")
    
    # Export to Excel with styling
    output_filename = "Manzanas_Atipicas_Sin_Disposicion_Ambos_724.xlsx"
    desktop_dir = os.path.expanduser("~/Desktop")
    workspace_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_filename)
    desktop_path = os.path.join(desktop_dir, output_filename) if os.path.exists(desktop_dir) else workspace_path
    
    with pd.ExcelWriter(workspace_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Sin Disposición (Ambos)', index=False)
        ws = writer.sheets['Sin Disposición (Ambos)']
        
        # Header style (Dark slate blue)
        header_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        border_thin = Side(border_style="thin", color="CBD5E1")
        cell_border = Border(top=border_thin, left=border_thin, right=border_thin, bottom=border_thin)
        
        for col_idx in range(1, len(df.columns) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cell_border
            
        # Data formatting
        for row_idx in range(2, len(df) + 2):
            for col_idx in range(1, len(df.columns) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = cell_border
                cell.font = Font(name="Calibri", size=10)
                
                # Alignments
                col_name = df.columns[col_idx - 1]
                if col_name in ["SM", "Sección", "Manzana", "Comuna", "Trazado C3D", "Trazado Morfo", "Cant. LFI", "Cant. LIB"]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")
                    
        # Adjust column widths safely
        for col_idx, col_name in enumerate(df.columns, 1):
            max_val_len = df[col_name].astype(str).str.len().max()
            max_len = max(max_val_len if pd.notnull(max_val_len) else 0, len(col_name)) + 4
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max(max_len, 12), 40)
            
        ws.row_dimensions[1].height = 28
        
    print(f"Archivo guardado exitosamente en:\n - {workspace_path}")
    
    if os.path.exists(desktop_dir) and desktop_path != workspace_path:
        shutil.copy2(workspace_path, desktop_path)
        print(f" - {desktop_path}")

if __name__ == '__main__':
    export_sin_dispo_ambos()
