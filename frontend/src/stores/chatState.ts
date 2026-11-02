import { interruptChat } from '../api/chatApi';
import {
  ApprovalRequest,
  ChatActivityEvent,
  ChatImageAttachment,
  ChatMessage,
  QueuedPrompt,
  RuleTrigger,
  Thread,
} from '../types/chat';
export interface ChatState {
  threads: Thread[];
  activeThreadId: string | null;
  draftConversationId: string;
  draftProjectId: string | null;
  draftImages: ChatImageAttachment[];
  messages: ChatMessage[];
  queuedPrompts: QueuedPrompt[];
  queuePaused: boolean;
  conversationQueues: Record<string, { queuedPrompts: QueuedPrompt[]; queuePaused: boolean }>;
  isStreaming: boolean;
  currentThinking: { step: number; text: string } | null;
  currentActivity: ChatActivityEvent[];
  approvalRequest: ApprovalRequest | null;
  selectedModel: string;
  ruleTrigger: RuleTrigger;
  attachedSkills: string[];
  attachedMcps: string[];

  loadThreads: (search?: string) => Promise<void>;
  selectThread: (threadId: string) => Promise<void>;
  openDraftConversation: (projectId?: string | null) => Promise<void>;
  newThread: (title?: string, groupId?: string, projectId?: string) => Promise<string>;
  sendMessage: (content: string, groupId?: string, images?: ChatImageAttachment[]) => Promise<void>;
  appendOrchestrationResult: (
    threadId: string,
    data: { project_id: string; group_id: string; run_id: string; input: string; content: string },
  ) => Promise<void>;
  editAndResendMessage: (messageId: string, content: string, images?: ChatImageAttachment[]) => Promise<void>;
  confirmAction: (choice: string) => Promise<void>;
  interrupt: () => Promise<void>;
  pauseQueue: () => Promise<void>;
  removeQueuedPrompt: (id: string) => void;
  editQueuedPrompt: (id: string, content: string) => void;
  guideQueuedPrompt: (id: string) => Promise<void>;
  resumeQueue: () => void;
  processQueue: () => void;
  setSelectedModel: (model: string) => void;
  setRuleTrigger: (t: RuleTrigger) => void;
  toggleSkillAttachment: (name: string) => void;
  toggleMcpAttachment: (id: string) => void;
  setDraftProjectId: (id: string | null) => void;
  addDraftImages: (images: ChatImageAttachment[]) => void;
  removeDraftImage: (id: string) => void;
  clearDraftImages: () => void;
}

export function getConversationKey(state: Pick<ChatState, 'activeThreadId' | 'draftConversationId'>): string {
  return state.activeThreadId ? `thread:${state.activeThreadId}` : `draft:${state.draftConversationId}`;
}

export function saveConversationQueue(
  queues: ChatState['conversationQueues'],
  key: string,
  queue: { queuedPrompts: QueuedPrompt[]; queuePaused: boolean },
): ChatState['conversationQueues'] {
  const next = { ...queues };
  if (queue.queuedPrompts.length || queue.queuePaused) next[key] = queue;
  else delete next[key];
  return next;
}

export function stopActiveStream(): void {
  streamState.activeStreamToken += 1;
  const cancel = streamState.cancelCurrentStream;
  streamState.cancelCurrentStream = null;
  cancel?.();
}

export async function interruptActiveStreamForNavigation(state: ChatState): Promise<void> {
  if (!state.isStreaming) {
    stopActiveStream();
    return;
  }

  streamState.activeStreamToken += 1;
  streamState.cancelCurrentStream = null;
  if (!state.activeThreadId) {
    stopActiveStream();
    return;
  }

  try {
    await interruptChat(
      state.activeThreadId,
      streamState.activeStreamHandle?.threadId === state.activeThreadId
        ? streamState.activeStreamHandle.clientMessageId
        : undefined,
    );
  } catch {
    // Keep the stream attached so the backend can finish and persist if the interrupt request fails.
  }
}

export function normalizeMessageContent(content: unknown): string | null {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    const text = content
      .flatMap((block) => {
        if (typeof block === 'string') return [block];
        if (block && typeof block === 'object' && 'text' in block && typeof block.text === 'string')
          return [block.text];
        return [];
      })
      .join('\n');
    return text || null;
  }
  return null;
}

export function summarizeConversationTitle(content: string): string {
  const firstLine = content.split(/\r?\n/).find((line) => line.trim()) || '新建对话';
  const cleaned = firstLine
    .replace(/^\s*\/(goal|plan)\s*/i, '')
    .replace(/[<>]/g, '')
    .trim();
  const title = Array.from(cleaned).slice(0, 22).join('').trim();
  return title || '新建对话';
}
export const streamState = {
  activeStreamToken: 0,
  activeThreadLoadToken: 0,
  cancelCurrentStream: null as (() => void) | null,
  activeStreamHandle: null as {
    threadId: string;
    clientMessageId: string;
    token: number;
    finished: Promise<void>;
  } | null,
};
