import os
import sys
import time
import subprocess

def run_script(filepath, index, total):
    filename = os.path.basename(filepath)
    print(f"\n" + "="*70)
    print(f"[{index}/{total}] INICIANDO: {filename}")
    print("="*70)
    
    start_time = time.time()
    
    # Configurar variables de entorno heredando las actuales
    env = os.environ.copy()
    # Agregar el directorio backend al PYTHONPATH
    backend_dir = os.path.dirname(filepath)
    env["PYTHONPATH"] = backend_dir
    
    # Iniciar subproceso capturando la salida en tiempo real
    process = subprocess.Popen(
        [sys.executable, filepath],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1  # line buffered
    )
    
    # Leer e imprimir la salida en tiempo real
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            # Imprimir línea con flush inmediato para ver progreso en vivo
            print(line.strip())
            
    # Esperar a que el proceso termine
    return_code = process.wait()
    duration = time.time() - start_time
    
    print("-"*70)
    if return_code == 0:
        print(f"COMPLETADO CON ÉXITO: {filename} (Duración: {duration:.2f}s)")
    else:
        print(f"FALLÓ CON CÓDIGO {return_code}: {filename} (Duración: {duration:.2f}s)")
    print("-"*70)
    
    return return_code == 0

def main():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Recopilar todos los scripts de importación de df_form_comp_value
    # Identificar todos los archivos que coinciden con el patrón
    all_files = [f for f in os.listdir(backend_dir) if f.startswith("import_df_form_comp_value") and f.endswith(".py")]
    
    # Asegurar un orden consistente de ejecución
    # Por ejemplo, primero el original (IFOCD) y luego el resto en orden alfabético
    all_files.sort(key=lambda x: (x != "import_df_form_comp_value.py", x))
    
    scripts = [os.path.join(backend_dir, f) for f in all_files]
    total_scripts = len(scripts)
    
    print("="*80)
    print(f"INICIANDO ORQUESTADOR DE IMPORTACIÓN MASIVA")
    print(f"Total de scripts detectados: {total_scripts}")
    print("="*80)
    
    success_count = 0
    start_global_time = time.time()
    
    for idx, script_path in enumerate(scripts, 1):
        success = run_script(script_path, idx, total_scripts)
        if success:
            success_count += 1
            
    total_duration = time.time() - start_global_time
    
    print("\n" + "="*80)
    print(f"RESUMEN GENERAL DE IMPORTACIÓN")
    print(f"Scripts ejecutados con éxito: {success_count}/{total_scripts}")
    print(f"Tiempo total transcurrido: {total_duration/60:.2f} minutos")
    print("="*80)

if __name__ == "__main__":
    main()
