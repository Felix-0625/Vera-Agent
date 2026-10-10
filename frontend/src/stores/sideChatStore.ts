import { create } from 'zustand';
import { closeEphemeralChat, confirmApproval, interruptChat, streamChat } from '../api/chatApi';
import { useChatStore } from './chatStore';
import { AgentMode, ChatActivityEvent, ChatImageAttachment, ChatMessage } from '../types/chat';

type ContextMessage = Pick<ChatMessage, 'role' | 'content'>;

interface SideChatState {
  threadId: string | null;
  sourceThreadId: string | null;
  sourceTitle: string;
  sourceContext: ContextMessage[];
  contextScope: 'recent' | 'full';
  contextLimit: 5 | 10 | 20 | 'full';
  selectedModel: string;
  contextRevision: number;
  injectedContextRevision: number;
  messages: ChatMessage[];
  currentActivity: ChatActivityEvent[];
  currentStatus: string;
  isStreaming: boolean;
  approvalRequest: { action_id: string; tool_name: string; message: string; args: Record<string, unknown> } | null;
  error: string | null;
  openFromContext: (threadId: string | null, title: string, context: ContextMessage[], scope?: 'recent' | 'full', limit?: 5 | 10 | 20 | 'full') => void;
  setContextMessages: (context: ContextMessage[], limit: 5 | 10 | 20 | 'full') => void;
  setSelectedModel: (model: string) => void;
  sendMessage: (content: string, images?: ChatImageAttachment[]) => void;
  confirmAction: (choice: string) => Promise<void>;
  interrupt: () => Promise<void>;
  dispose: () => void;
}

