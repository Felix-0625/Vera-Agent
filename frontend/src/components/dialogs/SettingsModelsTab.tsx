import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Plus, Edit3, Trash2, Settings2 } from 'lucide-react';
import { ModelConfig } from '../../types/settings';
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
    if (activeMenu === id) { setActiveMenu(null); return; }
    const rect = event.currentTarget.getBoundingClientRect();
    setPosition({ top: Math.min(rect.bottom + 5, window.innerHeight - 82), left: Math.max(8, Math.min(rect.right - 132, window.innerWidth - 140)) });
    setActiveMenu(id);
  };

  return <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
    <header style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: 20 }}>
      <h2 style={{ fontSize: 24, lineHeight: 1.25, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>模型</h2>
      <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 7, marginBottom: 0 }}>配置 API key，添加更多可用模型，并选择默认模型。</p>
    </header>
    <section>
      <h3 style={{ fontSize: 15, margin: '0 0 12px', color: 'var(--text-primary)' }}>模型管理</h3>
      <button onClick={onAdd} style={{ padding: '9px 13px', borderRadius: 10, backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)', fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}><Plus size={14} />添加模型</button>
    </section>
    <section style={{ border: '1px solid var(--border-default)', borderRadius: 14, overflow: 'hidden', background: '#151b25' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(200px,2fr) minmax(120px,1.3fr) minmax(150px,1fr)', alignItems: 'center', padding: '14px 20px', fontSize: 11.5, fontWeight: 600, color: 'var(--text-muted)', background: '#1c2531', borderBottom: '1px solid var(--border-subtle)' }}><span>模型</span><span>服务商</span><span style={{ textAlign: 'right' }}>操作</span></div>
      {models.length === 0 ? <div style={{ minHeight: 285, padding: '60px 20px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'flex-start', color: 'var(--text-primary)' }}><strong style={{ fontSize: 14 }}>尚未配置模型</strong><span style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>添加模型并配置服务商 API key 后，会显示在这里。</span></div> : models.map(model => <div key={model.id} style={{ display: 'grid', gridTemplateColumns: 'minmax(200px,2fr) minmax(120px,1.3fr) minmax(150px,1fr)', alignItems: 'center', padding: '13px 20px', borderBottom: '1px solid rgba(148,163,184,.12)', fontSize: 12.5 }}>
        <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{model.display_name || model.name}</span>
        <span style={{ color: 'var(--text-secondary)' }}>{model.provider || 'default'}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 13, justifyContent: 'flex-end' }}>
          <button onClick={e => toggleMenu(e, model.id)} title="模型操作" aria-label="模型操作" aria-expanded={activeMenu === model.id} style={{ color: 'var(--text-muted)', padding: 4 }}><Settings2 size={15} /></button>
          <Switch checked={model.enabled !== false} onChange={() => void onToggle(model)} />
        </div>
      </div>)}
    </section>
    {activeMenu && createPortal(<div role="menu" onPointerDown={e => e.stopPropagation()} style={{ position: 'fixed', top: position.top, left: position.left, width: 128, padding: 4, borderRadius: 9, background: '#171b24', border: '1px solid var(--border-default)', boxShadow: '0 12px 28px rgba(0,0,0,.42)', zIndex: 9999 }}>
      <button role="menuitem" className="composer-menu-row" onClick={() => { const model = models.find(item => item.id === activeMenu); setActiveMenu(null); if (model) onEdit(model); }}><Edit3 size={13} /><span>编辑</span></button>
      <button role="menuitem" className="composer-menu-row" onClick={() => { const id = activeMenu; setActiveMenu(null); void onDelete(id); }}><Trash2 size={13} color="var(--accent-rose)" /><span>删除</span></button>
    </div>, document.body)}
  </div>;
};
