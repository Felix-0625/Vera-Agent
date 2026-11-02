export type RunInputRecord = { node_id: string; title: string; relation?: string; label?: string; output: string };

export type RunNodeState = {
  node_id: string;
  status: string;
  output: string;
  error?: string;
  inputs?: RunInputRecord[];
};

export type RunLogEntry = { title: string; status: string; output: string; error?: string; inputs?: RunInputRecord[] };

export type WorkflowControlResult = { decision: 'YES' | 'NO'; reason: string; feedback?: string };

export type RunStage = 'supervisor_review' | 'control_decision';

export type RunSession = { node_id: string; thread_id: string };

export interface NodeTurnRequest {
  threadId: string;
  content: string;
  workflowInput: string;
  workflowContext: { task: string; upstream: RunInputRecord[] };
  workflowControl?: { type: 'condition' | 'loop'; condition: string; max_iterations?: number };
  workflowStage?: RunStage;
}

export interface RunnerDeps {
  /** Run one node turn; call `onText` with streamed text; resolve when the turn finished successfully. */
  streamNode: (request: NodeTurnRequest, onText: (output: string) => void) => Promise<void>;
  /** Persist intermediate run state (`PATCH .../runs/{run_id}` with status "running"). */
  saveNodes: (nodes: RunNodeState[]) => Promise<void>;
  /** Update the visible run log. */
  updateLog: (update: (entries: RunLogEntry[]) => RunLogEntry[]) => void;
}

export interface RunOutcome {
  finalAnswer: string;
  finalReviewerTitle: string;
  nodes: RunNodeState[];
}
