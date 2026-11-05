import os
import re
import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import create_engine, text

def check_single_smp(smp: str):
    """Consulta la API de Ciudad 3D para un SMP específico."""
    smp_clean = smp.strip()
    if not smp_clean:
        return {"smp": smp, "status": "ERROR", "mensaje": "SMP vacío"}

    url = f"https://epok.buenosaires.gob.ar/cur3d/seccion_edificabilidad/?smp={urllib.parse.quote(smp_clean)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8')
            data = json.loads(content)
            if isinstance(data, dict):
                if data.get('error'):
                    return {
                        "smp": smp_clean,
                        "status": "ERROR",
                        "mensaje": data.get('error'),
                        "encontrado": False
                    }
                else:
                    return {
                        "smp": smp_clean,
                        "status": "OK",
                        "mensaje": "Encontrado en Ciudad 3D",
                        "encontrado": True,
                        "altura_max": data.get('altura_max'),
                        "superficie_parcela": data.get('superficie_parcela'),
                        "unidad_edificabilidad": data.get('unidad_edificabilidad')
                    }
            return {"smp": smp_clean, "status": "ERROR", "mensaje": "Respuesta no esperada", "encontrado": False}
    except urllib.error.HTTPError as e:
        return {"smp": smp_clean, "status": "ERROR", "mensaje": f"HTTP {e.code}", "encontrado": False}
    except Exception as e:
        return {"smp": smp_clean, "status": "ERROR", "mensaje": str(e), "encontrado": False}

def parse_smps(smp_str: str):
    """Extrae la lista de SMPs individuales separando por comas, espacios o saltos."""
    if not smp_str:
        return []
    # Separar por comas, punto y comas o barras
    tokens = re.split(r'[,;\n]+', smp_str)
    res = []
    for t in tokens:
        cleaned = t.strip()
        if cleaned:
            res.append(cleaned)
    return res

def verify_record_smps(smp_surgente: str):
    """Verifica todos los SMPs surgentes de un registro y calcula el estado consolidado."""
    smps = parse_smps(smp_surgente)
    if not smps:
        return {
            "status": "SIN_SMP",
            "detalles": [{"mensaje": "No posee SMP Surgente definido", "status": "SIN_SMP"}]
        }

    detalles = []
    has_error = False
    has_ok = False

    for s in smps:
        res = check_single_smp(s)
        detalles.append(res)
        if res["status"] == "OK":
            has_ok = True
        else:
            has_error = True

    if has_ok and not has_error:
        overall_status = "OK"
    elif has_ok and has_error:
        overall_status = "PARCIAL"
    else:
        overall_status = "ERROR"

    return {
        "status": overall_status,
        "detalles": detalles
    }

def verify_all_records(limit=None):
    local_sade = os.getenv('DATABASE_URL_LOCAL') or 'postgresql://postgres:lenovo@localhost:5432/sade_db'
    geo_url = local_sade.rsplit('/', 1)[0] + '/geo-mdr'
    engine = create_engine(geo_url)

    with engine.connect() as conn:
        q = "SELECT id, smp_surgente FROM public.cd3d_catastro_seguimiento ORDER BY id ASC"
        if limit:
            q += f" LIMIT {limit}"
        rows = conn.execute(text(q)).fetchall()

    print(f"Iniciando verificación de {len(rows)} registros...")

    def worker(row):
        r_id, smp_surg = row[0], row[1]
        verif = verify_record_smps(smp_surg)
        return r_id, verif

    updates = []
    completed = 0
    start_time = time.time()

    # Ejecutar en concurrencia (max 8 hilos para no saturar EPOK)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(worker, r): r[0] for r in rows}
        for future in as_completed(futures):
            r_id, verif = future.result()
            updates.append({
                "id": r_id,
                "check_c3d": verif["status"],
                "check_c3d_detalle": json.dumps(verif["detalles"])
            })
            completed += 1
            if completed % 50 == 0 or completed == len(rows):
                print(f"  Procesados: {completed}/{len(rows)} ({(time.time()-start_time):.1f}s)")

    print("Guardando resultados en base de datos...")
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE public.cd3d_catastro_seguimiento
            SET 
                check_c3d = :check_c3d,
                check_c3d_fecha = NOW(),
                check_c3d_detalle = CAST(:check_c3d_detalle AS jsonb),
                ciudad_3d = CASE WHEN :check_c3d = 'OK' THEN 'Publicado' ELSE ciudad_3d END,
                updated_at = NOW()
            WHERE id = :id
        """), updates)

    print(f"Verificación finalizada con éxito en {(time.time()-start_time):.1f}s.")

if __name__ == '__main__':
    verify_all_records()
