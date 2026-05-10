import subprocess
import os
import sys
import time

def run_command(command, description):
    print(f"\n>>> {description}...", flush=True)
    try:
        # Usamos check_call para asegurar que si falla, el script se detenga
        subprocess.check_call([sys.executable] + command)
    except subprocess.CalledProcessError as e:
        print(f"\n[!] Error en {description}: {e}")
        sys.exit(1)

def kill_previous_etl():
    print(">>> Buscando procesos de ETL previos...")
    try:
        # Comando para encontrar PIDs de python que corren etl_sade.py
        ps_cmd = "Get-CimInstance Win32_Process -Filter \"CommandLine LIKE '%etl_sade.py%'\" | Select-Object ProcessId | ConvertTo-Json"
        result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
        
        if result.stdout.strip():
            import json
            data = json.loads(result.stdout)
            pids = []
            if isinstance(data, dict):
                pids.append(data["ProcessId"])
            elif isinstance(data, list):
                pids = [item["ProcessId"] for item in data]
            
            for pid in pids:
                print(f"  Killing PID {pid}")
                subprocess.run(["taskkill", "/F", "/PID", str(pid)])
                time.sleep(1)
    except Exception as e:
        print(f"  [!] Error al limpiar procesos: {e}")

def main():
    print("==========================================")
    print("INICIANDO FLUJO COMPLETO DE ACTUALIZACIÓN")
    print("==========================================")
    
    # 1. Limpieza
    kill_previous_etl()
    
    # 2. Copia de datos (Oracle -> Postgres)
    run_command(["etl_sade.py"], "Ejecutando copia de datos desde SADE (Oracle)")
    
    # 3. Refresco de Vistas Materializadas
    run_command(["scratch/refresh_views.py"], "Refrescando Vistas Materializadas en Postgres")
    
    print("\n==========================================")
    print("ACTUALIZACIÓN FINALIZADA CORRECTAMENTE")
    print("==========================================")

if __name__ == "__main__":
    main()
