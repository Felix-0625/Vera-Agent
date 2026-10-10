import React, { useState } from 'react';
import { Layers, Plus, ArrowRight } from 'lucide-react';
import { useProjectStore } from '../../stores/projectStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { Group } from '../../types/project';
import { deleteGroup } from '../../api/projectApi';
import { WorkflowGroupDetail } from './WorkflowGroupDetail';

/**
 * 右侧工具 10 - 业务分组拓扑与工作流管理
 */
export const WorkflowTab: React.FC = () => {
  const { groups, loadGroups } = useProjectStore();
  const { setProvisionGroupOpen } = useLayoutStore();
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);

  const handleDelete = async (gid: string) => {
    if (window.confirm('确定要删除此业务分组及绑定的工作树吗？')) {
      await deleteGroup(gid);
      loadGroups();
      if (selectedGroup?.group_id === gid) setSelectedGroup(null);
    }
  };

  if (selectedGroup) {
    return (
      <WorkflowGroupDetail
        group={selectedGroup}
        onBack={() => setSelectedGroup(null)}
        onDelete={handleDelete}
      />
    );
  }

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 16, backgroundColor: 'var(--bg-workspace)' }}>
      {/* 顶部标题与编排新建操作 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600 }}>
          <Layers size={16} color="var(--accent-emerald)" />
          <span>分组管理 · 实时工作流</span>
        </div>
        <button
          onClick={() => setProvisionGroupOpen(true)}
          style={{
            padding: '4px 10px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--accent-primary)',
            color: '#fff',
            fontSize: 11.5,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <Plus size={13} />
          <span>新建分组</span>
        </button>
      </div>

      {/* 业务组列表 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {groups.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: 40, fontSize: 13 }}>
            尚未创建业务分组，点击上方按钮进行一键模版编排
          </div>
        ) : (
          groups.map((g) => (
            <div
              key={g.group_id}
              onClick={() => setSelectedGroup(g)}
              className="glass-card"
              style={{
                padding: '12px 14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
              }}
            >
              <div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{g.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                  分支: {g.branch_name} · 拓扑: {g.topology_type || 'supervisor_dev'}
                </div>
              </div>
              <ArrowRight size={14} color="var(--text-muted)" />
            </div>
          ))
        )}
      </div>
    </div>
  );
};
