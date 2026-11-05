/**
 * UI layout and modal visibility (zustand): theme, sidebar sizes, per-conversation right sidebar
 * layout, bottom drawer, and which dialogs are open.
 */
import { create } from 'zustand';
import type { Project } from '../types/project';
import { McpServerConfig, ModelConfig } from '../types/settings';

interface LayoutState {
  theme: 'light' | 'dark';
  // Sidebar state
  leftCollapsed: boolean;
  leftWidth: number;
  rightSidebarByConversation: Record<string, RightSidebarLayout>;
  bottomDrawerOpen: boolean;
  bottomDrawerHeight: number;

  // Modals state
  settingsOpen: boolean;
  settingsTab: string;
  projectSelectorOpen: boolean;
  projectSelectorView: 'list' | 'create' | 'edit';
  editingProject: Project | null;
  historyOpen: boolean;
  scheduledTasksOpen: boolean;
  scheduledTasksVersion: number;
  workflowTemplatesOpen: boolean;
  taskboardOpen: boolean;
  newTaskDialogOpen: boolean;
  newTaskPrompt: string;
  modelConfigOpen: boolean;
  editingModel: ModelConfig | null;
  modelCatalogVersion: number;
  mcpCatalogVersion: number;
  mcpConfigOpen: boolean;
  editingMcp: McpServerConfig | null;

  // Actions
  toggleLeft: () => void;
  toggleTheme: () => void;
  setLeftWidth: (w: number) => void;
  toggleRight: (conversationKey: string) => void;
  setRightWidth: (conversationKey: string, w: number) => void;
  toggleRightMaximize: (conversationKey: string) => void;
  adoptRightSidebarLayout: (fromKey: string, toKey: string) => void;
  toggleBottomDrawer: () => void;
  setBottomDrawerHeight: (height: number) => void;

  openSettings: (tab?: string) => void;
  closeSettings: () => void;
  setProjectSelectorOpen: (open: boolean) => void;
  openProjectCreate: () => void;
  openProjectEdit: (project: Project) => void;
  setHistoryOpen: (open: boolean) => void;
  setScheduledTasksOpen: (open: boolean) => void;
  notifyScheduledTasksChanged: () => void;
  setWorkflowTemplatesOpen: (open: boolean) => void;
  setTaskboardOpen: (open: boolean) => void;
  setNewTaskDialogOpen: (open: boolean, prompt?: string) => void;
  setNewTaskPrompt: (prompt: string) => void;
  openModelConfig: (model?: ModelConfig | null) => void;
  notifyModelCatalogChanged: () => void;
  notifyMcpCatalogChanged: () => void;
  closeModelConfig: () => void;
  openMcpConfig: (mcp?: McpServerConfig | null) => void;
  closeMcpConfig: () => void;
}

export interface RightSidebarLayout {
  collapsed: boolean;
  width: number;
  maximized: boolean;
}

export const DEFAULT_RIGHT_SIDEBAR_LAYOUT: RightSidebarLayout = {
  collapsed: true,
  width: 560,
  maximized: false,
};

function readTheme(): 'light' | 'dark' {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
}

function applyTheme(theme: 'light' | 'dark') {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem('vera-agent-theme', theme);
  const workspaceColor = getComputedStyle(document.documentElement).getPropertyValue('--bg-workspace').trim();
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', workspaceColor);
}

