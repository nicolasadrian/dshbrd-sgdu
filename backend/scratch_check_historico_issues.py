import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== ANALIZANDO POR QUE mv_catastro_stock_historico DIFIERE DEL STOCK PROPIO PUNTUAL ===")
    
    # 1. En mv_catastro_stock_historico:
    # No excluye si el expediente YA EGRESÓ antes o después de la fecha de corte?
    # A la fecha de corte, si el expediente ya había emitido un IFGPA/FIPAR antes del corte, ¿debería seguir contando en stock propio a ese corte?
    # No, si ya egresó antes del corte, no está en stock propio al corte!
    # Además, ¿qué pasa con el pase posterior al egreso? Muchos expedientes luego de egresar quedan en la bandeja del analista durante días/meses hasta que los mandan a guarda o los archivan.
    
    # Veamos expedientes que a 2026-08 cuentan en stock histórico pero ya habían egresado antes:
    r_egresados_en_historico = conn.execute(text("""
        WITH cfg AS (
            SELECT cfg_gestion_metas.analistas_oficiales
            FROM cfg_gestion_metas
            WHERE cfg_gestion_metas.gerencia = 'catastro'::text AND cfg_gestion_metas.trata_reporte = 'INTERVENCIONES'::text
        ), destinatario_actual_corte AS (
            SELECT DISTINCT ON (u.id_expediente) u.id_expediente, u.trata, p.destinatario AS destinatario_cierre, p.fecha
            FROM mv_catastro_universo u
            JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente
            ORDER BY u.id_expediente, p.fecha DESC
        )
        SELECT 
            count(*) as total_en_analistas,
            count(CASE WHEN ee.id_expediente IS NOT NULL THEN 1 END) as ya_egresados_efectivos,
            count(CASE WHEN ee.id_expediente IS NULL THEN 1 END) as sin_egreso
        FROM destinatario_actual_corte dac
        LEFT JOIN mv_catastro_egresos_efectivos ee ON ee.id_expediente = dac.id_expediente
        CROSS JOIN cfg
        WHERE dac.trata = 'MDUG0134N' AND dac.destinatario_cierre = ANY(cfg.analistas_oficiales)
    """)).mappings().first()
    print("Expedientes en poder de analistas hoy para MDUG0134N:", dict(r_egresados_en_historico))
