import React, { useEffect, useState } from 'react';
import { Sparkles, Trash2, Plus, RefreshCw, Check } from 'lucide-react';
import { fetchSkills, scanSkills, toggleSkill, deleteSkill, fetchSkillsMarket, installSkill } from '../../api/settingsApi';
import { SkillItem } from '../../types/settings';
import { Switch } from '../common/Switch';

export const SkillsTab: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'installed' | 'market'>('installed');
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [market, setMarket] = useState<Array<{ name: string; description: string; category: string }>>([]);

  const loadData = async () => {
    try {
      const sData = await fetchSkills();
      setSkills(sData.skills || []);
      const mData = await fetchSkillsMarket();
      setMarket(mData.market || []);
    } catch {
      // fallback
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggle = async (s: SkillItem) => {
    await toggleSkill(s.name);
    loadData();
  };

  const handleDelete = async (name: string) => {
    if (window.confirm(`确定删除技能 ${name} 吗？`)) {
      await deleteSkill(name);
      loadData();
    }
  };

  const handleInstall = async (m: { name: string; description: string }) => {
    await installSkill(m);
    loadData();
    setActiveSubTab('installed');
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-workspace)' }}>
      {/* Tab Switcher */}
      <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', gap: 12, alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => setActiveSubTab('installed')}
            style={{
              padding: '4px 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: 12,
              fontWeight: activeSubTab === 'installed' ? 600 : 400,
              backgroundColor: activeSubTab === 'installed' ? 'var(--bg-card)' : 'transparent',
              color: activeSubTab === 'installed' ? 'var(--text-primary)' : 'var(--text-muted)',
            }}
          >
            本地技能
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
            技能市场
          </button>
        </div>

        <button
          onClick={loadData}
          style={{ padding: 4, color: 'var(--text-muted)' }}
          title="扫描刷新"
        >
          <RefreshCw size={13} />
        </button>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {activeSubTab === 'installed' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {skills.map((s) => (
              <div
                key={s.name}
                className="glass-card"
                style={{ padding: '12px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Sparkles size={16} color="var(--accent-primary)" />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{s.name}</div>
                    <div style={{ fontSize: 11.5, color: 'var(--text-secondary)' }}>{s.description}</div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <button onClick={() => handleDelete(s.name)} style={{ padding: 4, color: 'var(--accent-rose)' }} title="删除">
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {market.map((m) => (
              <div key={m.name} className="glass-card" style={{ padding: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{m.name}</div>
                  <button
                    onClick={() => handleInstall(m)}
                    style={{ padding: '4px 10px', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(124,58,237,0.15)', color: '#C4B5FD', fontSize: 11.5 }}
                  >
                    一键启用
                  </button>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{m.description}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
