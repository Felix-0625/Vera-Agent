import React, { useEffect, useMemo, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { useLayoutStore } from '../../stores/layoutStore';
import { Modal } from '../common/Modal';
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

type ParsedServer = { command: string; args?: string[]; env?: Record<string, string>; [key: string]: unknown };

export const McpManualConfigDialog: React.FC = () => {
  const { mcpConfigOpen, closeMcpConfig, editingMcp } = useLayoutStore();
  const [configText, setConfigText] = useState(exampleConfig);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const lineCount = useMemo(() => Math.max(1, configText.split('\n').length), [configText]);

  useEffect(() => {
    setError('');
    if (editingMcp) {
      const serverConfig: ParsedServer = { command: editingMcp.command, args: editingMcp.args, ...(editingMcp.env ? { env: editingMcp.env } : {}) };
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
    if (entries.some(([, server]) => !server || typeof server.command !== 'string' || !server.command.trim() || (server.args && !Array.isArray(server.args)))) {
      setError('每个 MCP 服务都需要有效的 command，args 必须是字符串数组。');
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
        });
      } else {
        for (const [name, server] of entries) {
          await createMcpServer({
            id: `mcp_${name.replace(/[^a-zA-Z0-9_-]/g, '_')}_${Date.now()}`,
            name,
            type: 'stdio',
            status: 'stopped',
            enabled: true,
            command: server.command,
            args: server.args || [],
            env: (server.env || {}) as Record<string, string>,
            tools: [],
          });
        }
      }
      closeMcpConfig();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : '保存 MCP 配置失败。');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={mcpConfigOpen} onClose={closeMcpConfig} title="手动配置" width={760}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: 12.5, lineHeight: 1.6, margin: 0 }}>请从 MCP Servers 的介绍页面复制配置 JSON（优先使用 NPX 或 UVX 配置），并粘贴到输入框中。</p>
        <div className="mcp-json-editor">
          <div className="mcp-json-gutter" aria-hidden="true">{Array.from({ length: lineCount }, (_, index) => <span key={index}>{index + 1}</span>)}</div>
          <textarea aria-label="MCP Servers 配置 JSON" spellCheck={false} value={configText} onChange={(event) => setConfigText(event.target.value)} />
        </div>
        {error && <div role="alert" style={{ color: '#ff8f8f', fontSize: 12 }}>{error}</div>}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 2 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#d3a846', fontSize: 11 }}><AlertTriangle size={13} />配置前请确认来源，甄别风险</span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" onClick={closeMcpConfig} style={{ minWidth: 72, padding: '7px 14px', borderRadius: 9, background: '#303238', color: '#d6d9df', fontSize: 12 }}>取消</button>
            <button type="button" onClick={() => void handleSave()} disabled={saving} style={{ minWidth: 72, padding: '7px 14px', borderRadius: 9, background: '#e2e6ed', color: '#17191e', fontSize: 12, fontWeight: 650, opacity: saving ? .7 : 1 }}>{saving ? '保存中…' : '确认'}</button>
          </div>
        </div>
      </div>
    </Modal>
  );
};
