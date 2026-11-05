# 本地 API 参考

VeraAgent 桌面界面通过本地 Starlette API 通信。本页覆盖全部 **17 个路由模块**，统一按"用途说明 → 路由表 → 边界提示"的结构列出；逐条路由的完整参数、错误码和处理函数行号见由代码生成并经 CI 校验的[仓库 API 索引](../../../docs/API.md#route-index)（当前 107 条路由）。接口供当前本机应用使用，不是带鉴权的公共云 API。

## 约定

| 项 | 约定 |
| --- | --- |
| 地址 | `http://127.0.0.1:<port>`；桌面应用从 8000 起选第一个空闲端口，界面与 API 同源 |
| 鉴权 | 无调用者认证，只能保持在 loopback 上；`server/security.py` 拒绝非 loopback 的 `Host`（400）和 `Origin`（403），CORS 只放行 loopback 来源 |
| 正文 | JSON；字段名为 `snake_case` |
| 错误 | 非 2xx 一般为 `{"error":"<message>"}`；部分消息是中文，会被界面直接展示 |
| 常见状态码 | `400` 无效输入，`403` 权限/确认拒绝或路径越界，`404` 未找到，`409` 状态冲突，`413` 内容超限，`502`/`504` 市场类接口的上游错误 |
| 项目范围 | 多数项目数据请求必须带已绑定的 `project_id`，服务端据此在该项目目录内解析路径 |

`GET /api/health` 用于轻量存活检查。Vite 开发服务用 `/api` 代理本地后端。

## 对话流（chat.py）

一轮对话的发起、确认、流控全部在这个模块，响应格式是 SSE（`text/event-stream`）。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/api/chat/stream` | 发起一轮对话；常用字段 `thread_id`、`project_id`、`content`、`model_id`，工作流运行额外传 `workflow_stage`、`workflow_control`、`workflow_input` |
| POST | `/api/chat/confirm` | 回应 `approval_required` 事件的审批请求 |
| POST | `/api/chat/interrupt` | 打断正在进行的一轮对话 |
| POST | `/api/chat/pause` / `/resume` | 暂停/恢复一轮对话的流式输出（只影响单轮内部，和工作流运行调度状态无关） |

`/api/chat/stream` 的 SSE 事件类型：

| 事件 | 含义 |
| --- | --- |
| `thinking` | 进度文本，**不是**模型隐藏推理 |
| `text_chunk` | 增量答复 |
| `tool_call` | 模型请求的工具动作及参数 |
| `approval_required` | 等待用户确认；经 `POST /api/chat/confirm` 回答 |
| `tool_result` | 工具的输出与返回码；展示输出截断到 5000 字符 |
| `subagent` | 被委派角色（子智能体）的进度记录 |
| `context_management` | 对话压缩等上下文管理事件 |
| `finish` | 一轮对话结束，固定作为最后一个事件，包含状态与用量摘要 |

前端解析实现在 `frontend/src/api/chatApi.ts`。

## 项目绑定（projects.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/projects` | 列出已绑定项目历史 |
| GET | `/api/projects/current` | 读取当前选中的项目 |
| POST | `/api/projects/bind` | 绑定已有本地目录；`path` 必须存在，可带 `name`、`project_id` |
| POST | `/api/projects/select-folder` | 打开系统目录选择器 |
| PATCH / DELETE | `/api/projects/{project_id}` | 更新项目记录 / 从历史中移除 |

绑定只记录路径，不会复制或隔离项目文件。

## 拓扑模板（templates.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/templates/topology` | 读取内置模板与自定义模板的合并列表 |
| POST | `/api/templates/topology` | 保存自定义模板；`name`、非空节点、合法连线；组织模板须满足单根/无环/仅角色节点的汇报树约束 |

## 组织/工作流实例与运行（groups.py / runs.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET / POST | `/api/groups` | 列出 / 创建项目下的实例 |
| PATCH / DELETE | `/api/groups/{group_id}` | 更新 / 删除实例 |
| POST | `/api/groups/instances` | 从模板创建项目实例；`project_id`、`name`、`group_mode`、节点（1–60）与连线（≤120） |
| POST | `/api/groups/compose` | 按协议直接写入实例；可用 18 种协议层节点类型，但多数类型目前没有运行时执行器 |
| POST | `/api/groups/provision` | 批量生成节点会话等配套资源 |
| GET / POST | `/api/groups/{group_id}/threads` | 读取 / 创建实例下的节点会话 |
| POST | `/api/groups/{group_id}/runs` | 创建运行；`project_id`、输入（≤100,000 字符）、字符串确认值 `"Y"`；为每个节点创建隔离会话 |
| PATCH | `/api/groups/{group_id}/runs/{run_id}` | 更新运行或节点状态；服务端只校验状态转换合法性并落盘，不参与调度决策 |

状态转换和字段上限见[数据模型](../../../docs/DATA_MODEL.md#run-record)，不能只依据 HTTP 成功响应判断一个流程已经完成。

## 会话管理（threads.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET / POST | `/api/threads` | 列出 / 创建对话 |
| GET | `/api/threads/{id}/messages` | 读取对话消息 |
| PATCH / DELETE | `/api/threads/{id}` | 更新 / 删除对话 |
| POST | `/api/threads/{id}/messages/deliver` | 把工作流/组织运行的最终复核结果写入发起该次运行的原始对话；是运行结束后唯一的结果回传路径 |
| POST | `/api/threads/{id}/messages/truncate` | 从某条用户消息开始截断对话历史，用于回到之前某一步重新回答 |
| GET | `/api/threads/{id}/context-probe`、`/context-status` | 查询当前对话相对所选模型上下文窗口的占用情况 |
| GET | `/api/context-status` | 同上，不带 `thread_id` 的草稿态版本 |
| POST | `/api/threads/{id}/context-rebirth` | 仅用于工作流/组织节点会话：上下文过长时重建一个精简新会话延续同一节点 |

## 任务看板（taskboard.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/taskboard/tasks` | 列出项目工作项 |
| POST | `/api/taskboard/tasks` | 创建工作项；`title`（1–240 字符）、可选 `description`、`status`、`priority`、`labels` |
| PATCH | `/api/taskboard/tasks/{id}` | 更新工作项；必须提交当前 `version`，过期版本返回 `409` 并附最新项（乐观锁） |
| DELETE | `/api/taskboard/tasks/{id}` | 软归档，不是物理删除 |

这是**持久看板任务**，和下面的"一次性定时任务"是两个独立概念。工作项可关联同项目对话，但状态不会因对话完成而自动更新，必须手动变更。字段约束见[任务数据模型](../../../docs/DATA_MODEL.md#task-board-work-item)。

## 一次性定时任务（tasks.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET / POST | `/api/tasks/scheduled` | 列出 / 创建一次性计划 Agent 提示 |
| PATCH | `/api/tasks/scheduled/{id}/toggle` | 启用 / 停用 |
| POST | `/api/tasks/scheduled/{id}/run` | 立即手动触发一次 |
| DELETE | `/api/tasks/scheduled/{id}` | 删除 |

任务存于 `<project>/.agents/scheduled_tasks.json`，由应用生命周期启动的后台调度器在到期时触发执行。

## 文件浏览与编辑（files.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/files/tree` | 读取项目文件树 |
| GET | `/api/files/content` | 读取文本文件内容 |
| GET | `/api/files/preview` | 只读预览（含非文本格式） |
| GET | `/api/files/raw` | 原始文件下载/展示 |
| PUT | `/api/files/content` | 保存文本文件 |
| PUT | `/api/files/excel` | 保存 Excel 文件，走独立于文本保存的处理逻辑 |
| POST | `/api/code/check-syntax` | 语法检查 |
| POST | `/api/code/search-symbols` | 符号搜索 |

所有路径都会被解析到已绑定项目目录内并校验不越界，**这是应用层路径策略，不是操作系统沙箱**。

## Git 分支与本地仓库（gitflow.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/gitflow/topology` | 项目的分支拓扑 |
| GET / POST | `/api/branches` | 列出 / 创建分支 |
| DELETE | `/api/branches/{name}` | 删除分支 |
| POST | `/api/branches/checkout` | 切换分支 |
| POST | `/api/branches/merge` | 合并分支；合并前读取仓库状态判断冲突 |
| POST | `/api/merge-review` | 合并前复核；是否调用模型取决于具体请求上下文，不等同于自动化代码审查服务 |

## Git 工作树（worktrees.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/worktrees/refs` | 读取可用分支/引用 |
| GET | `/api/worktrees/diff` | 读取工作树改动差异 |
| POST | `/api/worktrees/stage` | 暂存指定文件（`git add`） |
| POST | `/api/worktrees/discard` | 放弃指定文件的本地改动 |
| POST | `/api/worktrees/checkpoint` | 创建一次提交 |

面向工作流/组织运行中某个节点独立持有的本地 Git 工作树（按 `group_id` 或显式 `worktree_path` 定位目录），服务于 diff 查看器和节点级代码变更追踪，不是通用的项目级 Git 客户端。

## MCP 服务与市场（mcp.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET / POST | `/api/mcp/servers` | 列出 / 注册 MCP 服务器 |
| PUT | `/api/mcp/servers/{id}` | 更新配置 |
| PATCH | `/api/mcp/servers/{id}/toggle` | 启用 / 停用 |
| POST | `/api/mcp/servers/{id}/restart` | 重启连接 |
| DELETE | `/api/mcp/servers/{id}` | 删除 |
| POST | `/api/mcp/scan` | 扫描可用服务器 |
| GET | `/api/mcp/market` | 读取市场列表 |
| POST | `/api/mcp/market/install` | 从市场安装 |

配置是**应用级**的（`<projects_config_root>/.agents/mcp_servers.json`），不按项目隔离。市场安装 npm 包时以 `--ignore-scripts` 执行，远程条目要求 HTTPS，但市场列表本身不是安全审核，启用前仍需自行检查来源。

## Skill 发现与市场（skills.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/skills` | 列出已安装 Skill |
| POST | `/api/skills/scan` | 扫描本地 Skill |
| GET | `/api/skills/market` | 读取市场列表 |
| POST | `/api/skills/install` | 从市场安装 |
| DELETE | `/api/skills/{name}` | 删除 |
| PATCH | `/api/skills/{name}/toggle` | 启用 / 停用 |

Skill 是影响 Agent 行为的指令包文本，安装后落在应用级 `<projects_config_root>/.agents/skills/<name>/SKILL.md`。安装来源限定在几个预设的 GitHub 仓库（代码写死候选仓库列表，客户端不能自定义下载地址），但**Skill 文本本身仍是不可信输入**，来源受限不等于内容安全。与 MCP 的区别：MCP 是外部进程/服务的连接配置，Skill 是直接注入到 Agent 上下文里的指令文本。

## 应用设置（settings.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET / POST | `/api/settings/models` | 读取 / 保存模型配置列表 |
| PATCH / DELETE | `/api/settings/models/{id}` | 更新 / 删除单个模型 |
| POST | `/api/settings/models/test` | 测试模型连接 |
| GET / POST | `/api/settings/permissions` | 读取 / 保存权限策略 |
| GET / POST | `/api/settings/rules` | 读取 / 保存项目规则（如 `AGENTS.md` 读取开关） |
| GET / POST | `/api/settings/context` | 读取 / 保存上下文管理参数 |
| GET / POST | `/api/settings/user-memories` | 读取 / 创建用户记忆 |
| PATCH / DELETE | `/api/settings/user-memories/{id}` | 更新 / 删除单条用户记忆 |

模型配置含 API Key，明文存于 `models_config.json`。模型与权限设置是应用级；规则和上下文设置可能按项目生效，具体以对应路由实现为准。

## 使用统计（analytics.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/analytics/dashboard` | 汇总最近三个月的 token 用量、花费和活动数据 |

数据来源是已绑定项目下持久化的对话会话文件（逐条读取消息里的 usage/cost 字段聚合），不是额外的独立统计数据库。

## 健康检查（sessions.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/health` | 存活检查 |

## 终端（terminal.py）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/api/terminal/exec` | 一次性非交互命令执行 |
| WS | `/api/terminal/session?project_id=<id>` | 在项目目录打开 PowerShell 会话（也可用 `group_id`） |

WebSocket 客户端发送 `{"type":"input","data":"…"}`；服务端返回 `connected`、`output`、`exit` 或 `error` 消息。进程以当前 Windows 用户权限运行；会拒绝非 loopback 的 `Origin`。

## 接口边界

本地 API 当前没有认证，且 CORS 配置并不适合直接公开到网络。不要把端口映射到外部地址充当多人服务。需要新增接口时，先修改路由和前端类型，再更新[生成的 API 索引](../../../docs/API.md)及对应测试。

## 执行记录、记忆与改进接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/traces`、`/api/traces/summary`、`/api/traces/{trace_id}` | 轨迹列表、统计、详情 |
| POST | `/api/traces/{trace_id}/feedback` | 独立用户反馈 |
| GET / POST | `/api/memories` | 作用域记忆查询 / 新建 |
| PATCH / DELETE | `/api/memories/{memory_id}` | 修改 / 软删除 |
| GET / POST | `/api/memories/{memory_id}/history`、`/restore` | 版本列表 / 恢复 |
| GET / POST | `/api/memories/pending`、`/api/memories/pending/{change_id}` | 待确认列表 / 接受或拒绝 |
| GET | `/api/evolution/proposals` | 提案列表 |
| POST | `/api/evolution/analyze`、`/api/evolution/proposals/{proposal_id}/gate` | 模型分析 / 评测（有费用） |
| POST | `/api/evolution/proposals/{proposal_id}/adopt`、`/reject`、`/rollback` | 采纳、拒绝、回滚 |
| POST | `/api/evolution/monitor` | 用户触发在线评分比较 |
| GET / PUT | `/api/settings/telemetry`、`/api/settings/memory` | 设置读取 / 更新 |

完整路径、字段与状态码以[自动 API 索引](../../../docs/API.md)和[学习闭环](../../../docs/LEARNING_LOOP.md)为准；采纳需要 `{"confirm": true}`。本地 API 无调用者身份认证，仍只绑定 loopback。
