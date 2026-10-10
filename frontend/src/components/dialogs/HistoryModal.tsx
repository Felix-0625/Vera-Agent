import React, { useState } from 'react';
import { Search, Folder } from 'lucide-react';
import { useLayoutStore } from '../../stores/layoutStore';
import { useChatStore } from '../../stores/chatStore';
import { useProjectStore } from '../../stores/projectStore';
import { Modal } from '../common/Modal';

/**
 * 模态弹窗 2 - 对话历史
 * 严格按照 Penpot 原型 "History · 对话历史"
 */
export const HistoryModal: React.FC = () => {
  const { historyOpen, setHistoryOpen } = useLayoutStore();
  const { threads, selectThread } = useChatStore();
  const { currentProject } = useProjectStore();
  const [search, setSearch] = useState('');

  const filtered = threads.filter((t) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return t.title.toLowerCase().includes(q) || t.thread_id.toLowerCase().includes(q);
  });

  const handleSelect = (id: string) => {
    selectThread(id);
    setHistoryOpen(false);
  };

  return (
    <Modal
      isOpen={historyOpen}
      onClose={() => setHistoryOpen(false)}
      title=""
      width={680}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* 顶部标题与副标题严格对齐 Penpot */}
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
            对话历史
          </h2>
          <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 4, marginBottom: 0 }}>
            按最近活动查看并继续之前的工作
          </p>
        </div>

        {/* 搜索框 */}
        <div style={{ position: 'relative' }}>
          <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: 11 }} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索对话…"
            style={{
              width: '100%',
              padding: '9px 12px 9px 36px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-default)',
              fontSize: 13,
              color: 'var(--text-primary)',
            }}
          />
        </div>

        {/* 历史对话列表 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 420, overflowY: 'auto' }}>
          {filtered.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 20px' }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                暂无历史对话
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
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
                  padding: '12px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>
                    {t.title || '对话'}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5, color: 'var(--text-muted)', marginTop: 3 }}>
                    <Folder size={12} color="var(--accent-cyan)" />
                    <span>{currentProject?.name || 'VeraAgent'}</span>
                  </div>
                </div>

                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {t.updated_at ? new Date(t.updated_at).toLocaleDateString() : '刚刚'}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </Modal>
  );
};
