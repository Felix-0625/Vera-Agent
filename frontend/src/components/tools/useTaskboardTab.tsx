import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { archiveWorkItem, createWorkItem, fetchWorkItems, updateWorkItem } from '../../api/toolApi';
import { useChatStore } from '../../stores/chatStore';
import { useProjectStore } from '../../stores/projectStore';
import { WorkItem } from '../../types/tool';
import './taskboard.css';
import { COLUMNS, Draft, EMPTY_DRAFT, parseLabels, TaskboardTabProps } from './TaskboardTabParts';
export function useTaskboardTab({ projectId }: TaskboardTabProps) {
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
  const grouped = useMemo(
    () => new Map(COLUMNS.map((column) => [column.id, items.filter((item) => item.status === column.id)])),
    [items],
  );
  const saveItem = async (item: WorkItem, changes: Partial<WorkItem>): Promise<boolean> => {
    setBusyItemId(item.id);
    setError('');
    try {
      const { item: updated } = await updateWorkItem(item.id, { ...changes, version: item.version });
      setItems((current) => current.map((candidate) => (candidate.id === updated.id ? updated : candidate)));
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
        setItems((current) => current.map((candidate) => (candidate.id === linked.id ? linked : candidate)));
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
  return {
    projectId,
    project,
    activeThreadId,
    activeThread,
    items,
    loading,
    saving,
    busyItemId,
    error,
    setError,
    draft,
    setDraft,
    creating,
    setCreating,
    editing,
    setEditing,
    draggedId,
    setDraggedId,
    grouped,
    saveItem,
    submitDraft,
    startInAgent,
    linkCurrentThread,
    submitEdit,
    archiveItem,
  };
}
