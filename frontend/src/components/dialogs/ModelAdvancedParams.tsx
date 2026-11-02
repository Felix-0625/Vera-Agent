import { ChevronDown, ChevronRight, Info } from 'lucide-react';
import React from 'react';
import { Button } from '../common/Button';
import { TextInput } from '../common/Field';
import { RadioGroup } from '../common/RadioGroup';

interface ModelAdvancedParamsProps {
  provider: string;
  isOpen: boolean;
  onToggle: () => void;
  contextWindow: number | '';
  setContextWindow: (v: number | '') => void;
  outputTokens: number | '';
  setOutputTokens: (v: number | '') => void;
  maxToolCalls: number;
  setMaxToolCalls: (v: number) => void;
  supportsImages: boolean;
  setSupportsImages: (v: boolean) => void;
  thinkingMode: 'auto' | 'enabled' | 'disabled';
  setThinkingMode: (v: 'auto' | 'enabled' | 'disabled') => void;
  temperature: number | '';
  setTemperature: (v: number | '') => void;
  topP: number | '';
  setTopP: (v: number | '') => void;
  topK: number | '';
  setTopK: (v: number | '') => void;
}

const muted: React.CSSProperties = { fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' };
const hint = <Info size={13} color="var(--text-secondary)" />;

interface NumberParameterRowProps {
  label: string;
  labelWidth: number;
  value: number | '';
  placeholder: string;
  centeredLabel?: boolean;
  onChange: (value: number | '') => void;
}

function NumberParameterRow({
  label,
  labelWidth,
  value,
  placeholder,
  centeredLabel = false,
  onChange,
}: NumberParameterRowProps) {
  const inputId = React.useId();
  return (
    <div className="model-parameter-row" style={{ gridTemplateColumns: `${labelWidth}px minmax(0,1fr)` }}>
      <label htmlFor={inputId} className={`model-parameter-row__label${centeredLabel ? ' is-centered' : ''}`}>
        {label}
      </label>
      <TextInput
        id={inputId}
        className="model-parameter-row__input"
        type="number"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value === '' ? '' : Number(event.target.value))}
      />
    </div>
  );
}

export const ModelAdvancedParams: React.FC<ModelAdvancedParamsProps> = (p) => {
  const advancedParamsId = React.useId();
  const presetButton: React.CSSProperties = {
    color: 'var(--text-primary)',
    background: 'transparent',
    padding: 'var(--space-1) var(--space-1-25)',
    fontSize: 'var(--font-size-compact)',
    whiteSpace: 'nowrap',
  };
  return (
    <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-3-5)' }}>
      <button
        type="button"
        onClick={p.onToggle}
        aria-expanded={p.isOpen}
        aria-controls={advancedParamsId}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-1-75)',
          fontSize: 'var(--font-size-md)',
          color: 'var(--text-primary)',
          padding: 0,
        }}
      >
        {p.isOpen ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        <span>高级配置</span>
      </button>
      {p.isOpen && (
        <div
          id={advancedParamsId}
          style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3-5)', marginTop: 'var(--space-4-5)' }}
        >
          <div>
            <div style={{ ...muted, marginBottom: 'var(--space-1-5)' }}>上下文窗口（Token）</div>
            {(
              [
                ['输入', p.contextWindow, p.setContextWindow, ['128k', '256k', '512k', '1M']],
                ['输出', p.outputTokens, p.setOutputTokens, ['4k', '16k', '32k', '128k']],
              ] as const
            ).map(([label, value, set, presets]) => (
              <div
                key={label}
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'minmax(0, 2.2fr) minmax(150px, 1fr)',
                  gap: 'var(--space-2-5)',
                  marginBottom: 'var(--space-1-75)',
                }}
              >
                <NumberParameterRow
                  label={label}
                  labelWidth={84}
                  value={value}
                  placeholder="请输入数值，留空则使用最佳默认值"
                  centeredLabel
                  onChange={set}
                />
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-around' }}>
                  {presets.map((v) => (
                    <Button
                      key={v}
                      type="button"
                      variant="ghost"
                      size="sm"
                      style={presetButton}
                      onClick={() => set(Number(v.replace('k', '000').replace('M', '000000')))}
                    >
                      {v}
                    </Button>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <label className="model-max-tool-calls" style={muted}>
            单次对话工具调用上限（1–500 次）
            <TextInput
              type="number"
              min={1}
              max={500}
              step={1}
              value={p.maxToolCalls}
              onChange={(e) => p.setMaxToolCalls(Number(e.target.value))}
            />
          </label>
          <div>
            <div className="model-advanced-label">支持图片输入 {hint}</div>
            <RadioGroup
              label="支持图片输入"
              value={p.supportsImages ? 'yes' : 'no'}
              options={[
                { value: 'yes', label: '支持' },
                { value: 'no', label: '不支持' },
              ]}
              onChange={(v) => p.setSupportsImages(v === 'yes')}
            />
          </div>
          <div>
            <div className="model-advanced-label">思考模式 {hint}</div>
            {p.provider === 'deepseek' ? (
              <RadioGroup
                label="思考模式"
                value={p.thinkingMode}
                options={[
                  { value: 'auto', label: '跟随模型默认配置' },
                  { value: 'enabled', label: '开启' },
                  { value: 'disabled', label: '关闭' },
                ]}
                onChange={(v) => p.setThinkingMode(v as 'auto' | 'enabled' | 'disabled')}
              />
            ) : (
              <div style={{ fontSize: 'var(--font-size-compact)', color: 'var(--text-muted)' }}>
                该厂商的思考参数由模型默认策略决定；当前只对 DeepSeek 显式设置开关，避免向其他 API 发送不兼容参数。
              </div>
            )}
          </div>
          <div>
            <div
              style={{
                ...muted,
                display: 'flex',
                gap: 'var(--space-2)',
                alignItems: 'center',
                marginBottom: 'var(--space-1-75)',
              }}
            >
              采样参数 {hint}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1-5)' }}>
              <NumberParameterRow
                label="Temperature"
                labelWidth={144}
                value={p.temperature}
                onChange={p.setTemperature}
                placeholder="留空使用最佳配置，或输入 0 ~ 2 之间的数值"
              />
              <NumberParameterRow
                label="Top P"
                labelWidth={144}
                value={p.topP}
                onChange={p.setTopP}
                placeholder="留空使用最佳配置，或输入 0 ~ 1 之间的数值"
              />
              <NumberParameterRow
                label="Top K"
                labelWidth={144}
                value={p.topK}
                onChange={p.setTopK}
                placeholder="留空使用最佳配置，或输入 1 ~ 100 之间的数值"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
