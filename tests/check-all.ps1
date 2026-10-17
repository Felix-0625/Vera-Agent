$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root 'vera-agent\.venv\Scripts\python.exe'
$scripts = Join-Path $root 'vera-agent\.venv\Scripts'
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue

if (-not (Test-Path $python)) { throw "Python test environment missing: $python. See docs/DEVELOPMENT.md." }
if (-not $npm) { throw 'npm was not found. Install Node.js 20+ before running frontend checks.' }
$env:PATH = "$scripts;$env:PATH"

Write-Host '== Backend pytest ==' -ForegroundColor Cyan
Push-Location (Join-Path $root 'vera-agent')
try {
    & $python -m pytest tests
    if ($LASTEXITCODE -ne 0) { throw "Backend tests failed with exit code $LASTEXITCODE." }
} finally { Pop-Location }

Write-Host '== MCP example stdio smoke check ==' -ForegroundColor Cyan
Push-Location $root
try {
    & $python examples\mcp-server\test_client.py
    if ($LASTEXITCODE -ne 0) { throw "MCP example check failed with exit code $LASTEXITCODE." }
} finally { Pop-Location }

Write-Host '== Static website links and assets ==' -ForegroundColor Cyan
Push-Location $root
try {
    & $python website\check_site.py
    if ($LASTEXITCODE -ne 0) { throw "Static website validation failed with exit code $LASTEXITCODE." }
} finally { Pop-Location }

Write-Host '== Frontend lint ==' -ForegroundColor Cyan
Push-Location (Join-Path $root 'frontend')
try {
    & $npm.Source run lint
    if ($LASTEXITCODE -ne 0) { throw "Frontend lint failed with exit code $LASTEXITCODE." }

    Write-Host '== Frontend production build ==' -ForegroundColor Cyan
    & $npm.Source run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed with exit code $LASTEXITCODE." }
} finally { Pop-Location }

Write-Host 'All configured repository checks passed.' -ForegroundColor Green
