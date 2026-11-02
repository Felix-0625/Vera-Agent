import { Cpu, Edit3, Grid, Plus, RotateCw, Settings2, Trash2 } from 'lucide-react';
import React, { useState } from 'react';
import { McpServerConfig } from '../../types/settings';
import { Button } from '../common/Button';
import { IconButton } from '../common/IconButton';
import { PageHeading } from '../common/PageHeading';
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4-5)' }}>
      {}
      <PageHeading
        title="MCP"
        description="管理本地与云端 MCP 服务器及其可用工具。"
        divider
        actions={
          <Button
            onClick={onOpenMarket}
            variant="secondary"
            size="md"
            style={{ fontWeight: 600, whiteSpace: 'nowrap' }}
          >
            <Grid size={14} />
            浏览 MCP 市场
          </Button>
        }
      />

      {}
      <div
        className="glass-card"
        style={{
          padding: 'var(--space-4) var(--space-4-5)',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 'var(--space-1-5)',
          }}
        >
          <div style={{ fontSize: 'var(--font-size-subheading)', fontWeight: 600, color: 'var(--text-primary)' }}>
            MCP Servers 管理
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setAddMenuOpen((open) => !open)}
                style={{
                  padding: 'var(--space-1) var(--space-2-5)',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-primary)',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-1)',
                }}
              >
                <Plus size={13} />
                <span>添加</span>
              </button>
              {addMenuOpen && (
                <div
                  role="menu"
                  style={{
                    position: 'absolute',
                    right: 0,
                    top: 'calc(100% + 8px)',
                    width: 180,
                    padding: 'var(--space-1-25)',
                    borderRadius: 'var(--radius-md-wide)',
                    background: 'var(--bg-surface-elevated)',
                    border: '1px solid var(--border-default)',
                    boxShadow: 'var(--shadow-lg)',
                    zIndex: 20,
                  }}
                >
                  <button
                    role="menuitem"
                    className="composer-menu-row"
                    onClick={() => {
                      setAddMenuOpen(false);
                      onOpenMarket?.();
                    }}
                  >
                    <Grid size={14} />
                    <span>从市场添加</span>
                  </button>
                  <button
                    role="menuitem"
                    className="composer-menu-row"
                    onClick={() => {
                      setAddMenuOpen(false);
                      onAdd();
                    }}
                  >
                    <Plus size={14} />
                    <span>手动配置</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', marginBottom: 'var(--space-3-5)' }}>
          管理已添加的 MCP 服务器，可启用、配置或添加新的工具能力。
        </div>

        {servers.length === 0 ? (
          <div
            style={{
              padding: '36px var(--space-5)',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div style={{ fontSize: 'var(--font-size-subheading)', fontWeight: 600, color: 'var(--text-primary)' }}>
              暂无 MCP 服务器
            </div>
            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', marginTop: 'var(--space-1)' }}>
              添加本地或云端 MCP 服务器后，会显示在这里。
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {servers.map((s) => (
              <div
                key={s.id}
                style={{
                  padding: 'var(--space-2-5) var(--space-3-5)',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)' }}>
                  <Cpu size={16} color="var(--accent-cyan)" />
                  <div>
                    <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {s.name}
                    </div>
                    <div
                      style={{
                        fontSize: 'var(--font-size-compact)',
                        color: 'var(--text-muted)',
                        fontFamily: 'monospace',
                      }}
                    >
                      {s.type === 'remote'
                        ? `${s.transport || 'Streamable HTTP'} · ${s.url || ''}`
                        : `${s.command} ${s.args.join(' ')}`}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)' }}>
                  <Switch label={`启用 MCP 服务器：${s.name}`} checked={s.enabled} onChange={() => onToggle(s)} />
                  <div style={{ position: 'relative' }}>
                    <IconButton
                      label="服务器操作"
                      onClick={() => setActiveMenu(activeMenu === s.id ? null : s.id)}
                      size="sm"
                    >
                      <Settings2 size={15} />
                    </IconButton>
                    {activeMenu === s.id && (
                      <div
                        role="menu"
                        style={{
                          position: 'absolute',
                          right: 0,
                          top: 'calc(100% + 4px)',
                          width: 132,
                          padding: 'var(--space-1)',
                          borderRadius: 'var(--radius-md-plus)',
                          background: 'var(--bg-surface-elevated)',
                          border: '1px solid var(--border-default)',
                          boxShadow: 'var(--shadow-lg)',
                          zIndex: 10,
                        }}
                      >
                        <button
                          role="menuitem"
                          className="composer-menu-row"
                          onClick={() => {
                            setActiveMenu(null);
                            onEdit(s);
                          }}
                        >
                          <Edit3 size={13} />
                          <span>编辑</span>
                        </button>
                        <button
                          role="menuitem"
                          className="composer-menu-row"
                          onClick={() => {
                            setActiveMenu(null);
                            void onRestart(s.id);
                          }}
                        >
                          <RotateCw size={13} />
                          <span>重启</span>
                        </button>
                        <button
                          role="menuitem"
                          className="composer-menu-row"
                          onClick={() => {
                            setActiveMenu(null);
                            void onDelete(s.id);
                          }}
                        >
                          <Trash2 size={13} color="var(--accent-rose)" />
                          <span>删除</span>
                        </button>
                      </div>
                    )}
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
