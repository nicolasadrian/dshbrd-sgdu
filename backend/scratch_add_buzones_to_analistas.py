import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

buzones_a_incorporar = [
    'DGROC-CIC',
    'DGROC-COPIAPLANO',
    'DGROC-DCATDES',
    'DGROC-DCATMEN',
    'DGROC-DCATPOL',
    'DGROC-DCATTIT'
]

def add_buzones_to_analistas():
    with engine.connect() as conn:
        print("Incorporando buzones a analistas_oficiales para Catastro...")
        rows = conn.execute(text("SELECT id, analistas_oficiales FROM cfg_gestion_metas WHERE gerencia = 'catastro'")).mappings().fetchall()
        for r in rows:
            analistas = list(r['analistas_oficiales'] or [])
            modificado = False
            for b in buzones_a_incorporar:
                if b not in analistas:
                    analistas.append(b)
                    modificado = True
            if modificado:
                conn.execute(
                    text("UPDATE cfg_gestion_metas SET analistas_oficiales = :a WHERE id = :id"),
                    {"a": analistas, "id": r['id']}
                )
        conn.commit()
        print("Buzones incorporados con éxito a la configuración.")

if __name__ == '__main__':
    add_buzones_to_analistas()
