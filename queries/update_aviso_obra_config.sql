-- Actualización de Configuración para AVISO DE OBRA
INSERT INTO cfg_gestion_metas (gerencia, trata_reporte, tratas_incluidas, buzones_ingreso, analistas_oficiales, acronimos_egreso)
VALUES (
    'aviso_obra', 
    'MDUG0102B', 
    ARRAY['MDUG0102B'], 
    ARRAY['DGROC-AUTOMAT'], 
    ARRAY['DGROC-AUTOMAT'], 
    ARRAY['IFCAO', 'IFCFP', 'IFCAC']
),
(
    'aviso_obra', 
    'INTERVENCIONES', 
    ARRAY['MDUG0102B'], -- Aquí indicamos cuáles EXCLUIR (usaremos una lógica especial en la vista)
    ARRAY['DGROC-AUTOMAT'], 
    ARRAY['DGROC-AUTOMAT'], 
    ARRAY[]
)
ON CONFLICT (gerencia, trata_reporte) DO UPDATE SET
    tratas_incluidas = EXCLUDED.tratas_incluidas,
    buzones_ingreso = EXCLUDED.buzones_ingreso,
    analistas_oficiales = EXCLUDED.analistas_oficiales,
    acronimos_egreso = EXCLUDED.acronimos_egreso;

-- Refactor de la Vista de Lifecycle para soportar la lógica de INTERVENCIONES (Exclusión)
CREATE OR REPLACE VIEW v_expedientes_lifecycle AS
WITH pases_filtrados AS (
    SELECT p.id_expediente, p.fecha, p.destinatario, p.usuario as remitente, p.estado
    FROM mvw_ee_pases_secgdu p
),
ingresos AS (
    -- Casos Normales (Trámites específicos)
    SELECT 
        p.id_expediente, 
        cfg.gerencia, 
        cfg.trata_reporte,
        MIN(p.fecha)::date as fecha_ing
    FROM pases_filtrados p
    JOIN mvw_expedientes_tratas_secgdu et ON p.id_expediente = et.id_expediente
    JOIN cfg_gestion_metas cfg ON et.trata = ANY(cfg.tratas_incluidas) AND cfg.trata_reporte != 'INTERVENCIONES'
    WHERE p.destinatario = ANY(cfg.buzones_ingreso)
    GROUP BY 1, 2, 3

    UNION ALL

    -- Casos de INTERVENCIONES (Todo lo que entra a los buzones y NO es de la lista principal)
    SELECT 
        p.id_expediente, 
        cfg.gerencia, 
        'INTERVENCIONES' as trata_reporte,
        MIN(p.fecha)::date as fecha_ing
    FROM pases_filtrados p
    JOIN mvw_expedientes_tratas_secgdu et ON p.id_expediente = et.id_expediente
    JOIN cfg_gestion_metas cfg ON cfg.trata_reporte = 'INTERVENCIONES'
    WHERE p.destinatario = ANY(cfg.buzones_ingreso)
      AND et.trata != ALL(cfg.tratas_incluidas) -- EXCLUIMOS los trámites principales
    GROUP BY 1, 2, 3
),
egresos_gedo AS (
    SELECT 
        g.id_expediente, 
        i.gerencia,
        i.trata_reporte,
        MIN(g.fecha_creacion)::date as fecha_egr,
        'EFECTIVO' as tipo_egr
    FROM mvw_datos_gedo_secgdu g
    JOIN ingresos i ON g.id_expediente = i.id_expediente
    JOIN cfg_gestion_metas cfg ON i.gerencia = cfg.gerencia AND i.trata_reporte = cfg.trata_reporte
    WHERE g.acronimo = ANY(cfg.acronimos_egreso) AND g.fecha_creacion >= i.fecha_ing
    GROUP BY 1, 2, 3
),
egresos_pases AS (
    SELECT 
        p.id_expediente,
        i.gerencia,
        i.trata_reporte,
        -- Para Intervenciones usamos MAX (última fecha), para el resto MIN (primera fecha)
        CASE 
            WHEN i.trata_reporte = 'INTERVENCIONES' THEN MAX(p.fecha)::date 
            ELSE MIN(p.fecha)::date 
        END as fecha_egr,
        'NO_EFECTIVO' as tipo_egr
    FROM pases_filtrados p
    JOIN ingresos i ON p.id_expediente = i.id_expediente
    JOIN cfg_gestion_metas cfg ON i.gerencia = cfg.gerencia AND i.trata_reporte = cfg.trata_reporte
    WHERE p.fecha > i.fecha_ing 
      AND p.remitente = ANY(cfg.analistas_oficiales)
      AND p.destinatario != ANY(cfg.analistas_oficiales)
      AND p.destinatario != ANY(cfg.buzones_ingreso)
      -- Para INTERVENCIONES, el egreso es cuando sale del área hacia un usuario/buzón externo
      AND (
          i.trata_reporte != 'INTERVENCIONES' AND p.estado NOT ILIKE 'Subsanaci%'
          OR 
          i.trata_reporte = 'INTERVENCIONES'
      )
    GROUP BY 1, 2, 3
),
egresos_final AS (
    SELECT id_expediente, gerencia, trata_reporte, 
           CASE 
             WHEN trata_reporte = 'INTERVENCIONES' THEN MAX(fecha_egr)
             ELSE MIN(fecha_egr)
           END as fecha_egr, 
           tipo_egr
    FROM (
        SELECT * FROM egresos_gedo
        UNION ALL
        SELECT * FROM egresos_pases
    ) sub
    GROUP BY 1, 2, 3, 5
)
SELECT 
    i.id_expediente,
    i.gerencia,
    i.trata_reporte,
    i.fecha_ing,
    e.fecha_egr,
    e.tipo_egr,
    CASE 
        WHEN e.fecha_egr IS NULL THEN 'ACTIVO'
        ELSE 'CERRADO'
    END as status_gestion
FROM ingresos i
LEFT JOIN egresos_final e ON i.id_expediente = e.id_expediente AND i.gerencia = e.gerencia AND i.trata_reporte = e.trata_reporte;
