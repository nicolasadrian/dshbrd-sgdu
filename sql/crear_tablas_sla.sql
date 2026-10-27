-- ==============================================================
-- MIGRACIÓN DDL PARA MÓDULO SLA EN PRODUCCIÓN
-- Tablas: cfg_sla_tratas y cfg_sla_historial
-- ==============================================================

CREATE TABLE IF NOT EXISTS cfg_sla_tratas (
    id SERIAL PRIMARY KEY,
    direccion VARCHAR(20) NOT NULL DEFAULT 'DGROC',
    gerencia VARCHAR(50) NOT NULL,
    trata_reporte VARCHAR(50) NOT NULL,
    dias_sla INTEGER NOT NULL CHECK (dias_sla > 0),
    detalle TEXT NOT NULL,
    actualizado_por VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cfg_sla_gerencia_trata UNIQUE (gerencia, trata_reporte)
);

CREATE TABLE IF NOT EXISTS cfg_sla_historial (
    id SERIAL PRIMARY KEY,
    sla_id INTEGER REFERENCES cfg_sla_tratas(id) ON DELETE SET NULL,
    gerencia VARCHAR(50) NOT NULL,
    trata_reporte VARCHAR(50) NOT NULL,
    dias_sla INTEGER NOT NULL,
    detalle TEXT NOT NULL,
    usuario VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cfg_sla_gerencia_trata ON cfg_sla_tratas(gerencia, trata_reporte);
CREATE INDEX IF NOT EXISTS idx_cfg_sla_historial_trata ON cfg_sla_historial(gerencia, trata_reporte);
