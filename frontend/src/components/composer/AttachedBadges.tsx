import React from 'react';
import { RuleTrigger } from '../../types/chat';

interface AttachedBadgesProps {
  ruleTrigger: RuleTrigger | null;
  attachedSkills: string[];
  attachedMcps: string[];
}

/**
 * 签名输入卡顶部附加标签徽章条 (快捷指令模式、技能、MCP)
 */
export const AttachedBadges: React.FC<AttachedBadgesProps> = ({
  ruleTrigger,
  attachedSkills,
  attachedMcps,
}) => {
  if (!ruleTrigger && attachedSkills.length === 0 && attachedMcps.length === 0) {
    return null;
  }

  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', padding: '10px 14px 0' }}>
      {ruleTrigger && (
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            padding: '2px 8px',
            borderRadius: 'var(--radius-full)',
            backgroundColor: 'rgba(124, 58, 237, 0.2)',
            color: '#C4B5FD',
            border: '1px solid rgba(124, 58, 237, 0.4)',
          }}
        >
          /{ruleTrigger} 模式
        </span>
      )}
      {attachedSkills.map((s) => (
        <span
          key={s}
          style={{
            fontSize: 11,
            padding: '2px 8px',
            borderRadius: 'var(--radius-full)',
            backgroundColor: 'rgba(6, 182, 212, 0.15)',
            color: 'var(--accent-cyan)',
            border: '1px solid rgba(6, 182, 212, 0.3)',
          }}
        >
          +{s}
        </span>
      ))}
      {attachedMcps.map((m) => (
        <span
          key={m}
          style={{
            fontSize: 11,
            padding: '2px 8px',
            borderRadius: 'var(--radius-full)',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            color: 'var(--accent-emerald)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
          }}
        >
          mcp:{m}
        </span>
      ))}
    </div>
  );
};
