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

export async function fetchGroups(): Promise<{ groups: Group[] }> {
  return request('/api/groups');
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

export async function updateGroup(groupId: string, data: Partial<Group>): Promise<Group> {
  return request(`/api/groups/${groupId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteGroup(groupId: string): Promise<{ status: string }> {
  return request(`/api/groups/${groupId}`, {
    method: 'DELETE',
  });
}

export async function fetchTopologyTemplates(): Promise<{ templates: TopologyTemplate[] }> {
  return request('/api/templates/topology');
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
