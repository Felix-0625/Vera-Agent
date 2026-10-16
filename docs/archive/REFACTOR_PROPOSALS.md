# 交互模式与权限治理重构方案 (Refactor Proposals)

本文档记录在代码阅读过程中沉淀的待改造设计点。当前代码阅读完毕后，将按此文档推进重构。

---

## 核心设计共识与理念重塑

### 1. 工具调用哲学：鼓励自治使用，摒弃琐碎确认
- **问题现状**：在过去的交互模式（如 `confirm` 模式）下，对普通工具调用（如 `read`/`write`/`edit`）进行步步人工拦截，导致交互碎片化、用户疲劳，且抑制了大模型通过工具验证事实的积极性。
- **重构共识**：
  - **工具是智能体的感知器与执行器**。使用工具（查阅代码、运行测试、外科手术修改）远比大模型凭借过时知识或凭空想象“埋头苦做”更可靠、更具工程确定性。
  - **普通基元工具（Read / Write / Edit / 常规测试 Bash）默认全自动放行**，鼓励智能体充分利用工具探索和求证。
  - **权限审批严格收敛于关键临界点**：仅在“跨模块唤醒 Subagent 调度”或“高危破坏性操作（如删除核心分支/覆盖未保存文件）”时才向人类申请。

---

### 2. 结构化确认机制：`[Y]es / [N]o / [O]ther` 交互协议
- **问题现状**：当前确认模式依赖用户自由文本输入，容易出现模糊回复（例如用户回复“行吧”、“看看再说”、“随便”），导致模型产生理解歧义或意外中断。
- **重构方案**：
  当主 Agent（Main）认为需要 Subagent 协助并向用户发起申请时，交互终端必须提供确定性的 **`[Y] / [N] / [O]` 三态结构化交互**：

  ```
  [Agent 申请]: 当前排查涉及 6 个模块跨文件依赖，主 Agent 提议唤醒 Researcher 子智能体进行只读调研。
  请选择操作:
    [Y] 同意 (Yes)    - 批准申请，系统向主 Agent 临时解锁并派发 delegate_research
    [N] 拒绝 (No)     - 明确驳回，主 Agent 触发退守逻辑，自主收拢范围单点突破
    [O] 补充 (Other)  - 输入其他补充意见、技术指引或指定探索文件
  >
  ```

---

## 具体改造任务清单 (TODO Checklist)

### 模块 A：`interactive.py` 结构化交互器改造
- [ ] 实现 `prompt_structured_choice()` 交互函数，支持 `[Y/N/O]` 单键与带参数解析：
  - 输入 `y` 或 `Y`：返回 `Choice.YES`，主 Agent 获得授权并继续派发；
  - 输入 `n` 或 `N`：返回 `Choice.NO`，拦截调度，向 Session 注入标准驳回信号：`"User rejected subagent delegation. Fall back to local investigation."`；
  - 输入 `o` 或 `O`：提示用户输入自由文本意见，将用户意见作为 `role: "user"` 消息注入，引导主 Agent 按照人类指定方向推进。

### 模块 B：工具权限分级与白名单自治放行
- [ ] 将工具划分为两级：
  - **自治级（Autonomous Tier）**：`read`、`write`、`edit`、`bash`（白名单命令如 `pytest`, `git status`, `git diff`）一律自主执行，零人工打扰；
  - **审批级（Governed Tier）**：`delegate_research`、`delegate_review` 以及高危 Bash（如 `rm -rf`、`git push`），必须前置触发 `[Y/N/O]` 审批流。

### 模块 C：主 Agent 提示词与退守逻辑固化
- [ ] 在 `default.yaml` 中明确主 Agent 申请 Subagent 的提案格式规范；
- [ ] 固化主 Agent 被拒后的 **Fallback Policy（退守策略）**：
  - 若 `delegate_research` 被拒：主 Agent 不得重复申请，必须直接聚焦当前入口文件，用 `read` 与局部 `grep` 亲自排查；
  - 若 `delegate_review` 被拒：主 Agent 直接运行自身已有的冒烟测试，通过后向用户提请最终交付。
