import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Background, BackgroundVariant, Edge, Handle, MarkerType, Node, Position, ReactFlow,
  ReactFlowProvider, useNodesInitialized, useNodesState, useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import './gitflow.css';
import { ArrowLeft, GitBranch, GitCommitHorizontal, GitMerge, Plus, RefreshCw, Trash2, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { createBranch, deleteBranch, fetchGitFlowTopology, mergeBranch, requestMergeReview, checkoutBranch } from '../../api/toolApi';
import { BranchInfo, GitCommitInfo, GitFlowTopology } from '../../types/tool';
import { useChatStore } from '../../stores/chatStore';
import { TextInput } from '../common/Field';
import { EmptyState } from '../common/EmptyState';
import { Button } from '../common/Button';
import { IconButton } from '../common/IconButton';

type BranchNodeData = { branch: BranchInfo; onSelect: (branch: BranchInfo) => void; onOpen: (branch: BranchInfo) => void };
type FlowNode = Node<BranchNodeData>;
const branchColor = (name: string) => name === 'main' || name === 'master' ? 'var(--accent-primary)' : name === 'develop' || name === 'development' ? 'var(--accent-cyan)' : name.startsWith('feature/') || name.startsWith('feat/') ? 'var(--accent-emerald)' : name.startsWith('release/') ? 'var(--accent-amber)' : name.startsWith('hotfix/') ? 'var(--accent-rose)' : 'var(--text-muted)';

const BranchNode: React.FC<{ data: BranchNodeData; selected?: boolean }> = ({ data, selected }) => {
  const branch = data.branch;
  const color = branchColor(branch.name);
  return <div className={`gitflow-branch-node${selected ? ' is-selected' : ''}`} style={{ '--branch-color': color } as React.CSSProperties}>
    <Handle id="top" type="target" position={Position.Top} className="gitflow-handle" />
    <button className="gitflow-branch-card" title={`${branch.name} · 单击查看提交，双击查看操作`} onClick={(event) => { event.stopPropagation(); data.onSelect(branch); }} onDoubleClick={(event) => { event.stopPropagation(); data.onOpen(branch); }}>
      <GitBranch size={14} /><span>{branch.name}</span>{branch.is_current && <i>当前</i>}
    </button>
    <Handle id="bottom" type="source" position={Position.Bottom} className="gitflow-handle" />
  </div>;
};
const nodeTypes = { branch: BranchNode };

function buildGraph(topology: GitFlowTopology, onSelect: (branch: BranchInfo) => void, onOpen: (branch: BranchInfo) => void, saved: Record<string, { x: number; y: number }> = {}) {
  const branches = topology.branches.filter((branch) => !branch.is_remote);
  const byName = new Map(branches.map((branch) => [branch.name, branch]));
  const commitByHash = new Map(topology.commits.map((commit) => [commit.hash, commit]));
  const ancestorCache = new Map<string, Set<string>>();
  const ancestors = (head?: string): Set<string> => {
    if (!head) return new Set();
    const known = ancestorCache.get(head);
    if (known) return known;
    const found = new Set<string>();
    const pending = [head];
    while (pending.length) {
      const hash = pending.pop()!;
      if (found.has(hash)) continue;
      found.add(hash);
      pending.push(...(commitByHash.get(hash)?.parents || []));
    }
    ancestorCache.set(head, found);
    return found;
  };
  const roots = branches.filter((branch) => branch.name === 'main' || branch.name === 'master');
  const parentOf = (branch: BranchInfo): string | undefined => {
    if (branch.parent && byName.has(branch.parent)) return branch.parent;
    const lower = branch.name.toLowerCase();
    const candidates = lower === 'develop' || lower === 'development'
      ? roots
      : /^(feature|feat|bugfix|fix|release)\//.test(lower)
        ? branches.filter((candidate) => /^(develop|development)$/i.test(candidate.name))
        : lower.startsWith('hotfix/') ? roots : [];
    const childAncestors = ancestors(branch.head);
    return candidates.find((parent) => parent.name !== branch.name && [...childAncestors].some((hash) => ancestors(parent.head).has(hash)))?.name;
  };
  const parentByName = new Map(branches.map((branch) => [branch.name, parentOf(branch)]));
  const children = new Map<string, BranchInfo[]>();
  branches.forEach((branch) => {
    const parent = parentByName.get(branch.name);
    if (parent && byName.has(parent)) children.set(parent, [...(children.get(parent) || []), branch]);
  });
  const treeRoots = branches.filter((branch) => !parentByName.get(branch.name) || !byName.has(parentByName.get(branch.name)!)).sort((a, b) => Number(b.is_current) - Number(a.is_current) || a.name.localeCompare(b.name));
  const positions: Record<string, { x: number; y: number }> = {};
  let nextLeafX = 0;
  const place = (branch: BranchInfo, y: number): number => {
    const childList = (children.get(branch.name) || []).sort((a, b) => a.name.localeCompare(b.name));
    if (childList.length === 0) {
      const x = nextLeafX;
      nextLeafX += 250;
      positions[branch.name] = { x, y };
      return x;
    }
    const childXs = childList.map((child) => place(child, y + 116));
    const x = (childXs[0] + childXs[childXs.length - 1]) / 2;
    positions[branch.name] = { x, y };
    return x;
  };
  treeRoots.forEach((root) => { place(root, 24); });
  const nodes: FlowNode[] = branches.map((branch) => ({
    id: branch.name, type: 'branch', position: saved[branch.name] || positions[branch.name] || { x: 0, y: 24 },
    data: { branch, onSelect, onOpen }, draggable: true,
    selected: branch.name === topology.current_branch,
  }));
  const edges: Edge[] = branches.filter((branch) => parentByName.get(branch.name) && byName.has(parentByName.get(branch.name)!)).map((branch) => ({
    id: `${parentByName.get(branch.name)}->${branch.name}`, source: parentByName.get(branch.name)!, target: branch.name,
    type: 'smoothstep', sourceHandle: 'bottom', targetHandle: 'top', markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--text-muted)' },
    style: { stroke: 'var(--text-muted)', strokeWidth: 1.5 },
  }));
  return { nodes, edges };
}

