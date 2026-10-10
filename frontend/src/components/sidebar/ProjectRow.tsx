import React, { useEffect, useState } from 'react';
import { Folder, Plus, ChevronDown, ChevronRight, Pin, MoreVertical } from 'lucide-react';
import { Project } from '../../types/project';
import { Thread } from '../../types/chat';
import { useLayoutStore } from '../../stores/layoutStore';
import { useToolTabsStore } from '../../stores/toolTabsStore';
import { ProjectContextMenu } from './ProjectContextMenu';
import { InlineThreadRename } from './InlineThreadRename';

interface ProjectRowProps {
  project: Project;
  threads: Thread[];
  activeThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onNewDraftInProject: (projectId: string) => void;
  onContextMenu: (e: React.MouseEvent, thread: Thread) => void;
  onPinProject: (project: Project) => void;
  onEditProject: (project: Project) => void;
  onDeleteProject: (project: Project) => void;
  editingThreadId?: string | null;
  onRenameThread?: (thread: Thread, title: string | null) => Promise<void>;
}

/**
 * 侧边栏单个项目行与内嵌对话
 * 严格按照用户 Penpot 截图：
 * [📁] 项目名称         [+]
 *     对话        [📌] [...]
 */
export const ProjectRow: React.FC<ProjectRowProps> = ({
  project,
  threads,
  activeThreadId,
  onSelectThread,
  onNewDraftInProject,
  onContextMenu,
  onPinProject,
  onEditProject,
  onDeleteProject,
  editingThreadId = null,
  onRenameThread,
}) => {
  const { rightCollapsed, toggleRight, setProvisionGroupOpen } = useLayoutStore();
  const { openTab } = useToolTabsStore();

  const [isExpanded, setIsExpanded] = useState(true);
  const [limit, setLimit] = useState(5);
  const [menuPosition, setMenuPosition] = useState<{ left:number; top:number } | null>(null);
  useEffect(() => {
    if (!menuPosition) return;
    const close = () => setMenuPosition(null);
    document.addEventListener('pointerdown', close);
    document.addEventListener('keydown', close);
    window.addEventListener('resize', close);
    return () => { document.removeEventListener('pointerdown', close); document.removeEventListener('keydown', close); window.removeEventListener('resize', close); };
  }, [menuPosition]);
  const openMenu = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    const rect = event.currentTarget.getBoundingClientRect();
    setMenuPosition({ left:Math.min(rect.right-174,window.innerWidth-182), top:Math.min(rect.bottom+4,window.innerHeight-116) });
  };

  const visibleThreads = threads.slice(0, limit);
  const hasMore = threads.length > limit;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* 项目行 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 8px',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'rgba(255, 255, 255, 0.03)',
          color: 'var(--text-primary)',
          fontSize: 12.5,
          cursor: 'pointer',
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, overflow: 'hidden' }}>
          <span style={{ color: 'var(--text-muted)', display: 'inline-flex' }}>
            {isExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          </span>
          <Folder size={14} color="#4b91ff" />
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

        {/* 右侧动作按钮区：两个方框叠放 (创建分组) + '+' (新建对话) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <button onClick={openMenu} title="项目操作" aria-label={`${project.name} 项目操作`} aria-expanded={!!menuPosition} style={{ padding:3,borderRadius:3,color:'var(--text-muted)',display:'flex',alignItems:'center' }}><MoreVertical size={13}/></button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onNewDraftInProject(project.id);
              if (rightCollapsed) toggleRight();
              openTab('workflow', '分组管理', undefined, project.id);
              setProvisionGroupOpen(true);
            }}
            title="新建业务分组"
            style={{
              padding: 3,
              borderRadius: 3,
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
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
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onNewDraftInProject(project.id);
            }}
            title="在此项目中创建新对话"
            style={{
              padding: 3,
              borderRadius: 3,
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <Plus size={13} />
          </button>
        </div>
      </div>

      {/* 展开的对话列表 (前面无图标，缩进对齐截图) */}
      {isExpanded && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {visibleThreads.length === 0 ? (
            <div
              style={{
                padding: '4px 10px 4px 28px',
                fontSize: 11.5,
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
                  onClick={() => { if (editingThreadId !== t.thread_id) onSelectThread(t.thread_id); }}
                  onContextMenu={(e) => onContextMenu(e, t)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '5px 8px 5px 28px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: isActive ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
                    cursor: 'pointer',
                    fontSize: 12.5,
                    color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                    transition: 'background-color 0.1s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  {editingThreadId === t.thread_id && onRenameThread ? <InlineThreadRename title={t.title || '对话'} onSave={title => onRenameThread(t, title)} onCancel={() => onRenameThread(t, null)} /> : <span
                    style={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      flex: 1,
                      marginRight: 6,
                    }}
                  >
                    {t.title || '对话'}
                  </span>}

                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                    {t.is_pinned && <Pin size={11} color="var(--accent-amber)" />}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onContextMenu(e, t);
                      }}
                      style={{
                        padding: 2,
                        color: 'var(--text-muted)',
                        display: 'flex',
                        alignItems: 'center',
                        cursor: 'pointer',
                      }}
                      title="操作菜单"
                      onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
                    >
                      <MoreVertical size={13} />
                    </button>
                  </div>
                </div>
              );
            })
          )}

          {hasMore && (
            <button
              onClick={() => setLimit((prev) => prev + 5)}
              style={{
                padding: '4px 10px 6px 28px',
                fontSize: 11.5,
                color: 'var(--accent-primary)',
                textAlign: 'left',
                cursor: 'pointer',
                background: 'transparent',
                border: 'none',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.textDecoration = 'underline')}
              onMouseLeave={(e) => (e.currentTarget.style.textDecoration = 'none')}
            >
              展开更多 ({threads.length - limit} 条)
            </button>
          )}
        </div>
      )}
      {menuPosition && <ProjectContextMenu project={project} position={menuPosition} onClose={()=>setMenuPosition(null)} onPin={onPinProject} onEdit={onEditProject} onDelete={onDeleteProject} />}
    </div>
  );
};
