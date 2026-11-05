import os
from sqlalchemy import create_engine, text

def main():
    local_sade = os.getenv('DATABASE_URL_LOCAL') or 'postgresql://postgres:lenovo@localhost:5432/sade_db'
    geo_url = local_sade.rsplit('/', 1)[0] + '/geo-mdr'
    engine = create_engine(geo_url)
    with engine.begin() as conn:
        res = conn.execute(text("""
            UPDATE public.cd3d_catastro_seguimiento
            SET ciudad_3d = 'Publicado', updated_at = NOW()
            WHERE check_c3d = 'OK' AND (ciudad_3d IS NULL OR ciudad_3d != 'Publicado');
        """))
        print(f"Filas actualizadas a 'Publicado': {res.rowcount}")

        print("\nDistribución resultante de Estado (campo ciudad_3d):")
        for r in conn.execute(text("SELECT COALESCE(ciudad_3d, 'Sin Estado'), count(*) FROM public.cd3d_catastro_seguimiento GROUP BY 1 ORDER BY 2 DESC")):
            print(f"  {r[0]}: {r[1]}")

if __name__ == '__main__':
    main()
