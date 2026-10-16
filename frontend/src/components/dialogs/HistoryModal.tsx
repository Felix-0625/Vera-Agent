import React, { useState } from 'react';
import { Folder } from 'lucide-react';
import { useLayoutStore } from '../../stores/layoutStore';
import { useChatStore } from '../../stores/chatStore';
import { useProjectStore } from '../../stores/projectStore';
import { updateThread } from '../../api/chatApi';
import { Modal } from '../common/Modal';
import { SearchField } from '../common/Field';

/**
 * 模态弹窗 2 - 对话历史
 * 严格按照 Penpot 原型 "History · 对话历史"
 */
export const HistoryModal: React.FC = () => {
  const { historyOpen, setHistoryOpen } = useLayoutStore();
  const { threads, selectThread, loadThreads } = useChatStore();
  const { projectsHistory } = useProjectStore();
  const [search, setSearch] = useState('');
  const [actionError, setActionError] = useState('');

  const filtered = threads.filter((t) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return t.title.toLowerCase().includes(q) || t.thread_id.toLowerCase().includes(q);
  });

  const handleSelect = (id: string) => {
    selectThread(id);
    setHistoryOpen(false);
  };

  const handleUnarchive = async (event: React.MouseEvent, id: string) => {
    event.stopPropagation();
    setActionError('');
    try {
      await updateThread(id, { is_archived: false });
      await loadThreads();
    } catch {
      setActionError('恢复对话失败，请稍后重试。');
    }
  };

  return (
    <Modal
      isOpen={historyOpen}
      onClose={() => setHistoryOpen(false)}
      title=""
      width={680}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3-5)' }}>
        {actionError && <div role="alert" style={{ color: 'var(--accent-rose)', fontSize: 'var(--font-size-sm)' }}>{actionError}</div>}
        {/* 顶部标题与副标题严格对齐 Penpot */}
        <div>
          <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
            对话历史
          </h2>
          <p style={{ fontSize: 'var(--font-size-control)', color: 'var(--text-muted)', marginTop: 'var(--space-1)', marginBottom: 0 }}>
            按最近活动查看并继续之前的工作
          </p>
        </div>

        {/* 搜索框 */}
        <SearchField aria-label="搜索对话" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索对话…" />

        {/* 历史对话列表 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1-5)', maxHeight: 420, overflowY: 'auto' }}>
          {filtered.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px var(--space-5)' }}>
              <div style={{ fontSize: 'var(--font-size-body)', fontWeight: 600, color: 'var(--text-primary)' }}>
                暂无历史对话
              </div>
              <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', marginTop: 'var(--space-1)' }}>
                新的对话会显示在这里
              </div>
            </div>
          ) : (
            filtered.map((t) => (
              <div
                key={t.thread_id}
                onClick={() => handleSelect(t.thread_id)}
                className="glass-card"
                style={{
                  padding: 'var(--space-3) var(--space-3-5)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                <div>
                  <div style={{ fontSize: 'var(--font-size-subheading)', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {t.title || '对话'}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1-5)', fontSize: 'var(--font-size-label)', color: 'var(--text-muted)', marginTop: 'var(--space-0-75)' }}>
                    <Folder size={12} color="var(--accent-cyan)" />
                    <span>{projectsHistory.find((project) => project.id === t.project_id)?.name || 'VeraAgent'}</span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>
                  {t.is_archived && (
                    <button
                      onClick={(event) => void handleUnarchive(event, t.thread_id)}
                      aria-label={`取消归档 ${t.title || '对话'}`}
                      style={{ color: 'var(--accent-cyan)', fontSize: 'var(--font-size-compact)', fontWeight: 600 }}
                    >
                      取消归档
                    </button>
                  )}
                  <span>{t.updated_at ? new Date(t.updated_at * 1000).toLocaleDateString() : '刚刚'}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </Modal>
  );
};
