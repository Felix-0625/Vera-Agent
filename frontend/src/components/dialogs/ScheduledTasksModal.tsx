import { Plus, Search } from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';
import { deleteScheduledTask, fetchScheduledTasks, runScheduledTask, toggleScheduledTask } from '../../api/toolApi';
import { useLayoutStore } from '../../stores/layoutStore';
import { ScheduledTask } from '../../types/tool';
import { Button } from '../common/Button';
import { TextInput } from '../common/Field';
import { Modal } from '../common/Modal';
import { ScheduledTaskItem } from './ScheduledTaskItem';

export const ScheduledTasksModal: React.FC = () => {
  const { scheduledTasksOpen, scheduledTasksVersion, setScheduledTasksOpen, setNewTaskDialogOpen } = useLayoutStore();
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');

  const loadTasks = useCallback(async () => {
    try {
      const res = await fetchScheduledTasks();
      setTasks(res.tasks || []);
      setError('');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '加载计划任务失败。');
    }
  }, []);

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- Opening the dialog and task changes trigger an API refresh with loading/error feedback.
    if (scheduledTasksOpen) loadTasks();
  }, [scheduledTasksOpen, scheduledTasksVersion, loadTasks]);

  useEffect(() => {
    if (!scheduledTasksOpen || !tasks.some((task) => task.last_status === 'running')) return;
    const timer = window.setInterval(() => {
      void loadTasks();
    }, 2000);
    return () => window.clearInterval(timer);
  }, [scheduledTasksOpen, tasks, loadTasks]);

  const handleToggle = async (t: ScheduledTask) => {
    try {
      await toggleScheduledTask(t.id);
      await loadTasks();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '更新任务状态失败。');
    }
  };

  const handleRun = async (t: ScheduledTask) => {
    try {
      await runScheduledTask(t.id);
      await loadTasks();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '启动任务失败。');
    }
  };

  const handleDelete = async (t: ScheduledTask) => {
    if (window.confirm(`确定删除任务 "${t.name}" 吗？`)) {
      try {
        await deleteScheduledTask(t.id);
        await loadTasks();
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : '删除任务失败。');
      }
    }
  };

  const filtered = tasks.filter((t) => t.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <Modal isOpen={scheduledTasksOpen} onClose={() => setScheduledTasksOpen(false)} title="" width={720}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        {}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              定时任务
            </h2>
            <p
              style={{
                fontSize: 'var(--font-size-control)',
                color: 'var(--text-muted)',
                marginTop: 'var(--space-1)',
                marginBottom: 0,
              }}
            >
              任务会在指定的日期和时间自动运行一次
            </p>
          </div>

          <Button onClick={() => setNewTaskDialogOpen(true)} variant="primary" size="sm">
            <Plus size={14} />
            <span>新建任务</span>
          </Button>
        </div>

        {}
        <div style={{ position: 'relative' }}>
          <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: 11 }} />
          <TextInput
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索定时任务…"
            style={{ paddingLeft: 36 }}
          />
        </div>

        {error && (
          <div role="alert" style={{ color: 'var(--accent-rose)', fontSize: 'var(--font-size-sm)' }}>
            {error}
          </div>
        )}
        {}
        <div
          style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', maxHeight: 420, overflowY: 'auto' }}
        >
          {error && tasks.length === 0 ? null : filtered.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '48px var(--space-5)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
              }}
            >
              <div style={{ fontSize: 'var(--font-size-body)', fontWeight: 600, color: 'var(--text-primary)' }}>
                还没有定时任务
              </div>
              <div
                style={{
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--text-muted)',
                  marginTop: 'var(--space-1)',
                  maxWidth: 320,
                }}
              >
                创建一个任务，让 VeraAgent 在指定时间执行一次。
              </div>
              <Button
                onClick={() => setNewTaskDialogOpen(true)}
                variant="outline"
                size="sm"
                style={{
                  marginTop: 'var(--space-4)',
                  color: 'var(--accent-primary)',
                  borderColor: 'var(--accent-primary)',
                }}
              >
                <Plus size={13} />
                <span>新建任务</span>
              </Button>
            </div>
          ) : (
            filtered.map((t) => (
              <ScheduledTaskItem
                key={t.id}
                task={t}
                onRun={handleRun}
                onToggle={handleToggle}
                onDelete={handleDelete}
              />
            ))
          )}
        </div>
      </div>
    </Modal>
  );
};
