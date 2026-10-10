import React, { useState } from 'react';
import { Cpu, Settings as Gear, RotateCw, Trash2, Edit3 } from 'lucide-react';
import { McpServerConfig } from '../../types/settings';
import { Switch } from '../common/Switch';

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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {servers.map((s) => (
        <div
          key={s.id}
          className="glass-card"
          style={{ padding: '12px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Cpu size={16} color="var(--accent-cyan)" />
            <div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{s.name}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                {s.command} {s.args.join(' ')}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              onClick={() => setMenuId(menuId === s.id ? null : s.id)}
              style={{ padding: 4, color: 'var(--text-muted)' }}
              title="服务选项"
            >
              <Gear size={14} />
            </button>
            <Switch checked={s.enabled} onChange={() => onToggle(s)} />

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
                  padding: 4,
                  zIndex: 20,
                }}
              >
                <button
                  onClick={() => {
                    setMenuId(null);
                    onEdit(s);
                  }}
                  style={{ width: '100%', padding: '5px 8px', fontSize: 11.5, display: 'flex', gap: 6, alignItems: 'center' }}
                >
                  <Edit3 size={12} />
                  <span>编辑</span>
                </button>
                <button
                  onClick={() => {
                    setMenuId(null);
                    onRestart(s.id);
                  }}
                  style={{ width: '100%', padding: '5px 8px', fontSize: 11.5, display: 'flex', gap: 6, alignItems: 'center' }}
                >
                  <RotateCw size={12} />
                  <span>重启</span>
                </button>
                <button
                  onClick={() => {
                    setMenuId(null);
                    onDelete(s.id);
                  }}
                  style={{ width: '100%', padding: '5px 8px', fontSize: 11.5, display: 'flex', gap: 6, alignItems: 'center', color: 'var(--accent-rose)' }}
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
