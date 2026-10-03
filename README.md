# Multi-Agents

本项目工作空间包含用于学习与开发的 Coding Agent 相关项目。

## 目录结构

```text
.
├── mini-coding-agent/   # 学习项目：用于学习 Coding Agent 核心原理与实现机制（Python 单文件）
├── mini-swe-agent/      # 开发基座：用于后续二次开发与多智能体系统搭建的工程基座（Python 模块化）
├── pi-agent/            # 参考/扩展项目：高度可扩展的终端 Coding Agent 框架体系（TypeScript）
└── README.md            # 项目说明文档
```

## 目录与文件说明

- **`mini-coding-agent/`**
  - **定位**：学习项目。
  - **说明**：基于单文件实现的轻量级 Coding Agent，用于直观学习 Agent Loop、工具调用和上下文处理等核心机制。

- **`mini-swe-agent/`**
  - **定位**：开发基座。
  - **说明**：模块化、工程级的软件工程 Agent 基座，具备环境隔离、模型接入与可扩展架构，用于后续二次开发与 Multi-agent 拓展。

- **`pi-agent/`**
  - **定位**：参考与扩展项目。
  - **说明**：基于 TypeScript 的极简、高扩展性终端 Coding Agent 工具体系，支持多模型热切换、会话分支树（Branching Sessions）、MCP 协议及插件扩展。

- **`README.md`**
  - **说明**：当前工作空间的总览说明文档。
