$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$frontend = Join-Path $root 'frontend'
$python = Join-Path $root 'vera-agent\.venv\Scripts\python.exe'

if (-not (Test-Path $python)) { throw "找不到后端 Python 环境：$python" }
& $python -c 'import webview'
if ($LASTEXITCODE -ne 0) { throw '未安装桌面窗口依赖，请在 vera-agent 目录运行：uv sync --locked --no-dev --extra desktop' }

# 前端构建产物由 vera_agent.desktop 启动的本机 API 托管，界面与 API 同源，端口自动选择（8000 起）。
Push-Location $frontend
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "桌面前端构建失败，代码：$LASTEXITCODE" }
} finally { Pop-Location }

Push-Location (Join-Path $root 'vera-agent')
try {
    & $python -m vera_agent.desktop
    if ($LASTEXITCODE -ne 0) { throw "桌面窗口异常退出，代码：$LASTEXITCODE" }
} finally { Pop-Location }
