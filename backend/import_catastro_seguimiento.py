import os
import csv
import urllib.request
from datetime import datetime
from sqlalchemy import create_engine, text

def parse_date(val):
    if not val:
        return None
    val = val.strip()
    if not val or val in ['1/01/0001', '01/01/0001', '-', '/']:
        return None
    # Intentar varios formatos habituales
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y'):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            pass
    return None

def parse_timestamp(val):
    if not val:
        return None
    val = val.strip()
    if not val:
        return None
    for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            pass
    return None

def main():
    local_sade = os.getenv('DATABASE_URL_LOCAL') or 'postgresql://postgres:lenovo@localhost:5432/sade_db'
    geo_url = local_sade.rsplit('/', 1)[0] + '/geo-mdr'
    print(f"Conectando a base de datos geo-mdr: {geo_url}")

    engine = create_engine(geo_url)

    # 1. Crear la tabla si no existe
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS public.cd3d_catastro_seguimiento (
        id SERIAL PRIMARY KEY,
        marca_temporal TIMESTAMP,
        fecha DATE,
        mensura VARCHAR(150),
        expediente VARCHAR(200),
        tipo VARCHAR(100),
        smp_origen TEXT,
        smp_surgente TEXT,
        if_registro VARCHAR(200),
        registro DATE,
        proceso_cartografia VARCHAR(150),
        constitucion DATE,
        ficha_parcelaria DATE,
        shape_parcelas TEXT,
        tad VARCHAR(150),
        ciudad_3d VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_catastro_cd3d_tipo ON public.cd3d_catastro_seguimiento (tipo);
    CREATE INDEX IF NOT EXISTS idx_catastro_cd3d_estado ON public.cd3d_catastro_seguimiento (ciudad_3d);
    CREATE INDEX IF NOT EXISTS idx_catastro_cd3d_mensura ON public.cd3d_catastro_seguimiento (mensura);
    CREATE INDEX IF NOT EXISTS idx_catastro_cd3d_expediente ON public.cd3d_catastro_seguimiento (expediente);
    """

    with engine.begin() as conn:
        conn.execute(text(create_table_sql))
        print("Tabla public.cd3d_catastro_seguimiento verificada/creada con éxito.")

    # 2. Descargar CSV desde Google Sheets
    url = 'https://docs.google.com/spreadsheets/d/1qkfkG_jP22zPh1DegPe70emPsShAcu_vjvCYNCZYhw4/export?format=csv'
    print(f"Descargando Google Sheet desde: {url}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode('utf-8', errors='replace')

    lines = content.splitlines()
    reader = list(csv.reader(lines))
    print(f"Filas totales descargadas: {len(reader)}")

    # Tomar de la fila 1 (index 1) hasta la 634 inclusive (635 filas en total considerando el encabezado)
    data_rows = reader[1:635]
    print(f"Filas de datos a procesar: {len(data_rows)}")

    records = []
    for row in data_rows:
        # Pad con vacíos si la fila tiene menos de 15 columnas
        row_padded = row + [''] * (15 - len(row))
        col_a_o = row_padded[:15]

        marca_temp = parse_timestamp(col_a_o[0])
        fecha = parse_date(col_a_o[1])
        mensura = col_a_o[2].strip() or None
        expediente = col_a_o[3].strip() or None
        tipo = col_a_o[4].strip() or None
        smp_origen = col_a_o[5].strip() or None
        smp_surgente = col_a_o[6].strip() or None
        if_reg = col_a_o[7].strip() or None
        registro = parse_date(col_a_o[8])
        proc_carto = col_a_o[9].strip() or None
        constitucion = parse_date(col_a_o[10])
        ficha_parc = parse_date(col_a_o[11])
        shape_parc = col_a_o[12].strip() or None
        tad = col_a_o[13].strip() or None
        ciudad_3d = col_a_o[14].strip() or None

        records.append({
            "marca_temporal": marca_temp,
            "fecha": fecha,
            "mensura": mensura,
            "expediente": expediente,
            "tipo": tipo,
            "smp_origen": smp_origen,
            "smp_surgente": smp_surgente,
            "if_registro": if_reg,
            "registro": registro,
            "proceso_cartografia": proc_carto,
            "constitucion": constitucion,
            "ficha_parcelaria": ficha_parc,
            "shape_parcelas": shape_parc,
            "tad": tad,
            "ciudad_3d": ciudad_3d
        })

    # 3. Insertar registros
    insert_sql = """
    INSERT INTO public.cd3d_catastro_seguimiento (
        marca_temporal, fecha, mensura, expediente, tipo,
        smp_origen, smp_surgente, if_registro, registro,
        proceso_cartografia, constitucion, ficha_parcelaria,
        shape_parcelas, tad, ciudad_3d
    ) VALUES (
        :marca_temporal, :fecha, :mensura, :expediente, :tipo,
        :smp_origen, :smp_surgente, :if_registro, :registro,
        :proceso_cartografia, :constitucion, :ficha_parcelaria,
        :shape_parcelas, :tad, :ciudad_3d
    )
    """

    with engine.begin() as conn:
        # Opcional: truncar si es carga inicial limpia
        conn.execute(text("TRUNCATE TABLE public.cd3d_catastro_seguimiento RESTART IDENTITY;"))
        conn.execute(text(insert_sql), records)
        count = conn.execute(text("SELECT COUNT(*) FROM public.cd3d_catastro_seguimiento;")).scalar()
        print(f"Carga completada exitosamente. Total filas en tabla: {count}")

if __name__ == '__main__':
    main()
