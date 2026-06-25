-- public.mv_aph_egresos_efectivos source

CREATE MATERIALIZED VIEW public.mv_aph_egresos_efectivos
TABLESPACE pg_default
AS WITH reglas_por_trata AS (
         SELECT cfg.trata_reporte AS trata,
            unnest(cfg.acronimos_egreso) AS acronimo,
            cfg.firmantes_egreso
           FROM cfg_gestion_metas cfg
          WHERE cfg.gerencia = 'aph'::text AND cfg.trata_reporte <> 'INTERVENCIONES'::text
        ), egresos_validos AS (
         SELECT u.id_expediente,
            u.expediente,
            u.trata,
            u.descripcion_trata,
            u.descripcion,
            u.caratula,
            u.fecha_primer_ingreso_gerencia,
            d.documento AS documento_egreso,
            d.acronimo AS acronimo_egreso,
            d.fecha_asociacion AS fecha_egreso,
            d.usuario_creador AS usuario_egreso,
            row_number() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_asociacion) AS rn
           FROM mv_aph_universo u
             JOIN reglas_por_trata r ON r.trata = u.trata
             JOIN mvw_datos_gedo_secgdu d ON d.id_expediente = u.id_expediente AND d.acronimo = r.acronimo AND (r.firmantes_egreso IS NULL OR (d.usuario_creador = ANY (r.firmantes_egreso))) AND d.fecha_asociacion >= u.fecha_primer_ingreso_gerencia
          WHERE u.es_trata_propia = true
        )
 SELECT egresos_validos.id_expediente,
    egresos_validos.expediente,
    egresos_validos.trata,
    egresos_validos.descripcion_trata,
    egresos_validos.descripcion,
    egresos_validos.caratula,
    egresos_validos.fecha_primer_ingreso_gerencia,
    egresos_validos.documento_egreso,
    egresos_validos.acronimo_egreso,
    egresos_validos.fecha_egreso,
    egresos_validos.usuario_egreso,
    egresos_validos.fecha_egreso::date - egresos_validos.fecha_primer_ingreso_gerencia::date AS dias_tramitacion
   FROM egresos_validos
  WHERE egresos_validos.rn = 1
WITH DATA;

-- View indexes:
CREATE INDEX idx_mvc_eef_acro ON public.mv_aph_egresos_efectivos USING btree (acronimo_egreso);
CREATE UNIQUE INDEX idx_mvc_eef_exp ON public.mv_aph_egresos_efectivos USING btree (id_expediente);
CREATE INDEX idx_mvc_eef_fecha ON public.mv_aph_egresos_efectivos USING btree (fecha_egreso);
CREATE INDEX idx_mvc_eef_trata ON public.mv_aph_egresos_efectivos USING btree (trata);