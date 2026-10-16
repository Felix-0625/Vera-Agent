/** A tab's local interaction state belongs to its conversation and tab ID. */
export function getActivePanelInstanceKey(conversationKey: string, tabId?: string, toolType?: string | null): string {
  return `${conversationKey}:${tabId || toolType || 'empty'}`;
}
