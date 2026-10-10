import React from 'react';
import { PanelLeft, PanelRight, Terminal } from 'lucide-react';
import { useLayoutStore } from '../../stores/layoutStore';
import { ContextUsageIndicator } from './ContextUsageIndicator';

/**
 * 主工作台顶部工具条
 * 严格对齐 Penpot 原型截图：
 * 左侧无任何多余元素，右侧仅包含三键窗口布局控制胶囊
 */
export const WorkspaceHeader: React.FC = () => {
  const { toggleLeft, toggleRight, toggleBottomDrawer, leftCollapsed, rightCollapsed, bottomDrawerOpen } = useLayoutStore();

  return (
    <div
      style={{
        height: 44,
        padding: '0 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
        backgroundColor: 'transparent',
        flexShrink: 0,
      }}
    >
      <ContextUsageIndicator />
      {/* 右侧三键折叠胶囊，严格对齐用户截图 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: 6,
          padding: 2,
          gap: 2,
        }}
      >
        <button
          onClick={toggleLeft}
          title="切换左侧边栏"
          style={{
            padding: '3px 5px',
            borderRadius: 4,
            color: leftCollapsed ? 'var(--text-disabled)' : 'var(--text-secondary)',
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = leftCollapsed ? 'var(--text-disabled)' : 'var(--text-secondary)')}
        >
          <PanelLeft size={14} />
        </button>
        <button
          onClick={toggleBottomDrawer}
          title={bottomDrawerOpen ? '关闭底部终端' : '打开底部终端'}
          aria-label={bottomDrawerOpen ? '关闭底部终端' : '打开底部终端'}
          aria-pressed={bottomDrawerOpen}
          style={{
            padding: '3px 5px',
            borderRadius: 4,
            color: bottomDrawerOpen ? 'var(--accent-cyan)' : 'var(--text-secondary)',
            backgroundColor: bottomDrawerOpen ? 'rgba(34, 211, 238, .1)' : 'transparent',
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = bottomDrawerOpen ? 'var(--accent-cyan)' : 'var(--text-secondary)')}
        >
          <Terminal size={14} />
        </button>
        <button
          onClick={toggleRight}
          title="切换右侧工具栏"
          style={{
            padding: '3px 5px',
            borderRadius: 4,
            color: rightCollapsed ? 'var(--text-disabled)' : 'var(--text-secondary)',
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = rightCollapsed ? 'var(--text-disabled)' : 'var(--text-secondary)')}
        >
          <PanelRight size={14} />
        </button>
      </div>
    </div>
  );
};
