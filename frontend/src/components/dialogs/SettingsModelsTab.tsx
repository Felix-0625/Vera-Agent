import { Edit3, Plus, Settings2, Trash2 } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { ModelConfig } from '../../types/settings';
import { Button } from '../common/Button';
import { IconButton } from '../common/IconButton';
import { PageHeading } from '../common/PageHeading';
import { Switch } from '../common/Switch';

interface SettingsModelsTabProps {
  models: ModelConfig[];
  onEdit: (model: ModelConfig) => void;
  onDelete: (id: string) => Promise<void>;
  onToggle: (model: ModelConfig) => Promise<void>;
  onAdd: () => void;
}

export const SettingsModelsTab: React.FC<SettingsModelsTabProps> = ({ models, onEdit, onDelete, onToggle, onAdd }) => {
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  useEffect(() => {
    if (!activeMenu) return;
    const dismiss = () => setActiveMenu(null);
    document.addEventListener('pointerdown', dismiss);
    document.addEventListener('keydown', dismiss);
    window.addEventListener('resize', dismiss);
    window.addEventListener('scroll', dismiss, true);
    return () => {
      document.removeEventListener('pointerdown', dismiss);
      document.removeEventListener('keydown', dismiss);
      window.removeEventListener('resize', dismiss);
      window.removeEventListener('scroll', dismiss, true);
    };
  }, [activeMenu]);

  const toggleMenu = (event: React.MouseEvent<HTMLButtonElement>, id: string) => {
    event.stopPropagation();
    if (activeMenu === id) {
      setActiveMenu(null);
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    setPosition({
      top: Math.min(rect.bottom + 5, window.innerHeight - 82),
      left: Math.max(8, Math.min(rect.right - 132, window.innerWidth - 140)),
    });
    setActiveMenu(id);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
      <PageHeading title="模型" description="配置 API key，添加更多可用模型，并选择默认模型。" divider />
      <section>
        <h3 style={{ fontSize: 'var(--font-size-lg)', margin: '0 0 var(--space-3)', color: 'var(--text-primary)' }}>
          模型管理
        </h3>
        <Button onClick={onAdd} variant="secondary" size="md" style={{ fontWeight: 600 }}>
          <Plus size={14} />
          添加模型
        </Button>
      </section>
      <section
        style={{
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-lg-plus)',
          overflow: 'hidden',
          background: 'color-mix(in srgb, var(--accent-primary) 8%, var(--bg-surface))',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(200px,2fr) minmax(120px,1.3fr) minmax(150px,1fr)',
            alignItems: 'center',
            padding: 'var(--space-3-5) var(--space-5)',
            fontSize: 'var(--font-size-label)',
            fontWeight: 600,
            color: 'var(--text-muted)',
            background: 'color-mix(in srgb, var(--accent-primary) 8%, var(--bg-surface))',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <span>模型</span>
          <span>服务商</span>
          <span style={{ textAlign: 'right' }}>操作</span>
        </div>
        {models.length === 0 ? (
          <div
            style={{
              minHeight: 285,
              padding: '60px var(--space-5)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'flex-start',
              color: 'var(--text-primary)',
            }}
          >
            <strong style={{ fontSize: 'var(--font-size-body)' }}>尚未配置模型</strong>
            <span
              style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', marginTop: 'var(--space-1-5)' }}
            >
              添加模型并配置服务商 API key 后，会显示在这里。
            </span>
          </div>
        ) : (
          models.map((model) => (
            <div
              key={model.id}
              style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(200px,2fr) minmax(120px,1.3fr) minmax(150px,1fr)',
                alignItems: 'center',
                padding: 'var(--space-3-25) var(--space-5)',
                borderBottom: '1px solid var(--border-subtle)',
                fontSize: 'var(--font-size-control)',
              }}
            >
              <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{model.display_name || model.name}</span>
              <span style={{ color: 'var(--text-secondary)' }}>{model.provider || 'default'}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 13, justifyContent: 'flex-end' }}>
                <IconButton
                  label="模型操作"
                  onClick={(e) => toggleMenu(e, model.id)}
                  aria-expanded={activeMenu === model.id}
                  size="sm"
                >
                  <Settings2 size={15} />
                </IconButton>
                <Switch
                  label={`启用模型：${model.display_name || model.name}`}
                  checked={model.enabled !== false}
                  onChange={() => void onToggle(model)}
                />
              </div>
            </div>
          ))
        )}
      </section>
      {activeMenu &&
        createPortal(
          <div
            role="menu"
            onPointerDown={(e) => e.stopPropagation()}
            style={{
              position: 'fixed',
              top: position.top,
              left: position.left,
              width: 128,
              padding: 'var(--space-1)',
              borderRadius: 'var(--radius-md-plus)',
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-default)',
              boxShadow: 'var(--shadow-lg)',
              zIndex: 9999,
            }}
          >
            <button
              role="menuitem"
              className="composer-menu-row"
              onClick={() => {
                const model = models.find((item) => item.id === activeMenu);
                setActiveMenu(null);
                if (model) onEdit(model);
              }}
            >
              <Edit3 size={13} />
              <span>编辑</span>
            </button>
            <button
              role="menuitem"
              className="composer-menu-row"
              onClick={() => {
                const id = activeMenu;
                setActiveMenu(null);
                void onDelete(id);
              }}
            >
              <Trash2 size={13} color="var(--accent-rose)" />
              <span>删除</span>
            </button>
          </div>,
          document.body,
        )}
    </div>
  );
};
