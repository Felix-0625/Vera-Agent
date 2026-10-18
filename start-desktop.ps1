$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$backendProcess = $null
$backendReady = $false
$backendPort = 8000
$desktopApiBaseUrl = $env:VITE_API_BASE_URL
$reuseBackend = $false
$frontend = Join-Path $root 'frontend'
$python = Join-Path $root 'vera-agent\.venv\Scripts\python.exe'

try {
    if (-not (Test-Path $python)) { throw "找不到后端 Python 环境：$python" }
    & $python -c 'import webview'
    if ($LASTEXITCODE -ne 0) { throw '未安装桌面窗口依赖，请在 vera-agent 目录运行：uv sync --locked --no-dev --extra desktop' }

    $port8000Listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($port8000Listener) {
        try {
            $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/topology' -TimeoutSec 2
            $reuseBackend = $response.StatusCode -eq 200
        } catch { $reuseBackend = $false }

        if (-not $reuseBackend) {
            $freePort = 8001..8100 | Where-Object {
                -not (Get-NetTCPConnection -LocalPort $_ -State Listen -ErrorAction SilentlyContinue)
            } | Select-Object -First 1
            if (-not $freePort) { throw 'VeraAgent 需要的后端端口 8000 已被其他服务占用，且 8001–8100 没有可用端口。' }
            $backendPort = $freePort
        }
    }

    $env:VITE_API_BASE_URL = "http://127.0.0.1:$backendPort"
    Push-Location $frontend
    try {
        npm run build:desktop
        if ($LASTEXITCODE -ne 0) { throw "桌面前端构建失败，代码：$LASTEXITCODE" }
    } finally { Pop-Location }

    if (-not $reuseBackend) {
        $backendProcess = Start-Process -FilePath $python `
            -ArgumentList @('-m', 'uvicorn', 'vera_agent.server.app:create_app', '--factory', '--host', '127.0.0.1', '--port', "$backendPort") `
            -WorkingDirectory (Join-Path $root 'vera-agent') `
            -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $env:TEMP 'vera-agent-desktop-backend.log') `
            -RedirectStandardError (Join-Path $env:TEMP 'vera-agent-desktop-backend-error.log')
    }

    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:$backendPort/api/topology" -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $backendReady = $true; break }
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $backendReady) { throw "后端端口 $backendPort 未就绪，请查看 %TEMP%\vera-agent-desktop-backend-error.log" }

    Push-Location (Join-Path $root 'vera-agent')
    try {
        & $python -m vera_agent.desktop
        if ($LASTEXITCODE -ne 0) { throw "桌面窗口异常退出，代码：$LASTEXITCODE" }
    } finally { Pop-Location }
} finally {
    $env:VITE_API_BASE_URL = $desktopApiBaseUrl
    if ($backendProcess -and -not $backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue }
}
