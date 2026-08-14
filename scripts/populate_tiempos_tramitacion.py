import sys, time
sys.path.insert(0, './backend')
sys.path.insert(0, '.')
from database import engine
from sqlalchemy import text
from config import TRAMITES_CONFIG

g_list = list(TRAMITES_CONFIG.keys())

def populate():
    t0 = time.time()
    with engine.connect() as conn:
        print("=== RE-CREATING planificacion_tiempos_tramitacion_resumen TABLE ===")
        conn.execute(text("DROP TABLE IF EXISTS planificacion_tiempos_tramitacion_resumen CASCADE;"))
        conn.execute(text("""
            CREATE TABLE planificacion_tiempos_tramitacion_resumen (
                gerencia VARCHAR(50),
                trata VARCHAR(50),
                descripcion_trata VARCHAR(255),
                dias_propio_sector NUMERIC(10, 1),
                dias_subsanacion NUMERIC(10, 1),
                dias_intervenciones NUMERIC(10, 1),
                dias_totales NUMERIC(10, 1),
                dias_mediana_ingresados_este_ano NUMERIC(10, 1),
                ultimo_mes_cerrado VARCHAR(20)
            );
        """))
        conn.commit()

        conn.execute(text("TRUNCATE TABLE planificacion_tiempos_trata_historico;"))
        conn.commit()

        for g in g_list:
            t_g0 = time.time()
            print(f"Populating median processing times matching SLA for gerencia '{g}'...")
            try:
                # 1. Monthly historical population matching exact SLA logic per month using MEDIANS
                sql_hist_insert = f"""
                    INSERT INTO planificacion_tiempos_trata_historico (gerencia, trata, mes_label, dias_propio_sector, dias_subsanacion, dias_intervenciones)
                    WITH official_tratas AS (
                        SELECT trata_reporte
                        FROM cfg_gestion_metas
                        WHERE gerencia = '{g}' AND trata_reporte <> 'INTERVENCIONES'
                    ),
                    cfg AS (
                        SELECT analistas_oficiales, buzones_ingreso
                        FROM cfg_gestion_metas
                        WHERE gerencia = '{g}' AND trata_reporte = 'INTERVENCIONES'
                    ),
                    expedientes_egreso AS (
                        SELECT 
                            ee.id_expediente,
                            ee.trata,
                            to_char(ee.fecha_egreso, 'YYYY-MM') as mes_label,
                            ee.fecha_primer_ingreso_gerencia,
                            ee.fecha_egreso,
                            (EXTRACT(epoch FROM (ee.fecha_egreso - ee.fecha_primer_ingreso_gerencia)) / 86400.0) AS duracion_total
                        FROM mv_{g}_egresos_efectivos ee
                        JOIN official_tratas ot ON ot.trata_reporte = ee.trata
                        WHERE ee.fecha_egreso >= '2024-01-01' AND ee.fecha_egreso < DATE_TRUNC('month', CURRENT_DATE)
                    ),
                    pases_cronologicos AS (
                        SELECT 
                            e.id_expediente,
                            e.trata,
                            e.mes_label,
                            p.fecha AS fecha_inicio_tramo,
                            CASE
                                WHEN ((p.destinatario = ANY (cfg.analistas_oficiales)) OR (p.destinatario = ANY (cfg.buzones_ingreso))) THEN 'ADENTRO'
                                ELSE 'AFUERA'
                            END AS ubicacion_destino,
                            COALESCE(LEAD(p.fecha) OVER (PARTITION BY e.id_expediente ORDER BY p.fecha), e.fecha_egreso) AS fecha_fin_tramo
                        FROM expedientes_egreso e
                        CROSS JOIN cfg
                        JOIN mvw_ee_pases_secgdu p ON p.id_expediente = e.id_expediente
                        WHERE p.fecha >= e.fecha_primer_ingreso_gerencia AND p.fecha <= e.fecha_egreso
                    ),
                    tramos_resumidos AS (
                        SELECT 
                            pc.id_expediente,
                            SUM(CASE WHEN pc.ubicacion_destino = 'AFUERA' THEN (EXTRACT(epoch FROM (pc.fecha_fin_tramo - pc.fecha_inicio_tramo)) / 86400.0) ELSE 0.0 END) AS dias_en_otras_areas,
                            SUM(CASE WHEN pc.ubicacion_destino = 'ADENTRO' THEN (EXTRACT(epoch FROM (pc.fecha_fin_tramo - pc.fecha_inicio_tramo)) / 86400.0) ELSE 0.0 END) AS dias_adentro_bruto
                        FROM pases_cronologicos pc
                        GROUP BY pc.id_expediente
                    ),
                    subsanaciones_globales AS (
                        SELECT 
                            e.id_expediente,
                            SUM((EXTRACT(epoch FROM (a.fecha_cierre - a.fecha_alta)) / 86400.0)) AS duracion_subsanaciones
                        FROM expedientes_egreso e
                        JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = e.id_expediente
                        WHERE a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                          AND a.estado = 'CERRADA'
                          AND a.fecha_alta >= e.fecha_primer_ingreso_gerencia AND a.fecha_alta <= e.fecha_egreso
                        GROUP BY e.id_expediente
                    ),
                    pases_internos AS (
                        SELECT 
                            pc.id_expediente,
                            SUM((EXTRACT(epoch FROM (LEAST(a.fecha_cierre, pc.fecha_fin_tramo) - GREATEST(a.fecha_alta, pc.fecha_inicio_tramo))) / 86400.0)) AS duracion_subsanaciones_adentro
                        FROM pases_cronologicos pc
                        JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = pc.id_expediente
                        WHERE pc.ubicacion_destino = 'ADENTRO'
                          AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                          AND a.estado = 'CERRADA'
                          AND a.fecha_alta < pc.fecha_fin_tramo AND a.fecha_cierre > pc.fecha_inicio_tramo
                        GROUP BY pc.id_expediente
                    ),
                    tiempos_unificados AS (
                        SELECT 
                            e.trata,
                            e.mes_label,
                            e.id_expediente,
                            (COALESCE(t.dias_adentro_bruto, e.duracion_total) - COALESCE(sa.duracion_subsanaciones_adentro, 0.0)) AS duracion_neta,
                            COALESCE(s.duracion_subsanaciones, 0.0) AS duracion_sub,
                            COALESCE(t.dias_en_otras_areas, 0.0) AS duracion_int
                        FROM expedientes_egreso e
                        LEFT JOIN tramos_resumidos t ON t.id_expediente = e.id_expediente
                        LEFT JOIN subsanaciones_globales s ON s.id_expediente = e.id_expediente
                        LEFT JOIN pases_internos sa ON sa.id_expediente = e.id_expediente
                    )
                    SELECT 
                        '{g}' as gerencia,
                        tu.trata,
                        tu.mes_label,
                        ROUND(COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY tu.duracion_neta), 0.0)::numeric, 1) as dias_propio_sector,
                        ROUND(COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY tu.duracion_sub), 0.0)::numeric, 1) as dias_subsanacion,
                        ROUND(COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY tu.duracion_int), 0.0)::numeric, 1) as dias_intervenciones
                    FROM tiempos_unificados tu
                    GROUP BY tu.trata, tu.mes_label;
                """
                conn.execute(text(sql_hist_insert))

                # 2. Resumen con Mediana del último mes cerrado y Mediana de trámites ingresados este año
                sql_resumen_insert = f"""
                    INSERT INTO planificacion_tiempos_tramitacion_resumen (
                        gerencia, trata, descripcion_trata, 
                        dias_propio_sector, dias_subsanacion, dias_intervenciones, dias_totales,
                        dias_mediana_ingresados_este_ano, ultimo_mes_cerrado
                    )
                    WITH official_tratas AS (
                        SELECT trata_reporte, descripcion_trata
                        FROM cfg_gestion_metas
                        WHERE gerencia = '{g}' AND trata_reporte <> 'INTERVENCIONES'
                    ),
                    cfg AS (
                        SELECT analistas_oficiales, buzones_ingreso
                        FROM cfg_gestion_metas
                        WHERE gerencia = '{g}' AND trata_reporte = 'INTERVENCIONES'
                    ),
                    expedientes_egreso AS (
                        SELECT 
                            ee.id_expediente,
                            ee.trata,
                            to_char(ee.fecha_egreso, 'YYYY-MM') as mes_label,
                            ee.fecha_primer_ingreso_gerencia,
                            ee.fecha_egreso,
                            EXTRACT(YEAR FROM ee.fecha_primer_ingreso_gerencia)::integer as anio_ingreso,
                            (EXTRACT(epoch FROM (ee.fecha_egreso - ee.fecha_primer_ingreso_gerencia)) / 86400.0) AS duracion_total
                        FROM mv_{g}_egresos_efectivos ee
                        JOIN official_tratas ot ON ot.trata_reporte = ee.trata
                        WHERE ee.fecha_egreso >= '2025-01-01'
                    ),
                    pases_cronologicos AS (
                        SELECT 
                            e.id_expediente,
                            e.trata,
                            e.mes_label,
                            e.anio_ingreso,
                            p.fecha AS fecha_inicio_tramo,
                            CASE
                                WHEN ((p.destinatario = ANY (cfg.analistas_oficiales)) OR (p.destinatario = ANY (cfg.buzones_ingreso))) THEN 'ADENTRO'
                                ELSE 'AFUERA'
                            END AS ubicacion_destino,
                            COALESCE(LEAD(p.fecha) OVER (PARTITION BY e.id_expediente ORDER BY p.fecha), e.fecha_egreso) AS fecha_fin_tramo
                        FROM expedientes_egreso e
                        CROSS JOIN cfg
                        JOIN mvw_ee_pases_secgdu p ON p.id_expediente = e.id_expediente
                        WHERE p.fecha >= e.fecha_primer_ingreso_gerencia AND p.fecha <= e.fecha_egreso
                    ),
                    tramos_resumidos AS (
                        SELECT 
                            pc.id_expediente,
                            SUM(CASE WHEN pc.ubicacion_destino = 'AFUERA' THEN (EXTRACT(epoch FROM (pc.fecha_fin_tramo - pc.fecha_inicio_tramo)) / 86400.0) ELSE 0.0 END) AS dias_en_otras_areas,
                            SUM(CASE WHEN pc.ubicacion_destino = 'ADENTRO' THEN (EXTRACT(epoch FROM (pc.fecha_fin_tramo - pc.fecha_inicio_tramo)) / 86400.0) ELSE 0.0 END) AS dias_adentro_bruto
                        FROM pases_cronologicos pc
                        GROUP BY pc.id_expediente
                    ),
                    subsanaciones_globales AS (
                        SELECT 
                            e.id_expediente,
                            SUM((EXTRACT(epoch FROM (a.fecha_cierre - a.fecha_alta)) / 86400.0)) AS duracion_subsanaciones
                        FROM expedientes_egreso e
                        JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = e.id_expediente
                        WHERE a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                          AND a.estado = 'CERRADA'
                          AND a.fecha_alta >= e.fecha_primer_ingreso_gerencia AND a.fecha_alta <= e.fecha_egreso
                        GROUP BY e.id_expediente
                    ),
                    pases_internos AS (
                        SELECT 
                            pc.id_expediente,
                            SUM((EXTRACT(epoch FROM (LEAST(a.fecha_cierre, pc.fecha_fin_tramo) - GREATEST(a.fecha_alta, pc.fecha_inicio_tramo))) / 86400.0)) AS duracion_subsanaciones_adentro
                        FROM pases_cronologicos pc
                        JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = pc.id_expediente
                        WHERE pc.ubicacion_destino = 'ADENTRO'
                          AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                          AND a.estado = 'CERRADA'
                          AND a.fecha_alta < pc.fecha_fin_tramo AND a.fecha_cierre > pc.fecha_inicio_tramo
                        GROUP BY pc.id_expediente
                    ),
                    tiempos_unificados AS (
                        SELECT 
                            e.trata,
                            e.mes_label,
                            e.anio_ingreso,
                            e.duracion_total,
                            (COALESCE(t.dias_adentro_bruto, e.duracion_total) - COALESCE(sa.duracion_subsanaciones_adentro, 0.0)) AS duracion_neta,
                            COALESCE(s.duracion_subsanaciones, 0.0) AS duracion_sub,
                            COALESCE(t.dias_en_otras_areas, 0.0) AS duracion_int
                        FROM expedientes_egreso e
                        LEFT JOIN tramos_resumidos t ON t.id_expediente = e.id_expediente
                        LEFT JOIN subsanaciones_globales s ON s.id_expediente = e.id_expediente
                        LEFT JOIN pases_internos sa ON sa.id_expediente = e.id_expediente
                    ),
                    latest_trata_month AS (
                        SELECT 
                            trata,
                            MAX(mes_label) as max_mes
                        FROM tiempos_unificados
                        WHERE mes_label < to_char(CURRENT_DATE, 'YYYY-MM')
                        GROUP BY trata
                    ),
                    med_ultimo_mes AS (
                        SELECT 
                            tu.trata,
                            ROUND(COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY tu.duracion_neta), 0.0)::numeric, 1) as dias_propio_sector,
                            ROUND(COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY tu.duracion_sub), 0.0)::numeric, 1) as dias_subsanacion,
                            ROUND(COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY tu.duracion_int), 0.0)::numeric, 1) as dias_intervenciones,
                            ROUND(COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY tu.duracion_total), 0.0)::numeric, 1) as dias_totales,
                            ltm.max_mes as ultimo_mes_cerrado
                        FROM tiempos_unificados tu
                        JOIN latest_trata_month ltm ON ltm.trata = tu.trata AND ltm.max_mes = tu.mes_label
                        GROUP BY tu.trata, ltm.max_mes
                    ),
                    med_ing_2026 AS (
                        SELECT 
                            trata,
                            ROUND(COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duracion_total), 0.0)::numeric, 1) as dias_mediana_ingresados_este_ano
                        FROM tiempos_unificados
                        WHERE anio_ingreso = EXTRACT(YEAR FROM CURRENT_DATE)::integer
                        GROUP BY trata
                    )
                    SELECT 
                        '{g}' as gerencia,
                        ot.trata_reporte as trata,
                        ot.descripcion_trata,
                        COALESCE(m.dias_propio_sector, 0.0) as dias_propio_sector,
                        COALESCE(m.dias_subsanacion, 0.0) as dias_subsanacion,
                        COALESCE(m.dias_intervenciones, 0.0) as dias_intervenciones,
                        COALESCE(m.dias_totales, 0.0) as dias_totales,
                        COALESCE(i.dias_mediana_ingresados_este_ano, 0.0) as dias_mediana_ingresados_este_ano,
                        COALESCE(m.ultimo_mes_cerrado, to_char(CURRENT_DATE - INTERVAL '1 month', 'YYYY-MM')) as ultimo_mes_cerrado
                    FROM official_tratas ot
                    LEFT JOIN med_ultimo_mes m ON m.trata = ot.trata_reporte
                    LEFT JOIN med_ing_2026 i ON i.trata = ot.trata_reporte;
                """
                conn.execute(text(sql_resumen_insert))
                conn.commit()
                print(f"  Gerencia '{g}' median SLAs populated in {round(time.time() - t_g0, 2)}s.")

            except Exception as e:
                print(f"  Error populating gerencia '{g}': {e}")
                conn.rollback()

    print(f"All processing times using MEDIANS populated in {round(time.time() - t0, 2)}s!")

if __name__ == '__main__':
    populate()
