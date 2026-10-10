import React from 'react';
import { ChevronDown, ChevronRight, Info } from 'lucide-react';

interface ModelAdvancedParamsProps {
  isOpen: boolean; onToggle: () => void;
  family: string; setFamily: (v: string) => void;
  contextWindow: number | ''; setContextWindow: (v: number | '') => void;
  outputTokens: number | ''; setOutputTokens: (v: number | '') => void;
  maxToolCalls: number; setMaxToolCalls: (v: number) => void;
  supportsImages: boolean; setSupportsImages: (v: boolean) => void;
  thinkingMode: 'auto' | 'enabled' | 'disabled'; setThinkingMode: (v: 'auto' | 'enabled' | 'disabled') => void;
  temperature: number | ''; setTemperature: (v: number | '') => void;
  topP: number | ''; setTopP: (v: number | '') => void;
  topK: number | ''; setTopK: (v: number | '') => void;
}

const muted: React.CSSProperties = { fontSize: 12, color: 'var(--text-muted)' };
const field: React.CSSProperties = { minWidth: 0, height: 38, padding: '0 12px', borderRadius: 8, background: '#242629', border: '1px solid #37393d', color: '#e3e5e8', fontSize: 12 };
const hint = <Info size={13} color="#777d87" />;

export const ModelAdvancedParams: React.FC<ModelAdvancedParamsProps> = (p) => {
  const presetButton: React.CSSProperties = { color: '#b5bac3', background: 'transparent', padding: '4px 5px', fontSize: 11, whiteSpace: 'nowrap' };
  const numberField = (label: string, value: number | '', set: (v: number | '') => void, placeholder: string) => (
    <div style={{ display: 'grid', gridTemplateColumns: '144px minmax(0,1fr)', border: '1px solid #37393d', borderRadius: 8, overflow: 'hidden', minWidth: 0 }}>
      <span style={{ ...field, height: 36, border: 0, borderRadius: 0, display: 'flex', alignItems: 'center', background: '#303236', color: '#e1e3e6' }}>{label}</span>
      <input type="number" value={value} placeholder={placeholder} onChange={e => set(e.target.value === '' ? '' : Number(e.target.value))} style={{ ...field, height: 36, border: 0, borderRadius: 0, background: '#242629' }} />
    </div>
  );
  return <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 14 }}>
    <button type="button" onClick={p.onToggle} style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 13, color: '#d9dce1', padding: 0 }}>
      {p.isOpen ? <ChevronDown size={15} /> : <ChevronRight size={15} />}<span>高级配置</span>
    </button>
    {p.isOpen && <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 18 }}>
      <div><div style={{ ...muted, marginBottom: 5 }}>模型系列</div><div style={{ ...muted, marginBottom: 8 }}>针对特定模型系列优化了 Prompt 和超参数，未选择时使用默认配置。</div>
        <select value={p.family} onChange={e => p.setFamily(e.target.value)} style={{ ...field, width: '100%' }}><option value="default">默认</option><option value="gpt">GPT</option><option value="claude">Claude</option><option value="gemini">Gemini</option><option value="deepseek">DeepSeek</option></select>
      </div>
      <div><div style={{ ...muted, marginBottom: 6 }}>上下文窗口（Token）</div>
        {([['输入', p.contextWindow, p.setContextWindow, ['128k','256k','512k','1M']], ['输出', p.outputTokens, p.setOutputTokens, ['4k','16k','32k','128k']]] as const).map(([label,value,set,presets]) => <div key={label} style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2.2fr) minmax(150px, 1fr)', gap: 10, marginBottom: 7 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '84px minmax(0,1fr)', border: '1px solid #37393d', borderRadius: 8, overflow: 'hidden' }}><span style={{ ...field, height: 36, border: 0, borderRadius: 0, display: 'grid', placeItems: 'center', background: '#303236' }}>{label}</span><input type="number" value={value} placeholder="请输入数值，留空则使用最佳默认值" onChange={e => set(e.target.value === '' ? '' : Number(e.target.value))} style={{ ...field, height: 36, border: 0, borderRadius: 0 }} /></div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-around' }}>{presets.map(v => <button key={v} type="button" style={presetButton} onClick={() => set(Number(v.replace('k','000').replace('M','000000')))}>{v}</button>)}</div>
        </div>)}
      </div>
      <label style={{ ...muted, display: 'flex', flexDirection: 'column', gap: 6 }}>工具调用轮数<input type="number" value={p.maxToolCalls} onChange={e => p.setMaxToolCalls(Number(e.target.value))} style={{ ...field, width: '100%' }} /></label>
      <div><div style={{ ...muted, display: 'flex', gap: 8, alignItems: 'center', marginBottom: 7 }}>支持图片输入 {hint}</div><RadioGroup value={p.supportsImages ? 'yes' : 'no'} options={[['yes','支持'],['no','不支持']]} onChange={v => p.setSupportsImages(v === 'yes')} /></div>
      <div><div style={{ ...muted, display: 'flex', gap: 8, alignItems: 'center', marginBottom: 7 }}>思考模式 {hint}</div><RadioGroup value={p.thinkingMode} options={ [['auto','跟随模型默认配置'],['enabled','开启'],['disabled','关闭']] } onChange={v => p.setThinkingMode(v as 'auto'|'enabled'|'disabled')} /></div>
      <div><div style={{ ...muted, display: 'flex', gap: 8, alignItems: 'center', marginBottom: 7 }}>采样参数 {hint}</div><div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>{numberField('Temperature',p.temperature,p.setTemperature,'留空使用最佳配置，或输入 0 ~ 2 之间的数值')}{numberField('Top P',p.topP,p.setTopP,'留空使用最佳配置，或输入 0 ~ 1 之间的数值')}{numberField('Top K',p.topK,p.setTopK,'留空使用最佳配置，或输入 1 ~ 100 之间的数值')}</div></div>
    </div>}
  </div>;
};

const RadioGroup: React.FC<{value:string;options:readonly (readonly [string,string])[];onChange:(v:string)=>void}> = ({value,options,onChange}) => <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24 }}>{options.map(([v,label]) => <label key={v} style={{ ...muted, display: 'inline-flex', gap: 7, alignItems: 'center', cursor: 'pointer' }}><input type="radio" checked={value===v} onChange={()=>onChange(v)} style={{ accentColor: '#3478f6' }} />{label}</label>)}</div>;
