# Agents 项目核心架构与设计细节备忘录 (Design Notes)

本文档由系统维护，用于沉淀与记录项目在讨论过程中敲定的核心架构思想、业务逻辑细节与未来演进路线。

---

## 一、项目定位与核心哲学

1. **核心使命**：构建工程级、可落地的 **Multi-Agent 编程协作系统**。
2. **架构标杆**：**以 `pi-agent` 为设计基准**。
   - 核心思想：**Radical Minimalism（极致极简）**，“留白比盲目堆功能更重要”。
   - 架构基调：微提示词（< 800 tokens）、正交四基元工具（Read/Write/Edit/Bash）、无头核心（Headless Core）与外壳解耦。
   - 兼收并蓄：融合 `mini-swe-agent` 的稳定 Docker 沙箱隔离机制与异常驱动控制流。

---

## 二、多 Agent 协作体系（双层全景）

系统的多 Agent 协作严格划分为两大互补维度：

### 1. 微观维度：单个对话内的 Subagent 协作（黄金三角）
- **人员编制**：1 个主 Agent + 最多 2 个 Subagent（轻量敏捷）。
  - **主 Agent（Main Implementer）**：统筹调度，面对用户交互与代码实施，严格遵循 7 大核心工程准则（见下文）；
  - **Subagent 1（调研员 - Researcher）**：只读权限。负责快速勘探大型复杂代码库、推导依赖架构，输出极简方案简报，作为“上下文防火墙”；
  - **Subagent 2（审查与质检员 - Reviewer / Verifier）**：审计权限。负责审阅 Git Diff，在 Docker 中编写并执行对抗性边界测试用例，执行交付前的最终质量门禁。

- **主 Agent 7 大核心工程公理（Core Engineering Principles）**：
  1. **永远客观（Technical Objectivity）**：直截了当指出技术风险与缺陷，严禁盲从迎合用户。
  2. **理清意图（Clarify Intent）**：意图不明立刻暂停并主动提问，严禁臆测；讨论阶段不改动任何代码。
  3. **范围授权（Scope-Based Authorization）**：实施前必须正式提交方案、改动范围与预估影响文件清单申请授权；获批后约定范围内自主闭环，超出范围或高危时提级追加，全过程控制在 2-3 次确认内，杜绝琐碎形式主义授权。
  4. **最小成本（Minimal Cost & Standard Solutions）**：优先选用工业界成熟方案与标准库，追求最小代价解决问题，不小题大做，不重复造轮子。
  5. **精简测试（Pragmatic Testing）**：紧扣真实用户路径与核心回归，杜绝临时性、用完即删或无意义的冗余测试。
  6. **交付级代码规范（Production-Grade Maintainability）**：精简优雅、自解释命名、严格代码规范与详尽中文注释，确保人类无缝接手。
  7. **回答纪律（Communication Discipline - BLUF）**：结论先行（Bottom Line Up Front），用户不追问绝不自主过度解释，非必要不展开，杜绝无意义套话。
- **调用原则（重中之重）**：
  - **必须显式调用（Explicit Invocation）**：坚决杜绝后台黑盒自发死循环。Subagent 作为主 Agent 工具栏里的两把显式重武器（`delegate_research` / `delegate_review`），或由用户通过特权斜杠指令（如 `/research`、`/review`）唤醒；
  - **严苛门禁条件（Strict Gating）**：
    - *调研员门禁*：仅限 5 个以上跨文件未知复杂架构或全新技术栈评估时唤醒；单文件、有明确报错或日常问答绝对禁止唤醒！
    - *审查员门禁*：仅在“代码实施完毕 + 主 Agent 自身冒烟自测全部绿灯 + 交付前一刻”作为 Pre-merge Gate 介入一次，审完即走！

