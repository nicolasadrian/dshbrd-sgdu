-- public.mv_instalaciones_stock_historico source

CREATE MATERIALIZED VIEW public.mv_instalaciones_stock_historico
TABLESPACE pg_default
AS WITH cfg AS (
         SELECT cfg_gestion_metas.analistas_oficiales,
            cfg_gestion_metas.tratas_incluidas
           FROM cfg_gestion_metas
          WHERE cfg_gestion_metas.gerencia = 'instalaciones'::text AND cfg_gestion_metas.trata_reporte = 'INSTALACIONES'::text
        ), fechas_corte AS (
         SELECT (date_trunc('month'::text, mes.mes) + '1 mon -1 days'::interval)::date AS fecha_corte
           FROM generate_series(date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) - '11 mons'::interval, date_trunc('month'::text, CURRENT_DATE::timestamp with time zone), '1 mon'::interval) mes(mes)
        ), destinatario_por_corte AS (
         SELECT DISTINCT ON (u.id_expediente, fc.fecha_corte) u.id_expediente,
            u.trata,
            u.es_trata_propia,
            fc.fecha_corte,
            p.destinatario AS destinatario_cierre
           FROM mv_instalaciones_universo u
             CROSS JOIN fechas_corte fc
             JOIN mvw_ee_pases_secgdu p ON p.id_expediente = u.id_expediente AND p.fecha::date <= fc.fecha_corte
          ORDER BY u.id_expediente, fc.fecha_corte, p.fecha DESC
        ), subsanacion_abierta_al_cierre AS (
         SELECT DISTINCT ON (dpc_1.id_expediente, dpc_1.fecha_corte) dpc_1.id_expediente,
            dpc_1.fecha_corte,
            true AS tiene_subsanacion_abierta
           FROM destinatario_por_corte dpc_1
             JOIN mvw_ee_actividades_secgdu a ON a.id_expediente = dpc_1.id_expediente AND a.usuario_alta = dpc_1.destinatario_cierre AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'::text AND a.fecha_alta::date <= dpc_1.fecha_corte AND (a.fecha_cierre IS NULL OR a.fecha_cierre::date > dpc_1.fecha_corte)
          ORDER BY dpc_1.id_expediente, dpc_1.fecha_corte, a.fecha_alta DESC
        )
 SELECT dpc.fecha_corte AS mes_cierre,
    to_char(dpc.fecha_corte::timestamp with time zone, 'YYYY-MM'::text) AS mes_label,
    dpc.trata,
    dpc.es_trata_propia,
        CASE
            WHEN COALESCE(sac.tiene_subsanacion_abierta, false) THEN 'SUBSANACION'::text
            ELSE 'STOCK_PROPIO'::text
        END AS categoria,
    count(*) AS cant_expedientes
   FROM destinatario_por_corte dpc
     LEFT JOIN subsanacion_abierta_al_cierre sac ON sac.id_expediente = dpc.id_expediente AND sac.fecha_corte = dpc.fecha_corte
     CROSS JOIN cfg
  WHERE dpc.destinatario_cierre = ANY (cfg.analistas_oficiales)
  GROUP BY dpc.fecha_corte, dpc.trata, dpc.es_trata_propia, (
        CASE
            WHEN COALESCE(sac.tiene_subsanacion_abierta, false) THEN 'SUBSANACION'::text
            ELSE 'STOCK_PROPIO'::text
        END)
WITH DATA;

-- View indexes:
CREATE INDEX idx_mvi_sh_categoria ON public.mv_instalaciones_stock_historico USING btree (categoria);
CREATE INDEX idx_mvi_sh_mes ON public.mv_instalaciones_stock_historico USING btree (mes_cierre);
CREATE INDEX idx_mvi_sh_propia ON public.mv_instalaciones_stock_historico USING btree (es_trata_propia);
CREATE INDEX idx_mvi_sh_trata ON public.mv_instalaciones_stock_historico USING btree (trata);