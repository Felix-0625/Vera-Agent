import { MoreVertical } from 'lucide-react';
import React, { useState } from 'react';
import { deleteThread, updateThread } from '../../api/chatApi';
import { useChatStore } from '../../stores/chatStore';
import { Thread } from '../../types/chat';
import { IconButton } from '../common/IconButton';
import { ConversationContextMenu } from './ConversationContextMenu';
import { InlineThreadRename } from './InlineThreadRename';

export const RecentConversations: React.FC = () => {
  const { threads, activeThreadId, selectThread, loadThreads } = useChatStore();
  const [menuTarget, setMenuTarget] = useState<{ thread: Thread; pos: { x: number; y: number } } | null>(null);
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const recent = threads.filter((thread) => !thread.is_archived && !thread.project_id && !thread.is_pinned).slice(0, 6);

  const openMenu = (event: React.MouseEvent, thread: Thread) => {
    event.preventDefault();
    event.stopPropagation();
    setMenuTarget({ thread, pos: { x: event.clientX, y: event.clientY } });
  };
  const pin = async (thread: Thread) => {
    await updateThread(thread.thread_id, { is_pinned: !thread.is_pinned });
    await loadThreads();
  };
  const rename = async (thread: Thread) => {
    setEditingThreadId(thread.thread_id);
  };
  const saveThreadName = async (thread: Thread, title: string | null) => {
    if (title) {
      await updateThread(thread.thread_id, { title });
      await loadThreads();
    }
    setEditingThreadId(null);
  };
  const archive = async (thread: Thread) => {
    await updateThread(thread.thread_id, { is_archived: !thread.is_archived });
    await loadThreads();
  };
  const remove = async (thread: Thread) => {
    if (window.confirm(`确定要删除对话 "${thread.title}" 吗？`)) {
      await deleteThread(thread.thread_id);
      await loadThreads();
    }
  };

  return (
    <section
      style={{
        padding: '0 var(--space-3) var(--space-2-5)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-0-75)',
      }}
    >
      <div
        style={{
          padding: 'var(--space-0-5) var(--space-3)',
          fontSize: 'var(--font-size-compact)',
          fontWeight: 600,
          color: 'var(--text-muted)',
        }}
      >
        最近会话
      </div>
      {!recent.length ? (
        <div
          style={{
            padding: 'var(--space-1) var(--space-3)',
            fontSize: 'var(--font-size-sm)',
            color: 'var(--text-disabled)',
          }}
        >
          暂无对话
        </div>
      ) : (
        recent.map((thread) => {
          const active = activeThreadId === thread.thread_id;
          return (
            <div
              key={thread.thread_id}
              className={`sidebar-thread-row${active ? ' is-active' : ''}`}
              onClick={() => {
                if (editingThreadId !== thread.thread_id) void selectThread(thread.thread_id);
              }}
              onContextMenu={(event) => openMenu(event, thread)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-1-5)',
                minWidth: 0,
                padding: 'var(--space-1-25) var(--space-2) var(--space-1-25) var(--space-3)',
                borderRadius: 'var(--radius-sm)',
                color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontSize: 'var(--font-size-sm)',
                cursor: 'pointer',
              }}
            >
              {editingThreadId === thread.thread_id ? (
                <InlineThreadRename
                  title={thread.title || '对话'}
                  onSave={(title) => saveThreadName(thread, title)}
                  onCancel={() => saveThreadName(thread, null)}
                />
              ) : (
                <span
                  style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                >
                  {thread.title || '对话'}
                </span>
              )}
              <IconButton
                label={`${thread.title || '对话'} 操作菜单`}
                size="sm"
                onClick={(event) => {
                  event.stopPropagation();
                  openMenu(event, thread);
                }}
              >
                <MoreVertical size={13} />
              </IconButton>
            </div>
          );
        })
      )}
      {menuTarget && (
        <ConversationContextMenu
          thread={menuTarget.thread}
          position={menuTarget.pos}
          onClose={() => setMenuTarget(null)}
          onPin={pin}
          onRename={rename}
          onArchive={archive}
          onDelete={remove}
        />
      )}
    </section>
  );
};
