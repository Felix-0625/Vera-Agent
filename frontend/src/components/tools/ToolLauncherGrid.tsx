import React from 'react';
import { useToolTabsStore } from '../../stores/toolTabsStore';
import { TOOL_LAUNCHER_ITEMS } from './toolLauncherData';

/**
 * 右侧工具发射器磁贴大网格 (初始空态页面)
 */
export const ToolLauncherGrid: React.FC = () => {
  const { openTab } = useToolTabsStore();

  return (
    <div style={{ padding: '24px 20px', height: '100%', overflowY: 'auto' }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 20 }}>
        工具
      </h2>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 12,
        }}
      >
        {TOOL_LAUNCHER_ITEMS.map((card) => (
          <div
            key={card.id}
            onClick={() => openTab(card.id)}
            style={{
              padding: '12px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              cursor: 'pointer',
              height: 54,
              borderRadius: 12,
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.06)',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.06)';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.15)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.03)';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.06)';
            }}
          >
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
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

            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
              {card.title}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
