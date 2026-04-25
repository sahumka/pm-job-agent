param(
  [string]$DbPath = "data/jobs.db"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupRoot = Join-Path "outputs" "backups"
$dest = Join-Path $backupRoot $stamp
New-Item -ItemType Directory -Path $dest -Force | Out-Null

if (Test-Path $DbPath) {
  Copy-Item -Path $DbPath -Destination (Join-Path $dest "jobs.db")
}
if (Test-Path "config\target_companies.csv") {
  Copy-Item -Path "config\target_companies.csv" -Destination (Join-Path $dest "target_companies.csv")
}
if (Test-Path "config\users") {
  Copy-Item -Path "config\users" -Destination (Join-Path $dest "users") -Recurse -Force
}
if (Test-Path "outputs\url_validation") {
  Copy-Item -Path "outputs\url_validation" -Destination (Join-Path $dest "url_validation") -Recurse -Force
}

Write-Host "Backup created at $dest"