### 2. 宏观维度：跨对话窗口的项目组协作与工作流编排
- **项目组分组（Grouping）**：支持用户创建分组（如“重构组”、“支付模块开发组”），在分组中创建多个会话窗口，明确每个窗口的专属职责与角色；
- **显式节点编排（Workflow Nodes）**：支持将多个窗口串联成显式工作流，支持通过 `thread_id` 跨窗口互相发送消息与调用；
- **上下文交接机制（Context Handover）**：当某个窗口因为上下文过长（超过窗口阈值）产生幻觉或信息污染时，触发一键“交接摘要提炼（Handover Summary）”，并将精华无缝注入新建的对话窗口或交付给下一个 Agent 节点，彻底根治长上下文幻觉。

---

## 三、 框架选型与多智能体协作架构

针对本项目的代码编程特性（追求**极致极简、轻量、高确定性与类型安全**），我们拒绝引入类似 LangGraph 等庞大沉重的图计算框架（避免复杂的抽象层级与高运行时开销），确立**以 `PydanticAI` 为唯一核心框架、以 `Handoff（动态交接）` 为协同模式的轻量化架构**：

```
┌────────────────────────────────────────────────────────────────────────┐
│  宏观路由层 (Inter-Window Routing): 基于 thread_id 的异步会话总线       │
│  • SessionRouter 通过 thread_id 进行非阻塞异步寻址与队列投递 (AsyncIO)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│  调度流转层 (Agent Orchestration): Handoff（动态控制权交接）模式         │
│  • transfer_to_researcher / transfer_to_reviewer 极简接力棒交接        │
│  • 结合 [Y/N/O] 人机结构化确认流，拒绝黑盒幽灵循环                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│  微观契约层 (Node Kernel & Contracts): PydanticAI 框架驱动              │
│  • Agent[AgentDeps, ResultType] 强类型依赖注入 (注入 Env 与 Session)   │
│  • 四基元工具参数强类型校验 (@agent.tool)                              │
│  • 结构化输出结果验证 (CodeReviewResult / HandoverPayload)             │
└────────────────────────────────────────────────────────────────────────┘
```

### 核心分工与落地点：
1. **核心框架：`PydanticAI`（单节点内核与契约保障）**：
   - **用在哪里**：单个 Agent 内部的推理输入输出与工具校验。
   - **核心职责**：通过 `RunContext[AgentDeps]` 注入环境沙箱与会话；对 `read`/`write`/`edit`/`bash` 参数进行严格类型约束；审查员输出强制校验为 `CodeReviewResult` 结构化对象，从底层杜绝模型格式畸变。
2. **协作模式：`Handoff`（多智能体接力与交接流转）**：
   - **用在哪里**：主 Agent、调研员、审查员之间的控制权转移与协作。
   - **核心职责**：主 Agent 遇到复杂代码时触发 Handoff，子智能体同步挂起或接力运行，运行结束后返回标准结果；彻底摆脱沉重框架的胶水代码，保持微秒级轻量调度。
3. **跨窗口通信：`SessionRouter`（异步消息总线）**：
   - **用在哪里**：多对话窗口（Thread Windows）与工作组（Project Group）通信。
   - **核心职责**：每个会话窗口绑定唯一 `thread_id`；窗口之间通过 `SessionRouter` 原生异步消息队列（`asyncio.Queue`）投递消息与交接载荷，避免窗口间同步阻塞。

---

## 四、工程演进六阶段路线图

