# VeraAgent

VeraAgent 是一个面向本地软件项目的桌面 AI Agent 工作台。它把项目绑定、模型配置、文件与终端工具、MCP/Skill、项目规则和对话记录放在一个本地运行的应用中，方便开发者围绕真实代码协作。

目前桌面壳采用 **pywebview + WebView2**，界面由 React、TypeScript 和 Vite 构建，后端是 Python/Starlette。项目仍处于积极开发阶段；本仓库如实记录当前行为和已知限制，不把计划中的能力描述成已交付能力。

## 当前能做什么

- 绑定本地项目目录并在项目上下文中进行 Agent 对话。
- 配置模型提供方和模型参数；模型服务凭证由使用者自行配置。
- 按权限设置处理文件操作和工具调用，并在界面中查看工具执行事件。
- 管理项目规则、对话记忆、MCP 服务、Skill 和工作流/架构实例。
- 在界面提供的项目、文件、终端、Git 等工具中协作；实际可用范围以当前设置、项目状态和工具实现为准。

这不是操作系统级沙箱。项目目录范围设置用于约束应用层的文件操作；本地终端命令仍以当前 Windows 用户身份运行。请只绑定可信项目，并在启用外部 MCP/Skill 前审查其代码和权限。

## Windows 桌面版

仓库包含一个基于 GitHub 源码的 npx 引导入口。它会在本机准备源码、Python 虚拟环境和前端依赖，再启动桌面应用。**当前 npx 命令尚未发布到 npm Registry**；在仓库内容推送到 GitHub 后可使用：

```powershell
npx --yes github:Felix-0625/Agents
```

前置条件：Windows 10/11、Git、Node.js/npm、Python 3.10+、Microsoft Edge WebView2 Runtime，以及可访问依赖仓库的网络。首次运行会下载源码和依赖，需要较长时间；引导程序会先说明操作并要求确认。模型 API Key 需要在应用设置中由用户自行填写。详见 [Windows 安装与更新](docs/INSTALL_WINDOWS.md)。

开发者也可以走本地源码启动流程，见 [开发指南](docs/DEVELOPMENT.md)。

## 项目结构

```text
frontend/              React + TypeScript 桌面界面
vera-agent/            Python Agent、工具、会话和本地 API
vera-agent/tests/      后端单元、集成和 API 测试
examples/              可单独运行的项目/MCP 示例
tests/                 仓库级验证入口与测试说明
docs/                  面向使用者和维护者的事实型文档
website/               静态产品介绍页与 GitHub Pages 部署配置
```

`mcp-sever/` 曾作为未配置远端的嵌套 Git 指针存在，其他克隆无法可靠取得。可复现的 MCP 示例已放在 `examples/mcp-server/`。本机原目录保留为忽略的本地副本。

## 验证

```powershell
./tests/check-all.ps1
```

脚本执行后端 pytest、前端 lint、TypeScript/Vite 构建。当前测试覆盖范围、分类和需要外部服务的边界请看 [测试指南](docs/TESTING.md)。除非本仓库的 CI 实际运行并保留结果，本文不宣称某个测试数量“全部通过”。

## 文档与演示

- [架构概览](docs/ARCHITECTURE.md)
- [工具、权限与 MCP](docs/TOOLS_AND_MCP.md)
- [配置与本地数据](docs/CONFIGURATION.md)
- [测试与已知限制](docs/TESTING.md)
- [贡献指南](CONTRIBUTING.md)
- [网站现状](website/README.md)

旧产品介绍页已移除，网站目前只保留文档与模拟演示页面。GitHub Pages 工作流仍为手动触发，未自动发布到公共站点。

## 许可证与上游

`vera-agent/` 中包含来自 mini-swe-agent 的代码和 MIT 许可文本。其许可证和原作者署名保留在原位置；新增/改写部分的版权和再分发边界应在正式发布前由项目维护者确认。参见 [NOTICE](NOTICE.md) 和 [许可证说明](docs/LICENSES.md)。
