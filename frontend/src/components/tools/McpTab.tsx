import React, { useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import {
  fetchMcpServers,
  toggleMcpServer,
  restartMcpServer,
  deleteMcpServer,
  fetchMcpMarket,
  createMcpServer,
} from '../../api/settingsApi';
import { McpServerConfig } from '../../types/settings';
import { useLayoutStore } from '../../stores/layoutStore';
import { McpServerList } from './McpServerList';
import { McpMarketList } from './McpMarketList';

/**
 * 右侧工具 7 - MCP 服务与市场管理面板
 */
export const McpTab: React.FC = () => {
  const { openMcpConfig } = useLayoutStore();
  const [activeSubTab, setActiveSubTab] = useState<'servers' | 'market'>('servers');
  const [servers, setServers] = useState<McpServerConfig[]>([]);
  const [market, setMarket] = useState<Array<{ id: string; name: string; description: string; category: string }>>([]);

  const loadData = async () => {
    try {
      const sData = await fetchMcpServers();
      setServers(sData.servers || []);
      const mData = await fetchMcpMarket();
      setMarket(mData.market || []);
    } catch {
      // 保持静默回退
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggle = async (s: McpServerConfig) => {
    await toggleMcpServer(s.id);
    loadData();
  };

  const handleRestart = async (id: string) => {
    await restartMcpServer(id);
    loadData();
  };

  const handleDelete = async (id: string) => {
    if (window.confirm('确定要删除此 MCP 服务器吗？')) {
      await deleteMcpServer(id);
      loadData();
    }
  };

  const handleInstallMarket = async (item: { id: string; name: string; description: string }) => {
    await createMcpServer({
      id: item.id,
      name: item.name,
      command: 'python',
      args: ['server.py'],
      tools: [{ name: item.id, description: item.description }],
    });
    loadData();
    setActiveSubTab('servers');
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-workspace)' }}>
      {/* 顶部标签切换 & 新增操作 */}
      <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', gap: 12, alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => setActiveSubTab('servers')}
            style={{
              padding: '4px 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: 12,
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
              padding: '4px 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: 12,
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
            padding: '4px 10px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--accent-primary)',
            color: '#fff',
            fontSize: 11.5,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <Plus size={13} />
          <span>添加</span>
        </button>
      </div>

      {/* 主体列表 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {activeSubTab === 'servers' ? (
          <McpServerList
            servers={servers}
            onToggle={handleToggle}
            onEdit={(s) => openMcpConfig(s)}
            onRestart={handleRestart}
            onDelete={handleDelete}
          />
        ) : (
          <McpMarketList market={market} onInstall={handleInstallMarket} />
        )}
      </div>
    </div>
  );
};
