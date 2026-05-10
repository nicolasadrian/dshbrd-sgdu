@echo off
echo ==========================================
echo REINICIANDO TODO EL SISTEMA SGDU
echo ==========================================

echo [1/3] Finalizando procesos de Python (Backend)...
taskkill /F /IM python.exe /T 2>nul

echo [2/3] Liberando bloqueos en la base de datos...
python scratch\kill_db_sessions.py

echo [3/3] Iniciando Backend...
start "SGDU BACKEND" cmd /k "python backend\main.py"

echo ==========================================
echo REINICIO COMPLETADO. Verifique el tablero en el navegador.
echo ==========================================
pause