const GraphCanvas: React.FC<{ topology: GitFlowTopology; layoutScope: string; selectedBranch: BranchInfo | null; onSelectBranch: (branch: BranchInfo) => void; onOpenBranch: (branch: BranchInfo) => void }> = ({ topology, layoutScope, selectedBranch, onSelectBranch, onOpenBranch }) => {
  const flow = useReactFlow<FlowNode>();
  const [zoom, setZoom] = useState(1);
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>([]);
  const nodesInitialized = useNodesInitialized();
  const layoutKey = `veraagent:gitflow-layout:v3:${layoutScope}`;
  const graph = useMemo(() => {
    let saved: Record<string, { x: number; y: number }> = {};
    try { saved = JSON.parse(localStorage.getItem(layoutKey) || '{}'); } catch { /* Ignore invalid saved layout. */ }
    return buildGraph(topology, onSelectBranch, onOpenBranch, saved);
  }, [topology, onSelectBranch, onOpenBranch, layoutKey]);
  useEffect(() => {
    setNodes((current) => graph.nodes.map((node) => {
      const existing = current.find((item) => item.id === node.id);
      return { ...node, position: existing?.position || node.position, selected: node.id === selectedBranch?.name };
    }));
  }, [graph, selectedBranch, setNodes]);
  useEffect(() => {
    if (!nodesInitialized) return;
    const frame = requestAnimationFrame(() => flow.fitView({ duration: 180, padding: 0.18, maxZoom: 1 }));
    return () => cancelAnimationFrame(frame);
  }, [flow, nodesInitialized, layoutScope, topology.branches.length]);
  const savePositions = useCallback(() => {
    const positions = Object.fromEntries(flow.getNodes().map((node) => [node.id, node.position]));
    localStorage.setItem(layoutKey, JSON.stringify(positions));
  }, [flow, layoutKey]);
  const selectNode = useCallback((_: React.MouseEvent, node: FlowNode) => onSelectBranch(node.data.branch), [onSelectBranch]);
  const openNode = useCallback((_: React.MouseEvent, node: FlowNode) => onOpenBranch(node.data.branch), [onOpenBranch]);
  return <div className="gitflow-canvas-wrap">
    <ReactFlow className="gitflow-canvas" nodes={nodes} edges={graph.edges} onNodesChange={onNodesChange} nodeTypes={nodeTypes} defaultViewport={{ x: 0, y: 0, zoom: 0.8 }} onMove={(_, viewport) => setZoom(viewport.zoom)} onNodeDragStop={savePositions} onNodeClick={selectNode} onNodeDoubleClick={openNode} minZoom={0.35} maxZoom={1.8} panOnScroll zoomOnScroll={false} zoomOnPinch zoomOnDoubleClick={false} nodesDraggable nodesConnectable={false} elementsSelectable proOptions={{ hideAttribution: true }}>
      <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="var(--text-primary)" />
    </ReactFlow>
    <div className="gitflow-zoom-controls">
      <IconButton label="缩小" size="sm" onClick={() => flow.zoomOut({ duration: 180 })}><ZoomOut size={14} /></IconButton><span>{Math.round(zoom * 100)}%</span><IconButton label="放大" size="sm" onClick={() => flow.zoomIn({ duration: 180 })}><ZoomIn size={14} /></IconButton><IconButton label="适应视图" size="sm" onClick={() => flow.fitView({ duration: 250, padding: 0.12 })}><Maximize2 size={13} /></IconButton>
    </div>
  </div>;
};

