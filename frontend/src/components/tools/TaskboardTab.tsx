import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Archive, CheckSquare, CircleAlert, Clock3, LoaderCircle, MessageSquare, Play, Plus, X } from 'lucide-react';
import { archiveWorkItem, createWorkItem, fetchWorkItems, updateWorkItem } from '../../api/toolApi';
import { useChatStore } from '../../stores/chatStore';
import { useProjectStore } from '../../stores/projectStore';
import { WorkItem, WorkItemPriority, WorkItemStatus } from '../../types/tool';
import './taskboard.css';

const COLUMNS: Array<{ id: WorkItemStatus; title: string }> = [
  { id: 'backlog', title: '待规划' },
  { id: 'todo', title: '待办' },
  { id: 'in_progress', title: '进行中' },
  { id: 'blocked', title: '受阻' },
  { id: 'in_review', title: '待确认' },
  { id: 'done', title: '已完成' },
  { id: 'canceled', title: '已取消' },
];

const PRIORITIES: Array<{ id: WorkItemPriority; title: string }> = [
  { id: 'urgent', title: '紧急' },
  { id: 'high', title: '高' },
  { id: 'medium', title: '普通' },
  { id: 'low', title: '低' },
  { id: 'none', title: '无' },
];

interface TaskboardTabProps {
  projectId: string | null;
}

interface Draft {
  title: string;
  description: string;
  priority: WorkItemPriority;
  labels: string;
}

const EMPTY_DRAFT: Draft = { title: '', description: '', priority: 'medium', labels: '' };

function parseLabels(value: string): string[] | null {
  const labels = [...new Set(value.split(',').map((label) => label.trim()).filter(Boolean))];
  return labels.length <= 20 && labels.every((label) => label.length <= 48) ? labels : null;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric' }).format(new Date(value));
}

