import { create } from 'zustand';
import { ToolTab, ToolTabId } from '../types/tool';
import { useSideChatStore } from './sideChatStore';
import { useChatStore } from './chatStore';

const INITIAL_TAB: ToolTab = { id: 'tab_initial', toolType: 'launcher', title: '新标签页', closable: true };
export const DEFAULT_TOOL_TABS: ToolTab[] = [INITIAL_TAB];
const DEFAULT_TOOL_TITLES: Record<ToolTabId, string> = {
  launcher: '新标签页', diff: '变更', files: '文件', fileDocument: '文件', terminal: '终端', sidechat: '侧边聊天',
  subagents: '子智能体', metrics: '数据看板', mcp: 'MCP 市场', skills: 'Skill 市场', gitflow: 'GitFlow', workflow: '分组管理',
};
const CONVERSATION_TOOLS = new Set<ToolTabId>(['sidechat', 'subagents']);

export const getConversationToolScope = () => {
  const { activeThreadId, draftConversationId } = useChatStore.getState();
  return `conversation:${activeThreadId || draftConversationId || 'draft:initial'}`;
};

export const getCurrentProjectId = () => {
  const state = useChatStore.getState();
  return state.activeThreadId
    ? state.threads.find((thread) => thread.thread_id === state.activeThreadId)?.project_id || null
    : state.draftProjectId;
};

export const getProjectToolScope = (projectId = getCurrentProjectId()) => `project:${projectId || 'workspace'}`;

export const getToolScope = (toolType: ToolTabId, projectId = getCurrentProjectId(), conversationKey = getConversationToolScope()) =>
  CONVERSATION_TOOLS.has(toolType) ? conversationKey : getProjectToolScope(projectId);

interface ToolTabsState {
  tabsByConversation: Record<string, ToolTab[]>;
  activeTabByConversation: Record<string, string | null>;
  activeScopeByConversation: Record<string, string>;
  mountedPanelsByProject: Record<string, ToolTabId[]>;
  markPanelMounted: (projectKey: string, toolType: ToolTabId) => void;
  adoptConversationTabs: (fromKey: string, toKey: string) => void;
  openTab: (toolType: ToolTabId, title?: string, conversationKey?: string, projectId?: string) => void;
  closeTab: (id: string, scopeKey: string, conversationKey: string) => void;
  activateTab: (id: string, scopeKey: string, conversationKey: string) => void;
  addNewLauncherTab: (projectId?: string, conversationKey?: string) => void;
  openFileDocumentTab: (path: string, title: string, projectId?: string, conversationKey?: string) => void;
}

