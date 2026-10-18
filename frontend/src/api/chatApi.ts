/**
 * Conversation and chat-stream client.
 *
 * Backend: `server/routes/threads.py` (`/api/threads*`, `/api/context-status`) and
 * `server/routes/chat.py` (`/api/chat/*`). `streamChat` parses the SSE events documented in docs/API.md.
 */
import { request } from './client';
import { Thread, ChatMessage, ChatImageAttachment, StreamFinishPayload, SubagentRun } from '../types/chat';

export interface StreamChatParams {
  thread_id?: string;
  content: string;
  model_id?: string;
  rule_trigger?: string | null;
  attached_skills?: string[];
  attached_mcps?: string[];
  images?: ChatImageAttachment[];
  group_id?: string;
  project_id?: string;
  client_message_id?: string;
  ephemeral?: boolean;
  context_messages?: Array<Pick<ChatMessage, 'role' | 'content'>>;
  context_update?: boolean;
  workflow_input?: string;
  workflow_upstream?: string;
  workflow_context?: { task: string; upstream: Array<{ node_id: string; title: string; relation?: string; label?: string; output: string }> };
  workflow_control?: { type: 'condition' | 'loop'; condition: string; max_iterations?: number };
  workflow_stage?: 'supervisor_review' | 'control_decision';
  onThinking?: (step: number, content: string) => void;
  onTextChunk?: (chunk: string) => void;
  onToolCall?: (actionId: string, toolName: string, args: Record<string, unknown>) => void;
  onApprovalRequired?: (actionId: string, toolName: string, message: string, args: Record<string, unknown>) => void;
  onToolResult?: (actionId: string, toolName: string, output: string, returncode: number) => void;
  onSubagent?: (run: SubagentRun) => void;
  onContextManagement?: (event: { kind: string; timestamp: number; before_tokens: number; after_tokens: number; reason?: string }) => void;
  onFinish?: (payload: StreamFinishPayload) => void;
  onError?: (err: Error) => void;
}

export async function fetchThreads(search?: string, isArchived?: boolean): Promise<{ threads: Thread[] }> {
  const query = new URLSearchParams();
  if (search) query.set('search', search);
  if (isArchived !== undefined) query.set('is_archived', String(isArchived));
  return request(`/api/threads?${query.toString()}`);
}

export async function createThread(title: string, group_id?: string, project_id?: string): Promise<Thread> {
  return request('/api/threads', {
    method: 'POST',
    body: JSON.stringify({ title, group_id, project_id }),
  });
}

export async function fetchThreadMessages(threadId: string): Promise<{ messages: ChatMessage[]; cost: number; title: string }> {
  return request(`/api/threads/${threadId}/messages`);
}

export async function deliverOrchestrationResult(threadId: string, data: { project_id: string; group_id: string; run_id: string; input: string; content: string }): Promise<{ status: string; messages: ChatMessage[] }> {
  return request(`/api/threads/${encodeURIComponent(threadId)}/messages/deliver`, { method: 'POST', body: JSON.stringify(data) });
}

