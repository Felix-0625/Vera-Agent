import React, { useEffect, useMemo, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { useLayoutStore } from '../../stores/layoutStore';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { TextArea } from '../common/Field';
import { createMcpServer, updateMcpServer } from '../../api/settingsApi';

const exampleConfig = `// 示例：
// {
//   "mcpServers": {
//     "example-server": {
//       "command": "npx",
//       "args": [
//         "-y",
//         "mcp-server-example"
//       ]
//     }
//   }
// }`;

type ParsedServer = { command?: string; args?: string[]; env?: Record<string, string>; url?: string; type?: string; headers?: Record<string, string>; [key: string]: unknown };

export const McpManualConfigDialog: React.FC = () => {
  const { mcpConfigOpen, closeMcpConfig, editingMcp, notifyMcpCatalogChanged } = useLayoutStore();
  const [configText, setConfigText] = useState(exampleConfig);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const lineCount = useMemo(() => Math.max(1, configText.split('\n').length), [configText]);

  useEffect(() => {
    setError('');
    if (editingMcp) {
      const serverConfig: ParsedServer = { type: editingMcp.type, command: editingMcp.command, args: editingMcp.args, url: editingMcp.url, headers: editingMcp.headers, ...(editingMcp.env ? { env: editingMcp.env } : {}) };
      setConfigText(JSON.stringify({ mcpServers: { [editingMcp.name]: serverConfig } }, null, 2));
    } else {
      setConfigText(exampleConfig);
    }
  }, [editingMcp, mcpConfigOpen]);

  const handleSave = async () => {
    setError('');
    const withoutLineComments = configText.replace(/^\s*\/\/.*$/gm, '').trim();
    let parsed: { mcpServers?: Record<string, ParsedServer> };
    try {
      parsed = JSON.parse(withoutLineComments);
    } catch {
      setError('JSON 格式无效，请检查括号、引号和逗号。');
      return;
    }
    const entries = Object.entries(parsed.mcpServers || {});
    if (!entries.length) {
      setError('配置中没有找到 mcpServers，请按示例添加服务器配置。');
      return;
    }
    if (entries.some(([, server]) => !server || ((!server.url || !/^https?:\/\//.test(server.url)) && (typeof server.command !== 'string' || !server.command.trim())) || (server.args && (!Array.isArray(server.args) || server.args.some(arg => typeof arg !== 'string'))))) {
      setError('每个 MCP 服务都需要有效的 stdio command 或 HTTP(S) url，args 必须是字符串数组。');
      return;
    }

    setSaving(true);
    try {
      if (editingMcp) {
        const [name, server] = entries[0];
        await updateMcpServer(editingMcp.id, {
          ...editingMcp,
          name,
          command: server.command,
          args: server.args || [],
          env: (server.env || {}) as Record<string, string>,
          type: server.url ? 'remote' : 'stdio',
          url: server.url,
          headers: (server.headers || {}) as Record<string, string>,
          enabled: editingMcp.enabled,
          tools: [],
        });
      } else {
        for (const [name, server] of entries) {
          await createMcpServer({
            id: `mcp_${name.replace(/[^a-zA-Z0-9_-]/g, '_')}_${Date.now()}`,
            name,
            type: 'stdio',
            status: 'stopped',
            enabled: false,
            command: server.command,
            args: server.args || [],
            env: (server.env || {}) as Record<string, string>,
            tools: [],
            ...(server.url ? { type: 'remote', url: server.url, headers: server.headers || {} } : {}),
          });
        }
      }
      notifyMcpCatalogChanged();
      closeMcpConfig();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : '保存 MCP 配置失败。');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={mcpConfigOpen} onClose={closeMcpConfig} title="手动配置" width={760}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-control)', lineHeight: 1.6, margin: 0 }}>请从 MCP Servers 的介绍页面复制配置 JSON（优先使用 NPX 或 UVX 配置），并粘贴到输入框中。</p>
        <div className="mcp-json-editor">
          <div className="mcp-json-gutter" aria-hidden="true">{Array.from({ length: lineCount }, (_, index) => <span key={index}>{index + 1}</span>)}</div>
          <TextArea className="mcp-json-input" aria-label="MCP Servers 配置 JSON" spellCheck={false} value={configText} onChange={(event) => setConfigText(event.target.value)} />
        </div>
        {error && <div role="alert" style={{ color: 'var(--accent-rose)', fontSize: 'var(--font-size-sm)' }}>{error}</div>}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 'var(--space-0-5)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1-5)', color: 'var(--accent-amber)', fontSize: 'var(--font-size-compact)' }}><AlertTriangle size={13} />配置前请确认来源，甄别风险</span>
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <Button type="button" onClick={closeMcpConfig} variant="ghost" size="sm">取消</Button>
            <Button type="button" onClick={() => void handleSave()} disabled={saving} variant="primary" size="sm">{saving ? '保存中…' : '确认'}</Button>
          </div>
        </div>
      </div>
    </Modal>
  );
};
