import React, { useEffect, useRef } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { useToolTabsStore } from '../../stores/toolTabsStore';
import { useSideChatStore } from '../../stores/sideChatStore';
import { ensureRightSidebarOpen, getActiveConversationKey } from '../../stores/rightSidebarLayout';
import { MessageItem } from './MessageItem';

export const MessageStream: React.FC = () => {
  const { messages, isStreaming, queuePaused, currentThinking, activeThreadId, threads, editAndResendMessage } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentThinking]);

  const askForDetails = (message: (typeof messages)[number]) => {
    const index = messages.indexOf(message);
    const context = messages.slice(0, index + 1);
    const title = threads.find((thread) => thread.thread_id === activeThreadId)?.title || '主对话';
    const sideChatId = useSideChatStore.getState().openFromContext(activeThreadId, title, context);
    const conversationKey = getActiveConversationKey();
    useToolTabsStore.getState().openSideChatTab(sideChatId, title || '侧边聊天', conversationKey);
    ensureRightSidebarOpen(conversationKey);
  };

  const streamingAssistantIndex = isStreaming ? messages.findLastIndex((message) => message.role === 'assistant') : -1;
  const pendingUserIndex = streamingAssistantIndex >= 0 ? messages.findLastIndex((message, index) => index < streamingAssistantIndex && message.role === 'user') : -1;
  const thinkingText = currentThinking?.text || '';
  const streamLabel = thinkingText.startsWith('Working')
    ? '正在执行工具…'
    : thinkingText.includes('连接模型')
      ? '连接中…'
      : thinkingText.includes('模型处理中')
        ? '思考中…'
        : thinkingText.includes('启动子智能体')
          ? '正在启动子智能体…'
      : thinkingText.includes('生成回答')
        ? '生成中…'
        : '准备中…';

  return (
    <div
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: 'var(--space-4) var(--space-5)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {messages.map((message, index) => (
        <MessageItem key={message.id || index} message={message} isStreaming={index === streamingAssistantIndex} streamLabel={streamLabel} onAskDetails={message.role === 'assistant' && Boolean(message.content) ? askForDetails : undefined} onEditMessage={queuePaused && index === pendingUserIndex && message.id && activeThreadId ? (_message, content) => editAndResendMessage(message.id!, content, message.extra?.images) : undefined} />
      ))}

      <div ref={bottomRef} />
    </div>
  );
};
