# ================================================================
# run.ps1 -- Dev launcher for the full LinkedIn automation stack
# ================================================================
# Usage: .\run.ps1
# Run from the project root directory.
# Starts: n8n (WSL2, new window) + FastAPI microservice (this window)
# ================================================================

$ROOT = $PSScriptRoot
$VENV = Join-Path $ROOT ".venv"
$PYTHON = Join-Path $VENV "Scripts\python.exe"
$PIP    = Join-Path $VENV "Scripts\pip.exe"
$ACTIVATE = Join-Path $VENV "Scripts\Activate.ps1"

# ------------------------------------------------
# Step 1 -- ensure .venv exists
# ------------------------------------------------
if (-not (Test-Path $VENV)) {
    Write-Host "[INFO] .venv not found -- building virtual environment with Python 3.12..."
    py -3.12 -m venv $VENV
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[ERROR] Failed to create .venv. Is Python 3.12 installed? Run: py -3.12 --version"
        exit 1
    }
    Write-Host "[INFO] .venv created."
}

# ------------------------------------------------
# Step 2 -- activate
# ------------------------------------------------
Write-Host "[INFO] Activating .venv..."
. $ACTIVATE

# ------------------------------------------------
# Step 3 -- install requirements
# ------------------------------------------------
if (-not (Test-Path (Join-Path $ROOT "requirements.txt"))) {
    Write-Error "[ERROR] requirements.txt not found in project root."
    exit 1
}
Write-Host "[INFO] Installing requirements from requirements.txt..."
& $PIP install -r (Join-Path $ROOT "requirements.txt") --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Error "[ERROR] pip install failed."
    exit 1
}

# ------------------------------------------------
# Step 4 -- start n8n in WSL2 (new window) if not already running
# ------------------------------------------------
$n8nRunning = Test-NetConnection -ComputerName localhost -Port 5678 -InformationLevel Quiet -WarningAction SilentlyContinue
if ($n8nRunning) {
    Write-Host "[INFO] n8n already running at http://localhost:5678 -- skipping launch."
} else {
    Write-Host "[INFO] Opening WSL terminal -- run 'n8n start' in the Ubuntu tab to start n8n."
    Start-Process wt -ArgumentList "wsl"
    Write-Host "[INFO] Waiting for n8n to initialize (start it in the WSL tab, then wait ~6s)..."
    Start-Sleep -Seconds 6
}
Write-Host "[INFO] Opening n8n dashboard in default browser..."
Start-Process "http://localhost:5678"

# ------------------------------------------------
# Step 5 -- launch main.py via uvicorn
# ------------------------------------------------
$MAIN = Join-Path $ROOT "main.py"
if (-not (Test-Path $MAIN)) {
    Write-Error "[ERROR] main.py not found -- Stage 2 not yet complete."
    exit 1
}
Write-Host "[INFO] Starting FastAPI microservice on http://0.0.0.0:8000 ..."
& $PYTHON -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# © 2026 Brock Frary. All rights reserved.
