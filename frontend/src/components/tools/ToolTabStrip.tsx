import React from 'react';
import { Plus, X, Maximize2, Minimize2, Globe, PanelRightClose } from 'lucide-react';
import { ToolTab } from '../../types/tool';
import { useToolTabsStore } from '../../stores/toolTabsStore';
import { useRightSidebarLayout } from '../../stores/rightSidebarLayout';
import { IconButton } from '../common/IconButton';

export const ToolTabStrip: React.FC<{
  conversationKey: string;
  tabs: ToolTab[];
  activeTabId: string;
  projectId: string | null;
}> = ({ conversationKey, tabs, activeTabId, projectId }) => {
  const { activateTab, closeTab, addNewLauncherTab } = useToolTabsStore();
  const { toggleRightMaximize, toggleRight, rightMaximized } = useRightSidebarLayout(conversationKey);
  return (
    <div style={{ height: 'var(--layout-header-height)', backgroundColor: 'var(--bg-surface-elevated)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 var(--space-2-5)', flexShrink: 0 }}>
      <div role="tablist" aria-label="右侧工具标签" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1-5)', overflowX: 'auto', flex: 1 }}>
        {tabs.map((tab, index) => {
          const isActive = activeTabId === tab.id;
          return <div
            key={`${conversationKey}:${tab.id}`}
            id={`tool-tab-${conversationKey}-${tab.id}`}
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => activateTab(tab.id, conversationKey, conversationKey)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                activateTab(tab.id, conversationKey, conversationKey);
                return;
              }
              const nextIndex = event.key === 'ArrowRight' ? (index + 1) % tabs.length
                : event.key === 'ArrowLeft' ? (index - 1 + tabs.length) % tabs.length
                  : event.key === 'Home' ? 0
                    : event.key === 'End' ? tabs.length - 1 : -1;
              if (nextIndex < 0) return;
              event.preventDefault();
              const nextTab = tabs[nextIndex];
              activateTab(nextTab.id, conversationKey, conversationKey);
              event.currentTarget.parentElement?.querySelectorAll<HTMLElement>('[role="tab"]')[nextIndex]?.focus();
            }}
            style={{ height: 'var(--control-height-sm)', padding: '0 var(--space-2-5)', borderRadius: 'var(--radius-sm)', backgroundColor: isActive ? 'var(--bg-card)' : 'transparent', border: isActive ? '1px solid var(--border-default)' : '1px solid transparent', color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)', fontSize: 'var(--font-size-sm)', fontWeight: isActive ? 600 : 400, display: 'flex', alignItems: 'center', gap: 'var(--space-1-5)', cursor: 'pointer', whiteSpace: 'nowrap' }}
          >
            <Globe size={12.5} color={isActive ? 'var(--accent-cyan)' : 'var(--text-muted)'} />
            <span>{tab.title}</span>
            {tab.closable && <IconButton label="关闭标签页" size="sm" onClick={(event) => { event.stopPropagation(); closeTab(tab.id, conversationKey, conversationKey); }} onKeyDown={(event) => event.stopPropagation()}><X size={12} /></IconButton>}
          </div>;
        })}
        <IconButton label="开辟新标签页" size="sm" onClick={() => addNewLauncherTab(projectId || undefined, conversationKey)}><Plus size={15} /></IconButton>
      </div>
      <IconButton className="right-tools-panel__collapse" onClick={toggleRight} label="收起右侧工具栏" size="sm">
        <PanelRightClose size={14} />
      </IconButton>
      <IconButton onClick={toggleRightMaximize} label={rightMaximized ? '还原三栏布局' : '最大化右侧面板'} active={rightMaximized} size="sm">
        {rightMaximized ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
      </IconButton>
    </div>
  );
};
