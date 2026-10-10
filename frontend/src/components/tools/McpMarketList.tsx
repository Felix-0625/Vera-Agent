import React, { useState } from 'react';
import { Download, Search, PanelTop } from 'lucide-react';

interface MarketItem {
  id: string;
  name: string;
  description: string;
  category: string;
}

interface McpMarketListProps {
  market: MarketItem[];
  onInstall: (item: MarketItem) => Promise<void>;
  dialog?: boolean;
}

/**
 * 右侧工具 7 - MCP 市场插件列表组件
 */
export const McpMarketList: React.FC<McpMarketListProps> = ({ market, onInstall, dialog = false }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const filtered = market.filter((item) => `${item.name} ${item.description} ${item.category}`.toLowerCase().includes(searchTerm.toLowerCase()));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: dialog ? 'min(690px, 76vh)' : undefined, minHeight: dialog ? 360 : undefined }}>
      {dialog && <label style={{ height: 38, flex: '0 0 38px', display: 'flex', alignItems: 'center', gap: 9, padding: '0 13px', borderRadius: 9, background: '#232427', border: '1px solid #383a40', color: 'var(--text-muted)' }}><Search size={14} /><input value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="搜索 MCP 市场..." style={{ flex: 1, background: 'transparent', border: 0, outline: 0, fontSize: 12 }} /></label>}
      {filtered.length === 0 ? <div style={{ flex: 1, minHeight: dialog ? 260 : 180, border: '1px solid var(--border-default)', borderRadius: 12, background: '#232427', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}><PanelTop size={30} color="#8c929c" /><strong style={{ marginTop: 20, fontSize: 14 }}>暂无可用 MCP</strong><span style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>市场中的 MCP 服务器将在此处展示。</span>{dialog && <span style={{ marginTop: 7, fontSize: 11, color: 'var(--text-muted)' }}>请检查网络连接，或稍后再试。</span>}</div> : <div style={{ display: 'flex', flexDirection: 'column', gap: 10, overflowY: dialog ? 'auto' : undefined, flex: dialog ? 1 : undefined }}>
      {filtered.map((m) => (
        <div key={m.id} className="glass-card" style={{ padding: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{m.name}</div>
              <span
                style={{
                  fontSize: 10,
                  padding: '1px 6px',
                  borderRadius: 'var(--radius-full)',
                  backgroundColor: 'rgba(255, 255, 255, 0.06)',
                  color: 'var(--text-muted)',
                }}
              >
                {m.category}
              </span>
            </div>
            <button
              onClick={() => onInstall(m)}
              style={{
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(6,182,212,0.15)',
                color: 'var(--accent-cyan)',
                fontSize: 11.5,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <Download size={12} />
              <span>安装到本地</span>
            </button>
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
            {m.description}
          </div>
        </div>
      ))}
      </div>}
    </div>
  );
};
