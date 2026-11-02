import { Clock, Play, Trash2 } from 'lucide-react';
import React from 'react';
import { ScheduledTask } from '../../types/tool';
import { Button } from '../common/Button';
import { IconButton } from '../common/IconButton';
import { Switch } from '../common/Switch';

interface ScheduledTaskItemProps {
  task: ScheduledTask;
  onRun: (t: ScheduledTask) => void;
  onToggle: (t: ScheduledTask) => void;
  onDelete: (t: ScheduledTask) => void;
}

export const ScheduledTaskItem: React.FC<ScheduledTaskItemProps> = ({ task, onRun, onToggle, onDelete }) => {
  const runAt = new Date(task.run_at || '');
  const hasFixedSchedule = !Number.isNaN(runAt.getTime());
  const scheduleLabel = !hasFixedSchedule
    ? '旧版周期任务已停用，请删除并按固定时间重新创建'
    : `执行时间：${runAt.toLocaleString()}`;
  return (
    <div
      className="glass-card"
      style={{
        padding: 'var(--space-3) var(--space-3-5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        <Clock size={16} color="var(--accent-amber)" />
        <div>
          <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 600, color: 'var(--text-primary)' }}>
            {task.name}
          </div>
          <div
            style={{ fontSize: 'var(--font-size-label)', color: 'var(--text-muted)', marginTop: 'var(--space-0-5)' }}
          >
            {scheduleLabel}
            {' · 提示词: '}
            {task.prompt}
          </div>
          <div
            style={{
              fontSize: 'var(--font-size-compact)',
              color:
                task.last_status === 'failed' || task.last_status === 'approval_required'
                  ? 'var(--accent-rose)'
                  : 'var(--text-muted)',
              marginTop: 'var(--space-0-75)',
            }}
          >
            {task.last_status === 'running'
              ? '正在执行…'
              : task.last_status === 'success'
                ? '最近执行成功'
                : task.last_status === 'failed'
                  ? '最近执行失败'
                  : task.last_status === 'approval_required'
                    ? '需要审批的操作已停止'
                    : '尚未执行'}
            {task.last_error ? ` · ${task.last_error}` : ''}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)' }}>
        <Button
          onClick={() => onRun(task)}
          disabled={task.last_status === 'running' || !hasFixedSchedule}
          variant="secondary"
          size="sm"
          style={{ color: 'var(--accent-emerald)', borderColor: 'var(--border-success-soft)' }}
          title="立即触发一次"
        >
          <Play size={12} />
          <span>立即运行</span>
        </Button>
        <Switch
          label={`启用计划任务：${task.name}`}
          checked={hasFixedSchedule && task.enabled}
          disabled={!hasFixedSchedule}
          onChange={() => onToggle(task)}
        />
        <IconButton label="删除任务" onClick={() => onDelete(task)} tone="danger" size="sm">
          <Trash2 size={14} />
        </IconButton>
      </div>
    </div>
  );
};
