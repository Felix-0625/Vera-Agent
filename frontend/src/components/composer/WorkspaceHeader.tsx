import { PanelLeft, PanelRight, Terminal } from 'lucide-react';
import React from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { useRightSidebarLayout } from '../../stores/rightSidebarLayout';
import { IconButton } from '../common/IconButton';
import { ContextUsageIndicator } from './ContextUsageIndicator';

/** Main workspace toolbar and panel visibility controls. */
export const WorkspaceHeader: React.FC = () => {
  const { toggleLeft, toggleBottomDrawer, leftCollapsed, bottomDrawerOpen } = useLayoutStore();
  const { toggleRight, rightCollapsed } = useRightSidebarLayout();

  return (
    <div
      style={{
        height: 'var(--layout-header-height)',
        padding: '0 var(--space-4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid var(--border-subtle)',
        backgroundColor: 'transparent',
        flexShrink: 0,
      }}
    >
      <ContextUsageIndicator />
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          padding: 'var(--space-0-5)',
          gap: 'var(--space-0-5)',
        }}
      >
        <IconButton
          onClick={toggleLeft}
          label="切换左侧边栏"
          aria-pressed={!leftCollapsed}
          active={!leftCollapsed}
          size="sm"
        >
          <PanelLeft size={14} />
        </IconButton>
        <IconButton
          onClick={toggleBottomDrawer}
          label={bottomDrawerOpen ? '关闭底部终端' : '打开底部终端'}
          aria-pressed={bottomDrawerOpen}
          active={bottomDrawerOpen}
          size="sm"
        >
          <Terminal size={14} />
        </IconButton>
        <IconButton
          onClick={toggleRight}
          label="切换右侧工具栏"
          aria-pressed={!rightCollapsed}
          active={!rightCollapsed}
          size="sm"
        >
          <PanelRight size={14} />
        </IconButton>
      </div>
    </div>
  );
};
