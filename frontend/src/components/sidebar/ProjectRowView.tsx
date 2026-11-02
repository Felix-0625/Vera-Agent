import { Folder, FolderOpen, GitFork, Layers3, MoreVertical, Network, Pencil, Pin, Plus, Workflow } from 'lucide-react';
import { IconButton } from '../common/IconButton';
import { InlineThreadRename } from './InlineThreadRename';
import { ProjectContextMenu } from './ProjectContextMenu';
import { useProjectRow } from './useProjectRow';
export function ProjectRowView({
  project,
  threads,
  activeThreadId,
  onSelectThread,
  onNewDraftInProject,
  onContextMenu,
  onPinProject,
  onEditProject,
  onDeleteProject,
  editingThreadId,
  onRenameThread,
  rightCollapsed,
  toggleRight,
  openTab,
  isExpanded,
  setIsExpanded,
  limit,
  setLimit,
  projectGroups,
  expandedGroups,
  setExpandedGroups,
  groupThreadLimits,
  setGroupThreadLimits,
  menuPosition,
  setMenuPosition,
  openMenu,
  ordinaryThreads,
  editGroupInstance,
  visibleThreads,
  hasMore,
}: ReturnType<typeof useProjectRow>) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-0-5)' }}>
      {}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 'var(--space-1-5) var(--space-2)',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'var(--bg-interactive-hover)',
          color: 'var(--text-primary)',
          fontSize: 'var(--font-size-control)',
          cursor: 'pointer',
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1-75)', overflow: 'hidden' }}>
          <span
            title={isExpanded ? '收起项目' : '展开项目'}
            style={{ color: 'var(--text-muted)', display: 'inline-flex' }}
          >
            {isExpanded ? (
              <FolderOpen size={15} color="var(--accent-primary)" />
            ) : (
              <Folder size={14} color="var(--accent-primary)" />
            )}
          </span>
          <span
            style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontWeight: 500,
            }}
          >
            {project.name || '项目名称'}
          </span>
        </div>

        {}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-0-5)' }}>
          <IconButton onClick={openMenu} label={`${project.name} 项目操作`} aria-expanded={!!menuPosition} size="sm">
            <MoreVertical size={13} />
          </IconButton>
          <IconButton
            onClick={(e) => {
              e.stopPropagation();
              if (rightCollapsed) toggleRight();
              openTab('workflow', '流程编排', undefined, project.id);
            }}
            label={`${project.name} 项目流程编排`}
            size="sm"
          >
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="7" y="7" width="13" height="13" rx="2" ry="2" />
              <path d="M4 17V5a2 2 0 0 1 2-2h12" />
            </svg>
          </IconButton>

          <IconButton
            onClick={(e) => {
              e.stopPropagation();
              onNewDraftInProject(project.id);
            }}
            label={`在 ${project.name} 中新建对话`}
            size="sm"
          >
            <Plus size={13} />
          </IconButton>
        </div>
      </div>

      {}
      {isExpanded && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {projectGroups.map((group) => {
            const groupThreads = threads.filter((thread) => thread.group_id === group.group_id);
            const groupLimit = groupThreadLimits[group.group_id] || 5;
            const expanded = expandedGroups[group.group_id] ?? true;
            const GroupIcon = group.group_mode === 'architecture' ? Layers3 : Workflow;
            const CollapsedGroupIcon = group.group_mode === 'architecture' ? Network : GitFork;
            return (
              <div
                key={group.group_id}
                style={{
                  margin: 'var(--space-0-75) 0',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-1-5)',
                    padding: 'var(--space-1-75) var(--space-2) var(--space-1-75) 25px',
                    minWidth: 0,
                  }}
                >
                  <IconButton
                    label={expanded ? `折叠${group.name}` : `展开${group.name}`}
                    onClick={() => setExpandedGroups((current) => ({ ...current, [group.group_id]: !expanded }))}
                    size="sm"
                    style={{
                      color: group.group_mode === 'architecture' ? 'var(--accent-emerald)' : 'var(--accent-primary)',
                    }}
                  >
                    {expanded ? <GroupIcon size={14} /> : <CollapsedGroupIcon size={14} />}
                  </IconButton>
                  <button
                    onClick={() => setExpandedGroups((current) => ({ ...current, [group.group_id]: !expanded }))}
                    title={group.name}
                    style={{
                      flex: 1,
                      minWidth: 0,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      textAlign: 'left',
                      fontSize: 'var(--font-size-label)',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    {group.name}
                  </button>
                  <IconButton onClick={() => editGroupInstance(group)} label={`编辑${group.name}`} size="sm">
                    <Pencil size={11} />
                  </IconButton>
                </div>
                {expanded && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 1, paddingBottom: 'var(--space-0-75)' }}>
                    {groupThreads.slice(0, groupLimit).map((thread) => {
                      const isActive = activeThreadId === thread.thread_id;
                      return (
                        <div
                          key={thread.thread_id}
                          className={`sidebar-thread-row${isActive ? ' is-active' : ''}`}
                          onClick={() => {
                            if (editingThreadId !== thread.thread_id) onSelectThread(thread.thread_id);
                          }}
                          onContextMenu={(event) => onContextMenu(event, thread)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: 'var(--space-1-25) var(--space-1-75) var(--space-1-25) 48px',
                            borderRadius: 'var(--radius-sm)',
                            cursor: 'pointer',
                            fontSize: 'var(--font-size-label)',
                            color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                          }}
                        >
                          {editingThreadId === thread.thread_id && onRenameThread ? (
                            <InlineThreadRename
                              title={thread.title || '对话窗口'}
                              onSave={(title) => onRenameThread(thread, title)}
                              onCancel={() => onRenameThread(thread, null)}
                            />
                          ) : (
                            <span
                              style={{
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                                flex: 1,
                                marginRight: 'var(--space-1-25)',
                              }}
                            >
                              {thread.title || '对话窗口'}
                            </span>
                          )}
                          <IconButton
                            onClick={(event) => {
                              event.stopPropagation();
                              onContextMenu(event, thread);
                            }}
                            label={`${thread.title || '对话'} 操作菜单`}
                            size="sm"
                          >
                            <MoreVertical size={12} />
                          </IconButton>
                        </div>
                      );
                    })}
                    {groupThreads.length === 0 && (
                      <div
                        style={{
                          padding: 'var(--space-1) var(--space-2) var(--space-1-25) 48px',
                          fontSize: 'var(--font-size-subtle)',
                          color: 'var(--text-disabled)',
                        }}
                      >
                        尚无运行会话
                      </div>
                    )}
                    {groupThreads.length > groupLimit && (
                      <button
                        onClick={() =>
                          setGroupThreadLimits((current) => ({ ...current, [group.group_id]: groupLimit + 5 }))
                        }
                        style={{
                          padding: 'var(--space-1) var(--space-2) var(--space-1-25) 48px',
                          textAlign: 'left',
                          fontSize: 'var(--font-size-subtle)',
                          color: 'var(--accent-primary)',
                        }}
                      >
                        展开更多（{groupThreads.length - groupLimit}）
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {ordinaryThreads.length === 0 && projectGroups.length === 0 ? (
            <div
              style={{
                padding: 'var(--space-1) var(--space-2-5) var(--space-1) 28px',
                fontSize: 'var(--font-size-label)',
                color: 'var(--text-disabled)',
              }}
            >
              暂无对话
            </div>
          ) : (
            visibleThreads.map((t) => {
              const isActive = activeThreadId === t.thread_id;
              return (
                <div
                  key={t.thread_id}
                  onClick={() => {
                    if (editingThreadId !== t.thread_id) onSelectThread(t.thread_id);
                  }}
                  onContextMenu={(e) => onContextMenu(e, t)}
                  className={`sidebar-thread-row${isActive ? ' is-active' : ''}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: 'var(--space-1-25) var(--space-2) var(--space-1-25) 28px',
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                    fontSize: 'var(--font-size-control)',
                    color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  }}
                >
                  {editingThreadId === t.thread_id && onRenameThread ? (
                    <InlineThreadRename
                      title={t.title || '对话'}
                      onSave={(title) => onRenameThread(t, title)}
                      onCancel={() => onRenameThread(t, null)}
                    />
                  ) : (
                    <span
                      style={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        flex: 1,
                        marginRight: 'var(--space-1-5)',
                      }}
                    >
                      {t.title || '对话'}
                    </span>
                  )}

                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', flexShrink: 0 }}>
                    {t.is_pinned && <Pin size={11} color="var(--accent-amber)" />}
                    <IconButton
                      onClick={(e) => {
                        e.stopPropagation();
                        onContextMenu(e, t);
                      }}
                      label={`${t.title || '对话'} 操作菜单`}
                      size="sm"
                    >
                      <MoreVertical size={13} />
                    </IconButton>
                  </div>
                </div>
              );
            })
          )}

          {hasMore && (
            <button
              onClick={() => setLimit((prev) => prev + 5)}
              style={{
                padding: 'var(--space-1) var(--space-2-5) var(--space-1-5) 28px',
                fontSize: 'var(--font-size-label)',
                color: 'var(--accent-primary)',
                textAlign: 'left',
                cursor: 'pointer',
                background: 'transparent',
                border: 'none',
              }}
              className="sidebar-expand-more"
            >
              展开更多 ({threads.length - limit} 条)
            </button>
          )}
        </div>
      )}
      {menuPosition && (
        <ProjectContextMenu
          project={project}
          position={menuPosition}
          onClose={() => setMenuPosition(null)}
          onPin={onPinProject}
          onEdit={onEditProject}
          onDelete={onDeleteProject}
        />
      )}
    </div>
  );
}
