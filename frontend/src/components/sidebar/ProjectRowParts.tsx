import React from 'react';
import { Thread } from '../../types/chat';
import { Project } from '../../types/project';
export interface ProjectRowProps {
  project: Project;
  threads: Thread[];
  activeThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onNewDraftInProject: (projectId: string) => void;
  onContextMenu: (e: React.MouseEvent, thread: Thread) => void;
  onPinProject: (project: Project) => void;
  onEditProject: (project: Project) => void;
  onDeleteProject: (project: Project) => void;
  editingThreadId?: string | null;
  onRenameThread?: (thread: Thread, title: string | null) => Promise<void>;
}
