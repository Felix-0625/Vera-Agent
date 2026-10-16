import React from 'react';
import { Plus, History, Clock, Workflow } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';
import { Button } from '../common/Button';

/**
 * 侧边栏顶部快捷导航区
 * 严格按照用户 Penpot 截图实现：
 * 1. 顶部 "+ 新建对话" 按钮
 * 2. 紧凑左对齐 "对话历史" 与 "计划任务"
 */
export const NavLinks: React.FC = () => {
  const { openDraftConversation } = useChatStore();
  const { currentProject } = useProjectStore();
  const { setHistoryOpen } = useLayoutStore();

  const handleNewConversation = () => {
    openDraftConversation(currentProject?.id || null);
    // 聚焦中心输入框，确保用户立即输入
    setTimeout(() => {
      const textarea = document.querySelector('textarea');
      if (textarea) textarea.focus();
    }, 50);
  };

  return (
    <div style={{ padding: 'var(--space-2-5) var(--space-3) var(--space-1-5)', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
      {/* "+ 新建对话" 按钮：严格对齐用户 Penpot 截图 (左对齐紫框胶囊) */}
      <Button variant="outline" size="md" className="sidebar-new-conversation" onClick={handleNewConversation}>
        <Plus size={16} color="var(--accent-primary)" />
        <span>新建对话</span>
      </Button>

      {/* 对话历史与计划任务：严格左对齐与新建对话图标列对齐 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-0-5)' }}>
        <Button variant="ghost" size="sm" className="sidebar-navigation-button" onClick={() => setHistoryOpen(true)}>
          <History size={15} color="var(--text-muted)" />
          <span>对话历史</span>
        </Button>

      </div>
    </div>
  );
};

export const ScheduledTasksLink: React.FC = () => {
  const { setScheduledTasksOpen } = useLayoutStore();
  return <div style={{ padding: '0 var(--space-3)' }}><Button variant="ghost" size="sm" className="sidebar-navigation-button" onClick={() => setScheduledTasksOpen(true)}><Clock size={15} color="var(--text-muted)"/><span>计划任务</span></Button></div>;
};

export const WorkflowTemplatesLink: React.FC = () => {
  const { setWorkflowTemplatesOpen } = useLayoutStore();
  return <div style={{ padding: '0 var(--space-3)' }}><Button variant="ghost" size="sm" className="sidebar-navigation-button" onClick={() => setWorkflowTemplatesOpen(true)}><Workflow size={15} color="var(--accent-primary)"/><span>流程架构模板</span></Button></div>;
};
