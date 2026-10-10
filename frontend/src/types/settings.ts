export interface ModelConfig {
  id: string;
  name: string;
  display_name?: string;
  provider: string;
  base_url?: string;
  api_key?: string;
  max_tokens?: number;
  temperature?: number;
  model_family?: string;
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
  default_mode: 'confirm' | 'yolo' | 'human';
  whitelist_actions: string[];
  operation_scope?: 'project_only' | 'project_write_external_readonly';
  max_tool_attempts?: number;
}

export interface McpTool {
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
}

export interface SkillItem {
  name: string;
  description: string;
  category?: string;
  path?: string;
  enabled?: boolean;
}
