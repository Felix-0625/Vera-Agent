/**
 * Tool panel types: tab IDs, file tree/preview, diff, Git, task board, scheduled tasks, analytics.
 */
export type ToolTabId =
  | 'launcher'
  | 'diff'
  | 'files'
  | 'fileDocument'
  | 'terminal'
  | 'sidechat'
  | 'subagents'
  | 'metrics'
  | 'traces'
  | 'memory'
  | 'evolution'
  | 'gitflow'
  | 'workflow';

export interface ToolTab {
  id: string;
  toolType: ToolTabId;
  title: string;
  closable?: boolean;
  filePath?: string;
  sideChatId?: string;
  /** Project scope captured when a project-level tool is opened from a project row. */
  projectId?: string;
}

export type FilePreviewData =
  | { kind: 'text'; content: string }
  | { kind: 'image' | 'pdf'; url: string }
  | { kind: 'ppt'; slides: Array<{ text: string }> }
  | { kind: 'excel'; sheets: Array<{ name: string; rows: string[][] }>; sheet_names: string[] }
  | { kind: 'unsupported'; message: string; url?: string };

export interface DiffFile {
  file: string;
  status: string;
  additions?: number;
  deletions?: number;
}

export interface WorktreeDiffData {
  cwd: string;
  staged: DiffFile[];
  unstaged: DiffFile[];
  untracked: string[];
  diff_text: string;
  diff_staged: string;
  base_ref?: string | null;
}

export interface WorktreeCommitRef {
  hash: string;
  short_hash: string;
  subject: string;
  timestamp: number;
}

export interface FileTreeNode {
  name: string;
  path: string;
  is_dir: boolean;
  size?: number;
  children?: FileTreeNode[];
}

export interface ScheduledTask {
  id: string;
  name: string;
  /** One-time execution timestamp in ISO 8601 UTC form. */
  run_at?: string;
  prompt: string;
  thread_id?: string;
  model_id?: string;
  project_id?: string;
  enabled: boolean;
  created_at: number;
  last_run?: number | null;
  last_status?: string;
  last_error?: string | null;
}

export type WorkItemStatus = 'backlog' | 'todo' | 'in_progress' | 'blocked' | 'in_review' | 'done' | 'canceled';
export type WorkItemPriority = 'urgent' | 'high' | 'medium' | 'low' | 'none';

export interface WorkItem {
  id: string;
  project_id: string;
  identifier: string;
  title: string;
  description: string;
  status: WorkItemStatus;
  priority: WorkItemPriority;
  labels: string[];
  sort_order: number;
  thread_id: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface AnalyticsDashboard {
  summary: {
    total_cost_usd: number;
    total_tokens: number;
    today_cost_usd: number;
  };
  retained_months: string[];
  daily_trends: Array<{ month: string; date: string; tokens: number; cost_usd: number }>;
  weekly_trends: Array<{ month: string; week: number; label: string; tokens: number; cost_usd: number }>;
  monthly_models: Array<{ month: string; models: Array<{ name: string; tokens: number; cost_usd: number }> }>;
  mcp_usage: Array<{ name: string; count: number }>;
  skill_usage: Array<{ name: string; count: number }>;
}

export interface BranchInfo {
  name: string;
  is_current: boolean;
  is_remote: boolean;
  head?: string;
  parent?: string;
  upstream?: string;
  ahead?: number;
  behind?: number;
}

export interface GitCommitInfo {
  hash: string;
  short_hash: string;
  parents: string[];
  timestamp: number;
  subject: string;
}

export interface GitFlowTopology {
  repo_name: string;
  is_git?: boolean;
  current_branch: string;
  branches: BranchInfo[];
  commits: GitCommitInfo[];
}
