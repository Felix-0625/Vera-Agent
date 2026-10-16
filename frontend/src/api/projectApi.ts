import { request } from './client';
import { Project, Group, TopologyTemplate } from '../types/project';

export async function fetchProjects(): Promise<{ projects: Project[] }> {
  return request('/api/projects');
}

export async function fetchCurrentProject(): Promise<Project> {
  return request('/api/projects/current');
}

export async function bindProjectFolder(path: string, options: { projectId?: string; name?: string; folders?: string[] } = {}): Promise<Project> {
  return request('/api/projects/bind', {
    method: 'POST',
    body: JSON.stringify({ path, project_id: options.projectId, name: options.name, folders: options.folders }),
  });
}

export async function selectProjectFolder(): Promise<{ path: string | null }> {
  return request('/api/projects/select-folder', { method: 'POST' });
}

export async function updateProject(projectId: string, data: { name?: string; folders?: string[]; is_pinned?: boolean }): Promise<{ project: Project }> {
  return request(`/api/projects/${projectId}`, { method: 'PATCH', body: JSON.stringify(data) });
}

export async function deleteProjectHistory(projectId: string): Promise<{ status: string }> {
  return request(`/api/projects/${projectId}`, {
    method: 'DELETE',
  });
}

export async function fetchGroups(projectId?: string): Promise<{ groups: Group[] }> {
  return request(`/api/groups${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`);
}

export async function createGroup(data: {
  branch_name: string;
  base_branch?: string;
  name?: string;
}): Promise<Group> {
  return request('/api/groups', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateGroup(groupId: string, data: Partial<Group>, projectId?: string): Promise<Group> {
  return request(`/api/groups/${groupId}${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteGroup(groupId: string, projectId?: string): Promise<{ status: string }> {
  return request(`/api/groups/${groupId}${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`, {
    method: 'DELETE',
  });
}

export async function createGroupThread(groupId: string, projectId: string, data: { title: string; role: string; responsibilities: string[]; allowed_tools?: string[]; position?: { x: number; y: number } }): Promise<import('../types/chat').Thread> {
  return request(`/api/groups/${groupId}/threads?project_id=${encodeURIComponent(projectId)}`, {
    method: 'POST', body: JSON.stringify(data),
  });
}

export async function fetchTopologyTemplates(projectId?: string): Promise<{ templates: TopologyTemplate[] }> {
  return request(`/api/templates/topology${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`);
}

export async function saveTopologyTemplate(data: {
  template_id?: string; name: string; description?: string; topology_type?: 'workflow' | 'architecture';
  nodes: import('../types/project').WorkflowNodeDefinition[];
  edges: import('../types/project').WorkflowEdgeDefinition[];
}): Promise<{ status: string; template: TopologyTemplate }> {
  return request('/api/templates/topology', { method: 'POST', body: JSON.stringify(data) });
}

export async function composeGroup(data: {
  project_id: string;
  group_mode: 'team' | 'workflow';
  name: string;
  goal: string;
  template_id?: string | null;
  template_name?: string | null;
  topology_type?: string;
  nodes: import('../types/project').WorkflowNodeDefinition[];
  edges: import('../types/project').WorkflowEdgeDefinition[];
  layout?: Record<string, unknown>;
}): Promise<{ status: string; group: Group; threads: import('../types/chat').Thread[]; registry: Record<string, unknown> }> {
  return request('/api/groups/compose', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function createGroupInstance(data: {
  project_id: string; template_id?: string; template_name?: string; group_mode: 'workflow' | 'architecture';
  name: string; description?: string; nodes: import('../types/project').WorkflowNodeDefinition[];
  edges: import('../types/project').WorkflowEdgeDefinition[]; layout?: Record<string, unknown>;
}): Promise<{ group: Group }> {
  return request('/api/groups/instances', { method: 'POST', body: JSON.stringify(data) });
}

export interface OrchestrationRun {
  run_id: string; status: string; input: string;
  sessions: Array<{ node_id: string; thread_id: string; title: string; prompt_template: string }>;
  nodes: Array<{ node_id: string; status: string; output?: string }>;
}

export async function createGroupRun(groupId: string, data: { project_id: string; confirmation: 'Y'; input: string; node_ids?: string[] }): Promise<{ run: OrchestrationRun }> {
  return request(`/api/groups/${encodeURIComponent(groupId)}/runs`, { method: 'POST', body: JSON.stringify(data) });
}

export async function updateGroupRun(groupId: string, projectId: string, run: Partial<OrchestrationRun> & { run_id: string }): Promise<{ run: OrchestrationRun }> {
  return request(`/api/groups/${encodeURIComponent(groupId)}/runs/${encodeURIComponent(run.run_id)}?project_id=${encodeURIComponent(projectId)}`, { method: 'PATCH', body: JSON.stringify(run) });
}

export async function provisionGroup(data: {
  template_id: string;
  branch_name: string;
  base_branch?: string;
  group_name?: string;
  goal?: string;
}): Promise<{ status: string; group: Group }> {
  return request('/api/groups/provision', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
