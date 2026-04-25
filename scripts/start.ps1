$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

Write-Host "Installing dependencies..."
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "Initializing database..."
& ".\.venv\Scripts\python.exe" -c "from src.db import init_db; init_db('data/jobs.db'); print('DB initialized')"

Write-Host "Starting Streamlit dashboard..."
& ".\.venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8513
