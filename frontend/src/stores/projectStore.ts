import { create } from 'zustand';
import { Project, Group } from '../types/project';
import {
  fetchProjects,
  fetchCurrentProject,
  bindProjectFolder,
  deleteProjectHistory,
  fetchGroups,
  updateProject,
} from '../api/projectApi';

interface ProjectState {
  currentProject: Project | null;
  projectsHistory: Project[];
  groups: Group[];
  activeGroupId: string | null;
  loading: boolean;

  loadCurrentProject: () => Promise<void>;
  loadProjectsHistory: () => Promise<void>;
  bindProject: (path: string, options?: { projectId?: string; name?: string; folders?: string[] }) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  updateProject: (id: string, data: { name?: string; folders?: string[]; is_pinned?: boolean }) => Promise<void>;
  loadGroups: () => Promise<void>;
  setActiveGroupId: (id: string | null) => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  currentProject: null,
  projectsHistory: [],
  groups: [],
  activeGroupId: null,
  loading: false,

  loadCurrentProject: async () => {
    try {
      const proj = await fetchCurrentProject();
      set({ currentProject: proj });
    } catch {
      // fallback
    }
  },

  loadProjectsHistory: async () => {
    try {
      const data = await fetchProjects();
      set({ projectsHistory: data.projects || [] });
    } catch {
      // fallback
    }
  },

  bindProject: async (path: string, options = {}) => {
    set({ loading: true });
    try {
      const proj = await bindProjectFolder(path, options);
      set({ currentProject: { ...proj, path: proj.repo_root || path } });
      await get().loadProjectsHistory();
      await get().loadGroups();
    } finally {
      set({ loading: false });
    }
  },

  deleteProject: async (id: string) => {
    const removed = get().projectsHistory.find(project => project.id === id);
    const current = get().currentProject;
    await deleteProjectHistory(id);
    if (current?.id === id || (removed && current?.repo_root === removed.path)) set({ currentProject: null });
    await get().loadProjectsHistory();
  },

  updateProject: async (id, data) => {
    await updateProject(id, data);
    await get().loadProjectsHistory();
    await get().loadCurrentProject();
  },

  loadGroups: async () => {
    try {
      const data = await fetchGroups();
      set({ groups: data.groups || [] });
    } catch {
      // fallback
    }
  },

  setActiveGroupId: (id) => set({ activeGroupId: id }),
}));
