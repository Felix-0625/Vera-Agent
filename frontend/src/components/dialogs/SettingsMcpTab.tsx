import React, { useState } from 'react';
import { Plus, Grid, Edit3, Trash2, Cpu, Settings2, RotateCw } from 'lucide-react';
import { McpServerConfig } from '../../types/settings';
import { Switch } from '../common/Switch';

interface SettingsMcpTabProps {
  servers: McpServerConfig[];
  onToggle: (s: McpServerConfig) => Promise<void>;
  onEdit: (s: McpServerConfig) => void;
  onDelete: (id: string) => Promise<void>;
  onRestart: (id: string) => Promise<void>;
  onAdd: () => void;
  onOpenMarket?: () => void;
}

/**
 * 设置中心 - MCP Tab
 * 严格对齐 Penpot 画板 "系统设置 · MCP"
 */
export const SettingsMcpTab: React.FC<SettingsMcpTabProps> = ({
  servers,
  onToggle,
  onEdit,
  onDelete,
  onRestart,
  onAdd,
  onOpenMarket,
}) => {
  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      {/* 标题与描述 */}
      <div style={{ display: 'flex', alignItems: 'start', justifyContent: 'space-between', gap: 20, borderBottom: '1px solid var(--border-subtle)', paddingBottom: 20 }}>
        <div><h2 style={{ fontSize: 24, lineHeight: 1.25, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
          MCP
        </h2>
        <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 4, marginBottom: 0 }}>
          管理本地与云端 MCP 服务器及其可用工具。
        </p></div>
        <button onClick={onOpenMarket} style={{ padding: '10px 14px', borderRadius: 10, backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)', fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 7, whiteSpace: 'nowrap' }}><Grid size={14} />浏览 MCP 市场</button>
      </div>

      {/* 主卡片 */}
      <div
        className="glass-card"
        style={{
          padding: '16px 18px',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>
            MCP Servers 管理
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ position: 'relative' }}>
            <button
              onClick={() => setAddMenuOpen((open) => !open)}
              style={{
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-primary)',
                fontSize: 12,
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <Plus size={13} />
              <span>添加</span>
            </button>
            {addMenuOpen && <div role="menu" style={{ position: 'absolute', right: 0, top: 'calc(100% + 8px)', width: 180, padding: 5, borderRadius: 10, background: '#171b24', border: '1px solid var(--border-default)', boxShadow: '0 14px 30px rgba(0,0,0,.42)', zIndex: 20 }}>
              <button role="menuitem" className="composer-menu-row" onClick={() => { setAddMenuOpen(false); onOpenMarket?.(); }}><Grid size={14} /><span>从市场添加</span></button>
              <button role="menuitem" className="composer-menu-row" onClick={() => { setAddMenuOpen(false); onAdd(); }}><Plus size={14} /><span>手动配置</span></button>
            </div>}
            </div>
          </div>
        </div>

        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
          管理已添加的 MCP 服务器，可启用、配置或添加新的工具能力。
        </div>

        {servers.length === 0 ? (
          <div
            style={{
              padding: '36px 20px',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>
              暂无 MCP 服务器
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
              添加本地或云端 MCP 服务器后，会显示在这里。
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {servers.map((s) => (
              <div
                key={s.id}
                style={{
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Cpu size={16} color="var(--accent-cyan)" />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {s.name}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                      {s.command} {s.args.join(' ')}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Switch checked={s.enabled} onChange={() => onToggle(s)} />
                  <div style={{ position: 'relative' }}>
                    <button onClick={() => setActiveMenu(activeMenu === s.id ? null : s.id)} style={{ padding: 5, color: 'var(--text-muted)' }} title="服务器操作" aria-label="服务器操作"><Settings2 size={15} /></button>
                    {activeMenu === s.id && <div role="menu" style={{ position: 'absolute', right: 0, top: 'calc(100% + 4px)', width: 132, padding: 4, borderRadius: 9, background: '#171b24', border: '1px solid var(--border-default)', boxShadow: '0 12px 28px rgba(0,0,0,.42)', zIndex: 10 }}>
                      <button role="menuitem" className="composer-menu-row" onClick={() => { setActiveMenu(null); onEdit(s); }}><Edit3 size={13} /><span>编辑</span></button>
                      <button role="menuitem" className="composer-menu-row" onClick={() => { setActiveMenu(null); void onRestart(s.id); }}><RotateCw size={13} /><span>重启</span></button>
                      <button role="menuitem" className="composer-menu-row" onClick={() => { setActiveMenu(null); void onDelete(s.id); }}><Trash2 size={13} color="var(--accent-rose)" /><span>删除</span></button>
                    </div>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
