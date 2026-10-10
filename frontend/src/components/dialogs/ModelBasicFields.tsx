import React, { useState } from 'react';
import { Link2, Eye, EyeOff } from 'lucide-react';

interface ModelBasicFieldsProps {
  provider: string; setProvider: (val: string) => void;
  name: string; setName: (val: string) => void;
  displayName: string; setDisplayName: (val: string) => void;
  baseUrl: string; setBaseUrl: (val: string) => void;
  apiKey: string; setApiKey: (val: string) => void;
  isEditing: boolean;
}

const inputStyle: React.CSSProperties = { width: '100%', height: 38, padding: '0 13px', borderRadius: 9, backgroundColor: '#222326', border: '1px solid #383a40', fontSize: 12.5, color: 'var(--text-primary)', outline: 'none' };
const labelStyle: React.CSSProperties = { display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 5 };
const helperStyle: React.CSSProperties = { fontSize: 10.5, lineHeight: 1.4, color: 'var(--text-muted)', margin: '0 0 6px' };

export const ModelBasicFields: React.FC<ModelBasicFieldsProps> = ({ provider, setProvider, name, setName, displayName, setDisplayName, baseUrl, setBaseUrl, apiKey, setApiKey, isEditing }) => (
  <ModelBasicFieldsContent provider={provider} setProvider={setProvider} name={name} setName={setName} displayName={displayName} setDisplayName={setDisplayName} baseUrl={baseUrl} setBaseUrl={setBaseUrl} apiKey={apiKey} setApiKey={setApiKey} isEditing={isEditing} />
);

const ModelBasicFieldsContent: React.FC<ModelBasicFieldsProps> = ({ provider, setProvider, name, setName, displayName, setDisplayName, baseUrl, setBaseUrl, apiKey, setApiKey, isEditing }) => {
  const [completeUrl, setCompleteUrl] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  return <>
    <div>
      <label style={labelStyle}>API 格式</label>
      <select value={provider} onChange={(e) => setProvider(e.target.value)} style={inputStyle}>
        <option value="deepseek">OpenAI Chat Completions 格式</option>
        <option value="anthropic">Anthropic Messages 格式</option>
        <option value="ollama">Ollama 兼容格式</option>
      </select>
    </div>
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <label style={{ ...labelStyle, marginBottom: 0 }}>* 自定义请求地址</label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 7, color: 'var(--text-muted)', fontSize: 11 }}><Link2 size={13} /> 完整 URL <input type="checkbox" checked={completeUrl} onChange={(event) => setCompleteUrl(event.target.checked)} aria-label="使用完整 URL" /></label>
      </div>
      <p style={helperStyle}>{completeUrl ? '填写完整的 API 请求 URL。' : '请填写兼容 OpenAI API 的服务端点地址，不要以斜杠结尾。/chat/completions 将会被补充到你填写的地址末尾。'}</p>
      <input type="url" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="例如 https://api.openai.com/v1" style={inputStyle} />
    </div>
    <div>
      <label style={labelStyle}>模型 ID</label>
      <input type="text" required value={name} onChange={(e) => setName(e.target.value)} placeholder="输入模型 ID" style={inputStyle} />
    </div>
    <div>
      <label style={labelStyle}>模型展示名称</label>
      <p style={helperStyle}>在模型列表中展示的名称，未设置时默认显示 Model ID。</p>
      <div style={{ position: 'relative' }}><input type="text" maxLength={64} value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="请输入模型展示名称" style={{ ...inputStyle, paddingRight: 55 }} /><span style={{ position: 'absolute', right: 12, top: 12, color: 'var(--text-muted)', fontSize: 10 }}>{displayName.length}/64</span></div>
    </div>
    <div>
      <label style={labelStyle}>API 密钥</label>
      <div style={{ position: 'relative' }}><input type={showApiKey ? 'text' : 'password'} value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder={isEditing ? '留空则保留已有密钥' : '请输入 API Key'} style={{ ...inputStyle, paddingRight: 40 }} /><button type="button" aria-label={showApiKey ? '隐藏 API 密钥' : '显示 API 密钥'} title={showApiKey ? '隐藏 API 密钥' : '显示 API 密钥'} onClick={() => setShowApiKey((shown) => !shown)} style={{ position: 'absolute', right: 10, top: 10, color: 'var(--text-muted)' }}>{showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}</button></div>
    </div>
  </>;
};
