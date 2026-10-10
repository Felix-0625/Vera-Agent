import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { BranchInfo } from '../../types/tool';

interface BranchOperationPanelProps {
  selectedBranch: BranchInfo | null;
  currentBranch: string;
  reviewResult: { has_conflict: boolean; summary: string } | null;
  onCheckout: (name: string) => Promise<void>;
  onMerge: (name: string) => Promise<void>;
  onMergeReview: (name: string) => Promise<void>;
}

/**
 * 右侧工具 9 - 分支操作与三方审查结果面板
 */
export const BranchOperationPanel: React.FC<BranchOperationPanelProps> = ({
  selectedBranch,
  currentBranch,
  reviewResult,
  onCheckout,
  onMerge,
  onMergeReview,
}) => {
  if (!selectedBranch) {
    return (
      <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: 40, fontSize: 13 }}>
        请在左侧选择要操作的分支节点
      </div>
    );
  }

  return (
    <div>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>{selectedBranch.name}</h3>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
        当前所在主分支: <strong>{currentBranch}</strong>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {!selectedBranch.is_current && (
          <button
            onClick={() => onCheckout(selectedBranch.name)}
            style={{ padding: '6px 14px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-default)', fontSize: 12 }}
          >
            检出并切换 (Checkout)
          </button>
        )}
        <button
          onClick={() => onMerge(selectedBranch.name)}
          style={{ padding: '6px 14px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(245, 158, 11, 0.15)', color: 'var(--accent-amber)', fontSize: 12 }}
        >
          合并到当前分支 (Merge)
        </button>
        <button
          onClick={() => onMergeReview(selectedBranch.name)}
          style={{ padding: '6px 14px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(6, 182, 212, 0.15)', color: 'var(--accent-cyan)', fontSize: 12 }}
        >
          发起三方审查 (3-Way Review)
        </button>
      </div>

      {reviewResult && (
        <div className="glass-card" style={{ padding: 14 }}>
          <div style={{ fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
            <ShieldCheck size={16} color={reviewResult.has_conflict ? 'var(--accent-rose)' : 'var(--accent-emerald)'} />
            <span>审查结果: {reviewResult.has_conflict ? '检测到冲突' : '无合并冲突，允许直推'}</span>
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 6, lineHeight: 1.5 }}>
            {reviewResult.summary}
          </div>
        </div>
      )}
    </div>
  );
};