export async function updateThread(threadId: string, updates: Partial<Thread>): Promise<Thread> {
  return request(`/api/threads/${threadId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}

export async function truncateThreadFromMessage(threadId: string, messageId: string): Promise<void> {
  await request(`/api/threads/${threadId}/messages/truncate`, { method: 'POST', body: JSON.stringify({ message_id: messageId }) });
}

export async function deleteThread(threadId: string): Promise<{ status: string }> {
  return request(`/api/threads/${threadId}`, {
    method: 'DELETE',
  });
}

export async function probeThreadContext(threadId: string): Promise<{
  thread_id: string;
  title: string;
  last_user_message: string;
  last_assistant_message: string;
  summary: string;
}> {
  return request(`/api/threads/${threadId}/context-probe`);
}

export interface ThreadContextStatus {
  thread_id: string;
  model: string;
  context_limit: number | null;
  context_limit_source: string;
  used_tokens: number | null;
  used_percent: number | null;
  rebirth_logs: Array<{ timestamp: number; kind: string; detail: string }>;
  can_manual_rebirth?: boolean;
}

export async function fetchThreadContextStatus(threadId: string, modelId?: string): Promise<ThreadContextStatus> {
  const query = modelId ? `?model_id=${encodeURIComponent(modelId)}` : '';
  return request(`/api/threads/${encodeURIComponent(threadId)}/context-status${query}`);
}

export async function fetchDraftContextStatus(modelId?: string): Promise<ThreadContextStatus> {
  const query = modelId ? `?model_id=${encodeURIComponent(modelId)}` : '';
  return request(`/api/context-status${query}`);
}

export async function rebirthGroupThreadContext(threadId: string, modelId?: string): Promise<{ status: string; event: { kind: string; timestamp: number; detail: string } }> {
  return request(`/api/threads/${encodeURIComponent(threadId)}/context-rebirth`, {
    method: 'POST',
    body: JSON.stringify({ model_id: modelId }),
  });
}

export async function confirmApproval(thread_id: string, action_id: string, choice: string): Promise<{ status: string }> {
  return request('/api/chat/confirm', {
    method: 'POST',
    body: JSON.stringify({ thread_id, action_id, choice }),
  });
}

export async function interruptChat(thread_id: string, client_message_id?: string): Promise<{ status: string; interrupted: boolean }> {
  return request('/api/chat/interrupt', {
    method: 'POST',
    body: JSON.stringify({ thread_id, client_message_id }),
  });
}

export async function pauseChat(thread_id: string): Promise<{ status: string; paused: boolean }> {
  return request('/api/chat/pause', { method: 'POST', body: JSON.stringify({ thread_id }) });
}

export async function resumeChat(thread_id: string): Promise<{ status: string; resumed: boolean }> {
  return request('/api/chat/resume', { method: 'POST', body: JSON.stringify({ thread_id }) });
}

export function streamChat(params: StreamChatParams): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const resp = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: params.thread_id,
          content: params.content,
          model_id: params.model_id,
          rule_trigger: params.rule_trigger,
          attached_skills: params.attached_skills,
          attached_mcps: params.attached_mcps,
          images: params.images,
          group_id: params.group_id,
          project_id: params.project_id,
          client_message_id: params.client_message_id,
          ephemeral: params.ephemeral,
          context_messages: params.context_messages,
          context_update: params.context_update,
          workflow_input: params.workflow_input,
          workflow_upstream: params.workflow_upstream,
          workflow_context: params.workflow_context,
          workflow_control: params.workflow_control,
          workflow_stage: params.workflow_stage,
        }),
        signal: controller.signal,
      });

      if (!resp.ok) {
        const responseText = await resp.text();
        let message = responseText;
        try {
          const payload = JSON.parse(responseText);
          message = payload.error || payload.detail || responseText;
        } catch {
          // Keep the response body as the most useful available error detail.
        }
        throw new Error(message || `SSE HTTP Error ${resp.status}`);
      }

      const reader = resp.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      let buffer = '';
      let receivedFinish = false;
      let currentEvent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('event: ')) {
            currentEvent = trimmed.slice(7).trim();
          } else if (trimmed.startsWith('data: ')) {
            const rawData = trimmed.slice(6).trim();
            try {
              const data = JSON.parse(rawData);
              if (currentEvent === 'thinking') {
                params.onThinking?.(data.step, data.content);
              } else if (currentEvent === 'text_chunk') {
                params.onTextChunk?.(data.content);
              } else if (currentEvent === 'tool_call') {
                params.onToolCall?.(data.action_id, data.tool_name, data.args);
              } else if (currentEvent === 'approval_required') {
                params.onApprovalRequired?.(data.action_id, data.tool_name, data.message, data.args);
              } else if (currentEvent === 'tool_result') {
                params.onToolResult?.(data.action_id, data.tool_name, data.output, data.returncode);
              } else if (currentEvent === 'subagent') {
                params.onSubagent?.(data as SubagentRun);
              } else if (currentEvent === 'context_management') {
                params.onContextManagement?.(data);
              } else if (currentEvent === 'finish') {
                receivedFinish = true;
                params.onFinish?.(data);
              }
            } catch {
              // Ignore malformed event data and keep reading the stream.
            }
            currentEvent = '';
          }
        }
      }
      if (!receivedFinish && !controller.signal.aborted) {
        params.onError?.(new Error('模型连接已结束，但没有收到完成事件。'));
      }
    } catch (err: unknown) {
      if ((err as Error).name !== 'AbortError') {
        params.onError?.(err as Error);
      }
    }
  })();

  return () => controller.abort();
}

export async function closeEphemeralChat(thread_id: string): Promise<void> {
  await request('/api/chat/ephemeral/close', {
    method: 'POST',
    body: JSON.stringify({ thread_id }),
  });
}
