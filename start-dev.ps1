# ==============================================================================
# JARVIS 2.0 - Full-Stack Launcher (Backend & Frontend)
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "        INITIALIZING JARVIS CORE         " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backendDir  = Join-Path $root "backend"
$frontendDir = Join-Path $root "jarvis-frontend"

# Resolve Python: prefer backend venv -> root venv -> system Python
$backendVenvPy = Join-Path $backendDir ".venv\Scripts\python.exe"
$rootVenvPy    = Join-Path $root ".venv\Scripts\python.exe"

if (Test-Path $backendVenvPy) {
    $pythonExe = $backendVenvPy
    Write-Host "Using backend venv Python: $pythonExe" -ForegroundColor DarkGray
} elseif (Test-Path $rootVenvPy) {
    $pythonExe = $rootVenvPy
    Write-Host "Using root venv Python: $pythonExe" -ForegroundColor DarkGray
} else {
    $pythonExe = "python"
    Write-Host "Using system Python (no venv found)" -ForegroundColor Yellow
}

# 1. Launch FastAPI Backend
Write-Host "[1/2] Starting FastAPI Backend on http://127.0.0.1:8765 ..." -ForegroundColor Green
$backendCmd = "Set-Location '$backendDir'; & '$pythonExe' -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# Brief pause so the backend binds its port before Vite starts making proxy calls
Start-Sleep -Seconds 2

# 2. Launch React + Vite Frontend
Write-Host "[2/2] Starting React + Vite Frontend on http://localhost:1420 ..." -ForegroundColor Green
$frontendCmd = "Set-Location '$frontendDir'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# Wait for Vite dev server to initialize, then launch the HUD in browser
Start-Sleep -Seconds 2
try {
    Start-Process "http://localhost:1420"
} catch {
    # Non-blocking if running headless
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   JARVIS is now online and operational!   " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Frontend HUD  : http://localhost:1420"     -ForegroundColor Yellow
Write-Host "  Backend API   : http://127.0.0.1:8765/api/health" -ForegroundColor Yellow
Write-Host "  Swagger Docs  : http://127.0.0.1:8765/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "  TIP: Close the two terminal windows to stop JARVIS." -ForegroundColor DarkGray
