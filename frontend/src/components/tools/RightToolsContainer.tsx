import React, { Suspense, useEffect, useRef } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { useRightSidebarLayout } from '../../stores/rightSidebarLayout';
import { DEFAULT_TOOL_TABS, getMountedPanelScope, useToolTabsStore } from '../../stores/toolTabsStore';
import { ToolLauncherGrid } from './ToolLauncherGrid';
import { getActivePanelInstanceKey } from './toolPanelScope';
import { ToolTabStrip } from './ToolTabStrip';

const DiffViewerTab = React.lazy(() => import('./DiffViewerTab').then((module) => ({ default: module.DiffViewerTab })));
const FileExplorerTab = React.lazy(() =>
  import('./FileExplorerTab').then((module) => ({ default: module.FileExplorerTab })),
);
const FileDocumentTab = React.lazy(() =>
  import('./FileDocumentTab').then((module) => ({ default: module.FileDocumentTab })),
);
const TerminalTab = React.lazy(() => import('./TerminalTab').then((module) => ({ default: module.TerminalTab })));
const SideChatTab = React.lazy(() => import('./SideChatTab').then((module) => ({ default: module.SideChatTab })));
const SubagentsTab = React.lazy(() => import('./SubagentsTab').then((module) => ({ default: module.SubagentsTab })));
const MetricsTab = React.lazy(() => import('./MetricsTab').then((module) => ({ default: module.MetricsTab })));
const TracesTab = React.lazy(() => import('./TracesTab').then((module) => ({ default: module.TracesTab })));
const MemoryTab = React.lazy(() => import('./MemoryTab').then((module) => ({ default: module.MemoryTab })));
const EvolutionTab = React.lazy(() => import('./EvolutionTab').then((module) => ({ default: module.EvolutionTab })));
const GitFlowTab = React.lazy(() => import('./GitFlowTab').then((module) => ({ default: module.GitFlowTab })));
const WorkflowTab = React.lazy(() => import('./WorkflowTab').then((module) => ({ default: module.WorkflowTab })));

