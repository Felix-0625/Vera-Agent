/**
 * Types for the learning loop: turn traces and scores, scoped memories, and evolution proposals.
 * Backend: `server/routes/traces.py`, `server/routes/memories.py`, `server/routes/evolution.py`.
 */

export interface TraceScore {
  score_id: string;
  name: string;
  value: number;
  source: 'signal' | 'heuristic' | 'verifier' | 'user' | 'eval';
  comment: string;
  created_at: number;
}

export interface TraceSpan {
  span_id: string;
  parent_id: string | null;
  kind: 'model' | 'tool' | 'subagent' | 'approval';
  name: string;
  start_time: number;
  end_time: number | null;
  status: string;
  input: unknown;
  output: unknown;
  metadata: Record<string, unknown>;
}

export interface TraceSummary {
  trace_id: string;
  thread_id: string;
  project_id: string | null;
  task_type: string;
  input: string;
  output: string;
  start_time: number;
  duration: number;
  exit_status: string;
  steps: number;
  cost: number;
  model: string;
  outcome?: number | null;
}

export interface TraceDetail extends TraceSummary {
  spans: TraceSpan[];
  scores: TraceScore[];
}

export interface TaskTypeSuccess {
  task_type: string;
  traces: number;
  scored: number;
  mean_outcome: number | null;
  success_rate: number | null;
}

export type MemoryScope = 'user' | 'project' | 'session';
export type MemoryKind = 'profile' | 'preference' | 'habit' | 'feedback' | 'fact' | 'episode' | 'rule';

export interface MemoryItem {
  memory_id: string;
  scope: MemoryScope;
  scope_id: string;
  kind: MemoryKind;
  content: string;
  status: 'active' | 'superseded' | 'deleted';
  version: number;
  confidence: number;
  source: string;
  source_trace_id: string;
  updated_at: number;
  use_count: number;
}

export interface MemoryVersion {
  memory_id: string;
  version: number;
  content: string;
  kind: MemoryKind;
  status: string;
  reason: string;
  actor: string;
  trace_id: string;
  changed_at: number;
}

export interface PendingMemoryChange {
  change_id: string;
  operation: 'update' | 'delete';
  memory_id: string;
  content: string;
  current_content: string;
  reason: string;
  trace_id: string;
  apply_after: number | null;
  created_at: number;
}

export type ProposalStatus =
  | 'draft'
  | 'gated'
  | 'recommended'
  | 'not_recommended'
  | 'adopted'
  | 'rejected'
  | 'rolled_back';

export interface GateStage {
  split: 'train' | 'holdout' | 'guard';
  cases: number;
  wins: number;
  losses: number;
  ties: number;
  baseline_pass_rate: number;
  candidate_pass_rate: number;
  mean_delta: number;
  ci_low: number;
  ci_high: number;
  sign_test_p: number;
  verdict: 'better' | 'no_difference' | 'worse';
  regressions?: string[];
}

export interface EvolutionProposal {
  proposal_id: string;
  kind: 'rule' | 'skill' | 'prompt_overlay' | 'eval_case';
  title: string;
  content: string;
  rationale: string;
  skill_name: string;
  source_trace_ids: string[];
  status: ProposalStatus;
  created_at: number;
  gate: { status: string; reason: string; stages: GateStage[] } | null;
  monitor: { before_mean: number | null; after_mean: number | null; after_traces: number; action: string } | null;
  gate_running: boolean;
  diff: string;
}
