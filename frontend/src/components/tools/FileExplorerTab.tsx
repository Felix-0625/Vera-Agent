import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronRight, File, FileCode2, FileImage, FileSpreadsheet, FileText, Folder, FolderOpen, Folders, Presentation, RefreshCw } from 'lucide-react';
import { fetchFilePreview, fetchFileTree } from '../../api/toolApi';
import { FileTreeNode } from '../../types/tool';
import { useChatStore } from '../../stores/chatStore';
import { useFilePreviewStore } from '../../stores/filePreviewStore';
import { useToolTabsStore } from '../../stores/toolTabsStore';
import { useRightSidebarLayout } from '../../stores/rightSidebarLayout';
import { IconButton } from '../common/IconButton';
import { SearchField } from '../common/Field';
import { FilePreviewPane } from './FilePreviewPane';
import { ResizableTreeLayout } from './ResizableTreeLayout';

const getFileIcon = (name: string) => {
  const ext = name.split('.').pop()?.toLowerCase();
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext || '')) return <FileImage size={14} color="var(--accent-primary)" />;
  if (['pdf'].includes(ext || '')) return <FileText size={14} color="var(--accent-rose)" />;
  if (['xlsx', 'xlsm', 'xls', 'csv'].includes(ext || '')) return <FileSpreadsheet size={14} color="var(--accent-emerald)" />;
  if (['pptx', 'ppt'].includes(ext || '')) return <Presentation size={14} color="var(--accent-amber)" />;
  if (['md', 'markdown'].includes(ext || '')) return <FileText size={14} color="var(--accent-primary)" />;
  if (['ts', 'tsx', 'js', 'jsx', 'py', 'json', 'css', 'html'].includes(ext || '')) return <FileCode2 size={14} color="var(--accent-cyan)" />;
  return <File size={14} color="var(--text-muted)" />;
};

