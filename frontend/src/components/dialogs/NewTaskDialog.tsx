import React, { useState } from 'react';
import { createScheduledTask } from '../../api/toolApi';
import { useChatStore } from '../../stores/chatStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';
import { Button } from '../common/Button';
import { TextArea, TextInput } from '../common/Field';
import { Modal } from '../common/Modal';

export const NewTaskDialog: React.FC = () => {
  const { newTaskDialogOpen, newTaskPrompt, setNewTaskDialogOpen, setNewTaskPrompt } = useLayoutStore();
  const notifyTasksChanged = useLayoutStore((state) => state.notifyScheduledTasksChanged);
  const selectedModel = useChatStore((state) => state.selectedModel);
  const { activeThreadId, threads, draftProjectId } = useChatStore();
  const currentProject = useProjectStore((state) => state.currentProject);
  const [name, setName] = useState('');
  const [runAt, setRunAt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !newTaskPrompt.trim()) return;
    if (!selectedModel) {
      setError('请先在对话区选择一个模型。');
      return;
    }
    const scheduledDate = new Date(runAt);
    if (!runAt || Number.isNaN(scheduledDate.getTime()) || scheduledDate.getTime() <= Date.now()) {
      setError('请选择一个未来的执行时间。');
      return;
    }

    setLoading(true);
    setError('');
    try {
      await createScheduledTask({
        name: name.trim(),
        run_at: scheduledDate.toISOString(),
        prompt: newTaskPrompt.trim(),
        model_id: selectedModel,
        project_id:
          (activeThreadId
            ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id
            : draftProjectId) || currentProject?.id,
      });
      setName('');
      setRunAt('');
      notifyTasksChanged();
      setNewTaskDialogOpen(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '创建计划任务失败，请稍后重试。');
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
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3-5)' }}>
        {error && (
          <div role="alert" style={{ color: 'var(--accent-rose)', fontSize: 'var(--font-size-sm)' }}>
            {error}
          </div>
        )}
        <div>
          <label
            style={{
              display: 'block',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 600,
              color: 'var(--text-muted)',
              marginBottom: 'var(--space-1-5)',
            }}
          >
            任务名称
          </label>
          <TextInput
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如: 检查本次构建结果"
          />
        </div>

        <div>
          <label
            htmlFor="scheduled-task-run-at"
            style={{
              display: 'block',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 600,
              color: 'var(--text-muted)',
              marginBottom: 'var(--space-1-5)',
            }}
          >
            执行时间（本地时间，仅执行一次）
          </label>
          <TextInput
            id="scheduled-task-run-at"
            type="datetime-local"
            required
            value={runAt}
            onChange={(e) => {
              setRunAt(e.target.value);
              setError('');
            }}
            onInput={(e) => {
              setRunAt(e.currentTarget.value);
              setError('');
            }}
          />
        </div>

        <div>
          <label
            style={{
              display: 'block',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 600,
              color: 'var(--text-muted)',
              marginBottom: 'var(--space-1-5)',
            }}
          >
            执行任务提示词 (Prompt)
          </label>
          <TextArea
            required
            rows={4}
            value={newTaskPrompt}
            onChange={(e) => setNewTaskPrompt(e.target.value)}
            placeholder="描述到达指定时间后，智能体需要执行的任务..."
          />
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 'var(--space-2-5)',
            marginTop: 'var(--space-2-5)',
          }}
        >
          <Button type="button" onClick={() => setNewTaskDialogOpen(false)} variant="ghost" size="sm">
            取消
          </Button>
          <Button type="submit" disabled={loading} variant="primary" size="sm">
            {loading ? '正在保存...' : '创建定时任务'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
