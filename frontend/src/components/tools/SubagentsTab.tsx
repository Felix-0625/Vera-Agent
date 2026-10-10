import React, { useMemo, useState } from 'react';
import { Bot, ChevronRight, Clock3 } from 'lucide-react';
import { SubagentRun } from '../../types/chat';
import { useChatStore } from '../../stores/chatStore';
import { SubagentDetailView } from './SubagentDetailView';

export const SubagentsTab: React.FC = () => {
  const messages = useChatStore((state) => state.messages);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const agents = useMemo(() => {
    const byId = new Map<string, SubagentRun>();
    messages.forEach((message) => message.extra?.subagents?.forEach((agent) => byId.set(agent.id, agent)));
    return [...byId.values()].sort((a, b) => b.started_at - a.started_at);
  }, [messages]);
  const selected = agents.find((agent) => agent.id === selectedId);
  const running = agents.filter((agent) => agent.status === 'running');
  const completed = agents.filter((agent) => agent.status !== 'running');

  if (selected) return <SubagentDetailView agent={selected} onBack={() => setSelectedId(null)} />;

  const renderAgent = (agent: SubagentRun) => <button key={agent.id} type="button" onClick={() => setSelectedId(agent.id)} className="glass-card" style={{ width: '100%', padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12, textAlign: 'left', cursor: 'pointer' }}>
    <span style={{ width: 30, height: 30, display: 'grid', placeItems: 'center', borderRadius: 8, background: 'rgba(96,165,250,.13)', color: '#60A5FA' }}><Bot size={17} /></span>
    <span style={{ minWidth: 0, flex: 1 }}>
      <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 13, fontWeight: 600 }}>{agent.title}</span>
      <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: 4, color: 'var(--text-muted)', fontSize: 11 }}>{agent.task}</span>
    </span>
    <span style={{ color: agent.status === 'running' ? 'var(--accent-cyan)' : 'var(--text-muted)', fontSize: 11, whiteSpace: 'nowrap' }}>{agent.status === 'running' ? '进行中' : agent.status === 'completed' ? '已完成' : '失败'}</span>
    <ChevronRight size={14} color="var(--text-muted)" />
  </button>;

  return <div style={{ height: '100%', overflowY: 'auto', padding: '20px 24px', background: 'var(--bg-workspace)' }}>
    <div style={{ marginBottom: 22, color: 'var(--text-secondary)', fontSize: 13 }}>进行中 · {running.length}</div>
    {running.length ? <div style={{ display: 'grid', gap: 8, marginBottom: 26 }}>{running.map(renderAgent)}</div> : <div style={{ marginBottom: 28, color: 'var(--text-muted)', fontSize: 13 }}>没有正在运行的子智能体</div>}
    <div style={{ marginBottom: 12, color: 'var(--text-secondary)', fontSize: 13 }}>已完成 · {completed.length}</div>
    {completed.length ? <div style={{ display: 'grid', gap: 8 }}>{completed.map(renderAgent)}</div> : <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>此对话还没有已完成的子智能体</div>}
    {!agents.length && <div style={{ marginTop: 24, display: 'flex', alignItems: 'center', gap: 7, color: 'var(--text-disabled)', fontSize: 11 }}><Clock3 size={13} />子智能体只会显示当前对话中实际调用的任务</div>}
  </div>;
};
