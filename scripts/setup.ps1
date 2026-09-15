# One-shot local environment setup for native Windows (PowerShell).
# See docs/GETTING_STARTED.md and docs/SETUP_WINDOWS.md for details and the
# recommended WSL2-based alternative.

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

Write-Host "==> Checking prerequisites"
foreach ($cmd in @("git", "python", "node", "docker")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "'$cmd' is not installed or not on PATH. See docs/SETUP_WINDOWS.md."
        exit 1
    }
}

Write-Host "==> Setting up .env"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example — edit it if you need non-default values."
} else {
    Write-Host ".env already exists, leaving it untouched."
}

Write-Host "==> Setting up backend virtual environment"
Set-Location "$RootDir\backend"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& ".venv\Scripts\Activate.ps1"
pip install --upgrade pip | Out-Null
pip install -r requirements.txt
deactivate

Write-Host "==> Installing frontend dependencies"
Set-Location "$RootDir\frontend"
npm install

Write-Host ""
Write-Host "Setup complete. Next steps:"
Write-Host "  1. Start the backend:  cd backend; .venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000"
Write-Host "  2. Start the frontend: cd frontend; npm run dev"
Write-Host "  3. (Optional) Pull an Ollama model: ollama pull llama3.1; ollama serve"
Write-Host "See docs/GETTING_STARTED.md for details."
