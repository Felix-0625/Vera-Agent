import React from 'react';
import { Target, Compass, Clock, BookOpen, HelpCircle } from 'lucide-react';
import { RuleTrigger } from '../../types/chat';

interface SlashMenuProps {
  isOpen: boolean;
  onSelect: (trigger: RuleTrigger) => void;
  onClose: () => void;
}

/**
 * 输入框快速斜杠指令浮窗
 * 严格对齐 Penpot 快捷指令列表
 */
export const SlashMenu: React.FC<SlashMenuProps> = ({ isOpen, onSelect, onClose }) => {
  if (!isOpen) return null;

  const items: Array<{ key: RuleTrigger; label: string; desc: string; icon: React.ReactNode }> = [
    {
      key: 'goal',
      label: '/goal',
      desc: '目标驱动模式：自主迭代直至所有验收测试与目标全部通过',
      icon: <Target size={16} color="var(--accent-emerald)" />,
    },
    {
      key: 'plan',
      label: '/plan',
      desc: '规划模式：编写代码前显式拆解方案并输出架构设计规范',
      icon: <Compass size={16} color="var(--accent-cyan)" />,
    },
    {
      key: 'schedule',
      label: '/schedule',
      desc: '排期提醒：创建周期性 Cron 或单次后台任务',
      icon: <Clock size={16} color="var(--accent-amber)" />,
    },
    {
      key: 'learn',
      label: '/learn',
      desc: '沉淀规则：将本次对话修正与最佳实践保存到项目记忆',
      icon: <BookOpen size={16} color="var(--accent-primary)" />,
    },
    {
      key: 'grill-me',
      label: '/grill-me',
      desc: '设计对齐：通过结构化提问帮助理清需求与方案细节',
      icon: <HelpCircle size={16} color="#A78BFA" />,
    },
  ];

  return (
    <div
      className="glass-panel animate-fade-in"
      style={{
        position: 'absolute',
        bottom: '100%',
        left: 0,
        marginBottom: 8,
        width: 380,
        borderRadius: 'var(--radius-md)',
        padding: 6,
        boxShadow: 'var(--shadow-lg)',
        zIndex: 50,
      }}
    >
      <div style={{ padding: '4px 8px 6px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)' }}>
        快捷指令触发器
      </div>
      {items.map((item) => (
        <button
          key={item.key}
          onClick={() => {
            onSelect(item.key);
            onClose();
          }}
          style={{
            width: '100%',
            padding: '7px 10px',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            justifyContent: 'flex-start',
            textAlign: 'left',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.06)')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
        >
          {item.icon}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text-primary)' }}>
              {item.label}
            </span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.3 }}>
              {item.desc}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
};