export const useLayoutStore = create<LayoutState>((set) => ({
  theme: readTheme(),
  leftCollapsed: false,
  leftWidth: 240,
  rightSidebarByConversation: {},
  bottomDrawerOpen: false,
  bottomDrawerHeight: 260,

  settingsOpen: false,
  settingsTab: 'permissions',
  projectSelectorOpen: false,
  projectSelectorView: 'list',
  editingProject: null,
  historyOpen: false,
  scheduledTasksOpen: false,
  scheduledTasksVersion: 0,
  workflowTemplatesOpen: false,
  taskboardOpen: false,
  newTaskDialogOpen: false,
  newTaskPrompt: '',
  modelConfigOpen: false,
  editingModel: null,
  modelCatalogVersion: 0,
  mcpCatalogVersion: 0,
  mcpConfigOpen: false,
  editingMcp: null,

  toggleLeft: () => set((s) => ({ leftCollapsed: !s.leftCollapsed })),
  toggleTheme: () =>
    set((state) => {
      const theme = state.theme === 'light' ? 'dark' : 'light';
      applyTheme(theme);
      return { theme };
    }),
  setLeftWidth: (w) => set({ leftWidth: w }),
  toggleRight: (key) =>
    set((s) => {
      const current = s.rightSidebarByConversation[key] || DEFAULT_RIGHT_SIDEBAR_LAYOUT;
      return {
        rightSidebarByConversation: {
          ...s.rightSidebarByConversation,
          [key]: { ...current, collapsed: !current.collapsed },
        },
      };
    }),
  setRightWidth: (key, width) =>
    set((s) => {
      const current = s.rightSidebarByConversation[key] || DEFAULT_RIGHT_SIDEBAR_LAYOUT;
      return { rightSidebarByConversation: { ...s.rightSidebarByConversation, [key]: { ...current, width } } };
    }),
  toggleRightMaximize: (key) =>
    set((s) => {
      const current = s.rightSidebarByConversation[key] || DEFAULT_RIGHT_SIDEBAR_LAYOUT;
      return {
        rightSidebarByConversation: {
          ...s.rightSidebarByConversation,
          [key]: { ...current, maximized: !current.maximized },
        },
      };
    }),
  adoptRightSidebarLayout: (fromKey, toKey) =>
    set((s) => {
      const from = fromKey.startsWith('conversation:') ? fromKey : `conversation:${fromKey}`;
      const to = toKey.startsWith('conversation:') ? toKey : `conversation:${toKey}`;
      if (!s.rightSidebarByConversation[from] || s.rightSidebarByConversation[to]) return s;
      const { [from]: layout, ...remaining } = s.rightSidebarByConversation;
      return { rightSidebarByConversation: { ...remaining, [to]: layout } };
    }),
  toggleBottomDrawer: () => set((s) => ({ bottomDrawerOpen: !s.bottomDrawerOpen })),
  setBottomDrawerHeight: (height) => set({ bottomDrawerHeight: height }),

  openSettings: (tab = 'permissions') => set({ settingsOpen: true, settingsTab: tab }),
  closeSettings: () => set({ settingsOpen: false }),
  setProjectSelectorOpen: (open) =>
    set({ projectSelectorOpen: open, projectSelectorView: 'list', editingProject: null }),
  openProjectCreate: () => set({ projectSelectorOpen: true, projectSelectorView: 'create', editingProject: null }),
  openProjectEdit: (project) =>
    set({ projectSelectorOpen: true, projectSelectorView: 'edit', editingProject: project }),
  setHistoryOpen: (open) => set({ historyOpen: open }),
  setScheduledTasksOpen: (open) => set({ scheduledTasksOpen: open }),
  notifyScheduledTasksChanged: () => set((state) => ({ scheduledTasksVersion: state.scheduledTasksVersion + 1 })),
  setWorkflowTemplatesOpen: (open) => set({ workflowTemplatesOpen: open }),
  setTaskboardOpen: (open) => set({ taskboardOpen: open }),
  setNewTaskDialogOpen: (open, prompt = '') => set({ newTaskDialogOpen: open, newTaskPrompt: open ? prompt : '' }),
  setNewTaskPrompt: (newTaskPrompt) => set({ newTaskPrompt }),
  openModelConfig: (model = null) => set({ modelConfigOpen: true, editingModel: model }),
  notifyModelCatalogChanged: () => set((state) => ({ modelCatalogVersion: state.modelCatalogVersion + 1 })),
  notifyMcpCatalogChanged: () => set((state) => ({ mcpCatalogVersion: state.mcpCatalogVersion + 1 })),
  closeModelConfig: () => set({ modelConfigOpen: false, editingModel: null }),
  openMcpConfig: (mcp = null) => set({ mcpConfigOpen: true, editingMcp: mcp }),
  closeMcpConfig: () => set({ mcpConfigOpen: false, editingMcp: null }),
}));
