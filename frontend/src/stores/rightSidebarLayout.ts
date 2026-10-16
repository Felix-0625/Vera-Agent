import { useChatStore } from './chatStore';
import { DEFAULT_RIGHT_SIDEBAR_LAYOUT, useLayoutStore } from './layoutStore';

/** Right sidebar visibility and geometry belong to one conversation's view. */
export function getActiveConversationKey(): string {
  const { activeThreadId, draftConversationId } = useChatStore.getState();
  return `conversation:${activeThreadId || draftConversationId || 'draft:initial'}`;
}

export function ensureRightSidebarOpen(conversationKey: string): void {
  const state = useLayoutStore.getState();
  if ((state.rightSidebarByConversation[conversationKey] || DEFAULT_RIGHT_SIDEBAR_LAYOUT).collapsed) {
    state.toggleRight(conversationKey);
  }
}

export function useRightSidebarLayout(explicitConversationKey?: string) {
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const draftConversationId = useChatStore((state) => state.draftConversationId);
  const conversationKey = explicitConversationKey || `conversation:${activeThreadId || draftConversationId || 'draft:initial'}`;
  const layout = useLayoutStore((state) => state.rightSidebarByConversation[conversationKey] || DEFAULT_RIGHT_SIDEBAR_LAYOUT);
  const toggle = useLayoutStore((state) => state.toggleRight);
  const resize = useLayoutStore((state) => state.setRightWidth);
  const maximize = useLayoutStore((state) => state.toggleRightMaximize);

  return {
    rightCollapsed: layout.collapsed,
    rightWidth: layout.width,
    rightMaximized: layout.maximized,
    toggleRight: () => toggle(conversationKey),
    setRightWidth: (width: number) => resize(conversationKey, width),
    toggleRightMaximize: () => maximize(conversationKey),
  };
}
