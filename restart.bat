@echo off
echo ==========================================
echo INICIANDO TABLERO SGDU - AMBIENTE LOCAL
echo ==========================================

echo [1/3] Deteniendo procesos previos...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul
timeout /t 2 /nobreak >nul

echo [2/3] Iniciando Backend (puerto 8000)...
start "SGDU BACKEND" cmd /k "cd /d %~dp0 && python backend\main.py"

timeout /t 3 /nobreak >nul

echo [3/3] Iniciando Frontend (puerto 3000)...
start "SGDU FRONTEND" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ==========================================
echo Servicios iniciados:
echo   Backend  -^> http://localhost:8000/api/health
echo   Frontend -^> http://localhost:3000
echo ==========================================
pause
