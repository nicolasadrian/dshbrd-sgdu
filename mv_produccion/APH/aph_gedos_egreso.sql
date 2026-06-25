-- public.mv_aph_gedos_egreso source

CREATE MATERIALIZED VIEW public.mv_aph_gedos_egreso
TABLESPACE pg_default
AS WITH reglas_por_trata AS (
         SELECT cfg.trata_reporte AS trata,
            unnest(cfg.acronimos_egreso) AS acronimo,
            cfg.firmantes_egreso
           FROM cfg_gestion_metas cfg
          WHERE cfg.gerencia = 'aph'::text AND cfg.trata_reporte <> 'INTERVENCIONES'::text
        ), raw_gedos AS (
         SELECT u.id_expediente,
            u.expediente,
            u.trata,
            u.descripcion_trata,
            d.documento AS documento_egreso,
            d.acronimo AS acronimo_egreso,
            d.fecha_asociacion AS fecha_egreso,
            d.usuario_creador AS usuario_egreso,
            row_number() OVER (PARTITION BY u.id_expediente ORDER BY d.fecha_asociacion DESC, d.documento DESC) AS rn
           FROM mv_aph_universo u
             JOIN reglas_por_trata r ON r.trata = u.trata
             JOIN mvw_datos_gedo_secgdu d ON d.id_expediente = u.id_expediente AND d.acronimo = r.acronimo AND (r.firmantes_egreso IS NULL OR (d.usuario_creador = ANY (r.firmantes_egreso))) AND d.fecha_asociacion >= u.fecha_primer_ingreso_gerencia
          WHERE u.es_trata_propia = true
        )
 SELECT raw_gedos.id_expediente,
    raw_gedos.expediente,
    raw_gedos.trata,
    raw_gedos.descripcion_trata,
    raw_gedos.documento_egreso,
    raw_gedos.acronimo_egreso,
    raw_gedos.fecha_egreso,
    raw_gedos.usuario_egreso
   FROM raw_gedos
  WHERE raw_gedos.rn = 1
WITH DATA;

-- View indexes:
CREATE INDEX idx_mvc_geg_acro ON public.mv_aph_gedos_egreso USING btree (acronimo_egreso);
CREATE INDEX idx_mvc_geg_exp ON public.mv_aph_gedos_egreso USING btree (id_expediente);
CREATE INDEX idx_mvc_geg_fecha ON public.mv_aph_gedos_egreso USING btree (fecha_egreso);
CREATE INDEX idx_mvc_geg_trata ON public.mv_aph_gedos_egreso USING btree (trata);