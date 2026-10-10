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
        margin: '12px 0',
        padding: '14px 18px',
        borderRadius: 'var(--radius-md)',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        border: '1px solid rgba(245, 158, 11, 0.35)',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <AlertTriangle size={18} color="var(--accent-amber)" />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#FBBF24' }}>
            高危操作安全审批门禁
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
            工具调用: <code style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '2px 5px', borderRadius: 4 }}>{approvalRequest.tool_name}</code>
            {' — '}{approvalRequest.message}
          </div>
        </div>
      </div>

      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace', backgroundColor: 'rgba(0, 0, 0, 0.3)', padding: '6px 10px', borderRadius: 4, overflowX: 'auto' }}>
        {JSON.stringify(approvalRequest.args, null, 2)}
      </div>

      <ApprovalActionButtons onConfirm={confirmAction} />
    </div>
  );
};
