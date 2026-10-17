import React from 'react';
import { Plus, History, Clock, Workflow, CheckSquare } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';
import { Button } from '../common/Button';


export const NavLinks: React.FC = () => {
  const { openDraftConversation } = useChatStore();
  const { currentProject } = useProjectStore();
  const { setHistoryOpen, taskboardOpen, setTaskboardOpen } = useLayoutStore();

  const handleNewConversation = () => {
    openDraftConversation(currentProject?.id || null);
    setTaskboardOpen(false);
    setTimeout(() => {
      const textarea = document.querySelector('textarea');
      if (textarea) textarea.focus();
    }, 50);
  };

  return (
    <div style={{ padding: 'var(--space-2-5) var(--space-3) var(--space-1-5)', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
      {}
      <Button variant="outline" size="md" className="sidebar-new-conversation" onClick={handleNewConversation}>
        <Plus size={16} color="var(--accent-primary)" />
        <span>新建对话</span>
      </Button>

      {}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-0-5)' }}>
        <Button variant="ghost" size="sm" className="sidebar-navigation-button" onClick={() => setHistoryOpen(true)}>
          <History size={15} color="var(--text-muted)" />
          <span>对话历史</span>
        </Button>
        <Button
          variant={taskboardOpen ? 'secondary' : 'ghost'}
          size="sm"
          className={`sidebar-navigation-button${taskboardOpen ? ' is-current-page' : ''}`}
          onClick={() => setTaskboardOpen(!taskboardOpen)}
          aria-current={taskboardOpen ? 'page' : undefined}
        >
          <CheckSquare size={15} color={taskboardOpen ? 'var(--accent-primary)' : 'var(--text-muted)'} />
          <span>任务面板</span>
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
