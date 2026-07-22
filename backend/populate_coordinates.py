import re
import sys
import time
import json
import urllib.parse
import urllib.request
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import text
from database import engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('populate_coordinates.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("geocodificador")

# Mapeo específico de columna de dirección/ubicación por tabla GEDO
TABLE_LOCATION_COLUMNS = {
    "gedo_ifocd_datos": "ubicacion",
    "gedo_ifpdo_datos": "ubicacion",
    "gedo_proin_datos": "ubicacion",
    "gedo_pline_datos": "ubicacion",
    "gedo_ifsmc_datos": "ubicacion",
    "gedo_ifsmi_datos": "ubicacion",
    "gedo_ifpco_datos": "ubicacion",
    "gedo_iftpt_datos": "ubicacion",
    "gedo_ifpeo_datos": "ubicacion",
    "gedo_ifcis_datos": "ubicacion",
    "gedo_ifrsp_datos": "ubicacion",
    "gedo_ifroc_datos": "calle_altura",
    "gedo_cecnu_datos": "dom_caba_calle",
    "gedo_fipar_datos": "dom_caba_calle",
    "gedo_ifgpa_datos": "componente_domicilio",
    "gedo_ifpcb_datos": "dir",
    "gedo_ifcao_datos": "datos",
    "gedo_ifcfp_datos": "datos",
    "gedo_ifcac_datos": "datos"
}

# Prioridad de columnas que contienen direcciones cuando no hay mapeo específico
LOCATION_COLUMNS_PRIORITY = [
    "calle_altura",
    "ubicacion",
    "dom_caba_calle",
    "domicilio",
    "domicilio_1",
    "dom_est_calle",
    "domicilio_fisica"
]

# Expresión regular para separar Calle y Altura
# Soporta sufijos alfabéticos (ej. "CAMPANA 1549A" -> Calle: "CAMPANA", Altura: "1549")
# Soporta alturas múltiples (ej. "QUESADA 2545/2549/2551" o "QUESADA 2545-2551" -> Calle: "QUESADA", Altura: "2545")
ADDRESS_REGEX = re.compile(r'^(.*?)\s+(\d+)[A-Za-z]?(?:[\s\/\-]+\d+)*\s*$')

def split_address(address_str):
    if not address_str:
        return None, None
    # Corregir carácter  (código 65533 o 209 mal decodificado) reemplazándolo por Ñ
    address_str = address_str.replace('\ufffd', 'Ñ').replace('\xd1', 'Ñ').strip()
    match = ADDRESS_REGEX.search(address_str)
    if match:
        calle = match.group(1).strip()
        altura = match.group(2).strip()
        return calle, altura
    return address_str, None

def query_usig_api(calle, altura):
    """Consulta la API de USIG Normalizar para una combinación específica de calle y altura."""
    if not calle or not altura:
        return None, None
    direccion_completa = f"{calle} {altura}"
    dir_enc = urllib.parse.quote(direccion_completa)
    url = f"https://servicios.usig.buenosaires.gob.ar/normalizar/?direccion={dir_enc}&geocodificar=true&srid=4326"
    headers = {'accept': 'application/json'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_bytes = response.read()
            data = json.loads(res_bytes.decode('utf-8'))
            direcciones = data.get("direccionesNormalizadas", [])
            for d in direcciones:
                if d.get("cod_partido") == "caba" or d.get("nombre_partido") == "CABA":
                    coords = d.get("coordenadas")
                    if coords:
                        x = float(coords.get("x"))
                        y = float(coords.get("y"))
                        return x, y
    except Exception:
        pass
    return None, None

def generate_street_variants(calle):
    """Genera variantes progresivas del nombre de la calle para maximizar tasa de acierto en USIG."""
    variants = [calle]
    
    # Prefijos/títulos a remover de forma progresiva
    prefixes = [
        r'^\s*AV\.?\s+',
        r'^\s*DR\.?\s+',
        r'^\s*DRA\.?\s+',
        r'^\s*ING\.?\s+',
        r'^\s*ARQ\.?\s+',
        r'^\s*PRESIDENTE\s+',
        r'^\s*PRES\.?\s+',
        r'^\s*GRAL\.?\s+',
        r'^\s*GENERAL\s+',
        r'^\s*TENIENTE\s+CORONEL\s+',
        r'^\s*TENIENTE\s+GENERAL\s+',
        r'^\s*TENIENTE\s+',
        r'^\s*CNEL\.?\s+',
        r'^\s*CORONEL\s+',
        r'^\s*MARISCAL\s+',
        r'^\s*PADRE\s+',
        r'^\s*DON\s+'
    ]
    
    current = calle
    for pref in prefixes:
        new_curr = re.sub(pref, '', current, flags=re.IGNORECASE).strip()
        if new_curr and new_curr != current:
            variants.append(new_curr)
            current = new_curr

    # Si contiene Ñ, agregar versión reemplazando Ñ por nada o espacios
    if 'Ñ' in calle:
        variants.append(calle.replace('Ñ', ''))
        
    # Si contiene "DE LA MADRID", agregar variante unificada "LAMADRID" o "DE LAMADRID"
    if "DE LA MADRID" in calle.upper():
        variants.append(re.sub(r'\bDE\s+LA\s+MADRID\b', 'LAMADRID', calle, flags=re.IGNORECASE))
        variants.append(re.sub(r'\bDE\s+LA\s+MADRID\b', 'DE LAMADRID', calle, flags=re.IGNORECASE))
        if current:
            variants.append(re.sub(r'\bDE\s+LA\s+MADRID\b', 'LAMADRID', current, flags=re.IGNORECASE))
            variants.append(re.sub(r'\bDE\s+LA\s+MADRID\b', 'DE LAMADRID', current, flags=re.IGNORECASE))

    # Variante quitando nombres intermedios o iniciales (ej. "ROMULO S. NAON" -> "ROMULO NAON" -> "NAON")
    tokens = [t for t in current.split() if len(t) > 1 and not t.endswith('.')]
    if len(tokens) >= 1:
        # Última palabra (apellido principal ej. "NAON")
        variants.append(tokens[-1])
        if len(tokens) >= 2:
            # Últimas dos palabras
            variants.append(" ".join(tokens[-2:]))

    # Eliminar duplicados manteniendo el orden
    seen = set()
    unique_variants = []
    for v in variants:
        v_clean = v.strip()
        if v_clean and v_clean not in seen:
            seen.add(v_clean)
            unique_variants.append(v_clean)
            
    return unique_variants

def geocode_address(calle, altura):
    """Intenta geocodificar probando el nombre original y luego sus variantes progresivas."""
    variants = generate_street_variants(calle)
    for var in variants:
        x, y = query_usig_api(var, altura)
        if x is not None and y is not None:
            return x, y
    return None, None

def process_address(raw_addr):
    """Función de ayuda para el pool de hilos."""
    calle, altura = split_address(raw_addr)
    if calle and altura:
        x, y = geocode_address(calle, altura)
        if x is not None and y is not None:
            return raw_addr, x, y
    return raw_addr, None, None

def main():
    logger.info("Iniciando geocodificación masiva de tablas GEDO (Método Normalizar USIG - Lat/Long)...")
    
    conn = engine.connect()
    # Desactivar timeout de sentencias
    conn.execute(text("SET statement_timeout = 0;"))
    conn.commit()
    
    query_tables = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name LIKE 'gedo_%_datos'
        ORDER BY table_name;
    """
    tables = [row[0] for row in conn.execute(text(query_tables)).fetchall()]
    # Filtrar solo aquellas tablas que tengamos configuradas en TABLE_LOCATION_COLUMNS
    tables = [t for t in tables if t in TABLE_LOCATION_COLUMNS]
    logger.info(f"Se procesarán {len(tables)} tablas configuradas en TABLE_LOCATION_COLUMNS: {tables}")
    
    # Cache global en memoria para evitar repetir llamadas de API
    geo_cache = {}
    
    for table in tables:
        logger.info(f"\nAnalizando tabla: {table}")
        
        # Agregar columnas x e y si no existen
        conn.execute(text(f"ALTER TABLE public.{table} ADD COLUMN IF NOT EXISTS x DOUBLE PRECISION;"))
        conn.execute(text(f"ALTER TABLE public.{table} ADD COLUMN IF NOT EXISTS y DOUBLE PRECISION;"))
        
        # Limpiar coordenadas anteriores en formato Gauss-Kruger (valores positivos grandes)
        # para que sean re-geocodificadas en formato WGS84 Lat/Long (valores negativos)
        conn.execute(text(f"UPDATE public.{table} SET x = NULL, y = NULL WHERE x > 0 OR y > 0;"))
        conn.commit()
        
        # Buscar qué columna de ubicación existe en esta tabla
        query_cols = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}';"
        existing_cols = [row[0] for row in conn.execute(text(query_cols)).fetchall()]
        
        location_col = None
        if table in TABLE_LOCATION_COLUMNS:
            target_col = TABLE_LOCATION_COLUMNS[table]
            if target_col in existing_cols:
                location_col = target_col
            else:
                logger.warning(f"La columna especificada '{target_col}' no existe en la tabla {table}.")

        if not location_col:
            for col in LOCATION_COLUMNS_PRIORITY:
                if col in existing_cols:
                    location_col = col
                    break
                
        if not location_col:
            logger.warning(f"No se detectó columna de ubicación compatible para la tabla {table}. Omitiendo.")
            continue
            
        logger.info(f"Usando columna de ubicación: '{location_col}'")
        
        # Buscar todas las direcciones únicas que no tengan coordenadas asignadas (x e y nulos)
        query_addresses = f"""
            SELECT DISTINCT {location_col} 
            FROM public.{table} 
            WHERE {location_col} IS NOT NULL AND {location_col} <> '' AND (x IS NULL OR y IS NULL);
        """
        addresses = [row[0] for row in conn.execute(text(query_addresses)).fetchall()]
        logger.info(f"Encontradas {len(addresses):,} direcciones únicas pendientes de geocodificación.")
        
        if not addresses:
            logger.info("Sin direcciones pendientes para esta tabla.")
            continue
            
        # Filtrar direcciones que ya resolvimos y están en caché
        pending_addresses = []
        cached_updates = []
        for addr in addresses:
            if addr in geo_cache:
                x, y = geo_cache[addr]
                if x is not None and y is not None:
                    cached_updates.append((addr, x, y))
            else:
                pending_addresses.append(addr)
                
        logger.info(f"Direcciones en caché en memoria: {len(cached_updates):,} | Consultando API para: {len(pending_addresses):,}")
        
        # Resolver direcciones pendientes mediante ThreadPoolExecutor
        resolved_count = 0
        if pending_addresses:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(process_address, addr): addr for addr in pending_addresses}
                
                for idx, future in enumerate(as_completed(futures), 1):
                    addr, x, y = future.result()
                    if x is not None and y is not None:
                        geo_cache[addr] = (x, y)
                        cached_updates.append((addr, x, y))
                        resolved_count += 1
                        
                    if idx % 100 == 0 or idx == len(pending_addresses):
                        sys.stdout.write(f"\r    Consultado API: {idx:,} / {len(pending_addresses):,} completo")
                        sys.stdout.flush()
            print()
            
        logger.info(f"Geocodificación finalizada. Direcciones resueltas con coordenadas: {resolved_count:,}")
        
        # Realizar actualizaciones en base de datos
        logger.info("Actualizando base de datos...")
        update_query = f"""
            UPDATE public.{table}
            SET x = :x, y = :y
            WHERE {location_col} = :addr AND (x IS NULL OR y IS NULL);
        """
        
        # Procesar actualizaciones en lotes
        batch_size = 500
        for i in range(0, len(cached_updates), batch_size):
            batch = cached_updates[i : i + batch_size]
            for addr, x, y in batch:
                conn.execute(text(update_query), {"x": x, "y": y, "addr": addr})
            conn.commit()
            sys.stdout.write(f"\r    Actualizados {min(i+batch_size, len(cached_updates)):,} / {len(cached_updates):,} registros")
            sys.stdout.flush()
        print()
        logger.info(f"Tabla {table} actualizada correctamente.")
        
    conn.close()
    logger.info("Proceso de geocodificación finalizado exitosamente.")

if __name__ == "__main__":
    main()
