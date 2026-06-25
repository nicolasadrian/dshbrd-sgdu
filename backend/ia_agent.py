import os
import re
import json
import logging
from typing import Dict, Any, List
import google.generativeai as genai
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# Configurar API de Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY no configurada. El agente conversacional no responderá.")

# Esquema de tablas críticas simplificado para el Prompt
SCHEMA_INFO = """
1. VISTAS DE EGRESOS POR GERENCIA (mv_[gerencia]_gedos_egreso):
   - Nombres posibles: mv_usos_gedos_egreso, mv_catastro_gedos_egreso, mv_instalaciones_gedos_egreso, mv_regularizacion_gedos_egreso, mv_contable_gedos_egreso, mv_etapa_proyecto_gedos_egreso, mv_morfologia_gedos_egreso, mv_aph_gedos_egreso, mv_aviso_obra_gedos_egreso
   - Columnas principales: fecha_egreso (TIMESTAMP o DATE), trata (VARCHAR), expediente (VARCHAR)
   - Uso: Consultar la cantidad y detalle de egresos/trámites egresados por gerencia y fecha.

2. VISTA DE HISTORIAL DE REPORTES (mvw_reporte_historico_[gerencia]):
   - Ejemplos: mvw_reporte_historico_usos, mvw_reporte_historico_catastro.
   - Columnas: mes_label (VARCHAR, ej: '2026-01-01'), trata (VARCHAR), ingresos (INT), egresos (INT), stock_fin (INT).

3. TABLA DE CONFIGURACIÓN DE METAS (cfg_gestion_metas):
   - Columnas: gerencia (VARCHAR), tratas_incluidas (VARCHAR[])
"""

SYSTEM_PROMPT = f"""
Eres un agente de Inteligencia Artificial experto en SQL y análisis de datos para el sistema de Gestión de Desarrollo Urbano (SGDU).
Tu rol es traducir las preguntas en lenguaje natural del usuario a consultas SQL SELECT válidas y seguras para PostgreSQL.

Esquema de Base de Datos Disponible en el Tablero:
{SCHEMA_INFO}

Reglas específicas:
- "DGIUR" (Dirección General de Interpretación Urbanística) engloba tres gerencias clave: "morfologia", "aph" y "usos". 
- Si preguntan por egresos o trámites en "DGIUR", debes consolidar datos de las vistas correspondientes: `mv_morfologia_gedos_egreso`, `mv_aph_gedos_egreso` y `mv_usos_gedos_egreso` usando `UNION ALL`.
- "Disposiciones" o "DI" se refiere al acrónimo de documento 'DI'. En las vistas de egresos, la columna `trata` representa el tipo de trámite o documento. Para contar o buscar Disposiciones (DI), filtra por `trata LIKE '%%DI%%'` o similar en las gerencias de DGIUR (morfologia, aph, usos).
- "Consulta de Usos" se mapea a la gerencia "usos". Por lo tanto, los egresos de consulta de usos están en la vista: `mv_usos_gedos_egreso` o `mvw_reporte_historico_usos`.
- Para filtrar por los últimos 2 años: calcula el rango de fechas dinámicamente tomando como referencia la fecha actual del sistema (ej: `fecha_egreso >= NOW() - INTERVAL '2 years'`).

Instrucciones Críticas:
1. SOLO genera consultas SQL del tipo 'SELECT'. Cualquier otro comando está estrictamente prohibido.
2. Devuelve tu respuesta estructurada exactamente en formato JSON con la siguiente estructura:
{{
  "thought": "Explicación breve de lo que estás haciendo o razonamiento.",
  "sql": "La consulta SQL SELECT generada completa (sin formatear con saltos de línea molestos si no es necesario, pero válida)",
  "error": "Mensaje de error si la pregunta no puede ser resuelta con el esquema provisto."
}}
4. No envíes código markdown en tu respuesta (nada de ```json o ```sql), devuelve únicamente el string en formato JSON plano para que el parser lo procese directamente.
"""

