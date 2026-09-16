import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

def remove_martinezmab():
    with engine.connect() as conn:
        print("Eliminando MARTINEZMAB de analistas_oficiales en catastro...")
        rows = conn.execute(text("SELECT id, analistas_oficiales FROM cfg_gestion_metas WHERE gerencia = 'catastro'")).mappings().fetchall()
        for r in rows:
            analistas = r['analistas_oficiales'] or []
            nuevos_analistas = [a for a in analistas if a != 'MARTINEZMAB']
            if len(nuevos_analistas) != len(analistas):
                conn.execute(
                    text("UPDATE cfg_gestion_metas SET analistas_oficiales = :a WHERE id = :id"),
                    {"a": nuevos_analistas, "id": r['id']}
                )
        conn.commit()
        print("MARTINEZMAB eliminado con éxito.")

if __name__ == '__main__':
    remove_martinezmab()
