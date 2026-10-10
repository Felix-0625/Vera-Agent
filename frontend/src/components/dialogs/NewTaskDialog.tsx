import React, { useState } from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { Modal } from '../common/Modal';
import { createScheduledTask } from '../../api/toolApi';

export const NewTaskDialog: React.FC = () => {
  const { newTaskDialogOpen, setNewTaskDialogOpen } = useLayoutStore();
  const [name, setName] = useState('');
  const [cron, setCron] = useState('0 * * * *');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !prompt.trim()) return;

    setLoading(true);
    try {
      await createScheduledTask({
        name: name.trim(),
        cron: cron.trim() || '0 * * * *',
        prompt: prompt.trim(),
      });
      setName('');
      setPrompt('');
      setNewTaskDialogOpen(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={newTaskDialogOpen}
      onClose={() => setNewTaskDialogOpen(false)}
      title="新建计划任务 (Scheduled Task Dialog)"
      width={560}
    >
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
            任务名称
          </label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如: 每日凌晨回归测试巡检..."
            style={{
              width: '100%',
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-default)',
              fontSize: 13,
              color: 'var(--text-primary)',
            }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
            Cron 周期表达式 (5段标准格式)
          </label>
          <input
            type="text"
            required
            value={cron}
            onChange={(e) => setCron(e.target.value)}
            placeholder="例如: 0 2 * * * (每日凌晨2点)"
            style={{
              width: '100%',
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-default)',
              fontSize: 13,
              fontFamily: 'monospace',
              color: 'var(--text-primary)',
            }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
            执行任务提示词 (Prompt)
          </label>
          <textarea
            required
            rows={4}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="描述当调度触发时，智能体需要自动执行的研发任务与检查逻辑..."
            style={{
              width: '100%',
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-default)',
              fontSize: 13,
              color: 'var(--text-primary)',
              resize: 'vertical',
            }}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10 }}>
          <button
            type="button"
            onClick={() => setNewTaskDialogOpen(false)}
            style={{ padding: '7px 14px', borderRadius: 'var(--radius-sm)', color: 'var(--text-muted)', fontSize: 12.5 }}
          >
            取消
          </button>
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '7px 18px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--accent-primary)',
              color: '#fff',
              fontSize: 12.5,
              fontWeight: 600,
            }}
          >
            {loading ? '正在保存...' : '创建排期任务'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
