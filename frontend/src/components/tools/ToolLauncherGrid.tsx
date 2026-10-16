import React from 'react';
import { useToolTabsStore } from '../../stores/toolTabsStore';
import { TOOL_LAUNCHER_ITEMS } from './toolLauncherData';
import { Button } from '../common/Button';

/**
 * 右侧工具发射器磁贴大网格 (初始空态页面)
 */
export const ToolLauncherGrid: React.FC = () => {
  const { openTab } = useToolTabsStore();

  return (
    <div style={{ padding: 'var(--space-6) var(--space-5)', height: '100%', overflowY: 'auto' }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 'var(--space-5)' }}>
        工具
      </h2>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 'var(--space-3)',
        }}
      >
        {TOOL_LAUNCHER_ITEMS.map((card) => (
          <Button
            key={card.id}
            variant="ghost"
            size="md"
            onClick={() => openTab(card.id)}
            className="tool-launcher-card"
          >
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 'var(--radius-md)',
                backgroundColor: card.iconBg,
                border: `1px solid ${card.borderColor}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              {card.icon}
            </div>

            <span style={{ fontSize: 'var(--font-size-md)', fontWeight: 600, color: 'var(--text-primary)' }}>
              {card.title}
            </span>
          </Button>
        ))}
      </div>
    </div>
  );
};