export const FileExplorerTab: React.FC<{ projectId?: string | null }> = ({ projectId: projectIdOverride }) => {
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const threads = useChatStore((state) => state.threads);
  const draftProjectId = useChatStore((state) => state.draftProjectId);
  const projectId = projectIdOverride !== undefined ? projectIdOverride : activeThreadId ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id || null : draftProjectId;
  const projectKey = projectId || 'workspace';
  const showPreview = useFilePreviewStore((state) => state.showPreview);
  const selectedPreview = useFilePreviewStore((state) => state.previewsByProject[projectKey]);
  const selectedPath = selectedPreview?.path;
  const openFileDocumentTab = useToolTabsStore((state) => state.openFileDocumentTab);
  const { rightCollapsed, toggleRight } = useRightSidebarLayout();
  const [tree, setTree] = useState<FileTreeNode | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});
  const [loadingPath, setLoadingPath] = useState<string | null>(null);
  const [loadError, setLoadError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [hoveredPath, setHoveredPath] = useState<string | null>(null);
  const [treeCollapsed, setTreeCollapsed] = useState(false);
  const treeRequestVersion = useRef(0);
  const previewRequestVersion = useRef(0);

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
    const requestVersion = ++previewRequestVersion.current;
    setLoadingPath(node.path);
    setLoadError('');
    try {
      const preview = await fetchFilePreview(node.path, undefined, projectId || undefined);
      if (requestVersion === previewRequestVersion.current) {
        showPreview(projectKey, { path: node.path, name: node.name, preview });
      }
    } catch (error) {
      if (requestVersion === previewRequestVersion.current) {
        setLoadError(error instanceof Error ? error.message : '文件预览失败');
      }
    } finally {
      if (requestVersion === previewRequestVersion.current) setLoadingPath(null);
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
        <button onClick={() => setExpandedFolders((state) => ({ ...state, [node.path]: !isExpanded }))} onMouseEnter={() => setHoveredPath(node.path)} onMouseLeave={() => setHoveredPath(null)} title={node.path || node.name} style={{ width: '100%', minWidth: 0, height: 'var(--file-tree-row-height)', display: 'flex', alignItems: 'center', justifyContent: 'flex-start', gap: 'var(--space-2)', padding: '0 var(--space-2)', paddingLeft: 'var(--space-2)' + depth * 16, borderRadius: 'var(--radius-sm-plus)', color: 'var(--text-primary)', textAlign: 'left', background: hoveredPath === node.path ? 'var(--bg-card)' : 'transparent', cursor: 'pointer', transition: 'background 120ms ease' }}>
          <ChevronRight size={13} color="var(--text-muted)" style={{ flexShrink: 0, transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 120ms ease' }} />
          {isExpanded ? <FolderOpen size={15} color="var(--text-secondary)" /> : <Folder size={15} color="var(--text-secondary)" />}
          <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 'var(--font-size-control)' }}>{node.name}</span>
        </button>
        {isExpanded && node.children?.map((child) => renderTree(child, depth + 1))}
      </div>;
    }
    const selected = selectedPath === node.path;
    return <button key={`file:${node.path}`} onClick={() => void selectFile(node)} onMouseEnter={() => setHoveredPath(node.path)} onMouseLeave={() => setHoveredPath(null)} onDoubleClick={() => {
      void selectFile(node);
      openFileDocumentTab(node.path, node.name, projectId || undefined);
      if (rightCollapsed) toggleRight();
    }} title={`${node.name}${node.size == null ? '' : ` · ${formatFileSize(node.size)}`}\n单击预览，双击在标签页打开`} style={{ width: '100%', minWidth: 0, height: 'var(--file-tree-row-height)', display: 'flex', alignItems: 'center', justifyContent: 'flex-start', gap: 'var(--space-2)', padding: '0 var(--space-2)', paddingLeft: 28 + depth * 16, borderRadius: 'var(--radius-sm-plus)', color: 'var(--text-primary)', textAlign: 'left', background: selected || hoveredPath === node.path ? 'var(--bg-card)' : 'transparent', cursor: 'pointer', transition: 'background 120ms ease' }}>
      {getFileIcon(node.name)}
      <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 'var(--font-size-control)' }}>{node.name}</span>
      </button>;
  };

  const normalizedQuery = searchTerm.trim().toLocaleLowerCase();
  const visibleTree = tree ? filterNode(tree, normalizedQuery) : null;

  return <div style={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column', background: 'var(--bg-workspace)' }}>
    <div style={{ height: 'var(--layout-panel-header-height)', padding: '0 var(--space-3-25)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>
      <Folder size={15} color="var(--accent-primary)" />
      <strong style={{ fontSize: 'var(--font-size-control)' }}>项目文件</strong>
      <IconButton label={treeCollapsed ? '显示文件目录' : '收起文件目录'} onClick={() => setTreeCollapsed((value) => !value)} size="sm" style={{ marginLeft: 'auto' }}><Folders size={15} /></IconButton>
      <IconButton label="刷新目录" onClick={() => void loadTree()} size="sm"><RefreshCw size={14} /></IconButton>
    </div>
    <div style={{ flex: 1, minHeight: 0 }}>
      <ResizableTreeLayout collapsed={treeCollapsed} onToggle={() => setTreeCollapsed((value) => !value)} primary={<section aria-label="文件预览" style={{ minWidth: 0, minHeight: 0, height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {loadError && <div role="alert" style={{ padding: 'var(--space-2) var(--space-3)', color: 'var(--accent-rose)', fontSize: 'var(--font-size-label)', borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>{loadError}</div>}
        {projectId && selectedPreview ? <FilePreviewPane file={selectedPreview} projectKey={projectKey} projectId={projectId} embedded /> :
          <div style={{ height: '100%', display: 'grid', placeContent: 'center', gap: 'var(--space-2)', padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-muted)' }}>
            <File size={22} style={{ margin: '0 auto', opacity: 0.55 }} />
            {projectId ? <>
              <span style={{ fontSize: 'var(--font-size-sm)' }}>选择文件，在侧边栏中预览</span>
              <span style={{ fontSize: 'var(--font-size-compact)' }}>双击文件可在独立标签页中打开</span>
            </> : <span style={{ fontSize: 'var(--font-size-sm)' }}>当前对话未绑定项目，绑定项目后可预览文件</span>}
          </div>}
      </section>} secondary={<section aria-label="项目文件目录" style={{ width: '100%', height: '100%', minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: 'var(--space-2-5) var(--space-2-75) var(--space-2)', flexShrink: 0 }}>
          <SearchField aria-label="筛选文件" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="筛选文件…" />
        </div>
        <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '0 var(--space-1-75) var(--space-2)' }}>
          {!projectId ? <div style={{ padding: 'var(--space-3-5) var(--space-2-25)', color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)', lineHeight: 1.6 }}>当前对话未绑定项目<br />暂无文件目录</div> : tree ? visibleTree ? renderTree(visibleTree) : <div style={{ padding: 'var(--space-3)', color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>没有匹配的文件</div> : <div style={{ padding: 'var(--space-2-5)', color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>正在读取目录…</div>}
          {loadingPath && <div style={{ padding: 'var(--space-2) var(--space-2-5)', color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)' }}>正在预览 {loadingPath}</div>}
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
