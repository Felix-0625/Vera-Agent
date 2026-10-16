import React from 'react';
import { ArrowRight, Check, ExternalLink, Shield, Pencil, FolderPlus, Folder, Terminal, CirclePlus, Search, Users } from 'lucide-react';
import { PermissionCategory, PermissionsConfig } from '../../types/settings';
import { Switch } from '../common/Switch';
import { TextInput } from '../common/Field';
import { PageHeading } from '../common/PageHeading';

interface SettingsPermissionsTabProps {
  permissions: PermissionsConfig;
  onSave: (mode: PermissionsConfig['default_mode'], approvalActions?: PermissionCategory[], operationScope?: PermissionsConfig['operation_scope'], maxToolAttempts?: number) => Promise<void>;
}

const actions: Array<{ id: PermissionCategory; label: string; description: string; icon: React.ReactNode }> = [
  { id: 'read', label: '读取文件', description: '查看项目文件和目录，不更改内容。', icon: <Folder size={15} /> },
  { id: 'create', label: '新增文件', description: '在项目范围内创建文件。', icon: <FolderPlus size={15} /> },
  { id: 'edit', label: '修改文件', description: '在项目范围内修改已有文件。', icon: <Pencil size={15} /> },
  { id: 'terminal', label: '终端命令', description: '非只读白名单命令需要确认；命令识别不是系统沙箱。', icon: <Terminal size={15} /> },
  { id: 'search', label: '浏览与搜索', description: '网页搜索和读取网页内容，会向外部网站发送请求。', icon: <Search size={15} /> },
  { id: 'mcp', label: 'MCP 工具', description: '外部 MCP 工具可能读取或修改外部数据。', icon: <CirclePlus size={15} /> },
  { id: 'delegation', label: '子智能体协作', description: '启动研究员或审查员子智能体。', icon: <Users size={15} /> },
];

export const SettingsPermissionsTab: React.FC<SettingsPermissionsTabProps> = ({ permissions, onSave }) => {
  const modes: Array<{
    id: PermissionsConfig['default_mode'];
    name: string;
    tag: string;
    description: string;
    icon: React.ReactNode;
  }> = [
    { id: 'allow_all', name: '完全允许', tag: '无逐项审批', description: '工具调用不逐项询问；文件操作范围仍按下方边界执行。', icon: <ArrowRight size={18} /> },
    { id: 'auto', name: '自动审批', tag: '低风险自动放行', description: '项目内文件操作与常见只读命令自动执行；高风险或未识别操作仍询问。', icon: <Shield size={18} /> },
    { id: 'manual', name: '人工审批', tag: '按工具规则询问', description: '仅对下方开启“询问”的工具调用审批；未识别工具默认询问。', icon: <ExternalLink size={18} /> },
  ];

  const toggleAction = (id: PermissionCategory, ask: boolean) => {
    const current = new Set(permissions.approval_actions || []);
    if (ask) current.add(id);
    else current.delete(id);
    void onSave(permissions.default_mode, [...current]);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', paddingBottom: 'var(--space-3)' }}>
      <PageHeading title="权限审批" description="选择工具审批模式；仅人工审批模式显示逐类询问设置。" />

      <section>
        <h3 style={{ fontSize: 'var(--font-size-lg)', margin: '0 0 var(--space-1)', color: 'var(--text-primary)' }}>权限模式</h3>
        <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', margin: '0 0 var(--space-2-5)' }}>审批模式与文件路径范围分开生效。</p>
        <div className="permission-mode-grid">
          {modes.map((item) => {
            const selected = permissions.default_mode === item.id;
            return <button key={item.id} type="button" onClick={() => void onSave(item.id)} className={`permission-mode-card${selected ? ' selected' : ''}`}>
              <div className="permission-mode-top">
                <span className={`permission-mode-icon ${item.id}`}>{item.icon}</span>
                <strong>{item.name}</strong>
                <small>{selected ? '当前模式' : item.tag}</small>
              </div>
              <p>{item.description}</p>
              {selected && <span className="permission-selected"><Check size={12} /> 当前选择：{item.name}</span>}
            </button>;
          })}
        </div>
      </section>

      <section className="permission-tools-card">
        <h3>单次工具失败重试上限</h3>
        <p>同一工具操作连续失败后，最多允许的总尝试次数，包含首次调用；成功后重新计数。范围为 1–20 次。</p>
        <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-4)' }}>
          <span>每个相同操作的最大尝试次数</span>
          <TextInput
            type="number"
            min={1}
            max={20}
            step={1}
            value={permissions.max_tool_attempts ?? 3}
            onChange={(event) => {
              const value = event.currentTarget.valueAsNumber;
              if (Number.isInteger(value) && value >= 1 && value <= 20) {
                void onSave(permissions.default_mode, permissions.approval_actions, permissions.operation_scope, value);
              }
            }}
            style={{ width: 100 }}
          />
        </label>
      </section>

      <section className="permission-tools-card">
        <h3>文件操作范围</h3>
        <p>此范围只约束文件工具；终端、网页搜索等工具按各自权限规则执行。</p>
        <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap', marginTop: 'var(--space-3)' }}>
          {[
            { id: 'project_only' as const, title: '文件仅限项目内部', detail: '文件工具只可读取和修改当前项目内的文件。' },
            { id: 'project_write_external_readonly' as const, title: '项目内读写，项目外只读', detail: '文件工具可修改项目内文件，项目外文件仅可读取。' },
          ].map(option => <button key={option.id} type="button" onClick={() => void onSave(permissions.default_mode, permissions.approval_actions, option.id)} aria-pressed={(permissions.operation_scope || 'project_write_external_readonly') === option.id} style={{ flex: '1 1 250px', padding: 'var(--space-3) var(--space-3-5)', borderRadius: 'var(--radius-md-wide)', border: `1px solid ${(permissions.operation_scope || 'project_write_external_readonly') === option.id ? 'var(--accent-primary)' : 'var(--border-default)'}`, background: (permissions.operation_scope || 'project_write_external_readonly') === option.id ? 'color-mix(in srgb, var(--accent-primary) 8%, var(--bg-surface))' : 'transparent', color: 'var(--text-primary)', textAlign: 'left' }}><strong style={{ display: 'block', fontSize: 'var(--font-size-sm)' }}>{option.title}</strong><small style={{ display: 'block', marginTop: 'var(--space-1-25)', color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)' }}>{option.detail}</small></button>)}
        </div>
      </section>

      {permissions.default_mode === 'manual' && <section className="permission-tools-card">
        <h3>工具权限</h3>
        <p>开启“询问”后，每次调用此类工具都需要确认；读取、浏览搜索和子智能体也可分别设置。</p>
        <div>
          {actions.map((action, index) => {
            const asksForConfirmation = (permissions.approval_actions || []).includes(action.id);
            const label = asksForConfirmation ? '询问' : '允许';
            return <div className="permission-action-row" key={action.id}>
              <span className={`permission-action-icon ${action.id}`}>{action.icon}</span>
              <strong>{action.label}</strong>
              <small>{action.description}</small>
              <div className={`permission-switch ${asksForConfirmation ? 'allowed' : ''}`}><span>{label}</span><Switch label={`是否对“${action.label}”进行调用审批`} checked={asksForConfirmation} onChange={(checked) => toggleAction(action.id, checked)} /></div>
              {index < actions.length - 1 && <i />}
            </div>;
          })}
        </div>
      </section>}
    </div>
  );
};
