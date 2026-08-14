from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    r_p = conn.execute(text("SELECT * FROM mv_catastro_stock_propio LIMIT 1")).mappings().first()
    print('Sample row in mv_catastro_stock_propio:', dict(r_p) if r_p else 'Empty')

    r_i = conn.execute(text("SELECT * FROM mv_catastro_intervenciones_stock LIMIT 1")).mappings().first()
    print('Sample row in mv_catastro_intervenciones_stock:', dict(r_i) if r_i else 'Empty')
