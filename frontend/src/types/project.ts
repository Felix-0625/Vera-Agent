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
  branch_name?: string;
  project_id?: string;
  project_path?: string;
  base_branch?: string;
  worktree_path?: string;
  group_mode?: 'team' | 'workflow' | 'architecture';
  template_id?: string | null;
  template_name?: string | null;
  topology_type?: string;
  goal?: string;
  background?: string;
  nodes?: WorkflowNodeDefinition[];
  edges?: WorkflowEdgeDefinition[];
  layout?: Record<string, unknown>;
  is_pinned?: boolean;
  is_archived?: boolean;
  threads?: Thread[];
}

export type WorkflowNodeType = 'agent' | 'start' | 'input' | 'condition' | 'code' | 'tool' | 'http' | 'knowledge' | 'document' | 'variable' | 'aggregator' | 'template' | 'parallel' | 'loop' | 'iteration' | 'approval' | 'error' | 'output' | 'end';

export interface WorkflowNodeDefinition {
  id: string;
  type: WorkflowNodeType;
  title: string;
  role?: string;
  role_key?: string;
  background?: string;
  responsibilities?: string[];
  constraints?: string[];
  output_spec?: string;
  allowed_tools?: string[];
  prompt_template?: string;
  config?: Record<string, unknown>;
  position?: { x: number; y: number };
  thread_id?: string;
}

export interface WorkflowEdgeDefinition {
  id?: string;
  source: string;
  target: string;
  relation?: string;
  label?: string;
  config?: Record<string, unknown>;
}

export interface TopologyBlueprintNode {
  role_key: string;
  role: string;
  title: string;
  responsibilities: string[];
  allowed_tools: string[];
  prompt_template: string;
  position?: { x: number; y: number };
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
  nodes: WorkflowNodeDefinition[];
  edges: WorkflowEdgeDefinition[];
  is_custom?: boolean;
}
