import React, { useCallback, useEffect, useState } from 'react';
import { Sparkles, Trash2, RefreshCw } from 'lucide-react';
import { fetchSkills, scanSkills, toggleSkill, deleteSkill, fetchSkillsMarket, installSkill } from '../../api/settingsApi';
import { SkillItem } from '../../types/settings';
import { Switch } from '../common/Switch';

export const SkillsTab: React.FC<{ active?: boolean }> = ({ active = true }) => {
  const [activeSubTab, setActiveSubTab] = useState<'installed' | 'market'>('installed');
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [market, setMarket] = useState<Array<{ name: string; description: string; category: string }>>([]);
  const [error, setError] = useState('');
  const [busySkill, setBusySkill] = useState<string | null>(null);

  const loadData = useCallback(async (scan = false) => {
    const errors: string[] = [];
    const fetchInstalledSkills = scan ? scanSkills : fetchSkills;
    await Promise.all([
      fetchInstalledSkills()
        .then((data) => setSkills(data.skills || []))
        .catch((cause: unknown) => errors.push(cause instanceof Error ? cause.message : '技能列表加载失败')),
      fetchSkillsMarket()
        .then((data) => setMarket(data.market || []))
        .catch((cause: unknown) => errors.push(cause instanceof Error ? cause.message : '技能市场加载失败')),
    ]);
    setError(errors.join('；'));
  }, []);

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- Fetch installed skills and market data when this panel becomes active.
    if (active) void loadData();
  }, [active, loadData]);

  const handleToggle = async (s: SkillItem) => {
    setBusySkill(s.name);
    setError('');
    try {
      await toggleSkill(s.name);
      await loadData();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : `更新 ${s.name} 状态失败`);
    } finally {
      setBusySkill(null);
    }
  };

  const handleDelete = async (name: string) => {
    if (window.confirm(`确定删除技能 ${name} 吗？`)) {
      try {
        await deleteSkill(name);
        await loadData();
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : `删除 ${name} 失败`);
      }
    }
  };

  const handleInstall = async (m: { name: string; description: string }) => {
    setBusySkill(m.name);
    setError('');
    try {
      await installSkill(m);
      await loadData();
      setActiveSubTab('installed');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : `添加 ${m.name} 失败`);
    } finally {
      setBusySkill(null);
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-workspace)' }}>
      {/* Tab Switcher */}
      <div style={{ padding: 'var(--space-2) var(--space-4)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', gap: 'var(--space-3)', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <button
            onClick={() => setActiveSubTab('installed')}
            style={{
              padding: 'var(--space-1) var(--space-2-5)',
              borderRadius: 'var(--radius-sm)',
              fontSize: 'var(--font-size-sm)',
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
              padding: 'var(--space-1) var(--space-2-5)',
              borderRadius: 'var(--radius-sm)',
              fontSize: 'var(--font-size-sm)',
              fontWeight: activeSubTab === 'market' ? 600 : 400,
              backgroundColor: activeSubTab === 'market' ? 'var(--bg-card)' : 'transparent',
              color: activeSubTab === 'market' ? 'var(--text-primary)' : 'var(--text-muted)',
            }}
          >
            技能市场
          </button>
        </div>

        <button
          onClick={() => void loadData(true)}
          style={{ padding: 'var(--space-1)', color: 'var(--text-muted)' }}
          title="扫描刷新"
        >
          <RefreshCw size={13} />
        </button>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-4)' }}>
        {error && <div role="alert" style={{ marginBottom: 'var(--space-3)', padding: 'var(--space-2) var(--space-2-5)', borderRadius: 'var(--radius-md)', color: 'var(--accent-rose)', background: 'var(--bg-danger-soft)', fontSize: 'var(--font-size-sm)' }}>{error}</div>}
        {activeSubTab === 'installed' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {skills.map((s) => (
              <div
                key={s.name}
                className="glass-card"
                style={{ padding: 'var(--space-3) var(--space-3-5)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)' }}>
                  <Sparkles size={16} color="var(--accent-primary)" />
                  <div>
                    <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 600 }}>{s.name}</div>
                    <div style={{ fontSize: 'var(--font-size-label)', color: 'var(--text-secondary)' }}>{s.description}</div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)' }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)' }}>{s.enabled === false ? '已停用' : '已启用'}</span>
                  <Switch label={`启用 Skill：${s.name}`} checked={s.enabled !== false} disabled={busySkill === s.name} onChange={() => void handleToggle(s)} />
                  <button onClick={() => handleDelete(s.name)} style={{ padding: 'var(--space-1)', color: 'var(--accent-rose)' }} title="删除">
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2-5)' }}>
            {market.map((m) => (
              <div key={m.name} className="glass-card" style={{ padding: 'var(--space-3-5)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 600 }}>{m.name}</div>
                  <button
                    disabled={busySkill === m.name}
                    onClick={() => void handleInstall(m)}
                    style={{ padding: 'var(--space-1) var(--space-2-5)', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-accent-soft)', color: 'var(--accent-primary)', fontSize: 'var(--font-size-label)' }}
                  >
                    一键启用
                  </button>
                </div>
                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginTop: 'var(--space-1)' }}>{m.description}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
