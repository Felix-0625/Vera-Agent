import { StoreApi } from 'zustand';
import { createThread, streamChat } from '../api/chatApi';
import { ChatActivityEvent, ChatImageAttachment, ChatMessage, SubagentRun } from '../types/chat';
import { ChatState, saveConversationQueue, streamState, summarizeConversationTitle } from './chatState';
import { useLayoutStore } from './layoutStore';
export function createSendMessage(
  set: StoreApi<ChatState>['setState'],
  get: StoreApi<ChatState>['getState'],
): ChatState['sendMessage'] {
  return async (content: string, groupId?: string, imagesOverride?: ChatImageAttachment[]) => {
    const state = get();
    const images = imagesOverride ?? state.draftImages;
    const queuedText = content.trim() || (images.length ? '请查看我附上的图片并回答。' : '');
    if (state.isStreaming) {
      if (queuedText || images.length) {
        set((current) => ({
          queuedPrompts: [
            ...current.queuedPrompts,
            { id: `queue_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`, content: queuedText, images },
          ],
          draftImages: imagesOverride ? current.draftImages : [],
        }));
      }
      return;
    }
    let threadId = state.activeThreadId;
    const messageText = queuedText;
    if (!messageText) return;
    const conversationLoadToken = streamState.activeThreadLoadToken;

    if (!threadId) {
      try {
        const title = summarizeConversationTitle(messageText);
        const targetProj = state.draftProjectId || undefined;
        const thread = await createThread(title, groupId, targetProj);
        if (
          conversationLoadToken !== streamState.activeThreadLoadToken ||
          get().activeThreadId !== state.activeThreadId ||
          get().draftConversationId !== state.draftConversationId
        ) {
          void get().loadThreads();
          return;
        }
        threadId = thread.thread_id;
        set((s) => {
          const draftKey = `draft:${state.draftConversationId}`;
          const draftQueue = s.conversationQueues[draftKey] || {
            queuedPrompts: s.queuedPrompts,
            queuePaused: s.queuePaused,
          };
          const conversationQueues = saveConversationQueue(s.conversationQueues, draftKey, {
            queuedPrompts: [],
            queuePaused: false,
          });
          return {
            conversationQueues: saveConversationQueue(conversationQueues, `thread:${threadId}`, draftQueue),
            threads: [thread, ...s.threads],
            activeThreadId: threadId,
          };
        });
        if (state.draftConversationId) {
          useLayoutStore
            .getState()
            .adoptRightSidebarLayout(`conversation:${state.draftConversationId}`, `conversation:${threadId}`);
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
    const updateLastAssistant = (update: (message: ChatMessage) => ChatMessage) =>
      set((s) => {
        const msgs = [...s.messages];
        const index = msgs.length - 1;
        if (index >= 0 && msgs[index].role === 'assistant') msgs[index] = update(msgs[index]);
        return { messages: msgs };
      });
    const addActivity = (event: ChatActivityEvent) =>
      set((s) => {
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

    const streamToken = ++streamState.activeStreamToken;
    let resolveStreamFinished!: () => void;
    const streamFinished = new Promise<void>((resolve) => {
      resolveStreamFinished = resolve;
    });
    streamState.activeStreamHandle = {
      threadId,
      clientMessageId: userMsg.id!,
      token: streamToken,
      finished: streamFinished,
    };
    const markStreamFinished = () => {
      resolveStreamFinished();
      if (streamState.activeStreamHandle?.token === streamToken) streamState.activeStreamHandle = null;
    };
    streamState.cancelCurrentStream = streamChat({
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
        if (streamToken !== streamState.activeStreamToken) return;
        set({ currentThinking: { step, text } });
        addActivity({ id: `status-${step}`, kind: 'status', label: text.replace(/[.…]+$/, ''), status: 'working' });
      },
      onTextChunk: (chunk) => {
        if (streamToken !== streamState.activeStreamToken) return;
        currentAssistantText += chunk;
        updateLastAssistant((last) => ({ ...last, content: currentAssistantText }));
      },
      onToolCall: (actionId, toolName, args) => {
        if (streamToken !== streamState.activeStreamToken) return;
        const labels: Record<string, string> = {
          read: '读取文件',
          write: '写入文件',
          edit: '修改文件',
          web_search: '网页搜索',
          fetch_web_page: '读取网页',
          delegate_research: '研究任务',
          delegate_review: '审查任务',
        };
        const label = labels[toolName] || (toolName ? `调用 ${toolName}` : '终端命令');
        set({ currentThinking: { step: 0, text: `Working… ${label}` } });
        const taskDetail = typeof args.task === 'string' ? args.task.trim().slice(0, 120) : '';
        const pathDetail = typeof args.path === 'string' ? args.path : '';
        addActivity({
          id: actionId,
          kind: 'tool',
          label,
          detail: taskDetail || pathDetail || '执行中',
          status: 'working',
        });
      },
      onToolResult: (actionId, _toolName, _output, returncode) => {
        if (streamToken !== streamState.activeStreamToken) return;
        const resultStatus: ChatActivityEvent['status'] = returncode === 0 ? 'done' : 'error';
        set((s) => {
          const activity = s.currentActivity.map((event) =>
            event.id === actionId
              ? { ...event, status: resultStatus, detail: returncode === 0 ? '已完成' : '执行失败' }
              : event,
          );
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
        if (streamToken !== streamState.activeStreamToken) return;
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
        if (streamToken !== streamState.activeStreamToken) return;
        addActivity({
          id: `context-${event.timestamp}`,
          kind: 'status',
          label: event.kind === '换血' ? '上下文换血' : '压缩上下文',
          detail: `${event.before_tokens.toLocaleString()} → ${event.after_tokens.toLocaleString()} Token`,
          status: 'done',
        });
      },
      onApprovalRequired: (actionId, toolName, message, args) => {
        if (streamToken !== streamState.activeStreamToken) return;
        addActivity({
          id: actionId,
          kind: 'tool',
          label: `等待审批：${toolName || '终端命令'}`,
          detail: message,
          status: 'approval',
        });
        set({
          approvalRequest: { action_id: actionId, tool_name: toolName, message, args },
        });
      },
      onFinish: (payload) => {
        markStreamFinished();
        if (streamToken !== streamState.activeStreamToken) return;
        streamState.cancelCurrentStream = null;
        const completed = get().currentActivity.map((event) =>
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
        updateLastAssistant((last) => ({
          ...last,
          extra: { ...last.extra, activity: completed, duration: payload.duration },
        }));
        set({ isStreaming: false, currentThinking: null, currentActivity: [] });
        get().loadThreads();
        get().processQueue();
      },
      onError: (error) => {
        markStreamFinished();
        if (streamToken !== streamState.activeStreamToken) return;
        streamState.cancelCurrentStream = null;
        const failed = get().currentActivity.map((event) =>
          event.status === 'working' ? { ...event, status: 'error' as const, detail: '连接中断' } : event,
        );
        updateLastAssistant((last) => ({
          ...last,
          content: last.content || `模型连接失败：${error.message}`,
          extra: { ...last.extra, activity: failed },
        }));
        set({ isStreaming: false, currentThinking: null, currentActivity: [] });
        get().processQueue();
      },
    });
  };
}
