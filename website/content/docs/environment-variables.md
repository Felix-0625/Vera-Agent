# 环境变量表

桌面应用**没有必填环境变量**：模型凭据在设置界面填写。表中变量用于启动、开发代理、Python CLI、特定工具或测试。进程环境变量优先于 Python `.env`；历史 `MSWEA_*` 名称保留兼容，有 `VERA_*` 别名时优先使用后者。

| 变量 | 使用位置 | 作用 | 默认 |
| --- | --- | --- | --- |
| `VERA_GLOBAL_CONFIG_DIR` | Python 初始化 | CLI `.env` 所在目录；兼容 `MSWEA_GLOBAL_CONFIG_DIR` | 平台用户配置目录 |
| `VERA_SILENT_STARTUP` | Python 初始化 | 隐藏启动横幅；兼容 `MSWEA_SILENT_STARTUP` | 未设置 |
| `VERA_AGENT_BASH_PATH` | 本地命令工具 | 指定 Git for Windows 的 `bash.exe` | 自动查找 |
| `VERA_AGENT_DESKTOP_URL` | 桌面窗口 | 改为加载指定前端 URL | 构建后的前端 |
| `VERA_MINI_CONFIG_PATH` | 继承的 CLI | CLI YAML 配置；兼容 `MSWEA_MINI_CONFIG_PATH` | 内置 `mini.yaml` |
| `VERA_RUN_NETWORK_TESTS` | 后端测试 | `1` 时运行公共网络测试 | 未设置 |
| `MSWEA_MODEL_NAME` | Python 模型适配器 | CLI 未指定模型时的默认模型 | 未设置 |
| `OPENROUTER_API_KEY` | OpenRouter 适配器 | Python 适配器的 OpenRouter 密钥 | 未设置 |
| `PORTKEY_API_KEY` | Portkey 适配器 | 网关密钥 | 未设置 |
| `PORTKEY_VIRTUAL_KEY` | Portkey 适配器 | 虚拟密钥 | 未设置 |
| `REQUESTY_API_KEY` | Requesty 适配器 | Requesty 密钥 | 未设置 |
| `TAVILY_API_KEY` | Web 搜索工具 | 使用 Tavily；缺省改用 DuckDuckGo | 未设置 |
| `LITELLM_MODEL_REGISTRY_PATH` | LiteLLM 适配器 | 自定义模型成本/上下文元数据 JSON | 未设置 |
| `MSWEA_COST_TRACKING` | 模型适配器 | `default` 或 `ignore_errors` | `default` |
| `MSWEA_GLOBAL_COST_LIMIT` | 模型适配器 | 进程级美元费用上限；`0` 关闭 | `0` |
| `MSWEA_GLOBAL_CALL_LIMIT` | 模型适配器 | 进程级模型调用上限；`0` 关闭 | `0` |
| `MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT` | 模型重试 | 单次请求最多尝试次数 | `10` |
| `VITE_API_BASE_URL` | 前端构建 | 编入界面的 API 地址；桌面启动脚本设置它 | 开发同源；桌面默认 `http://127.0.0.1:8000` |
| `VITE_API_PROXY_TARGET` | Vite 开发服务 | `npm run dev` 的 `/api` 代理目标 | `http://127.0.0.1:8000` |

`ANTHROPIC_API_KEY`、`OPENAI_API_KEY`、`DEEPSEEK_API_KEY` 等服务商变量只在使用相应 Python CLI/LiteLLM 适配器时读取；桌面应用从模型设置传入密钥。不要把真实密钥写入源码、网站、截图或共享的 `.env`。维护基准见[仓库配置文档](../../../docs/CONFIGURATION.md#environment-variables)。

## 仅供 CLI 配置向导使用的变量

以下两个变量只在运行继承自 mini-swe-agent 的 `mini-extra config` 命令（配置向导，非桌面应用路径）时生效，桌面应用启动和运行过程不会读取它们：

| 变量 | 使用位置 | 作用 | 默认 |
| --- | --- | --- | --- |
| `MSWEA_CONFIGURED` | `run/utilities/config.py` | 标记是否已完成过一次 `config setup` 向导；设置后跳过首次引导 | 未设置 |
| `EDITOR` | `run/utilities/config.py` | `mini-extra config edit` 用来决定打开哪个文本编辑器 | `nano` |

基准测评专用的环境执行器变量（`MSWEA_DOCKER_EXECUTABLE`、`MSWEA_SINGULARITY_EXECUTABLE`、`MSWEA_BUBBLEWRAP_EXECUTABLE`、`MSWEA_CONFIG_DIR`）记录在上游 mini-swe-agent 文档中，同样不被桌面应用使用，这里不重复列出。
