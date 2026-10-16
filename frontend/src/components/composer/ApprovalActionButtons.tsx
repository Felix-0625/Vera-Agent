import React, { useState } from 'react';
import { Check, X, Edit2 } from 'lucide-react';
import { TextInput } from '../common/Field';
import { Button } from '../common/Button';

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
      <div style={{ display: 'flex', gap: 'var(--space-2)', marginTop: 'var(--space-1)' }}>
        <TextInput
          type="text"
          value={overrideText}
          onChange={(e) => setOverrideText(e.target.value)}
          placeholder="输入修正指令或执行反馈 (Override)..."
          className="approval-override-input"
        />
        <Button onClick={handleOverrideSubmit} variant="primary" size="sm">提交修正</Button>
        <Button onClick={() => setShowOverrideInput(false)} variant="ghost" size="sm">取消</Button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
      <Button
        onClick={() => onConfirm('Y')}
        variant="success"
        size="sm"
        icon={<Check size={14} />}
      >
        批准执行 (Y)
      </Button>

      <Button
        onClick={() => onConfirm('N')}
        variant="danger"
        size="sm"
        icon={<X size={14} />}
      >
        驳回操作 (N)
      </Button>

      <Button
        onClick={() => setShowOverrideInput(true)}
        variant="secondary"
        size="sm"
        icon={<Edit2 size={13} />}
      >
        修改执行 (O)
      </Button>
    </div>
  );
};
