import sys
sys.path.insert(0, './backend')
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("=== SUBSANACIONES ACTUALES: POR QUE NO CONSIDERA ULTIMO ESTADO PENDIENTE? ===")
    
    # Veamos expedientes donde la última actividad por fecha_alta es PENDIENTE vs donde hay PENDIENTE pero luego CERRADA
    sample_act = conn.execute(text("""
        WITH ranked_act AS (
            SELECT a.id_expediente, a.usuario_alta, a.nombre_tipo_actividad, a.estado, a.fecha_alta,
                   row_number() OVER (PARTITION BY a.id_expediente ORDER BY a.fecha_alta DESC) as rn
            FROM mvw_ee_actividades_secgdu a
            WHERE a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
        )
        SELECT ra.*, up.destinatario_actual, u.trata
        FROM ranked_act ra
        JOIN mv_catastro_universo u ON u.id_expediente = ra.id_expediente
        JOIN mv_ultimo_pase up ON up.id_expediente = ra.id_expediente
        WHERE ra.rn = 1 AND ra.estado = 'PENDIENTE'
        LIMIT 10
    """)).mappings().fetchall()
    
    print(f"Sample expedientes cuya ULTIMA actividad es PENDIENTE (total encontrados en sample: {len(sample_act)}):")
    for s in sample_act:
        print(dict(s))

    # Veamos casos donde DISTINCT ON en mv_catastro_subsanaciones toma algo que no es la última actividad real o cómo está armada la vista actual
    print("\n--- Analizando la consulta actual de mv_catastro_subsanaciones ---")
    current_subs = conn.execute(text("""
        SELECT count(*) FROM mv_catastro_subsanaciones WHERE trata = 'MDUG0134N'
    """)).scalar()
    print("Conteo en mv_catastro_subsanaciones para MDUG0134N:", current_subs)
    
    # Cuántos tienen la ÚLTIMA actividad como PENDIENTE
    ultima_act_pendiente = conn.execute(text("""
        WITH cfg AS (
            SELECT analistas_oficiales FROM cfg_gestion_metas 
            WHERE gerencia = 'catastro' AND trata_reporte = 'INTERVENCIONES'
        ),
        ultima_actividad AS (
            SELECT DISTINCT ON (id_expediente) id_expediente, usuario_alta, nombre_tipo_actividad, estado, fecha_alta
            FROM mvw_ee_actividades_secgdu
            WHERE nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
            ORDER BY id_expediente, fecha_alta DESC
        )
        SELECT count(*)
        FROM mv_catastro_universo u
        JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
        JOIN ultima_actividad ua ON ua.id_expediente = u.id_expediente
        CROSS JOIN cfg
        WHERE u.trata = 'MDUG0134N' AND u.es_trata_propia = true 
          AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
          AND ua.estado = 'PENDIENTE'
    """)).scalar()
    print("Conteo exigiendo que la ÚLTIMA actividad SOLICITUD_SUBSANACION_TAD sea PENDIENTE:", ultima_act_pendiente)

    # Y qué pasa si hay actividades TAD y SUBSANACION mezcladas
    todas_acts_pendiente = conn.execute(text("""
        WITH cfg AS (
            SELECT analistas_oficiales FROM cfg_gestion_metas 
            WHERE gerencia = 'catastro' AND trata_reporte = 'INTERVENCIONES'
        ),
        ultima_act_cualquiera AS (
            SELECT DISTINCT ON (id_expediente) id_expediente, usuario_alta, nombre_tipo_actividad, estado, fecha_alta
            FROM mvw_ee_actividades_secgdu
            ORDER BY id_expediente, fecha_alta DESC
        )
        SELECT count(*), ua.estado, ua.nombre_tipo_actividad
        FROM mv_catastro_universo u
        JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
        JOIN ultima_act_cualquiera ua ON ua.id_expediente = u.id_expediente
        CROSS JOIN cfg
        WHERE u.trata = 'MDUG0134N' AND u.es_trata_propia = true 
          AND up.destinatario_actual = ANY(cfg.analistas_oficiales)
        GROUP BY ua.estado, ua.nombre_tipo_actividad
    """)).mappings().fetchall()
    print("Distribución por última actividad cualquiera de expedientes en analistas:")
    for ta in todas_acts_pendiente:
        print(dict(ta))
