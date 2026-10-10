import { create } from 'zustand';
import { Thread, ChatMessage, ChatImageAttachment, ApprovalRequest, AgentMode, RuleTrigger, ChatActivityEvent, SubagentRun, QueuedPrompt } from '../types/chat';
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
} from '../api/chatApi';

interface ChatState {
  threads: Thread[];
  activeThreadId: string | null;
  draftConversationId: string;
  draftProjectId: string | null;
  draftImages: ChatImageAttachment[];
  messages: ChatMessage[];
  queuedPrompts: QueuedPrompt[];
  queuePaused: boolean;
  isStreaming: boolean;
  currentThinking: { step: number; text: string } | null;
  currentActivity: ChatActivityEvent[];
  approvalRequest: ApprovalRequest | null;
  mode: AgentMode;
  selectedModel: string;
  ruleTrigger: RuleTrigger;
  attachedSkills: string[];
  attachedMcps: string[];

  loadThreads: (search?: string) => Promise<void>;
  selectThread: (threadId: string) => Promise<void>;
  openDraftConversation: (projectId?: string | null) => void;
  newThread: (title?: string, groupId?: string, projectId?: string) => Promise<string>;
  sendMessage: (content: string, groupId?: string, images?: ChatImageAttachment[]) => Promise<void>;
  editAndResendMessage: (messageId: string, content: string, images?: ChatImageAttachment[]) => Promise<void>;
  confirmAction: (choice: string) => Promise<void>;
  interrupt: () => Promise<void>;
  pauseQueue: () => Promise<void>;
  removeQueuedPrompt: (id: string) => void;
  editQueuedPrompt: (id: string, content: string) => void;
  guideQueuedPrompt: (id: string) => Promise<void>;
  resumeQueue: () => void;
  processQueue: () => void;
  setMode: (mode: AgentMode) => void;
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
let cancelCurrentStream: (() => void) | null = null;

export const useChatStore = create<ChatState>((set, get) => ({
  threads: [],
  activeThreadId: null,
  draftConversationId: 'draft:initial',
  draftProjectId: null,
  draftImages: [],
  messages: [],
  queuedPrompts: [],
  queuePaused: false,
  isStreaming: false,
  currentThinking: null,
  currentActivity: [],
  approvalRequest: null,
  mode: 'confirm',
  selectedModel: 'deepseek/deepseek-chat',
  ruleTrigger: null,
  attachedSkills: [],
  attachedMcps: [],

  loadThreads: async (search?: string) => {
    try {
      const data = await fetchThreads(search);
      set({ threads: data.threads || [] });
    } catch {
      // 保持静默
    }
  },

  selectThread: async (threadId: string) => {
    set({
      activeThreadId: threadId,
      draftConversationId: '',
      draftProjectId: get().threads.find((thread) => thread.thread_id === threadId)?.project_id || null,
      draftImages: [],
      isStreaming: false,
      currentThinking: null,
      currentActivity: [],
      approvalRequest: null,
    });
    try {
      const data = await fetchThreadMessages(threadId);
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
      set({ messages: [] });
    }
  },

  openDraftConversation: (projectId = null) => {
    set({
      activeThreadId: null,
      draftConversationId: `draft:${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      draftProjectId: projectId,
      draftImages: [],
      messages: [],
      queuedPrompts: [],
      queuePaused: false,
      isStreaming: false,
      currentThinking: null,
      currentActivity: [],
      approvalRequest: null,
    });
  },

  newThread: async (title = '新建对话', groupId?: string, projectId?: string) => {
    const thread = await createThread(title, groupId, projectId);
    set((s) => ({
      threads: [thread, ...s.threads],
      activeThreadId: thread.thread_id,
      draftConversationId: '',
      draftProjectId: projectId || null,
      draftImages: [],
      messages: [],
      queuedPrompts: [],
      queuePaused: false,
      currentThinking: null,
      currentActivity: [],
      approvalRequest: null,
    }));
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

    // 若当前为草稿状态，用户首次发送消息时才正式创建该对话并绑定项目
    if (!threadId) {
      try {
        const title = summarizeConversationTitle(messageText);
        const targetProj = state.draftProjectId || undefined;
        const thread = await createThread(title, groupId, targetProj);
        threadId = thread.thread_id;
        set((s) => ({
          threads: [thread, ...s.threads],
          activeThreadId: threadId,
        }));
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
    cancelCurrentStream = streamChat({
      thread_id: threadId,
      content: messageText,
      model_id: state.selectedModel,
      mode: state.mode,
      rule_trigger: state.ruleTrigger,
      attached_skills: state.attachedSkills,
      attached_mcps: state.attachedMcps,
      images,
      group_id: groupId,
      project_id: state.draftProjectId || undefined,
      client_message_id: userMsg.id,
      onThinking: (step, text) => {
        set({ currentThinking: { step, text } });
        addActivity({ id: `status-${step}`, kind: 'status', label: text.replace(/[.…]+$/, ''), status: 'working' });
      },
      onTextChunk: (chunk) => {
        currentAssistantText += chunk;
        updateLastAssistant((last) => ({ ...last, content: currentAssistantText }));
      },
      onToolCall: (actionId, toolName, args) => {
        const labels: Record<string, string> = { read: '读取文件', write: '写入文件', edit: '修改文件', web_search: '网页搜索', fetch_web_page: '读取网页', delegate_research: '研究任务', delegate_review: '审查任务' };
        const label = labels[toolName] || (toolName ? `调用 ${toolName}` : '终端命令');
        set({ currentThinking: { step: 0, text: `Working… ${label}` } });
        const taskDetail = typeof args.task === 'string' ? args.task.trim().slice(0, 120) : '';
        const pathDetail = typeof args.path === 'string' ? args.path : '';
        addActivity({ id: actionId, kind: 'tool', label, detail: taskDetail || pathDetail || '执行中', status: 'working' });
      },
      onToolResult: (actionId, _toolName, _output, returncode) => {
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
      onSubagent: (run: SubagentRun) => updateLastAssistant((last) => {
        const current = last.extra?.subagents || [];
        const index = current.findIndex((item) => item.id === run.id);
        const subagents = [...current];
        if (index < 0) subagents.push(run);
        else subagents[index] = run;
        return { ...last, extra: { ...last.extra, subagents } };
      }),
      onContextManagement: (event) => addActivity({
        id: `context-${event.timestamp}`,
        kind: 'status',
        label: event.kind === '换血' ? '上下文换血' : '压缩上下文',
        detail: `${event.before_tokens.toLocaleString()} → ${event.after_tokens.toLocaleString()} Token`,
        status: 'done',
      }),
      onApprovalRequired: (actionId, toolName, message, args) => {
        addActivity({ id: actionId, kind: 'tool', label: `等待审批：${toolName || '终端命令'}`, detail: message, status: 'approval' });
        set({
          approvalRequest: { action_id: actionId, tool_name: toolName, message, args },
        });
      },
      onFinish: (payload) => {
        if (streamToken !== activeStreamToken) return;
        cancelCurrentStream = null;
        const completed = get().currentActivity.map((event) => event.status !== 'working' ? event : event.kind === 'status' ? { ...event, status: 'done' as const } : { ...event, status: 'error' as const, detail: payload.exit_status === 'interrupted' ? '已中断' : '未完成' });
        updateLastAssistant((last) => ({ ...last, extra: { ...last.extra, activity: completed, duration: payload.duration } }));
        set({ isStreaming: false, currentThinking: null, currentActivity: [] });
        get().loadThreads();
        get().processQueue();
      },
      onError: (error) => {
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
    activeStreamToken += 1;
    const cancelStream = cancelCurrentStream;
    cancelCurrentStream = null;
    await interruptChat(activeThreadId);
    cancelStream?.();
    await truncateThreadFromMessage(activeThreadId, messageId);
    set({ messages: messages.slice(0, index), isStreaming: false, currentThinking: null, currentActivity: [], queuePaused: false });
    await get().sendMessage(content, undefined, images);
  },

  interrupt: async () => {
    const state = get();
    if (!state.activeThreadId) return;
    set({ queuePaused: true });
    activeStreamToken += 1;
    const cancelStream = cancelCurrentStream;
    cancelCurrentStream = null;
    await interruptChat(state.activeThreadId);
    cancelStream?.();
    set({ isStreaming: false, currentThinking: null, currentActivity: [] });
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
    const [next, ...remaining] = state.queuedPrompts;
    set({ queuedPrompts: remaining });
    window.setTimeout(() => { void get().sendMessage(next.content, undefined, next.images); }, 0);
  },

  setMode: (mode) => set({ mode }),
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
