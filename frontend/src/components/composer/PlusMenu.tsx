import React, { useEffect, useRef, useState } from 'react';
import { Cpu, Sparkles, Check, Target, ListChecks, Clock, BookOpen, HelpCircle, Workflow } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { fetchMcpServers, fetchSkills } from '../../api/settingsApi';
import { McpServerConfig, SkillItem } from '../../types/settings';
import { fetchGroups } from '../../api/projectApi';
import { useToolTabsStore } from '../../stores/toolTabsStore';
import { ensureRightSidebarOpen } from '../../stores/rightSidebarLayout';
import { useLayoutStore } from '../../stores/layoutStore';
import { RuleTrigger } from '../../types/chat';
import { useOrchestrationInvokeStore } from '../../stores/orchestrationInvokeStore';
import { Button } from '../common/Button';

interface PlusMenuProps {
  isOpen: boolean;
  onClose: () => void;
  requestText?: string;
  onConsumeRequest?: () => void;
  onSelectRuleTrigger?: (trigger: RuleTrigger) => void;
}


export const PlusMenu: React.FC<PlusMenuProps> = ({ isOpen, onClose, requestText = '', onConsumeRequest, onSelectRuleTrigger }) => {
  const { attachedSkills, attachedMcps, ruleTrigger, setRuleTrigger, toggleSkillAttachment, toggleMcpAttachment } = useChatStore();
  const [mcps, setMcps] = useState<McpServerConfig[]>([]);
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [flows, setFlows] = useState<Array<{ group_id: string; name: string; group_mode?: string }>>([]);
  const { activeThreadId, threads, draftProjectId } = useChatStore();
  const projectId = activeThreadId ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id : draftProjectId;
  const openTab = useToolTabsStore((state) => state.openTab);
  const setNewTaskDialogOpen = useLayoutStore((state) => state.setNewTaskDialogOpen);
  const enqueueOrchestrationInvoke = useOrchestrationInvokeStore((state) => state.enqueue);
  const menuRef = useRef<HTMLDivElement>(null);
  const selectRuleTrigger = (trigger: Exclude<RuleTrigger, null>) => {
    setRuleTrigger(ruleTrigger === trigger ? null : trigger);
    onSelectRuleTrigger?.(trigger);
    onClose();
  };

  const invokeFlow = async (groupId: string, name: string) => {
    if (!projectId) return;
    const chat = useChatStore.getState();
    const originThreadId = chat.activeThreadId || await chat.newThread(`流程任务 · ${name}`, undefined, projectId);
    const conversationKey = `conversation:${originThreadId}`;
    ensureRightSidebarOpen(conversationKey);
    openTab('workflow', '流程编排', conversationKey, projectId);
    enqueueOrchestrationInvoke({
      conversationKey,
      projectId,
      groupId,
      input: requestText,
      originThreadId,
    });
    onConsumeRequest?.();
    onClose();
  };

  useEffect(() => {
    if (!isOpen) return;
    Promise.all([fetchMcpServers(), fetchSkills(), projectId ? fetchGroups(projectId) : Promise.resolve({ groups: [] })]).then(([mcpData, skillData, groupData]) => {
      setMcps((mcpData.servers || []).filter((server) => server.enabled));
      setSkills((skillData.skills || []).filter((skill) => skill.enabled !== false));
      setFlows(groupData.groups.filter((group) => group.group_mode === 'workflow' || group.group_mode === 'architecture'));
    }).catch(() => {
      setMcps([]);
      setSkills([]);
      setFlows([]);
    });
  }, [isOpen, projectId]);

  useEffect(() => {
    if (!isOpen) return;
    const closeOnOutside = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) onClose();
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('pointerdown', closeOnOutside);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('pointerdown', closeOnOutside);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      ref={menuRef}
      className="glass-panel animate-fade-in"
      style={{
        position: 'absolute',
        bottom: 'calc(100% + 8px)',
        left: 0,
        right: 0,
        width: '100%',
        maxHeight: 'min(420px, 52vh)',
        overflowY: 'auto',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-2-5) var(--space-3)',
        backgroundColor: 'color-mix(in srgb, var(--accent-primary) 8%, var(--bg-surface))',
        border: '1px solid var(--border-default)',
        boxShadow: 'var(--shadow-lg)',
        zIndex: 50,
      }}
    >
      <div style={{ padding: 'var(--space-0-75) var(--space-1-5) var(--space-1-5)', fontSize: 'var(--font-size-compact)', fontWeight: 600, color: 'var(--text-muted)' }}>快捷指令与模式</div>
      <Button variant="ghost" size="md" className="composer-menu-row" onClick={() => selectRuleTrigger('goal')}>
        <Target size={15} color="var(--accent-cyan)" /><span>目标模式</span><kbd>/goal</kbd>
        {ruleTrigger === 'goal' && <Check size={14} color="var(--accent-emerald)" />}
      </Button>
      <Button variant="ghost" size="md" className="composer-menu-row" onClick={() => selectRuleTrigger('plan')}>
        <ListChecks size={15} color="var(--text-secondary)" /><span>规划模式</span><kbd>/plan</kbd>
        {ruleTrigger === 'plan' && <Check size={14} color="var(--accent-emerald)" />}
      </Button>
      <Button variant="ghost" size="md" className="composer-menu-row" onClick={() => { setNewTaskDialogOpen(true, requestText.replace(/^\/schedule\b\s*/i, '').trim()); onConsumeRequest?.(); onClose(); }}>
        <Clock size={15} color="var(--accent-amber)" /><span>定时任务</span><kbd>/schedule</kbd>
      </Button>
      <Button variant="ghost" size="md" className="composer-menu-row" onClick={() => selectRuleTrigger('learn')}>
        <BookOpen size={15} color="var(--accent-primary)" /><span>沉淀用户记忆</span><kbd>/learn</kbd>
        {ruleTrigger === 'learn' && <Check size={14} color="var(--accent-emerald)" />}
      </Button>
      <Button variant="ghost" size="md" className="composer-menu-row" onClick={() => selectRuleTrigger('grill-me')}>
        <HelpCircle size={15} color="var(--accent-primary)" /><span>设计对齐</span><kbd>/grill-me</kbd>
        {ruleTrigger === 'grill-me' && <Check size={14} color="var(--accent-emerald)" />}
      </Button>
      <div className="composer-menu-divider" />
      <div style={{ padding: 'var(--space-0-75) var(--space-1-5) var(--space-1-25)', fontSize: 'var(--font-size-compact)', fontWeight: 600, color: 'var(--text-muted)' }}>调用当前项目流程</div>
      {flows.map((flow) => <Button key={flow.group_id} variant="ghost" size="md" className="composer-menu-row" onClick={() => void invokeFlow(flow.group_id, flow.name)}><Workflow size={14} color="var(--accent-primary)"/><span>{flow.name}</span><kbd>{flow.group_mode === 'architecture' ? '架构' : '工作流'}</kbd></Button>)}
      {!flows.length && <div className="composer-menu-empty">当前项目没有可调用的流程实例</div>}
      <div className="composer-menu-divider" />
      <div style={{ padding: 'var(--space-0-75) var(--space-1-5) var(--space-1-25)', fontSize: 'var(--font-size-compact)', fontWeight: 600, color: 'var(--text-muted)' }}>MCP 列表</div>
      {mcps.map((m) => {
        const isAttached = attachedMcps.includes(m.id);
        return (
          <Button
            key={m.id}
            type="button"
            onClick={() => toggleMcpAttachment(m.id)}
            variant="ghost" size="md" className="composer-menu-row"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1-75)' }}>
              <Cpu size={14} color="var(--accent-cyan)" />
              <span>{m.name}</span>
            </div>
            {isAttached && <Check size={14} color="var(--accent-emerald)" />}
          </Button>
        );
      })}
      {mcps.length === 0 && <div className="composer-menu-empty">没有已启用的 MCP</div>}
      <div className="composer-menu-divider" />
      <div style={{ padding: 'var(--space-0-75) var(--space-1-5) var(--space-1-25)', fontSize: 'var(--font-size-compact)', fontWeight: 600, color: 'var(--text-muted)' }}>Skill 列表</div>
      {skills.map((s) => {
        const isAttached = attachedSkills.includes(s.name);
        return (
          <Button
            key={s.name}
            type="button"
            onClick={() => toggleSkillAttachment(s.name)}
            variant="ghost" size="md" className="composer-menu-row"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1-75)' }}>
              <Sparkles size={14} color="var(--accent-primary)" />
              <span>{s.name}</span>
            </div>
            {isAttached && <Check size={14} color="var(--accent-emerald)" />}
          </Button>
        );
      })}
      {skills.length === 0 && <div className="composer-menu-empty">没有已启用的 Skill</div>}
    </div>
  );
};
