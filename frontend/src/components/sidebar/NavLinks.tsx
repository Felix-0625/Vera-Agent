import React from 'react';
import { Plus, History, Clock } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';

/**
 * 侧边栏顶部快捷导航区
 * 严格按照用户 Penpot 截图实现：
 * 1. 顶部 "+ 新建对话" 按钮
 * 2. 紧凑左对齐 "对话历史" 与 "计划任务"
 */
export const NavLinks: React.FC = () => {
  const { openDraftConversation } = useChatStore();
  const { currentProject } = useProjectStore();
  const { setHistoryOpen } = useLayoutStore();

  const handleNewConversation = () => {
    openDraftConversation(currentProject?.id || null);
    // 聚焦中心输入框，确保用户立即输入
    setTimeout(() => {
      const textarea = document.querySelector('textarea');
      if (textarea) textarea.focus();
    }, 50);
  };

  return (
    <div style={{ padding: '10px 12px 6px', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
      {/* "+ 新建对话" 按钮：严格对齐用户 Penpot 截图 (左对齐紫框胶囊) */}
      <button
        onClick={handleNewConversation}
        style={{
          width: '100%',
          height: 36,
          borderRadius: 8,
          backgroundColor: 'rgba(20, 21, 29, 0.6)',
          border: '1.5px solid #7C3AED',
          color: '#FFFFFF',
          fontSize: 13,
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-start',
          padding: '0 12px',
          gap: 8,
          cursor: 'pointer',
          marginBottom: 10,
          transition: 'all 0.15s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(124, 58, 237, 0.15)';
          e.currentTarget.style.borderColor = '#8B5CF6';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(20, 21, 29, 0.6)';
          e.currentTarget.style.borderColor = '#7C3AED';
        }}
      >
        <Plus size={16} color="#A78BFA" />
        <span>新建对话</span>
      </button>

      {/* 对话历史与计划任务：严格左对齐与新建对话图标列对齐 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <button
          onClick={() => setHistoryOpen(true)}
          style={{
            width: '100%',
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-secondary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-start',
            gap: 10,
            fontSize: 12.5,
            cursor: 'pointer',
            textAlign: 'left',
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
          <History size={15} color="var(--text-muted)" />
          <span>对话历史</span>
        </button>

      </div>
    </div>
  );
};

export const ScheduledTasksLink: React.FC = () => {
  const { setScheduledTasksOpen } = useLayoutStore();
  return <div style={{ padding:'0 12px' }}><button onClick={()=>setScheduledTasksOpen(true)} style={{width:'100%',padding:'6px 12px',borderRadius:'var(--radius-sm)',color:'var(--text-secondary)',display:'flex',alignItems:'center',justifyContent:'flex-start',gap:10,fontSize:12.5,textAlign:'left'}} onMouseEnter={event=>{event.currentTarget.style.backgroundColor='rgba(255,255,255,.05)';event.currentTarget.style.color='var(--text-primary)';}} onMouseLeave={event=>{event.currentTarget.style.backgroundColor='transparent';event.currentTarget.style.color='var(--text-secondary)';}}><Clock size={15} color="var(--text-muted)"/><span>计划任务</span></button></div>;
};
