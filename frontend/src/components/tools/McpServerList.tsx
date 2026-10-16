import React, { useState } from 'react';
import { Cpu, Settings as Gear, RotateCw, Trash2, Edit3 } from 'lucide-react';
import { McpServerConfig } from '../../types/settings';
import { Switch } from '../common/Switch';
import { IconButton } from '../common/IconButton';

interface McpServerListProps {
  servers: McpServerConfig[];
  onToggle: (s: McpServerConfig) => Promise<void>;
  onEdit: (s: McpServerConfig) => void;
  onRestart: (id: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

/**
 * 右侧工具 7 - MCP 服务列表组件
 */
export const McpServerList: React.FC<McpServerListProps> = ({
  servers,
  onToggle,
  onEdit,
  onRestart,
  onDelete,
}) => {
  const [menuId, setMenuId] = useState<string | null>(null);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
      {servers.map((s) => (
        <div
          key={s.id}
          className="glass-card"
          style={{ padding: 'var(--space-3) var(--space-3-5)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)' }}>
            <Cpu size={16} color="var(--accent-cyan)" />
            <div>
              <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 600 }}>{s.name}</div>
              <div style={{ fontSize: 'var(--font-size-compact)', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                {s.type === 'remote' ? `${s.transport || 'Streamable HTTP'} · ${s.url || ''}` : `${s.command} ${s.args.join(' ')}`}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)' }}>
            <IconButton
              label="服务选项"
              onClick={() => setMenuId(menuId === s.id ? null : s.id)}
              size="sm"
            >
              <Gear size={14} />
            </IconButton>
            <Switch label={`启用 MCP 服务器：${s.name}`} checked={s.enabled} onChange={() => onToggle(s)} />

            {/* Gear Dropdown */}
            {menuId === s.id && (
              <div
                className="glass-panel animate-fade-in"
                style={{
                  position: 'absolute',
                  right: 48,
                  top: 36,
                  minWidth: 100,
                  borderRadius: 'var(--radius-md)',
                  padding: 'var(--space-1)',
                  zIndex: 20,
                }}
              >
                <button
                  onClick={() => {
                    setMenuId(null);
                    onEdit(s);
                  }}
                  style={{ width: '100%', padding: 'var(--space-1-25) var(--space-2)', fontSize: 'var(--font-size-label)', display: 'flex', gap: 'var(--space-1-5)', alignItems: 'center' }}
                >
                  <Edit3 size={12} />
                  <span>编辑</span>
                </button>
                <button
                  onClick={() => {
                    setMenuId(null);
                    onRestart(s.id);
                  }}
                  style={{ width: '100%', padding: 'var(--space-1-25) var(--space-2)', fontSize: 'var(--font-size-label)', display: 'flex', gap: 'var(--space-1-5)', alignItems: 'center' }}
                >
                  <RotateCw size={12} />
                  <span>重启</span>
                </button>
                <button
                  onClick={() => {
                    setMenuId(null);
                    onDelete(s.id);
                  }}
                  style={{ width: '100%', padding: 'var(--space-1-25) var(--space-2)', fontSize: 'var(--font-size-label)', display: 'flex', gap: 'var(--space-1-5)', alignItems: 'center', color: 'var(--accent-rose)' }}
                >
                  <Trash2 size={12} />
                  <span>删除</span>
                </button>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
