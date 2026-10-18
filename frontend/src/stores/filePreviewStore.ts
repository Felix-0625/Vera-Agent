/**
 * File preview pane state, keyed by project so each project keeps its own open preview.
 */
import { create } from 'zustand';
import { FilePreviewData } from '../types/tool';

export interface FilePreviewRecord {
  path: string;
  name: string;
  preview: FilePreviewData;
}

interface FilePreviewState {
  previewsByProject: Record<string, FilePreviewRecord | null>;
  showPreview: (projectKey: string, preview: FilePreviewRecord) => void;
  closePreview: (projectKey: string) => void;
}

export const useFilePreviewStore = create<FilePreviewState>((set) => ({
  previewsByProject: {},
  showPreview: (projectKey, preview) => set((state) => ({ previewsByProject: { ...state.previewsByProject, [projectKey]: preview } })),
  closePreview: (projectKey) => set((state) => ({ previewsByProject: { ...state.previewsByProject, [projectKey]: null } })),
}));
