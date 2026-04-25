$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Missing virtual environment. Run scripts/start.ps1 once first."
}

& ".\.venv\Scripts\python.exe" -m src.run_hourly `
  --companies-csv config/target_companies.csv `
  --linkedin-csv config/linkedin_jobs.csv `
  --manual-jobs-csv config/manual_jobs.csv `
  --db-path data/jobs.db `
  --summary-path outputs/hourly_summary.json
