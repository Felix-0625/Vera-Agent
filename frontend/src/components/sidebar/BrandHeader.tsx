import React from 'react';
import { PanelLeft } from 'lucide-react';
import { VeraLogo } from '../common/VeraLogo';
import { useLayoutStore } from '../../stores/layoutStore';
import { IconButton } from '../common/IconButton';


export const BrandHeader: React.FC = () => {
  const { toggleLeft } = useLayoutStore();

  return (
    <div
      style={{
        height: 'var(--layout-header-height)',
        padding: '0 var(--space-3-5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)' }}>
        <VeraLogo size={24} />
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: 'var(--font-size-body)', fontWeight: 700, letterSpacing: '-0.2px', color: 'var(--text-primary)' }}>
            VeraAgent
          </span>
          <span style={{ fontSize: 'var(--font-size-tiny)', fontWeight: 600, letterSpacing: '0.6px', color: 'var(--text-muted)' }}>
            WORKSPACE
          </span>
        </div>
      </div>

      <IconButton
        onClick={toggleLeft}
        label="折叠侧边栏"
        size="sm"
      >
        <PanelLeft size={16} />
      </IconButton>
    </div>
  );
};
