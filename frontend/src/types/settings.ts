/**
 * Model profile, permission, MCP, and Skill settings types.
 *
 * `ModelProvider` must match the backend allow-list in `server/routes/settings.py` (checked by modelProviders.test.ts).
 */
export type ModelProvider =
  | 'openai'
  | 'anthropic'
  | 'google'
  | 'deepseek'
  | 'openrouter'
  | 'ollama'
  | 'qwen'
  | 'zhipu'
  | 'moonshot'
  | 'siliconflow'
  | 'volcengine'
  | 'xai'
  | 'mistral'
  | 'custom';
export type PermissionCategory = 'read' | 'create' | 'edit' | 'terminal' | 'search' | 'mcp' | 'delegation';

export interface ModelConfig {
  id: string;
  name: string;
  display_name?: string;
  provider: ModelProvider;
  base_url?: string;
  api_key?: string;
  max_tokens?: number;
  temperature?: number;
  context_window?: number;
  output_tokens?: number;
  max_tool_calls?: number;
  supports_images?: boolean;
  thinking_mode?: 'auto' | 'enabled' | 'disabled';
  top_p?: number;
  top_k?: number;
  is_default?: boolean;
  enabled?: boolean;
}

export interface PermissionsConfig {
  default_mode: 'allow_all' | 'auto' | 'manual';
  approval_actions: PermissionCategory[];
  operation_scope?: 'project_only' | 'project_write_external_readonly';
  max_tool_attempts: number;
}

interface McpTool {
  name: string;
  description: string;
}

export interface McpServerConfig {
  id: string;
  name: string;
  type: string;
  status: 'running' | 'stopped';
  enabled: boolean;
  command: string;
  args: string[];
  env?: Record<string, string>;
  tools: McpTool[];
  repository?: string;
  registry_version?: string;
  url?: string;
  transport?: string;
  headers?: Record<string, string>;
  registry_id?: string;
}

export interface SkillItem {
  name: string;
  description: string;
  category?: string;
  path?: string;
  enabled?: boolean;
}
