# ==============================================================================
# JARVIS — Full-Stack Launcher (Backend & Frontend)
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "        INITIALIZING JARVIS CORE         " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$root = $PSScriptRoot
$backendDir = Join-Path $root "AI\Backend\DR-doom-Day-2-Backend"
$frontendDir = Join-Path $root "jarvis-frontend"

# 1. Launch FastAPI Backend
Write-Host "[1/2] Starting FastAPI Backend on port 8765..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendDir'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload"

# 2. Launch React + Vite Frontend
Write-Host "[2/2] Starting React + Vite Frontend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; npm run dev"

Write-Host "`nJARVIS is now online and operational!" -ForegroundColor Cyan
Write-Host "Backend API Health: http://127.0.0.1:8765/api/health" -ForegroundColor Yellow
Write-Host "Backend Docs (Swagger): http://127.0.0.1:8765/docs" -ForegroundColor Yellow
Write-Host "Frontend HUD:       http://localhost:5173" -ForegroundColor Yellow
