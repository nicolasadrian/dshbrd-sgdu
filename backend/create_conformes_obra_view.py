import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import engine

DEFAULT_PROD_URL = os.getenv("DATABASE_URL_PUBLIC", "postgresql://postgres:frQB7%7D0%26p~.C_.X%40Ymu(1tAO7@34.136.69.128:5432/sade_db")

def build_create_view_sql(has_frentesparcelas: bool = True) -> str:
    fp_cte = """
    fp_ref AS (
        SELECT DISTINCT ON (lower(regexp_replace(smp, '-0*', '-', 'g')))
            lower(regexp_replace(smp, '-0*', '-', 'g')) AS clean_smp,
            seccion, manzana, parcela,
            (frente || ' ' || num_dom) AS direccion
        FROM public.frentesparcelas
        WHERE smp IS NOT NULL AND smp <> ''
        ORDER BY lower(regexp_replace(smp, '-0*', '-', 'g'))
    ),
    """ if has_frentesparcelas else """
    fp_ref AS (
        SELECT 
            ''::text AS clean_smp, 
            ''::text AS seccion, 
            ''::text AS manzana, 
            ''::text AS parcela, 
            ''::text AS direccion 
        WHERE false
    ),
    """

    return f"""
DROP MATERIALIZED VIEW IF EXISTS public.mvw_conformes_obra CASCADE;

CREATE MATERIALIZED VIEW public.mvw_conformes_obra AS
WITH 
ifocd_ref AS (
    SELECT DISTINCT ON (regexp_replace(expediente, '\\s+', '', 'g'))
        regexp_replace(expediente, '\\s+', '', 'g') AS clean_exp,
        id_expediente,
        ubicacion AS direccion,
        ubicacion_dgbarrio AS barrio,
        ubicacion_dgcomuna AS comuna,
        ubicacion_dgseccion AS seccion,
        ubicacion_dgmanzana AS manzana,
        ubicacion_dgparcela AS parcela,
        x, y,
        COALESCE(NULLIF(apellido_profesional, ''), '') AS apellido_profesional,
        COALESCE(NULLIF(nombre_profesional, ''), '') AS nombre_profesional,
        COALESCE(NULLIF(matricula_profesional, ''), '') AS matricula_profesional,
        sup_terreno,
        sup_existente,
        (COALESCE(sup_construir, 0) + COALESCE(sup_modificar, 0) + COALESCE(sup_ampliar, 0)) AS sup_total_permiso
    FROM public.gedo_ifocd_datos
    WHERE (ubicacion IS NOT NULL AND ubicacion <> '') OR (apellido_profesional IS NOT NULL AND apellido_profesional <> '')
    ORDER BY regexp_replace(expediente, '\\s+', '', 'g'), fecha_creacion DESC NULLS LAST
),
ifpdo_ref AS (
    SELECT DISTINCT ON (regexp_replace(expediente, '\\s+', '', 'g'))
        regexp_replace(expediente, '\\s+', '', 'g') AS clean_exp,
        id_expediente,
        ubicacion AS direccion,
        ubicacion_dgbarrio AS barrio,
        ubicacion_dgcomuna AS comuna,
        ubicacion_dgseccion AS seccion,
        ubicacion_dgmanzana AS manzana,
        ubicacion_dgparcela AS parcela,
        x, y,
        COALESCE(NULLIF(nombre_apellido, ''), NULLIF(nombre_apellido_r1, ''), NULLIF(nombre_apellido_r2, ''), '') AS profesional,
        COALESCE(NULLIF(matricula, ''), NULLIF(matricula_r1, ''), NULLIF(matricula_r2, ''), '') AS matricula_profesional,
        sup_terreno,
        sup_existente
    FROM public.gedo_ifpdo_datos
    WHERE (ubicacion IS NOT NULL AND ubicacion <> '') OR (nombre_apellido IS NOT NULL AND nombre_apellido <> '')
    ORDER BY regexp_replace(expediente, '\\s+', '', 'g'), fecha_creacion DESC NULLS LAST
),
fipar_ref AS (
    SELECT DISTINCT ON (regexp_replace(expediente, '\\s+', '', 'g'))
        regexp_replace(expediente, '\\s+', '', 'g') AS clean_exp,
        id_expediente,
        dom_caba_calle AS direccion,
        dom_caba_calle_barrio AS barrio,
        dom_caba_calle_comuna AS comuna,
        dom_caba_calle_seccion AS seccion,
        dom_caba_calle_manzana AS manzana,
        dom_caba_calle_parcela AS parcela,
        x, y
    FROM public.gedo_fipar_datos
    WHERE dom_caba_calle IS NOT NULL AND dom_caba_calle <> ''
    ORDER BY regexp_replace(expediente, '\\s+', '', 'g'), fecha_creacion DESC NULLS LAST
),
m2_ref AS (
    SELECT DISTINCT ON (regexp_replace(expediente, '\\s+', '', 'g'))
        regexp_replace(expediente, '\\s+', '', 'g') AS clean_exp,
        direccion, barrio, comuna, seccion, manzana, parcela, smp, x, y,
        apellido_profesional, nombre_profesional, matricula_profesional,
        sup_terreno, sup_existente,
        (COALESCE(sup_construir, 0) + COALESCE(sup_modificar, 0) + COALESCE(sup_ampliar, 0)) AS sup_total_permiso
    FROM public.mvw_m2_permisados
    WHERE direccion IS NOT NULL AND direccion <> ''
    ORDER BY regexp_replace(expediente, '\\s+', '', 'g'), fecha_creacion_pdo DESC NULLS LAST
),
smp_geo_ref AS (
    SELECT DISTINCT ON (clean_smp)
        clean_smp,
        barrio,
        comuna,
        x,
        y,
        direccion
    FROM (
        SELECT 
            lower(regexp_replace(smp, '-0*', '-', 'g')) AS clean_smp,
            barrio, comuna, x, y, direccion
        FROM public.mvw_m2_permisados
        WHERE smp IS NOT NULL AND smp <> '' AND barrio IS NOT NULL AND barrio <> ''
        UNION ALL
        SELECT 
            lower(regexp_replace(COALESCE(ubicacion_dgseccion, '') || '-' || COALESCE(ubicacion_dgmanzana, '') || '-' || COALESCE(ubicacion_dgparcela, ''), '-0*', '-', 'g')) AS clean_smp,
            ubicacion_dgbarrio AS barrio,
            ubicacion_dgcomuna AS comuna,
            x, y, ubicacion AS direccion
        FROM public.gedo_ifpdo_datos
        WHERE ubicacion_dgseccion IS NOT NULL AND ubicacion_dgbarrio IS NOT NULL AND ubicacion_dgbarrio <> ''
        UNION ALL
        SELECT 
            lower(regexp_replace(dom_caba_calle_seccion || '-' || dom_caba_calle_manzana || '-' || dom_caba_calle_parcela, '-0*', '-', 'g')) AS clean_smp,
            dom_caba_calle_barrio AS barrio,
            dom_caba_calle_comuna AS comuna,
            x, y, dom_caba_calle AS direccion
        FROM public.gedo_fipar_datos
        WHERE dom_caba_calle_seccion IS NOT NULL AND dom_caba_calle_barrio IS NOT NULL AND dom_caba_calle_barrio <> ''
    ) u
    WHERE clean_smp IS NOT NULL AND clean_smp <> '--'
    ORDER BY clean_smp, x IS NOT NULL DESC
),
seccion_geo_ref AS (
    SELECT DISTINCT ON (clean_sec)
        clean_sec,
        barrio,
        comuna
    FROM (
        SELECT 
            regexp_replace(seccion, '^0+', '') AS clean_sec,
            barrio, comuna,
            COUNT(*) OVER (PARTITION BY regexp_replace(seccion, '^0+', ''), barrio, comuna) as cnt
        FROM public.mvw_m2_permisados
        WHERE seccion IS NOT NULL AND seccion <> '' AND barrio IS NOT NULL AND barrio <> ''
        ORDER BY regexp_replace(seccion, '^0+', ''), cnt DESC
    ) s
),
{fp_cte}
ifpco_parsed AS (
    SELECT 
        'IFPCO'::text AS acronimo,
        p.id_expediente::bigint AS id_expediente,
        p.expediente::text AS expediente,
        p.documento::text AS documento,
        p.fecha_creacion::timestamp AS fecha_creacion,
        COALESCE(
            NULLIF(p.ubicacion_dgbarrio, ''),
            NULLIF(p.ubicacion_barrio, ''),
            NULLIF(p.ubicacion_dgbarrio_r1, ''),
            NULLIF(m2.barrio, ''),
            NULLIF(ocd.barrio, ''),
            NULLIF(pdo.barrio, ''),
            NULLIF(fip.barrio, ''),
            NULLIF(geo.barrio, ''),
            NULLIF(sec_geo.barrio, ''),
            ''
        )::text AS barrio,
        COALESCE(
            NULLIF(p.ubicacion_dgcomuna, ''),
            NULLIF(p.ubicacion_comuna, ''),
            NULLIF(p.ubicacion_dgcomuna_r1, ''),
            NULLIF(m2.comuna, ''),
            NULLIF(ocd.comuna, ''),
            NULLIF(pdo.comuna, ''),
            NULLIF(fip.comuna, ''),
            NULLIF(geo.comuna, ''),
            NULLIF(sec_geo.comuna, ''),
            ''
        )::text AS comuna,
        COALESCE(
            NULLIF(p.ubicacion_dgseccion, ''),
            NULLIF(p.ubicacion_seccion, ''),
            NULLIF(p.ubicacion_dgseccion_r1, ''),
            NULLIF(m2.seccion, ''),
            NULLIF(ocd.seccion, ''),
            NULLIF(pdo.seccion, ''),
            NULLIF(fip.seccion, ''),
            NULLIF(fp.seccion, ''),
            split_part(substring(p.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 1),
            ''
        )::text AS seccion,
        COALESCE(
            NULLIF(p.ubicacion_dgmanzana, ''),
            NULLIF(p.ubicacion_manzana, ''),
            NULLIF(p.ubicacion_dgmanzana_r1, ''),
            NULLIF(m2.manzana, ''),
            NULLIF(ocd.manzana, ''),
            NULLIF(pdo.manzana, ''),
            NULLIF(fip.manzana, ''),
            NULLIF(fp.manzana, ''),
            split_part(substring(p.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 2),
            ''
        )::text AS manzana,
        COALESCE(
            NULLIF(p.ubicacion_dgparcela, ''),
            NULLIF(p.ubicacion_parcela, ''),
            NULLIF(p.ubicacion_dgparcela_r1, ''),
            NULLIF(m2.parcela, ''),
            NULLIF(ocd.parcela, ''),
            NULLIF(pdo.parcela, ''),
            NULLIF(fip.parcela, ''),
            NULLIF(fp.parcela, ''),
            split_part(substring(p.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 3),
            ''
        )::text AS parcela,
        COALESCE(
            NULLIF(p.ubicacion, ''),
            NULLIF(p.ubicacion_r1, ''),
            NULLIF(m2.direccion, ''),
            NULLIF(ocd.direccion, ''),
            NULLIF(pdo.direccion, ''),
            NULLIF(fip.direccion, ''),
            NULLIF(geo.direccion, ''),
            NULLIF(fp.direccion, ''),
            ''
        )::text AS direccion,
        COALESCE(p.x, m2.x, ocd.x, pdo.x, fip.x, geo.x)::double precision AS x,
        COALESCE(p.y, m2.y, ocd.y, pdo.y, fip.y, geo.y)::double precision AS y,
        COALESCE(NULLIF(p.tipo_obra, ''), 'Conforme de Obra')::text AS tipo_obra,
        COALESCE(NULLIF(p.tipo_tarea, ''), 'Conforme Total')::text AS tipo_tarea,
        COALESCE(p.codigo_edificacion, '')::text AS codigo_edificacion,
        COALESCE(
            NULLIF(p.apellido, ''),
            NULLIF(p.apellido_r1, ''),
            NULLIF(p.apellido_r2, ''),
            NULLIF(p.apellido_r3, ''),
            NULLIF(p.apellido_r4, ''),
            NULLIF(p.apellido_r5, ''),
            NULLIF(m2.apellido_profesional, ''),
            NULLIF(ocd.apellido_profesional, ''),
            NULLIF(pdo.profesional, ''),
            ''
        )::text AS apellido_profesional,
        COALESCE(
            NULLIF(p.nombre, ''),
            NULLIF(p.nombre_r1, ''),
            NULLIF(p.nombre_r2, ''),
            NULLIF(p.nombre_r3, ''),
            NULLIF(p.nombre_r4, ''),
            NULLIF(p.nombre_r5, ''),
            NULLIF(m2.nombre_profesional, ''),
            NULLIF(ocd.nombre_profesional, ''),
            ''
        )::text AS nombre_profesional,
        COALESCE(
            NULLIF(p.matricula, ''),
            NULLIF(p.matricula_r1, ''),
            NULLIF(p.matricula_r2, ''),
            NULLIF(p.matricula_r3, ''),
            NULLIF(p.matricula_r4, ''),
            NULLIF(p.matricula_r5, ''),
            NULLIF(m2.matricula_profesional, ''),
            NULLIF(ocd.matricula_profesional, ''),
            NULLIF(pdo.matricula_profesional, ''),
            ''
        )::text AS matricula_profesional,
        COALESCE(p.sup_terreno, m2.sup_terreno, ocd.sup_terreno, pdo.sup_terreno, 0)::double precision AS sup_terreno,
        COALESCE(p.sup_existente, m2.sup_existente, ocd.sup_existente, pdo.sup_existente, 0)::double precision AS sup_existente,
        (
            COALESCE(p.construida, 0) + 
            COALESCE(p.sup_contrav_reg, 0) + 
            COALESCE(p.reglamentaria, 0) + 
            COALESCE(p.modif_sup_reglam, 0) + 
            COALESCE(p.supe_contra_reglamen_cur, 0)
        )::double precision AS sup_construida,
        (
            COALESCE(p.modificada, 0) + 
            COALESCE(p.sup_contrav_antirr, 0) + 
            COALESCE(p.antireglamentaria, 0) + 
            COALESCE(p.modif_sup_antirr, 0) + 
            COALESCE(p.super_ampliada_contravencion, 0) + 
            COALESCE(p.supe_contra_no_reglam_cur, 0) + 
            COALESCE(p.supe_contra_no_reglam_cpu, 0)
        )::double precision AS sup_modificada,
        COALESCE(p.sup_permiso_previo, m2.sup_total_permiso, ocd.sup_total_permiso, 0)::double precision AS sup_permiso_previo,
        (
            CASE 
                WHEN (
                    COALESCE(p.construida, 0) + 
                    COALESCE(p.modificada, 0) + 
                    COALESCE(p.sup_contrav_reg, 0) + 
                    COALESCE(p.sup_contrav_antirr, 0) + 
                    COALESCE(p.reglamentaria, 0) + 
                    COALESCE(p.antireglamentaria, 0) + 
                    COALESCE(p.modif_sup_reglam, 0) + 
                    COALESCE(p.modif_sup_antirr, 0) + 
                    COALESCE(p.super_ampliada_contravencion, 0) + 
                    COALESCE(p.supe_contra_reglamen_cur, 0) + 
                    COALESCE(p.supe_contra_no_reglam_cur, 0) + 
                    COALESCE(p.supe_contra_no_reglam_cpu, 0)
                ) > 0 THEN (
                    COALESCE(p.construida, 0) + 
                    COALESCE(p.modificada, 0) + 
                    COALESCE(p.sup_contrav_reg, 0) + 
                    COALESCE(p.sup_contrav_antirr, 0) + 
                    COALESCE(p.reglamentaria, 0) + 
                    COALESCE(p.antireglamentaria, 0) + 
                    COALESCE(p.modif_sup_reglam, 0) + 
                    COALESCE(p.modif_sup_antirr, 0) + 
                    COALESCE(p.super_ampliada_contravencion, 0) + 
                    COALESCE(p.supe_contra_reglamen_cur, 0) + 
                    COALESCE(p.supe_contra_no_reglam_cur, 0) + 
                    COALESCE(p.supe_contra_no_reglam_cpu, 0)
                )
                ELSE COALESCE(p.sup_permiso_previo, m2.sup_total_permiso, ocd.sup_total_permiso, 0)
            END
        )::double precision AS sup_total_afectada
    FROM public.gedo_ifpco_datos p
    LEFT JOIN m2_ref m2 ON m2.clean_exp = regexp_replace(p.expediente, '\\s+', '', 'g')
    LEFT JOIN ifocd_ref ocd ON ocd.clean_exp = regexp_replace(p.expediente, '\\s+', '', 'g')
    LEFT JOIN ifpdo_ref pdo ON pdo.clean_exp = regexp_replace(p.expediente, '\\s+', '', 'g')
    LEFT JOIN fipar_ref fip ON fip.clean_exp = regexp_replace(p.expediente, '\\s+', '', 'g')
    LEFT JOIN smp_geo_ref geo ON geo.clean_smp = lower(regexp_replace(
        COALESCE(
            NULLIF(p.ubicacion_dgseccion, ''),
            NULLIF(p.ubicacion_seccion, ''),
            NULLIF(m2.seccion, ''),
            NULLIF(ocd.seccion, ''),
            NULLIF(pdo.seccion, ''),
            NULLIF(fip.seccion, ''),
            split_part(substring(p.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 1)
        ) || '-' ||
        COALESCE(
            NULLIF(p.ubicacion_dgmanzana, ''),
            NULLIF(p.ubicacion_manzana, ''),
            NULLIF(m2.manzana, ''),
            NULLIF(ocd.manzana, ''),
            NULLIF(pdo.manzana, ''),
            NULLIF(fip.manzana, ''),
            split_part(substring(p.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 2)
        ) || '-' ||
        COALESCE(
            NULLIF(p.ubicacion_dgparcela, ''),
            NULLIF(p.ubicacion_parcela, ''),
            NULLIF(m2.parcela, ''),
            NULLIF(ocd.parcela, ''),
            NULLIF(pdo.parcela, ''),
            NULLIF(fip.parcela, ''),
            split_part(substring(p.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 3)
        ), '-0*', '-', 'g'))
    LEFT JOIN seccion_geo_ref sec_geo ON sec_geo.clean_sec = regexp_replace(
        COALESCE(
            NULLIF(p.ubicacion_dgseccion, ''),
            NULLIF(p.ubicacion_seccion, ''),
            NULLIF(m2.seccion, ''),
            NULLIF(ocd.seccion, ''),
            NULLIF(pdo.seccion, ''),
            NULLIF(fip.seccion, ''),
            split_part(substring(p.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 1)
        ), '^0+', '')
    LEFT JOIN fp_ref fp ON fp.clean_smp = lower(regexp_replace(
        COALESCE(
            NULLIF(p.ubicacion_dgseccion, ''),
            NULLIF(p.ubicacion_seccion, ''),
            NULLIF(m2.seccion, ''),
            NULLIF(ocd.seccion, ''),
            NULLIF(pdo.seccion, ''),
            NULLIF(fip.seccion, ''),
            split_part(substring(p.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 1)
        ) || '-' ||
        COALESCE(
            NULLIF(p.ubicacion_dgmanzana, ''),
            NULLIF(p.ubicacion_manzana, ''),
            NULLIF(m2.manzana, ''),
            NULLIF(ocd.manzana, ''),
            NULLIF(pdo.manzana, ''),
            NULLIF(fip.manzana, ''),
            split_part(substring(p.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 2)
        ) || '-' ||
        COALESCE(
            NULLIF(p.ubicacion_dgparcela, ''),
            NULLIF(p.ubicacion_parcela, ''),
            NULLIF(m2.parcela, ''),
            NULLIF(ocd.parcela, ''),
            NULLIF(pdo.parcela, ''),
            NULLIF(fip.parcela, ''),
            split_part(substring(p.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 3)
        ), '-0*', '-', 'g'))
    WHERE p.expediente IS NOT NULL
),
ifroc_parsed AS (
    SELECT 
        'IFROC'::text AS acronimo,
        r.id_expediente::bigint AS id_expediente,
        r.expediente::text AS expediente,
        r.documento::text AS documento,
        r.fecha_creacion::timestamp AS fecha_creacion,
        COALESCE(
            NULLIF(r.calle_altura_dgbarrio, ''),
            NULLIF(r.calle_altura_barrio, ''),
            NULLIF(m2.barrio, ''),
            NULLIF(ocd.barrio, ''),
            NULLIF(pdo.barrio, ''),
            NULLIF(fip.barrio, ''),
            NULLIF(geo.barrio, ''),
            NULLIF(sec_geo.barrio, ''),
            ''
        )::text AS barrio,
        COALESCE(
            NULLIF(r.calle_altura_dgcomuna, ''),
            NULLIF(r.calle_altura_comuna, ''),
            NULLIF(m2.comuna, ''),
            NULLIF(ocd.comuna, ''),
            NULLIF(pdo.comuna, ''),
            NULLIF(fip.comuna, ''),
            NULLIF(geo.comuna, ''),
            NULLIF(sec_geo.comuna, ''),
            ''
        )::text AS comuna,
        COALESCE(
            NULLIF(r.calle_altura_dgseccion, ''),
            NULLIF(r.calle_altura_seccion, ''),
            NULLIF(m2.seccion, ''),
            NULLIF(ocd.seccion, ''),
            NULLIF(pdo.seccion, ''),
            NULLIF(fip.seccion, ''),
            NULLIF(fp.seccion, ''),
            split_part(substring(r.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 1),
            ''
        )::text AS seccion,
        COALESCE(
            NULLIF(r.calle_altura_dgmanzana, ''),
            NULLIF(r.calle_altura_manzana, ''),
            NULLIF(m2.manzana, ''),
            NULLIF(ocd.manzana, ''),
            NULLIF(pdo.manzana, ''),
            NULLIF(fip.manzana, ''),
            NULLIF(fp.manzana, ''),
            split_part(substring(r.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 2),
            ''
        )::text AS manzana,
        COALESCE(
            NULLIF(r.calle_altura_dgparcela, ''),
            NULLIF(r.calle_altura_parcela, ''),
            NULLIF(m2.parcela, ''),
            NULLIF(ocd.parcela, ''),
            NULLIF(pdo.parcela, ''),
            NULLIF(fip.parcela, ''),
            NULLIF(fp.parcela, ''),
            split_part(substring(r.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 3),
            ''
        )::text AS parcela,
        COALESCE(
            NULLIF(r.calle_altura, ''),
            NULLIF(m2.direccion, ''),
            NULLIF(ocd.direccion, ''),
            NULLIF(pdo.direccion, ''),
            NULLIF(fip.direccion, ''),
            NULLIF(geo.direccion, ''),
            NULLIF(fp.direccion, ''),
            ''
        )::text AS direccion,
        COALESCE(r.x, m2.x, ocd.x, pdo.x, fip.x, geo.x)::double precision AS x,
        COALESCE(r.y, m2.y, ocd.y, pdo.y, fip.y, geo.y)::double precision AS y,
        'Registro de Obra en Contravención'::text AS tipo_obra,
        COALESCE(NULLIF(r.corresponde_tramite, ''), 'Registro de Contravención')::text AS tipo_tarea,
        COALESCE(r.codigo_edific, '')::text AS codigo_edificacion,
        COALESCE(
            NULLIF(r.prof_apellido, ''),
            NULLIF(m2.apellido_profesional, ''),
            NULLIF(ocd.apellido_profesional, ''),
            NULLIF(pdo.profesional, ''),
            ''
        )::text AS apellido_profesional,
        COALESCE(
            NULLIF(r.prof_nombre, ''),
            NULLIF(m2.nombre_profesional, ''),
            NULLIF(ocd.nombre_profesional, ''),
            ''
        )::text AS nombre_profesional,
        COALESCE(
            NULLIF(r.prof_matricula, ''),
            NULLIF(m2.matricula_profesional, ''),
            NULLIF(ocd.matricula_profesional, ''),
            NULLIF(pdo.matricula_profesional, ''),
            ''
        )::text AS matricula_profesional,
        COALESCE(r.sup_terreno, m2.sup_terreno, ocd.sup_terreno, pdo.sup_terreno, 0)::double precision AS sup_terreno,
        COALESCE(r.sup_exist, m2.sup_existente, ocd.sup_existente, pdo.sup_existente, 0)::double precision AS sup_existente,
        (
            COALESCE(r.contrav_reg, 0) + 
            COALESCE(r.contrav_antirreg, 0) + 
            COALESCE(r.contrav_reg_cur, 0) + 
            COALESCE(r.contrav_antirreg_cur, 0) + 
            COALESCE(r.contrav_antirreg_cpu, 0)
        )::double precision AS sup_construida,
        COALESCE(r.modif_reg, 0)::double precision AS sup_modificada,
        COALESCE(r.sup_permiso, m2.sup_total_permiso, ocd.sup_total_permiso, 0)::double precision AS sup_permiso_previo,
        (
            CASE 
                WHEN (
                    COALESCE(r.contrav_reg, 0) + 
                    COALESCE(r.contrav_antirreg, 0) + 
                    COALESCE(r.contrav_reg_cur, 0) + 
                    COALESCE(r.contrav_antirreg_cur, 0) + 
                    COALESCE(r.contrav_antirreg_cpu, 0) + 
                    COALESCE(r.modif_reg, 0)
                ) > 0 THEN (
                    COALESCE(r.contrav_reg, 0) + 
                    COALESCE(r.contrav_antirreg, 0) + 
                    COALESCE(r.contrav_reg_cur, 0) + 
                    COALESCE(r.contrav_antirreg_cur, 0) + 
                    COALESCE(r.contrav_antirreg_cpu, 0) + 
                    COALESCE(r.modif_reg, 0)
                )
                ELSE COALESCE(r.sup_permiso, m2.sup_total_permiso, ocd.sup_total_permiso, 0)
            END
        )::double precision AS sup_total_afectada
    FROM public.gedo_ifroc_datos r
    LEFT JOIN m2_ref m2 ON m2.clean_exp = regexp_replace(r.expediente, '\\s+', '', 'g')
    LEFT JOIN ifocd_ref ocd ON ocd.clean_exp = regexp_replace(r.expediente, '\\s+', '', 'g')
    LEFT JOIN ifpdo_ref pdo ON pdo.clean_exp = regexp_replace(r.expediente, '\\s+', '', 'g')
    LEFT JOIN fipar_ref fip ON fip.clean_exp = regexp_replace(r.expediente, '\\s+', '', 'g')
    LEFT JOIN smp_geo_ref geo ON geo.clean_smp = lower(regexp_replace(
        COALESCE(
            NULLIF(r.calle_altura_dgseccion, ''),
            NULLIF(r.calle_altura_seccion, ''),
            NULLIF(m2.seccion, ''),
            NULLIF(ocd.seccion, ''),
            NULLIF(pdo.seccion, ''),
            NULLIF(fip.seccion, ''),
            split_part(substring(r.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 1)
        ) || '-' ||
        COALESCE(
            NULLIF(r.calle_altura_dgmanzana, ''),
            NULLIF(r.calle_altura_manzana, ''),
            NULLIF(m2.manzana, ''),
            NULLIF(ocd.manzana, ''),
            NULLIF(pdo.manzana, ''),
            NULLIF(fip.manzana, ''),
            split_part(substring(r.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 2)
        ) || '-' ||
        COALESCE(
            NULLIF(r.calle_altura_dgparcela, ''),
            NULLIF(r.calle_altura_parcela, ''),
            NULLIF(m2.parcela, ''),
            NULLIF(ocd.parcela, ''),
            NULLIF(pdo.parcela, ''),
            NULLIF(fip.parcela, ''),
            split_part(substring(r.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 3)
        ), '-0*', '-', 'g'))
    LEFT JOIN seccion_geo_ref sec_geo ON sec_geo.clean_sec = regexp_replace(
        COALESCE(
            NULLIF(r.calle_altura_dgseccion, ''),
            NULLIF(r.calle_altura_seccion, ''),
            NULLIF(m2.seccion, ''),
            NULLIF(ocd.seccion, ''),
            NULLIF(pdo.seccion, ''),
            NULLIF(fip.seccion, ''),
            split_part(substring(r.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 1)
        ), '^0+', '')
    LEFT JOIN fp_ref fp ON fp.clean_smp = lower(regexp_replace(
        COALESCE(
            NULLIF(r.calle_altura_dgseccion, ''),
            NULLIF(r.calle_altura_seccion, ''),
            NULLIF(m2.seccion, ''),
            NULLIF(ocd.seccion, ''),
            NULLIF(pdo.seccion, ''),
            NULLIF(fip.seccion, ''),
            split_part(substring(r.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 1)
        ) || '-' ||
        COALESCE(
            NULLIF(r.calle_altura_dgmanzana, ''),
            NULLIF(r.calle_altura_manzana, ''),
            NULLIF(m2.manzana, ''),
            NULLIF(ocd.manzana, ''),
            NULLIF(pdo.manzana, ''),
            NULLIF(fip.manzana, ''),
            split_part(substring(r.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 2)
        ) || '-' ||
        COALESCE(
            NULLIF(r.calle_altura_dgparcela, ''),
            NULLIF(r.calle_altura_parcela, ''),
            NULLIF(m2.parcela, ''),
            NULLIF(ocd.parcela, ''),
            NULLIF(pdo.parcela, ''),
            NULLIF(fip.parcela, ''),
            split_part(substring(r.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 3)
        ), '-0*', '-', 'g'))
    WHERE r.expediente IS NOT NULL
),
ifsmi_parsed AS (
    SELECT 
        'IFSMI'::text AS acronimo,
        s.id_expediente::bigint AS id_expediente,
        s.expediente::text AS expediente,
        s.documento::text AS documento,
        s.fecha_creacion::timestamp AS fecha_creacion,
        COALESCE(
            NULLIF(s.ubicacion_dgbarrio, ''),
            NULLIF(s.ubicacion_barrio, ''),
            NULLIF(m2.barrio, ''),
            NULLIF(ocd.barrio, ''),
            NULLIF(pdo.barrio, ''),
            NULLIF(fip.barrio, ''),
            NULLIF(geo.barrio, ''),
            NULLIF(sec_geo.barrio, ''),
            ''
        )::text AS barrio,
        COALESCE(
            NULLIF(s.ubicacion_dgcomuna, ''),
            NULLIF(s.ubicacion_comuna, ''),
            NULLIF(m2.comuna, ''),
            NULLIF(ocd.comuna, ''),
            NULLIF(pdo.comuna, ''),
            NULLIF(fip.comuna, ''),
            NULLIF(geo.comuna, ''),
            NULLIF(sec_geo.comuna, ''),
            ''
        )::text AS comuna,
        COALESCE(
            NULLIF(s.ubicacion_dgseccion, ''),
            NULLIF(s.ubicacion_seccion, ''),
            NULLIF(m2.seccion, ''),
            NULLIF(ocd.seccion, ''),
            NULLIF(pdo.seccion, ''),
            NULLIF(fip.seccion, ''),
            NULLIF(fp.seccion, ''),
            split_part(substring(s.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 1),
            ''
        )::text AS seccion,
        COALESCE(
            NULLIF(s.ubicacion_dgmanzana, ''),
            NULLIF(s.ubicacion_manzana, ''),
            NULLIF(m2.manzana, ''),
            NULLIF(ocd.manzana, ''),
            NULLIF(pdo.manzana, ''),
            NULLIF(fip.manzana, ''),
            NULLIF(fp.manzana, ''),
            split_part(substring(s.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 2),
            ''
        )::text AS manzana,
        COALESCE(
            NULLIF(s.ubicacion_dgparcela, ''),
            NULLIF(s.ubicacion_parcela, ''),
            NULLIF(m2.parcela, ''),
            NULLIF(ocd.parcela, ''),
            NULLIF(pdo.parcela, ''),
            NULLIF(fip.parcela, ''),
            NULLIF(fp.parcela, ''),
            split_part(substring(s.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 3),
            ''
        )::text AS parcela,
        COALESCE(
            NULLIF(s.ubicacion, ''),
            NULLIF(m2.direccion, ''),
            NULLIF(ocd.direccion, ''),
            NULLIF(pdo.direccion, ''),
            NULLIF(fip.direccion, ''),
            NULLIF(geo.direccion, ''),
            NULLIF(fp.direccion, ''),
            ''
        )::text AS direccion,
        COALESCE(s.x, m2.x, ocd.x, pdo.x, fip.x, geo.x)::double precision AS x,
        COALESCE(s.y, m2.y, ocd.y, pdo.y, fip.y, geo.y)::double precision AS y,
        'Conforme Sin Modificación de Inmueble'::text AS tipo_obra,
        'Sin Modificación'::text AS tipo_tarea,
        COALESCE(s.codigo_edificacion, '')::text AS codigo_edificacion,
        COALESCE(
            NULLIF(s.apellido_profesional, ''),
            NULLIF(s.apellido_profesional_r1, ''),
            NULLIF(s.apellido_profesional_r2, ''),
            NULLIF(s.apellido_profesional_r3, ''),
            NULLIF(m2.apellido_profesional, ''),
            NULLIF(ocd.apellido_profesional, ''),
            NULLIF(pdo.profesional, ''),
            ''
        )::text AS apellido_profesional,
        COALESCE(
            NULLIF(s.nombre_profesional, ''),
            NULLIF(s.nombre_profesional_r1, ''),
            NULLIF(s.nombre_profesional_r2, ''),
            NULLIF(s.nombre_profesional_r3, ''),
            NULLIF(m2.nombre_profesional, ''),
            NULLIF(ocd.nombre_profesional, ''),
            ''
        )::text AS nombre_profesional,
        COALESCE(
            NULLIF(s.matricula_profesional, ''),
            NULLIF(s.matricula_profesional_r1, ''),
            NULLIF(s.matricula_profesional_r2, ''),
            NULLIF(s.matricula_profesional_r3, ''),
            NULLIF(m2.matricula_profesional, ''),
            NULLIF(ocd.matricula_profesional, ''),
            NULLIF(pdo.matricula_profesional, ''),
            ''
        )::text AS matricula_profesional,
        COALESCE(m2.sup_terreno, ocd.sup_terreno, pdo.sup_terreno, 0)::double precision AS sup_terreno,
        COALESCE(m2.sup_existente, ocd.sup_existente, pdo.sup_existente, 0)::double precision AS sup_existente,
        0::double precision AS sup_construida,
        0::double precision AS sup_modificada,
        COALESCE(m2.sup_total_permiso, ocd.sup_total_permiso, 0)::double precision AS sup_permiso_previo,
        COALESCE(s.sup_afectada, m2.sup_total_permiso, ocd.sup_total_permiso, 0)::double precision AS sup_total_afectada
    FROM public.gedo_ifsmi_datos s
    LEFT JOIN m2_ref m2 ON m2.clean_exp = regexp_replace(s.expediente, '\\s+', '', 'g')
    LEFT JOIN ifocd_ref ocd ON ocd.clean_exp = regexp_replace(s.expediente, '\\s+', '', 'g')
    LEFT JOIN ifpdo_ref pdo ON pdo.clean_exp = regexp_replace(s.expediente, '\\s+', '', 'g')
    LEFT JOIN fipar_ref fip ON fip.clean_exp = regexp_replace(s.expediente, '\\s+', '', 'g')
    LEFT JOIN smp_geo_ref geo ON geo.clean_smp = lower(regexp_replace(
        COALESCE(
            NULLIF(s.ubicacion_dgseccion, ''),
            NULLIF(s.ubicacion_seccion, ''),
            NULLIF(m2.seccion, ''),
            NULLIF(ocd.seccion, ''),
            NULLIF(pdo.seccion, ''),
            NULLIF(fip.seccion, ''),
            split_part(substring(s.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 1)
        ) || '-' ||
        COALESCE(
            NULLIF(s.ubicacion_dgmanzana, ''),
            NULLIF(s.ubicacion_manzana, ''),
            NULLIF(m2.manzana, ''),
            NULLIF(ocd.manzana, ''),
            NULLIF(pdo.manzana, ''),
            NULLIF(fip.manzana, ''),
            split_part(substring(s.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 2)
        ) || '-' ||
        COALESCE(
            NULLIF(s.ubicacion_dgparcela, ''),
            NULLIF(s.ubicacion_parcela, ''),
            NULLIF(m2.parcela, ''),
            NULLIF(ocd.parcela, ''),
            NULLIF(pdo.parcela, ''),
            NULLIF(fip.parcela, ''),
            split_part(substring(s.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 3)
        ), '-0*', '-', 'g'))
    LEFT JOIN seccion_geo_ref sec_geo ON sec_geo.clean_sec = regexp_replace(
        COALESCE(
            NULLIF(s.ubicacion_dgseccion, ''),
            NULLIF(s.ubicacion_seccion, ''),
            NULLIF(m2.seccion, ''),
            NULLIF(ocd.seccion, ''),
            NULLIF(pdo.seccion, ''),
            NULLIF(fip.seccion, ''),
            split_part(substring(s.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 1)
        ), '^0+', '')
    LEFT JOIN fp_ref fp ON fp.clean_smp = lower(regexp_replace(
        COALESCE(
            NULLIF(s.ubicacion_dgseccion, ''),
            NULLIF(s.ubicacion_seccion, ''),
            NULLIF(m2.seccion, ''),
            NULLIF(ocd.seccion, ''),
            NULLIF(pdo.seccion, ''),
            NULLIF(fip.seccion, ''),
            split_part(substring(s.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 1)
        ) || '-' ||
        COALESCE(
            NULLIF(s.ubicacion_dgmanzana, ''),
            NULLIF(s.ubicacion_manzana, ''),
            NULLIF(m2.manzana, ''),
            NULLIF(ocd.manzana, ''),
            NULLIF(pdo.manzana, ''),
            NULLIF(fip.manzana, ''),
            split_part(substring(s.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 2)
        ) || '-' ||
        COALESCE(
            NULLIF(s.ubicacion_dgparcela, ''),
            NULLIF(s.ubicacion_parcela, ''),
            NULLIF(m2.parcela, ''),
            NULLIF(ocd.parcela, ''),
            NULLIF(pdo.parcela, ''),
            NULLIF(fip.parcela, ''),
            split_part(substring(s.motivo from '([0-9]{{2,3}}-[0-9]{{3,4}}[a-zA-Z]?-[0-9]{{3,4}}[a-zA-Z]?)'), '-', 3)
        ), '-0*', '-', 'g'))
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
    CASE 
        WHEN NULLIF(seccion, '') IS NOT NULL AND NULLIF(manzana, '') IS NOT NULL AND NULLIF(parcela, '') IS NOT NULL 
        THEN seccion || '-' || manzana || '-' || parcela
        ELSE ''
    END AS smp,
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
CREATE INDEX idx_mvw_conformes_smp ON public.mvw_conformes_obra (smp);
"""

def execute_on_engine(eng, name="LOCAL"):
    print(f"[*] Conectando a {name} para crear mvw_conformes_obra...")
    try:
        with eng.begin() as conn:
            # Check if frentesparcelas exists
            has_fp = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'frentesparcelas'
            """)).scalar() > 0
            
            print(f"[*] Tabla frentesparcelas presente en {name}: {has_fp}")
            sql = build_create_view_sql(has_frentesparcelas=has_fp)
            print(f"[*] Ejecutando SQL DDL para mvw_conformes_obra e índices en {name}...")
            conn.execute(text(sql))
            print(f"[+] Vista materializada mvw_conformes_obra creada exitosamente en {name}!")
    except Exception as e:
        print(f"[-] Error en {name}: {e}")

def main():
    # 1. Local
    execute_on_engine(engine, "LOCAL")
    
    # 2. Prod if available
    try:
        prod_engine = create_engine(DEFAULT_PROD_URL, connect_args={"connect_timeout": 5})
        execute_on_engine(prod_engine, "PROD (Cloud SQL)")
    except Exception as e:
        print(f"[-] No se pudo conectar a PROD: {e}")

if __name__ == "__main__":
    main()
