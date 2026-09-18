import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import engine

SQL_CREATE_VIEW = """
DROP MATERIALIZED VIEW IF EXISTS public.mvw_conformes_obra CASCADE;

CREATE MATERIALIZED VIEW public.mvw_conformes_obra AS
WITH ifpco_parsed AS (
    SELECT 
        'IFPCO'::text AS acronimo,
        p.id_expediente::bigint AS id_expediente,
        p.expediente::text AS expediente,
        p.documento::text AS documento,
        p.fecha_creacion::timestamp AS fecha_creacion,
        COALESCE(p.ubicacion_dgbarrio, p.ubicacion_barrio, '')::text AS barrio,
        COALESCE(p.ubicacion_dgcomuna, p.ubicacion_comuna, '')::text AS comuna,
        COALESCE(p.ubicacion_dgseccion, p.ubicacion_seccion, '')::text AS seccion,
        COALESCE(p.ubicacion_dgmanzana, p.ubicacion_manzana, '')::text AS manzana,
        COALESCE(p.ubicacion_dgparcela, p.ubicacion_parcela, '')::text AS parcela,
        COALESCE(p.ubicacion, '')::text AS direccion,
        p.x::double precision AS x,
        p.y::double precision AS y,
        COALESCE(p.tipo_obra, '')::text AS tipo_obra,
        COALESCE(p.tipo_tarea, '')::text AS tipo_tarea,
        COALESCE(p.codigo_edificacion, '')::text AS codigo_edificacion,
        COALESCE(p.apellido, '')::text AS apellido_profesional,
        COALESCE(p.nombre, '')::text AS nombre_profesional,
        COALESCE(p.matricula, '')::text AS matricula_profesional,
        COALESCE(p.sup_terreno, 0)::double precision AS sup_terreno,
        COALESCE(p.sup_existente, 0)::double precision AS sup_existente,
        COALESCE(p.construida, 0)::double precision AS sup_construida,
        COALESCE(p.modificada, 0)::double precision AS sup_modificada,
        COALESCE(p.sup_permiso_previo, 0)::double precision AS sup_permiso_previo,
        (COALESCE(p.construida, 0) + COALESCE(p.modificada, 0))::double precision AS sup_total_afectada
    FROM public.gedo_ifpco_datos p
    WHERE p.expediente IS NOT NULL
),
ifroc_parsed AS (
    SELECT 
        'IFROC'::text AS acronimo,
        r.id_expediente::bigint AS id_expediente,
        r.expediente::text AS expediente,
        r.documento::text AS documento,
        r.fecha_creacion::timestamp AS fecha_creacion,
        COALESCE(r.calle_altura_dgbarrio, r.calle_altura_barrio, '')::text AS barrio,
        COALESCE(r.calle_altura_dgcomuna, r.calle_altura_comuna, '')::text AS comuna,
        COALESCE(r.calle_altura_dgseccion, r.calle_altura_seccion, '')::text AS seccion,
        COALESCE(r.calle_altura_dgmanzana, r.calle_altura_manzana, '')::text AS manzana,
        COALESCE(r.calle_altura_dgparcela, r.calle_altura_parcela, '')::text AS parcela,
        COALESCE(r.calle_altura, '')::text AS direccion,
        r.x::double precision AS x,
        r.y::double precision AS y,
        'Registro de Obra en Contravención'::text AS tipo_obra,
        COALESCE(r.corresponde_tramite, '')::text AS tipo_tarea,
        COALESCE(r.codigo_edific, '')::text AS codigo_edificacion,
        COALESCE(r.prof_apellido, '')::text AS apellido_profesional,
        COALESCE(r.prof_nombre, '')::text AS nombre_profesional,
        COALESCE(r.prof_matricula, '')::text AS matricula_profesional,
        COALESCE(r.sup_terreno, 0)::double precision AS sup_terreno,
        COALESCE(r.sup_exist, 0)::double precision AS sup_existente,
        (COALESCE(r.contrav_reg, 0) + COALESCE(r.contrav_antirreg, 0))::double precision AS sup_construida,
        COALESCE(r.modif_reg, 0)::double precision AS sup_modificada,
        COALESCE(r.sup_permiso, 0)::double precision AS sup_permiso_previo,
        (COALESCE(r.contrav_reg, 0) + COALESCE(r.contrav_antirreg, 0) + COALESCE(r.modif_reg, 0))::double precision AS sup_total_afectada
    FROM public.gedo_ifroc_datos r
    WHERE r.expediente IS NOT NULL
),
ifsmi_parsed AS (
    SELECT 
        'IFSMI'::text AS acronimo,
        s.id_expediente::bigint AS id_expediente,
        s.expediente::text AS expediente,
        s.documento::text AS documento,
        s.fecha_creacion::timestamp AS fecha_creacion,
        COALESCE(s.ubicacion_dgbarrio, s.ubicacion_barrio, '')::text AS barrio,
        COALESCE(s.ubicacion_dgcomuna, s.ubicacion_comuna, '')::text AS comuna,
        COALESCE(s.ubicacion_dgseccion, s.ubicacion_seccion, '')::text AS seccion,
        COALESCE(s.ubicacion_dgmanzana, s.ubicacion_manzana, '')::text AS manzana,
        COALESCE(s.ubicacion_dgparcela, s.ubicacion_parcela, '')::text AS parcela,
        COALESCE(s.ubicacion, '')::text AS direccion,
        s.x::double precision AS x,
        s.y::double precision AS y,
        'Conforme Sin Modificación de Inmueble'::text AS tipo_obra,
        'Sin Modificación'::text AS tipo_tarea,
        COALESCE(s.codigo_edificacion, '')::text AS codigo_edificacion,
        COALESCE(s.apellido_profesional, '')::text AS apellido_profesional,
        COALESCE(s.nombre_profesional, '')::text AS nombre_profesional,
        COALESCE(s.matricula_profesional, '')::text AS matricula_profesional,
        0::double precision AS sup_terreno,
        0::double precision AS sup_existente,
        0::double precision AS sup_construida,
        0::double precision AS sup_modificada,
        0::double precision AS sup_permiso_previo,
        COALESCE(s.sup_afectada, 0)::double precision AS sup_total_afectada
    FROM public.gedo_ifsmi_datos s
    WHERE s.expediente IS NOT NULL
),
combined AS (
    SELECT * FROM ifpco_parsed
    UNION ALL
    SELECT * FROM ifroc_parsed
    UNION ALL
    SELECT * FROM ifsmi_parsed
),
ranked AS (
    SELECT 
        c.*,
        ROW_NUMBER() OVER (
            PARTITION BY c.acronimo, c.id_expediente, c.documento
            ORDER BY c.fecha_creacion DESC
        ) as rn
    FROM combined c
)
SELECT 
    acronimo,
    id_expediente,
    expediente,
    documento,
    fecha_creacion,
    barrio,
    comuna,
    seccion,
    manzana,
    parcela,
    COALESCE(seccion, '') || '-' || COALESCE(manzana, '') || '-' || COALESCE(parcela, '') AS smp,
    direccion,
    x,
    y,
    tipo_obra,
    tipo_tarea,
    codigo_edificacion,
    apellido_profesional,
    nombre_profesional,
    matricula_profesional,
    sup_terreno,
    sup_existente,
    sup_construida,
    sup_modificada,
    sup_permiso_previo,
    sup_total_afectada
FROM ranked
WHERE rn = 1
WITH DATA;

CREATE INDEX idx_mvw_conformes_acronimo ON public.mvw_conformes_obra (acronimo);
CREATE INDEX idx_mvw_conformes_expediente ON public.mvw_conformes_obra (expediente);
CREATE INDEX idx_mvw_conformes_fecha ON public.mvw_conformes_obra (fecha_creacion);
CREATE INDEX idx_mvw_conformes_comuna ON public.mvw_conformes_obra (comuna);
CREATE INDEX idx_mvw_conformes_barrio ON public.mvw_conformes_obra (barrio);
"""

def main():
    print("[*] Conectando a la base de datos para crear mvw_conformes_obra...")
    try:
        with engine.begin() as conn:
            print("[*] Ejecutando SQL DDL para mvw_conformes_obra e índices...")
            conn.execute(text(SQL_CREATE_VIEW))
            print("[+] Vista materializada mvw_conformes_obra creada exitosamente!")
    except Exception as e:
        print(f"[-] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
