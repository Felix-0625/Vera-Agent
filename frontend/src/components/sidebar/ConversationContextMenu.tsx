import React, { useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Pin, Trash2, Edit3, Archive } from 'lucide-react';
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

/**
 * 对话右侧三个点弹出的完整操作菜单
 * 确保图标与中文文本完整清晰可见，防止任何截断
 */
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

  return createPortal((
    <>
      {/* 全屏透明遮罩用于点击外部关闭 */}
      <div
        style={{ position: 'fixed', inset: 0, zIndex: 9998 }}
        onClick={onClose}
        onContextMenu={(e) => {
          e.preventDefault();
          onClose();
        }}
      />

      {/* 浮动菜单实体 */}
      <div
        ref={menuRef}
        className="animate-fade-in"
        style={{
          position: 'fixed',
          left: safePosition.x,
          top: safePosition.y,
          zIndex: 9999,
          width: 184,
          backgroundColor: '#161720',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: 8,
          padding: 5,
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.65)',
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        {menuItems.map((item, idx) => (
          <button
            key={idx}
            onClick={() => {
              item.action();
              onClose();
            }}
            style={{
              width: '100%',
          padding: '8px 10px',
              borderRadius: 5,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 12,
              color: item.danger ? 'var(--accent-rose)' : 'var(--text-primary)',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              textAlign: 'left',
              whiteSpace: 'nowrap',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = item.danger
                ? 'rgba(239, 68, 68, 0.18)'
                : 'rgba(255, 255, 255, 0.08)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', flexShrink: 0 }}>
              {item.icon}
            </span>
            <span style={{ flex: 1, whiteSpace: 'nowrap' }}>{item.label}</span>
          </button>
        ))}
      </div>
    </>
  ), document.body);
};
