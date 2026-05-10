# Metodología de Cálculo - Tablero Integral SGDU

Este documento detalla la lógica de negocio y técnica aplicada para la generación de los indicadores del Tablero de Gestión.

## 1. Universo de Análisis
El reporte se basa en la extracción de datos del sistema SADE (EE y GEDO) procesados en el repositorio local PostgreSQL.

*   **Temporalidad**: Los flujos (Ingresos/Egresos) se analizan específicamente para el año **2026** para la vista mensual del tablero.
*   **Stock**: Se analiza de forma **Histórica Total**. Se consideran todos los expedientes desde el inicio de los registros en SADE sin ningún tipo de filtro por año de creación o pase. El ETL ha sido configurado para extraer la historia completa de Oracle.

---

## 2. Definición de Indicadores

### A. Ingresos (Flow In)
*   **Definición Funcional**: Entrada de un trámite a la Gerencia.
*   **Lógica Técnica**: Fecha mínima de ingreso a los buzones técnicos de la Gerencia.

### B. Egresos Efectivos (Éxito)
*   **Definición Funcional**: Finalización con documento resolutivo.
*   **Lógica Técnica**: Firma del primer documento GEDO con el acrónimo específico del trámite.

### C. Egresos No Efectivos (Desvíos)
*   **Definición Funcional**: Archivo o desvío a Guarda Temporal.
*   **Lógica Técnica**: Pase a "Guarda Temporal" sin documento de éxito previo.

### D. Egresos Totales
*   **Cálculo**: `Egresos Efectivos + Egresos No Efectivos`.

### E. Stock Propio
*   **Definición Funcional**: Expedientes pendientes en la Gerencia.
*   **Lógica Técnica**: Ingresos sin egreso, estado actual != "Subsanación".

### F. Subsanaciones Abiertas
*   **Definición Funcional**: Trámite en manos del profesional para corrección.
*   **Lógica Técnica**: Ingresos sin egreso, estado actual = "Subsanación".

---

## 3. Catálogo de Trámites - CATASTRO

| Código Trata | Detalle del Trámite | Acrónimos de Éxito |
| :--- | :--- | :--- |
| MDUG0115C | Anulación de Propiedad Horizontal | IFMMH |
| MDUG1501L | Certificado de cota de parcela nivel cero | IFMAD |
| MDUG0115G | Certificado de Determinación de Cinturón Digital | IF |
| MDUG1501H | Certificado de información catastral | IFDEX |
| MDUG0134C | Certificado de numeración domiciliaria | CECNU |
| MDUG0134N | Constitución de Estado Parcelario | IFGPA / FIPAR |
| MDUG0146A | Copia de plano | IFPCB / IFDEX |
| GENE0702C | Mensura Regularización Urbana Dominial | PPINV |
| MDUG0115F | Plano de mensura de objeto territorial | IFMOT |
| MDUG0115B | Plano de Mensura Particular | IFMSC |
| MDUG0132A | Plano de prehorizontalidad nuevo | IFMHC |
| MDUG0131A | Plano de Propiedad Horizontal modif/compl. | IFMHC |
| MDUG0131B | Plano de propiedad horizontal nuevo | IFMHC |
| MDUG0115E | Rectificación de Plano de Mensura | IFMSC / IFMHC |
| MDUG0134E | Solicitud de Certificado de fijación de línea | IFMAD |
| MDUG0135A | Solicitud de consideración a la DGROC | IFMHC, IFMMH, IFMAD, IFMSC, IFMOT, IFPCB, FIPAR |
