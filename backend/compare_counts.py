import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

local_url = (os.getenv('DATABASE_URL_LOCAL') or 'postgresql://postgres:lenovo@localhost:5432/sade_db').rsplit('/', 1)[0] + '/geo-mdr'
prod_url = ((os.getenv('DATABASE_URL_PUBLIC') or os.getenv('DATABASE_URL')).replace('postgres://', 'postgresql://')).rsplit('/', 1)[0] + '/geo-mdr'
pdi_url = os.getenv('PDI_DATABASE_URL')

def inspect_db(name, url):
    print(f"=== {name} ===")
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        for t in ['cur_manzanasatipicas', 'cur_lfi_particularizadas', 'cur_lib_particularizadas', 'atipicas_base_morfo']:
            try:
                cur.execute(f"SELECT COUNT(*) FROM public.{t}")
                cnt = cur.fetchone()[0]
                if t == 'cur_manzanasatipicas':
                    cur.execute(f"SELECT UPPER(TRIM(mz_tipo)), COUNT(*) FROM public.{t} GROUP BY 1")
                    tipos = cur.fetchall()
                    print(f"  {t}: total={cnt} | tipos={tipos}")
                else:
                    print(f"  {t}: total={cnt}")
            except Exception as e:
                print(f"  {t}: NO EXISTE o ERROR ({e})")
                conn.rollback()
        conn.close()
    except Exception as err:
        print(f"  Error conectando a {name}: {err}")

if __name__ == "__main__":
    inspect_db("PDI (10.10.8.207)", pdi_url)
    inspect_db("LOCAL geo-mdr", local_url)
    inspect_db("PROD geo-mdr", prod_url)
