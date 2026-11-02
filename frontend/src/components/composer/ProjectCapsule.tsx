import { Check, ChevronDown, Folder, FolderX, Plus, X } from 'lucide-react';
import React, { useMemo, useState } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';
import { Button } from '../common/Button';
import { IconButton } from '../common/IconButton';

const projectBlue = 'var(--accent-primary)';

export const ProjectCapsule: React.FC = () => {
  const { projectsHistory, bindProject } = useProjectStore();
  const { openProjectCreate } = useLayoutStore();
  const { draftProjectId, setDraftProjectId, loadThreads } = useChatStore();
  const [isOpen, setIsOpen] = useState(false);
  const projectMenuId = React.useId();
  const selectedProject = useMemo(
    () => projectsHistory.find((project) => project.id === draftProjectId) || null,
    [projectsHistory, draftProjectId],
  );

  const chooseProject = async (projectId: string | null, path?: string) => {
    setDraftProjectId(projectId);
    setIsOpen(false);
    if (path) {
      const project = projectsHistory.find((item) => item.id === projectId);
      await bindProject(
        path,
        project ? { projectId: project.id, name: project.name, folders: project.folders } : undefined,
      );
      await loadThreads();
    }
  };

  return (
    <div style={{ marginBottom: 'var(--space-2)', display: 'inline-block', position: 'relative' }}>
      <div className="project-capsule-wrap">
        <Button
          variant="outline"
          size="compact"
          className={`project-capsule-trigger${selectedProject ? ' is-bound' : ' is-unbound'}`}
          onClick={() => setIsOpen((value) => !value)}
          aria-haspopup="true"
          aria-expanded={isOpen}
          aria-controls={projectMenuId}
        >
          <Folder size={15} color={projectBlue} />
          <span>{selectedProject?.name || '选择项目'}</span>
          <ChevronDown size={13} className="project-capsule-chevron" />
        </Button>
        {selectedProject && (
          <IconButton
            className="project-capsule-clear"
            onClick={() => void chooseProject(null)}
            label="取消项目绑定"
            title="取消项目绑定"
            size="sm"
          >
            <X size={13} />
          </IconButton>
        )}
      </div>

      {isOpen && (
        <>
          <div style={{ position: 'fixed', inset: 0, zIndex: 998 }} onClick={() => setIsOpen(false)} />
          <div
            id={projectMenuId}
            role="group"
            aria-label="当前对话项目选择和操作"
            className="glass-panel animate-fade-in"
            style={{
              position: 'absolute',
              bottom: 'calc(100% + 8px)',
              left: 0,
              width: 278,
              maxWidth: 'calc(100vw - 24px)',
              borderRadius: 'var(--radius-md-wide)',
              backgroundColor: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-default)',
              boxShadow: 'var(--shadow-lg)',
              padding: 'var(--space-1-5)',
              zIndex: 999,
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-0-5)',
            }}
          >
            <div
              style={{
                padding: 'var(--space-1-25) var(--space-2) var(--space-1-75)',
                fontSize: 'var(--font-size-subtle)',
                fontWeight: 600,
                color: 'var(--text-muted)',
              }}
            >
              当前对话项目
            </div>
            <Button
              variant="ghost"
              size="md"
              onClick={() => void chooseProject(null)}
              aria-pressed={!draftProjectId}
              className="composer-menu-row"
              style={{
                minHeight: 40,
                borderRadius: 'var(--radius-md)',
                background: draftProjectId ? 'transparent' : 'var(--bg-accent-soft)',
              }}
            >
              <FolderX size={15} color={projectBlue} />
              <span>不绑定项目</span>
              <small style={{ color: 'var(--text-muted)' }}>最近会话</small>
              {!draftProjectId && <Check size={13} color={projectBlue} />}
            </Button>
            {projectsHistory.map((project) => {
              const selected = draftProjectId === project.id;
              return (
                <Button
                  key={project.id}
                  variant="ghost"
                  size="md"
                  onClick={() => void chooseProject(project.id, project.path)}
                  aria-pressed={selected}
                  className="composer-menu-row"
                  style={{ background: selected ? 'var(--bg-info-soft)' : undefined }}
                >
                  <Folder size={14} color={projectBlue} />
                  <span>{project.name}</span>
                  {selected && <Check size={13} color={projectBlue} />}
                </Button>
              );
            })}
            {projectsHistory.length === 0 && <div className="composer-menu-empty">尚未添加项目</div>}
            <div className="composer-menu-divider" />
            <Button
              variant="ghost"
              size="md"
              className="composer-menu-row"
              onClick={() => {
                setIsOpen(false);
                openProjectCreate();
              }}
            >
              <Plus size={14} color={projectBlue} />
              <span>新建项目并绑定文件夹…</span>
            </Button>
          </div>
        </>
      )}
    </div>
  );
};
