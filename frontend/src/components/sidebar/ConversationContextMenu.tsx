import { Archive, Edit3, Pin, Trash2 } from 'lucide-react';
import React, { useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Thread } from '../../types/chat';

interface ConversationContextMenuProps {
  thread: Thread;
  position: { x: number; y: number };
  onClose: () => void;
  onPin: (thread: Thread) => void;
  onRename: (thread: Thread) => void;
  onArchive: (thread: Thread) => void;
  onDelete: (thread: Thread) => void;
}

export const ConversationContextMenu: React.FC<ConversationContextMenuProps> = ({
  thread,
  position,
  onClose,
  onPin,
  onRename,
  onArchive,
  onDelete,
}) => {
  const menuRef = useRef<HTMLDivElement>(null);
  const [safePosition, setSafePosition] = useState(position);

  useLayoutEffect(() => {
    const menu = menuRef.current;
    if (!menu) return;
    const bounds = menu.getBoundingClientRect();
    const left = position.x + bounds.width > window.innerWidth - 8 ? position.x - bounds.width : position.x;
    const top = position.y + bounds.height > window.innerHeight - 8 ? position.y - bounds.height : position.y;
    setSafePosition({
      x: Math.max(8, Math.min(left, window.innerWidth - bounds.width - 8)),
      y: Math.max(8, Math.min(top, window.innerHeight - bounds.height - 8)),
    });
  }, [position]);
  const menuItems = [
    {
      label: thread.is_pinned ? '取消置顶' : '置顶对话',
      icon: <Pin size={13} />,
      action: () => onPin(thread),
    },
    {
      label: '重命名',
      icon: <Edit3 size={13} />,
      action: () => onRename(thread),
    },
    {
      label: thread.is_archived ? '取消归档' : '归档会话',
      icon: <Archive size={13} />,
      action: () => onArchive(thread),
    },
    {
      label: '删除对话',
      icon: <Trash2 size={13} color="var(--accent-rose)" />,
      danger: true,
      action: () => onDelete(thread),
    },
  ];

  return createPortal(
    <>
      {}
      <div
        style={{ position: 'fixed', inset: 0, zIndex: 9998 }}
        onClick={onClose}
        onContextMenu={(e) => {
          e.preventDefault();
          onClose();
        }}
      />

      {}
      <div
        ref={menuRef}
        className="animate-fade-in"
        style={{
          position: 'fixed',
          left: safePosition.x,
          top: safePosition.y,
          zIndex: 9999,
          width: 184,
          backgroundColor: 'color-mix(in srgb, var(--accent-primary) 8%, var(--bg-surface))',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--space-1-25)',
          boxShadow: 'var(--shadow-lg)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-0-5)',
        }}
      >
        {menuItems.map((item, idx) => (
          <button
            key={idx}
            className={`conversation-context-menu-item${item.danger ? ' is-danger' : ''}`}
            onClick={() => {
              item.action();
              onClose();
            }}
            style={{
              color: item.danger ? 'var(--accent-rose)' : 'var(--text-primary)',
            }}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', flexShrink: 0 }}>{item.icon}</span>
            <span style={{ flex: 1, whiteSpace: 'nowrap' }}>{item.label}</span>
          </button>
        ))}
      </div>
    </>,
    document.body,
  );
};
