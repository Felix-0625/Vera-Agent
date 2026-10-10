import React, { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown, Sparkles } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { fetchModels } from '../../api/settingsApi';
import { ModelConfig } from '../../types/settings';

const fallbackModels = [
  'deepseek/deepseek-chat',
  'deepseek/deepseek-reasoner',
  'openai/gpt-4o',
  'anthropic/claude-3-5-sonnet',
];

interface ModelDropdownProps { value?: string; onChange?: (model: string) => void; }

export const ModelDropdown: React.FC<ModelDropdownProps> = ({ value, onChange }) => {
  const store = useChatStore();
  const selectedModel = value ?? store.selectedModel;
  const setSelectedModel = onChange ?? store.setSelectedModel;
  const [open, setOpen] = useState(false);
  const [models, setModels] = useState<ModelConfig[]>([]);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchModels().then((data) => setModels(data.models || [])).catch(() => setModels([]));
  }, []);

  useEffect(() => {
    if (!open) return;
    const dismiss = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', dismiss);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', dismiss);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const options = models.length ? models.map((model) => ({ id: model.name, name: model.display_name || model.name, provider: model.provider })) : fallbackModels.map((name) => ({ id: name, name, provider: name.split('/')[0] }));
  const selectedOption = options.find((model) => model.id === selectedModel);
  const selectedConfig = models.find((model) => model.name === selectedModel);
  const selectedLabel = selectedConfig?.display_name || selectedOption?.name || selectedModel;

  return (
    <div ref={rootRef} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen((value) => !value)}
        title={`当前模型：${selectedLabel}`}
        aria-label={`当前模型：${selectedLabel}，点击切换`}
        style={{ height: 28, maxWidth: 250, minWidth: 0, padding: '0 10px', borderRadius: 7, backgroundColor: 'rgba(255,255,255,.045)', color: 'var(--text-secondary)', fontSize: 11.5, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}
      >
        <Sparkles size={13} color="var(--accent-cyan)" />
        <span style={{ maxWidth: 196, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{selectedLabel}</span>
        <ChevronDown size={12} style={{ transform: open ? 'rotate(180deg)' : undefined, transition: 'transform .15s ease' }} />
      </button>
      {open && (
        <div className="glass-panel animate-fade-in" style={{ position: 'absolute', bottom: 'calc(100% + 8px)', left: 0, width: 264, maxWidth: 'min(264px, calc(100vw - 24px))', padding: 6, borderRadius: 11, backgroundColor: '#171b24', border: '1px solid rgba(148, 163, 184, .16)', boxShadow: '0 16px 38px rgba(0,0,0,.42)', zIndex: 70 }}>
          <div style={{ padding: '5px 9px 7px', color: 'var(--text-muted)', fontSize: 10.5, fontWeight: 600, letterSpacing: '.04em' }}>可用模型</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2, maxHeight: 'min(320px, 45vh)', overflowY: 'auto' }}>
            {options.map((model) => {
              const selected = selectedModel === model.id;
              return (
                <button key={model.id} onClick={() => { setSelectedModel(model.id); setOpen(false); }} style={{ width: '100%', minHeight: 38, padding: '6px 9px', borderRadius: 7, display: 'flex', alignItems: 'center', gap: 8, textAlign: 'left', color: selected ? '#d9c7ff' : 'var(--text-primary)', backgroundColor: selected ? 'rgba(124,58,237,.14)' : 'transparent', cursor: 'pointer' }} onMouseEnter={(e) => { if (!selected) e.currentTarget.style.backgroundColor = 'rgba(255,255,255,.055)'; }} onMouseLeave={(e) => { if (!selected) e.currentTarget.style.backgroundColor = 'transparent'; }}>
                  <span style={{ width: 22, height: 22, borderRadius: 6, display: 'grid', placeItems: 'center', backgroundColor: selected ? 'rgba(124,58,237,.2)' : 'rgba(255,255,255,.06)', flexShrink: 0 }}><Sparkles size={12} color={selected ? 'var(--accent-primary)' : 'var(--text-muted)'} /></span>
                  <span style={{ flex: 1, minWidth: 0, fontSize: 11.5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{model.name}</span>
                  <span style={{ color: 'var(--text-muted)', fontSize: 9, textTransform: 'uppercase' }}>{model.provider}</span>
                  {selected && <Check size={13} color="var(--accent-primary)" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