def execute_readonly_sql(sql_query: str) -> List[Dict[str, Any]]:
    """Ejecuta una consulta SQL SELECT de solo lectura y retorna el resultado."""
    # Validación extra a nivel de string para evitar inyecciones destructivas
    cleaned_query = sql_query.strip().lower()
    for restricted in ["insert ", "update ", "delete ", "drop ", "truncate ", "alter ", "create "]:
        if restricted in cleaned_query:
            raise ValueError(f"Acción no permitida detectada en SQL: {restricted}")

    db_url = os.getenv("DATABASE_URL_LOCAL") or os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_PUBLIC")
    if not db_url:
        db_url = "postgresql://postgres:lenovo@localhost:5432/sade_db"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # Creamos un motor temporal
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            # Forzar sesión de solo lectura si es soportado por el motor/transacción
            conn.execute(text("SET TRANSACTION READ ONLY"))
            result = conn.execute(text(sql_query))
            
            # Formatear salida
            keys = result.keys()
            rows = [dict(zip(keys, row)) for row in result.fetchall()]
            return rows
    finally:
        engine.dispose()

def ask_agent(query_text: str, history_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Interactúa con el modelo Gemini para procesar la pregunta del usuario manteniendo el hilo."""
    if not GEMINI_API_KEY:
        return {
            "thought": "API key de Gemini ausente.",
            "response": "Lo siento, la API Key de Inteligencia Artificial no está configurada en el servidor.",
            "sql": None,
            "data": None
        }

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"},
            system_instruction=SYSTEM_PROMPT
        )
        
        # Mapear e inyectar el historial si existe (Gemini requiere turnos user/model completos)
        gemini_history = []
        if history_data and len(history_data) > 1:
            # Filtramos para asegurarnos de que la conversación sea alternada y no falle
            # Gemini espera: user -> model -> user -> model...
            for msg in history_data[:-1]:
                role = "user" if msg.get("role") == "user" else "model"
                gemini_history.append({
                    "role": role,
                    "parts": [msg.get("content", "")]
                })
            
            # Si el último mensaje del historial inyectado es 'user', Gemini dará error
            # al hacer send_message (ya que tendríamos user -> user seguido).
            # En ese caso, removemos el último para mantener la alternancia limpia.
            if gemini_history and gemini_history[-1]["role"] == "user":
                gemini_history.pop()
        
        # Crear la sesión de chat con el historial
        try:
            chat = model.start_chat(history=gemini_history)
            response = chat.send_message(query_text)
        except Exception as chat_err:
            logger.warning(f"Error al iniciar chat con historial: {chat_err}. Reintentando sin historial.")
            chat = model.start_chat(history=[])
            response = chat.send_message(query_text)
        
        response_data = json.loads(response.text)
        
        sql_generated = response_data.get("sql")
        thought = response_data.get("thought")
        error = response_data.get("error")

        if error or not sql_generated:
            return {
                "thought": thought,
                "response": error or "No pude deducir una consulta SQL apropiada para tu pregunta.",
                "sql": None,
                "data": None
            }

        # Ejecutar SQL de forma segura
        try:
            records = execute_readonly_sql(sql_generated)
            
            # Generar respuesta amigable con Gemini basándose en los datos obtenidos
            synthesis_prompt = f"""
            El usuario preguntó: "{query_text}"
            Se ejecutó la siguiente consulta SQL: "{sql_generated}"
            Los resultados obtenidos de la base de datos son: {records}

            Escribe una respuesta ejecutiva y amigable en español que responda exactamente a la pregunta del usuario usando estos datos.
            No agregues detalles de base de datos técnica (no menciones SQL o nombres de tablas) a menos que te lo pregunten.
            """
            
            synthesis_model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            synthesis_response = synthesis_model.generate_content(synthesis_prompt)
            
            return {
                "thought": thought,
                "response": synthesis_response.text,
                "sql": sql_generated,
                "data": records
            }

        except Exception as sql_err:
            logger.error(f"Error al ejecutar SQL de IA: {sql_err}")
            return {
                "thought": thought,
                "response": f"Se generó una consulta SQL pero falló al ejecutarse. Error: {str(sql_err)}",
                "sql": sql_generated,
                "data": None
            }

    except Exception as e:
        logger.error(f"Error en ask_agent: {e}")
        return {
            "thought": "Excepción en el backend del agente.",
            "response": f"Ocurrió un error inesperado al procesar tu solicitud: {str(e)}",
            "sql": None,
            "data": None
        }
