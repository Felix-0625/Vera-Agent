# VeraAgent 桌面端前端工程架构与实施规范说明书 (Frontend Implementation Specification)

> **文档性质**：本文档为 **VeraAgent 桌面端应用前端工程的权威实施指导规范**。  
> **制定依据**：严格对齐 Penpot 26 个核心原型画板与 [UI_IMPLEMENTATION_LEGACY.md](UI_IMPLEMENTATION_LEGACY.md) 业务流转逻辑。
> **核心铁律**：**严格对齐 Penpot 原型布局与文字（禁止擅自改动文案与空间排版），全量使用标准矢量图标（Lucide Vector），严禁前端编写超大单文件代码（严格践行原子组件解耦与逻辑外置）。**

---

## 目录
- [一、 桌面端技术架构与运行选型澄清](#一-桌面端技术架构与运行选型澄清)
- [二、 前端工程规范（禁止超大单文件代码）](#二-前端工程规范禁止超大单文件代码)
- [三、 视窗布局系统与弹性伸缩机制（核心前端细节）](#三-视窗布局系统与弹性伸缩机制核心前端细节)
- [四、 Penpot 原型与文档 100% 严格对齐映射清单](#四-penpot-原型与文档-100-严格对齐映射清单)
- [五、 核心界面完整实施规范与组件清单](#五-核心界面完整实施规范与组件清单)
  - [5.1 主工作台 (VeraAgent Conversation Workspace)](#51-主工作台-veraagent-conversation-workspace)
  - [5.2 左侧边栏 (Left Sidebar)](#52-左侧边栏-left-sidebar)
  - [5.3 中间主对话区 (Center Composer Workspace)](#53-中间主对话区-center-composer-workspace)
  - [5.4 右侧多标签页容器与 10 大工具体系 (Right Tool Tab Container)](#54-右侧多标签页容器与-10-大工具体系-right-tool-tab-container)
  - [5.5 历史对话与定时任务体系](#55-历史对话与定时任务体系)
  - [5.6 系统设置中心五大模块 (Settings Center)](#56-系统设置中心五大模块-settings-center)
  - [5.7 全局关键浮窗与弹窗体系 (Modals & Overlays)](#57-全局关键浮窗与弹窗体系-modals--overlays)
- [六、 后端 API 接口与数据契约映射表](#六-后端-api-接口与数据契约映射表)
- [七、 界面设计与工程实施自检清单 (Self-Inspection Checklist)](#七-界面设计与工程实施自检清单-self-inspection-checklist)

---

## 一、 桌面端技术架构与运行选型澄清

在 [UI_IMPLEMENTATION_LEGACY.md](UI_IMPLEMENTATION_LEGACY.md) 中，目标形态明确为**“桌面端 App，本地化运行，一体化交付，无需用户在终端敲命令启动”**。针对该定位，确立以下技术架构选型：

```
┌────────────────────────────────────────────────────────────────────────┐
│                        桌面端 App 外壳 (Desktop Shell)                  │
│                     Tauri 2.0 (Rust) / 极轻量原生运行时                  │
│   • 原生系统托盘、多窗口管理、系统文件选择器 (rfd/native dialog)           │
│   • 启动时静默拉起 Python 后端子进程 (Sidecar / Daemon Process)           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ 本地 HTTP / WebSocket 环回总线 (127.0.0.1)
┌───────────────────────────────────▼────────────────────────────────────┐
│                        前端渲染层 (Webview / Frontend)                  │
│   • 框架选型：React 18/19 + TypeScript + Vite 快速打包构建              │
│   • 样式体系：TailwindCSS + CSS Modules (严格锁定 KokonutUI 暗夜玻璃拟态) │
│   • 状态管理：Zustand (极简原子化 Store，严禁全局大单例)                 │
│   • 拓扑引擎：@xyflow/react (React Flow 12，用于 GitFlow 与实时工作流)    │
│   • 内嵌终端：@xterm/xterm + @xterm/addon-fit (用于 Bash 沙箱终端)      │
│   • 矢量图标：lucide-react (统一度量衡，Stroke 2px，禁止杂乱位图)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API & WebSocket 通信
┌───────────────────────────────────▼────────────────────────────────────┐
│                     本地无头服务层 (Python Core Sidecar)                 │
│   • Starlette / FastAPI ASGI Server (已落地的 server/app.py)            │
│   • PydanticAI 契约核、Git Worktree 管理器、SessionRouter 异步总线      │
└────────────────────────────────────────────────────────────────────────┘
```

### 1. 为什么选择 Tauri 2.0 + React 而非重型 Electron？
1. **安装包体积与内存开销**：Tauri 打包后体积仅约 10MB~15MB，内存占用仅 30MB~50MB（使用系统自带 WebView2），而 Electron 动辄 150MB+ 且附带独立 Chromium 实例；
2. **本地文件与文件夹绑定**：左侧边栏的“新建项目绑定本地文件夹”，通过 Tauri 原生 `tauri-plugin-dialog` 能够以零时延呼出 Windows 资源管理器原生文件夹选择框，直接获取绝对路径；
3. **后台进程伴生守护 (Sidecar)**：Tauri 具备原生 Rust 子进程守护能力，应用打开时静默在后台启动 Python ASGI 服务（`localhost:8000`），应用关闭时平妥释放端口并销毁进程，完全不需要用户打开终端。

---

## 二、 前端工程规范（禁止超大单文件代码）

为防止前端代码随着页面和工具数量增加而迅速膨胀为难以维护的“千行巨型组件”，制定以下**强制性工程红线**：

### 1. 单文件代码体量红线
- **硬性上限**：**单个 `.tsx` 或 `.ts` 文件代码行数严禁超过 250 行**！日常组件推荐控制在 **100 ~ 180 行**；
- **拆分标准**：一旦组件超过 200 行，必须按职责拆分为：
  - `types.ts`（类型定义）
  - `useXxx.ts`（自定义 Hook，收拢交互逻辑与数据拉取）
  - `SubComponent.tsx`（子视图渲染原子）。

### 2. 标准目录分层结构
```
src/
├── api/                       # 后端 API 接口与 WebSocket 通信模块
│   ├── client.ts              # Axios / Fetch 客户端基类
│   ├── topology.ts            # GitFlow 拓扑与工作树接口
│   ├── session.ts             # 会话操作与投递接口
│   └── settings.ts            # MCP / 模型 / Skill 配置接口
├── assets/                    # 静态资源 (SVG 特殊徽标、品牌渐变等)
├── components/                # 纯粹的 UI 视图组件层 (严格遵循原子化)
│   ├── common/                # 通用基础原子组件 (Button, Input, Dropdown, Modal, Switch)
│   ├── layout/                # 3 栏弹性布局脚手架与拖拽手柄
│   ├── sidebar/               # 左侧边栏模块 (BrandHeader, NavList, ProjectTree, UserProfile)
│   ├── composer/              # 中间主对话与输入控制台 (GlassConsole, ModelSelector, PlusMenu)
│   ├── tools/                 # 右侧 10 大工具专属组件包
│   │   ├── diff/              # 工具 1: 变更与差异
│   │   ├── files/             # 工具 2: 文件预览浏览
│   │   ├── terminal/          # 工具 3: xterm 终端
│   │   ├── sidechat/          # 工具 4: 侧边隔离聊天
│   │   ├── subagents/         # 工具 5: 子智能体列表与详情
│   │   ├── metrics/           # 工具 6: 指标监控看板
│   │   ├── mcp/               # 工具 7: MCP 市场与管理
│   │   ├── skills/            # 工具 8: Skill 技能市场与管理
│   │   ├── gitflow/           # 工具 9: GitFlow 拓扑与分支操作
│   │   └── workflow/          # 工具 10: 分组管理与实时工作流编排
│   └── dialogs/               # 全局独立弹窗 (新建任务、新建分组、添加模型等)
├── hooks/                     # 业务自定义 Hooks (解耦所有事件与计算)
│   ├── useLayoutResize.ts     # 左右侧栏拖拽与中间区域自适应逻辑
│   ├── useSessionState.ts     # 活跃会话与流式消息
│   └── useProjectBinding.ts   # 项目本地文件夹选择与绑定
├── stores/                    # Zustand 状态存储 (轻量独立切片)
│   ├── layoutStore.ts         # 侧栏展开/收起、拖拽宽度、最大化状态
│   ├── sessionStore.ts        # 历史会话、活跃会话、消息列表
│   ├── projectStore.ts        # 当前项目、多项目绑定列表、分组信息
│   └── toolTabsStore.ts       # 右侧多标签页增删、激活 Tab 状态
└── styles/                    # 全局样式与 Nocturne Glass 设计令牌 (tokens.css)
```

### 3. UI 视图与业务逻辑严格分离 (Hook-and-Store Rule)
- **禁止在 JSX 中嵌入复杂数据过滤、网络请求或深层状态变换**；
- 页面组件只做“展示 + 派发事件”，数据拉取与流转统一移入 `stores/` 或 `hooks/`；
- **全量矢量图标规范**：一律引入 `lucide-react`，严格禁止在组件中直接书写超长原生 `<svg>` 代码段，所有自定义图标（如品牌 V Logo）必须封装为单独的图标组件（`<VeraLogo size={22} />`）。

---

## 三、 视窗布局系统与弹性伸缩机制（核心前端细节）

严格对齐 [UI_IMPLEMENTATION_LEGACY.md](UI_IMPLEMENTATION_LEGACY.md) 第 4 节中的交互规范：

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [V Logo] [◫] [←] [→]            [ ◫  ⛶ ] (中间总控)            [⊕ 新标签页 x] [+]  [⛶] [◫] │
├─────────────────────┬──────────────────────────────────────────┬───────────────────────┤
│                     │ 拖拽手柄 1                      拖拽手柄 2 │                       │
│    左侧边栏 (L)      │ │                                      │ │      右侧边栏 (R)     │
│   (Max 40%, Min 15%) │ │          中间主对话区 (C)             │ │    (Max 60%, Min 15%) │
│                     │ │      (最小保障 20% / 最大居中 50%)     │ │                     │
└─────────────────────┴─┴────────────────────────────────────────┴─┴───────────────────────┘
```

### 1. 三处折叠/展开按钮的具体联动定义
1. **第一处**：左侧边栏右上角 `[ ◫ ]`（折叠/展开左侧边栏）；
2. **第二处**：主对话区域右上角的总控按钮组 `[ ◫  ⛶ ]`：
   - 包含：左侧边栏开关、底部终端开关（在中间区域底部滑出轻量终端抽屉）、右侧边栏开关；
3. **第三处**：右侧边栏右上角 `[ ◫ ]`（收起/打开右侧标签页面板）。

### 2. 鼠标拖拽调整大小与边界响应法则 (Boundary Physics)
- **拖拽控制**：鼠标悬停在区域边界手柄（Resize Handle）时出现 `col-resize` 光标，按住可横向拖拽调整；
- **左侧边栏 (L)**：
  - 最大宽度：占屏幕宽度 **40%**；
  - 最小折叠门限：拖动到页面占比 **< 15%** 时自动吸附收起（完全折叠为 0）；
- **右侧边栏 (R)**：
  - 常规拖动最大宽度：占屏幕宽度 **40% ~ 50%**；
  - 极端拖动最大宽度：**允许达到 60%**；
  - **中间区保护逻辑**：一旦中间对话区域宽度被压缩至 **< 20%**，系统判定进入右侧聚焦态，右侧边栏自动扩大到 **60%**，中间主对话区自动隐去；
  - 最小折叠门限：拖拽到 **< 15%** 时自动收起；
- **中间主对话区域 (C) 居中与自适应**：
  - 即使左右两侧边栏全部关闭，中间对话区域的最大宽度仍限制为**屏幕居中 50%**（保证可读性与聚焦体验，不盲目拉伸成超长宽条）；
  - 整个对话区域伴随侧栏伸缩**平滑微移**：例如当左侧边栏展开时，中间对话区适度向右移动（微调偏移量约为侧栏展开量的 20%~30%，而非生硬 1:1 挤压），保持全局视觉平衡。

### 3. 右侧边栏最大化逻辑 (Maximize Behavior)
- 点击右侧边栏顶部 `[ ⛶ ]` 按钮触发最大化：
  - 中间对话区域暂时隐去，右侧边栏直接向左延伸填满空间；
  - 若左侧边栏开启，则呈现“左侧边栏 + 右侧全屏边栏”双栏态，此时允许拖拽中线动态调整左右比例；
  - 若左侧边栏也关闭，则右侧边栏占满整个窗口 100%；再次点击 `[ ⛶ ]` 恢复原三栏比例。

### 4. 标签页空白态与多 Tab 规则 (Tab Behavior)
- **初始态**：右侧首次打开必为 `新标签页`（工具快捷启动中心）；
- **关闭全部**：若用户点击 `x` 删除了最后一个标签页，右侧呈现干净的**空白占位态**；
- **新建 Tab**：点击标签栏右侧的 `[+]` 按钮，永远是**新开辟一个新标签页**，严禁在当前已有标签页上直接覆盖。

---

## 四、 Penpot 原型与文档 100% 严格对齐映射清单

在 Penpot 中已创建的 26 个画板与 [UI_IMPLEMENTATION_LEGACY.md](UI_IMPLEMENTATION_LEGACY.md) 中的业务逻辑**严格对齐，零文案修改**：

| Penpot 原型画板名称 | 对应功能区域 / 模块定位 | 触发入口与交互动作 | 目标跳转与状态行为 |
| :--- | :--- | :--- | :--- |
| **`VeraAgent · Conversation Workspace`** | 核心主画板 (三栏工作台) | 应用初始默认主界面 | 承载左侧边栏、中间对话区、右侧工具栏 |
| **`History · 对话历史`** | 左侧导航 1：历史对话列表 | 点击左侧边栏 `历史对话` | 全屏/主区覆盖展示历史会话卡片与搜索框 |
| **`Scheduled Tasks · 定时任务`** | 左侧导航 2：定时任务列表 | 点击左侧边栏 `计划任务` | 展示已排期 Cron/Interval 任务流水 |
| **`Scheduled task · Dialog only`** | 定时任务新建弹窗 | 在定时任务面板中点击 `【新建任务】` | 弹出模态框设置触发周期与执行提示词 |
| **`Project selector · Dropdown only`** | 项目选择浮窗菜单 | 点击输入框上方 `选择项目` 或左侧 `带+文件夹` | 弹出项目下拉列表或绑定本地物理文件夹 |
| **`系统设置 · 权限审批`** | 设置模块 1：权限门禁 | 点击左侧边栏底栏 `设置` | 呈现自动授权模式、高危操作阻断策略 |
| **`系统设置 · MCP`** | 设置模块 2：MCP 服务器列表 | 在设置面板切换 Tab: `MCP` | 呈现已安装 MCP 列表、滑动开关与齿轮操作 |
| **`MCP · Add menu only`** | MCP 添加快捷菜单浮窗 | 在系统设置 · MCP 中点击 `添加` | 浮窗菜单呈现：`从市场添加` / `手动配置` |
| **`MCP · Marketplace dialog only`** | MCP 市场弹窗 (Marketplace) | 在 MCP 菜单中点击 `从市场添加` | 弹出官方精选 MCP 插件中心卡片流 |
| **`MCP · Manual configuration dialog only`**| MCP 手动 JSON 配置弹窗 | 点击 `手动配置` 或在已有项齿轮点击 `编辑` | 弹出完整 JSON/命令行配置面板，回显旧数据 |
| **`系统设置 · 模型配置`** | 设置模块 3：模型服务与密钥 | 在设置面板切换 Tab: `模型配置` | 呈现已启用模型、供应商、开关与编辑 |
| **`模型 · 添加模型（高级配置展开）`** | 添加/编辑模型专属弹窗 | 点击 `+ 添加模型` 或已有模型齿轮点 `编辑` | 弹出模型配置，默认收起高级，回显原有字段 |
| **`系统设置 · Skill`** | 设置模块 4：Skill 生态管理 | 在设置面板切换 Tab: `Skill` | 展示本地与生态技能列表，带删除与启用 |
| **`系统设置 · 规则与记忆`** | 设置模块 5：项目级 AGENTS 规则 | 在设置面板切换 Tab: `规则与记忆` | 编辑项目通用公理、Prompt 约束与记忆库 |
| **`侧边聊天 · 空状态`** | 右侧工具 4：独立隔离侧边对话 | 在右侧工具矩阵点击 `侧边聊天` | 打开新 Tab 侧边聊天，关闭即清空，支持探查主上下文 |
| **`文件 · 预览与文件浏览`** | 右侧工具 2：代码与目录工作树 | 在右侧工具矩阵点击 `文件` | 打开新 Tab 展示当前绑定项目物理文件树与源码 |
| **`文件 · 变更与差异`** | 右侧工具 1：Git 暂存审查 | 在右侧工具矩阵点击 `变更` | 打开新 Tab 审查 Unified Diff、支持暂存撤销 |
| **`子智能体 · 列表`** | 右侧工具 5：调研员/审查员看板 | 在右侧工具矩阵点击 `子智能体` | 列出当前会话挂载的 Subagent 状态 |
| **`子智能体 · 结果详情`** | 子智能体交付详情报告 | 在子智能体列表中点击某项条目 | 展示只读调研摘要或代码审查 Gate 决策报告 |
| **`GitFlow · 右侧工具`** | 右侧工具 9：分支拓扑主视图 | 在右侧工具矩阵点击 `GitFlow` | 呈现分支拓扑图，支持缩放、新增/合并分支 |
| **`GitFlow · 分支节点操作`** | 分支节点管理弹窗/右侧抽屉 | 双击拓扑图中的某个特定分支节点 | 弹出分支检出、一键自愈回滚、发起 Merge 审查 |
| **`分组管理 · 列表`** | 右侧工具 10：业务组管理主页 | 在右侧工具矩阵点击 `分组管理` | 展示当前项目下划分的研发工作组 |
| **`指标看板 · 右侧工具`** | 右侧工具 6：实时消耗看板 | 在右侧工具矩阵点击 `指标监控` | 实时监控 Token 速率、调用次数、费用估算 |
| **`分组管理 · 创建分组`** | 新建业务分组抽屉/面板 | 在分组管理列表中点击 `新建分组` | 填写组名称、绑定 Git Worktree 物理分支 |
| **`分组管理 · 基本信息与模板`** | 分组详情与模板挂载 | 点击分组列表中已创建的具体分组 | 展示项目归属（项目级隔离）、绑定流水线模板 |
| **`分组管理 · 实时工作流编排`** | 节点流可视化编排画布 | 在分组详情中点击 `工作流编排` | React Flow 画布拖拽配置节点，点击发布生效 |

---

## 五、 核心界面完整实施规范与组件清单

### 5.1 主工作台 (VeraAgent Conversation Workspace)
- **原型文件对应**：画板 `VeraAgent · Conversation Workspace`（1600 × 900）。
- **色彩与材质 Tokens**：
  - 背景画布：`#0D0E12`（曜石深邃灰）；
  - 氛围流光：低透明度夜蓝微光（`#1E1B4B`，高斯模糊 120px，仅充当微弱底光）；
  - 侧栏表面：`#111217`，边框线：`1px solid #1E2028`。
- **组件结构拆分**：
  - `src/components/layout/WorkspaceShell.tsx`（根布局，承载 3 栏）
  - `src/components/layout/ResizeHandle.tsx`（拖拽分界线手柄）

---

### 5.2 左侧边栏 (Left Sidebar)
- **尺寸基准**：默认宽度 250px，允许拖拽范围 15%~40%。
- **界面元素严格对齐清单**：
  1. **顶栏 (Row 1)**：
     - **品牌 V Logo**：矢量渐变紫蓝图标（22×22px）；
     - **3 联微控件**：`[ ◫ ]`（折叠侧栏，Lucide `PanelLeft`）、`[ ← ]`（后退，Lucide `ChevronLeft`）、`[ → ]`（前进，Lucide `ChevronRight`）；
  2. **主操作大按钮**：
     - `+ 新建对话`（背景 `#1A1C24`，圆角 8px，边框 `#2A2C38`，文字 `#ECEEF2`，图标 Lucide `Plus`）；
  3. **导航列表行 (无卡片，纯粹列表行)**：
     - `历史对话`（图标 Lucide `History`，点击跳转 `History · 对话历史` 画板）；
     - `计划任务`（图标 Lucide `Clock`，点击跳转 `Scheduled Tasks · 定时任务` 画板）；
  4. **项目区 (Projects)**：
     - 分组标题：`项目`（文字 11px，颜色 `#636779`）；
     - 标题右侧工具图标：`[ ☷ ]`（筛选，Lucide `Filter`）、`[ + ]`（绑定本地文件夹，调起系统目录选择器，打开 `Project selector · Dropdown only`）；
     - 树形结构渲染：
       - 项目条目：`📁 项目名称`（图标 Lucide `Folder`）；
       - 右侧悬停图标：`[ ⋮ ]`（操作）、`[ + ]`（创建新会话）；
       - 缩进挂载子条目：`对话`（圆角矩形选中高亮框，边框 `#3B4254`，右侧常驻 `[ ⋮ ]` `[ 📌 ]` `[ + ]`）；
       - 点击 `[ ⋮ ]` 必须弹出原生菜单：包含 **“置顶”、“删除”、“重命名”、“归档”**。
  5. **通用会话区 (Conversations)**：
     - 分组标题：`会话`，右侧带 `[ + ]`（快速创建独立无项目会话）；
     - 会话条目：`对话`，右侧悬停展示 `[ ⋮ ]` `[ 📌 ]` `[ + ]`；
  6. **底栏**：
     - `⚙ 设置`（图标 Lucide `Settings`，点击直达 `系统设置 · 权限审批`）。
- **组件拆分**：
  - `src/components/sidebar/LeftSidebar.tsx`（容器）
  - `src/components/sidebar/ProjectTree.tsx`（项目与会话树形行）
  - `src/components/sidebar/ConversationContextMenu.tsx`（“置顶/删除/重命名/归档”下拉菜单）

---

### 5.3 中间主对话区 (Center Composer Workspace)
- **尺寸基准**：弹性宽度，限制最大居中 50% 显示。
- **界面元素严格对齐清单**：
  1. **顶栏右上角总控组**：
     - 胶囊控件 `[ ◫  ⛶ ]`（青色微光边框 `#155E75`，图标 Lucide `SplitSquareVertical` 与 `Maximize`）；
  2. **项目选择浮动胶囊 (Project Selector Capsule)**：
     - 位置：**输入框左上方常驻悬浮**；
     - 结构：`[ 📁 选择项目 ]`（背景 `#161720`，边框 `#222530`，点击调起 `Project selector · Dropdown only`）；
  3. **悬浮签名卡片式输入框 (Signature Input Card)**：
     - 尺寸：740×116px，圆角 16px，半透明磨砂黑玻璃（`#14151D`，边框 `1px solid #222530`，大柔和阴影）；
     - 多行文本区：占位提示文字严格为 `Ask anything, / for actions`（颜色 `#636779`）；
     - 输入键盘监听：输入 `/` 时自动定位光标并弹出 `Composer · Plus dropdown only`；
     - 底栏工具条：
       - 左侧一：`+` 按钮（唤醒 `Composer · Plus dropdown only` 浮窗，供用户勾选启用的 MCP / Skill）；
       - 左侧二：`模型切换 ▾`（点击展开下拉列表，显示已启用的模型名称，快速切换）；
       - 右侧一：`🎙` 麦克风图标（Lucide `Mic`）；
       - 右侧二：`→` 发送按钮（圆形/圆角方块 `#222530`，白色箭头，按 Enter 触发执行）。
- **组件拆分**：
  - `src/components/composer/CenterWorkspace.tsx`（主画布）
  - `src/components/composer/GlassInputCard.tsx`（输入卡片）
  - `src/components/composer/ComposerPlusMenu.tsx`（“+”与“/”能力弹出菜单）

---

### 5.4 右侧多标签页容器与 10 大工具体系 (Right Tool Tab Container)
- **尺寸基准**：默认宽度 480px~520px，支持拖拽与最大化。
- **顶部标签栏 (Tab Strip)**：
  - 激活标签：`[ ⊕ 新标签页 x ]`（深色微底 `#1A1C24`，带关闭 `x`）；
  - 右侧控制：`[ + ]`（开辟新标签页）、`[ ⛶ ]`（最大化）、`[ ◫ ]`（收起右侧边栏）；
  - 标签管理规范：**严格按项目进行物理与状态隔离**！
- **新标签页首页 (工具快捷启动中心，8~10 卡片矩阵)**：
  - 标题：`工具`（加粗 15px `#F4F4F6`）；
  - 矩阵排版：**4 行 × 2 列**，每个卡片尺寸 218×52px，圆角 8px，背景 `#161720`，边框 `#222530`：
    - 行 1：`[ 🗲 变更 ]`（跳转 `文件 · 变更与差异`） | `[ ⌨ 终端 ]`（新标签页内嵌 `xterm.js`）
    - 行 2：`[ 📄 文件 ]`（跳转 `文件 · 预览与文件浏览`） | `[ 💬 侧边聊天 ]`（跳转 `侧边聊天 · 空状态`）
    - 行 3：`[ 👤 子智能体 ]`（跳转 `子智能体 · 列表`） | `[ 指标监控 ]`（跳转 `指标看板 · 右侧工具`）
    - 行 4：`[ MCP 市场 ]`（复用系统设置 MCP 市场） | `[ SKILL 市场 ]`（复用系统设置 Skill 市场）
    - 拓展工具入口：`[ GitFlow ]`（跳转 `GitFlow · 右侧工具`）、`[ 分组管理 ]`（跳转 `分组管理 · 列表`）。
- **10 大工具独立实施规范**：
  1. **工具 1: 文件 · 变更与差异 (`DiffViewerTab.tsx`)**：
     - 展示当前工作树的 Git Diff 对比（Unified / Split 视图），支持单文件暂存、撤销与冲突标记；
  2. **工具 2: 文件 · 预览与文件浏览 (`FileExplorerTab.tsx`)**：
     - 展示本地项目物理文件树，右侧预览代码，支持代码高亮与行号；
  3. **工具 3: 终端 (`TerminalTab.tsx`)**：
     - 基于 `xterm.js` 接入后端 PTY / Docker 执行流，支持用户直接键盘交互与颜色输出；
  4. **工具 4: 侧边聊天 (`SideChatTab.tsx`)**：
     - **业务哲学**：轻量级临时会话，不污染主对话上下文。默认仅继承主对话关键摘要，支持一键“探查主对话上下文并挂载”；关闭该 Tab 时内容立即清空；
  5. **工具 5: 子智能体 (`SubagentsTab.tsx` & `SubagentDetailTab.tsx`)**：
     - 列表呈现调研员 (Researcher) 与审查员 (Reviewer) 的挂载态；
     - 点击列表项滑入详情，查看单向交接摘要（Handover Summary）与预合并审查结论；
  6. **工具 6: 指标看板 (`MetricsTab.tsx`)**：
     - 实时渲染 Token 吞吐速率、总字符消耗、累计成本（USD/CNY）、API 调用频次计数图表；
  7. **工具 7: MCP 市场 (`MCPMarketplaceTab.tsx`)**：
     - 开源生态中精选 MCP 工具列表，支持一键“安装到本地”与环境依赖检测；
  8. **工具 8: Skill 市场 (`SkillMarketplaceTab.tsx`)**：
     - 扫描 `.agents/skills` 与公共市场，支持快速启用/禁用专属工作流提示词包；
  9. **工具 9: GitFlow 可视化 (`GitFlowTab.tsx`)**：
     - 基于 React Flow 渲染分支状态图，支持画布平移缩放；
     - 双击分支节点打开 `GitFlow · 分支节点操作` 抽屉，支持检出、快照创建（Checkpoint）、合并（Merge Review）；
  10. **工具 10: 分组管理与实时编排 (`WorkflowTab.tsx`)**：
      - 分组列表 -> 点击 `新建分组` 弹出创建抽屉 -> 进入 `基本信息与模板` -> 点击 `实时工作流编排` 在 React Flow 画布中连线拖拽生成节点，点击 `发布` 后正式落地。

---

### 5.5 历史对话与定时任务体系
1. **History · 对话历史**：
   - 顶部搜索框：支持**全文本检索与归档会话检索**（归档会话在此处自动匹配，支持一键“取消归档”）；
   - 卡片列表：展示会话标题、关联项目、最后修改时间、Token 消耗量。
2. **Scheduled Tasks · 定时任务**：
   - 列表展示当前排期运行的 Cron / Interval 任务；
   - 点击顶部 `【新建任务】` 按钮，弹出 `Scheduled task · Dialog only`：输入任务名称、Cron 表达式、指定会话或 Agent 执行提示词。

---

### 5.6 系统设置中心五大模块 (Settings Center)
- **统一样式**：左侧 5 个垂直 Tab 切换，右侧宽面板配置。
- **五大 Tab 规范**：
  1. **Tab 1: 权限审批 (`SettingsPermissions.tsx`)**：
     - 权限模式选择（自动执行 / 结构化 Y/N/O 审批）、高危 Bash 命令黑名单阻断设置；
  2. **Tab 2: MCP (`SettingsMCP.tsx`)**：
     - 点击顶部 `添加` 弹出 `MCP · Add menu only`（`从市场添加` / `手动配置`）；
     - 列表项：左侧名称与状态，最右侧**滑动开关（Switch）**控制启停；开关左侧**齿轮图标**点击展开下拉菜单（`编辑`、`重启`、`删除`）；
     - 点击 `编辑` 必须跳转到 `MCP · Manual configuration dialog only` 并**严格回显已有配置数据，严禁重置清空**；
  3. **Tab 3: Skill (`SettingsSkill.tsx`)**：
     - 展示本地扫描发现的 SKILL.md，提供开关控制与删除按钮；
  4. **Tab 4: 模型配置 (`SettingsModels.tsx`)**：
     - 点击 `+ 添加模型` 弹出 `模型 · 添加模型（高级配置展开）`；
     - 字段：供应商、模型标识、Base URL、API Key，**高级设置（Temperature、Context Window、Max Tokens）默认折叠收起**；
     - 列表项右侧带滑动开关与齿轮操作（编辑/删除），点击 `编辑` 同样回显配置数据；
  5. **Tab 5: 规则与记忆 (`SettingsRules.tsx`)**：
     - 编辑项目级 `AGENTS.md` / 全局通用规则约束与记忆持久化。

---

### 5.7 全局关键浮窗与弹窗体系 (Modals & Overlays)
- **Project selector · Dropdown only**：
  - 尺寸：306×220px；列出已绑定的本地项目，底部提供 `[+ 新建项目绑定本地文件夹]`；
- **Composer · Plus dropdown only**：
  - 尺寸：约 280×300px；列出已启用的 MCP 工具、可用 Skills 以及快速斜杠指令；
- **MCP · Add menu only**：
  - 尺寸：220×112px；两个选项：`从市场添加` / `手动配置`；
- **Scheduled task · Dialog only**：
  - 尺寸：640×752px；表单式模态框。

---

## 六、 后端 API 接口与数据契约映射表

前端所有交互动作均与项目中已构建的 **Starlette ASGI Web Control API (`server/app.py`)** 及底层模块严格打通，严禁自行臆造接口：

| 前端操作 / 界面触发 | 后端 API 端点 | HTTP 方法 | 请求体载荷 (Payload) / 响应结构 | 对应后端业务核心 |
| :--- | :--- | :--- | :--- | :--- |
| **拉取 GitFlow 拓扑** | `/api/topology` | `GET` | 响应: `{ nodes: GraphNode[], edges: GraphEdge[] }` | `GitFlowGraph.export_react_flow_topology()` |
| **创建新业务组** | `/api/groups` | `POST` | `{ group_id, name, worktree_path, base_branch }` | `ProjectGroup` + `WorktreeManager` 物理创建 |
| **挂载会话到分支** | `/api/sessions/attach` | `POST` | `{ group_id, thread_id }` | `GitFlowGraph.attach_session()` |
| **解除会话挂载** | `/api/sessions/detach` | `POST` | `{ thread_id }` | `GitFlowGraph.detach_session()` |
| **创建工作树快照** | `/api/worktrees/checkpoint`| `POST` | `{ group_id, message }` | `WorktreeManager.create_checkpoint()` |
| **工作树自愈回滚** | `/api/worktrees/reset` | `POST` | `{ group_id, hard: true }` | `WorktreeManager.reset_worktree()` |
| **PR 3-Way 冲突审查** | `/api/merge-review` | `POST` | `{ source_branch, target_branch }` | 纯内存 3-way Merge 冲突探测 |
| **获取可用 Skill** | `/api/skills` | `GET` | 响应: `{ skills: SkillMetadata[] }` | `SkillManager.list_skills()` 动态扫描 |
| **AST 代码语法预检** | `/api/code/check-syntax` | `POST` | `{ code_content }` | `code_tools.check_syntax_op()` |
| **AST 符号快速检索** | `/api/code/search-symbols`| `POST` | `{ root_dir, symbol_name }` | `code_tools.symbol_search_op()` |
| **会话消息投递** | `/api/messages/send` | `POST` | `{ thread_id, content, sender_id }` | `SessionRouter` 异步消息总线投递 |

---

## 七、 界面设计与工程实施自检清单 (Self-Inspection Checklist)

前端工程师在开发完成每个组件后，必须根据以下清单进行**严格逐项自检**，未通过自检不得提交代码：

### 1. Penpot 视觉与文字一致性自检 (Zero-Deviation Check)
- [ ] **文案完全对齐**：检查页面中的每个文字，是否与 Penpot 原型和 `UI_IMPLEMENTATION_LEGACY.md` 完全一致？（例如：`新建对话`、`历史对话`、`计划任务`、`项目名称`、`选择项目`、`Ask anything, / for actions`、`模型切换 ▾` 等，严禁随意更名）；
- [ ] **布局排版对齐**：左侧边栏是否为列表行而非卡片？项目是否包含折叠树与双方框/加号图标？右侧是否为 4 行 2 列工具卡片？
- [ ] **全量矢量图标**：是否彻底摒弃位图与散乱 XML？是否全部使用规范化的 `lucide-react` 图标组件？
- [ ] **暗夜玻璃拟态**：底色是否锁定为 `#0D0E12`？容器是否采用深色低透明磨砂（`#111217` / `#161720`）并辅以 `1px solid #1E2028` 极细高光边？

### 2. 代码体量与工程规范自检 (Anti-Bloat Check)
- [ ] **单文件行数红线**：没有任何一个 `.tsx` 文件超过 250 行代码；
- [ ] **逻辑彻底解耦**：组件内不存在大块 `fetch`/状态计算代码，所有逻辑是否已抽离为 `hooks/` 和 `stores/`？
- [ ] **强类型约束**：所有接口数据模型是否完整匹配 TypeScript 类型，未出现任何 `any` 逃逸？

### 3. 弹性窗口与物理边界自检 (Resize & Maximize Check)
- [ ] **折叠控件三处就位**：左侧顶栏折叠、中间区总控三联按钮、右侧顶栏折叠均可正常工作；
- [ ] **拖拽限制生效**：左侧拖拽限制在 15%~40%，右侧限制在 15%~60%，中间区 <20% 时触发右侧放大 60% 且中间区隐去；
- [ ] **居中保障生效**：全收起侧边栏时，主对话卡片依然优雅居中，宽度限制在 50% 视窗内；
- [ ] **右侧最大化与标签页**：点击 `[ ⛶ ]` 能够平滑挤占中间空间并同步中线拖拽；删除全部标签显示空白，点击 `+` 开辟新 Tab。

### 4. 状态持久化与回显自检 (State Persistence Check)
- [ ] **配置回显**：点击 MCP 或模型条目的“编辑”时，原有的配置内容（JSON、API Key、URL）是否完好回显，未被初始化清空？
- [ ] **侧边聊天隔离**：侧边聊天是否保持独立对话环境，不污染主会话；关闭侧边栏 Tab 是否完成临时数据清空？
- [ ] **项目级隔离**：右侧边栏开启的所有工具状态，切换不同项目时是否做到彻底物理隔离？
