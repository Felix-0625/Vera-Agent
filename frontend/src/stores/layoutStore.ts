import { create } from 'zustand';
import { ModelConfig, McpServerConfig } from '../types/settings';
import type { Project } from '../types/project';

interface LayoutState {
  // Sidebar state
  leftCollapsed: boolean;
  leftWidth: number;
  rightCollapsed: boolean;
  rightWidth: number;
  rightMaximized: boolean;
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
  newTaskDialogOpen: boolean;
  provisionGroupOpen: boolean;
  modelConfigOpen: boolean;
  editingModel: ModelConfig | null;
  mcpConfigOpen: boolean;
  editingMcp: McpServerConfig | null;

  // Actions
  toggleLeft: () => void;
  setLeftWidth: (w: number) => void;
  toggleRight: () => void;
  setRightWidth: (w: number) => void;
  toggleRightMaximize: () => void;
  toggleBottomDrawer: () => void;
  setBottomDrawerHeight: (height: number) => void;

  openSettings: (tab?: string) => void;
  closeSettings: () => void;
  setProjectSelectorOpen: (open: boolean) => void;
  openProjectCreate: () => void;
  openProjectEdit: (project: Project) => void;
  setHistoryOpen: (open: boolean) => void;
  setScheduledTasksOpen: (open: boolean) => void;
  setNewTaskDialogOpen: (open: boolean) => void;
  setProvisionGroupOpen: (open: boolean) => void;
  openModelConfig: (model?: ModelConfig | null) => void;
  closeModelConfig: () => void;
  openMcpConfig: (mcp?: McpServerConfig | null) => void;
  closeMcpConfig: () => void;
}

export const useLayoutStore = create<LayoutState>((set) => ({
  leftCollapsed: false,
  leftWidth: 240,
  rightCollapsed: false,
  rightWidth: 560,
  rightMaximized: false,
  bottomDrawerOpen: false,
  bottomDrawerHeight: 260,

  settingsOpen: false,
  settingsTab: 'permissions',
  projectSelectorOpen: false,
  projectSelectorView: 'list',
  editingProject: null,
  historyOpen: false,
  scheduledTasksOpen: false,
  newTaskDialogOpen: false,
  provisionGroupOpen: false,
  modelConfigOpen: false,
  editingModel: null,
  mcpConfigOpen: false,
  editingMcp: null,

  toggleLeft: () => set((s) => ({ leftCollapsed: !s.leftCollapsed })),
  setLeftWidth: (w) => set({ leftWidth: w }),
  toggleRight: () => set((s) => ({ rightCollapsed: !s.rightCollapsed })),
  setRightWidth: (w) => set({ rightWidth: w }),
  toggleRightMaximize: () => set((s) => ({ rightMaximized: !s.rightMaximized })),
  toggleBottomDrawer: () => set((s) => ({ bottomDrawerOpen: !s.bottomDrawerOpen })),
  setBottomDrawerHeight: (height) => set({ bottomDrawerHeight: height }),

  openSettings: (tab = 'permissions') => set({ settingsOpen: true, settingsTab: tab }),
  closeSettings: () => set({ settingsOpen: false }),
  setProjectSelectorOpen: (open) => set({ projectSelectorOpen: open, projectSelectorView: 'list', editingProject: null }),
  openProjectCreate: () => set({ projectSelectorOpen: true, projectSelectorView: 'create', editingProject: null }),
  openProjectEdit: (project) => set({ projectSelectorOpen: true, projectSelectorView: 'edit', editingProject: project }),
  setHistoryOpen: (open) => set({ historyOpen: open }),
  setScheduledTasksOpen: (open) => set({ scheduledTasksOpen: open }),
  setNewTaskDialogOpen: (open) => set({ newTaskDialogOpen: open }),
  setProvisionGroupOpen: (open) => set({ provisionGroupOpen: open }),
  openModelConfig: (model = null) => set({ modelConfigOpen: true, editingModel: model }),
  closeModelConfig: () => set({ modelConfigOpen: false, editingModel: null }),
  openMcpConfig: (mcp = null) => set({ mcpConfigOpen: true, editingMcp: mcp }),
  closeMcpConfig: () => set({ mcpConfigOpen: false, editingMcp: null }),
}));
