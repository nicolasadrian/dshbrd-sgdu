/* 
   ANÁLISIS DE TIEMPOS DE RESOLUCIÓN: MDUG0146A (Copia de Plano)
   Calcula el tiempo desde el ingreso a Catastro hasta la firma del documento final (IFPCB o IFDEX)
*/

WITH ingresos AS (
    -- Identificar cuándo entró cada expediente a los buzones de Catastro
    SELECT p.id_expediente, MIN(p.fecha) as fecha_ingreso
    FROM mvw_ee_pases_secgdu p
    JOIN mvw_expedientes_tratas_secgdu e ON p.id_expediente = e.id_expediente
    WHERE e.trata = 'MDUG0146A'
      AND p.destinatario IN (
          'DGROC-CIC', 'DGROC-COPIAPLANO', 'DGROC-DCATDES', 
          'DGROC-DCATMEN', 'DGROC-DCATPOL', 'DGROC-DCATTIT'
      )
    GROUP BY p.id_expediente
),
egresos AS (
    -- Identificar cuándo se firmó el documento de salida (IFPCB o IFDEX) después del ingreso
    SELECT g.id_expediente, MIN(g.fecha_creacion) as fecha_egreso
    FROM mvw_datos_gedo_secgdu g
    JOIN ingresos i ON g.id_expediente = i.id_expediente
    WHERE g.acronimo IN ('IFPCB', 'IFDEX')
      AND g.fecha_creacion >= i.fecha_ingreso
    GROUP BY g.id_expediente
),
calculo_tiempos AS (
    -- Calcular la diferencia de días para cada trámite finalizado
    SELECT 
        i.id_expediente,
        (e.fecha_egreso::date - i.fecha_ingreso::date) as dias_tramitacion
    FROM ingresos i
    JOIN egresos e ON i.id_expediente = e.id_expediente
)
SELECT 
    COUNT(*) as cantidad_tramites_finalizados,
    ROUND(AVG(dias_tramitacion), 2) as tiempo_promedio_resolucion_dias,
    MAX(dias_tramitacion) as peor_tiempo_resolucion_dias,
    MIN(dias_tramitacion) as mejor_tiempo_resolucion_dias
FROM calculo_tiempos;
