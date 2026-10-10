import { request } from './client';
import {
  ModelConfig,
  PermissionsConfig,
  McpServerConfig,
  SkillItem,
} from '../types/settings';

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
  const current = await fetchModels();
  return request('/api/settings/models', {
    method: 'POST',
    body: JSON.stringify({ models: [...(current.models || []), data] }),
  });
}

export async function deleteModel(modelId: string): Promise<{ status: string }> {
  return request(`/api/settings/models/${modelId}`, {
    method: 'DELETE',
  });
}

export async function testModelConnection(model: {
  name: string;
  api_key?: string;
  base_url?: string;
}): Promise<{ success: boolean; message?: string; error?: string }> {
  return request('/api/settings/models/test', {
    method: 'POST',
    body: JSON.stringify(model),
  });
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

export async function fetchRules(): Promise<{ content: string; exists: boolean }> {
  return request('/api/settings/rules');
}

export async function saveRules(content: string): Promise<{ status: string }> {
  return request('/api/settings/rules', {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

// 3. MCP Servers
export async function fetchMcpServers(): Promise<{ servers: McpServerConfig[] }> {
  return request('/api/mcp/servers');
}

export async function scanMcpServers(): Promise<{ servers: McpServerConfig[] }> {
  return request('/api/mcp/scan', { method: 'POST' });
}

export async function createMcpServer(data: Partial<McpServerConfig>): Promise<{ server: McpServerConfig }> {
  return request('/api/mcp/servers', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateMcpServer(serverId: string, data: Partial<McpServerConfig>): Promise<{ server: McpServerConfig }> {
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

export async function fetchMcpMarket(): Promise<{ market: Array<{ id: string; name: string; description: string; category: string; type: string }> }> {
  return request('/api/mcp/market');
}

// 4. Skills
export async function fetchSkills(): Promise<{ skills: SkillItem[] }> {
  return request('/api/skills');
}

export async function scanSkills(): Promise<{ skills: SkillItem[] }> {
  return request('/api/skills/scan', { method: 'POST' });
}

export async function toggleSkill(name: string): Promise<{ status: string; state: string }> {
  return request(`/api/skills/${name}/toggle`, {
    method: 'PATCH',
  });
}

export async function deleteSkill(name: string): Promise<{ status: string }> {
  return request(`/api/skills/${name}`, {
    method: 'DELETE',
  });
}

export async function fetchSkillsMarket(): Promise<{ market: Array<{ name: string; description: string; category: string }> }> {
  return request('/api/skills/market');
}

export async function installSkill(skill: { name: string; description: string; instructions?: string }): Promise<{ status: string }> {
  return request('/api/skills/install', {
    method: 'POST',
    body: JSON.stringify(skill),
  });
}
