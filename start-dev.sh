#!/usr/bin/env bash
set -e

echo "========================================="
echo "        INITIALIZING JARVIS CORE         "
echo "========================================="

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
BACKEND_DIR="$DIR/AI/Backend/DR-doom-Day-2-Backend"
FRONTEND_DIR="$DIR/jarvis-frontend"

# Check Python environment
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed."
    exit 1
fi

# Check Node environment
if ! command -v npm &> /dev/null; then
    echo "Node.js / npm is required but not installed."
    exit 1
fi

echo "[1/2] Launching FastAPI Backend on http://127.0.0.1:8765..."
(cd "$BACKEND_DIR" && python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload) &
BACKEND_PID=$!

echo "[2/2] Launching React Frontend..."
(cd "$FRONTEND_DIR" && npm run dev) &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT

echo "JARVIS is online. Press Ctrl+C to stop all services."
wait
