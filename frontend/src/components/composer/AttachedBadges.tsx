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
    <div style={{ display: 'flex', gap: 'var(--space-1-5)', flexWrap: 'wrap', padding: 'var(--space-2-5) var(--space-3-5) 0' }}>
      {ruleTrigger && (
        <span
          style={{
            fontSize: 'var(--font-size-compact)',
            fontWeight: 600,
            padding: 'var(--space-0-5) var(--space-2)',
            borderRadius: 'var(--radius-full)',
            backgroundColor: 'var(--bg-accent-soft)',
            color: 'var(--accent-primary)',
            border: '1px solid color-mix(in srgb, var(--accent-primary) 35%, var(--border-subtle))',
          }}
        >
          /{ruleTrigger} 模式
        </span>
      )}
      {attachedSkills.map((s) => (
        <span
          key={s}
          style={{
            fontSize: 'var(--font-size-compact)',
            padding: 'var(--space-0-5) var(--space-2)',
            borderRadius: 'var(--radius-full)',
            backgroundColor: 'var(--bg-info-soft)',
            color: 'var(--accent-cyan)',
            border: '1px solid color-mix(in srgb, var(--accent-cyan) 35%, var(--border-subtle))',
          }}
        >
          +{s}
        </span>
      ))}
      {attachedMcps.map((m) => (
        <span
          key={m}
          style={{
            fontSize: 'var(--font-size-compact)',
            padding: 'var(--space-0-5) var(--space-2)',
            borderRadius: 'var(--radius-full)',
            backgroundColor: 'var(--bg-success-soft)',
            color: 'var(--accent-emerald)',
            border: '1px solid color-mix(in srgb, var(--accent-emerald) 35%, var(--border-subtle))',
          }}
        >
          mcp:{m}
        </span>
      ))}
    </div>
  );
};
