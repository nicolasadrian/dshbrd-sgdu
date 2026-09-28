import os
import sys
import pandas as pd
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import geo_engine, engine

def export_manzanas_por_seccion_barrio():
    print("[*] Obteniendo datos de Ciudad 3D - Extensiones Irregulares...")
    
    query = """
    WITH troneras_agg AS (
        SELECT TRIM(seccion) AS seccion,
               TRIM(manzana) AS manzana,
               SUM(CASE WHEN TRIM(UPPER(irregular)) = 'SI' THEN 1 ELSE 0 END) AS irregular_si,
               SUM(CASE WHEN TRIM(UPPER(irregular)) = 'NO' THEN 1 ELSE 0 END) AS irregular_no
        FROM public.mdr_troneras
        WHERE seccion IS NOT NULL AND manzana IS NOT NULL
        GROUP BY TRIM(seccion), TRIM(manzana)
    ),
    barrio_manzana AS (
        SELECT DISTINCT ON (TRIM(seccion), TRIM(manzana))
               TRIM(seccion) AS seccion,
               TRIM(manzana) AS manzana,
               TRIM(barrio) AS barrio
        FROM public.cur_parcelas_ok
        WHERE seccion IS NOT NULL AND manzana IS NOT NULL AND barrio IS NOT NULL AND TRIM(barrio) <> ''
    )
    SELECT bm.barrio,
           bm.seccion,
           bm.manzana,
           COALESCE(t.irregular_si, 0) AS irregular_si,
           COALESCE(t.irregular_no, 0) AS irregular_no
    FROM barrio_manzana bm
    JOIN public.manzanas m ON TRIM(m.seccion) = bm.seccion AND TRIM(m.manzana) = bm.manzana
    JOIN troneras_agg t ON t.seccion = bm.seccion AND t.manzana = bm.manzana
    ORDER BY bm.barrio, bm.seccion, bm.manzana
    """
    
    with geo_engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    
    print(f"[*] Registros base de manzanas obtenidos: {len(df):,}")
    
    # Agrupación por Barrio y Sección
    df_agg = df.groupby(['barrio', 'seccion']).agg(
        cantidad_manzanas=('manzana', 'count'),
        manzanas_con_extension_irregular=('irregular_si', lambda x: (x > 0).sum()),
        manzanas_sin_extension_irregular=('irregular_si', lambda x: (x == 0).sum()),
        total_extensiones_irregulares=('irregular_si', 'sum'),
        manzanas_detalle=('manzana', lambda x: ', '.join(sorted(x.unique())))
    ).reset_index()
    
    # Ordenar por barrio ascendente y sección
    df_agg = df_agg.sort_values(by=['barrio', 'seccion']).reset_index(drop=True)
    
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "extensiones_manzanas_por_seccion_barrio.csv"))
    df_agg.to_csv(out_path, index=False, encoding="utf-8-sig")
    
    print(f"[+] Archivo CSV generado exitosamente: {out_path}")
    print(f"[+] Total de combinaciones Barrio - Sección: {len(df_agg):,}")
    print(f"[+] Total de manzanas contabilizadas: {df_agg['cantidad_manzanas'].sum():,}")
    
    return out_path, df_agg

if __name__ == "__main__":
    export_manzanas_por_seccion_barrio()
