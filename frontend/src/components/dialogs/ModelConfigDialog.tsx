import React, { useState, useEffect } from 'react';
import { Activity, Save } from 'lucide-react';
import { useLayoutStore } from '../../stores/layoutStore';
import { Modal } from '../common/Modal';
import { createModel, patchModel, testModelConnection } from '../../api/settingsApi';
import { ModelConfig } from '../../types/settings';
import { ModelBasicFields } from './ModelBasicFields';
import { ModelAdvancedParams } from './ModelAdvancedParams';

/**
 * 模态弹窗 4 - 模型配置弹窗
 * 按照 Penpot 原型规范与模块化架构设计
 */
export const ModelConfigDialog: React.FC = () => {
  const { modelConfigOpen, closeModelConfig, editingModel } = useLayoutStore();

  const [provider, setProvider] = useState('deepseek');
  const [name, setName] = useState('deepseek/deepseek-chat');
  const [displayName, setDisplayName] = useState('');
  const [baseUrl, setBaseUrl] = useState('https://api.deepseek.com');
  const [apiKey, setApiKey] = useState('');
  const [maxTokens, setMaxTokens] = useState(8192);
  const [temperature, setTemperature] = useState<number | ''>(0.2);
  const [family, setFamily] = useState('default');
  const [contextWindow, setContextWindow] = useState<number | ''>('');
  const [outputTokens, setOutputTokens] = useState<number | ''>('');
  const [maxToolCalls, setMaxToolCalls] = useState(500);
  const [supportsImages, setSupportsImages] = useState(true);
  const [thinkingMode, setThinkingMode] = useState<'auto' | 'enabled' | 'disabled'>('auto');
  const [topP, setTopP] = useState<number | ''>('');
  const [topK, setTopK] = useState<number | ''>('');
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; msg: string } | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    if (editingModel) {
      setProvider(editingModel.provider || 'deepseek');
      setName(editingModel.name || '');
      setDisplayName(editingModel.display_name || '');
      setBaseUrl(editingModel.base_url || '');
      setApiKey(''); // 留空表示不修改已有密钥
      setMaxTokens(editingModel.max_tokens || 8192);
      setTemperature(editingModel.temperature ?? 0.2);
      setFamily(editingModel.model_family || 'default');
      setContextWindow(editingModel.context_window ?? '');
      setOutputTokens(editingModel.output_tokens ?? editingModel.max_tokens ?? '');
      setMaxToolCalls(editingModel.max_tool_calls ?? 500);
      setSupportsImages(editingModel.supports_images ?? true);
      setThinkingMode(editingModel.thinking_mode ?? 'auto');
      setTopP(editingModel.top_p ?? '');
      setTopK(editingModel.top_k ?? '');
    } else {
      setProvider('deepseek');
      setName('deepseek/deepseek-chat');
      setDisplayName('');
      setBaseUrl('https://api.deepseek.com');
      setApiKey('');
      setMaxTokens(8192);
      setTemperature(0.2);
      setFamily('default'); setContextWindow(''); setOutputTokens(''); setMaxToolCalls(500);
      setSupportsImages(true); setThinkingMode('auto'); setTopP(''); setTopK('');
    }
    setAdvancedOpen(false); // Penpot 原型规定默认折叠
    setTestResult(null);
  }, [editingModel, modelConfigOpen]);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testModelConnection({ name, api_key: apiKey, base_url: baseUrl });
      setTestResult({
        success: res.success,
        msg: res.success ? (res.message || '连通性验证成功！') : (res.error || '连通失败'),
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    const modelId = editingModel?.id || `model_${Date.now()}`;
    const payload: Partial<ModelConfig> = {
      id: modelId,
      name,
      provider,
      base_url: baseUrl,
      max_tokens: Number(outputTokens || maxTokens),
      output_tokens: outputTokens === '' ? undefined : Number(outputTokens),
      context_window: contextWindow === '' ? undefined : Number(contextWindow),
      model_family: family,
      max_tool_calls: Number(maxToolCalls),
      supports_images: supportsImages,
      thinking_mode: thinkingMode,
      temperature: temperature === '' ? undefined : Number(temperature),
      top_p: topP === '' ? undefined : Number(topP),
      top_k: topK === '' ? undefined : Number(topK),
      display_name: displayName.trim() || name,
    };
    if (apiKey) payload.api_key = apiKey;

    if (editingModel) await patchModel(modelId, payload);
    else await createModel({ ...payload, id: modelId, name, provider, display_name: displayName.trim() || name } as ModelConfig);
    closeModelConfig();
  };

  return (
    <Modal
      isOpen={modelConfigOpen}
      onClose={closeModelConfig}
      title={editingModel ? '编辑模型' : '添加模型'}
      width={760}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <ModelBasicFields
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
          isEditing={!!editingModel}
        />

        <ModelAdvancedParams
          isOpen={advancedOpen}
          onToggle={() => setAdvancedOpen(!advancedOpen)}
          temperature={temperature}
          setTemperature={setTemperature}
          family={family} setFamily={setFamily}
          contextWindow={contextWindow} setContextWindow={setContextWindow}
          outputTokens={outputTokens} setOutputTokens={setOutputTokens}
          maxToolCalls={maxToolCalls} setMaxToolCalls={setMaxToolCalls}
          supportsImages={supportsImages} setSupportsImages={setSupportsImages}
          thinkingMode={thinkingMode} setThinkingMode={setThinkingMode}
          topP={topP} setTopP={setTopP} topK={topK} setTopK={setTopK}
        />

        {testResult && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              fontSize: 12,
              backgroundColor: testResult.success ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
              color: testResult.success ? 'var(--accent-emerald)' : 'var(--accent-rose)',
            }}
          >
            {testResult.msg}
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 10 }}>
          <button
            type="button"
            onClick={handleTest}
            disabled={testing}
            style={{
              padding: '7px 14px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-default)',
              color: 'var(--text-secondary)',
              fontSize: 12,
              display: 'flex',
              gap: 5,
              alignItems: 'center',
            }}
          >
            <Activity size={13} />
            <span>{testing ? '测试中...' : '测试连通性'}</span>
          </button>

          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={closeModelConfig}
              style={{ padding: '7px 14px', borderRadius: 'var(--radius-sm)', color: '#d7dbe2', fontSize: 12 }}
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleSave}
              style={{
                padding: '7px 18px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: '#e2e6ed',
                color: '#17191e',
                fontSize: 12,
                fontWeight: 600,
                display: 'flex',
                gap: 5,
                alignItems: 'center',
              }}
            >
              <Save size={13} />
              <span>保存配置</span>
            </button>
          </div>
        </div>
      </div>
    </Modal>
  );
};
