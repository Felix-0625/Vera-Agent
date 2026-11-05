/**
 * Learning-loop client: traces, scoped memories, and evolution proposals.
 *
 * Backend: `server/routes/traces.py` (`/api/traces*`), `server/routes/memories.py`
 * (`/api/memories*`), and `server/routes/evolution.py` (`/api/evolution/*`).
 */
import {
  EvolutionProposal,
  MemoryItem,
  MemoryVersion,
  PendingMemoryChange,
  TaskTypeSuccess,
  TraceDetail,
  TraceSummary,
} from '../types/learning';
import { request } from './client';

const query = (params: Record<string, string | number | undefined | null>) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value));
  });
  const text = search.toString();
  return text ? `?${text}` : '';
};

// 1. Traces
export async function fetchTraces(
  params: { projectId?: string | null; threadId?: string; days?: number; belowScore?: number } = {},
): Promise<{ traces: TraceSummary[] }> {
  return request(
    `/api/traces${query({ project_id: params.projectId, thread_id: params.threadId, days: params.days, below_score: params.belowScore })}`,
  );
}

export async function fetchTraceSummary(days = 30): Promise<{ task_types: TaskTypeSuccess[] }> {
  return request(`/api/traces/summary${query({ days })}`);
}

export async function fetchTrace(traceId: string): Promise<{ trace: TraceDetail }> {
  return request(`/api/traces/${encodeURIComponent(traceId)}`);
}

export async function sendTraceFeedback(traceId: string, value: number, comment = ''): Promise<unknown> {
  return request(`/api/traces/${encodeURIComponent(traceId)}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ value, comment }),
  });
}

// 2. Memories
export async function fetchMemories(
  params: { scope?: string; kind?: string; status?: string } = {},
): Promise<{ memories: MemoryItem[] }> {
  return request(`/api/memories${query(params)}`);
}

export async function deleteMemory(memoryId: string): Promise<unknown> {
  return request(`/api/memories/${encodeURIComponent(memoryId)}`, { method: 'DELETE' });
}

export async function fetchMemoryHistory(memoryId: string): Promise<{ history: MemoryVersion[] }> {
  return request(`/api/memories/${encodeURIComponent(memoryId)}/history`);
}

export async function restoreMemoryVersion(memoryId: string, version: number): Promise<{ memory: MemoryItem }> {
  return request(`/api/memories/${encodeURIComponent(memoryId)}/restore`, {
    method: 'POST',
    body: JSON.stringify({ version }),
  });
}

export async function fetchPendingChanges(): Promise<{ changes: PendingMemoryChange[] }> {
  return request('/api/memories/pending');
}

export async function resolvePendingChange(changeId: string, accept: boolean): Promise<unknown> {
  return request(`/api/memories/pending/${encodeURIComponent(changeId)}`, {
    method: 'POST',
    body: JSON.stringify({ accept }),
  });
}

// 3. Evolution
export async function fetchProposals(): Promise<{ proposals: EvolutionProposal[] }> {
  return request('/api/evolution/proposals');
}

export async function analyzeTraces(): Promise<{ traces: number; drafts: string[]; proposals: EvolutionProposal[] }> {
  return request('/api/evolution/analyze', { method: 'POST' });
}

export async function startGate(proposalId: string): Promise<unknown> {
  return request(`/api/evolution/proposals/${encodeURIComponent(proposalId)}/gate`, { method: 'POST' });
}

export async function adoptProposal(proposalId: string, override = false): Promise<{ proposal: EvolutionProposal }> {
  return request(`/api/evolution/proposals/${encodeURIComponent(proposalId)}/adopt`, {
    method: 'POST',
    body: JSON.stringify({ confirm: true, override }),
  });
}

export async function rejectProposal(proposalId: string): Promise<{ proposal: EvolutionProposal }> {
  return request(`/api/evolution/proposals/${encodeURIComponent(proposalId)}/reject`, { method: 'POST' });
}

export async function rollbackProposal(proposalId: string, reason = ''): Promise<{ proposal: EvolutionProposal }> {
  return request(`/api/evolution/proposals/${encodeURIComponent(proposalId)}/rollback`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}
