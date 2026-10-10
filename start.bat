@echo off
chcp 65001 >nul
echo ========================================================
echo          VeraAgent 一键启动程序 (Backend + Frontend)
echo ========================================================

cd /d "%~dp0vera-agent"
echo [*] 正在启动后端核心服务 (Port 8000)...
start "VeraAgent Backend (Port 8000)" .\.venv\Scripts\python.exe -m uvicorn vera_agent.server.app:create_app --factory --host 127.0.0.1 --port 8000

cd /d "%~dp0frontend"
echo [*] 正在启动前端开发服务 (Port 5173)...
start "VeraAgent Frontend (Port 5173)" cmd /c "npm run dev"

timeout /t 2 >nul
echo ========================================================
echo [✔] 启动指令已发送！
echo     后端服务: http://127.0.0.1:8000
echo     前端界面: http://localhost:5173
echo ========================================================

start http://localhost:5173
