import React, { useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Edit3, Pin, Trash2 } from 'lucide-react';
import { Project } from '../../types/project';

interface ProjectContextMenuProps {
  project: Project;
  position: { left: number; top: number };
  onClose: () => void;
  onPin: (project: Project) => void;
  onEdit: (project: Project) => void;
  onDelete: (project: Project) => void;
}

export const ProjectContextMenu: React.FC<ProjectContextMenuProps> = ({ project, position, onClose, onPin, onEdit, onDelete }) => {
  const menuRef = useRef<HTMLDivElement>(null);
  const [safePosition, setSafePosition] = useState(position);

  useLayoutEffect(() => {
    const bounds = menuRef.current?.getBoundingClientRect();
    if (!bounds) return;
    setSafePosition({
      left: Math.max(8, Math.min(position.left, window.innerWidth - bounds.width - 8)),
      top: Math.max(8, Math.min(position.top, window.innerHeight - bounds.height - 8)),
    });
  }, [position]);

  const items = [
    { label: project.is_pinned ? '取消置顶' : '置顶项目', icon: <Pin size={13} />, run: onPin },
    { label: '编辑', icon: <Edit3 size={13} />, run: onEdit },
    { label: '移除项目', icon: <Trash2 size={13} />, run: onDelete, danger: true },
  ];

  return createPortal(<>
    <div aria-hidden="true" onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 9998 }} />
    <div ref={menuRef} role="menu" onPointerDown={event => event.stopPropagation()} style={{ position: 'fixed', left: safePosition.left, top: safePosition.top, width: 174, padding: 5, borderRadius: 9, background: '#171b24', border: '1px solid var(--border-default)', boxShadow: '0 12px 28px rgba(0,0,0,.42)', zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 2 }}>
      {items.map(item => <button key={item.label} role="menuitem" className="composer-menu-row" style={item.danger ? { color: 'var(--accent-rose)' } : undefined} onClick={() => { item.run(project); onClose(); }}>
        {item.icon}<span>{item.label}</span>
      </button>)}
    </div>
  </>, document.body);
};
