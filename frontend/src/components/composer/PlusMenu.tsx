import React, { useEffect, useRef, useState } from 'react';
import { Cpu, Sparkles, Check, Target, ListChecks, Clock, BookOpen, HelpCircle } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { fetchMcpServers, fetchSkills } from '../../api/settingsApi';
import { McpServerConfig, SkillItem } from '../../types/settings';

interface PlusMenuProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * 输入框 '+' 能力拓展挂载浮窗
 * 支持动态挂载启用 MCP 工具与 Skill 技能包
 */
export const PlusMenu: React.FC<PlusMenuProps> = ({ isOpen, onClose }) => {
  const { attachedSkills, attachedMcps, ruleTrigger, setRuleTrigger, toggleSkillAttachment, toggleMcpAttachment } = useChatStore();
  const [mcps, setMcps] = useState<McpServerConfig[]>([]);
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    Promise.all([fetchMcpServers(), fetchSkills()]).then(([mcpData, skillData]) => {
      setMcps((mcpData.servers || []).filter((server) => server.enabled));
      setSkills((skillData.skills || []).filter((skill) => skill.enabled !== false));
    }).catch(() => {
      setMcps([]);
      setSkills([]);
    });
  }, [isOpen]);

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
        borderRadius: 12,
        padding: '10px 12px',
        backgroundColor: '#171b24',
        border: '1px solid rgba(148, 163, 184, 0.16)',
        boxShadow: 'var(--shadow-lg)',
        zIndex: 50,
      }}
    >
      <div style={{ padding: '3px 6px 6px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)' }}>快捷指令与模式</div>
      <button className="composer-menu-row" onClick={() => { setRuleTrigger(ruleTrigger === 'goal' ? null : 'goal'); onClose(); }}>
        <Target size={15} color="var(--accent-cyan)" /><span>目标模式</span><kbd>/goal</kbd>
        {ruleTrigger === 'goal' && <Check size={14} color="var(--accent-emerald)" />}
      </button>
      <button className="composer-menu-row" onClick={() => { setRuleTrigger(ruleTrigger === 'plan' ? null : 'plan'); onClose(); }}>
        <ListChecks size={15} color="var(--text-secondary)" /><span>规划模式</span><kbd>/plan</kbd>
        {ruleTrigger === 'plan' && <Check size={14} color="var(--accent-emerald)" />}
      </button>
      <button className="composer-menu-row" onClick={() => { setRuleTrigger(ruleTrigger === 'schedule' ? null : 'schedule'); onClose(); }}>
        <Clock size={15} color="var(--accent-amber)" /><span>排期提醒</span><kbd>/schedule</kbd>
        {ruleTrigger === 'schedule' && <Check size={14} color="var(--accent-emerald)" />}
      </button>
      <button className="composer-menu-row" onClick={() => { setRuleTrigger(ruleTrigger === 'learn' ? null : 'learn'); onClose(); }}>
        <BookOpen size={15} color="var(--accent-primary)" /><span>沉淀规则</span><kbd>/learn</kbd>
        {ruleTrigger === 'learn' && <Check size={14} color="var(--accent-emerald)" />}
      </button>
      <button className="composer-menu-row" onClick={() => { setRuleTrigger(ruleTrigger === 'grill-me' ? null : 'grill-me'); onClose(); }}>
        <HelpCircle size={15} color="#A78BFA" /><span>设计对齐</span><kbd>/grill-me</kbd>
        {ruleTrigger === 'grill-me' && <Check size={14} color="var(--accent-emerald)" />}
      </button>
      <div className="composer-menu-divider" />
      <div style={{ padding: '3px 6px 5px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)' }}>MCP 列表</div>
      {mcps.map((m) => {
        const isAttached = attachedMcps.includes(m.id);
        return (
          <button
            key={m.id}
            onClick={() => toggleMcpAttachment(m.id)}
            className="composer-menu-row"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <Cpu size={14} color="var(--accent-cyan)" />
              <span>{m.name}</span>
            </div>
            {isAttached && <Check size={14} color="var(--accent-emerald)" />}
          </button>
        );
      })}
      {mcps.length === 0 && <div className="composer-menu-empty">没有已启用的 MCP</div>}
      <div className="composer-menu-divider" />
      <div style={{ padding: '3px 6px 5px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)' }}>Skill 列表</div>
      {skills.map((s) => {
        const isAttached = attachedSkills.includes(s.name);
        return (
          <button
            key={s.name}
            onClick={() => toggleSkillAttachment(s.name)}
            className="composer-menu-row"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <Sparkles size={14} color="var(--accent-primary)" />
              <span>{s.name}</span>
            </div>
            {isAttached && <Check size={14} color="var(--accent-emerald)" />}
          </button>
        );
      })}
      {skills.length === 0 && <div className="composer-menu-empty">没有已启用的 Skill</div>}
    </div>
  );
};
