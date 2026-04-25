param(
  [string]$OutputDir = "outputs/releases"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$archivePath = Join-Path $OutputDir ("pm-job-copilot_{0}.zip" -f $stamp)

$include = @(
  "app.py",
  "README.md",
  "requirements.txt",
  "pyproject.toml",
  ".env.example",
  ".github",
  "components",
  "config",
  "scripts",
  "services",
  "src",
  "styles",
  "tests"
)

$staging = Join-Path $OutputDir ("staging_{0}" -f $stamp)
New-Item -ItemType Directory -Path $staging -Force | Out-Null

foreach ($path in $include) {
  if (Test-Path $path) {
    Copy-Item -Path $path -Destination (Join-Path $staging $path) -Recurse -Force
  }
}

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $archivePath -Force
Remove-Item -Path $staging -Recurse -Force

Write-Host "Release package created: $archivePath"
