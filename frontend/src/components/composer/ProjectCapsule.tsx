import React, { useMemo, useState } from 'react';
import { Check, ChevronDown, Folder, FolderX, FolderPlus, Plus, X } from 'lucide-react';
import { useProjectStore } from '../../stores/projectStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { useChatStore } from '../../stores/chatStore';

const projectBlue = '#4b91ff';

export const ProjectCapsule: React.FC = () => {
  const { projectsHistory, bindProject } = useProjectStore();
  const { openProjectCreate } = useLayoutStore();
  const { draftProjectId, setDraftProjectId, loadThreads } = useChatStore();
  const [isOpen, setIsOpen] = useState(false);
  const selectedProject = useMemo(() => projectsHistory.find((project) => project.id === draftProjectId) || null, [projectsHistory, draftProjectId]);

  const chooseProject = async (projectId: string | null, path?: string) => {
    setDraftProjectId(projectId);
    setIsOpen(false);
    if (path) {
      const project = projectsHistory.find(item => item.id === projectId);
      await bindProject(path, project ? { projectId: project.id, name: project.name, folders: project.folders } : undefined);
      await loadThreads();
    }
  };

  return (
    <div style={{ marginBottom: 8, display: 'inline-block', position: 'relative' }}>
      <div className="project-capsule-wrap">
        <button className={`project-capsule-trigger${selectedProject ? ' is-bound' : ' is-unbound'}`} onClick={() => setIsOpen((value) => !value)} aria-haspopup="listbox" aria-expanded={isOpen}>
          <Folder size={15} color={projectBlue} />
          <span>{selectedProject?.name || '选择项目'}</span>
          <ChevronDown size={13} className="project-capsule-chevron" />
        </button>
        {selectedProject && <button className="project-capsule-clear" onClick={() => void chooseProject(null)} aria-label="取消项目绑定" title="取消项目绑定"><X size={13} /></button>}
      </div>

      {isOpen && (
        <>
          <div style={{ position: 'fixed', inset: 0, zIndex: 998 }} onClick={() => setIsOpen(false)} />
          <div role="listbox" className="glass-panel animate-fade-in" style={{ position: 'absolute', bottom: 'calc(100% + 8px)', left: 0, width: 278, maxWidth: 'calc(100vw - 24px)', borderRadius: 10, backgroundColor: '#171b24', border: '1px solid rgba(148,163,184,.16)', boxShadow: '0 14px 32px rgba(0,0,0,.42)', padding: 6, zIndex: 999, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <div style={{ padding: '5px 8px 7px', fontSize: 10.5, fontWeight: 600, color: 'var(--text-muted)' }}>当前对话项目</div>
            <button onClick={() => void chooseProject(null)} className="composer-menu-row" style={{ minHeight:40, borderRadius:8, background: draftProjectId ? 'transparent' : 'rgba(75,145,255,.11)' }}>
              <FolderX size={15} color={projectBlue} />
              <span>不绑定项目</span><small style={{ color: 'var(--text-muted)' }}>最近会话</small>
              {!draftProjectId && <Check size={13} color={projectBlue} />}
            </button>
            {projectsHistory.map((project) => {
              const selected = draftProjectId === project.id;
              return <button key={project.id} onClick={() => void chooseProject(project.id, project.path)} className="composer-menu-row" style={{ background: selected ? 'rgba(6,182,212,.1)' : undefined }}>
                <Folder size={14} color={projectBlue} /><span>{project.name}</span>{selected && <Check size={13} color={projectBlue} />}
              </button>;
            })}
            {projectsHistory.length === 0 && <div className="composer-menu-empty">尚未添加项目</div>}
            <div className="composer-menu-divider" />
            <button className="composer-menu-row" onClick={() => { setIsOpen(false); openProjectCreate(); }}><Plus size={14} color={projectBlue} /><span>新建项目并绑定文件夹…</span></button>
          </div>
        </>
      )}
    </div>
  );
};
