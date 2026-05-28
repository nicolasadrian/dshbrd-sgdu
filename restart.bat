@echo off
echo ==========================================
echo REINICIANDO TODO EL SISTEMA SGDU
echo ==========================================

echo [1/3] Finalizando procesos de Python (Backend)...
taskkill /F /IM python.exe /T 2>nul

echo [2/3] Liberando bloqueos en la base de datos...
python scratch\kill_db_sessions.py

echo [3/4] Iniciando Backend...
start "SGDU BACKEND" cmd /k "python backend\main.py"

echo [4/4] Iniciando Frontend...
start "SGDU FRONTEND" cmd /k "python -m http.server 3000 --directory frontend"

echo ==========================================
echo REINICIO COMPLETADO. Abra http://localhost:3000 en su navegador.
echo ==========================================
pause
