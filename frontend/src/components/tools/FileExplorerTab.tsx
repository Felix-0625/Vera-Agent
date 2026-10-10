import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronRight, File, FileCode2, FileImage, FileSpreadsheet, FileText, Folder, FolderOpen, Folders, Presentation, RefreshCw, Search } from 'lucide-react';
import { fetchFilePreview, fetchFileTree } from '../../api/toolApi';
import { FileTreeNode } from '../../types/tool';
import { useChatStore } from '../../stores/chatStore';
import { useFilePreviewStore } from '../../stores/filePreviewStore';
import { useToolTabsStore } from '../../stores/toolTabsStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { FilePreviewPane } from './FilePreviewPane';
import { ResizableTreeLayout } from './ResizableTreeLayout';

const getFileIcon = (name: string) => {
  const ext = name.split('.').pop()?.toLowerCase();
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext || '')) return <FileImage size={14} color="#60A5FA" />;
  if (['pdf'].includes(ext || '')) return <FileText size={14} color="#FB7185" />;
  if (['xlsx', 'xlsm', 'xls', 'csv'].includes(ext || '')) return <FileSpreadsheet size={14} color="#34D399" />;
  if (['pptx', 'ppt'].includes(ext || '')) return <Presentation size={14} color="#FB923C" />;
  if (['md', 'markdown'].includes(ext || '')) return <FileText size={14} color="#A78BFA" />;
  if (['ts', 'tsx', 'js', 'jsx', 'py', 'json', 'css', 'html'].includes(ext || '')) return <FileCode2 size={14} color="var(--accent-cyan)" />;
  return <File size={14} color="var(--text-muted)" />;
};

