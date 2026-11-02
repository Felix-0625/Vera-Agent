import { Moon, Settings, Sun } from 'lucide-react';
import React from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { Button } from '../common/Button';

export const SidebarFooter: React.FC = () => {
  const { openSettings, theme, toggleTheme } = useLayoutStore();

  return (
    <div
      style={{
        padding: 'var(--space-2-5) var(--space-3)',
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 'var(--space-2)',
        flexShrink: 0,
      }}
    >
      <Button variant="ghost" size="sm" className="sidebar-settings-button" onClick={() => openSettings('permissions')}>
        <Settings size={15} />
        <span>设置</span>
      </Button>
      <button
        type="button"
        role="switch"
        aria-checked={theme === 'dark'}
        aria-label={theme === 'light' ? '切换到深色主题' : '切换到浅色主题'}
        title={theme === 'light' ? '深色主题' : '浅色主题'}
        onClick={toggleTheme}
        style={{
          position: 'relative',
          flex: '0 0 48px',
          width: 48,
          height: 28,
          padding: 0,
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-full)',
          background: 'transparent',
          color: 'var(--text-muted)',
          cursor: 'pointer',
          WebkitTapHighlightColor: 'transparent',
        }}
      >
        <span
          aria-hidden="true"
          style={{
            position: 'absolute',
            top: 3,
            left: theme === 'light' ? 3 : 23,
            width: 20,
            height: 20,
            display: 'grid',
            placeItems: 'center',
            borderRadius: 'var(--radius-full)',
            background: 'var(--bg-card-hover)',
            color: 'var(--accent-primary)',
            boxShadow: 'var(--shadow-sm)',
            transition: 'left 180ms ease',
          }}
        >
          {theme === 'light' ? <Sun size={13} /> : <Moon size={13} />}
        </span>
      </button>
    </div>
  );
};
