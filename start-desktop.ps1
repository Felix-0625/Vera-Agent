$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$backendProcess = $null
$backendReady = $false
$frontend = Join-Path $root 'frontend'
$python = Join-Path $root 'vera-agent\.venv\Scripts\python.exe'

try {
    if (-not (Test-Path $python)) { throw "找不到后端 Python 环境：$python" }
    & $python -c 'import webview'
    if ($LASTEXITCODE -ne 0) { throw '未安装桌面窗口依赖，请在 vera-agent 目录运行：uv sync --locked --no-dev --extra desktop' }

    Push-Location $frontend
    try {
        npm run build:desktop
        if ($LASTEXITCODE -ne 0) { throw "桌面前端构建失败，代码：$LASTEXITCODE" }
    } finally { Pop-Location }

    if (-not (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)) {
        $backendProcess = Start-Process -FilePath $python `
            -ArgumentList @('-m', 'uvicorn', 'vera_agent.server.app:create_app', '--factory', '--host', '127.0.0.1', '--port', '8000') `
            -WorkingDirectory (Join-Path $root 'vera-agent') `
            -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $env:TEMP 'vera-agent-desktop-backend.log') `
            -RedirectStandardError (Join-Path $env:TEMP 'vera-agent-desktop-backend-error.log')
    }

    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/topology' -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $backendReady = $true; break }
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $backendReady) { throw '后端 8000 端口未就绪，请查看 %TEMP%\vera-agent-desktop-backend-error.log' }

    Push-Location (Join-Path $root 'vera-agent')
    try {
        & $python -m vera_agent.desktop
        if ($LASTEXITCODE -ne 0) { throw "桌面窗口异常退出，代码：$LASTEXITCODE" }
    } finally { Pop-Location }
} finally {
    if ($backendProcess -and -not $backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue }
}
