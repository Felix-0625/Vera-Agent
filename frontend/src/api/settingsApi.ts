/**
 * Settings, MCP, and Skill client.
 *
 * Backend: `server/routes/settings.py` (`/api/settings/*`), `server/routes/mcp.py` (`/api/mcp/*`),
 * and `server/routes/skills.py` (`/api/skills*`).
 */
import { McpServerConfig, ModelConfig, PermissionsConfig, SkillItem } from '../types/settings';
import { request } from './client';

// 1. Models
export async function fetchModels(): Promise<{ models: ModelConfig[] }> {
  return request('/api/settings/models');
}

export async function patchModel(modelId: string, data: Partial<ModelConfig>): Promise<{ model: ModelConfig }> {
  return request(`/api/settings/models/${modelId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function createModel(data: ModelConfig): Promise<{ status: string }> {
  return request('/api/settings/models', {
    method: 'POST',
    body: JSON.stringify({ model: data }),
  });
}

export async function deleteModel(modelId: string): Promise<{ status: string }> {
  return request(`/api/settings/models/${modelId}`, {
    method: 'DELETE',
  });
}

export async function testModelConnection(model: {
  model_id?: string;
  name: string;
  provider?: string;
  api_key?: string;
  base_url?: string;
}): Promise<{ success: boolean; message?: string; error?: string }> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 12_000);
  try {
    return await request('/api/settings/models/test', {
      method: 'POST',
      body: JSON.stringify(model),
      signal: controller.signal,
    });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

// 2. Permissions & Rules
export async function fetchPermissions(): Promise<PermissionsConfig> {
  return request('/api/settings/permissions');
}

export async function savePermissions(cfg: PermissionsConfig): Promise<{ status: string }> {
  return request('/api/settings/permissions', {
    method: 'POST',
    body: JSON.stringify(cfg),
  });
}

export interface UserContextSettings {
  user_rules: string;
  include_agents_md: boolean;
  memory_enabled: boolean;
}

export interface UserMemory {
  id: string;
  category: 'profile' | 'preference' | 'habit' | 'feedback';
  content: string;
  created_at: number;
  updated_at: number;
  source?: 'agent' | 'user';
  source_thread_id?: string;
}

export async function fetchRules(): Promise<UserContextSettings> {
  return request('/api/settings/context');
}

export async function saveRules(content: string): Promise<{ status: string; content: string }> {
  return request('/api/settings/rules', {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

export async function saveContextSettings(
  settings: Partial<Pick<UserContextSettings, 'include_agents_md' | 'memory_enabled'>>,
): Promise<UserContextSettings> {
  return request('/api/settings/context', { method: 'POST', body: JSON.stringify(settings) });
}

export async function fetchUserMemories(): Promise<{ memories: UserMemory[] }> {
  return request('/api/settings/user-memories');
}

export async function saveUserMemory(
  data: Pick<UserMemory, 'category' | 'content'>,
  memoryId?: string,
): Promise<{ memory: UserMemory }> {
  return request(
    memoryId ? `/api/settings/user-memories/${encodeURIComponent(memoryId)}` : '/api/settings/user-memories',
    {
      method: memoryId ? 'PATCH' : 'POST',
      body: JSON.stringify(data),
    },
  );
}

export async function deleteUserMemory(memoryId: string): Promise<{ status: string }> {
  return request(`/api/settings/user-memories/${encodeURIComponent(memoryId)}`, { method: 'DELETE' });
}

// 3. MCP Servers
export async function fetchMcpServers(): Promise<{ servers: McpServerConfig[] }> {
  return request('/api/mcp/servers');
}

export async function createMcpServer(data: Partial<McpServerConfig>): Promise<{ server: McpServerConfig }> {
  return request('/api/mcp/servers', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateMcpServer(
  serverId: string,
  data: Partial<McpServerConfig>,
): Promise<{ server: McpServerConfig }> {
  return request(`/api/mcp/servers/${serverId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function toggleMcpServer(serverId: string): Promise<{ server: McpServerConfig }> {
  return request(`/api/mcp/servers/${serverId}/toggle`, {
    method: 'PATCH',
  });
}

export async function restartMcpServer(serverId: string): Promise<{ status: string }> {
  return request(`/api/mcp/servers/${serverId}/restart`, {
    method: 'POST',
  });
}

export async function deleteMcpServer(serverId: string): Promise<{ status: string }> {
  return request(`/api/mcp/servers/${serverId}`, {
    method: 'DELETE',
  });
}

export interface McpMarketItem {
  id: string;
  name: string;
  description: string;
  category: string;
  type: string;
  version?: string;
  repository?: string;
  packages?: Array<{ registryType?: string; identifier?: string; version?: string; transport?: { type?: string } }>;
  remotes?: Array<{
    type?: string;
    url?: string;
    headers?: Array<{ name: string; description?: string; isRequired?: boolean }>;
  }>;
}

export async function fetchMcpMarket(
  query = '',
  cursor = '',
): Promise<{ market: McpMarketItem[]; source?: string; next_cursor?: string | null }> {
  const params = new URLSearchParams();
  if (query.trim()) params.set('q', query.trim());
  if (cursor) params.set('cursor', cursor);
  const suffix = params.size ? `?${params.toString()}` : '';
  return request(`/api/mcp/market${suffix}`);
}

export async function installMcpFromMarket(
  item: McpMarketItem,
): Promise<{ status?: string; server: McpServerConfig; install_scripts?: string }> {
  const npmPackage = item.packages?.find((pkg) => pkg.registryType === 'npm' && pkg.identifier);
  if (npmPackage) {
    return request('/api/mcp/market/install', { method: 'POST', body: JSON.stringify({ registry_id: item.id }) });
  }
  const remote = item.remotes?.find((entry) => entry.url);
  if (remote?.url) {
    if (!remote.url.startsWith('https://')) throw new Error('Registry 远程 MCP 必须使用 HTTPS。');
    return createMcpServer({
      registry_id: item.id,
      name: item.name,
      type: 'remote',
      status: 'stopped',
      enabled: false,
      command: '',
      args: [],
      env: {},
      headers: {},
      tools: [],
      url: remote.url,
      transport: remote.type,
      repository: item.repository,
      registry_version: item.version,
    });
  }
  throw new Error('该 Registry 条目没有可安装的 NPM 包或 HTTPS 远程端点。');
}

// 4. Skills
export async function fetchSkills(): Promise<{ skills: SkillItem[] }> {
  return request('/api/skills');
}

export async function deleteSkill(name: string): Promise<{ status: string }> {
  return request(`/api/skills/${name}`, {
    method: 'DELETE',
  });
}

export interface SkillMarketItem {
  market_id: string;
  name: string;
  description: string;
  category: string;
  source_id: string;
  source_path: string;
  source: string;
  commit: string;
}

export async function fetchSkillsMarket(
  query = '',
): Promise<{ market: SkillMarketItem[]; sources?: Array<{ id: string; label: string; url: string }> }> {
  const suffix = query.trim() ? `?q=${encodeURIComponent(query.trim())}` : '';
  return request(`/api/skills/market${suffix}`);
}

export async function installSkill(skill: {
  name: string;
  description?: string;
  instructions?: string;
  source_id?: string;
  source_path?: string;
  commit?: string;
}): Promise<{ status: string }> {
  return request('/api/skills/install', {
    method: 'POST',
    body: JSON.stringify(skill),
  });
}
