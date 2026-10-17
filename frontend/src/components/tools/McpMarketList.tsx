import React, { useEffect, useRef, useState } from 'react';
import { Download, PanelTop } from 'lucide-react';
import { McpMarketItem } from '../../api/settingsApi';
import { SearchField } from '../common/Field';

interface McpMarketListProps {
  market: McpMarketItem[];
  onInstall: (item: McpMarketItem) => Promise<void>;
  onSearch?: (query: string) => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
  loading?: boolean;
  error?: string;
  installedIds?: string[];
  dialog?: boolean;
}


export const McpMarketList: React.FC<McpMarketListProps> = ({ market, onInstall, onSearch, onLoadMore, hasMore = false, loading = false, error, installedIds = [], dialog = false }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [installError, setInstallError] = useState('');
  const searchTimer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(searchTimer.current), []);
  const normalizedSearch = searchTerm.trim().toLowerCase();
  const filtered = market.filter((item) => `${item.name} ${item.description} ${item.category}`.toLowerCase().includes(normalizedSearch));
  const install = async (item: McpMarketItem) => {
    setBusyId(item.id); setInstallError('');
    try { await onInstall(item); }
    catch (error) { setInstallError(error instanceof Error ? error.message : `添加 ${item.name} 失败。`); }
    finally { setBusyId(null); }
  };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', height: dialog ? 'min(690px, 76vh)' : undefined, minHeight: dialog ? 360 : undefined }}>
      {dialog && <aside role="note" style={{ padding: 'var(--space-2-5) var(--space-3)', borderRadius: 'var(--radius-md-plus)', border:'1px solid color-mix(in srgb, var(--accent-amber) 30%, var(--border-subtle))', background:'var(--bg-warning-soft)', color:'var(--text-secondary)', fontSize:'var(--font-size-label)', lineHeight:1.55 }}><strong style={{ color: 'var(--accent-amber)' }}>安全提示：</strong>官方 Registry 的收录和发布者/包归属校验不代表服务器代码已通过安全审计。MCP 服务启用后可能运行本地程序或连接远程服务。请先检查发布者、源代码、依赖和所需权限；确认可信后再启用。</aside>}
      {dialog && <SearchField aria-label="搜索 MCP Registry" wrapperClassName="mcp-market-search" value={searchTerm} onChange={(event) => { const query = event.target.value; setSearchTerm(query); window.clearTimeout(searchTimer.current); searchTimer.current = window.setTimeout(() => onSearch?.(query), 350); }} placeholder="搜索 MCP Registry..." />}
      {error && <div role="alert" style={{ color:'var(--accent-rose)', fontSize: 'var(--font-size-sm)', padding: 'var(--space-2) var(--space-2-5)', borderRadius: 'var(--radius-md)', background:'var(--bg-danger-soft)' }}>{error}</div>}
      {installError && <div role="alert" style={{ color:'var(--accent-rose)', fontSize: 'var(--font-size-sm)', padding: 'var(--space-2) var(--space-2-5)', borderRadius: 'var(--radius-md)', background:'var(--bg-danger-soft)' }}>{installError}</div>}
      {filtered.length === 0 ? <div aria-live="polite" style={{ flex: 1, minHeight: dialog ? 260 : 180, border: '1px solid var(--border-default)', borderRadius: 'var(--radius-lg)', background: 'var(--bg-surface)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}><PanelTop size={30} color="var(--text-secondary)" /><strong style={{ marginTop: 'var(--space-5)', fontSize: 'var(--font-size-body)' }}>{loading ? '正在加载 MCP 市场…' : '暂无可用 MCP'}</strong><span style={{ marginTop: 'var(--space-2)', fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>{loading ? '正在从官方 Registry 获取列表。' : '市场中的 MCP 服务器将在此处展示。'}</span>{dialog && !loading && <span style={{ marginTop: 'var(--space-1-75)', fontSize: 'var(--font-size-compact)', color: 'var(--text-muted)' }}>请检查网络连接，或稍后再试。</span>}</div> : <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2-5)', overflowY: dialog ? 'auto' : undefined, flex: dialog ? 1 : undefined }}>
      {filtered.map((m) => {
        const installed = installedIds.includes(m.id);
        return (
        <div key={m.id} className="glass-card" style={{ padding: 'var(--space-3-5)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 600 }}>{m.name}</div>
              <span
                style={{
                  fontSize: 'var(--font-size-xs)',
                  padding: '1px var(--space-1-5)',
                  borderRadius: 'var(--radius-full)',
                  backgroundColor: 'var(--bg-card-hover)',
                  color: 'var(--text-muted)',
                }}
              >
                {m.category}
              </span>
            </div>
            <button
              disabled={busyId !== null || installed}
              onClick={() => void install(m)}
              style={{
                padding: 'var(--space-1) var(--space-2-5)',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-info-soft)',
                color: 'var(--accent-cyan)',
                fontSize: 'var(--font-size-label)',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-1)',
              }}
            >
              <Download size={12} />
              <span>{installed ? '已添加' : busyId === m.id ? '添加中…' : '添加'}</span>
            </button>
          </div>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginTop: 'var(--space-1)' }}>
            {m.description}
          </div>
          <div style={{ display:'flex', gap: 'var(--space-3)', marginTop: 'var(--space-1-5)', fontSize:'var(--font-size-subtle)', color:'var(--text-muted)', overflowWrap:'anywhere' }}>
            <span>Registry v{m.version || 'unknown'}</span>
            {m.repository && <a href={m.repository} target="_blank" rel="noreferrer" style={{ color:'var(--accent-cyan)' }}>查看源仓库</a>}
            {!!m.packages?.length && <span>{m.packages.map(pkg => `${pkg.registryType || 'package'}:${pkg.identifier || ''}`).join(' · ')}</span>}
            {!!m.remotes?.length && <span>远程传输</span>}
            {!!m.remotes?.some(remote => remote.headers?.length) && <span>需配置请求头：{m.remotes.flatMap(remote => remote.headers || []).map(header => header.name).join(', ')}</span>}
          </div>
        </div>
      ); })}
      {dialog && hasMore && onLoadMore && <button disabled={loading} onClick={onLoadMore} style={{ alignSelf:'center', padding: 'var(--space-2) var(--space-4)', borderRadius: 'var(--radius-md)', border:'1px solid var(--border-default)', color:'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>{loading ? '加载中…' : '加载更多'}</button>}
      </div>}
    </div>
  );
};
