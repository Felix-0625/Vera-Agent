import { create } from 'zustand';
import {
  confirmApproval,
  createThread,
  deliverOrchestrationResult,
  fetchThreadMessages,
  fetchThreads,
  interruptChat,
  pauseChat,
  resumeChat,
  truncateThreadFromMessage,
} from '../api/chatApi';
import { ChatImageAttachment, ChatMessage } from '../types/chat';
import { createSendMessage } from './chatSendMessage';
import {
  ChatState,
  getConversationKey,
  interruptActiveStreamForNavigation,
  normalizeMessageContent,
  saveConversationQueue,
  streamState,
} from './chatState';
import { useLayoutStore } from './layoutStore';
export const useChatStore = create<ChatState>((set, get) => ({
  threads: [],
  activeThreadId: null,
  draftConversationId: 'draft:initial',
  draftProjectId: null,
  draftImages: [],
  messages: [],
  queuedPrompts: [],
  queuePaused: false,
  conversationQueues: {},
  isStreaming: false,
  currentThinking: null,
  currentActivity: [],
  approvalRequest: null,
  selectedModel: '',
  ruleTrigger: null,
  attachedSkills: [],
  attachedMcps: [],

  loadThreads: async (search?: string) => {
    try {
      const data = await fetchThreads(search);
      set({ threads: data.threads || [] });
    } catch {}
  },

  selectThread: async (threadId: string) => {
    const loadToken = ++streamState.activeThreadLoadToken;
    await interruptActiveStreamForNavigation(get());
    if (loadToken !== streamState.activeThreadLoadToken) return;
    const previous = get();
    const previousKey = getConversationKey(previous);
    const nextKey = `thread:${threadId}`;
    set((state) => {
      const conversationQueues = saveConversationQueue(state.conversationQueues, previousKey, {
        queuedPrompts: state.queuedPrompts,
        queuePaused: state.queuePaused,
      });
      const nextQueue = conversationQueues[nextKey] || { queuedPrompts: [], queuePaused: false };
      return {
        conversationQueues,
        queuedPrompts: nextQueue.queuedPrompts,
        queuePaused: nextQueue.queuePaused,
        activeThreadId: threadId,
        draftConversationId: '',
        draftProjectId: state.threads.find((thread) => thread.thread_id === threadId)?.project_id || null,
        draftImages: [],
        // Clear the previous conversation before its history request can finish.
        messages: [],
        isStreaming: false,
        currentThinking: null,
        currentActivity: [],
        approvalRequest: null,
      };
    });
    try {
      const data = await fetchThreadMessages(threadId);
      if (loadToken !== streamState.activeThreadLoadToken || get().activeThreadId !== threadId) return;
      // Persisted sessions can contain internal tool records and incomplete
      // assistant placeholders (content: null). The chat renderer only handles
      // user/assistant/system text messages, so normalize replay data at the API
      // boundary instead of letting malformed history crash the whole view.
      const messages = (Array.isArray(data.messages) ? data.messages : []).flatMap((raw): ChatMessage[] => {
        if (!raw || !['user', 'assistant', 'system'].includes(raw.role)) return [];
        const content = normalizeMessageContent(raw.content);
        if (content === null) return [];
        return [{ ...raw, content }];
      });
      set({ messages });
    } catch {
      if (loadToken === streamState.activeThreadLoadToken && get().activeThreadId === threadId) set({ messages: [] });
    }
  },

  openDraftConversation: async (projectId = null) => {
    const navigationToken = ++streamState.activeThreadLoadToken;
    await interruptActiveStreamForNavigation(get());
    if (navigationToken !== streamState.activeThreadLoadToken) return;
    const previous = get();
    const previousKey = getConversationKey(previous);
    const draftConversationId = `draft:${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const nextKey = `draft:${draftConversationId}`;
    set((state) => {
      const conversationQueues = saveConversationQueue(state.conversationQueues, previousKey, {
        queuedPrompts: state.queuedPrompts,
        queuePaused: state.queuePaused,
      });
      const nextQueue = conversationQueues[nextKey] || { queuedPrompts: [], queuePaused: false };
      return {
        conversationQueues,
        queuedPrompts: nextQueue.queuedPrompts,
        queuePaused: nextQueue.queuePaused,
        activeThreadId: null,
        draftConversationId,
        draftProjectId: projectId,
        draftImages: [],
        messages: [],
        isStreaming: false,
        currentThinking: null,
        currentActivity: [],
        approvalRequest: null,
      };
    });
  },

  newThread: async (title = '新建对话', groupId?: string, projectId?: string) => {
    const createToken = ++streamState.activeThreadLoadToken;
    await interruptActiveStreamForNavigation(get());
    const previous = get();
    const previousKey = getConversationKey(previous);
    const thread = await createThread(title, groupId, projectId);
    if (createToken !== streamState.activeThreadLoadToken) {
      void get().loadThreads();
      return thread.thread_id;
    }
    set((s) => {
      const conversationQueues = saveConversationQueue(s.conversationQueues, previousKey, {
        queuedPrompts: s.queuedPrompts,
        queuePaused: s.queuePaused,
      });
      const nextQueue = conversationQueues[`thread:${thread.thread_id}`] || { queuedPrompts: [], queuePaused: false };
      return {
        conversationQueues,
        queuedPrompts: nextQueue.queuedPrompts,
        queuePaused: nextQueue.queuePaused,
        threads: [thread, ...s.threads],
        activeThreadId: thread.thread_id,
        draftConversationId: '',
        draftProjectId: projectId || null,
        draftImages: [],
        messages: [],
        currentThinking: null,
        currentActivity: [],
        approvalRequest: null,
      };
    });
    if (!previous.activeThreadId && previous.draftConversationId) {
      useLayoutStore
        .getState()
        .adoptRightSidebarLayout(`conversation:${previous.draftConversationId}`, `conversation:${thread.thread_id}`);
    }
    return thread.thread_id;
  },

  sendMessage: createSendMessage(set, get),

  appendOrchestrationResult: async (threadId, data) => {
    const { messages } = await deliverOrchestrationResult(threadId, data);
    if (get().activeThreadId === threadId) {
      set((state) => {
        const known = new Set(
          state.messages.filter((item) => item.extra?.orchestration_run_id === data.run_id).map((item) => item.id),
        );
        return { messages: [...state.messages, ...messages.filter((message) => !known.has(message.id))] };
      });
    }
    void get().loadThreads();
  },

  confirmAction: async (choice: string) => {
    const state = get();
    if (!state.approvalRequest) return;
    const actionId = state.approvalRequest.action_id;
    set({ approvalRequest: null });
    await confirmApproval(state.activeThreadId || '', actionId, choice);
  },

  editAndResendMessage: async (messageId: string, content: string, images?: ChatImageAttachment[]) => {
    const { activeThreadId, messages, isStreaming, queuePaused } = get();
    if (!activeThreadId || !isStreaming || !queuePaused) return;
    const index = messages.findIndex((message) => message.id === messageId);
    if (index < 0) return;
    const assistantIndex = messages.findLastIndex((message) => message.role === 'assistant');
    const pendingUserIndex = messages.findLastIndex(
      (message, messageIndex) => messageIndex < assistantIndex && message.role === 'user',
    );
    if (index !== pendingUserIndex) return;
    const streamHandle =
      streamState.activeStreamHandle?.threadId === activeThreadId ? streamState.activeStreamHandle : null;
    await interruptChat(activeThreadId, streamHandle?.clientMessageId);
    await streamHandle?.finished;
    streamState.activeStreamToken += 1;
    const cancelStream = streamState.cancelCurrentStream;
    streamState.cancelCurrentStream = null;
    cancelStream?.();
    await truncateThreadFromMessage(activeThreadId, messageId);
    set({
      messages: messages.slice(0, index),
      isStreaming: false,
      currentThinking: null,
      currentActivity: [],
      queuePaused: false,
    });
    await get().sendMessage(content, undefined, images);
  },

  interrupt: async () => {
    const state = get();
    if (!state.activeThreadId || !state.isStreaming) return;
    set({ queuePaused: true });
    await interruptChat(
      state.activeThreadId,
      streamState.activeStreamHandle?.threadId === state.activeThreadId
        ? streamState.activeStreamHandle.clientMessageId
        : undefined,
    );
  },

  removeQueuedPrompt: (id) =>
    set((state) => ({ queuedPrompts: state.queuedPrompts.filter((prompt) => prompt.id !== id) })),
  editQueuedPrompt: (id, content) =>
    set((state) => ({
      queuedPrompts: state.queuedPrompts.map((prompt) => (prompt.id === id ? { ...prompt, content } : prompt)),
    })),
  guideQueuedPrompt: async (id) => {
    const state = get();
    const selected = state.queuedPrompts.find((prompt) => prompt.id === id);
    if (!selected) return;
    const remaining = state.queuedPrompts.filter((prompt) => prompt.id !== id);
    set({ queuedPrompts: [selected, ...remaining] });
    if (!state.isStreaming && !state.queuePaused) get().processQueue();
  },
  pauseQueue: async () => {
    const { activeThreadId, isStreaming } = get();
    if (!activeThreadId || !isStreaming) return;
    set({ queuePaused: true });
    try {
      await pauseChat(activeThreadId);
    } catch (error) {
      set({ queuePaused: false });
      throw error;
    }
  },
  resumeQueue: () => {
    const { activeThreadId, isStreaming } = get();
    set({ queuePaused: false });
    if (activeThreadId && isStreaming) {
      void resumeChat(activeThreadId).catch(() => undefined);
      return;
    }
    get().processQueue();
  },
  processQueue: () => {
    const state = get();
    if (state.isStreaming || state.queuePaused || !state.queuedPrompts.length) return;
    const sourceKey = getConversationKey(state);
    const [next, ...remaining] = state.queuedPrompts;
    set({ queuedPrompts: remaining });
    window.setTimeout(() => {
      const current = get();
      if (getConversationKey(current) !== sourceKey) {
        set((latest) => {
          const saved = latest.conversationQueues[sourceKey] || { queuedPrompts: [], queuePaused: false };
          return {
            conversationQueues: {
              ...latest.conversationQueues,
              [sourceKey]: { queuedPrompts: [next, ...saved.queuedPrompts], queuePaused: true },
            },
          };
        });
        return;
      }
      void get().sendMessage(next.content, undefined, next.images);
    }, 0);
  },

  setSelectedModel: (selectedModel) => set({ selectedModel }),
  setRuleTrigger: (ruleTrigger) => set({ ruleTrigger }),

  toggleSkillAttachment: (name) =>
    set((s) => ({
      attachedSkills: s.attachedSkills.includes(name)
        ? s.attachedSkills.filter((x) => x !== name)
        : [...s.attachedSkills, name],
    })),

  toggleMcpAttachment: (id) =>
    set((s) => ({
      attachedMcps: s.attachedMcps.includes(id) ? s.attachedMcps.filter((x) => x !== id) : [...s.attachedMcps, id],
    })),

  setDraftProjectId: (draftProjectId) => set({ draftProjectId }),
  addDraftImages: (images) => set((s) => ({ draftImages: [...s.draftImages, ...images].slice(0, 4) })),
  removeDraftImage: (id) => set((s) => ({ draftImages: s.draftImages.filter((image) => image.id !== id) })),
  clearDraftImages: () => set({ draftImages: [] }),
}));
