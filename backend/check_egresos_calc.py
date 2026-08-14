import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

g_list = ['catastro', 'instalaciones', 'regularizacion', 'contable', 'etapa_proyecto', 'morfologia', 'aph', 'usos', 'aviso_obra']

def test_breakdown_egresos_efectivos():
    with engine.connect() as conn:
        for g in g_list:
            print(f"\n==================== GERENCIA: {g.upper()} ====================")
            sql = f"""
                WITH egresados AS (
                    SELECT 
                        ee.id_expediente,
                        ee.trata,
                        ee.fecha_primer_ingreso_gerencia,
                        ee.fecha_egreso,
                        EXTRACT(EPOCH FROM (ee.fecha_egreso - ee.fecha_primer_ingreso_gerencia)) / 86400.0 as duracion_total
                    FROM mv_{g}_egresos_efectivos ee
                    JOIN cfg_gestion_metas c ON c.gerencia = '{g}' AND c.trata_reporte = ee.trata
                    WHERE ee.fecha_egreso >= '2024-01-01'
                ),
                cfg AS (
                    SELECT analistas_oficiales
                    FROM cfg_gestion_metas
                    WHERE gerencia = '{g}' AND trata_reporte = 'INTERVENCIONES'
                ),
                pases AS (
                    SELECT 
                        e.trata,
                        p.id_expediente,
                        p.destinatario,
                        EXTRACT(EPOCH FROM (COALESCE(LEAD(p.fecha) OVER (PARTITION BY p.id_expediente ORDER BY p.fecha ASC), e.fecha_egreso) - p.fecha)) / 86400.0 as duracion_pase,
                        (p.destinatario = ANY (cfg.analistas_oficiales)) as es_propio
                    FROM egresados e
                    JOIN mvw_ee_pases_secgdu p ON p.id_expediente = e.id_expediente
                    CROSS JOIN cfg
                    WHERE p.fecha >= e.fecha_primer_ingreso_gerencia AND p.fecha <= e.fecha_egreso
                ),
                subs AS (
                    SELECT 
                        e.trata,
                        a.id_expediente,
                        EXTRACT(EPOCH FROM (COALESCE(a.fecha_cierre, e.fecha_egreso) - a.fecha_alta)) / 86400.0 as duracion_subs
                    FROM egresados e
                    JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = e.id_expediente
                    WHERE a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                      AND a.fecha_alta >= e.fecha_primer_ingreso_gerencia AND a.fecha_alta <= e.fecha_egreso
                ),
                pases_trata AS (
                    SELECT 
                        trata,
                        ROUND(AVG(CASE WHEN es_propio THEN duracion_pase ELSE NULL END)::numeric, 1) as avg_propio,
                        ROUND(AVG(CASE WHEN NOT es_propio THEN duracion_pase ELSE NULL END)::numeric, 1) as avg_intervenciones
                    FROM pases
                    GROUP BY trata
                ),
                subs_trata AS (
                    SELECT 
                        trata,
                        ROUND(AVG(duracion_subs)::numeric, 1) as avg_subs
                    FROM subs
                    GROUP BY trata
                ),
                total_trata AS (
                    SELECT 
                        trata,
                        COUNT(*) as cant_egresados,
                        ROUND(AVG(duracion_total)::numeric, 1) as avg_total
                    FROM egresados
                    GROUP BY trata
                )
                SELECT 
                    ot.trata_reporte as trata,
                    ot.descripcion_trata,
                    COALESCE(tt.cant_egresados, 0) as egresados,
                    COALESCE(pt.avg_propio, 0) as dias_propio,
                    COALESCE(st.avg_subs, 0) as dias_subsanacion,
                    COALESCE(pt.avg_intervenciones, 0) as dias_intervenciones,
                    COALESCE(tt.avg_total, 0) as dias_totales
                FROM cfg_gestion_metas ot
                LEFT JOIN total_trata tt ON tt.trata = ot.trata_reporte
                LEFT JOIN pases_trata pt ON pt.trata = ot.trata_reporte
                LEFT JOIN subs_trata st ON st.trata = ot.trata_reporte
                WHERE ot.gerencia = '{g}' AND ot.trata_reporte <> 'INTERVENCIONES'
                ORDER BY ot.trata_reporte;
            """
            rows = conn.execute(text(sql)).mappings().fetchall()
            for r in rows:
                if r['egresados'] > 0:
                    print(f"Trata {r['trata']:10s} | Egresados:{r['egresados']:5d} | Propio:{float(r['dias_propio']):6.1f} d | Subs:{float(r['dias_subsanacion']):6.1f} d | Interv:{float(r['dias_intervenciones']):6.1f} d | TOTAL:{float(r['dias_totales']):6.1f} d")

if __name__ == '__main__':
    test_breakdown_egresos_efectivos()