export const useToolTabsStore = create<ToolTabsState>((set, get) => ({
  tabsByConversation: {},
  activeTabByConversation: {},
  activeScopeByConversation: {},
  mountedPanelsByProject: {},
  markPanelMounted: (projectKey, toolType) => set((state) => {
    const current = state.mountedPanelsByProject[projectKey] || [];
    return current.includes(toolType) ? state : { mountedPanelsByProject: { ...state.mountedPanelsByProject, [projectKey]: [...current, toolType] } };
  }),
  adoptConversationTabs: (fromKey, toKey) => set((state) => {
    const from = fromKey.startsWith('conversation:') ? fromKey : `conversation:${fromKey}`;
    const to = toKey.startsWith('conversation:') ? toKey : `conversation:${toKey}`;
    if (!state.tabsByConversation[from] || state.tabsByConversation[to]) return state;
    const { [from]: tabs, ...remainingTabs } = state.tabsByConversation;
    const { [from]: activeTabId, ...remainingActive } = state.activeTabByConversation;
    const { [from]: activeScope, ...remainingScopes } = state.activeScopeByConversation;
    return {
      tabsByConversation: { ...remainingTabs, [to]: tabs },
      activeTabByConversation: { ...remainingActive, [to]: activeTabId ?? null },
      activeScopeByConversation: { ...remainingScopes, [to]: activeScope === from ? to : activeScope || getProjectToolScope() },
    };
  }),

  openTab: (toolType, customTitle, requestedConversationKey, requestedProjectId) => {
    const conversationKey = requestedConversationKey || getConversationToolScope();
    const scopeKey = getToolScope(toolType, requestedProjectId ?? getCurrentProjectId(), conversationKey);
    const defaultTabs = scopeKey.startsWith('project:') ? DEFAULT_TOOL_TABS : [];
    const tabs = get().tabsByConversation[scopeKey] || defaultTabs;
    const existing = tabs.find((tab) => tab.toolType === toolType);
    if (existing) {
      set((state) => ({
        activeTabByConversation: { ...state.activeTabByConversation, [scopeKey]: existing.id },
        activeScopeByConversation: { ...state.activeScopeByConversation, [conversationKey]: scopeKey },
      }));
      return;
    }
    const id = `tab_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    const tab: ToolTab = { id, toolType, title: customTitle || DEFAULT_TOOL_TITLES[toolType] || '工具', closable: true };
    set((state) => ({
      tabsByConversation: { ...state.tabsByConversation, [scopeKey]: [...tabs, tab] },
      activeTabByConversation: { ...state.activeTabByConversation, [scopeKey]: id },
      activeScopeByConversation: { ...state.activeScopeByConversation, [conversationKey]: scopeKey },
    }));
  },

  closeTab: (id, scopeKey, conversationKey) => {
    const tabs = get().tabsByConversation[scopeKey] || [];
    const activeId = get().activeTabByConversation[scopeKey];
    if (tabs.find((tab) => tab.id === id)?.toolType === 'sidechat') useSideChatStore.getState().dispose();
    const nextTabs = tabs.filter((tab) => tab.id !== id);
    const nextId = activeId === id ? nextTabs.at(-1)?.id ?? null : activeId;
    const projectKey = getProjectToolScope();
    const conversationTabs = get().tabsByConversation[conversationKey] || [];
    const currentScope = get().activeScopeByConversation[conversationKey] || projectKey;
    const nextScope = currentScope !== scopeKey || nextId
      ? currentScope
      : (scopeKey === projectKey && conversationTabs.length ? conversationKey : projectKey);
    set((state) => ({
      tabsByConversation: { ...state.tabsByConversation, [scopeKey]: nextTabs },
      activeTabByConversation: { ...state.activeTabByConversation, [scopeKey]: nextId },
      activeScopeByConversation: { ...state.activeScopeByConversation, [conversationKey]: nextScope },
    }));
  },

  activateTab: (id, scopeKey, conversationKey) => set((state) => ({
    activeTabByConversation: { ...state.activeTabByConversation, [scopeKey]: id },
    activeScopeByConversation: { ...state.activeScopeByConversation, [conversationKey]: scopeKey },
  })),

  addNewLauncherTab: (requestedProjectId, requestedConversationKey) => {
    const conversationKey = requestedConversationKey || getConversationToolScope();
    const scopeKey = getProjectToolScope(requestedProjectId ?? getCurrentProjectId());
    const tabs = get().tabsByConversation[scopeKey] || DEFAULT_TOOL_TABS;
    const id = `tab_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    const tab: ToolTab = { id, toolType: 'launcher', title: '新标签页', closable: true };
    set((state) => ({
      tabsByConversation: { ...state.tabsByConversation, [scopeKey]: [...tabs, tab] },
      activeTabByConversation: { ...state.activeTabByConversation, [scopeKey]: id },
      activeScopeByConversation: { ...state.activeScopeByConversation, [conversationKey]: scopeKey },
    }));
  },

  openFileDocumentTab: (path, title, requestedProjectId, requestedConversationKey) => {
    const conversationKey = requestedConversationKey || getConversationToolScope();
    const scopeKey = getProjectToolScope(requestedProjectId ?? getCurrentProjectId());
    const tabs = get().tabsByConversation[scopeKey] || DEFAULT_TOOL_TABS;
    const existing = tabs.find((tab) => tab.toolType === 'fileDocument' && tab.filePath === path);
    if (existing) {
      set((state) => ({
        activeTabByConversation: { ...state.activeTabByConversation, [scopeKey]: existing.id },
        activeScopeByConversation: { ...state.activeScopeByConversation, [conversationKey]: scopeKey },
      }));
      return;
    }
    const id = `file_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    const tab: ToolTab = { id, toolType: 'fileDocument', title, filePath: path, closable: true };
    set((state) => ({
      tabsByConversation: { ...state.tabsByConversation, [scopeKey]: [...tabs, tab] },
      activeTabByConversation: { ...state.activeTabByConversation, [scopeKey]: id },
      activeScopeByConversation: { ...state.activeScopeByConversation, [conversationKey]: scopeKey },
    }));
  },
}));
