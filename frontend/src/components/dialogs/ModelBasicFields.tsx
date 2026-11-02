import { Eye, EyeOff } from 'lucide-react';
import React, { useState } from 'react';
import { ModelProvider } from '../../types/settings';
import { SelectField, TextInput } from '../common/Field';
import { IconButton } from '../common/IconButton';
import { getProviderBaseUrl, MODEL_PROVIDERS } from './modelProviders';

interface ModelBasicFieldsProps {
  provider: ModelProvider;
  setProvider: (val: ModelProvider) => void;
  name: string;
  setName: (val: string) => void;
  displayName: string;
  setDisplayName: (val: string) => void;
  baseUrl: string;
  setBaseUrl: (val: string) => void;
  apiKey: string;
  setApiKey: (val: string) => void;
  isEditing: boolean;
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: 'var(--font-size-sm)',
  fontWeight: 600,
  color: 'var(--text-secondary)',
  marginBottom: 'var(--space-1-25)',
};
const helperStyle: React.CSSProperties = {
  fontSize: 'var(--font-size-subtle)',
  lineHeight: 1.4,
  color: 'var(--text-muted)',
  margin: '0 0 var(--space-1-5)',
};

export const ModelBasicFields: React.FC<ModelBasicFieldsProps> = ({
  provider,
  setProvider,
  name,
  setName,
  displayName,
  setDisplayName,
  baseUrl,
  setBaseUrl,
  apiKey,
  setApiKey,
  isEditing,
}) => (
  <ModelBasicFieldsContent
    provider={provider}
    setProvider={setProvider}
    name={name}
    setName={setName}
    displayName={displayName}
    setDisplayName={setDisplayName}
    baseUrl={baseUrl}
    setBaseUrl={setBaseUrl}
    apiKey={apiKey}
    setApiKey={setApiKey}
    isEditing={isEditing}
  />
);

const ModelBasicFieldsContent: React.FC<ModelBasicFieldsProps> = ({
  provider,
  setProvider,
  name,
  setName,
  displayName,
  setDisplayName,
  baseUrl,
  setBaseUrl,
  apiKey,
  setApiKey,
  isEditing,
}) => {
  const [showApiKey, setShowApiKey] = useState(false);
  const selectProvider = (value: ModelProvider) => {
    setProvider(value);
    setBaseUrl(getProviderBaseUrl(value));
  };
  return (
    <>
      <div>
        <label style={labelStyle}>模型厂商</label>
        <SelectField value={provider} onChange={(e) => selectProvider(e.target.value as ModelProvider)}>
          {MODEL_PROVIDERS.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </SelectField>
      </div>
      <div>
        <label style={labelStyle}>请求地址</label>
        <p style={helperStyle}>
          {provider === 'custom'
            ? '自定义服务不会自动填入地址，请填写服务商提供的 API 根地址。'
            : '已按所选厂商填入默认 API 地址；如使用代理或自定义网关，可在此修改。'}
        </p>
        <TextInput
          type="url"
          required
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder={provider === 'custom' ? 'https://your-provider.example/v1' : '厂商 API 地址'}
        />
      </div>
      <div>
        <label style={labelStyle}>模型 ID</label>
        <TextInput
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="输入模型 ID"
        />
      </div>
      <div>
        <label style={labelStyle}>模型展示名称</label>
        <p style={helperStyle}>在模型列表中展示的名称，未设置时默认显示 Model ID。</p>
        <div style={{ position: 'relative' }}>
          <TextInput
            type="text"
            maxLength={64}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="请输入模型展示名称"
            style={{ paddingRight: 55 }}
          />
          <span
            style={{
              position: 'absolute',
              right: 12,
              top: 12,
              color: 'var(--text-muted)',
              fontSize: 'var(--font-size-xs)',
            }}
          >
            {displayName.length}/64
          </span>
        </div>
      </div>
      <div>
        <label style={labelStyle}>API 密钥</label>
        <div style={{ position: 'relative' }}>
          <TextInput
            type={showApiKey ? 'text' : 'password'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={isEditing ? '留空则保留已有密钥' : '请输入 API Key'}
            style={{ paddingRight: 40 }}
          />
          <IconButton
            className="model-api-key-toggle"
            label={showApiKey ? '隐藏 API 密钥' : '显示 API 密钥'}
            size="sm"
            onClick={() => setShowApiKey((shown) => !shown)}
          >
            {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
          </IconButton>
        </div>
      </div>
    </>
  );
};