export const TaskboardTab: React.FC<TaskboardTabProps> = ({ projectId }) => {
  const project = useProjectStore((state) => state.projectsHistory.find((item) => item.id === projectId));
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const activeThread = useChatStore((state) => state.threads.find((thread) => thread.thread_id === activeThreadId));
  const selectedModel = useChatStore((state) => state.selectedModel);
  const [items, setItems] = useState<WorkItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [busyItemId, setBusyItemId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<WorkItem | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);

  const loadItems = useCallback(async () => {
    if (!projectId) {
      setItems([]);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const result = await fetchWorkItems(projectId);
      setItems(result.items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : '任务看板加载失败');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- Project selection is the boundary for loading that project's task items.
    void loadItems();
  }, [loadItems]);

  const grouped = useMemo(() => new Map(
    COLUMNS.map((column) => [column.id, items.filter((item) => item.status === column.id)]),
  ), [items]);

  const saveItem = async (item: WorkItem, changes: Partial<WorkItem>): Promise<boolean> => {
    setBusyItemId(item.id);
    setError('');
    try {
      const { item: updated } = await updateWorkItem(item.id, { ...changes, version: item.version });
      setItems((current) => current.map((candidate) => candidate.id === updated.id ? updated : candidate));
      return true;
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : '任务保存失败，请刷新后重试');
      if (saveError instanceof Error && saveError.message.toLowerCase().includes('changed')) void loadItems();
      return false;
    } finally {
      setBusyItemId(null);
    }
  };

  const submitDraft = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!projectId || !draft.title.trim()) return;
    setSaving(true);
    setError('');
    try {
      const labels = parseLabels(draft.labels);
      if (!labels) {
        setError('最多添加 20 个标签，每个标签不超过 48 个字符。');
        return;
      }
      const { item } = await createWorkItem({
        project_id: projectId,
        title: draft.title.trim(),
        description: draft.description.trim(),
        priority: draft.priority,
        labels,
      });
      setItems((current) => [...current, item]);
      setDraft(EMPTY_DRAFT);
      setCreating(false);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : '创建任务失败');
    } finally {
      setSaving(false);
    }
  };

  const startInAgent = async (item: WorkItem) => {
    if (!projectId || !selectedModel) {
      setError('请先在对话输入框选择模型，再启动 Agent 处理任务。');
      return;
    }
    setBusyItemId(item.id);
    setError('');
    try {
      let threadId = item.thread_id;
      const chat = useChatStore.getState();
      if (threadId) {
        await chat.selectThread(threadId);
      } else {
        threadId = await chat.newThread(`任务 · ${item.identifier} ${item.title}`, undefined, projectId);
      }
      const changes: Partial<WorkItem> = {};
      if (!item.thread_id) changes.thread_id = threadId;
      if (item.status === 'todo' || item.status === 'backlog') changes.status = 'in_progress';
      if (Object.keys(changes).length > 0) {
        const { item: linked } = await updateWorkItem(item.id, { ...changes, version: item.version });
        setItems((current) => current.map((candidate) => candidate.id === linked.id ? linked : candidate));
      }
      const prompt = [
        `请处理项目工作项 ${item.identifier}：${item.title}`,
        item.description.trim() ? `\n任务说明：\n${item.description.trim()}` : '',
        '\n请先阅读项目规则并检查相关代码，再按项目现有方式完成任务。完成后总结改动和验证结果；不要自行将看板任务标记为已完成。',
      ].join('');
      await useChatStore.getState().sendMessage(prompt);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : '启动 Agent 任务失败');
    } finally {
      setBusyItemId(null);
      void loadItems();
    }
  };

  const linkCurrentThread = async (item: WorkItem) => {
    if (!activeThreadId || activeThread?.project_id !== projectId) return;
    await saveItem(item, { thread_id: activeThreadId });
  };

  const submitEdit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!editing) return;
    const labels = parseLabels(draft.labels);
    if (!labels) {
      setError('最多添加 20 个标签，每个标签不超过 48 个字符。');
      return;
    }
    const saved = await saveItem(editing, {
      title: draft.title,
      description: draft.description,
      priority: draft.priority,
      status: editing.status,
      labels,
    });
    if (saved) setEditing(null);
  };

  const archiveItem = async (item: WorkItem) => {
    setBusyItemId(item.id);
    try {
      await archiveWorkItem(item.id);
      setItems((current) => current.filter((candidate) => candidate.id !== item.id));
    } catch (archiveError) {
      setError(archiveError instanceof Error ? archiveError.message : '归档任务失败');
    } finally {
      setBusyItemId(null);
    }
  };

  if (!projectId) {
    return <div className="taskboard-empty"><CheckSquare size={24} /><strong>先选择一个项目</strong><span>任务看板按项目管理，请在左侧绑定或选择项目后打开。</span></div>;
  }

  return (
    <section className="taskboard-panel" aria-label={`${project?.name || '项目'}任务看板`}>
      <header className="taskboard-header">
        <div className="taskboard-heading">
          <div className="taskboard-heading-icon"><CheckSquare size={17} /></div>
          <div><h2>任务看板</h2><p>{project?.name || '当前项目'} · {items.length} 项工作</p></div>
        </div>
        <button className="taskboard-primary-button" type="button" onClick={() => { setDraft(EMPTY_DRAFT); setCreating(true); }}><Plus size={15} />新建任务</button>
      </header>

      {error && <div className="taskboard-error" role="alert"><CircleAlert size={15} />{error}<button type="button" onClick={() => setError('')} aria-label="关闭提示"><X size={13} /></button></div>}
      {loading ? <div className="taskboard-loading"><LoaderCircle size={17} className="taskboard-spin" />加载任务…</div> : (
        <div className="taskboard-columns">
          {COLUMNS.map((column) => {
            const columnItems = grouped.get(column.id) || [];
            return <section
              className={`taskboard-column taskboard-column--${column.id}${draggedId ? ' is-dragging' : ''}`}
              key={column.id}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                const id = event.dataTransfer.getData('text/plain') || draggedId;
                const item = items.find((candidate) => candidate.id === id);
                if (item && item.status !== column.id) void saveItem(item, { status: column.id });
                setDraggedId(null);
              }}
            >
              <header><span className="taskboard-column-dot" /><h3>{column.title}</h3><span className="taskboard-column-count">{columnItems.length}</span></header>
              <div className="taskboard-card-list">
                {columnItems.map((item) => (
                  <article
                    className="taskboard-card"
                    key={item.id}
                    draggable
                    onDragStart={(event) => { setDraggedId(item.id); event.dataTransfer.setData('text/plain', item.id); }}
                    onDragEnd={() => setDraggedId(null)}
                    onClick={() => { setDraft({ title: item.title, description: item.description, priority: item.priority, labels: item.labels.join(', ') }); setEditing(item); }}
                  >
                    <div className="taskboard-card-meta"><span>{item.identifier}</span><span className={`taskboard-priority taskboard-priority--${item.priority}`}>{PRIORITIES.find((value) => value.id === item.priority)?.title}</span></div>
                    <h4>{item.title}</h4>
                    {item.description && <p className="taskboard-card-description">{item.description}</p>}
                    {item.labels.length > 0 && <div className="taskboard-labels">{item.labels.map((label) => <span key={label}>{label}</span>)}</div>}
                    <footer>
                      <span className="taskboard-card-date"><Clock3 size={12} />{formatDate(item.updated_at)}</span>
                      <span className="taskboard-card-actions" onClick={(event) => event.stopPropagation()}>
                        {item.thread_id ? <button type="button" title="打开关联对话" onClick={() => void useChatStore.getState().selectThread(item.thread_id!)}><MessageSquare size={13} /></button> : activeThreadId && activeThread?.project_id === projectId ? <button type="button" title="关联当前对话" onClick={() => void linkCurrentThread(item)}><MessageSquare size={13} /></button> : null}
                        <button type="button" title="在 Agent 对话中处理" disabled={busyItemId === item.id} onClick={() => void startInAgent(item)}><Play size={13} /></button>
                        <button type="button" title="归档任务" disabled={busyItemId === item.id} onClick={() => void archiveItem(item)}><Archive size={13} /></button>
                      </span>
                    </footer>
                  </article>
                ))}
                {columnItems.length === 0 && <div className="taskboard-column-empty">拖动任务到此列，或新建任务</div>}
              </div>
            </section>;
          })}
        </div>
      )}

      {(creating || editing) && <div className="taskboard-dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) { setCreating(false); setEditing(null); } }}>
        <form className="taskboard-dialog" onSubmit={creating ? submitDraft : submitEdit}>
          <header><div><h3>{creating ? '新建项目任务' : `编辑 ${editing?.identifier || '任务'}`}</h3><p>工作项属于项目；计划任务仍在侧边栏单独管理。</p></div><button type="button" onClick={() => { setCreating(false); setEditing(null); }} aria-label="关闭"><X size={17} /></button></header>
          <label>标题<input autoFocus maxLength={240} required value={draft.title} onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))} /></label>
          <label>说明<textarea maxLength={20_000} rows={5} value={draft.description} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} /></label>
          <div className="taskboard-dialog-row">
            <label>优先级<select value={draft.priority} onChange={(event) => setDraft((current) => ({ ...current, priority: event.target.value as WorkItemPriority }))}>{PRIORITIES.map((value) => <option key={value.id} value={value.id}>{value.title}</option>)}</select></label>
            {!creating && editing && <label>状态<select value={editing.status} onChange={(event) => setEditing({ ...editing, status: event.target.value as WorkItemStatus })}>{COLUMNS.map((value) => <option key={value.id} value={value.id}>{value.title}</option>)}</select></label>}
          </div>
          <label>标签<input placeholder="逗号分隔，例如：前端, 优化" value={draft.labels} onChange={(event) => setDraft((current) => ({ ...current, labels: event.target.value }))} /></label>
          <footer><button type="button" className="taskboard-secondary-button" onClick={() => { setCreating(false); setEditing(null); }}>取消</button><button className="taskboard-primary-button" type="submit" disabled={saving || busyItemId !== null}>{saving ? '保存中…' : '保存任务'}</button></footer>
        </form>
      </div>}
    </section>
  );
};
