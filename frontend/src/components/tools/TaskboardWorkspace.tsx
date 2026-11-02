import { ArrowLeft, CheckSquare, FolderOpen, Plus } from 'lucide-react';
import React, { useMemo, useState } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';
import { TaskboardTab } from './TaskboardTab';
import './taskboard.css';

interface TaskboardWorkspaceProps {
  onClose: () => void;
}

export const TaskboardWorkspace: React.FC<TaskboardWorkspaceProps> = ({ onClose }) => {
  const projectsHistory = useProjectStore((state) => state.projectsHistory);
  const currentProject = useProjectStore((state) => state.currentProject);
  const openProjectCreate = useLayoutStore((state) => state.openProjectCreate);
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const activeThread = useChatStore((state) => state.threads.find((thread) => thread.thread_id === activeThreadId));
  const draftProjectId = useChatStore((state) => state.draftProjectId);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  const projects = useMemo(() => {
    if (!currentProject || projectsHistory.some((project) => project.id === currentProject.id)) return projectsHistory;
    return [currentProject, ...projectsHistory];
  }, [currentProject, projectsHistory]);

  const contextualProjectId = activeThread?.project_id || draftProjectId || currentProject?.id || null;

  const selectedProject = projects.find((project) => project.id === selectedProjectId);
  const contextualProject = projects.find((project) => project.id === contextualProjectId);
  const fallbackProject = projects.find((project) => project.id === currentProject?.id) || projects[0];
  const resolvedProjectId = selectedProject?.id || contextualProject?.id || fallbackProject?.id || null;

  return (
    <main className="taskboard-workspace" aria-label="任务面板">
      <header className="taskboard-workspace-header">
        <div className="taskboard-workspace-brand">
          <span className="taskboard-heading-icon">
            <CheckSquare size={17} />
          </span>
          <div>
            <h1>任务面板</h1>
            <p>按项目跟踪工作，并关联 Agent 对话</p>
          </div>
        </div>
        <div className="taskboard-workspace-actions">
          {projects.length > 0 ? (
            <label className="taskboard-project-select">
              <FolderOpen size={15} aria-hidden="true" />
              <select
                aria-label="选择任务面板项目"
                value={resolvedProjectId || ''}
                onChange={(event) => setSelectedProjectId(event.target.value || null)}
              >
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <button className="taskboard-secondary-button" type="button" onClick={openProjectCreate}>
              <Plus size={15} />
              绑定项目
            </button>
          )}
          <button className="taskboard-secondary-button" type="button" onClick={onClose}>
            <ArrowLeft size={15} />
            返回对话
          </button>
        </div>
      </header>
      {selectedProjectId ? (
        <TaskboardTab key={selectedProjectId} projectId={selectedProjectId} />
      ) : (
        <div className="taskboard-empty taskboard-no-project">
          <FolderOpen size={25} />
          <strong>先绑定一个项目</strong>
          <span>任务面板中的工作项属于项目，请绑定本地项目文件夹后开始管理。</span>
          <button className="taskboard-primary-button" type="button" onClick={openProjectCreate}>
            <Plus size={15} />
            绑定项目
          </button>
        </div>
      )}
    </main>
  );
};
