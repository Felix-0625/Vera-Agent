# VeraAgent PowerShell 启动脚本
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      VeraAgent 一键启动程序 (Backend + Frontend)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$root = $PSScriptRoot

Write-Host "[*] 正在启动后端服务 (Port 8000)..." -ForegroundColor Yellow
Start-Process -FilePath "$root\vera-agent\.venv\Scripts\python.exe" -ArgumentList "-m uvicorn vera_agent.server.app:create_app --factory --host 127.0.0.1 --port 8000" -WorkingDirectory "$root\vera-agent"

Write-Host "[*] 正在启动前端开发服务 (Port 5173)..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory "$root\frontend"

Start-Sleep -Seconds 2

Write-Host "[✔] 项目服务已启动！" -ForegroundColor Green
Write-Host "    后端地址: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "    前端地址: http://localhost:5173" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

Start-Process "http://localhost:5173"
