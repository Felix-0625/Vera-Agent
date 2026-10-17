param(
    [string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'VeraAgent\app')
)

$ErrorActionPreference = 'Stop'
$repository = 'https://github.com/Felix-0625/Agents.git'
$branch = 'main'

function Stop-Install([string]$Message) {
    Write-Error $Message
    exit 1
}

if (-not $env:LOCALAPPDATA) { Stop-Install '无法确定 Windows 用户本地应用数据目录。' }
$git = Get-Command git.exe -ErrorAction SilentlyContinue
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
$py = Get-Command py.exe -ErrorAction SilentlyContinue
$python = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $git) { Stop-Install '请先安装 Git for Windows，并确保 git.exe 已加入 PATH。' }
if (-not $npm) { Stop-Install '请先安装 Node.js 20 或更高版本（包含 npm）。' }
if (-not ($py -or $python)) { Stop-Install '请先安装 Python 3.10 或更高版本。' }

if ($py) {
    $pythonCommand = $py.Source
    $pythonPrefix = @('-3')
} else {
    $pythonCommand = $python.Source
    $pythonPrefix = @()
}
$pythonVersion = & $pythonCommand @pythonPrefix -c 'import sys; print("%d.%d" % sys.version_info[:2])'
if ($LASTEXITCODE -ne 0) { Stop-Install '无法启动 Python。' }
if ([version]$pythonVersion -lt [version]'3.10') { Stop-Install "检测到 Python $pythonVersion；需要 Python 3.10 或更高版本。" }

Write-Host ''
Write-Host 'VeraAgent Windows 桌面版将执行以下操作：' -ForegroundColor Cyan
Write-Host "  源码目录：$InstallDirectory"
Write-Host '  更新/克隆 Felix-0625/Agents 的 main 分支'
Write-Host '  使用仓库 uv.lock 安装锁定的 Python 桌面依赖'
Write-Host '  使用 npm ci 安装前端锁定依赖，然后启动 pywebview 桌面应用'
Write-Host '  依赖下载需要网络；不会写入系统级 Python 或 npm 全局目录。'
Write-Host ''
$answer = Read-Host '继续吗？输入 Y 继续，其他输入取消'
if ($answer -notin @('Y', 'y')) { Write-Host '已取消。'; exit 0 }

$InstallDirectory = [System.IO.Path]::GetFullPath($InstallDirectory)
$parent = Split-Path -Parent $InstallDirectory
New-Item -ItemType Directory -Force -Path $parent | Out-Null

if (-not (Test-Path (Join-Path $InstallDirectory '.git'))) {
    if (Test-Path $InstallDirectory) {
        $existing = Get-ChildItem -Force -LiteralPath $InstallDirectory -ErrorAction SilentlyContinue
        if ($existing) { Stop-Install "安装目录已存在且不是 VeraAgent Git 仓库；为保护现有文件，不会覆盖：$InstallDirectory" }
    } else {
        New-Item -ItemType Directory -Force -Path $InstallDirectory | Out-Null
    }
    & $git.Source clone --depth 1 --branch $branch $repository $InstallDirectory
    if ($LASTEXITCODE -ne 0) { Stop-Install '克隆 VeraAgent 源码失败。' }
} else {
    $origin = & $git.Source -C $InstallDirectory remote get-url origin
    if ($LASTEXITCODE -ne 0 -or $origin.TrimEnd('/') -ne 'https://github.com/Felix-0625/Agents.git') {
        Stop-Install "安装目录的 Git 远程地址与 VeraAgent 不匹配；为保护现有仓库，不会更新：$InstallDirectory"
    }
    $changes = & $git.Source -C $InstallDirectory status --porcelain --untracked-files=no
    if ($LASTEXITCODE -ne 0) { Stop-Install '无法检查安装目录的 Git 状态。' }
    if ($changes) { Stop-Install '安装目录有未提交的受跟踪文件修改。请先备份并处理后再运行更新；引导程序不会重置或覆盖它们。' }
    & $git.Source -C $InstallDirectory pull --ff-only origin $branch
    if ($LASTEXITCODE -ne 0) { Stop-Install '更新 VeraAgent 源码失败；现有文件和数据已保留。' }
}

$frontend = Join-Path $InstallDirectory 'frontend'
$backend = Join-Path $InstallDirectory 'vera-agent'
if (-not (Test-Path (Join-Path $frontend 'package-lock.json'))) { Stop-Install '源码中缺少前端锁文件 package-lock.json。' }
if (-not (Test-Path (Join-Path $backend 'pyproject.toml'))) { Stop-Install '源码中缺少 Python 项目配置 pyproject.toml。' }

Push-Location $backend
try {
    $bootstrapPython = Join-Path $backend '.bootstrap-venv\Scripts\python.exe'
    $uvExecutable = Join-Path $backend '.bootstrap-venv\Scripts\uv.exe'
    if (-not (Test-Path $uvExecutable)) {
        if (-not (Test-Path $bootstrapPython)) {
            & $pythonCommand @pythonPrefix -m venv .bootstrap-venv
            if ($LASTEXITCODE -ne 0) { Stop-Install '创建安装器工具环境失败。' }
        }
        & $bootstrapPython -m pip install 'uv==0.11.15'
        if ($LASTEXITCODE -ne 0) { Stop-Install '安装 Python 依赖管理器 uv 失败。' }
    }
    & $uvExecutable sync --locked --no-dev --extra desktop
    if ($LASTEXITCODE -ne 0) { Stop-Install '按 uv.lock 安装 Python 桌面依赖失败。' }
} finally { Pop-Location }

Push-Location $frontend
try {
    & $npm.Source ci
    if ($LASTEXITCODE -ne 0) { Stop-Install 'npm ci 安装前端依赖失败。' }
} finally { Pop-Location }

Write-Host '安装完成，正在启动 VeraAgent。关闭桌面窗口后启动脚本会结束。' -ForegroundColor Green
Push-Location $InstallDirectory
try {
    & (Join-Path $InstallDirectory 'start-desktop.ps1')
    if ($LASTEXITCODE -ne 0) { Stop-Install "桌面应用退出，代码：$LASTEXITCODE" }
} finally { Pop-Location }
