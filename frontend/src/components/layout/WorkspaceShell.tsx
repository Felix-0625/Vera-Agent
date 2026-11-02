import React, { useEffect } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';
import { useRightSidebarLayout } from '../../stores/rightSidebarLayout';
import { CenterWorkspace } from '../composer/CenterWorkspace';
import { LeftSidebar } from '../sidebar/LeftSidebar';
import { RightToolsContainer } from '../tools/RightToolsContainer';
import { TaskboardWorkspace } from '../tools/TaskboardWorkspace';
import { ResizeHandle } from './ResizeHandle';

// Modals
import { HistoryModal } from '../dialogs/HistoryModal';
import { McpManualConfigDialog } from '../dialogs/McpManualConfigDialog';
import { ModelConfigDialog } from '../dialogs/ModelConfigDialog';
import { NewTaskDialog } from '../dialogs/NewTaskDialog';
import { ProjectSelectorModal } from '../dialogs/ProjectSelectorModal';
import { ScheduledTasksModal } from '../dialogs/ScheduledTasksModal';
import { SettingsModal } from '../dialogs/SettingsModal';
import { WorkflowTemplatesModal } from '../dialogs/WorkflowTemplatesModal';

export const WorkspaceShell: React.FC = () => {
  const { leftCollapsed, leftWidth, setLeftWidth, toggleLeft, taskboardOpen, setTaskboardOpen } = useLayoutStore();
  const { rightCollapsed, rightWidth, setRightWidth, toggleRight, rightMaximized } = useRightSidebarLayout();

  const { loadCurrentProject, loadProjectsHistory, loadGroups } = useProjectStore();
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const { loadThreads } = useChatStore();
  const previousThreadId = React.useRef(activeThreadId);

  useEffect(() => {
    loadCurrentProject();
    loadProjectsHistory();
    loadGroups();
    loadThreads();
  }, [loadCurrentProject, loadProjectsHistory, loadGroups, loadThreads]);

  useEffect(() => {
    if (previousThreadId.current !== activeThreadId && taskboardOpen) setTaskboardOpen(false);
    previousThreadId.current = activeThreadId;
  }, [activeThreadId, setTaskboardOpen, taskboardOpen]);

  const handleResizeLeft = (deltaX: number) => {
    const winWidth = window.innerWidth;
    const newWidth = leftWidth + deltaX;
    const ratio = newWidth / winWidth;

    if (ratio < 0.15) {
      if (!leftCollapsed) toggleLeft();
    } else if (ratio <= 0.4) {
      if (leftCollapsed) toggleLeft();
      setLeftWidth(newWidth);
    }
  };

  const handleResizeRight = (deltaX: number) => {
    const winWidth = window.innerWidth;
    const newWidth = rightWidth + deltaX;
    const ratio = newWidth / winWidth;

    if (ratio < 0.15) {
      if (!rightCollapsed) toggleRight();
    } else if (ratio <= 0.6) {
      if (rightCollapsed) toggleRight();
      setRightWidth(newWidth);
    }
  };

  return (
    <div
      style={
        {
          width: '100vw',
          height: '100vh',
          display: 'flex',
          overflow: 'hidden',
          position: 'relative',
          backgroundColor: 'var(--bg-workspace)',
          '--left-panel-width': `${leftCollapsed ? 0 : leftWidth}px`,
        } as React.CSSProperties
      }
    >
      {/* 1. Left Sidebar */}
      <LeftSidebar />

      {taskboardOpen ? (
        <TaskboardWorkspace onClose={() => setTaskboardOpen(false)} />
      ) : (
        <>
          {/* Resize Handle 1 */}
          {!leftCollapsed && !rightMaximized && <ResizeHandle onResize={handleResizeLeft} direction="left" />}

          {/* 2. Middle Workspace */}
          {!rightMaximized && <CenterWorkspace />}

          {/* Resize Handle 2 */}
          {!rightCollapsed && !rightMaximized && <ResizeHandle onResize={handleResizeRight} direction="right" />}

          {/* 3. Right Tools Panel */}
          <RightToolsContainer />
        </>
      )}

      {/* Global Modals */}
      <ProjectSelectorModal />
      <HistoryModal />
      <ScheduledTasksModal />
      <NewTaskDialog />
      <SettingsModal />
      <ModelConfigDialog />
      <McpManualConfigDialog />
      <WorkflowTemplatesModal />
    </div>
  );
};