1. **阶段 1 & 2（基础设施与 Pi-agent 融合改造 - 已完成）**：
   - [x] **第一步：微提示词与双模交互闭环（已彻底对齐 Pi-agent）**：
     - 提示词瘦身重构（主 Agent 7 大工程公理，Token 压降至 ~320）；
     - 解耦独立 Subagent 配置（`researcher.yaml` / `reviewer.yaml`，只读约束，支持 Markdown 文档交接）；
     - Action 解析器松绑（允许 0 工具调用，支持纯文本自然对话）；
     - 交互式主 Agent 双模 Turn Loop 落地；
     - Subagent 自然交付机制（`complete_on_empty_actions`，无工具调用即代表输出完成并返回结果）；
     - 项目级上下文动态自动注入（自动向上扫描发现 `AGENTS.md` / `CLAUDE.md` 并挂载至 `<project_instructions>`）。
   - [x] **第二步：正交四基元工具注入（已完成）**：
     - 在 Python 端实现 `read`、`write`、`edit`、`bash` 四基元工具，摆脱容器与宿主环境内脆弱的 `sed`/`cat` 脚本；
     - `read`: 支持行号展示、offset/limit 视窗分页与越界截断；
     - `write`: 自动递归创建父级目录、原子写入；
     - `edit`: 精准上下文匹配查找替换、歧义多处匹配拦截，单次调用支持多处连续替换并输出 Unified Diff；
     - Local 与 Docker 双环境对齐（Docker 采用 base64 内存注入执行，彻底规避 Windows 到 Linux 容器的 Shell 转义损坏与换行问题）；
     - 模型端适配全量工具定义（标准 OpenAI Function Calling 与 Responses API 扁平格式双向适配，覆盖 LiteLLM/OpenRouter/Portkey/Requesty）；
     - 建立完备基元工具单元测试套件（`tests/test_tools.py` 13 个核心测试用例全部通过）。
   - [x] **第三步：Session 与交接抽象（ThreadSession）（已完成）**：
     - 构建轻量级 `ThreadSession` 实体，统一收拢 `thread_id`、`role`、`messages` 历史轨迹与 `cost`/`n_calls` 度量指标；
     - 实现多轮 JSON 快照持久化（`save` / `load`）；
     - 实现 `export_handover_summary()` 标准化 Markdown 上下文交接文档生成，从消息流中自动提取 `[read]`/`[write]`/`[edit]` 触碰文件清单与最新核心结论，有效遏制长上下文信息膨胀与幻觉污染；
     - 原生挂载至 `DefaultAgent` 与 `InteractiveAgent`，与现有工作流无缝互通；
     - 建立完备单元测试套件（`tests/test_session.py` 6 项测试全部绿灯）。
2. **阶段 3（对话内 Subagent 开发）（已完成）**：
   - [x] 实现 `delegate_research` 与 `delegate_review` 显式重武器调度工具；
   - [x] 落地严苛门禁规则（Strict Gating）：调研员限 2 次复杂架构探索，审查员限 1 次交付前最终审核，超限直接拦截；
   - [x] 构筑上下文防火墙（Context Firewall）：主从 Agent 会话隔离，仅通过标准化 Handover Summary 单向交接；
   - [x] 实现主从沙箱复用：共享 Environment，成本与调用度量实时合并；
   - [x] 扩展交互式特权斜杠指令（`/research`、`/review`）；
   - [x] 建立完备单元测试套件（`tests/test_subagents.py` 8 项测试全部绿灯）。
3. **阶段 4（项目分组、GitFlow 隔离、Thread 窗口与 Pydantic 契约核落地 - 已完成）**：
   - [x] **Pydantic 单节点契约核与依赖注入 (`contracts.py`)**：
     - 构建 `AgentDeps`（封装 `Environment`、`ThreadSession`、`worktree_path` 与 `scratch_dir`）；
     - 定义强类型 `HandoverPayload`（含 `rejected_paths` 显式否定约束槽位，防止过时需求死灰复燃）；
     - 定义 `MergeReviewResult` 强类型 PR 审阅报告（含冲突列表、Diff 摘要、测试状态）；
     - 定义对齐 React Flow 工业标准的 `GraphTopology`（`GraphNode`, `GraphEdge`），为后续 Web 可视化前端奠基。
   - [x] **Git Worktree 任务级隔离与快照机制 (`worktree.py`)**：
     - 借鉴 GitHub Copilot Workspace 与 OpenHands，基于原生 Git Porcelain 落地 `WorktreeManager`；
     - 实现多分支物理工作树零拷贝秒级创建与移除；
     - 借鉴 Aider 落地 `create_checkpoint()` 临时快照提交机制，工作树改崩时一键 `reset_worktree(hard=True)` 无损复原，解决“烂摊子不敢提交又难接盘”死局；
     - 实现 `try_merge()` 纯内存 3-way Merge 冲突探测（无需物理检出即可预判冲突）。
   - [x] **GitFlow 拓扑状态图与分组实体 (`graph.py`)**：
     - 实现 `ProjectGroup`，将逻辑研发组与物理 Git Worktree / 分支强绑定；
     - 实现 `GitFlowGraph` 拓扑状态机，支持 Agent 会话热插拔挂载与脱钩换树（`attach_session` / `detach_session`）；
     - 原生导出标准 React Flow 拓扑 JSON 数据流。
   - [x] **跨窗口异步消息总线 (`router.py`)**：
     - 基于 `asyncio.Queue` 实现线程级专属邮箱，支持点对点投递、组内广播（`broadcast_to_group`）与 PR 交叉审阅路由（`request_merge_review`）；
     - 落地 `prompt_structured_choice()` 人机 `[Y/N/O]` 结构化审批流。
   - [x] **建立完备测试套件**：
     - 新增 `tests/test_phase4_worktree_router.py`，全量 50 项多智能体测试 100% 绿灯通过。
