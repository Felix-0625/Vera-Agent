# 快速开始

VeraAgent 目前在 Windows 10/11 上从 GitHub 源码启动。安装依赖需要访问 GitHub、npm 和 Python 包索引；模型服务是否可用取决于你自己的配置。

## 准备环境

| 依赖 | 版本或要求 |
| --- | --- |
| Windows | 10 或 11 |
| Git for Windows | 提供 Git，也为本地命令工具提供 Git Bash |
| Node.js | 推荐 24 LTS；支持 20.19+ 或 22.12+，带 npm |
| Python | 3.10 或更新 |
| uv | 0.11 或更新 |
| Microsoft Edge WebView2 Runtime | 用于桌面窗口 |

## 安装并启动

在 PowerShell 中执行：

```powershell
git clone https://github.com/Felix-0625/Vera-Agent.git
cd Vera-Agent\frontend
npm ci
cd ..\vera-agent
uv sync --locked --no-dev --extra desktop
cd ..
.\start-desktop.ps1
```

前端和 Python 依赖分别来自仓库锁文件。首次安装会下载依赖；脚本构建前端、启动本地 API，并打开桌面窗口。若 8000 端口被其他程序占用，脚本会在 8001–8100 中选择可用端口。也可在仓库根目录双击 `start.bat` 启动同一流程。

## 首次使用

1. 打开 **设置 → 模型**，添加模型服务并在应用内输入凭据。桌面应用不要求先写 `.env`。
2. 绑定一个本地软件项目目录。绑定只记录路径，不复制整个项目。
3. 在该项目下开始对话，先尝试只读任务，再按权限提示确认需要修改文件或执行命令的操作。
4. 想体验组织与流程，可按[项目使用指南](usage.md#自定义组织与工作流)操作，或使用仓库的[工作流示例](../../../examples/workflow-quickstart/README.md)。

## 再次启动与更新

完成安装后，从仓库根目录运行 `./start-desktop.ps1` 即可再次打开工作站。更新代码前先关闭应用并备份应用与项目的 `.agents/` 目录；当锁文件变化时重新运行 `npm ci` 和 `uv sync --locked --no-dev --extra desktop`。当前没有自动更新器。

遇到启动失败，先查[排错](troubleshooting.md)。安装步骤的维护基准是仓库的[Windows 安装说明](../../../docs/INSTALL_WINDOWS.md)。
