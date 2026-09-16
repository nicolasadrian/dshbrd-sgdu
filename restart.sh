#!/usr/bin/env bash
set -e

# Directorio base del script
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================="
echo "INICIANDO TABLERO SGDU - AMBIENTE LINUX"
echo "=========================================="

# 1. Detener procesos previos
echo "[1/4] Deteniendo procesos previos en puertos 8000 y 3000..."
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 3000/tcp 2>/dev/null || true
sleep 1

# 2. Verificar servicio de PostgreSQL
echo "[2/4] Verificando PostgreSQL..."
if ! pg_isready -q; then
    echo "Iniciando servicio PostgreSQL..."
    echo lenovo | sudo -S systemctl start postgresql
fi

# 3. Iniciar Backend
echo "[3/4] Iniciando Backend en segundo plano (puerto 8000)..."
"$PROJECT_DIR/venv/bin/uvicorn" main:app --app-dir "$PROJECT_DIR/backend" --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Esperar a que el backend esté listo
echo "Esperando que el backend responda..."
for i in {1..15}; do
    if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
        echo "Backend listo en http://localhost:8000"
        break
    fi
    sleep 1
done

# 4. Iniciar Frontend
echo "[4/4] Iniciando Frontend (puerto 3000)..."
echo "Para detener ambos servicios presione Ctrl+C"

trap "echo 'Deteniendo servicios...'; kill $BACKEND_PID 2>/dev/null || true; exit 0" SIGINT SIGTERM EXIT

cd "$PROJECT_DIR/frontend"
npx vite --host 0.0.0.0 --port 3000
