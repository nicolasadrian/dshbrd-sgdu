import os
import sys
from sqlalchemy import create_engine, text

# Add backend directory to path to allow importing local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_PROD_URL = os.getenv("DATABASE_URL_PUBLIC", "postgresql://postgres:frQB7%7D0%26p~.C_.X%40Ymu(1tAO7@34.136.69.128:5432/sade_db")

SQL_VIEW = """
DROP MATERIALIZED VIEW IF EXISTS public.mvw_m2_permisados CASCADE;

CREATE MATERIALIZED VIEW public.mvw_m2_permisados AS
WITH ranked_rows AS (
    SELECT 
        o.id_expediente,
        o.expediente,
        
        -- Ubicación
        o.ubicacion AS direccion,
        o.ubicacion_dgseccion AS seccion,
        o.ubicacion_dgmanzana AS manzana,
        o.ubicacion_dgparcela AS parcela,
        o.ubicacion_dgcomuna AS comuna,
        o.ubicacion_dgbarrio AS barrio,
        o.hay_uf AS es_uf,
        COALESCE(o.ubicacion_dgseccion, '') || '-' || COALESCE(o.ubicacion_dgmanzana, '') || '-' || COALESCE(o.ubicacion_dgparcela, '') AS smp,
        o.x, -- Columna de longitud (X)
        o.y, -- Columna de latitud (Y)
        
        -- Datos del Trámite
        o.uso_particular AS uso_particularizado,
        o.tipo_tarea,
        o.tipo_obra,
        o.sup_terreno,
        o.sup_libre,
        o.sup_existente,
        o.sup_demoler,
        o.sup_construir,
        o.sup_subsuelo AS profundidad_subsuelos,
        o.subsuelos AS cantidad_subsuelos,
        o.pisos AS cantidad_pisos,
        o.altura AS altura_metros,
        o.cur AS uso_cur,
        
        -- Datos del Profesional
        o.apellido_profesional,
        o.nombre_profesional,
        o.matricula_profesional,
        
        -- Documentacion
        -- Plano (Concatenación de act-anio-nro-rep)
        CASE WHEN o.plano_obra_act IS NULL AND o.plano_obra_anio IS NULL AND o.plano_obra_nro IS NULL AND o.plano_obra_rep IS NULL THEN ''
             ELSE COALESCE(o.plano_obra_act, '') || '-' || COALESCE(CAST(o.plano_obra_anio AS INTEGER)::text, '') || '-' || COALESCE(CAST(o.plano_obra_nro AS INTEGER)::text, '') || '-' || COALESCE(o.plano_obra_rep, '')
        END AS plano,
        
        -- Encomienda Profesional (Concatenación de act-anio-nro-rep)
        CASE WHEN o.encomienda_profesional_act IS NULL AND o.encomienda_profesional_anio IS NULL AND o.encomienda_profesional_nro IS NULL AND o.encomienda_profesional_rep IS NULL THEN ''
             ELSE COALESCE(o.encomienda_profesional_act, '') || '-' || COALESCE(CAST(o.encomienda_profesional_anio AS INTEGER)::text, '') || '-' || COALESCE(CAST(o.encomienda_profesional_nro AS INTEGER)::text, '') || '-' || COALESCE(o.encomienda_profesional_rep, '')
        END AS encomienda_profesional,
        
        -- Comprobante Pagos Derechos (Concatenación de act-anio-nro-rep)
        CASE WHEN o.pago_derechos_act IS NULL AND o.pago_derechos_anio IS NULL AND o.pago_derechos_nro IS NULL AND o.pago_derechos_rep IS NULL THEN ''
             ELSE COALESCE(o.pago_derechos_act, '') || '-' || COALESCE(CAST(o.pago_derechos_anio AS INTEGER)::text, '') || '-' || COALESCE(CAST(o.pago_derechos_nro AS INTEGER)::text, '') || '-' || COALESCE(o.pago_derechos_rep, '')
        END AS comprobante_pagos_derechos,
        
        -- Informe de Dominio (Concatenación de act-anio-nro-rep)
        CASE WHEN o.informe_dominio_act IS NULL AND o.informe_dominio_anio IS NULL AND o.informe_dominio_nro IS NULL AND o.informe_dominio_rep IS NULL THEN ''
             ELSE COALESCE(o.informe_dominio_act, '') || '-' || COALESCE(CAST(o.informe_dominio_anio AS INTEGER)::text, '') || '-' || COALESCE(CAST(o.informe_dominio_nro AS INTEGER)::text, '') || '-' || COALESCE(o.informe_dominio_rep, '')
        END AS informe_dominio,
        
        -- Fechas para filtros
        o.fecha_creacion AS fecha_creacion_ocd,
        p.fecha_creacion AS fecha_creacion_pdo,
        
        -- Ránking para desempatar duplicados (tomamos el más reciente)
        ROW_NUMBER() OVER (
            PARTITION BY o.id_expediente 
            ORDER BY p.fecha_creacion DESC, o.fecha_creacion DESC, o.id DESC
        ) as rn
        
    FROM public.gedo_ifocd_datos o
    INNER JOIN public.gedo_ifpdo_datos p ON o.id_expediente = p.id_expediente
    LEFT JOIN public.vw_expedientes_maestro m ON o.id_expediente = m.id_expediente
    WHERE (m.trata IS NULL OR (m.trata <> 'MDUG1501K' AND m.descripcion_trata NOT ILIKE '%demolicion%'))
)
SELECT *
FROM ranked_rows
WHERE rn = 1
WITH DATA;

-- Índices
CREATE UNIQUE INDEX idx_m2_permisados_id_exp ON public.mvw_m2_permisados (id_expediente);
CREATE INDEX idx_m2_permisados_exp ON public.mvw_m2_permisados (expediente);
CREATE INDEX idx_m2_permisados_smp ON public.mvw_m2_permisados (smp);
CREATE INDEX idx_m2_permisados_prof ON public.mvw_m2_permisados (matricula_profesional);
"""

def main():
    print(f"[*] Conectando a producción para crear la vista materializada...")
    prod_engine = create_engine(DEFAULT_PROD_URL)
    
    try:
        with prod_engine.connect() as conn:
            # Dividir los comandos SQL por punto y coma y ejecutarlos secuencialmente
            # O ejecutar el bloque completo
            print("[*] Ejecutando definición SQL de mvw_m2_permisados...")
            conn.execute(text(SQL_VIEW))
            conn.commit()
            print("[+] Vista materializada y sus índices creados correctamente en producción.")
    except Exception as e:
        print(f"[-] Error al crear la vista en producción: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
