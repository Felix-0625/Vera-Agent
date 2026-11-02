import { ShieldCheck } from 'lucide-react';
import React from 'react';
import { BranchInfo } from '../../types/tool';

interface BranchOperationPanelProps {
  selectedBranch: BranchInfo | null;
  currentBranch: string;
  reviewResult: { has_conflict: boolean; summary: string } | null;
  onCheckout: (name: string) => Promise<void>;
  onMerge: (name: string) => Promise<void>;
  onMergeReview: (name: string) => Promise<void>;
}

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
      <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: 40, fontSize: 'var(--font-size-md)' }}>
        请在左侧选择要操作的分支节点
      </div>
    );
  }

  return (
    <div>
      <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, marginBottom: 'var(--space-2)' }}>
        {selectedBranch.name}
      </h3>
      <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>
        当前所在主分支: <strong>{currentBranch}</strong>
      </div>

      <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-4)', flexWrap: 'wrap' }}>
        {!selectedBranch.is_current && (
          <button
            onClick={() => onCheckout(selectedBranch.name)}
            style={{
              padding: 'var(--space-1-5) var(--space-3-5)',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-default)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            检出并切换 (Checkout)
          </button>
        )}
        <button
          onClick={() => onMerge(selectedBranch.name)}
          style={{
            padding: 'var(--space-1-5) var(--space-3-5)',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--bg-warning-soft)',
            color: 'var(--accent-amber)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          合并到当前分支 (Merge)
        </button>
        <button
          onClick={() => onMergeReview(selectedBranch.name)}
          style={{
            padding: 'var(--space-1-5) var(--space-3-5)',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--bg-info-soft)',
            color: 'var(--accent-cyan)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          发起三方审查 (3-Way Review)
        </button>
      </div>

      {reviewResult && (
        <div className="glass-card" style={{ padding: 'var(--space-3-5)' }}>
          <div
            style={{
              fontSize: 'var(--font-size-md)',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-1-5)',
            }}
          >
            <ShieldCheck size={16} color={reviewResult.has_conflict ? 'var(--accent-rose)' : 'var(--accent-emerald)'} />
            <span>审查结果: {reviewResult.has_conflict ? '检测到冲突' : '无合并冲突，允许直推'}</span>
          </div>
          <div
            style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--text-secondary)',
              marginTop: 'var(--space-1-5)',
              lineHeight: 1.5,
            }}
          >
            {reviewResult.summary}
          </div>
        </div>
      )}
    </div>
  );
};
