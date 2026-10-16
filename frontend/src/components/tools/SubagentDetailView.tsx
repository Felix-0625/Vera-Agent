import React from 'react';
import { ArrowLeft, CheckCircle2, CircleDashed, ChevronDown, ChevronRight, Wrench } from 'lucide-react';
import { SubagentRun } from '../../types/chat';
import { MarkdownContent } from '../composer/MarkdownContent';

interface SubagentDetailViewProps {
  agent: SubagentRun;
  onBack: () => void;
}

export const SubagentDetailView: React.FC<SubagentDetailViewProps> = ({ agent, onBack }) => (
  <div style={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column', background: 'var(--bg-workspace)' }}>
    <header style={{ minHeight: 50, display: 'flex', alignItems: 'center', gap: 'var(--space-2-5)', padding: '0 var(--space-4)', borderBottom: '1px solid var(--border-subtle)' }}>
      <button type="button" onClick={onBack} aria-label="返回子智能体列表" style={{ display: 'grid', placeItems: 'center', color: 'var(--text-muted)' }}><ArrowLeft size={16} /></button>
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 600 }}>{agent.title}</div>
        <div style={{ marginTop: 'var(--space-0-5)', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>{agent.role} · {agent.status === 'running' ? '工作中' : agent.status === 'completed' ? '已完成' : '失败'}</div>
      </div>
      {agent.status === 'running' ? <CircleDashed size={15} color="var(--accent-cyan)" className="pulse-glow" /> : <CheckCircle2 size={15} color={agent.status === 'completed' ? 'var(--accent-emerald)' : 'var(--accent-rose)'} />}
    </header>
    <div style={{ minHeight: 0, flex: 1, overflowY: 'auto', padding: 'var(--space-4-5)' }}>
      <section style={{ marginBottom: 22 }}>
        <div style={{ marginBottom: 'var(--space-2)', color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)', fontWeight: 600 }}>任务</div>
        <div style={{ color: 'var(--text-primary)', fontSize: 'var(--font-size-md)', lineHeight: 1.65, whiteSpace: 'pre-wrap' }}>{agent.task}</div>
      </section>
      <details style={{ marginBottom: 22 }}>
        <summary className="subagent-process-summary" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1-75)', marginBottom: 'var(--space-2-5)', color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)', fontWeight: 600, cursor: 'pointer', listStyle: 'none', userSelect: 'none' }}>
          <ChevronRight size={14} className="subagent-process-collapsed" />
          <ChevronDown size={14} className="subagent-process-expanded" />
          <span>执行过程</span>
          {agent.activities.length > 0 && <span style={{ color: 'var(--text-disabled)', fontWeight: 400 }}>· {agent.activities.length}</span>}
        </summary>
        {agent.activities.length ? <div style={{ display: 'grid', gap: 'var(--space-2-25)', paddingLeft: 21 }}>{agent.activities.map((activity, index) => <div key={`${activity.timestamp}-${index}`} style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-2-25)', color: activity.status === 'working' ? 'var(--text-primary)' : 'var(--text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          {activity.label === '正在分析任务' ? <CircleDashed size={14} color="var(--accent-cyan)" /> : <Wrench size={14} color="var(--text-muted)" />}
          <div><div>{activity.label}</div>{activity.detail && <div style={{ marginTop: 'var(--space-0-75)', color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)' }}>{activity.detail}</div>}</div>
        </div>)}</div> : <div style={{ paddingLeft: 21, color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>正在准备子智能体会话…</div>}
      </details>
      <section>
        <div style={{ marginBottom: 'var(--space-2-5)', color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)', fontWeight: 600 }}>输出结果</div>
        {agent.result ? <div className="markdown-content"><MarkdownContent content={agent.result} /></div> : <div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>{agent.status === 'running' ? '子智能体完成后会显示结果。' : '没有可显示的结果。'}</div>}
      </section>
    </div>
    <div style={{ padding: 'var(--space-2) var(--space-4)', borderTop: '1px solid var(--border-subtle)', color: 'var(--text-disabled)', fontSize: 'var(--font-size-xs)' }}>只读视图 · 子智能体不会在此处接收新消息</div>
  </div>
);
