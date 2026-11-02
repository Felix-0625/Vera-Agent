/**
 * Ephemeral side chats opened from a conversation's context.
 *
 * Each side chat streams through `/api/chat/stream` with `ephemeral: true` and is closed via
 * `/api/chat/ephemeral/close`; nothing is persisted as a thread.
 */
import { create } from 'zustand';
import { closeEphemeralChat, confirmApproval, interruptChat, streamChat } from '../api/chatApi';
import { ChatActivityEvent, ChatImageAttachment, ChatMessage } from '../types/chat';
import { useChatStore } from './chatStore';

type ContextLimit = 0 | 5 | 10 | 20 | 'full';
type ContextMessage = Pick<ChatMessage, 'role' | 'content'>;

export interface SideChatSession {
  id: string;
  threadId: string | null;
  sourceThreadId: string | null;
  sourceTitle: string;
  projectId: string | null;
  groupId: string | null;
  sourceContext: ContextMessage[];
  contextScope: 'recent' | 'full';
  contextLimit: ContextLimit;
  selectedModel: string;
  contextRevision: number;
  injectedContextRevision: number;
  messages: ChatMessage[];
  currentActivity: ChatActivityEvent[];
  currentStatus: string;
  isStreaming: boolean;
  approvalRequest: { action_id: string; tool_name: string; message: string; args: Record<string, unknown> } | null;
  error: string | null;
}

interface SideChatState {
  sessions: Record<string, SideChatSession>;
  openFromContext: (
    threadId: string | null,
    title: string,
    context: ContextMessage[],
    scope?: 'recent' | 'full',
    limit?: ContextLimit,
  ) => string;
  setContextMessages: (id: string, context: ContextMessage[], limit: ContextLimit) => void;
  setSelectedModel: (id: string, model: string) => void;
  sendMessage: (id: string, content: string, images?: ChatImageAttachment[]) => void;
  confirmAction: (id: string, choice: string) => Promise<void>;
  interrupt: (id: string) => Promise<void>;
  dispose: (id: string) => void;
}