4. **阶段 5（Handoff 流水线与上下文自动换血 - 已完成）**：
   - [x] **Typed Handoff 流转链 (`handoff_tools.py`)**：
     - 实现 `transfer_to_researcher_op`、`transfer_to_reviewer_op` 与 `transfer_to_main_op` 接力棒流转；
     - 结合强类型 `HandoverPayload`，实现跨阶段无损成果移交，强制携带 `rejected_paths` 否定约束。
   - [x] **上下文高水位警报与自动换血流水线 (`pipeline.py`)**：
     - 建立 `WatermarkPolicy` 监控线（支持多轮次、总字符量、成本三维高水位触发）；
     - 超标时触发 `HandoffPipeline.auto_rebirth_if_needed()`，自动将老旧会话完整快照归档至磁盘，生成携带纯净 Markdown 锚点的派生 `ThreadSession(parent_thread_id=old_id)`，物理切断上下文垃圾；
     - 在拓扑状态图中自动追加 `rebirth_handoff` 演进边。
   - [x] **建立完备测试套件**：
     - 新增 `tests/test_phase5_handoff_pipeline.py`，全量 58 项多智能体测试 100% 绿灯通过。
5. **阶段 6（Tool/Skill 生态扩充与 Web Control API 落地 - 已完成）**：
   - [x] **AST 代码智能与语法校验工具 (`code_tools.py`)**：
     - 实现 `check_syntax_op`：基于 Python 内置 AST 进行零依赖语法预检；
     - 实现 `symbol_search_op`：快速遍历解析 AST，支持按类名、函数名与方法名搜索定位文件与行号；
     - 实现 `find_references_op`：轻量符号引用检索。
   - [x] **动态 Skill 发现与注入引擎 (`skill_tools.py`)**：
     - 实现 `SkillManager`：自动扫描 `.agents/skills/<name>/SKILL.md` 与项目级 Skills；
     - 解析 YAML 元数据并按需（Just-In-Time）渲染注入提示词，避免静态上下文膨胀。
   - [x] **Starlette ASGI Web Control API 服务 (`server/app.py`)**：
     - 提供 React Flow 标准拓扑流 (`GET /api/topology`)；
     - 提供工作组与工作树管理 (`POST /api/groups`)；
     - 提供会话热插拔挂载与脱钩 (`POST /api/sessions/attach`, `detach`)；
     - 提供临时快照与一键自愈 (`POST /api/worktrees/checkpoint`, `reset`)；
     - 提供内存 3-Way PR 冲突审查 (`POST /api/merge-review`)；
     - 提供代码语法预检、符号检索与 Skill 清单端点；
     - 开启全量 CORS，为后续 Web 前端（React Flow / Vite）开箱即用铺平道路。
   - [x] **建立完备测试套件**：
     - 新增 `tests/test_phase6_server_and_skills.py`，全量 61 项多智能体测试 100% 绿灯通过。
