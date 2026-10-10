import React, { useState } from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';
import { Modal } from '../common/Modal';
import { provisionGroup } from '../../api/projectApi';

export const ProvisionGroupDialog: React.FC = () => {
  const { provisionGroupOpen, setProvisionGroupOpen } = useLayoutStore();
  const { loadGroups } = useProjectStore();

  const [groupName, setGroupName] = useState('业务研发协作组');
  const [branchName, setBranchName] = useState('feat/module-iteration');
  const [templateId, setTemplateId] = useState('supervisor_dev');
  const [goal, setGoal] = useState('执行系统解耦与功能特性研发任务');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!branchName.trim()) return;

    setLoading(true);
    try {
      await provisionGroup({
        group_name: groupName.trim(),
        branch_name: branchName.trim(),
        template_id: templateId,
        goal: goal.trim(),
      });
      await loadGroups();
      setProvisionGroupOpen(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={provisionGroupOpen}
      onClose={() => setProvisionGroupOpen(false)}
      title="一键编排多 Agent 业务分组 (Provision Group)"
      width={560}
    >
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
            分组名称 (Group Name)
          </label>
          <input
            type="text"
            required
            value={groupName}
            onChange={(e) => setGroupName(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-surface-elevated)', border: '1px solid var(--border-default)', fontSize: 13, color: 'var(--text-primary)' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
            Git 隔离工作树分支 (Branch Name)
          </label>
          <input
            type="text"
            required
            value={branchName}
            onChange={(e) => setBranchName(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-surface-elevated)', border: '1px solid var(--border-default)', fontSize: 13, fontFamily: 'monospace', color: 'var(--text-primary)' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
            协作拓扑模板 (Multi-Agent Topology)
          </label>
          <select
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-surface-elevated)', border: '1px solid var(--border-default)', fontSize: 13, color: 'var(--text-primary)' }}
          >
            <option value="supervisor_dev">架构主管-双开发者 (Supervisor-Devs)</option>
            <option value="parallel_peers">并行同级对等组 (Parallel Peers)</option>
          </select>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
            业务总目标 (Goal & Acceptance Criteria)
          </label>
          <textarea
            rows={3}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-surface-elevated)', border: '1px solid var(--border-default)', fontSize: 13, color: 'var(--text-primary)' }}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
          <button type="button" onClick={() => setProvisionGroupOpen(false)} style={{ padding: '7px 14px', borderRadius: 'var(--radius-sm)', color: 'var(--text-muted)', fontSize: 12.5 }}>
            取消
          </button>
          <button
            type="submit"
            disabled={loading}
            style={{ padding: '7px 18px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--accent-primary)', color: '#fff', fontSize: 12.5, fontWeight: 600 }}
          >
            {loading ? '正在编排分支...' : '立即编排并创建'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
