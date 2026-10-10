import React from 'react';
import { Pin, MoreVertical } from 'lucide-react';
import { Thread } from '../../types/chat';

interface ThreadRowProps {
  thread: Thread;
  isActive: boolean;
  onSelect: () => void;
  onContextMenu: (e: React.MouseEvent) => void;
}

/**
 * 侧边栏单个对话项组件
 * 严格按照用户需求与 Penpot 原型：对话前面没有任何图标，仅展示标题与右侧操作
 */
export const ThreadRow: React.FC<ThreadRowProps> = ({
  thread,
  isActive,
  onSelect,
  onContextMenu,
}) => {
  return (
    <div
      onClick={onSelect}
      onContextMenu={onContextMenu}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '5px 10px',
        paddingLeft: 24, // 相对项目行进行层级缩进
        borderRadius: 'var(--radius-sm)',
        backgroundColor: isActive ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
        cursor: 'pointer',
        fontSize: 12.5,
        color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
        position: 'relative',
        transition: 'background-color 0.1s ease',
      }}
      onMouseEnter={(e) => {
        if (!isActive) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
      }}
      onMouseLeave={(e) => {
        if (!isActive) e.currentTarget.style.backgroundColor = 'transparent';
      }}
    >
      {/* 对话前面完全去除图标，只保留标题文字 */}
      <span
        style={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          flex: 1,
          marginRight: 6,
        }}
      >
        {thread.title || '对话'}
      </span>

      {/* 右侧置顶状态与三点更多菜单 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
        {thread.is_pinned && <Pin size={11} color="var(--accent-amber)" />}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onContextMenu(e);
          }}
          style={{
            padding: 3,
            color: 'var(--text-muted)',
            borderRadius: 3,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          title="操作菜单"
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
        >
          <MoreVertical size={13} />
        </button>
      </div>
    </div>
  );
};
