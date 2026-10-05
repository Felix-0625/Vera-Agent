# VeraAgent (`vera-agent`)

> **Minimalist Multi-Agent GitFlow Collaboration Engine**
> 
> *以“Radical Minimalism（极致极简）”与“物理真实（Ground Truth）”为核心哲学的高可靠多智能体软件工程协同系统。*

---

## 一、 为什么叫 VeraAgent？

**Vera** 源自拉丁语 *verus*（真理、真实、经过验证的）：
1. **抗幻觉与物理真实（Ground Truth）**：代码状态不依赖大模型的模糊自然语言记忆，而是直接锚定在 Git 文件系统、真实 Diff 与真实单元测试执行结果上；
2. **零文件踩踏（Zero Collision）**：基于原生 **Git Worktree** 实现多特性分支、多团队任务级物理隔离；
3. **彻底根除长上下文污染（No Context Contamination）**：三层动态剪枝与 Session Rebirth 自动换血流水线，确保上下文永远纯净。

---

## 二、 核心架构全景

```
┌────────────────────────────────────────────────────────────────────────┐
│  Web 控制层 & 动态图谱 (Starlette ASGI API / React Flow JSON)            │
│  • GET /api/topology  | POST /api/groups  | POST /api/sessions/attach  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│  会话路由与 PR 仲裁层 (SessionRouter & In-Memory 3-Way Merge Review)   │
│  • 基于 asyncio.Queue 的跨线程异步邮箱，点对点投递、组内广播与 PR 预检     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│  物理隔离与快照层 (Git Worktree Manager & Aider-style Checkpoints)     │
│  • .agents/worktrees/{branch}/ 零拷贝独立目录，并发无踩踏                │
│  • 临时 Checkpoint 提交，工作树改崩时一键 reset_worktree(hard=True) 秒级自愈 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│  智能体调度与换血层 (Subagent Golden Triangle & Handoff Pipeline)       │
│  • Main Implementer (主实施) + Researcher (调研) + Reviewer (质检)     │
│  • WatermarkPolicy 监控线触发 Session Rebirth 纯净换血                 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 三、 目录结构与模块说明

```text
.
├── vera-agent/              # VeraAgent 核心引擎实现
│   ├── src/
│   │   └── vera_agent/      # 引擎核心源码包
│   │       ├── models/      # 强类型契约 (contracts.py: AgentDeps, HandoverPayload, MergeReviewResult)
│   │       ├── session/     # Worktree 管理、GitFlowGraph 拓扑、SessionRouter、HandoffPipeline
│   │       ├── tools/       # 四基元工具、网络检索、AST 符号导航、Skill 动态发现
│   │       ├── server/      # Starlette ASGI Web API 服务
│   │       └── agents/      # DefaultAgent 与 InteractiveAgent [Y/N/O] 人机确认
│   └── tests/               # 结构化分类测试套件
│       ├── core/            # 基元工具、沙箱安全、Session 抽象测试 (13项)
│       ├── multiagent/      # 子智能体门禁、动态压缩、Handoff 换血测试 (15项)
│       ├── gitflow/         # Worktree 隔离、临时快照、SessionRouter 测试 (9项)
│       ├── server/          # Web API 服务、代码智能、Skill 发现测试 (3项)
│       └── e2e/             # 10 步真实电商微服务端到端生产场景测试 (1项)
└── DESIGN_NOTES.md          # 核心架构设计与工程备忘录
```

---

## 四、 快速开始与测试验证

### 1. 运行全量结构化测试套件 (62 项测试 100% 绿灯)
在 `vera-agent` 目录下执行：
```bash
pytest tests/core tests/multiagent tests/gitflow tests/server tests/e2e -v
```

### 2. 启动 Web 控制 API 服务
```bash
python -m uvicorn vera_agent.server.app:create_app --factory --port 8000
```
访问 `http://localhost:8000/api/topology` 即可获取 React Flow 标准的拓扑节点与连线数据。
