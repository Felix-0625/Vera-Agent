/**
 * Right-side tool panel client: diff/worktree, files, task board, scheduled tasks, Git, analytics.
 * (The terminal panel talks to the WebSocket in `stores/terminalStore.ts`.)
 *
 * Backend: `server/routes/{worktrees,files,taskboard,tasks,gitflow,analytics}.py`.
 */
import {
  AnalyticsDashboard,
  FilePreviewData,
  FileTreeNode,
  GitFlowTopology,
  ScheduledTask,
  WorkItem,
  WorktreeCommitRef,
  WorktreeDiffData,
} from '../types/tool';
import { request } from './client';

// 1. Worktree
export async function fetchWorktreeRefs(
  projectId?: string,
  branch?: string,
): Promise<{ branches: string[]; current_branch: string; commits: WorktreeCommitRef[] }> {
  const query = new URLSearchParams();
  if (projectId) query.set('project_id', projectId);
  if (branch) query.set('branch', branch);
  return request(`/api/worktrees/refs${query.size ? `?${query.toString()}` : ''}`);
}

export async function fetchWorktreeDiff(
  groupId?: string,
  projectId?: string,
  baseRef?: string,
): Promise<WorktreeDiffData> {
  const query = new URLSearchParams();
  if (groupId) query.set('group_id', groupId);
  if (projectId) query.set('project_id', projectId);
  if (baseRef) query.set('base_ref', baseRef);
  return request(`/api/worktrees/diff${query.size ? `?${query.toString()}` : ''}`);
}

export async function stageWorktreeFile(
  files: string[],
  groupId?: string,
  projectId?: string,
): Promise<{ status: string }> {
  return request('/api/worktrees/stage', {
    method: 'POST',
    body: JSON.stringify({ files, group_id: groupId, project_id: projectId }),
  });
}

export async function discardWorktreeFile(
  files: string[],
  groupId?: string,
  projectId?: string,
): Promise<{ status: string }> {
  return request('/api/worktrees/discard', {
    method: 'POST',
    body: JSON.stringify({ files, group_id: groupId, project_id: projectId }),
  });
}

// 2. Files
export async function fetchFileTree(groupId?: string, projectId?: string): Promise<FileTreeNode> {
  const query = new URLSearchParams();
  if (groupId) query.set('group_id', groupId);
  if (projectId) query.set('project_id', projectId);
  return request(`/api/files/tree${query.size ? `?${query.toString()}` : ''}`);
}

export async function fetchFilePreview(path: string, groupId?: string, projectId?: string): Promise<FilePreviewData> {
  const query = new URLSearchParams({ path });
  if (groupId) query.set('group_id', groupId);
  if (projectId) query.set('project_id', projectId);
  return request(`/api/files/preview?${query.toString()}`);
}

export async function saveTextFile(path: string, content: string, groupId?: string, projectId?: string): Promise<void> {
  await request('/api/files/content', {
    method: 'PUT',
    body: JSON.stringify({ path, content, group_id: groupId, project_id: projectId }),
  });
}

export async function saveExcelFile(
  path: string,
  sheets: Array<{ name: string; rows: string[][] }>,
  groupId?: string,
  projectId?: string,
): Promise<void> {
  await request('/api/files/excel', {
    method: 'PUT',
    body: JSON.stringify({ path, sheets, group_id: groupId, project_id: projectId }),
  });
}

// 3. Scheduled Tasks
export async function fetchScheduledTasks(): Promise<{ tasks: ScheduledTask[] }> {
  return request('/api/tasks/scheduled');
}

// Project work items are separate from timed Agent prompts in `/api/tasks/scheduled`.
export async function fetchWorkItems(projectId: string): Promise<{ items: WorkItem[] }> {
  const query = new URLSearchParams({ project_id: projectId });
  return request(`/api/taskboard/tasks?${query.toString()}`);
}