export const FileExplorerTab: React.FC = () => {
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const threads = useChatStore((state) => state.threads);
  const draftProjectId = useChatStore((state) => state.draftProjectId);
  const projectId = activeThreadId ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id || null : draftProjectId;
  const projectKey = projectId || 'workspace';
  const showPreview = useFilePreviewStore((state) => state.showPreview);
  const selectedPreview = useFilePreviewStore((state) => state.previewsByProject[projectKey]);
  const selectedPath = selectedPreview?.path;
  const openFileDocumentTab = useToolTabsStore((state) => state.openFileDocumentTab);
  const rightCollapsed = useLayoutStore((state) => state.rightCollapsed);
  const toggleRight = useLayoutStore((state) => state.toggleRight);
  const [tree, setTree] = useState<FileTreeNode | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});
  const [loadingPath, setLoadingPath] = useState<string | null>(null);
  const [loadError, setLoadError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [hoveredPath, setHoveredPath] = useState<string | null>(null);
  const [treeCollapsed, setTreeCollapsed] = useState(false);
  const treeRequestVersion = useRef(0);

  const loadTree = useCallback(async () => {
    const requestVersion = ++treeRequestVersion.current;
    setLoadError('');
    setTree(null);
    if (!projectId) return;
    try {
      const nextTree = await fetchFileTree(undefined, projectId || undefined);
      if (requestVersion === treeRequestVersion.current) setTree(nextTree);
    } catch (error) {
      if (requestVersion === treeRequestVersion.current) setLoadError(error instanceof Error ? error.message : '目录读取失败');
    }
  }, [projectId]);
  useEffect(() => { void loadTree(); }, [loadTree]);

  const selectFile = async (node: FileTreeNode) => {
    setLoadingPath(node.path);
    setLoadError('');
    try {
      const preview = await fetchFilePreview(node.path, undefined, projectId || undefined);
      showPreview(projectKey, { path: node.path, name: node.name, preview });
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : '文件预览失败');
    } finally {
      setLoadingPath(null);
    }
  };

  const filterNode = (node: FileTreeNode, query: string): FileTreeNode | null => {
    if (!query) return node;
    const ownMatch = node.name.toLocaleLowerCase().includes(query);
    if (ownMatch) return node;
    if (!node.is_dir || !node.children) return null;
    const children = node.children.map((child) => filterNode(child, query)).filter((child): child is FileTreeNode => child !== null);
    return children.length ? { ...node, children } : null;
  };

  const renderTree = (node: FileTreeNode, depth = 0): React.ReactNode => {
    if (node.is_dir) {
      const isExpanded = searchTerm.trim() ? true : expandedFolders[node.path] ?? depth === 0;
      return <div key={`dir:${node.path}`}>
        <button onClick={() => setExpandedFolders((state) => ({ ...state, [node.path]: !isExpanded }))} onMouseEnter={() => setHoveredPath(node.path)} onMouseLeave={() => setHoveredPath(null)} title={node.path || node.name} style={{ width: '100%', minWidth: 0, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'flex-start', gap: 8, padding: '0 8px', paddingLeft: 8 + depth * 16, borderRadius: 7, color: 'var(--text-primary)', textAlign: 'left', background: hoveredPath === node.path ? 'var(--bg-card)' : 'transparent', cursor: 'pointer', transition: 'background 120ms ease' }}>
          <ChevronRight size={13} color="var(--text-muted)" style={{ flexShrink: 0, transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 120ms ease' }} />
          {isExpanded ? <FolderOpen size={15} color="#8B95A7" /> : <Folder size={15} color="#8B95A7" />}
          <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12.5 }}>{node.name}</span>
        </button>
        {isExpanded && node.children?.map((child) => renderTree(child, depth + 1))}
      </div>;
    }
    const selected = selectedPath === node.path;
    return <button key={`file:${node.path}`} onClick={() => void selectFile(node)} onMouseEnter={() => setHoveredPath(node.path)} onMouseLeave={() => setHoveredPath(null)} onDoubleClick={() => {
      void selectFile(node);
      openFileDocumentTab(node.path, node.name);
      if (rightCollapsed) toggleRight();
    }} title={`${node.name}${node.size == null ? '' : ` · ${formatFileSize(node.size)}`}\n单击预览，双击在标签页打开`} style={{ width: '100%', minWidth: 0, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'flex-start', gap: 8, padding: '0 8px', paddingLeft: 28 + depth * 16, borderRadius: 7, color: 'var(--text-primary)', textAlign: 'left', background: selected || hoveredPath === node.path ? 'var(--bg-card)' : 'transparent', cursor: 'pointer', transition: 'background 120ms ease' }}>
      {getFileIcon(node.name)}
      <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12.5 }}>{node.name}</span>
      </button>;
  };

  const normalizedQuery = searchTerm.trim().toLocaleLowerCase();
  const visibleTree = tree ? filterNode(tree, normalizedQuery) : null;

  return <div style={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column', background: 'var(--bg-workspace)' }}>
    <div style={{ height: 48, padding: '0 13px', display: 'flex', alignItems: 'center', gap: 8, borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>
      <Folder size={15} color="#60A5FA" />
      <strong style={{ fontSize: 12.5 }}>项目文件</strong>
      <button onClick={() => setTreeCollapsed((value) => !value)} title={treeCollapsed ? '显示文件目录' : '收起文件目录'} aria-label={treeCollapsed ? '显示文件目录' : '收起文件目录'} style={{ marginLeft: 'auto', display: 'flex', padding: 5, color: 'var(--text-muted)' }}><Folders size={15} /></button>
      <button onClick={() => void loadTree()} title="刷新目录" aria-label="刷新目录" style={{ display: 'flex', padding: 5, color: 'var(--text-muted)' }}><RefreshCw size={14} /></button>
    </div>
    <div style={{ flex: 1, minHeight: 0 }}>
      <ResizableTreeLayout collapsed={treeCollapsed} onToggle={() => setTreeCollapsed((value) => !value)} primary={<section aria-label="文件预览" style={{ minWidth: 0, minHeight: 0, height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {loadError && <div role="alert" style={{ padding: '8px 12px', color: 'var(--accent-rose)', fontSize: 11.5, borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>{loadError}</div>}
        {projectId && selectedPreview ? <FilePreviewPane file={selectedPreview} projectKey={projectKey} projectId={projectId} embedded /> :
          <div style={{ height: '100%', display: 'grid', placeContent: 'center', gap: 8, padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
            <File size={22} style={{ margin: '0 auto', opacity: 0.55 }} />
            {projectId ? <>
              <span style={{ fontSize: 12 }}>选择文件，在侧边栏中预览</span>
              <span style={{ fontSize: 11 }}>双击文件可在独立标签页中打开</span>
            </> : <span style={{ fontSize: 12 }}>当前对话未绑定项目，绑定项目后可预览文件</span>}
          </div>}
      </section>} secondary={<section aria-label="项目文件目录" style={{ width: '100%', height: '100%', minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '10px 11px 8px', flexShrink: 0 }}>
          <label style={{ height: 34, display: 'flex', alignItems: 'center', gap: 8, padding: '0 10px', border: '1px solid var(--border-subtle)', borderRadius: 10, background: 'var(--bg-surface)', color: 'var(--text-muted)' }}>
            <Search size={14} />
            <input aria-label="筛选文件" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="筛选文件…" style={{ width: '100%', minWidth: 0, border: 0, outline: 0, background: 'transparent', color: 'var(--text-primary)', fontSize: 12 }} />
          </label>
        </div>
        <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '0 7px 8px' }}>
          {!projectId ? <div style={{ padding: '14px 9px', color: 'var(--text-muted)', fontSize: 12, lineHeight: 1.6 }}>当前对话未绑定项目<br />暂无文件目录</div> : tree ? visibleTree ? renderTree(visibleTree) : <div style={{ padding: 12, color: 'var(--text-muted)', fontSize: 12 }}>没有匹配的文件</div> : <div style={{ padding: 10, color: 'var(--text-muted)', fontSize: 12 }}>正在读取目录…</div>}
          {loadingPath && <div style={{ padding: '8px 10px', color: 'var(--text-muted)', fontSize: 11 }}>正在预览 {loadingPath}</div>}
        </div>
      </section>} />
    </div>
  </div>;
};

function formatFileSize(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}
