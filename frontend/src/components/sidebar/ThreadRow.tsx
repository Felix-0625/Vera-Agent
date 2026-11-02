import { MoreVertical, Pin } from 'lucide-react';
import React from 'react';
import { Thread } from '../../types/chat';
import { IconButton } from '../common/IconButton';

interface ThreadRowProps {
  thread: Thread;
  isActive: boolean;
  onSelect: () => void;
  onContextMenu: (e: React.MouseEvent) => void;
}

/** A conversation row with a consistent active state and accessible menu action. */
export const ThreadRow: React.FC<ThreadRowProps> = ({ thread, isActive, onSelect, onContextMenu }) => (
  <div
    className={`sidebar-thread-row${isActive ? ' is-active' : ''}`}
    onClick={onSelect}
    onContextMenu={onContextMenu}
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: 'var(--space-1-25) var(--space-2-5)',
      paddingLeft: 'var(--space-6)',
      borderRadius: 'var(--radius-sm)',
      cursor: 'pointer',
      fontSize: 'var(--font-size-control)',
      color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
      position: 'relative',
    }}
  >
    <span
      style={{
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        flex: 1,
        marginRight: 'var(--space-1-5)',
      }}
    >
      {thread.title || '对话'}
    </span>
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', flexShrink: 0 }}>
      {thread.is_pinned && <Pin size={11} color="var(--accent-amber)" />}
      <IconButton
        onClick={(event) => {
          event.stopPropagation();
          onContextMenu(event);
        }}
        label={`${thread.title || '对话'} 操作菜单`}
        size="sm"
      >
        <MoreVertical size={13} />
      </IconButton>
    </div>
  </div>
);
