import { create } from 'zustand';
import { ToolTab, ToolTabId } from '../types/tool';
import { useSideChatStore } from './sideChatStore';
import { useChatStore } from './chatStore';
import { useTerminalStore } from './terminalStore';

const INITIAL_TAB: ToolTab = { id: 'tab_initial', toolType: 'launcher', title: '新标签页', closable: true };
export const DEFAULT_TOOL_TABS: ToolTab[] = [INITIAL_TAB];
const DEFAULT_TOOL_TITLES: Partial<Record<ToolTabId, string>> = {
  launcher: '新标签页', diff: '变更', files: '文件', fileDocument: '文件', terminal: '终端', sidechat: '侧边聊天',
  subagents: '子智能体', metrics: '数据看板', gitflow: 'GitFlow', workflow: '流程编排',
};
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
export const getMountedPanelScope = (conversationKey: string, projectKey: string) => JSON.stringify([conversationKey, projectKey]);

interface MountedPanelGroup {
  conversationKey: string;
  projectKey: string;
  toolTypes: ToolTabId[];
}

// Tabs are a view owned by a conversation. Project tools still resolve their
// data from the active conversation's project, but opening/activating a tab in
// one conversation must not change another conversation's tab strip.
export const getToolScope = (_toolType: ToolTabId, _projectId = getCurrentProjectId(), conversationKey = getConversationToolScope()) => conversationKey;

interface ToolTabsState {
  tabsByConversation: Record<string, ToolTab[]>;
  activeTabByConversation: Record<string, string | null>;
  activeScopeByConversation: Record<string, string>;
  mountedPanelsByScope: Record<string, MountedPanelGroup>;
  markPanelMounted: (conversationKey: string, projectKey: string, toolType: ToolTabId) => void;
  adoptConversationTabs: (fromKey: string, toKey: string) => void;
  openTab: (toolType: ToolTabId, title?: string, conversationKey?: string, projectId?: string) => void;
  openSideChatTab: (sideChatId: string, title?: string, conversationKey?: string, projectId?: string) => void;
  closeTab: (id: string, scopeKey: string, conversationKey: string) => void;
  activateTab: (id: string, scopeKey: string, conversationKey: string) => void;
  addNewLauncherTab: (projectId?: string, conversationKey?: string) => void;
  openFileDocumentTab: (path: string, title: string, projectId?: string, conversationKey?: string) => void;
}