const PanelLoading: React.FC = () => (
  <div
    role="status"
    aria-live="polite"
    style={{ padding: 'var(--space-4)', color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}
  >
    正在加载工具面板…
  </div>
);

export const RightToolsContainer: React.FC = () => {
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const draftConversationId = useChatStore((state) => state.draftConversationId);
  const threads = useChatStore((state) => state.threads);
  const draftProjectId = useChatStore((state) => state.draftProjectId);
  const conversationProjectId = activeThreadId
    ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id || null
    : draftProjectId;
  const scope = `conversation:${activeThreadId || draftConversationId || 'draft:initial'}`;
  const { rightCollapsed, rightWidth, rightMaximized } = useRightSidebarLayout(scope);
  const tabs = useToolTabsStore((state) => state.tabsByConversation[scope] || DEFAULT_TOOL_TABS);
  const activeTabId = useToolTabsStore((state) => state.activeTabByConversation[scope] ?? 'tab_initial');
  const activeTab = tabs.find((t) => t.id === activeTabId);
  const activeProjectId = activeTab?.projectId || conversationProjectId;
  const projectKey = activeProjectId || 'workspace';
  const mountedPanelsByScope = useToolTabsStore((state) => state.mountedPanelsByScope);
  const markPanelMounted = useToolTabsStore((state) => state.markPanelMounted);
  const adoptConversationTabs = useToolTabsStore((state) => state.adoptConversationTabs);
  const previousScope = useRef(scope);

  useEffect(() => {
    if (activeTab && !['sidechat', 'subagents', 'fileDocument', 'terminal'].includes(activeTab.toolType)) {
      markPanelMounted(scope, projectKey, activeTab.toolType);
    }
  }, [activeTab, markPanelMounted, projectKey, scope]);
  useEffect(() => {
    const previous = previousScope.current;
    if (previous !== scope && previous.startsWith('conversation:draft:') && !scope.startsWith('conversation:draft:'))
      adoptConversationTabs(previous, scope);
    previousScope.current = scope;
  }, [adoptConversationTabs, scope]);

  const renderTool = (
    toolType: string,
    panelProjectId: string | null = activeProjectId,
    _isActive = true,
    conversationKey = scope,
  ) => {
    switch (toolType) {
      case 'launcher':
        return <ToolLauncherGrid />;
      case 'diff':
        return (
          <Suspense fallback={<PanelLoading />}>
            <DiffViewerTab projectId={panelProjectId} />
          </Suspense>
        );
      case 'files':
        return (
          <Suspense fallback={<PanelLoading />}>
            <FileExplorerTab projectId={panelProjectId} />
          </Suspense>
        );
      case 'fileDocument':
        return (
          <Suspense fallback={<PanelLoading />}>
            <FileDocumentTab path={activeTab?.filePath} projectId={activeTab?.projectId ?? panelProjectId} />
          </Suspense>
        );
      case 'terminal':
        return (
          <Suspense fallback={<PanelLoading />}>
            <TerminalTab projectId={panelProjectId} />
          </Suspense>
        );
      case 'sidechat':
        return (
          <Suspense fallback={<PanelLoading />}>
            <SideChatTab sessionId={activeTab?.sideChatId || activeTab?.id || ''} />
          </Suspense>
        );
      case 'subagents':
        return (
          <Suspense fallback={<PanelLoading />}>
            <SubagentsTab />
          </Suspense>
        );
      case 'metrics':
        return (
          <Suspense fallback={<PanelLoading />}>
            <MetricsTab projectId={panelProjectId} />
          </Suspense>
        );
      case 'traces':
        return (
          <Suspense fallback={<PanelLoading />}>
            <TracesTab projectId={panelProjectId} />
          </Suspense>
        );
      case 'memory':
        return (
          <Suspense fallback={<PanelLoading />}>
            <MemoryTab />
          </Suspense>
        );
      case 'evolution':
        return (
          <Suspense fallback={<PanelLoading />}>
            <EvolutionTab />
          </Suspense>
        );
      case 'gitflow':
        return (
          <Suspense fallback={<PanelLoading />}>
            <GitFlowTab projectId={panelProjectId} />
          </Suspense>
        );
      case 'workflow':
        return (
          <Suspense fallback={<PanelLoading />}>
            <WorkflowTab projectId={panelProjectId} conversationKey={conversationKey} />
          </Suspense>
        );
      default:
        return <ToolLauncherGrid />;
    }
  };

  const activeToolType = activeTab?.toolType || null;
  // The shell output/working directory follows the project, but terminal input
  // and command history are UI state and must reset when the conversation changes.
  const activePanelKey = getActivePanelInstanceKey(scope, activeTab?.id, activeToolType);

  return (
    <aside
      className={`glass-panel right-tools-panel${rightMaximized ? ' is-maximized' : ''}`}
      style={{
        width: rightCollapsed ? 0 : rightMaximized ? 'auto' : rightWidth,
        maxWidth: rightMaximized ? 'none' : '38vw',
        minWidth: 0,
        boxSizing: 'border-box',
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
      <ToolTabStrip conversationKey={scope} tabs={tabs} activeTabId={activeTabId} projectId={activeProjectId} />
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {Object.entries(mountedPanelsByScope).flatMap(([cachedScopeKey, panelGroup]) =>
          panelGroup.toolTypes
            .filter((toolType) => !['sidechat', 'subagents', 'fileDocument', 'terminal'].includes(toolType))
            .map((toolType) => {
              const activeScopeKey = getMountedPanelScope(scope, projectKey);
              const isActive = cachedScopeKey === activeScopeKey && activeToolType === toolType;
              const panelProjectId = panelGroup.projectKey === 'workspace' ? null : panelGroup.projectKey;
              return (
                <div
                  key={`${cachedScopeKey}:${toolType}`}
                  style={{ display: isActive ? 'block' : 'none', height: '100%' }}
                >
                  {renderTool(toolType, panelProjectId, isActive, panelGroup.conversationKey)}
                </div>
              );
            }),
        )}
        {['sidechat', 'subagents', 'fileDocument', 'terminal'].includes(activeToolType || '') && (
          <div key={activePanelKey} style={{ height: '100%' }}>
            {renderTool(activeToolType || '')}
          </div>
        )}
        {!activeToolType && (
          <div
            style={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-muted)',
              fontSize: 'var(--font-size-md)',
            }}
          >
            已关闭所有标签页，点击顶部 [+] 开辟新工具
          </div>
        )}
      </div>
    </aside>
  );
};
