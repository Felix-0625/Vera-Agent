import { ArrowLeft, Trash2 } from 'lucide-react';
import React from 'react';
import { Group } from '../../types/project';

interface WorkflowGroupDetailProps {
  group: Group;
  onBack: () => void;
  onDelete: (gid: string) => Promise<void>;
}

export const WorkflowGroupDetail: React.FC<WorkflowGroupDetailProps> = ({ group, onBack, onDelete }) => {
  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'var(--bg-workspace)',
        padding: 'var(--space-4)',
      }}
    >
      <button
        onClick={onBack}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-1-5)',
          color: 'var(--text-muted)',
          fontSize: 'var(--font-size-sm)',
          marginBottom: 'var(--space-3-5)',
        }}
      >
        <ArrowLeft size={14} />
        <span>返回业务组列表</span>
      </button>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 'var(--space-3-5)',
        }}
      >
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>{group.name}</h3>
          <div
            style={{ fontSize: 'var(--font-size-label)', color: 'var(--text-muted)', marginTop: 'var(--space-0-5)' }}
          >
            分支: <code style={{ color: 'var(--accent-cyan)' }}>{group.branch_name}</code>
          </div>
        </div>
        <button
          onClick={() => onDelete(group.group_id)}
          style={{ padding: 'var(--space-1-25)', color: 'var(--accent-rose)' }}
          title="删除分组"
        >
          <Trash2 size={15} />
        </button>
      </div>

      <div className="glass-card" style={{ padding: 'var(--space-3-5)', marginBottom: 'var(--space-3-5)' }}>
        <div
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: 600,
            color: 'var(--text-muted)',
            marginBottom: 'var(--space-1-5)',
          }}
        >
          业务总目标
        </div>
        <div style={{ fontSize: 'var(--font-size-md)', color: 'var(--text-primary)', lineHeight: 1.5 }}>
          {group.goal || '执行分配的研发任务'}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        <div
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: 600,
            color: 'var(--text-muted)',
            marginBottom: 'var(--space-2)',
          }}
        >
          组内协同会话线程 ({group.threads?.length || 0})
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1-5)' }}>
          {group.threads?.map((t) => (
            <div
              key={t.thread_id}
              style={{
                padding: 'var(--space-2-5) var(--space-3)',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-surface-elevated)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ fontSize: 'var(--font-size-control)', fontWeight: 500 }}>{t.title}</div>
                <div style={{ fontSize: 'var(--font-size-compact)', color: 'var(--text-muted)' }}>角色: {t.role}</div>
              </div>
              <span style={{ fontSize: 'var(--font-size-compact)', color: 'var(--accent-emerald)' }}>就绪 (idle)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
