import { MoreVertical, Pin } from 'lucide-react';
import React, { useState } from 'react';
import { deleteThread, updateThread } from '../../api/chatApi';
import { useChatStore } from '../../stores/chatStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';
import { Thread } from '../../types/chat';
import { IconButton } from '../common/IconButton';
import { ConversationContextMenu } from './ConversationContextMenu';
import { InlineThreadRename } from './InlineThreadRename';
import { ProjectRow } from './ProjectRow';

export const PinnedItems: React.FC = () => {
  const { projectsHistory, updateProject: saveProject, deleteProject } = useProjectStore();
  const { threads, activeThreadId, selectThread, openDraftConversation, loadThreads } = useChatStore();
  const [menuTarget, setMenuTarget] = useState<{ thread: Thread; pos: { x: number; y: number } } | null>(null);
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const { openProjectEdit } = useLayoutStore();
  const pinnedProjects = projectsHistory.filter((project) => project.is_pinned);
  const pinnedProjectIds = new Set(pinnedProjects.map((project) => project.id));
  const pinnedThreads = threads.filter(
    (thread) =>
      thread.is_pinned && !thread.is_archived && !(thread.project_id && pinnedProjectIds.has(thread.project_id)),
  );
  if (!pinnedProjects.length && !pinnedThreads.length) return null;

  const openMenu = (event: React.MouseEvent, thread: Thread) => {
    event.preventDefault();
    event.stopPropagation();
    setMenuTarget({ thread, pos: { x: event.clientX, y: event.clientY } });
  };
  const handlePin = async (thread: Thread) => {
    await updateThread(thread.thread_id, { is_pinned: !thread.is_pinned });
    await loadThreads();
  };
  const handleRename = async (thread: Thread) => {
    setEditingThreadId(thread.thread_id);
  };
  const saveThreadName = async (thread: Thread, title: string | null) => {
    if (title) {
      await updateThread(thread.thread_id, { title });
      await loadThreads();
    }
    setEditingThreadId(null);
  };
  const handleArchive = async (thread: Thread) => {
    await updateThread(thread.thread_id, { is_archived: !thread.is_archived });
    await loadThreads();
  };
  const handleDelete = async (thread: Thread) => {
    if (window.confirm(`确定要删除对话 "${thread.title}" 吗？`)) {
      await deleteThread(thread.thread_id);
      await loadThreads();
    }
  };
  const togglePin = async (project: (typeof pinnedProjects)[number]) => {
    await saveProject(project.id, { is_pinned: !project.is_pinned });
  };

  return (
    <section
      style={{ padding: '0 var(--space-3)', display: 'flex', flexDirection: 'column', gap: 'var(--space-0-75)' }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: 'var(--space-0-5) var(--space-3)',
          fontSize: 'var(--font-size-compact)',
          fontWeight: 650,
          color: 'var(--text-muted)',
        }}
      >
        置顶
      </div>
      {pinnedProjects.map((project) => (
        <ProjectRow
          key={project.id}
          project={project}
          threads={threads.filter((thread) => !thread.is_archived && thread.project_id === project.id)}
          activeThreadId={activeThreadId}
          onSelectThread={(id) => void selectThread(id)}
          onNewDraftInProject={(id) => openDraftConversation(id)}
          onContextMenu={openMenu}
          onPinProject={togglePin}
          onEditProject={openProjectEdit}
          onDeleteProject={(item) => void deleteProject(item.id)}
          editingThreadId={editingThreadId}
          onRenameThread={saveThreadName}
        />
      ))}
      {pinnedThreads.map((thread) => (
        <div
          key={thread.thread_id}
          className={`sidebar-thread-row sidebar-pinned-thread${activeThreadId === thread.thread_id ? ' is-active' : ''}`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-1-5)',
            minWidth: 0,
            padding: 'var(--space-1-5) var(--space-2-25)',
            borderRadius: 'var(--radius-md)',
            color: activeThreadId === thread.thread_id ? 'var(--text-primary)' : 'var(--text-secondary)',
            fontSize: 'var(--font-size-sm)',
            cursor: 'pointer',
          }}
          onClick={() => {
            if (editingThreadId !== thread.thread_id) void selectThread(thread.thread_id);
          }}
          onContextMenu={(event) => openMenu(event, thread)}
        >
          <Pin size={12} color="var(--accent-amber)" />
          {editingThreadId === thread.thread_id ? (
            <InlineThreadRename
              title={thread.title || '对话'}
              onSave={(title) => saveThreadName(thread, title)}
              onCancel={() => saveThreadName(thread, null)}
            />
          ) : (
            <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {thread.title || '对话'}
            </span>
          )}
          <IconButton
            label={`${thread.title || '置顶对话'} 操作菜单`}
            size="sm"
            onClick={(event) => {
              event.stopPropagation();
              openMenu(event, thread);
            }}
          >
            <MoreVertical size={13} />
          </IconButton>
        </div>
      ))}
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
    </section>
  );
};
