import React, { useMemo, useState } from 'react';
import { CheckSquare, ChevronDown, ChevronRight, File, Folder, Undo2 } from 'lucide-react';
import { WorktreeDiffData } from '../../types/tool';

type TreeNode = { name: string; path: string; children: Map<string, TreeNode>; file?: { status: string; staged: boolean; untracked: boolean; additions: number; deletions: number } };

interface DiffFileListProps {
  data: WorktreeDiffData | null;
  selectedFile: string | null;
  onSelect: (file: string) => void;
  onStage: (file: string) => Promise<void>;
  onDiscard: (file: string) => Promise<void>;
}

export const DiffFileList: React.FC<DiffFileListProps> = ({ data, selectedFile, onSelect, onStage, onDiscard }) => {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const root = useMemo(() => {
    const node: TreeNode = { name: '', path: '', children: new Map() };
    if (!data) return node;
    const entries = new Map<string, TreeNode['file']>();
    data.staged.forEach((item) => entries.set(item.file, { status: item.status, staged: true, untracked: false, additions: item.additions || 0, deletions: item.deletions || 0 }));
    data.unstaged.forEach((item) => {
      const previous = entries.get(item.file);
      entries.set(item.file, { status: item.status, staged: previous?.staged ?? false, untracked: false, additions: item.additions || previous?.additions || 0, deletions: item.deletions || previous?.deletions || 0 });
    });
    data.untracked.forEach((file) => {
      const previous = entries.get(file);
      entries.set(file, { status: '?', staged: false, untracked: true, additions: previous?.additions || 0, deletions: previous?.deletions || 0 });
    });
    for (const [path, file] of entries) {
      const parts = path.replaceAll('\\', '/').split('/').filter(Boolean);
      let current = node;
      parts.forEach((part, index) => {
        const nextPath = parts.slice(0, index + 1).join('/');
        if (!current.children.has(part)) current.children.set(part, { name: part, path: nextPath, children: new Map() });
        current = current.children.get(part)!;
        if (index === parts.length - 1) current.file = file;
      });
    }
    return node;
  }, [data]);

  const renderNodes = (parent: TreeNode, depth: number): React.ReactNode => [...parent.children.values()]
    .sort((a, b) => Number(Boolean(b.children.size)) - Number(Boolean(a.children.size)) || a.name.localeCompare(b.name))
    .map((node) => {
      const directory = node.children.size > 0;
      const isCollapsed = collapsed.has(node.path);
      const active = selectedFile === node.path;
      return <React.Fragment key={node.path}>
        <div style={{ display: 'flex', alignItems: 'center', minHeight: 30, padding: '0 5px', paddingLeft: 7 + depth * 15, borderRadius: 6, background: active ? 'var(--bg-surface-elevated)' : 'transparent' }}>
          <button onClick={() => directory ? setCollapsed((prev) => { const next = new Set(prev); if (next.has(node.path)) next.delete(node.path); else next.add(node.path); return next; }) : onSelect(node.path)} title={node.path} style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-start', gap: 6, minWidth: 0, flex: 1, textAlign: 'left', color: node.file?.untracked ? 'var(--accent-emerald)' : node.file?.staged ? 'var(--accent-emerald)' : node.file ? 'var(--accent-amber)' : 'var(--text-secondary)', fontSize: 12 }}>
            {directory ? (isCollapsed ? <ChevronRight size={13} /> : <ChevronDown size={13} />) : <span style={{ width: 13 }} />}
            {directory ? <Folder size={14} /> : <File size={14} />}
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{node.name}</span>
          </button>
          {node.file && <div style={{ marginLeft: 5, display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0, fontFamily: 'ui-monospace, monospace', fontSize: 10.5 }}>
            {!node.file.staged && <button onClick={() => onStage(node.path)} title="暂存" style={{ padding: 2, color: 'var(--text-muted)' }}><CheckSquare size={12} /></button>}
            {!node.file.untracked && <button onClick={() => onDiscard(node.path)} title="撤销修改" style={{ padding: 2, color: 'var(--text-muted)' }}><Undo2 size={12} /></button>}
            {(node.file.additions ?? 0) > 0 && <span style={{ marginLeft: 3, color: 'var(--accent-emerald)' }}>+{node.file.additions}</span>}
            {(node.file.deletions ?? 0) > 0 && <span style={{ color: 'var(--accent-rose)' }}>-{node.file.deletions}</span>}
          </div>}
        </div>
        {directory && !isCollapsed && renderNodes(node, depth + 1)}
      </React.Fragment>;
    });

  return <aside style={{ width: '100%', height: '100%', minWidth: 0, overflowY: 'auto', padding: 8, fontSize: 12 }}>
    <div style={{ fontWeight: 600, color: 'var(--text-muted)', padding: '3px 6px 8px' }}>变更文件</div>
    {root.children.size ? renderNodes(root, 0) : <div style={{ padding: 6, color: 'var(--text-disabled)' }}>当前没有变更文件</div>}
  </aside>;
};
