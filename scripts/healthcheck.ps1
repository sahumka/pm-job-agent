param(
  [string]$DbPath = "data/jobs.db",
  [string]$OutputJson = "outputs/healthcheck.json"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  Write-Error "Virtual environment not found. Run: python -m venv .venv"
}

& ".\.venv\Scripts\python.exe" -m src.healthcheck --db-path $DbPath --output-json $OutputJson