export const useToolTabsStore = create<ToolTabsState>((set, get) => ({
  tabsByConversation: {},
  activeTabByConversation: {},
  activeScopeByConversation: {},
  mountedPanelsByScope: {},
  markPanelMounted: (conversationKey, projectKey, toolType) => set((state) => {
    const scopeKey = getMountedPanelScope(conversationKey, projectKey);
    const current = state.mountedPanelsByScope[scopeKey];
    if (current?.toolTypes.includes(toolType)) return state;
    return {
      mountedPanelsByScope: {
        ...state.mountedPanelsByScope,
        [scopeKey]: {
          conversationKey,
          projectKey,
          toolTypes: [...(current?.toolTypes || []), toolType],
        },
      },
    };
  }),
  adoptConversationTabs: (fromKey, toKey) => set((state) => {
    const from = fromKey.startsWith('conversation:') ? fromKey : `conversation:${fromKey}`;
    const to = toKey.startsWith('conversation:') ? toKey : `conversation:${toKey}`;
    if (!state.tabsByConversation[from] || state.tabsByConversation[to]) return state;
    const { [from]: tabs, ...remainingTabs } = state.tabsByConversation;
    const { [from]: activeTabId, ...remainingActive } = state.activeTabByConversation;
    const { [from]: activeScope, ...remainingScopes } = state.activeScopeByConversation;
    const mountedPanelsByScope = { ...state.mountedPanelsByScope };
    for (const [scopeKey, panelGroup] of Object.entries(state.mountedPanelsByScope)) {
      if (panelGroup.conversationKey !== from) continue;
      delete mountedPanelsByScope[scopeKey];
      const nextScopeKey = getMountedPanelScope(to, panelGroup.projectKey);
      const nextGroup = mountedPanelsByScope[nextScopeKey];
      mountedPanelsByScope[nextScopeKey] = {
        conversationKey: to,
        projectKey: panelGroup.projectKey,
        toolTypes: [...new Set([...(nextGroup?.toolTypes || []), ...panelGroup.toolTypes])],
      };
    }
    return {
      tabsByConversation: { ...remainingTabs, [to]: tabs },
      activeTabByConversation: { ...remainingActive, [to]: activeTabId ?? null },
      activeScopeByConversation: { ...remainingScopes, [to]: activeScope === from ? to : activeScope || getProjectToolScope() },
      mountedPanelsByScope,
    };
  }),

  openTab: (toolType, customTitle, requestedConversationKey, requestedProjectId) => {
    // MCP and Skill management is application configuration, so it belongs in Settings.
    if (toolType === 'mcp' || toolType === 'skills') return;
    const conversationKey = requestedConversationKey || getConversationToolScope();
    const scopeKey = getToolScope(toolType, requestedProjectId ?? getCurrentProjectId(), conversationKey);
    if (toolType === 'sidechat') {
      const sideChatId = useSideChatStore.getState().openFromContext(null, '主对话', [], 'recent');
      get().openSideChatTab(sideChatId, customTitle, conversationKey, requestedProjectId);
      return;
    }
    const defaultTabs = DEFAULT_TOOL_TABS;
    const tabs = get().tabsByConversation[scopeKey] || defaultTabs;
    const existing = tabs.find((tab) => tab.toolType === toolType);
    if (existing) {
      set((state) => ({
        tabsByConversation: { ...state.tabsByConversation, [scopeKey]: tabs.map((tab) => tab.id === existing.id ? { ...tab, projectId: requestedProjectId ?? tab.projectId } : tab) },
        activeTabByConversation: { ...state.activeTabByConversation, [scopeKey]: existing.id },
        activeScopeByConversation: { ...state.activeScopeByConversation, [conversationKey]: scopeKey },
      }));
      return;
    }
    const id = `tab_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    const tab: ToolTab = { id, toolType, title: customTitle || DEFAULT_TOOL_TITLES[toolType] || '工具', closable: true, projectId: requestedProjectId ?? undefined };
    set((state) => ({
      tabsByConversation: { ...state.tabsByConversation, [scopeKey]: [...tabs, tab] },
      activeTabByConversation: { ...state.activeTabByConversation, [scopeKey]: id },
      activeScopeByConversation: { ...state.activeScopeByConversation, [conversationKey]: scopeKey },
    }));
  },

  openSideChatTab: (sideChatId, customTitle, requestedConversationKey, requestedProjectId) => {
    const conversationKey = requestedConversationKey || getConversationToolScope();
    const scopeKey = getToolScope('sidechat', requestedProjectId ?? getCurrentProjectId(), conversationKey);
    const tabs = get().tabsByConversation[scopeKey] || [];
    const id = `sidechat_${sideChatId}`;
    const tab: ToolTab = { id, sideChatId, toolType: 'sidechat', title: customTitle || '侧边聊天', closable: true };
    set((state) => ({
      tabsByConversation: { ...state.tabsByConversation, [scopeKey]: [...tabs, tab] },
      activeTabByConversation: { ...state.activeTabByConversation, [scopeKey]: id },
      activeScopeByConversation: { ...state.activeScopeByConversation, [conversationKey]: scopeKey },
    }));
  },

  closeTab: (id, scopeKey, conversationKey) => {
    const tabs = get().tabsByConversation[scopeKey] || [];
    const activeId = get().activeTabByConversation[scopeKey];
    const closing = tabs.find((tab) => tab.id === id);
    if (closing?.toolType === 'sidechat' && closing.sideChatId) useSideChatStore.getState().dispose(closing.sideChatId);
    if (closing?.toolType === 'terminal') {
      const projectId = closing.projectId ?? getCurrentProjectId();
      useTerminalStore.getState().disconnect(`${projectId || 'current-project'}:project-root`);
    }
    const nextTabs = tabs.filter((tab) => tab.id !== id);
    const nextId = activeId === id ? nextTabs.at(-1)?.id ?? null : activeId;
    const nextScope = conversationKey;
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
    const scopeKey = conversationKey;
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
    const scopeKey = conversationKey;
    const tabs = get().tabsByConversation[scopeKey] || DEFAULT_TOOL_TABS;
    const projectId = requestedProjectId ?? getCurrentProjectId() ?? undefined;
    const existing = tabs.find((tab) =>
      tab.toolType === 'fileDocument'
      && tab.filePath === path
      && (tab.projectId ?? projectId) === projectId,
    );
    if (existing) {
      set((state) => ({
        tabsByConversation: {
          ...state.tabsByConversation,
          [scopeKey]: tabs.map((tab) => tab.id === existing.id ? { ...tab, title, projectId } : tab),
        },
        activeTabByConversation: { ...state.activeTabByConversation, [scopeKey]: existing.id },
        activeScopeByConversation: { ...state.activeScopeByConversation, [conversationKey]: scopeKey },
      }));
      return;
    }
    const id = `file_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    const tab: ToolTab = { id, toolType: 'fileDocument', title, filePath: path, projectId, closable: true };
    set((state) => ({
      tabsByConversation: { ...state.tabsByConversation, [scopeKey]: [...tabs, tab] },
      activeTabByConversation: { ...state.activeTabByConversation, [scopeKey]: id },
      activeScopeByConversation: { ...state.activeScopeByConversation, [conversationKey]: scopeKey },
    }));
  },
}));
