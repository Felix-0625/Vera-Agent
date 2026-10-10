import React, { useEffect, useState } from 'react';
import { FileText, Plus } from 'lucide-react';
import { Switch } from '../common/Switch';
import { Modal } from '../common/Modal';
import { fetchRules, saveRules } from '../../api/settingsApi';

/**
 * 设置中心 - 规则与记忆 Tab
 * 严格对齐 Penpot 画板 "系统设置 · 规则与记忆"
 */
export const SettingsRulesTab: React.FC = () => {
  const [includeAgents, setIncludeAgents] = useState(true);
  const [includeClaude, setIncludeClaude] = useState(false);
  const [memoryEnabled, setMemoryEnabled] = useState(true);
  const [editorOpen, setEditorOpen] = useState(false);
  const [rules, setRules] = useState('');
  const [exists, setExists] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const loadRules = async () => {
    try { const result = await fetchRules(); setRules(result.content || ''); setExists(result.exists); }
    catch { setError('读取 AGENTS.md 失败，请检查服务连接。'); }
  };
  useEffect(() => { void loadRules(); }, []);
  const openEditor = async () => { setEditorOpen(true); setError(''); await loadRules(); };
  const handleSave = async () => {
    setBusy(true); setError('');
    try { await saveRules(rules); setExists(true); setEditorOpen(false); }
    catch { setError('保存 AGENTS.md 失败，请检查服务连接。'); }
    finally { setBusy(false); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      {/* 标题与描述严格对齐 Penpot */}
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
          规则与记忆
        </h2>
        <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 4, marginBottom: 0 }}>
          为 Agent 配置项目规则与对话记忆。
        </p>
      </div>

      {/* 1. 导入设置卡片 */}
      <div
        className="glass-card"
        style={{
          padding: '16px 18px',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
        }}
      >
        <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>
          导入设置
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
              将 AGENTS.md 包含在上下文中
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              智能体将读取项目根目录中的 AGENTS.md 文件并将其添加到上下文中。
            </div>
          </div>
          <Switch checked={includeAgents} onChange={() => setIncludeAgents(!includeAgents)} />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: 12 }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
              将 CLAUDE.md 包含在上下文中
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              智能体将读取项目根目录中的 CLAUDE.md 文件并将其添加到上下文中。
            </div>
          </div>
          <Switch checked={includeClaude} onChange={() => setIncludeClaude(!includeClaude)} />
        </div>
      </div>

      {/* 2. 规则卡片 */}
      <div
        className="glass-card"
        style={{
          padding: '16px 18px',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>
            规则
          </div>
          <button
            onClick={() => void openEditor()}
            style={{
              padding: '4px 10px',
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
            <span>{exists ? '编辑' : '创建'}</span>
          </button>
        </div>

        {exists ? <button onClick={() => void openEditor()} style={{ width:'100%', display:'flex', alignItems:'center', gap:10, padding:'12px 14px', textAlign:'left', border:'1px solid var(--border-subtle)', borderRadius:9, color:'var(--text-primary)' }}><FileText size={15} color="var(--accent-primary)"/><span><strong style={{display:'block',fontSize:12}}>AGENTS.md</strong><span style={{fontSize:11,color:'var(--text-muted)'}}>项目规则文件，点击查看或编辑</span></span></button> : <div style={{ padding: '24px 20px', textAlign: 'center' }}>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>
            暂无规则
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
            创建规则，为 Agent 添加持续遵循的项目约定。
          </div>
        </div>}
      </div>

      {/* 3. 记忆卡片 */}
      <div
        className="glass-card"
        style={{
          padding: '16px 18px',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)' }}>
            记忆
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
            允许 Agent 记住对话中的相关上下文。
          </div>
        </div>
        <Switch checked={memoryEnabled} onChange={() => setMemoryEnabled(!memoryEnabled)} />
      </div>
      <Modal isOpen={editorOpen} onClose={() => setEditorOpen(false)} title={exists ? '编辑项目规则' : '创建项目规则'} width={760}>
        <div style={{display:'flex',flexDirection:'column',gap:12}}>
          <div style={{fontSize:12,color:'var(--text-muted)'}}>内容将保存到项目根目录的 AGENTS.md，支持 Markdown 格式。</div>
          {error && <div role="alert" style={{fontSize:12,color:'var(--accent-rose)'}}>{error}</div>}
          <textarea autoFocus value={rules} onChange={e=>setRules(e.target.value)} spellCheck={false} placeholder={'# 项目规则\n\n写下 Agent 在本项目中应持续遵循的约定。'} rows={18} style={{width:'100%',resize:'vertical',padding:14,borderRadius:9,background:'var(--bg-surface-elevated)',border:'1px solid var(--border-default)',color:'var(--text-primary)',fontFamily:'ui-monospace,monospace',fontSize:12,lineHeight:1.6}} />
          <div style={{display:'flex',justifyContent:'flex-end',gap:8}}><button onClick={()=>setEditorOpen(false)} style={{padding:'8px 12px',fontSize:12,color:'var(--text-secondary)'}}>取消</button><button disabled={busy} onClick={()=>void handleSave()} style={{padding:'8px 14px',borderRadius:8,background:'var(--accent-primary)',color:'#fff',fontSize:12}}>{busy?'保存中…':'保存规则'}</button></div>
        </div>
      </Modal>
    </div>
  );
};