function branchCommits(branch: BranchInfo, commits: GitCommitInfo[]): GitCommitInfo[] {
  if (!branch.head) return [];
  const byHash = new Map(commits.map((commit) => [commit.hash, commit]));
  const visited = new Set<string>();
  const stack = [branch.head];
  while (stack.length) {
    const hash = stack.pop()!;
    if (visited.has(hash)) continue;
    visited.add(hash);
    const commit = byHash.get(hash);
    if (commit) stack.push(...commit.parents);
  }
  return commits.filter((commit) => visited.has(commit.hash));
}

const CommitEntry: React.FC<{ commit: GitCommitInfo; compact?: boolean }> = ({ commit, compact }) => {
  const mergeCommit = commit.parents.length > 1;
  const parentLabel = commit.parents.map((parent) => parent.slice(0, 8)).join(' · ');
  return <div className={`gitflow-commit-row${mergeCommit ? ' is-merge' : ''}`} key={commit.hash}>
    <code>{commit.short_hash}</code>
    <div className="gitflow-commit-content"><span title={commit.subject}>{commit.subject || '（无提交说明）'}</span>{mergeCommit && <small>合并提交 · 父提交 {parentLabel}</small>}</div>
    {mergeCommit && <i className="gitflow-merge-badge">合并</i>}
    <time>{new Date(commit.timestamp * 1000).toLocaleString(undefined, compact ? { dateStyle: 'short' } : undefined)}</time>
  </div>;
};

const modalBackdrop: React.CSSProperties = { position: 'fixed', inset: 0, zIndex: 30, display: 'grid', placeItems: 'center', background: 'var(--overlay-scrim)' };
const modal: React.CSSProperties = { width: 'min(620px, calc(100vw - 32px))', maxHeight: 'min(760px, calc(100vh - 32px))', display: 'flex', flexDirection: 'column', gap: 'var(--space-3-5)', padding: 'var(--space-5)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-lg-plus)', background: 'var(--bg-surface-elevated)', boxShadow: 'var(--shadow-lg)', overflow: 'auto' };

