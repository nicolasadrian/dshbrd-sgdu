-- OPTIMIZACIÓN CENTRAL: Línea de Tiempo de Pases
-- Esta vista pre-calcula los rangos de fecha de cada pase para evitar usar LEAD() en cada reporte.

DROP MATERIALIZED VIEW IF EXISTS mvw_pases_timeline CASCADE;

CREATE MATERIALIZED VIEW mvw_pases_timeline AS
SELECT 
    id_expediente,
    fecha as fecha_inicio,
    LEAD(fecha) OVER (PARTITION BY id_expediente ORDER BY fecha) as fecha_fin,
    destinatario,
    usuario as remitente,
    estado,
    CASE WHEN estado ILIKE 'Subsanaci%' THEN 1 ELSE 0 END as is_subs
FROM mvw_ee_pases_secgdu;

-- Índices críticos para que los reportes históricos vuelen
CREATE INDEX idx_timeline_id_exp ON mvw_pases_timeline (id_expediente);
CREATE INDEX idx_timeline_fechas ON mvw_pases_timeline (fecha_inicio, fecha_fin);
CREATE INDEX idx_timeline_subs ON mvw_pases_timeline (is_subs) WHERE is_subs = 1;
CREATE INDEX idx_timeline_destinatario ON mvw_pases_timeline (destinatario);

ANALYZE mvw_pases_timeline;
