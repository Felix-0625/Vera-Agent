import React, { useEffect } from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';
import { useChatStore } from '../../stores/chatStore';
import { LeftSidebar } from '../sidebar/LeftSidebar';
import { CenterWorkspace } from '../composer/CenterWorkspace';
import { RightToolsContainer } from '../tools/RightToolsContainer';
import { ResizeHandle } from './ResizeHandle';

// Modals
import { ProjectSelectorModal } from '../dialogs/ProjectSelectorModal';
import { HistoryModal } from '../dialogs/HistoryModal';
import { ScheduledTasksModal } from '../dialogs/ScheduledTasksModal';
import { NewTaskDialog } from '../dialogs/NewTaskDialog';
import { SettingsModal } from '../dialogs/SettingsModal';
import { ModelConfigDialog } from '../dialogs/ModelConfigDialog';
import { McpManualConfigDialog } from '../dialogs/McpManualConfigDialog';
import { ProvisionGroupDialog } from '../dialogs/ProvisionGroupDialog';

export const WorkspaceShell: React.FC = () => {
  const {
    leftCollapsed,
    leftWidth,
    setLeftWidth,
    toggleLeft,
    rightCollapsed,
    rightWidth,
    setRightWidth,
    toggleRight,
    rightMaximized,
  } = useLayoutStore();

  const { loadCurrentProject, loadProjectsHistory, loadGroups } = useProjectStore();
  const { loadThreads } = useChatStore();

  useEffect(() => {
    loadCurrentProject();
    loadProjectsHistory();
    loadGroups();
    loadThreads();
  }, []);

  const handleResizeLeft = (deltaX: number) => {
    const winWidth = window.innerWidth;
    const newWidth = leftWidth + deltaX;
    const ratio = newWidth / winWidth;

    if (ratio < 0.15) {
      if (!leftCollapsed) toggleLeft();
    } else if (ratio <= 0.40) {
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
    } else if (ratio <= 0.60) {
      if (rightCollapsed) toggleRight();
      setRightWidth(newWidth);
    }
  };

  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        display: 'flex',
        overflow: 'hidden',
        position: 'relative',
        backgroundColor: 'var(--bg-workspace)',
      }}
    >
      {/* 1. Left Sidebar */}
      <LeftSidebar />

      {/* Resize Handle 1 */}
      {!leftCollapsed && !rightMaximized && (
        <ResizeHandle onResize={handleResizeLeft} direction="left" />
      )}

      {/* 2. Middle Workspace */}
      {!rightMaximized && <CenterWorkspace />}

      {/* Resize Handle 2 */}
      {!rightCollapsed && !rightMaximized && (
        <ResizeHandle onResize={handleResizeRight} direction="right" />
      )}

      {/* 3. Right Tools Panel */}
      <RightToolsContainer />

      {/* Global Modals */}
      <ProjectSelectorModal />
      <HistoryModal />
      <ScheduledTasksModal />
      <NewTaskDialog />
      <SettingsModal />
      <ModelConfigDialog />
      <McpManualConfigDialog />
      <ProvisionGroupDialog />
    </div>
  );
};
