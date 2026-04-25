$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Missing virtual environment. Run scripts/start.ps1 once first."
}

& ".\.venv\Scripts\python.exe" -m src.validate_targets `
  --input-csv config/target_companies.csv `
  --output-dir outputs/url_validation `
  --timeout 8 `
  --max-workers 32
