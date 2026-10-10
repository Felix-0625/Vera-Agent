import React, { useEffect, useState } from 'react';
import { Plus, Search } from 'lucide-react';
import { useLayoutStore } from '../../stores/layoutStore';
import { Modal } from '../common/Modal';
import { fetchScheduledTasks, toggleScheduledTask, runScheduledTask, deleteScheduledTask } from '../../api/toolApi';
import { ScheduledTask } from '../../types/tool';
import { ScheduledTaskItem } from './ScheduledTaskItem';

/**
 * 模态弹窗 3 - 定时任务
 * 严格按照 Penpot 原型 "Scheduled Tasks · 定时任务"
 */
export const ScheduledTasksModal: React.FC = () => {
  const { scheduledTasksOpen, setScheduledTasksOpen, setNewTaskDialogOpen } = useLayoutStore();
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [search, setSearch] = useState('');

  const loadTasks = async () => {
    try {
      const res = await fetchScheduledTasks();
      setTasks(res.tasks || []);
    } catch {
      // 保持静默
    }
  };

  useEffect(() => {
    if (scheduledTasksOpen) loadTasks();
  }, [scheduledTasksOpen]);

  const handleToggle = async (t: ScheduledTask) => {
    await toggleScheduledTask(t.id);
    loadTasks();
  };

  const handleRun = async (t: ScheduledTask) => {
    await runScheduledTask(t.id);
    alert(`任务 "${t.name}" 已手动触发执行！`);
    loadTasks();
  };

  const handleDelete = async (t: ScheduledTask) => {
    if (window.confirm(`确定删除任务 "${t.name}" 吗？`)) {
      await deleteScheduledTask(t.id);
      loadTasks();
    }
  };

  const filtered = tasks.filter((t) => t.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <Modal
      isOpen={scheduledTasksOpen}
      onClose={() => setScheduledTasksOpen(false)}
      title=""
      width={720}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* 顶部标题与新建按钮对齐 Penpot */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              定时任务
            </h2>
            <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 4, marginBottom: 0 }}>
              自动运行的任务会按计划启动
            </p>
          </div>

          <button
            onClick={() => setNewTaskDialogOpen(true)}
            style={{
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--accent-primary)',
              color: '#FFFFFF',
              fontSize: 12,
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <Plus size={14} />
            <span>新建任务</span>
          </button>
        </div>

        {/* 搜索框 */}
        <div style={{ position: 'relative' }}>
          <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: 11 }} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索定时任务…"
            style={{
              width: '100%',
              padding: '9px 12px 9px 36px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-default)',
              fontSize: 13,
              color: 'var(--text-primary)',
            }}
          />
        </div>

        {/* 任务列表或空态对齐 Penpot */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 420, overflowY: 'auto' }}>
          {filtered.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                还没有定时任务
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, maxWidth: 320 }}>
                创建一个计划，让 VeraAgent 按时为你完成重复工作。
              </div>
              <button
                onClick={() => setNewTaskDialogOpen(true)}
                style={{
                  marginTop: 16,
                  padding: '6px 14px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(124, 58, 237, 0.15)',
                  border: '1px solid var(--accent-primary)',
                  color: 'var(--accent-primary)',
                  fontSize: 12.5,
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <Plus size={13} />
                <span>新建任务</span>
              </button>
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