function newSideThreadId(): string {
  return `side_${typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}_${Math.random().toString(16).slice(2)}`}`;
}

function filterContext(context: ContextMessage[]): ContextMessage[] {
  return context
    .filter(
      (message) =>
        (message.role === 'user' || message.role === 'assistant') &&
        typeof message.content === 'string' &&
        message.content.trim(),
    )
    .map(({ role, content }) => ({ role, content }));
}

function updateSession(
  set: (updater: (state: SideChatState) => Partial<SideChatState> | SideChatState) => void,
  id: string,
  update: (session: SideChatSession) => SideChatSession,
) {
  set((state) => {
    const current = state.sessions[id];
    return current ? { sessions: { ...state.sessions, [id]: update(current) } } : {};
  });
}

function stopEphemeral(session: SideChatSession | undefined) {
  if (!session?.threadId) return;
  void interruptChat(session.threadId).catch(() => undefined);
  void closeEphemeralChat(session.threadId).catch(() => undefined);
}

export const useSideChatStore = create<SideChatState>((set, get) => ({
  sessions: {},

  openFromContext: (sourceThreadId, sourceTitle, context, scope = 'recent', limit = scope === 'full' ? 'full' : 5) => {
    const main = useChatStore.getState();
    const resolvedThreadId = sourceThreadId || main.activeThreadId;
    const sourceThread = main.threads.find((thread) => thread.thread_id === resolvedThreadId);
    const projectId = resolvedThreadId ? sourceThread?.project_id || null : main.draftProjectId;
    const id = newSideThreadId();
    const session: SideChatSession = {
      id,
      threadId: null,
      sourceThreadId: resolvedThreadId,
      sourceTitle: sourceTitle || '主对话',
      projectId,
      groupId: sourceThread?.group_id || null,
      sourceContext: filterContext(context.length ? context : main.messages),
      contextScope: scope,
      contextLimit: limit,
      selectedModel: main.selectedModel,
      contextRevision: 1,
      injectedContextRevision: 0,
      messages: [],
      currentActivity: [],
      currentStatus: 'Thinking…',
      isStreaming: false,
      approvalRequest: null,
      error: null,
    };
    set((state) => ({ sessions: { ...state.sessions, [id]: session } }));
    return id;
  },

  setContextMessages: (id, context, limit) =>
    updateSession(set, id, (session) => ({
      ...session,
      sourceContext: filterContext(context).slice(-100),
      contextScope: limit === 'full' ? 'full' : 'recent',
      contextLimit: limit,
      contextRevision: session.contextRevision + 1,
    })),

  setSelectedModel: (id, selectedModel) => updateSession(set, id, (session) => ({ ...session, selectedModel })),

  sendMessage: (id, content, images = []) => {
    const text = content.trim();
    const session = get().sessions[id];
    if (!text || !session || session.isStreaming) return;
    const main = useChatStore.getState();
    const threadId = session.threadId || newSideThreadId();
    const isFirstSideMessage = session.messages.length === 0;
    const contextUpdate = !isFirstSideMessage && session.contextRevision > session.injectedContextRevision;
    updateSession(set, id, (current) => ({
      ...current,
      threadId,
      messages: [
        ...current.messages,
        { role: 'user', content: text, extra: { images } },
        { role: 'assistant', content: '', extra: { activity: [] } },
      ],
      currentActivity: [],
      currentStatus: 'Thinking…',
      isStreaming: true,
      approvalRequest: null,
      error: null,
    }));

    let answer = '';
    const updateAssistant = (updater: (message: ChatMessage) => ChatMessage) =>
      updateSession(set, id, (current) => {
        const messages = [...current.messages];
        const last = messages.length - 1;
        if (last >= 0 && messages[last].role === 'assistant') messages[last] = updater(messages[last]);
        return { ...current, messages };
      });
    const addActivity = (event: ChatActivityEvent) =>
      updateSession(set, id, (current) => {
        const activity = [...current.currentActivity, event];
        const messages = [...current.messages];
        const last = messages.length - 1;
        if (last >= 0 && messages[last].role === 'assistant')
          messages[last] = { ...messages[last], extra: { ...messages[last].extra, activity } };
        return { ...current, messages, currentActivity: activity };
      });

    streamChat({
      thread_id: threadId,
      content: text,
      model_id: session.selectedModel,
      attached_skills: main.attachedSkills,
      attached_mcps: main.attachedMcps,
      group_id: session.groupId || undefined,
      project_id: session.projectId || undefined,
      ephemeral: true,
      images,
      context_messages:
        isFirstSideMessage || contextUpdate
          ? session.contextLimit === 'full'
            ? session.sourceContext
            : session.contextLimit === 0
              ? []
              : session.sourceContext.slice(-session.contextLimit)
          : undefined,
      context_update: contextUpdate,
      onThinking: (_step, label) => {
        updateSession(set, id, (current) => ({
          ...current,
          currentStatus: /executing step/i.test(label) ? 'Working…' : 'Thinking…',
        }));
        addActivity({ id: `status-${Date.now()}-${Math.random()}`, kind: 'status', label, status: 'working' });
      },
      onTextChunk: (chunk) => {
        answer += chunk;
        updateAssistant((message) => ({ ...message, content: answer }));
      },
      onToolCall: (actionId, toolName) => {
        updateSession(set, id, (current) => ({ ...current, currentStatus: `Working… ${toolName || '终端命令'}` }));
        addActivity({ id: actionId, kind: 'tool', label: toolName || '终端命令', detail: '执行中', status: 'working' });
      },
      onToolResult: (actionId, _toolName, _output, returncode) =>
        updateSession(set, id, (current) => {
          const currentActivity = current.currentActivity.map((event) =>
            event.id === actionId
              ? {
                  ...event,
                  status: returncode === 0 ? ('done' as const) : ('error' as const),
                  detail: returncode === 0 ? '已完成' : '执行失败',
                }
              : event,
          );
          const messages = [...current.messages];
          const last = messages.length - 1;
          if (last >= 0 && messages[last].role === 'assistant')
            messages[last] = { ...messages[last], extra: { ...messages[last].extra, activity: currentActivity } };
          return { ...current, messages, currentActivity, currentStatus: 'Thinking…' };
        }),
      onContextManagement: (event) =>
        addActivity({
          id: `context-${event.timestamp}`,
          kind: 'status',
          label: event.kind === '换血' ? '上下文换血' : '压缩上下文',
          detail: `${event.before_tokens.toLocaleString()} → ${event.after_tokens.toLocaleString()} Token`,
          status: 'done',
        }),
      onApprovalRequired: (actionId, toolName, message, args) => {
        addActivity({
          id: actionId,
          kind: 'tool',
          label: `等待审批：${toolName || '终端命令'}`,
          detail: message,
          status: 'approval',
        });
        updateSession(set, id, (current) => ({
          ...current,
          approvalRequest: { action_id: actionId, tool_name: toolName, message, args },
        }));
      },
      onFinish: (payload) =>
        updateSession(set, id, (current) => {
          const completed = current.currentActivity.map((event) =>
            event.status !== 'working'
              ? event
              : event.kind === 'status' && payload.exit_status === 'finish'
                ? { ...event, status: 'done' as const }
                : {
                    ...event,
                    status: 'error' as const,
                    detail:
                      payload.exit_status === 'interrupted'
                        ? '已中断'
                        : payload.exit_status === 'error'
                          ? '模型请求失败'
                          : '未完成',
                  },
          );
          const messages = [...current.messages];
          const last = messages.length - 1;
          if (last >= 0 && messages[last].role === 'assistant')
            messages[last] = {
              ...messages[last],
              extra: { ...messages[last].extra, activity: completed, duration: payload.duration },
            };
          return {
            ...current,
            messages,
            isStreaming: false,
            currentStatus: '',
            currentActivity: [],
            injectedContextRevision: current.contextRevision,
          };
        }),
      onError: (error) =>
        updateSession(set, id, (current) => {
          const failed = current.currentActivity.map((event) =>
            event.status === 'working' ? { ...event, status: 'error' as const, detail: '连接中断' } : event,
          );
          const messages = [...current.messages];
          const last = messages.length - 1;
          if (last >= 0 && messages[last].role === 'assistant')
            messages[last] = { ...messages[last], extra: { ...messages[last].extra, activity: failed } };
          return {
            ...current,
            messages,
            isStreaming: false,
            currentActivity: [],
            currentStatus: '',
            error: error.message,
          };
        }),
    });
  },

  confirmAction: async (id, choice) => {
    const session = get().sessions[id];
    if (!session?.threadId || !session.approvalRequest) return;
    updateSession(set, id, (current) => ({ ...current, approvalRequest: null }));
    await confirmApproval(session.threadId, session.approvalRequest.action_id, choice);
  },

  interrupt: async (id) => {
    const threadId = get().sessions[id]?.threadId;
    if (!threadId) return;
    await interruptChat(threadId);
    updateSession(set, id, (session) => ({ ...session, isStreaming: false, currentStatus: '', currentActivity: [] }));
  },

  dispose: (id) => {
    const session = get().sessions[id];
    stopEphemeral(session);
    set((state) => {
      const { [id]: _removed, ...sessions } = state.sessions;
      return { sessions };
    });
  },
}));