export const GitFlowTab: React.FC<{ projectId?: string | null }> = ({ projectId: projectIdOverride }) => {
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const threads = useChatStore((state) => state.threads);
  const draftProjectId = useChatStore((state) => state.draftProjectId);
  const projectId = projectIdOverride !== undefined ? projectIdOverride || undefined : activeThreadId ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id || undefined : draftProjectId || undefined;
  const [topology, setTopology] = useState<GitFlowTopology | null>(null);
  const [selectedBranch, setSelectedBranch] = useState<BranchInfo | null>(null);
  const [detailBranch, setDetailBranch] = useState<BranchInfo | null>(null);
  const [reviewResult, setReviewResult] = useState<{ has_conflict: boolean; summary: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [branchName, setBranchName] = useState('');
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState<'local' | 'remote'>('local');

  const loadData = useCallback(async () => {
    if (!projectId) { setTopology(null); return; }
    setLoading(true); setError('');
    try {
      const result = await fetchGitFlowTopology(projectId);
      setTopology(result);
      setSelectedBranch((current) => current ? result.branches.find((branch) => branch.name === current.name) || result.branches.find((branch) => branch.is_current) || null : result.branches.find((branch) => branch.is_current) || null);
      setDetailBranch((current) => current ? result.branches.find((branch) => branch.name === current.name) || null : null);
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setLoading(false); }
  }, [projectId]);
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- Refresh Git topology when the conversation's project changes.
    void loadData();
  }, [loadData]);

  const runAction = async (action: () => Promise<unknown>) => {
    setBusy(true);
    try { await action(); await loadData(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setBusy(false); }
  };
  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!branchName.trim() || !projectId) return;
    await runAction(() => createBranch(branchName.trim(), topology?.current_branch || 'HEAD', projectId));
    setBranchName(''); setShowCreate(false);
  };
  const selectBranch = useCallback((branch: BranchInfo) => { setSelectedBranch(branch); setReviewResult(null); }, []);
  const openBranch = useCallback((branch: BranchInfo) => { selectBranch(branch); setDetailBranch(branch); }, [selectBranch]);
  const commitsForBranch = useMemo(() => selectedBranch && topology ? branchCommits(selectedBranch, topology.commits) : [], [selectedBranch, topology]);
  const detailCommits = useMemo(() => detailBranch && topology ? branchCommits(detailBranch, topology.commits) : [], [detailBranch, topology]);
  const branchActions = (branch: BranchInfo) => <div className="gitflow-detail-actions">
    {!branch.is_current && !branch.is_remote && <Button disabled={busy} onClick={() => void runAction(() => checkoutBranch(branch.name, projectId!))} variant="secondary" size="sm" className="gitflow-action">切换到此分支</Button>}
    {!branch.is_current && !branch.is_remote && <Button disabled={busy} onClick={() => { if (window.confirm(`将 ${branch.name} 合并到 ${topology?.current_branch}？`)) void runAction(() => mergeBranch(branch.name, projectId!)); }} variant="secondary" size="sm" className="gitflow-action" icon={<GitMerge size={12} aria-hidden="true"/>}>合并到当前分支</Button>}
    {!branch.is_current && !branch.is_remote && <Button disabled={busy} onClick={() => void runAction(async () => setReviewResult(await requestMergeReview(branch.name, topology!.current_branch, projectId!)))} variant="secondary" size="sm" className="gitflow-action">合并审查</Button>}
    {!branch.is_current && !branch.is_remote && <Button disabled={busy} onClick={() => { if (window.confirm(`安全删除已合并分支 ${branch.name}？`)) void runAction(() => deleteBranch(branch.name, projectId!)); }} variant="danger" size="sm" className="gitflow-action" icon={<Trash2 size={12} aria-hidden="true"/>}>安全删除</Button>}
  </div>;

  return <div style={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column', color: 'var(--text-primary)', background: 'var(--bg-workspace)' }}>
    <header style={{ padding: 'var(--space-3) var(--space-4)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-25)', minWidth: 0 }}><span style={{ width: 30, height: 30, display: 'grid', placeItems: 'center', borderRadius: 'var(--radius-md-plus)', color: 'var(--accent-primary)', background: 'color-mix(in srgb, var(--accent-primary) 9%, var(--bg-surface))' }}><GitBranch size={16} /></span><div style={{ minWidth: 0 }}><div style={{ fontSize: 'var(--font-size-md)', fontWeight: 650 }}>GitFlow</div><div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{topology?.repo_name || '分支工作流'}</div></div></div>
      <div style={{ display: 'flex', gap: 'var(--space-1-75)', alignItems: 'center' }}>{topology?.is_git !== false && topology && <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)', marginRight: 'var(--space-0-75)' }}>HEAD · <b style={{ color: 'var(--accent-emerald)' }}>{topology.current_branch}</b></span>}{topology?.is_git !== false && <Button disabled={!projectId || busy || !topology} onClick={() => setShowCreate(true)} variant="primary" size="sm" className="gitflow-action" icon={<Plus size={13} aria-hidden="true"/>}>新建分支</Button>}<IconButton label="刷新拓扑" title="刷新拓扑" onClick={() => void loadData()} disabled={loading} size="sm"><RefreshCw size={14} className={loading ? 'pulse-glow' : ''} /></IconButton></div>
    </header>
    {error && <div style={{ padding: 'var(--space-1-75) var(--space-3-5)', color: 'var(--accent-rose)', background: 'color-mix(in srgb, var(--accent-rose) 8%, var(--bg-surface))', fontSize: 'var(--font-size-compact)' }}>{error}</div>}
    {!projectId ? <EmptyState className="gitflow-empty-state" icon={<GitBranch size={24}/>} title="此对话未绑定项目" description="GitFlow 是项目级工具，请先为对话选择项目。" /> : !topology && loading ? <EmptyState className="gitflow-empty-state" title="正在读取项目仓库…" /> : topology ? <>
      {topology.is_git === false ? <EmptyState className="gitflow-empty-state" icon={<GitBranch size={25}/>} title="此项目目录不是 Git 仓库" description="当前目录没有 Git 分支和提交记录。" /> : <>
      <div className="gitflow-subtabs"><button className={view === 'local' ? 'active' : ''} onClick={() => setView('local')}>本地分支 <span>{topology.branches.filter((branch) => !branch.is_remote).length}</span></button><button className={view === 'remote' ? 'active' : ''} onClick={() => setView('remote')}>远程状态 <span>{topology.branches.filter((branch) => branch.is_remote).length}</span></button></div>
      {view === 'local' ? <>
        <div className="gitflow-topology-title"><div><strong>本地分支关系</strong><span>仅显示仓库现有分支；拖动节点可调整位置。</span></div><span className="gitflow-branch-total">{topology.branches.filter((branch) => !branch.is_remote).length} 个分支</span></div>
        {topology.branches.some((branch) => !branch.is_remote) ? <div className="gitflow-graph-frame"><ReactFlowProvider><GraphCanvas topology={topology} layoutScope={projectId} selectedBranch={selectedBranch} onSelectBranch={selectBranch} onOpenBranch={openBranch} /></ReactFlowProvider></div> : <EmptyState className="gitflow-empty-state" icon={<GitBranch size={24}/>} title="仓库还没有分支" description="创建首个提交后，Git 才会生成可展示的分支。" />}
        {selectedBranch && !selectedBranch.is_remote ? <>
        <div className="gitflow-commit-heading"><div><GitCommitHorizontal size={14} /><b>{selectedBranch.name} · 提交记录</b></div><IconButton onClick={() => openBranch(selectedBranch)} label="查看分支操作" size="sm"><Maximize2 size={13} /></IconButton></div>
        <div className="gitflow-commit-list">{commitsForBranch.length ? commitsForBranch.slice(0, 4).map((commit) => <CommitEntry commit={commit} compact key={commit.hash} />) : <div className="gitflow-no-commits">此分支暂无可读取的提交记录</div>}</div>
        </> : <div className="gitflow-no-commits">选择本地分支查看提交记录</div>}
      </> : <div className="gitflow-remote-list">{topology.branches.filter((branch) => branch.is_remote).length ? topology.branches.filter((branch) => branch.is_remote).map((branch) => {
        const local = topology.branches.find((candidate) => !candidate.is_remote && (candidate.upstream === branch.name || branch.name === `origin/${candidate.name}`));
        const localCommits = local ? branchCommits(local, topology.commits) : [];
        const remoteCommits = branchCommits(branch, topology.commits);
        const ahead = local?.ahead ?? localCommits.filter((commit) => !remoteCommits.some((remoteCommit) => remoteCommit.hash === commit.hash)).length;
        const behind = local?.behind ?? remoteCommits.filter((commit) => !localCommits.some((localCommit) => localCommit.hash === commit.hash)).length;
        return <button key={branch.name} className="gitflow-remote-row" onClick={() => setSelectedBranch(branch)}><GitBranch size={14} /><strong>{branch.name}</strong><span>{local ? `关联 ${local.name} · 未推送 ${ahead} · 待拉取 ${behind}` : '远程跟踪引用'}</span><code>{branch.head?.slice(0, 8)}</code></button>;
      }) : <EmptyState className="gitflow-empty-state" icon={<GitBranch size={24}/>} title="暂无远程分支引用" description="此页只列出本地仓库已获取的远程跟踪分支。" />}</div>}
      </>}
    </> : <EmptyState className="gitflow-empty-state" icon={<GitBranch size={25}/>} title="无法读取仓库" description={error || '检查项目目录和 Git 仓库状态。'} />}
    {detailBranch && topology && <div style={modalBackdrop} onMouseDown={(event) => { if (event.target === event.currentTarget) setDetailBranch(null); }}><section style={modal} role="dialog" aria-modal="true" aria-label={`${detailBranch.name} 分支详情`}>
      <div className="gitflow-detail-header"><IconButton onClick={() => setDetailBranch(null)} label="返回" size="sm"><ArrowLeft size={16} /></IconButton><div><strong style={{ color: branchColor(detailBranch.name) }}>{detailBranch.name}</strong><small>{detailBranch.is_current ? '当前分支' : detailBranch.is_remote ? '远程跟踪分支' : '本地分支'}{detailBranch.head ? ` · HEAD ${detailBranch.head.slice(0, 8)}` : ''}</small></div><GitBranch size={18} color="var(--accent-primary)" /></div>
      <div className="gitflow-detail-section"><b>分支操作</b>{branchActions(detailBranch)}{reviewResult && <p className={reviewResult.has_conflict ? 'gitflow-review-error' : 'gitflow-review-ok'}>{reviewResult.summary}</p>}</div>
      <div className="gitflow-detail-section"><b>提交记录 <span>{detailCommits.length} · 合并提交标注父提交关系</span></b><div className="gitflow-detail-commits">{detailCommits.length ? detailCommits.map((commit) => <CommitEntry commit={commit} key={commit.hash} />) : <div className="gitflow-no-commits">此分支暂无可读取的提交记录</div>}</div></div>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}><Button onClick={() => setDetailBranch(null)} variant="secondary" size="sm" className="gitflow-action">完成</Button></div>
    </section></div>}
    {showCreate && <div style={modalBackdrop} onMouseDown={(event) => { if (event.target === event.currentTarget) setShowCreate(false); }}><form onSubmit={handleCreate} style={{ ...modal, width: 320 }}><b style={{ fontSize: 'var(--font-size-body)' }}>新建分支</b><span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)' }}>从当前分支 {topology?.current_branch || 'HEAD'} 创建</span><TextInput autoFocus value={branchName} onChange={(event) => setBranchName(event.target.value)} placeholder="feature/your-branch" className="gitflow-branch-name-input" /><div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}><Button type="button" onClick={() => setShowCreate(false)} variant="secondary" size="sm" className="gitflow-action">取消</Button><Button type="submit" disabled={!branchName.trim() || busy} variant="primary" size="sm" className="gitflow-action">创建分支</Button></div></form></div>}
  </div>;
};
