import React, { useEffect, useState } from 'react';
import { GitBranch, Plus, RefreshCw } from 'lucide-react';
import { fetchBranches, createBranch, checkoutBranch, mergeBranch, requestMergeReview } from '../../api/toolApi';
import { BranchInfo } from '../../types/tool';
import { BranchOperationPanel } from './BranchOperationPanel';
import { useChatStore } from '../../stores/chatStore';

/**
 * 右侧工具 9 - GitFlow 分支拓扑与合并审查面板
 */
export const GitFlowTab: React.FC = () => {
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const threads = useChatStore((state) => state.threads);
  const draftProjectId = useChatStore((state) => state.draftProjectId);
  const projectId = activeThreadId ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id || undefined : draftProjectId || undefined;
  const [branches, setBranches] = useState<BranchInfo[]>([]);
  const [currentBranch, setCurrentBranch] = useState('main');
  const [selectedBranch, setSelectedBranch] = useState<BranchInfo | null>(null);
  const [reviewResult, setReviewResult] = useState<{ has_conflict: boolean; summary: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await fetchBranches(projectId);
      setBranches(res.branches || []);
      setCurrentBranch(res.current_branch || 'main');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [projectId]);

  const handleCreateBranch = async () => {
    const name = window.prompt('请输入新分支名称 (如 feat/payment):');
    if (name) {
      await createBranch(name.trim(), 'HEAD', projectId);
      loadData();
    }
  };

  const handleCheckout = async (name: string) => {
    await checkoutBranch(name, projectId);
    loadData();
  };

  const handleMerge = async (source: string) => {
    if (window.confirm(`确认将分支 ${source} 合并到当前分支 ${currentBranch} 吗？`)) {
      await mergeBranch(source, projectId);
      loadData();
    }
  };

  const handleMergeReview = async (source: string) => {
    const res = await requestMergeReview(source, currentBranch);
    setReviewResult(res);
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-workspace)' }}>
      {/* 顶部标题与操作栏 */}
      <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600 }}>
          <GitBranch size={16} color="var(--accent-amber)" />
          <span>GitFlow 分支拓扑与合并审查</span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={handleCreateBranch}
            style={{ padding: '4px 10px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--accent-primary)', color: '#fff', fontSize: 11.5, display: 'flex', gap: 4, alignItems: 'center' }}
          >
            <Plus size={13} />
            <span>新建分支</span>
          </button>
          <button onClick={loadData} style={{ padding: 4, color: 'var(--text-muted)' }}>
            <RefreshCw size={14} className={loading ? 'pulse-glow' : ''} />
          </button>
        </div>
      </div>

      {/* 左右分栏: 左侧分支列表，右侧操作详情 */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <div style={{ width: 220, borderRight: '1px solid var(--border-subtle)', overflowY: 'auto', padding: 8 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8 }}>
            仓库分支列表
          </div>
          {branches.map((b) => (
            <div
              key={b.name}
              onClick={() => {
                setSelectedBranch(b);
                setReviewResult(null);
              }}
              style={{
                padding: '7px 10px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: selectedBranch?.name === b.name ? 'var(--bg-card)' : 'transparent',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                fontSize: 12,
                color: b.is_current ? 'var(--accent-emerald)' : 'var(--text-secondary)',
                fontWeight: b.is_current ? 600 : 400,
              }}
            >
              <span>{b.name}</span>
              {b.is_current && <span style={{ fontSize: 10, color: 'var(--accent-emerald)' }}>HEAD</span>}
            </div>
          ))}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          <BranchOperationPanel
            selectedBranch={selectedBranch}
            currentBranch={currentBranch}
            reviewResult={reviewResult}
            onCheckout={handleCheckout}
            onMerge={handleMerge}
            onMergeReview={handleMergeReview}
          />
        </div>
      </div>
    </div>
  );
};
