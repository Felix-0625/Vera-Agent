import React from 'react';
import { Clock, Play, Trash2 } from 'lucide-react';
import { ScheduledTask } from '../../types/tool';
import { Switch } from '../common/Switch';

interface ScheduledTaskItemProps {
  task: ScheduledTask;
  onRun: (t: ScheduledTask) => void;
  onToggle: (t: ScheduledTask) => void;
  onDelete: (t: ScheduledTask) => void;
}

/**
 * 单个计划任务卡片项
 */
export const ScheduledTaskItem: React.FC<ScheduledTaskItemProps> = ({
  task,
  onRun,
  onToggle,
  onDelete,
}) => {
  return (
    <div
      className="glass-card"
      style={{
        padding: '12px 14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <Clock size={16} color="var(--accent-amber)" />
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
            {task.name}
          </div>
          <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2 }}>
            周期: <code style={{ color: 'var(--accent-cyan)' }}>{task.cron}</code>
            {' · 提示词: '}{task.prompt}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <button
          onClick={() => onRun(task)}
          style={{
            padding: '4px 8px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'rgba(16,185,129,0.15)',
            color: 'var(--accent-emerald)',
            fontSize: 11.5,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
          title="立即触发一次"
        >
          <Play size={12} />
          <span>立即运行</span>
        </button>
        <Switch checked={task.enabled} onChange={() => onToggle(task)} />
        <button
          onClick={() => onDelete(task)}
          style={{ padding: 4, color: 'var(--accent-rose)' }}
          title="删除任务"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
};
