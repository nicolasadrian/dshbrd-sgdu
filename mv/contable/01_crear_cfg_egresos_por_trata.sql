-- ============================================================
-- MIGRACIÓN 01: Crear cfg_egresos_por_trata y cargar reglas existentes
-- ============================================================
-- PROPÓSITO:
--   1) Crear tabla nueva cfg_egresos_por_trata.
--   2) Cargar las reglas actuales de Instalaciones y Morfología.
--
-- EFECTO: Esta tabla es retrocompatible. No afecta a las MVs actuales
-- hasta que se recreen los archivos siguientes (02 y 03).
--
-- ORDEN DE EJECUCIÓN: 1° del paquete de migración.
-- ============================================================

CREATE TABLE IF NOT EXISTS cfg_egresos_por_trata (
    id           SERIAL PRIMARY KEY,
    gerencia     TEXT NOT NULL,
    trata        TEXT NOT NULL,
    acronimo     TEXT NOT NULL,
    firmantes    TEXT[],                  -- NULL = cualquier firmante
    fecha_desde  DATE,                    -- NULL = sin restricción
    fecha_hasta  DATE,                    -- NULL = sin restricción
    UNIQUE (gerencia, trata, acronimo)
);

CREATE INDEX IF NOT EXISTS idx_cep_gerencia ON cfg_egresos_por_trata(gerencia);
CREATE INDEX IF NOT EXISTS idx_cep_trata    ON cfg_egresos_por_trata(trata);

COMMENT ON TABLE cfg_egresos_por_trata IS 
'Reglas de egreso efectivo por (gerencia, trata, acrónimo). Permite restricciones por firmante y por rango temporal.';


-- Limpiar registros previos para idempotencia
DELETE FROM cfg_egresos_por_trata WHERE gerencia IN ('instalaciones','morfologia');


-- ============================================================
-- INSTALACIONES: 15 tratas × 3 acrónimos base (+ 2 extras para MDUG2101A)
-- Sin restricción de firmante (cualquiera puede firmar)
-- ============================================================
INSERT INTO cfg_egresos_por_trata (gerencia, trata, acronimo, firmantes) VALUES
-- MDUG2101A tiene 5 acrónimos
('instalaciones','MDUG2101A','PROIN',NULL),
('instalaciones','MDUG2101A','PLINE',NULL),
('instalaciones','MDUG2101A','IFCIS',NULL),
('instalaciones','MDUG2101A','IFSMC',NULL),
('instalaciones','MDUG2101A','IFRSP',NULL),
-- Resto de tratas: 3 acrónimos
('instalaciones','MDUG2901A','PROIN',NULL),
('instalaciones','MDUG2901A','PLINE',NULL),
('instalaciones','MDUG2901A','IFSMC',NULL),
('instalaciones','MDUG2501A','PROIN',NULL),
('instalaciones','MDUG2501A','PLINE',NULL),
('instalaciones','MDUG2501A','IFSMC',NULL),
('instalaciones','MDUG2201A','PROIN',NULL),
('instalaciones','MDUG2201A','PLINE',NULL),
('instalaciones','MDUG2201A','IFSMC',NULL),
('instalaciones','MDUG2701A','PROIN',NULL),
('instalaciones','MDUG2701A','PLINE',NULL),
('instalaciones','MDUG2701A','IFSMC',NULL),
('instalaciones','MDUG2401A','PROIN',NULL),
('instalaciones','MDUG2401A','PLINE',NULL),
('instalaciones','MDUG2401A','IFSMC',NULL),
('instalaciones','MDUG2601A','PROIN',NULL),
('instalaciones','MDUG2601A','PLINE',NULL),
('instalaciones','MDUG2601A','IFSMC',NULL),
('instalaciones','MDUG2301A','PROIN',NULL),
('instalaciones','MDUG2301A','PLINE',NULL),
('instalaciones','MDUG2301A','IFSMC',NULL),
('instalaciones','MDUG3301A','PROIN',NULL),
('instalaciones','MDUG3301A','PLINE',NULL),
('instalaciones','MDUG3301A','IFSMC',NULL),
('instalaciones','MDUG0904A','PROIN',NULL),
('instalaciones','MDUG0904A','PLINE',NULL),
('instalaciones','MDUG0904A','IFSMC',NULL),
('instalaciones','MDUG0120A','PROIN',NULL),
('instalaciones','MDUG0120A','PLINE',NULL),
('instalaciones','MDUG0120A','IFSMC',NULL),
('instalaciones','MJGG1601A','PROIN',NULL),
('instalaciones','MJGG1601A','PLINE',NULL),
('instalaciones','MJGG1601A','IFSMC',NULL),
('instalaciones','MDUG0101D','PROIN',NULL),
('instalaciones','MDUG0101D','PLINE',NULL),
('instalaciones','MDUG0101D','IFSMC',NULL),
('instalaciones','MDUG0101G','PROIN',NULL),
('instalaciones','MDUG0101G','PLINE',NULL),
('instalaciones','MDUG0101G','IFSMC',NULL),
('instalaciones','MJGG1701A','PROIN',NULL),
('instalaciones','MJGG1701A','PLINE',NULL),
('instalaciones','MJGG1701A','IFSMC',NULL);


-- ============================================================
-- MORFOLOGIA: 10 tratas × 3 acrónimos (DI, ANEXO, IF) firmados por ALANDAZURI
-- ============================================================
INSERT INTO cfg_egresos_por_trata (gerencia, trata, acronimo, firmantes)
SELECT 
    'morfologia' AS gerencia,
    trata,
    acronimo,
    ARRAY['ALANDAZURI']::TEXT[] AS firmantes
FROM (
    SELECT UNNEST(ARRAY[
        'MDUG1801A','MDUG0107A','MDUG3501A','MDUG3601A','MDUG3901A',
        'MDUG1802A','MDUG1804A','MDUG1803A','MDUG1805A','MDUG1806A'
    ]) AS trata
) t
CROSS JOIN (
    SELECT UNNEST(ARRAY['DI','ANEXO','IF']) AS acronimo
) a;


-- ============================================================
-- VALIDACIÓN
-- ============================================================
SELECT 
    gerencia,
    COUNT(*) AS reglas_cargadas,
    COUNT(DISTINCT trata) AS tratas_distintas,
    COUNT(DISTINCT acronimo) AS acronimos_distintos
FROM cfg_egresos_por_trata
GROUP BY gerencia
ORDER BY gerencia;

-- Esperado:
-- instalaciones: 47 reglas, 15 tratas, 5 acrónimos
-- morfologia:    30 reglas, 10 tratas, 3 acrónimos
