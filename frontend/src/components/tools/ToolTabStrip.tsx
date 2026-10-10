import React from 'react';
import { Plus, X, Maximize2, Minimize2, Globe } from 'lucide-react';
import { ToolTab } from '../../types/tool';
import { useToolTabsStore } from '../../stores/toolTabsStore';
import { useLayoutStore } from '../../stores/layoutStore';

export const ToolTabStrip: React.FC<{
  conversationKey: string;
  projectScope: string;
  projectTabs: ToolTab[];
  conversationTabs: ToolTab[];
  activeScope: string;
  activeTabId: string;
  projectId: string | null;
}> = ({ conversationKey, projectScope, projectTabs, conversationTabs, activeScope, activeTabId, projectId }) => {
  const { activateTab, closeTab, addNewLauncherTab } = useToolTabsStore();
  const { toggleRightMaximize, rightMaximized } = useLayoutStore();
  const tabs = [...projectTabs.map((tab) => ({ tab, scope: projectScope })), ...conversationTabs.map((tab) => ({ tab, scope: conversationKey }))];

  return (
    <div style={{ height: 44, backgroundColor: 'var(--bg-surface-elevated)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 10px', flexShrink: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflowX: 'auto', flex: 1 }}>
        {tabs.map(({ tab, scope }) => {
          const isActive = activeScope === scope && activeTabId === tab.id;
          return <div key={`${scope}:${tab.id}`} onClick={() => activateTab(tab.id, scope, conversationKey)} style={{ height: 28, padding: '0 10px', borderRadius: 'var(--radius-sm)', backgroundColor: isActive ? 'var(--bg-card)' : 'transparent', border: isActive ? '1px solid var(--border-default)' : '1px solid transparent', color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)', fontSize: 12, fontWeight: isActive ? 600 : 400, display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', whiteSpace: 'nowrap' }}>
            <Globe size={12.5} color={isActive ? 'var(--accent-cyan)' : 'var(--text-muted)'} />
            <span>{tab.title}</span>
            {tab.closable && <button onClick={(event) => { event.stopPropagation(); closeTab(tab.id, scope, conversationKey); }} title="关闭标签页" style={{ padding: 2, borderRadius: 2, color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}><X size={12} /></button>}
          </div>;
        })}
        <button onClick={() => addNewLauncherTab(projectId || undefined, conversationKey)} title="开辟新标签页" aria-label="开辟新标签页" style={{ padding: 4, borderRadius: 'var(--radius-sm)', color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}><Plus size={15} /></button>
      </div>
      <button onClick={toggleRightMaximize} title={rightMaximized ? '还原三栏布局' : '最大化右侧面板'} aria-label={rightMaximized ? '还原三栏布局' : '最大化右侧面板'} style={{ padding: 5, color: rightMaximized ? 'var(--accent-primary)' : 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>
        {rightMaximized ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
      </button>
    </div>
  );
};
