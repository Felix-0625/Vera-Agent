import React, { useCallback, useEffect, useState } from 'react';
import { Brain, Check, History, RefreshCw, Trash2, X } from 'lucide-react';
import {
  deleteMemory,
  fetchMemories,
  fetchMemoryHistory,
  fetchPendingChanges,
  resolvePendingChange,
  restoreMemoryVersion,
} from '../../api/learningApi';
import { MemoryItem, MemoryVersion, PendingMemoryChange } from '../../types/learning';
import { MEMORY_KIND_LABELS } from './learningFormat';

const SCOPE_LABELS: Record<string, string> = { user: '个人', project: '项目', session: '会话' };

const PendingList: React.FC<{ changes: PendingMemoryChange[]; onResolve: (id: string, accept: boolean) => void }> = ({ changes, onResolve }) => (
  <section className="metrics-card learning-pending">
    <header className="metrics-card-title"><h3>待确认的修改</h3><span className="metrics-total">{changes.length} 条</span></header>
    <ul className="learning-list">
      {changes.map((change) => (
        <li key={change.change_id} className="learning-change">
          <div>
            <strong>{change.operation === 'delete' ? '删除' : '更新'}</strong>
            <del>{change.current_content}</del>
            {change.operation === 'update' && <ins>{change.content}</ins>}
            {change.reason && <small>原因：{change.reason}</small>}
          </div>
          <span className="learning-row-actions">
            <button type="button" onClick={() => onResolve(change.change_id, true)} aria-label="接受修改"><Check size={14} /></button>
            <button type="button" onClick={() => onResolve(change.change_id, false)} aria-label="拒绝修改"><X size={14} /></button>
          </span>
        </li>
      ))}
    </ul>
  </section>
);

const VersionList: React.FC<{ versions: MemoryVersion[]; onRestore: (version: number) => void }> = ({ versions, onRestore }) => (
  <ol className="learning-versions">
    {versions.map((entry) => (
      <li key={entry.version}>
        <span>v{entry.version} · {entry.actor} · {entry.reason || entry.status}</span>
        <q>{entry.content}</q>
        {entry.version !== versions.at(-1)?.version && <button type="button" onClick={() => onRestore(entry.version)}>恢复此版本</button>}
      </li>
    ))}
  </ol>
);

export const MemoryTab: React.FC = () => {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [pending, setPending] = useState<PendingMemoryChange[]>([]);
  const [scope, setScope] = useState('');
  const [history, setHistory] = useState<{ id: string; versions: MemoryVersion[] } | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      const [list, changes] = await Promise.all([fetchMemories(scope ? { scope } : {}), fetchPendingChanges()]);
      setMemories(list.memories);
      setPending(changes.changes);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '记忆加载失败');
    }
  }, [scope]);
  // oxlint-disable-next-line react/set-state-in-effect -- The request must begin when the scope filter changes.
  useEffect(() => { void load(); }, [load]);

  const run = async (action: () => Promise<unknown>) => {
    try { await action(); await load(); } catch (cause) { setError(cause instanceof Error ? cause.message : '操作失败'); }
  };
  const showHistory = async (memoryId: string) => {
    if (history?.id === memoryId) { setHistory(null); return; }
    setHistory({ id: memoryId, versions: (await fetchMemoryHistory(memoryId)).history });
  };

  return (
    <div className="metrics-page">
      <div className="metrics-header">
        <div className="metrics-heading"><span><Brain size={16} /></span><strong>长期记忆</strong></div>
        <button className="metrics-refresh" onClick={() => void load()} title="刷新" aria-label="刷新记忆"><RefreshCw size={14} /></button>
      </div>
      {error && <div className="metrics-empty metrics-error" role="alert">{error}</div>}
      {pending.length > 0 && <PendingList changes={pending} onResolve={(id, accept) => void run(() => resolvePendingChange(id, accept))} />}
      <div className="metrics-periods" role="group" aria-label="记忆范围">
        {['', 'user', 'project', 'session'].map((value) => (
          <button key={value || 'all'} type="button" className={scope === value ? 'active' : ''} onClick={() => setScope(value)}>{value ? SCOPE_LABELS[value] : '全部'}</button>
        ))}
      </div>
      <section className="metrics-card">
        {!memories.length ? <div className="metrics-empty-small">暂无记忆</div> : (
          <ul className="learning-list">
            {memories.map((memory) => (
              <li key={memory.memory_id} className="learning-memory">
                <div>
                  <span className={`learning-tag ${memory.kind}`}>{MEMORY_KIND_LABELS[memory.kind]}</span>
                  <small>{SCOPE_LABELS[memory.scope]} · v{memory.version} · 置信度 {memory.confidence.toFixed(1)} · 使用 {memory.use_count} 次</small>
                  <p>{memory.content}</p>
                  {history?.id === memory.memory_id && <VersionList versions={history.versions} onRestore={(version) => void run(() => restoreMemoryVersion(memory.memory_id, version))} />}
                </div>
                <span className="learning-row-actions">
                  <button type="button" onClick={() => void showHistory(memory.memory_id)} aria-label="查看版本历史"><History size={14} /></button>
                  <button type="button" onClick={() => void run(() => deleteMemory(memory.memory_id))} aria-label="删除记忆"><Trash2 size={14} /></button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
};
