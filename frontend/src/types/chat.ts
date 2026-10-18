/**
 * Conversation, message, streaming event, and approval types. Field names mirror backend JSON (snake_case).
 */
export interface ChatImageAttachment {
  id: string;
  name: string;
  mime_type: string;
  data_url: string;
}

export type RuleTrigger = 'goal' | 'plan' | 'schedule' | 'learn' | 'grill-me' | null;

export interface ToolAction {
  tool_name: string;
  [key: string]: unknown;
}

export interface ChatActivityEvent {
  id: string;
  kind: 'status' | 'tool';
  label: string;
  detail?: string;
  status: 'working' | 'done' | 'approval' | 'error';
}

export interface SubagentActivity {
  label: string;
  detail: string;
  status: string;
  timestamp: number;
}

export interface SubagentRun {
  id: string;
  title: string;
  role: 'researcher' | 'reviewer' | string;
  task: string;
  status: 'running' | 'completed' | 'failed' | string;
  activities: SubagentActivity[];
  result: string;
  started_at: number;
  finished_at?: number;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  extra?: {
    actions?: ToolAction[];
    rule_trigger?: string;
    attached_skills?: string[];
    attached_mcps?: string[];
    images?: ChatImageAttachment[];
    activity?: ChatActivityEvent[];
    sender_id?: string;
    orchestration_run_id?: string;
    orchestration_group_id?: string;
    duration?: number;
    cost?: number;
    subagents?: SubagentRun[];
  };
  timestamp?: number;
}

export interface Thread {
  thread_id: string;
  project_id?: string | null;
  group_id?: string | null;
  role: string;
  title: string;
  is_pinned?: boolean;
  is_archived?: boolean;
  cost: number;
  n_calls: number;
  message_count?: number;
  messages?: ChatMessage[];
  updated_at?: number;
  created_at?: number;
}

export interface QueuedPrompt {
  id: string;
  content: string;
  images?: ChatImageAttachment[];
}

export interface ApprovalRequest {
  action_id: string;
  tool_name: string;
  args: Record<string, unknown>;
  message: string;
}

export interface StreamFinishPayload {
  duration: number;
  steps: number;
  cost: number;
  total_cost: number;
  exit_status: 'finish' | 'interrupted' | 'error';
}
