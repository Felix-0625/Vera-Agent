import { FolderPlus } from 'lucide-react';
import React, { useState } from 'react';
import { deleteThread, updateThread } from '../../api/chatApi';
import { useChatStore } from '../../stores/chatStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';
import { Thread } from '../../types/chat';
import { ConversationContextMenu } from './ConversationContextMenu';
import { ProjectRow } from './ProjectRow';

export const ProjectTree: React.FC = () => {
  const { currentProject, projectsHistory, updateProject, deleteProject } = useProjectStore();
  const { threads, activeThreadId, selectThread, openDraftConversation, loadThreads } = useChatStore();
  const { openProjectCreate, openProjectEdit } = useLayoutStore();

  const [menuTarget, setMenuTarget] = useState<{ thread: Thread; pos: { x: number; y: number } } | null>(null);
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);

  const allProjects = React.useMemo(() => {
    const list = [...projectsHistory];
    if (currentProject && !list.some((p) => p.id === currentProject.id)) {
      list.unshift(currentProject);
    }
    return list;
  }, [projectsHistory, currentProject]);

  const handleContextMenu = (e: React.MouseEvent, thread: Thread) => {
    e.preventDefault();
    setMenuTarget({ thread, pos: { x: e.clientX, y: e.clientY } });
  };

  const handlePin = async (t: Thread) => {
    await updateThread(t.thread_id, { is_pinned: !t.is_pinned });
    loadThreads();
  };

  const handlePinProject = async (project: (typeof allProjects)[number]) => {
    await updateProject(project.id, { is_pinned: !project.is_pinned });
  };
  const handleDeleteProject = async (project: (typeof allProjects)[number]) => {
    await deleteProject(project.id);
    if (useChatStore.getState().draftProjectId === project.id) {
      useChatStore.getState().setDraftProjectId(null);
    }
  };

  const handleRename = async (t: Thread) => {
    setEditingThreadId(t.thread_id);
  };

  const saveThreadName = async (t: Thread, title: string | null) => {
    if (title) {
      await updateThread(t.thread_id, { title });
      await loadThreads();
    }
    setEditingThreadId(null);
  };

  const handleArchive = async (t: Thread) => {
    await updateThread(t.thread_id, { is_archived: !t.is_archived });
    loadThreads();
  };

  const handleDelete = async (t: Thread) => {
    if (window.confirm(`确定要删除对话 "${t.title}" 吗？`)) {
      await deleteThread(t.thread_id);
      loadThreads();
    }
  };

  return (
    <div
      style={{
        padding: 'var(--space-0-5) var(--space-3)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-3-5)',
      }}
    >
      {}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1-5)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: 'var(--space-0-5) var(--space-3)',
            fontSize: 'var(--font-size-compact)',
            fontWeight: 600,
            color: 'var(--text-muted)',
          }}
        >
          <span>项目</span>
          <button
            onClick={openProjectCreate}
            title="选择或绑定本地目录"
            style={{
              color: 'var(--accent-primary)',
              padding: 'var(--space-0-5)',
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
            }}
          >
            <FolderPlus size={14} />
          </button>
        </div>

        {allProjects
          .filter((project) => !project.is_pinned)
          .map((project) => {
            const projectThreads = threads.filter((t) => !t.is_archived && !t.is_pinned && t.project_id === project.id);

            return (
              <ProjectRow
                key={project.id}
                project={project}
                threads={projectThreads}
                activeThreadId={activeThreadId}
                onSelectThread={selectThread}
                onNewDraftInProject={(pId) => openDraftConversation(pId)}
                onContextMenu={handleContextMenu}
                onPinProject={(p) => void handlePinProject(p)}
                onEditProject={openProjectEdit}
                onDeleteProject={(p) => void handleDeleteProject(p)}
                editingThreadId={editingThreadId}
                onRenameThread={saveThreadName}
              />
            );
          })}
      </div>

      {menuTarget && (
        <ConversationContextMenu
          thread={menuTarget.thread}
          position={menuTarget.pos}
          onClose={() => setMenuTarget(null)}
          onPin={handlePin}
          onRename={handleRename}
          onArchive={handleArchive}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
};
