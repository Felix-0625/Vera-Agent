import { Archive, CheckSquare, CircleAlert, Clock3, LoaderCircle, MessageSquare, Play, Plus, X } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { WorkItemPriority, WorkItemStatus } from '../../types/tool';
import './taskboard.css';
import { COLUMNS, EMPTY_DRAFT, formatDate, PRIORITIES } from './TaskboardTabParts';
import { useTaskboardTab } from './useTaskboardTab';
export function TaskboardTabView({
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
}: ReturnType<typeof useTaskboardTab>) {
  if (!projectId) {
    return (
      <div className="taskboard-empty">
        <CheckSquare size={24} />
        <strong>先选择一个项目</strong>
        <span>任务看板按项目管理，请在左侧绑定或选择项目后打开。</span>
      </div>
    );
  }
  return (
    <section className="taskboard-panel" aria-label={`${project?.name || '项目'}任务看板`}>
      <header className="taskboard-header">
        <div className="taskboard-heading">
          <div className="taskboard-heading-icon">
            <CheckSquare size={17} />
          </div>
          <div>
            <h2>任务看板</h2>
            <p>
              {project?.name || '当前项目'} · {items.length} 项工作
            </p>
          </div>
        </div>
        <button
          className="taskboard-primary-button"
          type="button"
          onClick={() => {
            setDraft(EMPTY_DRAFT);
            setCreating(true);
          }}
        >
          <Plus size={15} />
          新建任务
        </button>
      </header>

      {error && (
        <div className="taskboard-error" role="alert">
          <CircleAlert size={15} />
          {error}
          <button type="button" onClick={() => setError('')} aria-label="关闭提示">
            <X size={13} />
          </button>
        </div>
      )}
      {loading ? (
        <div className="taskboard-loading">
          <LoaderCircle size={17} className="taskboard-spin" />
          加载任务…
        </div>
      ) : (
        <div className="taskboard-columns">
          {COLUMNS.map((column) => {
            const columnItems = grouped.get(column.id) || [];
            return (
              <section
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
                <header>
                  <span className="taskboard-column-dot" />
                  <h3>{column.title}</h3>
                  <span className="taskboard-column-count">{columnItems.length}</span>
                </header>
                <div className="taskboard-card-list">
                  {columnItems.map((item) => (
                    <article
                      className="taskboard-card"
                      key={item.id}
                      draggable
                      onDragStart={(event) => {
                        setDraggedId(item.id);
                        event.dataTransfer.setData('text/plain', item.id);
                      }}
                      onDragEnd={() => setDraggedId(null)}
                      onClick={() => {
                        setDraft({
                          title: item.title,
                          description: item.description,
                          priority: item.priority,
                          labels: item.labels.join(', '),
                        });
                        setEditing(item);
                      }}
                    >
                      <div className="taskboard-card-meta">
                        <span>{item.identifier}</span>
                        <span className={`taskboard-priority taskboard-priority--${item.priority}`}>
                          {PRIORITIES.find((value) => value.id === item.priority)?.title}
                        </span>
                      </div>
                      <h4>{item.title}</h4>
                      {item.description && <p className="taskboard-card-description">{item.description}</p>}
                      {item.labels.length > 0 && (
                        <div className="taskboard-labels">
                          {item.labels.map((label) => (
                            <span key={label}>{label}</span>
                          ))}
                        </div>
                      )}
                      <footer>
                        <span className="taskboard-card-date">
                          <Clock3 size={12} />
                          {formatDate(item.updated_at)}
                        </span>
                        <span className="taskboard-card-actions" onClick={(event) => event.stopPropagation()}>
                          {item.thread_id ? (
                            <button
                              type="button"
                              title="打开关联对话"
                              onClick={() => void useChatStore.getState().selectThread(item.thread_id!)}
                            >
                              <MessageSquare size={13} />
                            </button>
                          ) : activeThreadId && activeThread?.project_id === projectId ? (
                            <button type="button" title="关联当前对话" onClick={() => void linkCurrentThread(item)}>
                              <MessageSquare size={13} />
                            </button>
                          ) : null}
                          <button
                            type="button"
                            title="在 Agent 对话中处理"
                            disabled={busyItemId === item.id}
                            onClick={() => void startInAgent(item)}
                          >
                            <Play size={13} />
                          </button>
                          <button
                            type="button"
                            title="归档任务"
                            disabled={busyItemId === item.id}
                            onClick={() => void archiveItem(item)}
                          >
                            <Archive size={13} />
                          </button>
                        </span>
                      </footer>
                    </article>
                  ))}
                  {columnItems.length === 0 && <div className="taskboard-column-empty">拖动任务到此列，或新建任务</div>}
                </div>
              </section>
            );
          })}
        </div>
      )}

      {(creating || editing) && (
        <div
          className="taskboard-dialog-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setCreating(false);
              setEditing(null);
            }
          }}
        >
          <form className="taskboard-dialog" onSubmit={creating ? submitDraft : submitEdit}>
            <header>
              <div>
                <h3>{creating ? '新建项目任务' : `编辑 ${editing?.identifier || '任务'}`}</h3>
                <p>工作项属于项目；计划任务仍在侧边栏单独管理。</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setCreating(false);
                  setEditing(null);
                }}
                aria-label="关闭"
              >
                <X size={17} />
              </button>
            </header>
            <label>
              标题
              <input
                autoFocus
                maxLength={240}
                required
                value={draft.title}
                onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
              />
            </label>
            <label>
              说明
              <textarea
                maxLength={20_000}
                rows={5}
                value={draft.description}
                onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))}
              />
            </label>
            <div className="taskboard-dialog-row">
              <label>
                优先级
                <select
                  value={draft.priority}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, priority: event.target.value as WorkItemPriority }))
                  }
                >
                  {PRIORITIES.map((value) => (
                    <option key={value.id} value={value.id}>
                      {value.title}
                    </option>
                  ))}
                </select>
              </label>
              {!creating && editing && (
                <label>
                  状态
                  <select
                    value={editing.status}
                    onChange={(event) => setEditing({ ...editing, status: event.target.value as WorkItemStatus })}
                  >
                    {COLUMNS.map((value) => (
                      <option key={value.id} value={value.id}>
                        {value.title}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>
            <label>
              标签
              <input
                placeholder="逗号分隔，例如：前端, 优化"
                value={draft.labels}
                onChange={(event) => setDraft((current) => ({ ...current, labels: event.target.value }))}
              />
            </label>
            <footer>
              <button
                type="button"
                className="taskboard-secondary-button"
                onClick={() => {
                  setCreating(false);
                  setEditing(null);
                }}
              >
                取消
              </button>
              <button className="taskboard-primary-button" type="submit" disabled={saving || busyItemId !== null}>
                {saving ? '保存中…' : '保存任务'}
              </button>
            </footer>
          </form>
        </div>
      )}
    </section>
  );
}
