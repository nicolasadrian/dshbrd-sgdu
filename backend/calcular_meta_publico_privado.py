import os
import sys
from datetime import datetime, date
import psycopg2
from dotenv import load_dotenv

# Cargar configuración del .env
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

try:
    from deploy.notifier_telegram import send_telegram_alert
except ImportError:
    from notifier_telegram import send_telegram_alert

LOCAL_DB_URL = os.getenv("DATABASE_URL_LOCAL", "postgresql://postgres:lenovo@localhost:5432/sade_db")
PROD_DB_URL = os.getenv("DATABASE_URL_PUBLIC") or os.getenv("DATABASE_URL")

def get_dias_laborables(anio: int, mes: int) -> int:
    """Calcula la cantidad de días hábiles (lunes a viernes) en un mes determinado."""
    import calendar
    _, total_dias = calendar.monthrange(anio, mes)
    dias_habiles = 0
    for d in range(1, total_dias + 1):
        # 0 = Lunes, 4 = Viernes, 5 = Sábado, 6 = Domingo
        if date(anio, mes, d).weekday() < 5:
            dias_habiles += 1
    return dias_habiles

def calcular_y_guardar_meta(anio: int = None, mes: int = None, meses_ventana: int = 2):
    """
    Calcula la meta del mes para Público Privado:
      Meta = Promedio de ingresos mensuales de los últimos 2 meses concluidos.
    Analistas contemplados: NDEFAVERI, NARGANDONAJULIO, DGIUR-GERENCIAPPP, E.SALERNO, JOSPINASUAREZ, AESCOBARDELCID, EWILLIAN.
    Guarda el resultado en metas_productividad_ppp tanto en LOCAL como en PRODUCCIÓN.
    """
    hoy = date.today()
    if anio is None: anio = hoy.year
    if mes is None: mes = hoy.month

    target_mes_label = f"{anio}-{mes:02d}"
    print(f"================================================================================")
    print(f"   CÁLCULO AUTOMÁTICO DE META DE PRODUCTIVIDAD - PÚBLICO PRIVADO ({target_mes_label})")
    print(f"================================================================================")

    analistas_ppp = [
        "NDEFAVERI", "NARGANDONAJULIO", "DGIUR-GERENCIAPPP",
        "E.SALERNO", "JOSPINASUAREZ", "AESCOBARDELCID", "EWILLIAN"
    ]

    # Conectar a Producción para extraer el histórico más certero
    db_source_url = PROD_DB_URL or LOCAL_DB_URL
    if not db_source_url:
        print("[ERROR] No hay URL de base de datos configurada.")
        return

    conn_source = psycopg2.connect(db_source_url)
    with conn_source.cursor() as cur:
        # 1. Extraer los últimos N meses concluidos (excluyendo el mes en curso)
        cur.execute("""
            SELECT mes_label,
                   COUNT(DISTINCT CASE WHEN tipo_evento = 'ING' THEN id_expediente END) as cant_ingresos,
                   COUNT(DISTINCT CASE WHEN tipo_evento = 'EGR' THEN id_expediente END) as cant_egresos
            FROM mvw_publico_privado_produccion
            WHERE analista = ANY(%s)
              AND mes_label < %s
            GROUP BY mes_label
            ORDER BY mes_label DESC
            LIMIT %s;
        """, (analistas_ppp, target_mes_label, meses_ventana))
        rows = cur.fetchall()

        # 2. Extraer el stock propio actual en poder de los analistas de PPP
        cur.execute("""
            SELECT 
                COUNT(*) - COUNT(CASE WHEN EXISTS (
                    SELECT 1 FROM mvw_ee_actividades_secgdu a
                    WHERE a.id_expediente = up.id_expediente
                      AND a.usuario_alta = up.destinatario_actual
                      AND a.estado = 'PENDIENTE'
                      AND a.nombre_tipo_actividad = 'SOLICITUD_SUBSANACION_TAD'
                ) THEN 1 END) as stock_propio
            FROM mv_ultimo_pase up
            WHERE up.destinatario_actual = ANY(%s);
        """, (analistas_ppp,))
        stock_propio_actual = int(cur.fetchone()[0] or 0)

    conn_source.close()

    if not rows:
        print("  [!] No se encontraron meses anteriores para promediar. Usando valor por defecto (75).")
        promedio_ing = 90.0
        promedio_egr = 75.0
        meta = 75
    else:
        # Orden cronológico para mostrar
        rows_cron = sorted(rows, key=lambda x: x[0])
        ingresos_list = [r[1] for r in rows_cron]
        egresos_list = [r[2] for r in rows_cron]
        
        promedio_ing = sum(ingresos_list) / len(ingresos_list)
        promedio_egr = sum(egresos_list) / len(egresos_list)
        meta = int(round(promedio_egr))

        print(f"  Historial considerado ({len(rows_cron)} últimos meses concluidos):")
        for m_lbl, cant_in, cant_out in rows_cron:
            print(f"    - {m_lbl}: Ingresos = {cant_in}, Egresos = {cant_out}")
        print(f"  --> Promedio ingresos ({len(rows_cron)} meses): {promedio_ing:.1f} expedientes/mes")
        print(f"  --> Promedio egresos ({len(rows_cron)} meses): {promedio_egr:.1f} expedientes/mes")
        print(f"  --> Stock propio actual de referencia: {stock_propio_actual} expedientes")
        print(f"  --> META FINAL DE EGRESOS: {meta} (Promedio de egresos últimos {len(rows_cron)} meses completos)")

    dias_lab = get_dias_laborables(anio, mes)
    obs = (
        f"Meta = Promedio de Egresos de los últimos {len(rows)} meses completos ({promedio_egr:.1f} exp/mes)."
    )

    upsert_sql = """
        INSERT INTO public.metas_productividad_ppp 
        (anio, mes, mes_label, dias_laborables_mes, meta_egresos, promedio_historico_base, 
         promedio_ingresos, stock_propio_base, pct_reduccion_stock, meses_muestra, observaciones, fecha_calculo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (anio, mes) DO UPDATE SET
            dias_laborables_mes = EXCLUDED.dias_laborables_mes,
            meta_egresos = EXCLUDED.meta_egresos,
            promedio_historico_base = EXCLUDED.promedio_historico_base,
            promedio_ingresos = EXCLUDED.promedio_ingresos,
            stock_propio_base = EXCLUDED.stock_propio_base,
            pct_reduccion_stock = EXCLUDED.pct_reduccion_stock,
            meses_muestra = EXCLUDED.meses_muestra,
            observaciones = EXCLUDED.observaciones,
            fecha_calculo = CURRENT_TIMESTAMP;
    """

    targets = [("LOCAL", LOCAL_DB_URL), ("PRODUCCION", PROD_DB_URL)]
    for env_name, url in targets:
        if not url: continue
        try:
            with psycopg2.connect(url) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(upsert_sql, (
                        anio, mes, target_mes_label, dias_lab, meta, round(promedio_egr, 2),
                        round(promedio_ing, 2), stock_propio_actual, 0.0,
                        len(rows), obs
                    ))
            print(f"  [OK] Guardado en {env_name}.")
        except Exception as e:
            print(f"  [!] Error al guardar en {env_name}: {e}")

    # Notificación a Telegram
    send_telegram_alert(
        f"🎯 *Meta Actualizada - Público Privado*\n"
        f"📅 Período: *{target_mes_label}*\n"
        f"🎯 *Meta Egresos:* *{meta}*\n"
        f"📊 Base: Promedio de egresos de los últimos 2 meses completos ({promedio_egr:.1f} exp/mes)\n"
        f"🗓 Días hábiles del mes: {dias_lab}"
    )

if __name__ == "__main__":
    calcular_y_guardar_meta()
