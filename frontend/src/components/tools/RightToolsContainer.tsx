import React, { useEffect, useRef } from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { DEFAULT_TOOL_TABS, getProjectToolScope, useToolTabsStore } from '../../stores/toolTabsStore';
import { ToolTabStrip } from './ToolTabStrip';
import { ToolLauncherGrid } from './ToolLauncherGrid';
import { DiffViewerTab } from './DiffViewerTab';
import { FileExplorerTab } from './FileExplorerTab';
import { FileDocumentTab } from './FileDocumentTab';
import { TerminalTab } from './TerminalTab';
import { SideChatTab } from './SideChatTab';
import { SubagentsTab } from './SubagentsTab';
import { MetricsTab } from './MetricsTab';
import { McpTab } from './McpTab';
import { SkillsTab } from './SkillsTab';
import { GitFlowTab } from './GitFlowTab';
import { WorkflowTab } from './WorkflowTab';
import { useChatStore } from '../../stores/chatStore';

const EMPTY_TOOL_TABS: never[] = [];

export const RightToolsContainer: React.FC = () => {
  const { rightCollapsed, rightWidth, rightMaximized } = useLayoutStore();
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const draftConversationId = useChatStore((state) => state.draftConversationId);
  const threads = useChatStore((state) => state.threads);
  const draftProjectId = useChatStore((state) => state.draftProjectId);
  const activeProjectId = activeThreadId ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id || null : draftProjectId;
  const scope = `conversation:${activeThreadId || draftConversationId || 'draft:initial'}`;
  const projectKey = activeProjectId || 'workspace';
  const projectScope = getProjectToolScope(activeProjectId);
  const projectTabs = useToolTabsStore((state) => state.tabsByConversation[projectScope] || DEFAULT_TOOL_TABS);
  const conversationTabs = useToolTabsStore((state) => state.tabsByConversation[scope] || EMPTY_TOOL_TABS);
  const requestedActiveScope = useToolTabsStore((state) => state.activeScopeByConversation[scope]);
  const activeScope = requestedActiveScope === scope && conversationTabs.length ? scope : projectScope;
  const tabs = [...projectTabs, ...conversationTabs];
  const activeTabId = useToolTabsStore((state) => state.activeTabByConversation[activeScope] ?? (activeScope === projectScope ? 'tab_initial' : ''));
  const mountedPanelsByProject = useToolTabsStore((state) => state.mountedPanelsByProject);
  const markPanelMounted = useToolTabsStore((state) => state.markPanelMounted);
  const adoptConversationTabs = useToolTabsStore((state) => state.adoptConversationTabs);
  const previousScope = useRef(scope);

  const activeTab = tabs.find((t) => t.id === activeTabId);
  useEffect(() => {
    if (activeTab && !['sidechat', 'subagents', 'fileDocument'].includes(activeTab.toolType)) markPanelMounted(projectKey, activeTab.toolType);
  }, [activeTab?.toolType, markPanelMounted, projectKey]);
  useEffect(() => {
    const previous = previousScope.current;
    if (previous !== scope && previous.startsWith('conversation:draft:') && !scope.startsWith('conversation:draft:')) adoptConversationTabs(previous, scope);
    previousScope.current = scope;
  }, [adoptConversationTabs, scope]);

  const renderTool = (toolType: string) => {
    switch (toolType) {
      case 'launcher':
        return <ToolLauncherGrid />;
      case 'diff':
        return <DiffViewerTab />;
      case 'files':
        return <FileExplorerTab />;
      case 'fileDocument':
        return <FileDocumentTab path={activeTab?.filePath} />;
      case 'terminal':
        return <TerminalTab />;
      case 'sidechat':
        return <SideChatTab />;
      case 'subagents':
        return <SubagentsTab />;
      case 'metrics':
        return <MetricsTab />;
      case 'mcp':
        return <McpTab />;
      case 'skills':
        return <SkillsTab />;
      case 'gitflow':
        return <GitFlowTab />;
      case 'workflow':
        return <WorkflowTab />;
      default:
        return <ToolLauncherGrid />;
    }
  };

  const activeToolType = activeTab?.toolType || null;

  return (
    <aside
      className="glass-panel"
      style={{
        width: rightCollapsed ? 0 : rightMaximized ? 'auto' : rightWidth,
        height: '100%',
        flexDirection: 'column',
        backgroundColor: 'var(--bg-surface)',
        borderLeft: rightCollapsed ? 0 : '1px solid var(--border-subtle)',
        userSelect: 'none',
        flex: rightCollapsed ? '0 0 0px' : rightMaximized ? 1 : '0 0 auto',
        display: rightCollapsed ? 'none' : 'flex',
        zIndex: rightMaximized ? 40 : 10,
      }}
    >
      <ToolTabStrip conversationKey={scope} projectScope={projectScope} projectTabs={projectTabs} conversationTabs={conversationTabs} activeScope={activeScope} activeTabId={activeTabId} projectId={activeProjectId} />
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {Object.entries(mountedPanelsByProject).flatMap(([cachedProjectKey, toolTypes]) => toolTypes.filter((toolType) => !['sidechat', 'subagents', 'fileDocument'].includes(toolType)).map((toolType) => (
          <div key={`${cachedProjectKey}:${toolType}`} style={{ display: cachedProjectKey === projectKey && activeToolType === toolType ? 'block' : 'none', height: '100%' }}>
            {renderTool(toolType)}
          </div>
        )))}
        {(['sidechat', 'subagents', 'fileDocument'].includes(activeToolType || '')) && <div style={{ height: '100%' }}>{renderTool(activeToolType || '')}</div>}
        {!activeToolType && <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>已关闭所有标签页，点击顶部 [+] 开辟新工具</div>}
      </div>
    </aside>
  );
};
