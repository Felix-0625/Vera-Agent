import React from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { BrandHeader } from './BrandHeader';
import { NavLinks, ScheduledTasksLink } from './NavLinks';
import { ProjectTree } from './ProjectTree';
import { SidebarFooter } from './SidebarFooter';
import { PinnedItems } from './PinnedItems';
import { RecentConversations } from './RecentConversations';

export const LeftSidebar: React.FC = () => {
  const { leftCollapsed, leftWidth } = useLayoutStore();

  if (leftCollapsed) return null;

  return (
    <aside
      className="glass-panel"
      style={{
        width: leftWidth,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'var(--bg-sidebar)',
        borderRight: '1px solid var(--border-subtle)',
        userSelect: 'none',
        flexShrink: 0,
      }}
    >
      <BrandHeader />
      <NavLinks />
      <ScheduledTasksLink />
      <div style={{ flex:1,minHeight:0,overflowY:'auto',display:'flex',flexDirection:'column',gap:14,paddingTop:4 }}>
        <PinnedItems />
        <ProjectTree />
        <RecentConversations />
      </div>
      <SidebarFooter />
    </aside>
  );
};
