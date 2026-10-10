import React from 'react';
import { ArrowRight, Check, ExternalLink, Shield, Zap, Trash2, Pencil, FolderPlus, Folder, Terminal, CirclePlus } from 'lucide-react';
import { PermissionsConfig } from '../../types/settings';
import { Switch } from '../common/Switch';

interface SettingsPermissionsTabProps {
  permissions: PermissionsConfig;
  onSave: (mode: 'confirm' | 'yolo' | 'human', whitelistActions?: string[], maxToolAttempts?: number, operationScope?: PermissionsConfig['operation_scope']) => Promise<void>;
}

const actions = [
  { id: 'read', label: '读取文件', description: '查看项目文件和目录，不更改内容。', icon: <Folder size={15} /> },
  { id: 'create', label: '新增文件', description: '写入新文件前请求确认。', icon: <FolderPlus size={15} /> },
  { id: 'edit', label: '修改文件', description: '展示目标文件和修改计划后请求确认。', icon: <Pencil size={15} /> },
  { id: 'delete', label: '删除文件', description: '列出预计删除文件，确认后再执行。', icon: <Trash2 size={15} /> },
  { id: 'terminal', label: '终端命令', description: '运行命令前展示命令内容与影响范围。', icon: <Terminal size={15} /> },
  { id: 'mcp', label: 'MCP / Skill 调用', description: '外部工具调用前逐项确认。', icon: <CirclePlus size={15} /> },
];

export const SettingsPermissionsTab: React.FC<SettingsPermissionsTabProps> = ({ permissions, onSave }) => {
  const modes: Array<{
    id: 'human' | 'yolo' | 'confirm';
    name: string;
    tag: string;
    description: string;
    icon: React.ReactNode;
  }> = [
    { id: 'human', name: '完全允许', tag: '直接执行', description: '文件操作和工具调用均不逐项询问。Agent 按当前设置直接执行。', icon: <ArrowRight size={18} /> },
    { id: 'yolo', name: '自动审批', tag: '按策略判断', description: 'Agent 根据风险与策略自动审批；高风险操作仍可要求确认。', icon: <Shield size={18} /> },
    { id: 'confirm', name: '手动审批', tag: '当前模式', description: '需要新增、修改或删除文件时，在对话输入区上方展示审批提示。', icon: <ExternalLink size={18} /> },
  ];

  const toggleAction = (id: string, enabled: boolean) => {
    const current = new Set(permissions.whitelist_actions || []);
    // Every tool permission uses the same switch semantics: on asks first;
    // off allows the action without a per-call prompt.
    const allowed = !enabled;
    if (allowed) current.add(id);
    else current.delete(id);
    void onSave(permissions.default_mode, [...current]);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, paddingBottom: 12 }}>
      <header>
        <h2 style={{ fontSize: 24, lineHeight: 1.25, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>权限审批</h2>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 7, marginBottom: 0 }}>配置文件操作审批方式、工具调用上限，以及各类工具是否需要逐项确认。</p>
      </header>

      <section>
        <h3 style={{ fontSize: 15, margin: '0 0 4px', color: 'var(--text-primary)' }}>权限模式</h3>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 10px' }}>选择 Agent 开始执行任务时采用的审批策略。</p>
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

      <section className="permission-limit-card">
        <div><strong>单次工具最大调用次数</strong><small>单个工具调用失败时最多尝试的总次数（包含首次调用）。</small></div>
        <label><input aria-label="单次工具最大调用次数" type="number" min={1} max={20} value={permissions.max_tool_attempts ?? 3} onChange={(event) => { const value = Number(event.target.value); if (Number.isInteger(value) && value >= 1 && value <= 20) void onSave(permissions.default_mode, permissions.whitelist_actions, value); }} /><span>次</span></label>
      </section>

      <section className="permission-tools-card">
        <h3>操作范围</h3>
        <p>文件读取和写入会按此范围校验；subagent 的写入还会限制在其独立工作区。终端命令目前仍以应用运行账户执行，尚未实现操作系统级文件沙箱。</p>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 12 }}>
          {[
            { id: 'project_only' as const, title: '仅项目内部', detail: '只允许读取和操作当前项目。' },
            { id: 'project_write_external_readonly' as const, title: '项目内可操作，项目外只读', detail: '项目文件可按工具权限修改；项目外文件仅可读取。' },
          ].map(option => <button key={option.id} type="button" onClick={() => void onSave(permissions.default_mode, permissions.whitelist_actions, permissions.max_tool_attempts, option.id)} aria-pressed={(permissions.operation_scope || 'project_write_external_readonly') === option.id} style={{ flex: '1 1 250px', padding: '12px 14px', borderRadius: 10, border: `1px solid ${(permissions.operation_scope || 'project_write_external_readonly') === option.id ? '#3688ff' : 'var(--border-default)'}`, background: (permissions.operation_scope || 'project_write_external_readonly') === option.id ? 'rgba(54,136,255,.1)' : 'transparent', color: 'var(--text-primary)', textAlign: 'left' }}><strong style={{ display: 'block', fontSize: 12 }}>{option.title}</strong><small style={{ display: 'block', marginTop: 5, color: 'var(--text-muted)', fontSize: 11 }}>{option.detail}</small></button>)}
        </div>
      </section>

      <section className="permission-tools-card">
        <h3>工具权限</h3>
        <p>按工具类型设置为「询问」或「允许」，作为当前权限模式的细项控制。</p>
        <div>
          {actions.map((action, index) => {
            const allowed = (permissions.whitelist_actions || []).includes(action.id);
            const asksForConfirmation = !allowed;
            const checked = asksForConfirmation;
            const active = asksForConfirmation;
            const label = asksForConfirmation ? '询问' : '允许';
            return <div className="permission-action-row" key={action.id}>
              <span className={`permission-action-icon ${action.id}`}>{action.icon}</span>
              <strong>{action.label}</strong>
              <small>{action.description}</small>
              <div className={`permission-switch ${active ? 'allowed' : ''}`}><span>{label}</span><Switch checked={checked} onChange={(nextChecked) => toggleAction(action.id, nextChecked)} /></div>
              {index < actions.length - 1 && <i />}
            </div>;
          })}
        </div>
      </section>
    </div>
  );
};
