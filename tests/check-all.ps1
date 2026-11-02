$ErrorActionPreference = 'Stop'
# Runs every repository check in CI order. Does not install dependencies or call model APIs.
$root = Split-Path -Parent $PSScriptRoot
$scripts = Join-Path $root 'vera-agent\.venv\Scripts'
$python = Join-Path $scripts 'python.exe'
$ruff = Join-Path $scripts 'ruff.exe'
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue

if (-not (Test-Path $python)) { throw "Python environment missing: $python. See docs/DEVELOPMENT.md." }
if (-not (Test-Path $ruff)) { throw "ruff missing. Install dev dependencies: uv sync --locked --extra desktop --extra dev" }
if (-not $npm) { throw 'npm was not found. Install Node.js 24 (or 20.19+ / 22.12+) before running frontend checks.' }
$env:PATH = "$scripts;$env:PATH"

function Invoke-Step([string]$Title, [string]$Directory, [scriptblock]$Command) {
    Write-Host "== $Title ==" -ForegroundColor Cyan
    Push-Location (Join-Path $root $Directory)
    try {
        & $Command
        if ($LASTEXITCODE -ne 0) { throw "$Title failed with exit code $LASTEXITCODE." }
    } finally { Pop-Location }
}

Invoke-Step 'Backend lint and format' 'vera-agent' { & $ruff check src tests; if ($LASTEXITCODE -eq 0) { & $ruff format --check src tests } }
Invoke-Step 'Backend tests' 'vera-agent' { & $python -m pytest tests }
Invoke-Step 'Repository lint and format' '.' { & $ruff check .; if ($LASTEXITCODE -eq 0) { & $ruff format --check . } }
Invoke-Step 'Repository tests (examples, docs, hygiene)' '.' { & $python -m pytest tests }
Invoke-Step 'MCP example stdio smoke check' '.' { & $python examples\mcp-server\test_client.py }
Invoke-Step 'Static website links and assets' '.' { & $python website\check_site.py }
Invoke-Step 'Frontend lint' 'frontend' { & $npm.Source run lint }
Invoke-Step 'Frontend formatting' 'frontend' { & $npm.Source run format:check }
Invoke-Step 'Frontend unit tests' 'frontend' { & $npm.Source test }
Invoke-Step 'Frontend production build' 'frontend' { & $npm.Source run build }

Write-Host 'All repository checks passed.' -ForegroundColor Green
