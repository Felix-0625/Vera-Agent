# VeraAgent

[English](README.md) | **简体中文**

VeraAgent 是面向软件项目的本地单用户 AI Agent 工作站：把项目任务看板、主 Agent 对话、子智能体、多 Agent 协作，以及**可自定义的工作流与组织架构**放在同一个桌面应用中。模板只需设计一次，就可以在项目中实例化，并从对话里直接调用。

Agent 内核基于 [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent)，工具设计沿用 Pi Agent 的极简思路（read、write、edit、bash 四个原语）。这里说明的是技术渊源，不代表上游项目为 VeraAgent 背书。

[![VeraAgent 交互演示预览](website/assets/video/demo-poster.png)](website/assets/video/veraagent-task-collaboration-demo.webm)

演示录像和[网站交互演示](website/playground/index.html)使用脚本数据，不连接模型、后端或访客的本地文件。

## 功能

- **项目**：绑定本地目录，在项目上下文中与 Agent 对话（可在设置中启用读取项目的 `AGENTS.md` 规则）。
- **任务看板**：跟踪项目工作项（待规划 → 已完成），并关联到对话。
- **子智能体**：主 Agent 可以把调研和评审委派给隔离的子智能体。
- **工作流与组织架构**：在可视化编辑器中搭建模板（对话窗口、是/否判断、循环），按项目填写目标和背景后实例化，在对话中确认后运行。每个节点使用独立会话，经 Supervisor 复核后结果回到发起对话。
- **工具**：文件浏览、Diff/暂存/检查点、Git 分支、终端、MCP 服务、Skill、定时任务和用量统计。
- **权限**：按类别审批（编辑、终端、搜索、MCP、委派），每次工具调用都会显示在对话中。

VeraAgent **不是**操作系统级沙箱：终端命令以当前 Windows 用户身份运行。请只绑定可信项目，启用 MCP 服务和 Skill 前先审查其代码。

## 快速开始（Windows）

需要 Windows 10/11、Git、Node.js 20+、Python 3.10+、[uv](https://docs.astral.sh/uv/) 0.11+ 和 Microsoft Edge WebView2 Runtime。

```powershell
git clone https://github.com/Felix-0625/Agents.git
cd Agents\frontend
npm ci
cd ..\vera-agent
uv sync --locked --no-dev --extra desktop
cd ..
.\start-desktop.ps1
```

启动后在 **设置 → 模型** 中添加模型。VeraAgent 只在 GitHub 以源码形式发布，不提供 npm 包、PyPI 包或签名安装程序。详见 [Windows 安装说明](docs/INSTALL_WINDOWS.md)（英文）。

**体验示例**：[`examples/workflow-quickstart`](examples/workflow-quickstart/README.md) 会载入演示项目、两个模板和一个看板任务，并带你从对话中调用工作流。

## 文档

维护文档以英文为准，入口见 [README.md](README.md#documentation)：架构与模块地图、HTTP API、数据模型、配置与环境变量、工具与权限、测试与验收记录、贡献指南。

## 验证

```powershell
./tests/check-all.ps1
```

依次运行代码规范检查、后端测试、仓库级测试（示例、文档、仓库卫生）、MCP 示例、网站检查，以及前端 lint、单元测试和生产构建。脚本不安装依赖，也不调用模型 API。

## 许可证

MIT，见 [LICENSE](LICENSE)。`vera-agent/` 包含源自 mini-swe-agent 的代码，其 MIT 声明保留在 [vera-agent/LICENSE.md](vera-agent/LICENSE.md)。另见 [NOTICE.md](NOTICE.md) 和[第三方许可证清单](docs/THIRD_PARTY_LICENSES.md)。
