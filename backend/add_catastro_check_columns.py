import os
from sqlalchemy import create_engine, text

def main():
    local_sade = os.getenv('DATABASE_URL_LOCAL') or 'postgresql://postgres:lenovo@localhost:5432/sade_db'
    geo_url = local_sade.rsplit('/', 1)[0] + '/geo-mdr'
    engine = create_engine(geo_url)
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE public.cd3d_catastro_seguimiento 
            ADD COLUMN IF NOT EXISTS check_c3d VARCHAR(20) DEFAULT 'PENDIENTE',
            ADD COLUMN IF NOT EXISTS check_c3d_fecha TIMESTAMP,
            ADD COLUMN IF NOT EXISTS check_c3d_detalle JSONB;
            
            CREATE INDEX IF NOT EXISTS idx_catastro_check_c3d ON public.cd3d_catastro_seguimiento(check_c3d);
        """))
        print("Columnas de verificación creadas exitosamente.")

if __name__ == '__main__':
    main()
