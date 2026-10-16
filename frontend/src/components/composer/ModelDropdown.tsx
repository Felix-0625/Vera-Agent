import React, { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown, Sparkles } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useLayoutStore } from '../../stores/layoutStore';
import { fetchModels } from '../../api/settingsApi';
import { ModelConfig } from '../../types/settings';
import { Button } from '../common/Button';

const fallbackModels = [
  'deepseek/deepseek-chat',
  'deepseek/deepseek-reasoner',
  'openai/gpt-4o',
  'anthropic/claude-3-5-sonnet',
];

interface ModelDropdownProps { value?: string; onChange?: (model: string) => void; }

export const ModelDropdown: React.FC<ModelDropdownProps> = ({ value, onChange }) => {
  const store = useChatStore();
  const modelCatalogVersion = useLayoutStore((state) => state.modelCatalogVersion);
  const selectedModel = value ?? store.selectedModel;
  const setSelectedModel = onChange ?? store.setSelectedModel;
  const [open, setOpen] = useState(false);
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [modelsLoaded, setModelsLoaded] = useState(false);
  const [modelLoadFailed, setModelLoadFailed] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const modelListId = React.useId();
  const selectedModelRef = useRef(selectedModel);
  const setSelectedModelRef = useRef(setSelectedModel);

  useEffect(() => {
    selectedModelRef.current = selectedModel;
    setSelectedModelRef.current = setSelectedModel;
  }, [selectedModel, setSelectedModel]);

  useEffect(() => {
    let active = true;
    fetchModels().then((data) => {
      if (!active) return;
      const configured = data.models || [];
      setModels(configured);
      setModelLoadFailed(false);
      setModelsLoaded(true);
      const enabled = configured.filter((model) => model.enabled !== false);
      if (configured.length) {
        const currentSelection = selectedModelRef.current;
        const current = enabled.find((model) => model.id === currentSelection || model.name === currentSelection);
        const next = current || enabled.find((model) => model.is_default) || enabled[0];
        setSelectedModelRef.current(next?.id || '');
      } else {
        const currentSelection = selectedModelRef.current;
        setSelectedModelRef.current(fallbackModels.includes(currentSelection) ? currentSelection : fallbackModels[0]);
      }
    }).catch(() => { if (active) { setModels([]); setModelLoadFailed(true); setModelsLoaded(true); } });
    return () => { active = false; };
  }, [modelCatalogVersion]);

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

  const options = !modelsLoaded || modelLoadFailed ? [] : models.length ? models.filter((model) => model.enabled !== false).map((model) => ({ id: model.id || model.name, name: model.display_name || model.name, provider: model.provider })) : fallbackModels.map((name) => ({ id: name, name, provider: name.split('/')[0] }));
  const selectedOption = options.find((model) => model.id === selectedModel);
  const selectedConfig = models.find((model) => model.id === selectedModel || model.name === selectedModel);
  const selectedLabel = selectedConfig?.display_name || selectedOption?.name || selectedModel || (!modelsLoaded ? '正在加载模型…' : modelLoadFailed ? '模型列表加载失败' : models.length ? '没有已启用的模型' : '选择模型');

  return (
    <div ref={rootRef} style={{ position: 'relative' }}>
      <Button
        onClick={() => setOpen((value) => !value)}
        title={`当前模型：${selectedLabel}`}
        aria-label={`当前模型：${selectedLabel}，点击切换`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={modelListId}
        variant="ghost"
        size="sm"
        className="model-dropdown-trigger"
        icon={<Sparkles size={13} color="var(--accent-cyan)" aria-hidden="true"/>}
      >
        <span style={{ maxWidth: 196, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{selectedLabel}</span>
        <ChevronDown size={12} style={{ transform: open ? 'rotate(180deg)' : undefined, transition: 'transform .15s ease' }} />
      </Button>
      {open && (
        <div className="glass-panel animate-fade-in" style={{ position: 'absolute', bottom: 'calc(100% + 8px)', left: 0, width: 264, maxWidth: 'min(264px, calc(100vw - 24px))', padding: 'var(--space-1-5)', borderRadius: 'var(--radius-lg-minus)', backgroundColor: 'var(--bg-surface-elevated)', border: '1px solid var(--border-default)', boxShadow: 'var(--shadow-lg)', zIndex: 70 }}>
          <div style={{ padding: 'var(--space-1-25) var(--space-2-25) var(--space-1-75)', color: 'var(--text-muted)', fontSize: 'var(--font-size-subtle)', fontWeight: 600, letterSpacing: '.04em' }}>可用模型</div>
          <div id={modelListId} role="listbox" aria-label="可用模型" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-0-5)', maxHeight: 'min(320px, 45vh)', overflowY: 'auto' }}>
            {options.length === 0 && <div style={{ padding: 'var(--space-2-5) var(--space-2-25)', color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)' }}>{!modelsLoaded ? '正在加载模型列表…' : modelLoadFailed ? '无法加载模型列表，请检查服务连接后重试。' : '没有已启用的模型，请先到设置中启用模型。'}</div>}
            {options.map((model) => {
              const selected = selectedModel === model.id;
              return (
                <Button key={model.id} type="button" role="option" aria-selected={selected} variant="ghost" size="sm" className={`model-dropdown-option${selected ? ' is-selected' : ''}`} onClick={() => { setSelectedModel(model.id); setOpen(false); }}>
                  <span className={`model-dropdown-option-icon${selected ? ' is-selected' : ''}`}><Sparkles size={12} color={selected ? 'var(--accent-primary)' : 'var(--text-muted)'} /></span>
                  <span style={{ flex: 1, minWidth: 0, fontSize: 'var(--font-size-label)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{model.name}</span>
                  <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-tiny)', textTransform: 'uppercase' }}>{model.provider}</span>
                  {selected && <Check size={13} color="var(--accent-primary)" />}
                </Button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
