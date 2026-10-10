import React, { useEffect, useState } from 'react';
import { RefreshCw, Bookmark, Folders } from 'lucide-react';
import { fetchFilePreview, fetchWorktreeDiff, fetchWorktreeRefs, stageWorktreeFile, discardWorktreeFile, createWorktreeCheckpoint } from '../../api/toolApi';
import { WorktreeCommitRef, WorktreeDiffData } from '../../types/tool';
import { DiffFileList } from './DiffFileList';
import { DiffCodeView } from './DiffCodeView';
import { useChatStore } from '../../stores/chatStore';
import { ResizableTreeLayout } from './ResizableTreeLayout';

/**
 * 右侧工具 1 - 差异对比与工作树检查点面板
 */
export const DiffViewerTab: React.FC = () => {
  const { activeThreadId, threads, draftProjectId } = useChatStore();
  const [data, setData] = useState<WorktreeDiffData | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [sourcePreview, setSourcePreview] = useState<string | null>(null);
  const [previewMessage, setPreviewMessage] = useState<string | null>(null);
  const [branches, setBranches] = useState<string[]>([]);
  const [commits, setCommits] = useState<WorktreeCommitRef[]>([]);
  const [selectedBranch, setSelectedBranch] = useState('');
  const [selectedCommit, setSelectedCommit] = useState('');
  const [refsLoadedFor, setRefsLoadedFor] = useState<string | null>(null);
  const [treeCollapsed, setTreeCollapsed] = useState(false);

  const activeThread = threads.find((thread) => thread.thread_id === activeThreadId);
  const projectId = activeThreadId ? activeThread?.project_id || undefined : draftProjectId || undefined;
  const selectedPatch = selectedFile ? [data?.diff_staged, data?.diff_text].filter(Boolean).flatMap((text) => text!.split(/(?=^diff --git )/m).filter((block) => block.includes(`b/${selectedFile}`) || block.includes(`a/${selectedFile}`))).join('\n') : '';

  const loadDiff = async (baseRef = selectedCommit) => {
    if (!projectId) {
      setData(null);
      setSelectedFile(null);
      return;
    }
    setLoading(true);
    try {
      const res = await fetchWorktreeDiff(undefined, projectId, baseRef || undefined);
      setData(res);
      const files = [...new Set([...res.staged.map((item) => item.file), ...res.unstaged.map((item) => item.file), ...res.untracked])];
      setSelectedFile((current) => current && files.includes(current) ? current : files[0] || null);
    } finally {
      setLoading(false);
    }
  };

  const loadRefs = async (branch?: string) => {
    if (!projectId) { setBranches([]); setCommits([]); setSelectedBranch(''); setSelectedCommit(''); setRefsLoadedFor(null); return; }
    setRefsLoadedFor(null);
    const refs = await fetchWorktreeRefs(projectId, branch);
    setBranches(refs.branches);
    const nextBranch = branch || refs.current_branch || refs.branches[0] || '';
    setSelectedBranch(nextBranch);
    setCommits(refs.commits);
    setSelectedCommit(refs.commits[0]?.hash || nextBranch);
    setRefsLoadedFor(projectId);
  };

  useEffect(() => {
    void loadRefs();
  }, [projectId]);

  useEffect(() => {
    if (!projectId) void loadDiff('');
    else if (refsLoadedFor === projectId) void loadDiff(selectedCommit);
  }, [projectId, selectedCommit, refsLoadedFor]);

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
      .catch((error: unknown) => { if (!cancelled) setPreviewMessage(error instanceof Error ? error.message : '无法读取文件预览'); });
    return () => { cancelled = true; };
  }, [selectedFile, selectedPatch, projectId]);

  const handleStage = async (file: string) => {
    await stageWorktreeFile([file], undefined, projectId);
    loadDiff(selectedCommit);
  };

  const handleDiscard = async (file: string) => {
    if (window.confirm(`确定放弃对 ${file} 的修改吗？`)) {
      await discardWorktreeFile([file], undefined, projectId);
      loadDiff(selectedCommit);
    }
  };

  const handleCheckpoint = async () => {
    const msg = window.prompt('请输入检查点提交说明:', 'Manual Checkpoint');
    if (msg) {
      await createWorktreeCheckpoint(msg, undefined, projectId);
      loadDiff(selectedCommit);
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-workspace)' }}>
      {/* 顶部操作栏 */}
      <div
        style={{
          padding: '10px 16px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ fontSize: 13, fontWeight: 600 }}>变更</span>
          <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>当前工作树 · 对比所选提交</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {projectId && <>
            <select aria-label="选择对比分支" value={selectedBranch} onChange={(event) => { void loadRefs(event.target.value); }} style={selectorStyle}>
              {branches.map((branch) => <option key={branch} value={branch}>{branch}</option>)}
            </select>
            <select aria-label="选择对比提交" value={selectedCommit} onChange={(event) => setSelectedCommit(event.target.value)} style={{ ...selectorStyle, maxWidth: 190 }}>
              {commits.map((commit) => <option key={commit.hash} value={commit.hash}>{commit.short_hash} · {commit.subject}</option>)}
            </select>
          </>}
          <button
            onClick={() => setTreeCollapsed((value) => !value)}
            title={treeCollapsed ? '显示变更目录' : '收起变更目录'}
            aria-label={treeCollapsed ? '显示变更目录' : '收起变更目录'}
            style={{ padding: 5, color: 'var(--text-muted)' }}
          ><Folders size={15} /></button>
          <button
            onClick={handleCheckpoint}
            style={{
              padding: '4px 10px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'rgba(124, 58, 237, 0.15)',
              color: '#C4B5FD',
              border: '1px solid rgba(124, 58, 237, 0.3)',
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
          >
            <Bookmark size={13} />
            <span>创建检查点</span>
          </button>
          <button
            onClick={() => { void loadDiff(selectedCommit); }}
            style={{ padding: 5, borderRadius: 'var(--radius-sm)', color: 'var(--text-muted)' }}
          >
            <RefreshCw size={14} className={loading ? 'pulse-glow' : ''} />
          </button>
        </div>
      </div>

      {/* 左右分栏: 左侧文件列表，右侧代码统一对比 */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {!projectId ? <div style={{ flex: 1, display: 'grid', placeItems: 'center', color: 'var(--text-muted)', fontSize: 13 }}>当前对话未绑定项目，没有可显示的变更</div> : <ResizableTreeLayout collapsed={treeCollapsed} onToggle={() => setTreeCollapsed((value) => !value)} primary={<DiffCodeView fileName={selectedFile} sourceText={sourcePreview} message={previewMessage} diffText={selectedPatch} />} secondary={<DiffFileList data={data} selectedFile={selectedFile} onSelect={setSelectedFile} onStage={handleStage} onDiscard={handleDiscard} />} />}
      </div>
    </div>
  );
};

const selectorStyle: React.CSSProperties = { maxWidth: 150, minWidth: 90, height: 27, padding: '0 7px', color: 'var(--text-secondary)', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 6, fontSize: 10.5 };
