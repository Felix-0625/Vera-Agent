import { ModelProvider } from '../../types/settings';

export const MODEL_PROVIDERS = [
  { id: 'openai', label: 'OpenAI', baseUrl: 'https://api.openai.com/v1' },
  { id: 'anthropic', label: 'Anthropic', baseUrl: 'https://api.anthropic.com' },
  { id: 'google', label: 'Google Gemini', baseUrl: 'https://generativelanguage.googleapis.com/v1beta' },
  { id: 'deepseek', label: 'DeepSeek', baseUrl: 'https://api.deepseek.com' },
  { id: 'openrouter', label: 'OpenRouter', baseUrl: 'https://openrouter.ai/api/v1' },
  { id: 'ollama', label: 'Ollama（本地）', baseUrl: 'http://localhost:11434' },
  { id: 'qwen', label: '阿里云百炼 / Qwen', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { id: 'zhipu', label: '智谱 AI', baseUrl: 'https://open.bigmodel.cn/api/paas/v4' },
  { id: 'moonshot', label: '月之暗面 / Kimi', baseUrl: 'https://api.moonshot.cn/v1' },
  { id: 'siliconflow', label: '硅基流动', baseUrl: 'https://api.siliconflow.cn/v1' },
  { id: 'volcengine', label: '火山引擎 / 豆包', baseUrl: 'https://ark.cn-beijing.volces.com/api/v3' },
  { id: 'xai', label: 'xAI', baseUrl: 'https://api.x.ai/v1' },
  { id: 'mistral', label: 'Mistral AI', baseUrl: 'https://api.mistral.ai/v1' },
  { id: 'custom', label: '自定义兼容服务', baseUrl: '' },
] as const;

export const getProviderBaseUrl = (provider: ModelProvider): string => MODEL_PROVIDERS.find((item) => item.id === provider)?.baseUrl ?? '';
