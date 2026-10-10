import React from 'react';
import { ArrowLeft, Trash2 } from 'lucide-react';
import { Group } from '../../types/project';

interface WorkflowGroupDetailProps {
  group: Group;
  onBack: () => void;
  onDelete: (gid: string) => Promise<void>;
}

/**
 * 右侧工具 10 - 分组工作流详情查看面板
 */
export const WorkflowGroupDetail: React.FC<WorkflowGroupDetailProps> = ({
  group,
  onBack,
  onDelete,
}) => {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-workspace)', padding: 16 }}>
      <button
        onClick={onBack}
        style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: 12, marginBottom: 14 }}
      >
        <ArrowLeft size={14} />
        <span>返回业务组列表</span>
      </button>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>{group.name}</h3>
          <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2 }}>
            分支: <code style={{ color: 'var(--accent-cyan)' }}>{group.branch_name}</code>
          </div>
        </div>
        <button
          onClick={() => onDelete(group.group_id)}
          style={{ padding: 5, color: 'var(--accent-rose)' }}
          title="删除分组"
        >
          <Trash2 size={15} />
        </button>
      </div>

      <div className="glass-card" style={{ padding: 14, marginBottom: 14 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>业务总目标</div>
        <div style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.5 }}>
          {group.goal || '执行分配的研发任务'}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8 }}>
          组内协同会话线程 ({group.threads?.length || 0})
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {group.threads?.map((t) => (
            <div
              key={t.thread_id}
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-surface-elevated)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ fontSize: 12.5, fontWeight: 500 }}>{t.title}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>角色: {t.role}</div>
              </div>
              <span style={{ fontSize: 11, color: 'var(--accent-emerald)' }}>就绪 (idle)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
