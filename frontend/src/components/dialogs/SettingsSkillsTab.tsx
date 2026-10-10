import React, { useState } from 'react';
import { Search, Plus, Grid, Trash2, Sparkles, Check } from 'lucide-react';
import { SkillItem } from '../../types/settings';
import { fetchSkillsMarket, installSkill } from '../../api/settingsApi';
import { Modal } from '../common/Modal';

interface SettingsSkillsTabProps {
  skills: SkillItem[];
  onDelete: (name: string) => Promise<void>;
  onNewSkill?: () => void;
  onOpenMarket?: () => void;
}

/**
 * 设置中心 - Skill Tab
 * 严格对齐 Penpot 画板 "系统设置 · Skill"
 */
export const SettingsSkillsTab: React.FC<SettingsSkillsTabProps> = ({
  skills,
  onDelete,
  onNewSkill,
  onOpenMarket,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [dialog, setDialog] = useState<'market' | 'create' | null>(null);
  const [market, setMarket] = useState<Array<{name:string;description:string;category:string}>>([]);
  const [skillName, setSkillName] = useState('');
  const [description, setDescription] = useState('');
  const [instructions, setInstructions] = useState('# Skill 指南\n\n');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const openMarket = async () => {
    setDialog('market'); setError('');
    try { const res = await fetchSkillsMarket(); setMarket(res.market || []); } catch { setError('技能市场加载失败，请检查服务连接。'); }
  };
  const createSkill = async () => {
    const name = skillName.trim();
    if (!name) { setError('请输入 Skill 名称。'); return; }
    if (!/^[a-zA-Z0-9_-]+$/.test(name)) { setError('名称仅支持英文字母、数字、连字符和下划线。'); return; }
    if (skills.some(skill => skill.name.toLowerCase() === name.toLowerCase())) { setError('同名 Skill 已存在，请使用其他名称。'); return; }
    setBusy(true); setError('');
    try { await installSkill({ name, description: description.trim() || name, instructions }); setDialog(null); setSkillName(''); setDescription(''); setInstructions('# Skill 指南\n\n'); await onNewSkill?.(); }
    catch { setError('保存失败，请检查名称或服务连接。'); } finally { setBusy(false); }
  };
  const installMarketSkill = async (skill: {name:string;description:string}) => {
    setBusy(true); setError('');
    try { await installSkill(skill); await onNewSkill?.(); setMarket(current => current.filter(item => item.name !== skill.name)); }
    catch { setError(`安装 ${skill.name} 失败，请检查服务连接。`); } finally { setBusy(false); }
  };

  const filtered = skills.filter(
    (s) =>
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      {/* 标题与描述严格对齐 Penpot */}
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
          Skill
        </h2>
        <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 4, marginBottom: 0 }}>
          管理 Agent 可调用的技能。
        </p>
      </div>

      {/* 搜索与工具条 */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <div
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            backgroundColor: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-sm)',
            padding: '6px 10px',
          }}
        >
          <Search size={14} color="var(--text-muted)" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="搜索 Skills…"
            style={{
              width: '100%',
              backgroundColor: 'transparent',
              fontSize: 12.5,
              color: 'var(--text-primary)',
            }}
          />
        </div>

        <button
          onClick={() => { void openMarket(); }}
          style={{
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-secondary)',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 5,
          }}
        >
          <Grid size={13} />
          <span>浏览技能市场</span>
        </button>

        <button
          onClick={() => { setError(''); setDialog('create'); }}
          style={{
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--accent-primary)',
            color: '#FFFFFF',
            fontSize: 12,
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <Plus size={13} />
          <span>新建</span>
        </button>
      </div>

      {/* 技能列表或空态 */}
      {filtered.length === 0 ? (
        <div
          className="glass-card"
          style={{
            padding: '40px 20px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>
            暂无 Skill
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
            创建 Skill 或从技能市场添加。
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {filtered.map((s) => (
            <div
              key={s.name}
              className="glass-card"
              style={{
                padding: '10px 14px',
                borderRadius: 'var(--radius-sm)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Sparkles size={15} color="var(--accent-primary)" />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{s.name}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{s.description}</div>
                </div>
              </div>

              <button
                onClick={() => onDelete(s.name)}
                style={{ padding: 4, color: 'var(--accent-rose)' }}
                title="删除 Skill"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      )}
      <Modal isOpen={dialog === 'market'} onClose={() => setDialog(null)} title="技能市场" width={760}>
        <div style={{ display:'flex', flexDirection:'column', gap:10, maxHeight:'calc(90vh - 110px)', overflowY:'auto', padding:2 }}>
          {error && <div role="alert" style={{ color:'var(--accent-rose)', fontSize:12, padding:'8px 10px', borderRadius:8, background:'rgba(244,63,94,.08)' }}>{error}</div>}
          {market.map(skill => {
            const installed = skills.some(item => item.name.toLowerCase() === skill.name.toLowerCase());
            return <article key={skill.name} style={{ display:'grid', gridTemplateColumns:'minmax(0,1fr) auto', alignItems:'center', gap:20, padding:'15px 16px', border:'1px solid rgba(148,163,184,.14)', borderRadius:13, background:'linear-gradient(115deg, rgba(255,255,255,.035), rgba(255,255,255,.012))', transition:'border-color .16s ease, background .16s ease' }}>
              <div style={{ display:'flex', alignItems:'flex-start', gap:12, minWidth:0 }}>
                <span aria-hidden="true" style={{ flex:'0 0 34px', width:34, height:34, display:'grid', placeItems:'center', borderRadius:10, color:'#bb8aff', background:'rgba(139,92,246,.14)', border:'1px solid rgba(167,139,250,.18)' }}><Sparkles size={16}/></span>
                <div style={{ minWidth:0 }}>
                  <div style={{ fontSize:13.5, fontWeight:650, color:'var(--text-primary)', lineHeight:1.4, overflowWrap:'anywhere' }}>{skill.name}</div>
                  <span style={{ display:'inline-flex', marginTop:5, padding:'2px 7px', borderRadius:999, color:'#a99abf', background:'rgba(139,92,246,.09)', fontSize:10.5, lineHeight:1.5 }}>{skill.category}</span>
                  <div style={{ fontSize:11.5, lineHeight:1.55, color:'var(--text-muted)', marginTop:6, overflowWrap:'anywhere' }}>{skill.description}</div>
                </div>
              </div>
              <button disabled={busy || installed} onClick={() => void installMarketSkill(skill)} style={{ display:'inline-flex', flex:'0 0 78px', width:78, minWidth:78, height:34, alignItems:'center', justifyContent:'center', gap:5, whiteSpace:'nowrap', padding:'0 12px', borderRadius:9, background:installed?'rgba(255,255,255,.07)':'linear-gradient(135deg,#8b5cf6,#7138df)', color:installed?'var(--text-muted)':'#fff', fontSize:12, fontWeight:600, boxShadow:installed?'none':'0 4px 14px rgba(124,58,237,.2)', cursor:installed?'default':'pointer' }}>{installed?<><Check size={13}/>已添加</>:'添加'}</button>
            </article>;
          })}
          {!market.length && !error && <div style={{ padding:36, textAlign:'center', color:'var(--text-muted)', fontSize:12, border:'1px dashed var(--border-default)', borderRadius:12 }}>技能市场暂无可用项目。</div>}
        </div>
      </Modal>
      <Modal isOpen={dialog === 'create'} onClose={() => setDialog(null)} title="新建 Skill" width={680}>
        <div style={{display:'flex',flexDirection:'column',gap:12}}>
          {error && <div role="alert" style={{color:'var(--accent-rose)',fontSize:12}}>{error}</div>}
          <label style={{fontSize:12,color:'var(--text-secondary)'}}>名称<input value={skillName} onChange={e=>setSkillName(e.target.value)} placeholder="例如: project-guidelines" style={{display:'block',width:'100%',marginTop:5,padding:'9px 11px',borderRadius:8,background:'var(--bg-surface-elevated)',border:'1px solid var(--border-default)',color:'var(--text-primary)'}} /></label>
          <label style={{fontSize:12,color:'var(--text-secondary)'}}>简介<input value={description} onChange={e=>setDescription(e.target.value)} placeholder="描述这个 Skill 的用途" style={{display:'block',width:'100%',marginTop:5,padding:'9px 11px',borderRadius:8,background:'var(--bg-surface-elevated)',border:'1px solid var(--border-default)',color:'var(--text-primary)'}} /></label>
          <label style={{fontSize:12,color:'var(--text-secondary)'}}>SKILL.md 内容<textarea value={instructions} onChange={e=>setInstructions(e.target.value)} rows={12} spellCheck={false} style={{display:'block',width:'100%',resize:'vertical',marginTop:5,padding:11,borderRadius:8,background:'var(--bg-surface-elevated)',border:'1px solid var(--border-default)',color:'var(--text-primary)',fontFamily:'ui-monospace,monospace',fontSize:12,lineHeight:1.55}} /></label>
          <div style={{display:'flex',justifyContent:'flex-end',gap:8}}><button onClick={()=>setDialog(null)} style={{padding:'8px 12px',fontSize:12,color:'var(--text-secondary)'}}>取消</button><button disabled={busy} onClick={()=>void createSkill()} style={{padding:'8px 14px',borderRadius:8,background:'var(--accent-primary)',color:'#fff',fontSize:12}}>{busy?'保存中…':'创建 Skill'}</button></div>
        </div>
      </Modal>
    </div>
  );
};