function newSideThreadId(): string {
  return `side_${typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}_${Math.random().toString(16).slice(2)}`}`;
}

function resetSideSession(threadId: string | null) {
  if (!threadId) return;
  void interruptChat(threadId).catch(() => undefined);
  void closeEphemeralChat(threadId).catch(() => undefined);
}

export const useSideChatStore = create<SideChatState>((set, get) => ({
  threadId: null,
  sourceThreadId: null,
  sourceTitle: '主对话',
  sourceContext: [],
  contextScope: 'recent',
  contextLimit: 5,
  selectedModel: 'deepseek/deepseek-chat',
  contextRevision: 0,
  injectedContextRevision: 0,
  messages: [],
  currentActivity: [],
  currentStatus: 'Thinking…',
  isStreaming: false,
  approvalRequest: null,
  error: null,

  openFromContext: (sourceThreadId, sourceTitle, context, scope = 'recent', limit = scope === 'full' ? 'full' : 5) => {
    resetSideSession(get().threadId);
    const selectedModel = useChatStore.getState().selectedModel;
    const sourceContext = context.filter((message) => (message.role === 'user' || message.role === 'assistant') && typeof message.content === 'string' && message.content.trim()).map(({ role, content }) => ({ role, content }));
    set({
      threadId: newSideThreadId(), sourceThreadId, sourceTitle, sourceContext, contextScope: scope,
      contextLimit: limit, selectedModel,
      contextRevision: 1, injectedContextRevision: 0, messages: [], currentActivity: [],
      currentStatus: 'Thinking…', isStreaming: false, approvalRequest: null, error: null,
    });
  },

  setContextMessages: (context, limit) => set((state) => ({
    sourceContext: context.filter((message) => (message.role === 'user' || message.role === 'assistant') && typeof message.content === 'string' && message.content.trim()).slice(-100).map(({ role, content }) => ({ role, content })),
    contextScope: limit === 'full' ? 'full' : 'recent',
    contextLimit: limit,
    contextRevision: state.contextRevision + 1,
  })),

  setSelectedModel: (selectedModel) => set({ selectedModel }),

  sendMessage: (content, images = []) => {
    const text = content.trim();
    const state = get();
    if (!text || state.isStreaming) return;
    const main = useChatStore.getState();
    const thread = main.threads.find((item) => item.thread_id === state.sourceThreadId);
    const threadId = state.threadId || newSideThreadId();
    const isFirstSideMessage = state.messages.length === 0;
    const contextUpdate = !isFirstSideMessage && state.contextRevision > state.injectedContextRevision;
    const activity: ChatActivityEvent[] = [];
    set((current) => ({
      threadId,
      messages: [...current.messages, { role: 'user', content: text, extra: { images } }, { role: 'assistant', content: '', extra: { activity: [] } }],
      currentActivity: activity,
      currentStatus: 'Thinking…',
      isStreaming: true,
      approvalRequest: null,
      error: null,
    }));

    let answer = '';
    const updateAssistant = (updater: (message: ChatMessage) => ChatMessage) => set((current) => {
      const messages = [...current.messages];
      const last = messages.length - 1;
      if (last >= 0 && messages[last].role === 'assistant') messages[last] = updater(messages[last]);
      return { messages };
    });
    const addActivity = (event: ChatActivityEvent) => set((current) => {
      const nextActivity = [...current.currentActivity, event];
      const messages = [...current.messages];
      const last = messages.length - 1;
      if (last >= 0 && messages[last].role === 'assistant') messages[last] = { ...messages[last], extra: { ...messages[last].extra, activity: nextActivity } };
      return { messages, currentActivity: nextActivity };
    });

    streamChat({
      thread_id: threadId,
      content: text,
      model_id: state.selectedModel,
      mode: main.mode as AgentMode,
      attached_skills: main.attachedSkills,
      attached_mcps: main.attachedMcps,
      group_id: thread?.group_id || undefined,
      project_id: thread?.project_id || undefined,
      ephemeral: true,
      images,
      context_messages: isFirstSideMessage || contextUpdate ? (state.contextLimit === 'full' ? state.sourceContext : state.sourceContext.slice(-state.contextLimit)) : undefined,
      context_update: contextUpdate,
      onThinking: (_step, label) => {
        set({ currentStatus: /executing step/i.test(label) ? 'Working…' : 'Thinking…' });
        addActivity({ id: `status-${Date.now()}-${Math.random()}`, kind: 'status', label, status: 'working' });
      },
      onTextChunk: (chunk) => {
        answer += chunk;
        updateAssistant((message) => ({ ...message, content: answer }));
      },
      onToolCall: (actionId, toolName) => {
        const label = toolName || '终端命令';
        set({ currentStatus: `Working… ${label}` });
        addActivity({ id: actionId, kind: 'tool', label, detail: '执行中', status: 'working' });
      },
      onToolResult: (actionId, _toolName, _output, returncode) => set((current) => {
        const resultStatus: ChatActivityEvent['status'] = returncode === 0 ? 'done' : 'error';
        const currentActivity = current.currentActivity.map((event) => event.id === actionId ? { ...event, status: resultStatus, detail: returncode === 0 ? '已完成' : '执行失败' } : event);
        const messages = [...current.messages];
        const last = messages.length - 1;
        if (last >= 0 && messages[last].role === 'assistant') messages[last] = { ...messages[last], extra: { ...messages[last].extra, activity: currentActivity } };
        return { messages, currentActivity, currentStatus: 'Thinking…' };
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
        set({ approvalRequest: { action_id: actionId, tool_name: toolName, message, args } });
      },
      onFinish: (payload) => {
        const completed = get().currentActivity.map((event) => event.status !== 'working' ? event : event.kind === 'status' ? { ...event, status: 'done' as const } : { ...event, status: 'error' as const, detail: payload.exit_status === 'interrupted' ? '已中断' : '未完成' });
        updateAssistant((message) => ({ ...message, extra: { ...message.extra, activity: completed, duration: payload.duration } }));
        set((current) => ({ isStreaming: false, currentStatus: '', currentActivity: [], injectedContextRevision: current.contextRevision }));
      },
      onError: (error) => {
        const failed = get().currentActivity.map((event) => event.status === 'working' ? { ...event, status: 'error' as const, detail: '连接中断' } : event);
        updateAssistant((message) => ({ ...message, extra: { ...message.extra, activity: failed } }));
        set({ isStreaming: false, currentActivity: [], currentStatus: '', error: error.message });
      },
    });
  },

  confirmAction: async (choice) => {
    const { threadId, approvalRequest } = get();
    if (!threadId || !approvalRequest) return;
    set({ approvalRequest: null });
    await confirmApproval(threadId, approvalRequest.action_id, choice);
  },

  interrupt: async () => {
    const threadId = get().threadId;
    if (!threadId) return;
    await interruptChat(threadId);
    set({ isStreaming: false, currentStatus: '', currentActivity: [] });
  },

  dispose: () => {
    const threadId = get().threadId;
    resetSideSession(threadId);
    set({ threadId: null, messages: [], currentActivity: [], isStreaming: false, currentStatus: '', approvalRequest: null, error: null, sourceThreadId: null, sourceContext: [], contextScope: 'recent', contextLimit: 5, contextRevision: 0, injectedContextRevision: 0 });
  },
}));
