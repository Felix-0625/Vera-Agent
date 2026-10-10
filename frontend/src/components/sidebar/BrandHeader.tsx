import React from 'react';
import { PanelLeft } from 'lucide-react';
import { VeraLogo } from '../common/VeraLogo';
import { useLayoutStore } from '../../stores/layoutStore';

/**
 * 侧边栏顶部品牌头
 * 严格按照 Penpot 用户截图：Logo + VeraAgent + WORKSPACE，右侧仅单个折叠图标
 */
export const BrandHeader: React.FC = () => {
  const { toggleLeft } = useLayoutStore();

  return (
    <div
      style={{
        height: 44,
        padding: '0 14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <VeraLogo size={24} />
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: 14, fontWeight: 700, letterSpacing: '-0.2px', color: 'var(--text-primary)' }}>
            VeraAgent
          </span>
          <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.6px', color: 'var(--text-muted)' }}>
            WORKSPACE
          </span>
        </div>
      </div>

      <button
        onClick={toggleLeft}
        title="折叠侧边栏"
        style={{
          padding: 5,
          borderRadius: 'var(--radius-sm)',
          color: 'var(--text-muted)',
          display: 'flex',
          alignItems: 'center',
          cursor: 'pointer',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
        onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
      >
        <PanelLeft size={16} />
      </button>
    </div>
  );
};
