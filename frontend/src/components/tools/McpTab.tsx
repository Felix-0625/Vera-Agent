import React, { useCallback, useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import {
  fetchMcpServers,
  toggleMcpServer,
  restartMcpServer,
  deleteMcpServer,
  fetchMcpMarket,
  installMcpFromMarket,
  McpMarketItem,
} from '../../api/settingsApi';
import { McpServerConfig } from '../../types/settings';
import { useLayoutStore } from '../../stores/layoutStore';
import { McpServerList } from './McpServerList';
import { McpMarketList } from './McpMarketList';

/**
 * 右侧工具 7 - MCP 服务与市场管理面板
 */
export const McpTab: React.FC<{ active?: boolean }> = ({ active = true }) => {
  const { openMcpConfig } = useLayoutStore();
  const [activeSubTab, setActiveSubTab] = useState<'servers' | 'market'>('servers');
  const [servers, setServers] = useState<McpServerConfig[]>([]);
  const [market, setMarket] = useState<McpMarketItem[]>([]);
  const [error, setError] = useState('');

  const loadData = useCallback(async () => {
    const errors: string[] = [];
    await Promise.all([
      fetchMcpServers()
        .then((data) => setServers(data.servers || []))
        .catch((cause: unknown) => errors.push(cause instanceof Error ? cause.message : 'MCP 服务列表加载失败')),
      fetchMcpMarket()
        .then((data) => setMarket(data.market || []))
        .catch((cause: unknown) => errors.push(cause instanceof Error ? cause.message : 'MCP 市场加载失败')),
    ]);
    setError(errors.join('；'));
  }, []);

  useEffect(() => {
    if (active) void loadData();
  }, [active, loadData]);

  const handleToggle = async (s: McpServerConfig) => {
    try {
      await toggleMcpServer(s.id);
      await loadData();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : `更新 ${s.name} 状态失败`);
    }
  };

  const handleRestart = async (id: string) => {
    try {
      await restartMcpServer(id);
      await loadData();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '重启 MCP 服务失败');
    }
  };

  const handleDelete = async (id: string) => {
    if (window.confirm('确定要删除此 MCP 服务器吗？')) {
      try {
        await deleteMcpServer(id);
        await loadData();
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : '删除 MCP 服务失败');
      }
    }
  };

  const handleInstallMarket = async (item: McpMarketItem) => {
    try {
      await installMcpFromMarket(item);
      await loadData();
      setActiveSubTab('servers');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : `安装 ${item.name} 失败`);
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-workspace)' }}>
      {/* 顶部标签切换 & 新增操作 */}
      <div style={{ padding: 'var(--space-2) var(--space-4)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', gap: 'var(--space-3)', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <button
            onClick={() => setActiveSubTab('servers')}
            style={{
              padding: 'var(--space-1) var(--space-2-5)',
              borderRadius: 'var(--radius-sm)',
              fontSize: 'var(--font-size-sm)',
              fontWeight: activeSubTab === 'servers' ? 600 : 400,
              backgroundColor: activeSubTab === 'servers' ? 'var(--bg-card)' : 'transparent',
              color: activeSubTab === 'servers' ? 'var(--text-primary)' : 'var(--text-muted)',
            }}
          >
            服务管理
          </button>
          <button
            onClick={() => setActiveSubTab('market')}
            style={{
              padding: 'var(--space-1) var(--space-2-5)',
              borderRadius: 'var(--radius-sm)',
              fontSize: 'var(--font-size-sm)',
              fontWeight: activeSubTab === 'market' ? 600 : 400,
              backgroundColor: activeSubTab === 'market' ? 'var(--bg-card)' : 'transparent',
              color: activeSubTab === 'market' ? 'var(--text-primary)' : 'var(--text-muted)',
            }}
          >
            插件市场
          </button>
        </div>

        <button
          onClick={() => openMcpConfig(null)}
          style={{
            padding: 'var(--space-1) var(--space-2-5)',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--accent-primary)',
            color:'var(--text-on-accent)',
            fontSize: 'var(--font-size-label)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-1)',
          }}
        >
          <Plus size={13} />
          <span>添加</span>
        </button>
      </div>

      {/* 主体列表 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-4)' }}>
        {error && <div role="alert" style={{ marginBottom: 'var(--space-3)', padding: 'var(--space-2) var(--space-2-5)', borderRadius: 'var(--radius-md)', color: 'var(--accent-rose)', background: 'var(--bg-danger-soft)', fontSize: 'var(--font-size-sm)' }}>{error}</div>}
        {activeSubTab === 'servers' ? (
          <McpServerList
            servers={servers}
            onToggle={handleToggle}
            onEdit={(s) => openMcpConfig(s)}
            onRestart={handleRestart}
            onDelete={handleDelete}
          />
        ) : (
          <McpMarketList market={market} installedIds={servers.map(server => server.registry_id || '')} onInstall={handleInstallMarket} />
        )}
      </div>
    </div>
  );
};
