# VeraAgent 落地页内容源

这里存放网站各页面的中文 Markdown 文案。设计页和文档页由静态页面直接读取相应 Markdown 并渲染；首页和交互演示仍由各自的 HTML/JavaScript 实现。

| 网站入口 | 内容源 | 页面职责 |
| --- | --- | --- |
| 首页 | [home.md](home.md) | 说明 VeraAgent 是什么、展示工作站协作方式、引导体验与启动 |
| 设计 | [design/index.md](design/index.md) | 解释代码实现、运行架构、调用链、组织与工作流、数据和边界 |
| 文档 | [docs/index.md](docs/index.md) | 按任务查安装、启动、配置、变量、使用、接口和排错 |
| 演示视频 | [playground.md](playground.md) | 解释当前预设流程录屏和后续真实任务实录的边界 |

设计页和文档页均按**左侧目录、右侧正文**组织。页面内的标题可用作目录锚点；代码块、表格和提示框是正文组件，不另起一张“幻灯片”。

## 设计图稿

五张图均已提供中文、英文 SVG，并接入双语设计页。可编辑的原生节点、箭头、文字保存在 [system-design.drawio](../diagrams/system-design.drawio) 的十个分页中；[图库与说明](../diagrams/README.md)。

1. 运行架构：桌面 UI、本地 API、模型与工具、本地数据、外部模型边界。
2. 对话时序：共享 `run_turn`、七种 SSE 事件、审批独立请求与真实工具退出码。
3. 模板/实例/运行：隔离会话、前端串行调度、Supervisor 复核回传。
4. 本地数据：应用级与项目级 `.agents/`，SQLite、评测、提案、凭据与代码原目录。
5. 学习闭环：轨迹、记忆、Critic、三阶段门禁、确认采纳与用户触发监控回滚。

## 内容校对依据

- 产品、能力与边界：[中文 README](../../README_zh-CN.md)、[架构](../../docs/ARCHITECTURE.md)、[测试记录](../../docs/TESTING.md)
- 安装、变量、接口：[Windows 安装](../../docs/INSTALL_WINDOWS.md)、[配置](../../docs/CONFIGURATION.md)、[API](../../docs/API.md)
- 组织、工作流与本地数据：[数据模型](../../docs/DATA_MODEL.md)、[示例](../../examples/workflow-quickstart/README.md)

接口路由索引由仓库脚本生成，网站文案只解释常用契约，不复制整个索引。若代码与这里的文字冲突，应先核对代码并修正文案。
