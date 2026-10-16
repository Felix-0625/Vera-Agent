import React, { useState } from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { useProjectStore } from '../../stores/projectStore';
import { Modal } from '../common/Modal';
import { SelectField, TextArea, TextInput } from '../common/Field';
import { Button } from '../common/Button';
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
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3-5)' }}>
        <div>
          <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 'var(--space-1-5)' }}>
            分组名称 (Group Name)
          </label>
          <TextInput
            type="text"
            required
            value={groupName}
            onChange={(e) => setGroupName(e.target.value)}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 'var(--space-1-5)' }}>
            Git 隔离工作树分支 (Branch Name)
          </label>
          <TextInput
            type="text"
            required
            value={branchName}
            onChange={(e) => setBranchName(e.target.value)}
            className="ui-field--code"
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 'var(--space-1-5)' }}>
            协作拓扑模板 (Multi-Agent Topology)
          </label>
          <SelectField
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
          >
            <option value="supervisor_dev">架构主管-双开发者 (Supervisor-Devs)</option>
            <option value="parallel_peers">并行同级对等组 (Parallel Peers)</option>
          </SelectField>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 'var(--space-1-5)' }}>
            业务总目标 (Goal & Acceptance Criteria)
          </label>
          <TextArea
            rows={3}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2-5)', marginTop: 'var(--space-2)' }}>
          <Button type="button" onClick={() => setProvisionGroupOpen(false)} variant="ghost" size="sm">
            取消
          </Button>
          <Button
            type="submit"
            disabled={loading}
            variant="primary"
            size="sm"
          >
            {loading ? '正在编排分支...' : '立即编排并创建'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
