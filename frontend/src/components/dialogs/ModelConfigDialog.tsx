import React, { useState, useEffect } from 'react';
import { Activity, Save } from 'lucide-react';
import { useLayoutStore } from '../../stores/layoutStore';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { createModel, patchModel, testModelConnection } from '../../api/settingsApi';
import { ModelConfig, ModelProvider } from '../../types/settings';
import { getProviderBaseUrl, ModelBasicFields } from './ModelBasicFields';
import { ModelAdvancedParams } from './ModelAdvancedParams';

/**
 * 模态弹窗 4 - 模型配置弹窗
 * 按照 Penpot 原型规范与模块化架构设计
 */
export const ModelConfigDialog: React.FC = () => {
  const { modelConfigOpen, closeModelConfig, editingModel, notifyModelCatalogChanged } = useLayoutStore();

  const [provider, setProvider] = useState<ModelProvider>('deepseek');
  const [name, setName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [maxTokens, setMaxTokens] = useState(8192);
  const [temperature, setTemperature] = useState<number | ''>(0.2);
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
  const [formError, setFormError] = useState('');

  useEffect(() => {
    if (editingModel) {
      setProvider(editingModel.provider || 'deepseek');
      setName(editingModel.name || '');
      setDisplayName(editingModel.display_name || '');
      setBaseUrl(editingModel.base_url || '');
      setApiKey(''); // 留空表示不修改已有密钥
      setMaxTokens(editingModel.max_tokens || 8192);
      setTemperature(editingModel.temperature ?? 0.2);
      setContextWindow(editingModel.context_window ?? '');
      setOutputTokens(editingModel.output_tokens ?? editingModel.max_tokens ?? '');
      setMaxToolCalls(editingModel.max_tool_calls ?? 500);
      setSupportsImages(editingModel.supports_images ?? true);
      setThinkingMode(editingModel.thinking_mode ?? 'auto');
      setTopP(editingModel.top_p ?? '');
      setTopK(editingModel.top_k ?? '');
    } else {
      setProvider('deepseek');
      setName('');
      setDisplayName('');
      setBaseUrl(getProviderBaseUrl('deepseek'));
      setApiKey('');
      setMaxTokens(8192);
      setTemperature(0.2);
      setContextWindow(''); setOutputTokens(''); setMaxToolCalls(500);
      setSupportsImages(true); setThinkingMode('auto'); setTopP(''); setTopK('');
    }
    setAdvancedOpen(false); // Penpot 原型规定默认折叠
    setTestResult(null);
    setFormError('');
  }, [editingModel, modelConfigOpen]);

  const handleTest = async () => {
    if (!name.trim()) {
      setTestResult({ success: false, msg: '请先填写模型 ID。' });
      return;
    }
    if (!baseUrl.trim()) {
      setTestResult({ success: false, msg: '请先填写请求地址。' });
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testModelConnection({
        model_id: editingModel?.id,
        name: name.trim(),
        provider,
        api_key: apiKey,
        base_url: baseUrl.trim(),
      });
      setTestResult({
        success: res.success,
        msg: res.success ? (res.message || '连通性验证成功！') : (res.error || '连通失败'),
      });
    } catch (error) {
      setTestResult({
        success: false,
        msg: error instanceof DOMException && error.name === 'AbortError'
          ? '连接测试超时（12 秒），请检查请求地址、网络和密钥。'
          : error instanceof Error ? `连接测试失败：${error.message}` : '连接测试失败，请检查请求地址和模型配置。',
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setFormError('');
    if (!name.trim()) {
      setFormError('请填写模型 ID。');
      return;
    }
    if (!baseUrl.trim()) {
      setFormError('请填写请求地址。');
      return;
    }
    const modelId = editingModel?.id || `model_${Date.now()}`;
    const payload: Partial<ModelConfig> = {
      id: modelId,
      name: name.trim(),
      provider,
      base_url: baseUrl.trim(),
      max_tokens: Number(outputTokens || maxTokens),
      output_tokens: outputTokens === '' ? undefined : Number(outputTokens),
      context_window: contextWindow === '' ? undefined : Number(contextWindow),
      max_tool_calls: Number(maxToolCalls),
      supports_images: supportsImages,
      thinking_mode: thinkingMode,
      temperature: temperature === '' ? undefined : Number(temperature),
      top_p: topP === '' ? undefined : Number(topP),
      top_k: topK === '' ? undefined : Number(topK),
      display_name: displayName.trim() || name.trim(),
    };
    if (apiKey) payload.api_key = apiKey;

    try {
      if (editingModel) await patchModel(modelId, payload);
      else await createModel({ ...payload, id: modelId, name: name.trim(), provider, display_name: displayName.trim() || name.trim() } as ModelConfig);
      notifyModelCatalogChanged();
      closeModelConfig();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : '保存模型配置失败。');
    }
  };

  return (
    <Modal
      isOpen={modelConfigOpen}
      onClose={closeModelConfig}
      title={editingModel ? '编辑模型' : '添加模型'}
      width={760}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3-5)' }}>
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
          provider={provider}
          isOpen={advancedOpen}
          onToggle={() => setAdvancedOpen(!advancedOpen)}
          temperature={temperature}
          setTemperature={setTemperature}
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
              padding: 'var(--space-2) var(--space-3)',
              borderRadius: 'var(--radius-sm)',
              fontSize: 'var(--font-size-sm)',
              backgroundColor: testResult.success ? 'var(--bg-success-soft)' : 'var(--bg-danger-soft)',
              color: testResult.success ? 'var(--accent-emerald)' : 'var(--accent-rose)',
            }}
          >
            {testResult.msg}
          </div>
        )}
        {formError && (
          <div role="alert" style={{ padding: 'var(--space-2) var(--space-3)', borderRadius: 'var(--radius-sm)', fontSize: 'var(--font-size-sm)', backgroundColor: 'var(--bg-danger-soft)', color: 'var(--accent-rose)' }}>
            {formError}
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 'var(--space-2-5)' }}>
          <Button
            type="button"
            onClick={handleTest}
            disabled={testing}
            variant="secondary"
            size="sm"
          >
            <Activity size={13} />
            <span>{testing ? '测试中...' : '测试连通性'}</span>
          </Button>

          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <Button
              type="button"
              onClick={closeModelConfig}
              variant="ghost"
              size="sm"
            >
              取消
            </Button>
            <Button
              type="button"
              onClick={handleSave}
              variant="primary"
              size="sm"
            >
              <Save size={13} />
              <span>保存配置</span>
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
};
