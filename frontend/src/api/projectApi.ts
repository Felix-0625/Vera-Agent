/**
 * Projects, groups, topology templates, workflow instances, and runs.
 *
 * Backend: `server/routes/projects.py` (`/api/projects*`) and `server/routes/groups.py`
 * (`/api/groups*`, `/api/templates/topology`).
 */
import { Group, Project, TopologyTemplate } from '../types/project';
import { request } from './client';

export async function fetchProjects(): Promise<{ projects: Project[] }> {
  return request('/api/projects');
}

export async function fetchCurrentProject(): Promise<Project> {
  return request('/api/projects/current');
}

export async function bindProjectFolder(
  path: string,
  options: { projectId?: string; name?: string; folders?: string[] } = {},
): Promise<Project> {
  return request('/api/projects/bind', {
    method: 'POST',
    body: JSON.stringify({ path, project_id: options.projectId, name: options.name, folders: options.folders }),
  });
}

export async function selectProjectFolder(): Promise<{ path: string | null }> {
  return request('/api/projects/select-folder', { method: 'POST' });
}

export async function updateProject(
  projectId: string,
  data: { name?: string; folders?: string[]; is_pinned?: boolean },
): Promise<{ project: Project }> {
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

export async function fetchTopologyTemplates(projectId?: string): Promise<{ templates: TopologyTemplate[] }> {
  return request(`/api/templates/topology${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''}`);
}

export async function saveTopologyTemplate(data: {
  template_id?: string;
  name: string;
  description?: string;
  topology_type?: 'workflow' | 'architecture';
  nodes: import('../types/project').WorkflowNodeDefinition[];
  edges: import('../types/project').WorkflowEdgeDefinition[];
}): Promise<{ status: string; template: TopologyTemplate }> {
  return request('/api/templates/topology', { method: 'POST', body: JSON.stringify(data) });
}

export async function createGroupInstance(data: {
  project_id: string;
  template_id?: string;
  template_name?: string;
  group_mode: 'workflow' | 'architecture';
  name: string;
  goal?: string;
  background?: string;
  description?: string;
  nodes: import('../types/project').WorkflowNodeDefinition[];
  edges: import('../types/project').WorkflowEdgeDefinition[];
  layout?: Record<string, unknown>;
}): Promise<{ group: Group }> {
  return request('/api/groups/instances', { method: 'POST', body: JSON.stringify(data) });
}

export interface OrchestrationRun {
  run_id: string;
  status: string;
  input: string;
  final_output?: string;
  error?: string;
  sessions: Array<{ node_id: string; thread_id: string; title: string; prompt_template: string }>;
  nodes: Array<{
    node_id: string;
    status: string;
    output?: string;
    error?: string;
    inputs?: Array<{ node_id: string; title: string; relation?: string; label?: string; output: string }>;
  }>;
  events?: Array<{ type: string; at: number; node_id?: string; status?: string; from?: string; to?: string }>;
}

export async function createGroupRun(
  groupId: string,
  data: { project_id: string; confirmation: 'Y'; input: string; node_ids?: string[] },
): Promise<{ run: OrchestrationRun }> {
  return request(`/api/groups/${encodeURIComponent(groupId)}/runs`, { method: 'POST', body: JSON.stringify(data) });
}

export async function updateGroupRun(
  groupId: string,
  projectId: string,
  run: Partial<OrchestrationRun> & { run_id: string },
): Promise<{ run: OrchestrationRun }> {
  return request(
    `/api/groups/${encodeURIComponent(groupId)}/runs/${encodeURIComponent(run.run_id)}?project_id=${encodeURIComponent(projectId)}`,
    { method: 'PATCH', body: JSON.stringify(run) },
  );
}
