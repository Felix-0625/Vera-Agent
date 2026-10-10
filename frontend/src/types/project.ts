import { Thread } from './chat';

export interface Project {
  id: string;
  name: string;
  path: string;
  repo_root?: string;
  active_branch?: string;
  is_git?: boolean;
  last_opened?: number;
  folders?: string[];
  is_pinned?: boolean;
}

export interface Group {
  group_id: string;
  name: string;
  branch_name: string;
  base_branch?: string;
  worktree_path?: string;
  topology_type?: string;
  goal?: string;
  is_pinned?: boolean;
  is_archived?: boolean;
  threads?: Thread[];
}

export interface TopologyBlueprintNode {
  role_key: string;
  role: string;
  title: string;
  responsibilities: string[];
  allowed_tools: string[];
  prompt_template: string;
}

export interface TopologyBlueprintEdge {
  source_role: string;
  target_role: string;
  relation: string;
}

export interface TopologyTemplate {
  template_id: string;
  name: string;
  description: string;
  topology_type: string;
  nodes: TopologyBlueprintNode[];
  edges: TopologyBlueprintEdge[];
}
