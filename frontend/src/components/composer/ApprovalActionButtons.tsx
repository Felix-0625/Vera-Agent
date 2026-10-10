import React, { useState } from 'react';
import { Check, X, Edit2 } from 'lucide-react';

interface ApprovalActionButtonsProps {
  onConfirm: (action: string) => void;
}

/**
 * 审批门禁底部的操作按钮与修正指令输入行
 */
export const ApprovalActionButtons: React.FC<ApprovalActionButtonsProps> = ({ onConfirm }) => {
  const [overrideText, setOverrideText] = useState('');
  const [showOverrideInput, setShowOverrideInput] = useState(false);

  const handleOverrideSubmit = () => {
    if (overrideText.trim()) {
      onConfirm(`O:${overrideText.trim()}`);
      setOverrideText('');
      setShowOverrideInput(false);
    }
  };

  if (showOverrideInput) {
    return (
      <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
        <input
          type="text"
          value={overrideText}
          onChange={(e) => setOverrideText(e.target.value)}
          placeholder="输入修正指令或执行反馈 (Override)..."
          style={{
            flex: 1,
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            fontSize: 12,
            color: 'var(--text-primary)',
          }}
        />
        <button
          onClick={handleOverrideSubmit}
          style={{
            padding: '6px 14px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--accent-primary)',
            color: '#FFFFFF',
            fontSize: 12,
            fontWeight: 500,
          }}
        >
          提交修正
        </button>
        <button
          onClick={() => setShowOverrideInput(false)}
          style={{
            padding: '6px 10px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'transparent',
            color: 'var(--text-muted)',
            fontSize: 12,
          }}
        >
          取消
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end' }}>
      <button
        onClick={() => onConfirm('Y')}
        style={{
          padding: '6px 14px',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'rgba(16, 185, 129, 0.2)',
          border: '1px solid var(--accent-emerald)',
          color: 'var(--accent-emerald)',
          fontSize: 12,
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: 5,
        }}
      >
        <Check size={14} />
        <span>批准执行 (Y)</span>
      </button>

      <button
        onClick={() => onConfirm('N')}
        style={{
          padding: '6px 14px',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid var(--accent-rose)',
          color: 'var(--accent-rose)',
          fontSize: 12,
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: 5,
        }}
      >
        <X size={14} />
        <span>驳回操作 (N)</span>
      </button>

      <button
        onClick={() => setShowOverrideInput(true)}
        style={{
          padding: '6px 12px',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-default)',
          color: 'var(--text-secondary)',
          fontSize: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 5,
        }}
      >
        <Edit2 size={13} />
        <span>修改执行 (O)</span>
      </button>
    </div>
  );
};
