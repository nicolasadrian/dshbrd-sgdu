import sys, time, os
sys.path.insert(0, './backend')
sys.path.insert(0, '.')
from sqlalchemy import create_engine, text
from config import TRAMITES_CONFIG
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL_LOCAL") or os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_PUBLIC") or "postgresql://postgres:lenovo@localhost:5432/sade_db"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, connect_args={"options": "-c statement_timeout=0"})

g_list = list(TRAMITES_CONFIG.keys())

def populate():
    t0 = time.time()
    with engine.connect() as conn:
        conn.execute(text("SET statement_timeout = 0;"))
        print("=== RE-CREATING planificacion_tiempos_tramitacion_resumen TABLE ===")
        conn.execute(text("DROP TABLE IF EXISTS planificacion_tiempos_tramitacion_resumen CASCADE;"))
        conn.execute(text("""
            CREATE TABLE planificacion_tiempos_tramitacion_resumen (
                gerencia VARCHAR(50),
                trata VARCHAR(50),
                descripcion_trata VARCHAR(255),
                -- Métricas Último Mes Completo Cerrado
                dias_propio_sector NUMERIC(10, 1),
                dias_subsanacion NUMERIC(10, 1),
                dias_intervenciones NUMERIC(10, 1),
                dias_totales NUMERIC(10, 1),
                total_resueltos_ultimo_mes INT,
                -- Métricas Expedientes Ingresados en el Año en Curso (resueltos en último mes cerrado)
                dias_propio_sector_este_ano NUMERIC(10, 1),
                dias_subsanacion_este_ano NUMERIC(10, 1),
                dias_intervenciones_este_ano NUMERIC(10, 1),
                dias_totales_este_ano NUMERIC(10, 1),
                dias_mediana_ingresados_este_ano NUMERIC(10, 1),
                total_resueltos_este_ano INT,
                ultimo_mes_cerrado VARCHAR(20)
            );
        """))
        conn.commit()

        conn.execute(text("TRUNCATE TABLE planificacion_tiempos_trata_historico;"))
        conn.commit()

        for g in g_list:
            t_g0 = time.time()
            print(f"Populating processing times matching SLA for gerencia '{g}'...")
            try:
                conn.execute(text("SET statement_timeout = 0;"))
                # 1. Monthly historical population matching exact SLA logic per month using AVERAGES
                sql_hist_insert = f"""
                    INSERT INTO planificacion_tiempos_trata_historico (gerencia, trata, mes_label, dias_propio_sector, dias_subsanacion, dias_intervenciones)
                    WITH official_tratas AS (
                        SELECT DISTINCT trata_reporte
                        FROM cfg_gestion_metas
                        WHERE gerencia = '{g}' AND trata_reporte <> 'INTERVENCIONES'
                    ),
                    cfg AS (
                        SELECT analistas_oficiales, buzones_ingreso
                        FROM cfg_gestion_metas
                        WHERE gerencia = '{g}' AND trata_reporte = 'INTERVENCIONES'
                        LIMIT 1
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
                    sol_sub AS (
                        SELECT 
                            id_expediente, 
                            fecha_alta as fecha_solicitud,
                            LEAD(fecha_alta) OVER (PARTITION BY id_expediente ORDER BY fecha_alta ASC) as next_solicitud
                        FROM mvw_ee_actividades_secgdu
                        WHERE nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                    ),
                    ciclos_sub AS (
                        SELECT 
                            s.id_expediente,
                            s.fecha_solicitud,
                            COALESCE(
                                (SELECT MIN(r.fecha_alta) 
                                 FROM mvw_ee_actividades_secgdu r 
                                 WHERE r.id_expediente = s.id_expediente 
                                   AND r.nombre_tipo_actividad = 'SUBSANACION'
                                   AND r.fecha_alta >= s.fecha_solicitud
                                   AND (s.next_solicitud IS NULL OR r.fecha_alta <= s.next_solicitud)
                                ),
                                s.next_solicitud,
                                e.fecha_egreso
                            ) as fecha_fin_sub
                        FROM sol_sub s
                        JOIN expedientes_egreso e ON e.id_expediente = s.id_expediente
                        WHERE s.fecha_solicitud >= e.fecha_primer_ingreso_gerencia AND s.fecha_solicitud <= e.fecha_egreso
                    ),
                    subsanaciones_globales AS (
                        SELECT 
                            cs.id_expediente,
                            SUM(GREATEST(0, (EXTRACT(epoch FROM (cs.fecha_fin_sub - cs.fecha_solicitud)) / 86400.0))) AS duracion_subsanaciones
                        FROM ciclos_sub cs
                        GROUP BY cs.id_expediente
                    ),
                    pases_internos AS (
                        SELECT 
                            pc.id_expediente,
                            SUM(GREATEST(0, (EXTRACT(epoch FROM (LEAST(cs.fecha_fin_sub, pc.fecha_fin_tramo) - GREATEST(cs.fecha_solicitud, pc.fecha_inicio_tramo))) / 86400.0))) AS duracion_subsanaciones_adentro
                        FROM pases_cronologicos pc
                        JOIN ciclos_sub cs ON cs.id_expediente = pc.id_expediente
                        WHERE pc.ubicacion_destino = 'ADENTRO'
                          AND cs.fecha_solicitud < pc.fecha_fin_tramo AND cs.fecha_fin_sub > pc.fecha_inicio_tramo
                        GROUP BY pc.id_expediente
                    ),
                    tiempos_unificados AS (
                        SELECT 
                            e.trata,
                            e.mes_label,
                            e.id_expediente,
                            GREATEST(0.0, (COALESCE(t.dias_adentro_bruto, e.duracion_total) - COALESCE(sa.duracion_subsanaciones_adentro, 0.0))) AS duracion_neta,
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
                        CEIL(COALESCE(AVG(tu.duracion_neta), 0.0)) as dias_propio_sector,
                        CEIL(COALESCE(AVG(tu.duracion_sub), 0.0)) as dias_subsanacion,
                        CEIL(COALESCE(AVG(tu.duracion_int), 0.0)) as dias_intervenciones
                    FROM tiempos_unificados tu
                    GROUP BY tu.trata, tu.mes_label;
                """
                conn.execute(text(sql_hist_insert))

                # 2. Resumen con Promedios del último mes cerrado y Promedios de trámites ingresados este año
                sql_resumen_insert = f"""
                    INSERT INTO planificacion_tiempos_tramitacion_resumen (
                        gerencia, trata, descripcion_trata, 
                        dias_propio_sector, dias_subsanacion, dias_intervenciones, dias_totales,
                        total_resueltos_ultimo_mes,
                        dias_propio_sector_este_ano, dias_subsanacion_este_ano, dias_intervenciones_este_ano, dias_totales_este_ano,
                        dias_mediana_ingresados_este_ano, total_resueltos_este_ano,
                        ultimo_mes_cerrado
                    )
                    WITH official_tratas AS (
                        SELECT DISTINCT trata_reporte, descripcion_trata
                        FROM cfg_gestion_metas
                        WHERE gerencia = '{g}' AND trata_reporte <> 'INTERVENCIONES'
                    ),
                    cfg AS (
                        SELECT analistas_oficiales, buzones_ingreso
                        FROM cfg_gestion_metas
                        WHERE gerencia = '{g}' AND trata_reporte = 'INTERVENCIONES'
                        LIMIT 1
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
                        WHERE ee.fecha_egreso >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months')
                          AND ee.fecha_egreso < DATE_TRUNC('month', CURRENT_DATE)
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
                    sol_sub AS (
                        SELECT 
                            id_expediente, 
                            fecha_alta as fecha_solicitud,
                            LEAD(fecha_alta) OVER (PARTITION BY id_expediente ORDER BY fecha_alta ASC) as next_solicitud
                        FROM mvw_ee_actividades_secgdu
                        WHERE nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                    ),
                    ciclos_sub AS (
                        SELECT 
                            s.id_expediente,
                            s.fecha_solicitud,
                            COALESCE(
                                (SELECT MIN(r.fecha_alta) 
                                 FROM mvw_ee_actividades_secgdu r 
                                 WHERE r.id_expediente = s.id_expediente 
                                   AND r.nombre_tipo_actividad = 'SUBSANACION'
                                   AND r.fecha_alta >= s.fecha_solicitud
                                   AND (s.next_solicitud IS NULL OR r.fecha_alta <= s.next_solicitud)
                                ),
                                s.next_solicitud,
                                e.fecha_egreso
                            ) as fecha_fin_sub
                        FROM sol_sub s
                        JOIN expedientes_egreso e ON e.id_expediente = s.id_expediente
                        WHERE s.fecha_solicitud >= e.fecha_primer_ingreso_gerencia AND s.fecha_solicitud <= e.fecha_egreso
                    ),
                    subsanaciones_globales AS (
                        SELECT 
                            cs.id_expediente,
                            SUM(GREATEST(0, (EXTRACT(epoch FROM (cs.fecha_fin_sub - cs.fecha_solicitud)) / 86400.0))) AS duracion_subsanaciones
                        FROM ciclos_sub cs
                        GROUP BY cs.id_expediente
                    ),
                    pases_internos AS (
                        SELECT 
                            pc.id_expediente,
                            SUM(GREATEST(0, (EXTRACT(epoch FROM (LEAST(cs.fecha_fin_sub, pc.fecha_fin_tramo) - GREATEST(cs.fecha_solicitud, pc.fecha_inicio_tramo))) / 86400.0))) AS duracion_subsanaciones_adentro
                        FROM pases_cronologicos pc
                        JOIN ciclos_sub cs ON cs.id_expediente = pc.id_expediente
                        WHERE pc.ubicacion_destino = 'ADENTRO'
                          AND cs.fecha_solicitud < pc.fecha_fin_tramo AND cs.fecha_fin_sub > pc.fecha_inicio_tramo
                        GROUP BY pc.id_expediente
                    ),
                    tiempos_unificados AS (
                        SELECT 
                            e.trata,
                            e.mes_label,
                            e.anio_ingreso,
                            e.duracion_total,
                            GREATEST(0.0, (COALESCE(t.dias_adentro_bruto, e.duracion_total) - COALESCE(sa.duracion_subsanaciones_adentro, 0.0))) AS duracion_neta,
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
                            COUNT(*) as count_ultimo_mes,
                            CEIL(COALESCE(AVG(tu.duracion_neta), 0.0)) as prom_propio_sector,
                            CEIL(COALESCE(AVG(tu.duracion_sub), 0.0)) as prom_subsanacion,
                            CEIL(COALESCE(AVG(tu.duracion_int), 0.0)) as prom_intervenciones,
                            ltm.max_mes as ultimo_mes_cerrado
                        FROM tiempos_unificados tu
                        JOIN latest_trata_month ltm ON ltm.trata = tu.trata AND ltm.max_mes = tu.mes_label
                        GROUP BY tu.trata, ltm.max_mes
                    ),
                    med_ing_este_ano AS (
                        SELECT 
                            tu.trata,
                            COUNT(*) as count_este_ano,
                            CEIL(COALESCE(AVG(tu.duracion_neta), 0.0)) as prom_propio_sector_este_ano,
                            CEIL(COALESCE(AVG(tu.duracion_sub), 0.0)) as prom_subsanacion_este_ano,
                            CEIL(COALESCE(AVG(tu.duracion_int), 0.0)) as prom_intervenciones_este_ano
                        FROM tiempos_unificados tu
                        JOIN latest_trata_month ltm ON ltm.trata = tu.trata AND ltm.max_mes = tu.mes_label
                        WHERE tu.anio_ingreso = EXTRACT(YEAR FROM CURRENT_DATE)::integer
                        GROUP BY tu.trata
                    )
                    SELECT 
                        '{g}' as gerencia,
                        ot.trata_reporte as trata,
                        ot.descripcion_trata,
                        COALESCE(m.prom_propio_sector, 0.0) as dias_propio_sector,
                        COALESCE(m.prom_subsanacion, 0.0) as dias_subsanacion,
                        COALESCE(m.prom_intervenciones, 0.0) as dias_intervenciones,
                        (COALESCE(m.prom_propio_sector, 0.0) + COALESCE(m.prom_subsanacion, 0.0) + COALESCE(m.prom_intervenciones, 0.0)) as dias_totales,
                        COALESCE(m.count_ultimo_mes, 0) as total_resueltos_ultimo_mes,
                        COALESCE(i.prom_propio_sector_este_ano, 0.0) as dias_propio_sector_este_ano,
                        COALESCE(i.prom_subsanacion_este_ano, 0.0) as dias_subsanacion_este_ano,
                        COALESCE(i.prom_intervenciones_este_ano, 0.0) as dias_intervenciones_este_ano,
                        (COALESCE(i.prom_propio_sector_este_ano, 0.0) + COALESCE(i.prom_subsanacion_este_ano, 0.0) + COALESCE(i.prom_intervenciones_este_ano, 0.0)) as dias_totales_este_ano,
                        (COALESCE(i.prom_propio_sector_este_ano, 0.0) + COALESCE(i.prom_subsanacion_este_ano, 0.0) + COALESCE(i.prom_intervenciones_este_ano, 0.0)) as dias_mediana_ingresados_este_ano,
                        COALESCE(i.count_este_ano, 0) as total_resueltos_este_ano,
                        COALESCE(m.ultimo_mes_cerrado, to_char(CURRENT_DATE - INTERVAL '1 month', 'YYYY-MM')) as ultimo_mes_cerrado
                    FROM official_tratas ot
                    LEFT JOIN med_ultimo_mes m ON m.trata = ot.trata_reporte
                    LEFT JOIN med_ing_este_ano i ON i.trata = ot.trata_reporte;
                """
                conn.execute(text(sql_resumen_insert))
                conn.commit()
                print(f"  Gerencia '{g}' processing times populated in {round(time.time() - t_g0, 2)}s.")

            except Exception as e:
                print(f"  Error populating gerencia '{g}': {e}")
                conn.rollback()

    print(f"All processing times using AVERAGES populated in {round(time.time() - t0, 2)}s!")

if __name__ == '__main__':
    populate()
