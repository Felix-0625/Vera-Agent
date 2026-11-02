import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { streamChat } from '../api/chatApi';

type StreamRequest = Parameters<typeof streamChat>[0];
const api = vi.hoisted(() => ({
  stream: vi.fn(),
  history: vi.fn(),
  interrupt: vi.fn(),
  threads: vi.fn(),
}));

vi.mock('../api/chatApi', () => ({
  streamChat: api.stream,
  fetchThreadMessages: api.history,
  interruptChat: api.interrupt,
  fetchThreads: api.threads,
  createThread: vi.fn(),
  deliverOrchestrationResult: vi.fn(),
  confirmApproval: vi.fn(),
  pauseChat: vi.fn(),
  resumeChat: vi.fn(),
  truncateThreadFromMessage: vi.fn(),
}));
vi.mock('./layoutStore', () => ({
  useLayoutStore: { getState: () => ({ adoptRightSidebarLayout: vi.fn() }) },
}));

import { useChatStore } from './chatStore';

describe('conversation lifecycle across the extracted send and queue modules', () => {
  let requests: StreamRequest[];

  beforeEach(() => {
    requests = [];
    vi.clearAllMocks();
    api.stream.mockImplementation((request: StreamRequest) => {
      requests.push(request);
      return vi.fn();
    });
    api.history.mockResolvedValue({ messages: [] });
    api.interrupt.mockResolvedValue({ status: 'ok' });
    api.threads.mockResolvedValue({ threads: [] });
    useChatStore.setState({
      activeThreadId: 'thread-a',
      draftConversationId: '',
      draftProjectId: 'project-a',
      draftImages: [],
      threads: [],
      messages: [],
      queuedPrompts: [],
      queuePaused: false,
      conversationQueues: {},
      isStreaming: false,
      currentActivity: [],
      currentThinking: null,
      approvalRequest: null,
      attachedSkills: [],
      attachedMcps: [],
      selectedModel: 'fixture',
    });
  });

  it('keeps queued input with its originating conversation and ignores stale streamed text', async () => {
    await useChatStore.getState().sendMessage('first task');
    requests[0].onTextChunk?.('partial answer');
    await useChatStore.getState().sendMessage('queued task');
    expect(requests).toHaveLength(1);

    await useChatStore.getState().selectThread('thread-b');
    expect(api.interrupt).toHaveBeenCalledWith('thread-a', expect.any(String));
    expect(useChatStore.getState().queuedPrompts).toEqual([]);
    requests[0].onTextChunk?.('late text from thread a');
    expect(useChatStore.getState().messages).toEqual([]);

    await useChatStore.getState().selectThread('thread-a');
    expect(useChatStore.getState().queuedPrompts.map((prompt) => prompt.content)).toEqual(['queued task']);
  });

  it('uses only the most recently selected history when requests complete out of order', async () => {
    let resolveOlder!: (result: { messages: { role: string; content: string }[] }) => void;
    api.history.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOlder = resolve;
        }),
    );
    const older = useChatStore.getState().selectThread('thread-b');
    await vi.waitFor(() => expect(api.history).toHaveBeenCalledWith('thread-b'));
    await useChatStore.getState().selectThread('thread-c');
    resolveOlder({ messages: [{ role: 'assistant', content: 'stale history' }] });
    await older;
    expect(useChatStore.getState().activeThreadId).toBe('thread-c');
    expect(useChatStore.getState().messages).toEqual([]);
  });
});
