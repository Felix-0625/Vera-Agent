import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { ApprovalActionButtons } from './ApprovalActionButtons';

/**
 * 中间区域 - 高危操作安全审批门禁卡片
 */
export const ApprovalBanner: React.FC = () => {
  const { approvalRequest, confirmAction } = useChatStore();

  if (!approvalRequest) return null;

  return (
    <div
      className="animate-fade-in"
      style={{
        margin: 'var(--space-3) 0',
        padding: 'var(--space-3-5) var(--space-4-5)',
        borderRadius: 'var(--radius-md)',
        backgroundColor: 'var(--bg-warning-soft)',
        border: '1px solid color-mix(in srgb, var(--accent-amber) 35%, var(--border-subtle))',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-2-5)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)' }}>
        <AlertTriangle size={18} color="var(--accent-amber)" />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 600, color: 'var(--accent-amber)' }}>
            高危操作安全审批门禁
          </div>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginTop: 'var(--space-0-5)' }}>
            工具调用: <code style={{ backgroundColor: 'var(--bg-input)', padding: 'var(--space-0-5) var(--space-1-25)', borderRadius: 'var(--radius-xs)' }}>{approvalRequest.tool_name}</code>
            {' — '}{approvalRequest.message}
          </div>
        </div>
      </div>

      <div style={{ fontSize: 'var(--font-size-compact)', color: 'var(--text-muted)', fontFamily: 'monospace', backgroundColor: 'var(--bg-input)', padding: 'var(--space-1-5) var(--space-2-5)', borderRadius: 'var(--radius-xs)', overflowX: 'auto' }}>
        {JSON.stringify(approvalRequest.args, null, 2)}
      </div>

      <ApprovalActionButtons onConfirm={confirmAction} />
    </div>
  );
};
