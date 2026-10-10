import React from 'react';
import { Settings } from 'lucide-react';
import { useLayoutStore } from '../../stores/layoutStore';

export const SidebarFooter: React.FC = () => {
  const { openSettings } = useLayoutStore();

  return (
    <div
      style={{
        padding: '10px 12px',
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}
    >
      <button
        onClick={() => openSettings('permissions')}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          fontSize: 12.5,
          color: 'var(--text-secondary)',
          width: '100%',
          justifyContent: 'flex-start',
          padding: '6px 12px',
          borderRadius: 'var(--radius-sm)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
          e.currentTarget.style.color = 'var(--text-primary)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent';
          e.currentTarget.style.color = 'var(--text-secondary)';
        }}
      >
        <Settings size={15} />
        <span>设置</span>
      </button>
    </div>
  );
};
