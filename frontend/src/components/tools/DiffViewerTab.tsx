import React, { useCallback, useEffect, useRef, useState } from 'react';
import { RefreshCw, Folders } from 'lucide-react';
import { fetchFilePreview, fetchWorktreeDiff, fetchWorktreeRefs, stageWorktreeFile, discardWorktreeFile } from '../../api/toolApi';
import { WorktreeCommitRef, WorktreeDiffData } from '../../types/tool';
import { DiffFileList } from './DiffFileList';
import { DiffCodeView } from './DiffCodeView';
import { useChatStore } from '../../stores/chatStore';
import { ResizableTreeLayout } from './ResizableTreeLayout';
import { SelectField } from '../common/Field';
import { IconButton } from '../common/IconButton';

/**
 * 右侧工具 1 - 差异对比与工作树检查点面板
 */
export const DiffViewerTab: React.FC<{ projectId?: string | null }> = ({ projectId: projectIdOverride }) => {
  const { activeThreadId, threads, draftProjectId } = useChatStore();
  const [data, setData] = useState<WorktreeDiffData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [sourcePreview, setSourcePreview] = useState<string | null>(null);
  const [previewMessage, setPreviewMessage] = useState<string | null>(null);
  const [branches, setBranches] = useState<string[]>([]);
  const [commits, setCommits] = useState<WorktreeCommitRef[]>([]);
  const [selectedBranch, setSelectedBranch] = useState('');
  const [selectedCommit, setSelectedCommit] = useState('');
  const [refsLoadedFor, setRefsLoadedFor] = useState<string | null>(null);
  const [treeCollapsed, setTreeCollapsed] = useState(false);
  const diffRequestId = useRef(0);
  const refsRequestId = useRef(0);

  const activeThread = threads.find((thread) => thread.thread_id === activeThreadId);
  const projectId = projectIdOverride !== undefined ? projectIdOverride || undefined : activeThreadId ? activeThread?.project_id || undefined : draftProjectId || undefined;
  const selectedPatch = selectedFile ? [data?.diff_staged, data?.diff_text].filter(Boolean).flatMap((text) => text!.split(/(?=^diff --git )/m).filter((block) => block.includes(`b/${selectedFile}`) || block.includes(`a/${selectedFile}`))).join('\n') : '';

  const loadDiff = useCallback(async (baseRef = selectedCommit) => {
    const requestId = ++diffRequestId.current;
    if (!projectId) {
      setData(null);
      setSelectedFile(null);
      setLoading(false);
      setError('');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await fetchWorktreeDiff(undefined, projectId, baseRef || undefined);
      if (requestId !== diffRequestId.current) return;
      setData(res);
      const files = [...new Set([...res.staged.map((item) => item.file), ...res.unstaged.map((item) => item.file), ...res.untracked])];
      setSelectedFile((current) => current && files.includes(current) ? current : files[0] || null);
    } catch (cause) {
      if (requestId !== diffRequestId.current) return;
      setData(null);
      setSelectedFile(null);
      setError(cause instanceof Error ? cause.message : '读取工作树差异失败');
    } finally {
      if (requestId === diffRequestId.current) setLoading(false);
    }
  }, [projectId, selectedCommit]);

  const loadRefs = useCallback(async (branch?: string) => {
    const requestId = ++refsRequestId.current;
    if (!projectId) { setBranches([]); setCommits([]); setSelectedBranch(''); setSelectedCommit(''); setRefsLoadedFor(null); setError(''); return; }
    setRefsLoadedFor(null);
    setError('');
    try {
      const refs = await fetchWorktreeRefs(projectId, branch);
      if (requestId !== refsRequestId.current) return;
      setBranches(refs.branches);
      const nextBranch = branch || refs.current_branch || refs.branches[0] || '';
      setSelectedBranch(nextBranch);
      setCommits(refs.commits);
      setSelectedCommit(refs.commits[0]?.hash || nextBranch);
      setRefsLoadedFor(projectId);
    } catch (cause) {
      if (requestId !== refsRequestId.current) return;
      setBranches([]);
      setCommits([]);
      setData(null);
      setSelectedFile(null);
      setError(cause instanceof Error ? cause.message : '读取分支和提交失败');
    }
  }, [projectId]);

  useEffect(() => {
    void loadRefs();
  }, [loadRefs]);

  useEffect(() => {
    if (!projectId) void loadDiff('');
    else if (refsLoadedFor === projectId) void loadDiff(selectedCommit);
  }, [loadDiff, projectId, selectedCommit, refsLoadedFor]);

  useEffect(() => {
    let cancelled = false;
    setSourcePreview(null);
    setPreviewMessage(null);
    if (!selectedFile || selectedPatch) return () => { cancelled = true; };
    fetchFilePreview(selectedFile, undefined, projectId)
      .then((result) => {
        if (cancelled) return;
        if (result.kind === 'text') setSourcePreview(result.content);
        else if (result.kind === 'unsupported') setPreviewMessage(result.message);
        else setPreviewMessage('该文件没有可显示的文本差异。');
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : '';
        setPreviewMessage(/not found|404/i.test(message) ? '此文件无变更记录，预览请在文件标签页打开' : message || '无法读取文件预览');
      });
    return () => { cancelled = true; };
  }, [selectedFile, selectedPatch, projectId]);

  const handleStage = async (file: string) => {
    try {
      await stageWorktreeFile([file], undefined, projectId);
      await loadDiff(selectedCommit);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '暂存文件失败');
    }
  };

  const handleDiscard = async (file: string) => {
    if (window.confirm(`确定放弃对 ${file} 的修改吗？`)) {
      try {
        await discardWorktreeFile([file], undefined, projectId);
        await loadDiff(selectedCommit);
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : '放弃文件修改失败');
      }
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-workspace)' }}>
      {/* 顶部操作栏 */}
      <div
        style={{
          padding: 'var(--space-2-5) var(--space-4)',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-0-5)' }}>
          <span style={{ fontSize: 'var(--font-size-md)', fontWeight: 600 }}>变更</span>
          <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>当前工作树 · 对比所选提交</span>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          {projectId && <>
            <SelectField aria-label="选择对比分支" value={selectedBranch} onChange={(event) => { void loadRefs(event.target.value); }} className="diff-selector diff-selector--branch">
              {branches.map((branch) => <option key={branch} value={branch}>{branch}</option>)}
            </SelectField>
            <SelectField aria-label="选择对比提交" value={selectedCommit} onChange={(event) => setSelectedCommit(event.target.value)} className="diff-selector diff-selector--commit">
              {commits.map((commit) => <option key={commit.hash} value={commit.hash}>{commit.short_hash} · {commit.subject}</option>)}
            </SelectField>
          </>}
          <IconButton
            label={treeCollapsed ? '显示变更目录' : '收起变更目录'}
            onClick={() => setTreeCollapsed((value) => !value)}
            title={treeCollapsed ? '显示变更目录' : '收起变更目录'}
            size="sm"
          ><Folders size={15} /></IconButton>
          <IconButton
            label="刷新差异"
            onClick={() => { void loadDiff(selectedCommit); }}
            disabled={loading}
            size="sm"
          >
            <RefreshCw size={14} className={loading ? 'pulse-glow' : ''} />
          </IconButton>
        </div>
      </div>

      {error && <div role="alert" style={{ padding: 'var(--space-1-75) var(--space-3-5)', color: 'var(--accent-rose)', background: 'color-mix(in srgb, var(--accent-rose) 8%, var(--bg-surface))', fontSize: 'var(--font-size-compact)' }}>{error}</div>}

      {/* 左右分栏: 左侧文件列表，右侧代码统一对比 */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {!projectId ? <div style={{ flex: 1, display: 'grid', placeItems: 'center', color: 'var(--text-muted)', fontSize: 'var(--font-size-md)' }}>当前对话未绑定项目，没有可显示的变更</div> : <ResizableTreeLayout collapsed={treeCollapsed} onToggle={() => setTreeCollapsed((value) => !value)} primary={<DiffCodeView fileName={selectedFile} sourceText={sourcePreview} message={previewMessage} diffText={selectedPatch} />} secondary={<DiffFileList data={data} selectedFile={selectedFile} onSelect={setSelectedFile} onStage={handleStage} onDiscard={handleDiscard} />} />}
      </div>
    </div>
  );
};
