-- public.mv_aph_egresos_no_efectivos source

CREATE MATERIALIZED VIEW public.mv_aph_egresos_no_efectivos
TABLESPACE pg_default
AS SELECT u.id_expediente,
    u.expediente,
    u.trata,
    u.descripcion_trata,
    u.descripcion,
    u.caratula,
    u.estado_expediente,
    u.fecha_primer_ingreso_gerencia,
    up.fecha_ultimo_pase AS fecha_ultimo_movimiento,
    up.destinatario_actual AS poseedor_actual,
    CURRENT_DATE - up.fecha_ultimo_pase::date AS dias_desde_guarda,
    up.fecha_ultimo_pase::date - u.fecha_primer_ingreso_gerencia::date AS dias_tramitacion_aprox
   FROM mv_aph_universo u
     JOIN mv_ultimo_pase up ON up.id_expediente = u.id_expediente
     LEFT JOIN mv_aph_egresos_efectivos eef ON eef.id_expediente = u.id_expediente
  WHERE u.es_trata_propia = true AND u.estado_expediente = 'Guarda Temporal'::text AND eef.id_expediente IS NULL
WITH DATA;

-- View indexes:
CREATE UNIQUE INDEX idx_mvc_ene_exp ON public.mv_aph_egresos_no_efectivos USING btree (id_expediente);
CREATE INDEX idx_mvc_ene_fecha ON public.mv_aph_egresos_no_efectivos USING btree (fecha_ultimo_movimiento);
CREATE INDEX idx_mvc_ene_trata ON public.mv_aph_egresos_no_efectivos USING btree (trata);