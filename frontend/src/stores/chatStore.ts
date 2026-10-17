import { create } from 'zustand';
import { Thread, ChatMessage, ChatImageAttachment, ApprovalRequest, RuleTrigger, ChatActivityEvent, SubagentRun, QueuedPrompt } from '../types/chat';
import {
  fetchThreads,
  createThread,
  fetchThreadMessages,
  streamChat,
  confirmApproval,
  interruptChat,
  pauseChat,
  resumeChat,
  truncateThreadFromMessage,
  deliverOrchestrationResult,
} from '../api/chatApi';
import { useLayoutStore } from './layoutStore';

interface ChatState {
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
  appendOrchestrationResult: (threadId: string, data: { project_id: string; group_id: string; run_id: string; input: string; content: string }) => Promise<void>;
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

let activeStreamToken = 0;
let activeThreadLoadToken = 0;
let cancelCurrentStream: (() => void) | null = null;
let activeStreamHandle: { threadId: string; clientMessageId: string; token: number; finished: Promise<void> } | null = null;

function getConversationKey(state: Pick<ChatState, 'activeThreadId' | 'draftConversationId'>): string {
  return state.activeThreadId ? `thread:${state.activeThreadId}` : `draft:${state.draftConversationId}`;
}

function saveConversationQueue(
  queues: ChatState['conversationQueues'],
  key: string,
  queue: { queuedPrompts: QueuedPrompt[]; queuePaused: boolean },
): ChatState['conversationQueues'] {
  const next = { ...queues };
  if (queue.queuedPrompts.length || queue.queuePaused) next[key] = queue;
  else delete next[key];
  return next;
}

function stopActiveStream(): void {
  activeStreamToken += 1;
  const cancel = cancelCurrentStream;
  cancelCurrentStream = null;
  cancel?.();
}

async function interruptActiveStreamForNavigation(): Promise<void> {
  const state = useChatStore.getState();
  if (!state.isStreaming) {
    stopActiveStream();
    return;
  }

  activeStreamToken += 1;
  cancelCurrentStream = null;
  if (!state.activeThreadId) {
    stopActiveStream();
    return;
  }

  try {
    await interruptChat(state.activeThreadId, activeStreamHandle?.threadId === state.activeThreadId ? activeStreamHandle.clientMessageId : undefined);
  } catch {
    // Keep the stream attached so the backend can finish and persist if the interrupt request fails.
  }
}

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
    } catch {
    }
  },

  selectThread: async (threadId: string) => {
    const loadToken = ++activeThreadLoadToken;
    await interruptActiveStreamForNavigation();
    if (loadToken !== activeThreadLoadToken) return;
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
      if (loadToken !== activeThreadLoadToken || get().activeThreadId !== threadId) return;
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
      if (loadToken === activeThreadLoadToken && get().activeThreadId === threadId) set({ messages: [] });
    }
  },

  openDraftConversation: async (projectId = null) => {
    const navigationToken = ++activeThreadLoadToken;
    await interruptActiveStreamForNavigation();
    if (navigationToken !== activeThreadLoadToken) return;
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
    const createToken = ++activeThreadLoadToken;
    await interruptActiveStreamForNavigation();
    const previous = get();
    const previousKey = getConversationKey(previous);
    const thread = await createThread(title, groupId, projectId);
    if (createToken !== activeThreadLoadToken) {
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
      useLayoutStore.getState().adoptRightSidebarLayout(`conversation:${previous.draftConversationId}`, `conversation:${thread.thread_id}`);
    }
    return thread.thread_id;
  },

  sendMessage: async (content: string, groupId?: string, imagesOverride?: ChatImageAttachment[]) => {
    const state = get();
    const images = imagesOverride ?? state.draftImages;
    const queuedText = content.trim() || (images.length ? '请查看我附上的图片并回答。' : '');
    if (state.isStreaming) {
      if (queuedText || images.length) {
        set((current) => ({ queuedPrompts: [...current.queuedPrompts, { id: `queue_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`, content: queuedText, images }], draftImages: imagesOverride ? current.draftImages : [] }));
      }
      return;
    }
    let threadId = state.activeThreadId;
    const messageText = queuedText;
    if (!messageText) return;
    const conversationLoadToken = activeThreadLoadToken;

    if (!threadId) {
      try {
        const title = summarizeConversationTitle(messageText);
        const targetProj = state.draftProjectId || undefined;
        const thread = await createThread(title, groupId, targetProj);
        if (
          conversationLoadToken !== activeThreadLoadToken ||
          get().activeThreadId !== state.activeThreadId ||
          get().draftConversationId !== state.draftConversationId
        ) {
          void get().loadThreads();
          return;
        }
        threadId = thread.thread_id;
        set((s) => {
          const draftKey = `draft:${state.draftConversationId}`;
          const draftQueue = s.conversationQueues[draftKey] || { queuedPrompts: s.queuedPrompts, queuePaused: s.queuePaused };
          const conversationQueues = saveConversationQueue(s.conversationQueues, draftKey, { queuedPrompts: [], queuePaused: false });
          return {
            conversationQueues: saveConversationQueue(conversationQueues, `thread:${threadId}`, draftQueue),
            threads: [thread, ...s.threads],
            activeThreadId: threadId,
          };
        });
        if (state.draftConversationId) {
          useLayoutStore.getState().adoptRightSidebarLayout(`conversation:${state.draftConversationId}`, `conversation:${threadId}`);
        }
      } catch {
        threadId = `th_${Date.now()}`;
        set({ activeThreadId: threadId });
      }
    }

    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      role: 'user',
      content: messageText,
      extra: {
        rule_trigger: state.ruleTrigger || undefined,
        attached_skills: state.attachedSkills,
        attached_mcps: state.attachedMcps,
        images,
      },
      timestamp: Date.now(),
    };

    set((s) => ({
      messages: [...s.messages, userMsg, { role: 'assistant', content: '', extra: { activity: [] } }],
      draftImages: [],
      isStreaming: true,
      currentThinking: { step: 0, text: '准备执行...' },
      currentActivity: [],
      approvalRequest: null,
      ruleTrigger: null,
    }));

    let currentAssistantText = '';
    const updateLastAssistant = (update: (message: ChatMessage) => ChatMessage) => set((s) => {
      const msgs = [...s.messages];
      const index = msgs.length - 1;
      if (index >= 0 && msgs[index].role === 'assistant') msgs[index] = update(msgs[index]);
      return { messages: msgs };
    });
    const addActivity = (event: ChatActivityEvent) => set((s) => {
      const existingIndex = s.currentActivity.findIndex((item) => item.id === event.id);
      const activity = [...s.currentActivity];
      if (existingIndex < 0) activity.push(event);
      else activity[existingIndex] = event;
      const msgs = [...s.messages];
      const index = msgs.length - 1;
      if (index >= 0 && msgs[index].role === 'assistant') {
        const last = msgs[index];
        msgs[index] = { ...last, extra: { ...last.extra, activity } };
      }
      return { currentActivity: activity, messages: msgs };
    });

    const streamToken = ++activeStreamToken;
    let resolveStreamFinished!: () => void;
    const streamFinished = new Promise<void>((resolve) => { resolveStreamFinished = resolve; });
    activeStreamHandle = { threadId, clientMessageId: userMsg.id!, token: streamToken, finished: streamFinished };
    const markStreamFinished = () => {
      resolveStreamFinished();
      if (activeStreamHandle?.token === streamToken) activeStreamHandle = null;
    };
    cancelCurrentStream = streamChat({
      thread_id: threadId,
      content: messageText,
      model_id: state.selectedModel,
      rule_trigger: state.ruleTrigger,
      attached_skills: state.attachedSkills,
      attached_mcps: state.attachedMcps,
      images,
      group_id: groupId,
      project_id: state.draftProjectId || undefined,
      client_message_id: userMsg.id,
      onThinking: (step, text) => {
        if (streamToken !== activeStreamToken) return;
        set({ currentThinking: { step, text } });
        addActivity({ id: `status-${step}`, kind: 'status', label: text.replace(/[.…]+$/, ''), status: 'working' });
      },
      onTextChunk: (chunk) => {
        if (streamToken !== activeStreamToken) return;
        currentAssistantText += chunk;
        updateLastAssistant((last) => ({ ...last, content: currentAssistantText }));
      },
      onToolCall: (actionId, toolName, args) => {
        if (streamToken !== activeStreamToken) return;
        const labels: Record<string, string> = { read: '读取文件', write: '写入文件', edit: '修改文件', web_search: '网页搜索', fetch_web_page: '读取网页', delegate_research: '研究任务', delegate_review: '审查任务' };
        const label = labels[toolName] || (toolName ? `调用 ${toolName}` : '终端命令');
        set({ currentThinking: { step: 0, text: `Working… ${label}` } });
        const taskDetail = typeof args.task === 'string' ? args.task.trim().slice(0, 120) : '';
        const pathDetail = typeof args.path === 'string' ? args.path : '';
        addActivity({ id: actionId, kind: 'tool', label, detail: taskDetail || pathDetail || '执行中', status: 'working' });
      },
      onToolResult: (actionId, _toolName, _output, returncode) => {
        if (streamToken !== activeStreamToken) return;
        const resultStatus: ChatActivityEvent['status'] = returncode === 0 ? 'done' : 'error';
        set((s) => {
          const activity = s.currentActivity.map((event) => event.id === actionId ? { ...event, status: resultStatus, detail: returncode === 0 ? '已完成' : '执行失败' } : event);
          const msgs = [...s.messages];
          const index = msgs.length - 1;
          if (index >= 0 && msgs[index].role === 'assistant') {
            const last = msgs[index];
            msgs[index] = { ...last, extra: { ...last.extra, activity } };
          }
          return { currentActivity: activity, messages: msgs, currentThinking: { step: 0, text: 'Thinking…' } };
        });
      },
      onSubagent: (run: SubagentRun) => {
        if (streamToken !== activeStreamToken) return;
        updateLastAssistant((last) => {
        const current = last.extra?.subagents || [];
        const index = current.findIndex((item) => item.id === run.id);
        const subagents = [...current];
        if (index < 0) subagents.push(run);
        else subagents[index] = run;
        return { ...last, extra: { ...last.extra, subagents } };
        });
      },
      onContextManagement: (event) => {
        if (streamToken !== activeStreamToken) return;
        addActivity({
          id: `context-${event.timestamp}`,
          kind: 'status',
          label: event.kind === '换血' ? '上下文换血' : '压缩上下文',
          detail: `${event.before_tokens.toLocaleString()} → ${event.after_tokens.toLocaleString()} Token`,
          status: 'done',
        });
      },
      onApprovalRequired: (actionId, toolName, message, args) => {
        if (streamToken !== activeStreamToken) return;
        addActivity({ id: actionId, kind: 'tool', label: `等待审批：${toolName || '终端命令'}`, detail: message, status: 'approval' });
        set({
          approvalRequest: { action_id: actionId, tool_name: toolName, message, args },
        });
      },
      onFinish: (payload) => {
        markStreamFinished();
        if (streamToken !== activeStreamToken) return;
        cancelCurrentStream = null;
        const completed = get().currentActivity.map((event) => event.status !== 'working' ? event : event.kind === 'status' && payload.exit_status === 'finish' ? { ...event, status: 'done' as const } : { ...event, status: 'error' as const, detail: payload.exit_status === 'interrupted' ? '已中断' : payload.exit_status === 'error' ? '模型请求失败' : '未完成' });
        updateLastAssistant((last) => ({ ...last, extra: { ...last.extra, activity: completed, duration: payload.duration } }));
        set({ isStreaming: false, currentThinking: null, currentActivity: [] });
        get().loadThreads();
        get().processQueue();
      },
      onError: (error) => {
        markStreamFinished();
        if (streamToken !== activeStreamToken) return;
        cancelCurrentStream = null;
        const failed = get().currentActivity.map((event) => event.status === 'working' ? { ...event, status: 'error' as const, detail: '连接中断' } : event);
        updateLastAssistant((last) => ({
          ...last,
          content: last.content || `模型连接失败：${error.message}`,
          extra: { ...last.extra, activity: failed },
        }));
        set({ isStreaming: false, currentThinking: null, currentActivity: [] });
        get().processQueue();
      },
    });
  },

  appendOrchestrationResult: async (threadId, data) => {
    const { messages } = await deliverOrchestrationResult(threadId, data);
    if (get().activeThreadId === threadId) {
      set((state) => {
        const known = new Set(state.messages.filter((item) => item.extra?.orchestration_run_id === data.run_id).map((item) => item.id));
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
    const pendingUserIndex = messages.findLastIndex((message, messageIndex) => messageIndex < assistantIndex && message.role === 'user');
    if (index !== pendingUserIndex) return;
    const streamHandle = activeStreamHandle?.threadId === activeThreadId ? activeStreamHandle : null;
    await interruptChat(activeThreadId, streamHandle?.clientMessageId);
    await streamHandle?.finished;
    activeStreamToken += 1;
    const cancelStream = cancelCurrentStream;
    cancelCurrentStream = null;
    cancelStream?.();
    await truncateThreadFromMessage(activeThreadId, messageId);
    set({ messages: messages.slice(0, index), isStreaming: false, currentThinking: null, currentActivity: [], queuePaused: false });
    await get().sendMessage(content, undefined, images);
  },

  interrupt: async () => {
    const state = get();
    if (!state.activeThreadId || !state.isStreaming) return;
    set({ queuePaused: true });
    await interruptChat(state.activeThreadId, activeStreamHandle?.threadId === state.activeThreadId ? activeStreamHandle.clientMessageId : undefined);
  },

  removeQueuedPrompt: (id) => set((state) => ({ queuedPrompts: state.queuedPrompts.filter((prompt) => prompt.id !== id) })),
  editQueuedPrompt: (id, content) => set((state) => ({ queuedPrompts: state.queuedPrompts.map((prompt) => prompt.id === id ? { ...prompt, content } : prompt) })),
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
          return { conversationQueues: { ...latest.conversationQueues, [sourceKey]: { queuedPrompts: [next, ...saved.queuedPrompts], queuePaused: true } } };
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
      attachedMcps: s.attachedMcps.includes(id)
        ? s.attachedMcps.filter((x) => x !== id)
        : [...s.attachedMcps, id],
    })),

  setDraftProjectId: (draftProjectId) => set({ draftProjectId }),
  addDraftImages: (images) => set((s) => ({ draftImages: [...s.draftImages, ...images].slice(0, 4) })),
  removeDraftImage: (id) => set((s) => ({ draftImages: s.draftImages.filter((image) => image.id !== id) })),
  clearDraftImages: () => set({ draftImages: [] }),
}));

function normalizeMessageContent(content: unknown): string | null {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    const text = content.flatMap((block) => {
      if (typeof block === 'string') return [block];
      if (block && typeof block === 'object' && 'text' in block && typeof block.text === 'string') return [block.text];
      return [];
    }).join('\n');
    return text || null;
  }
  return null;
}

function summarizeConversationTitle(content: string): string {
  const firstLine = content.split(/\r?\n/).find((line) => line.trim()) || '新建对话';
  const cleaned = firstLine.replace(/^\s*\/(goal|plan)\s*/i, '').replace(/[<>]/g, '').trim();
  const title = Array.from(cleaned).slice(0, 22).join('').trim();
  return title || '新建对话';
}