export async function createWorkItem(data: {
  project_id: string;
  title: string;
  description?: string;
  status?: WorkItem['status'];
  priority?: WorkItem['priority'];
  labels?: string[];
}): Promise<{ item: WorkItem }> {
  return request('/api/taskboard/tasks', { method: 'POST', body: JSON.stringify(data) });
}

export async function updateWorkItem(
  id: string,
  data: Partial<WorkItem> & { version: number },
): Promise<{ item: WorkItem }> {
  return request(`/api/taskboard/tasks/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(data) });
}

export async function archiveWorkItem(id: string): Promise<{ status: string; id: string }> {
  return request(`/api/taskboard/tasks/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export async function createScheduledTask(task: {
  name: string;
  run_at: string;
  prompt: string;
  model_id?: string;
  project_id?: string;
  thread_id?: string;
}): Promise<ScheduledTask> {
  return request('/api/tasks/scheduled', {
    method: 'POST',
    body: JSON.stringify(task),
  });
}

export async function toggleScheduledTask(taskId: string): Promise<ScheduledTask> {
  return request(`/api/tasks/scheduled/${taskId}/toggle`, {
    method: 'PATCH',
  });
}

export async function runScheduledTask(taskId: string): Promise<{ status: string; task_id?: string }> {
  return request(`/api/tasks/scheduled/${taskId}/run`, {
    method: 'POST',
  });
}

export async function deleteScheduledTask(taskId: string): Promise<{ status: string }> {
  return request(`/api/tasks/scheduled/${taskId}`, {
    method: 'DELETE',
  });
}

// 4. GitFlow & Analytics
export async function fetchGitFlowTopology(projectId: string): Promise<GitFlowTopology> {
  let data: Partial<GitFlowTopology>;
  try {
    data = await request<Partial<GitFlowTopology>>(`/api/gitflow/topology?project_id=${encodeURIComponent(projectId)}`);
  } catch (error) {
    // Older backend builds report non-Git folders as HTTP 400 instead of a typed empty state.
    if (
      error instanceof Error &&
      (error.message.includes('不是可用的 Git 仓库') || error.message.toLowerCase().includes('not a git repository'))
    ) {
      return { repo_name: '', is_git: false, current_branch: '', branches: [], commits: [] };
    }
    throw error;
  }
  if (!Array.isArray(data.commits) || !Array.isArray(data.branches)) {
    throw new Error('GitFlow 后端接口版本较旧，请重启后端服务后重试。');
  }
  return data as GitFlowTopology;
}

export async function createBranch(
  branch_name: string,
  start_point = 'HEAD',
  project_id?: string,
): Promise<{ status: string }> {
  return request('/api/branches', {
    method: 'POST',
    body: JSON.stringify({ branch_name, start_point, project_id }),
  });
}

export async function checkoutBranch(branch_name: string, project_id?: string): Promise<{ status: string }> {
  return request('/api/branches/checkout', {
    method: 'POST',
    body: JSON.stringify({ branch_name, project_id }),
  });
}

export async function deleteBranch(branch_name: string, project_id?: string): Promise<{ status: string }> {
  const query = project_id ? `?project_id=${encodeURIComponent(project_id)}` : '';
  return request(`/api/branches/${encodeURIComponent(branch_name)}${query}`, { method: 'DELETE' });
}

export async function mergeBranch(
  source_branch: string,
  project_id?: string,
): Promise<{ status: string; returncode: number }> {
  return request('/api/branches/merge', {
    method: 'POST',
    body: JSON.stringify({ source_branch, project_id }),
  });
}

export async function requestMergeReview(
  source_branch: string,
  target_branch = 'main',
  project_id?: string,
): Promise<{
  has_conflict: boolean;
  conflict_files: string[];
  summary: string;
}> {
  return request('/api/merge-review', {
    method: 'POST',
    body: JSON.stringify({ source_branch, target_branch, project_id }),
  });
}

export async function fetchAnalyticsDashboard(projectId?: string): Promise<AnalyticsDashboard> {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
  return request(`/api/analytics/dashboard${query}`);
}
