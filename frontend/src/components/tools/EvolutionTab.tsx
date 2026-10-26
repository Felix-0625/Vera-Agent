import React, { useCallback, useEffect, useState } from 'react';
import { FlaskConical, RefreshCw, Sparkles } from 'lucide-react';
import {
  adoptProposal,
  analyzeTraces,
  fetchProposals,
  rejectProposal,
  rollbackProposal,
  startGate,
} from '../../api/learningApi';
import { EvolutionProposal, GateStage } from '../../types/learning';
import { PROPOSAL_STATUS_LABELS, formatDelta, formatRate, verdictLabel } from './learningFormat';

const SPLIT_LABELS: Record<GateStage['split'], string> = { train: '训练集', holdout: '留出集', guard: '守护集' };

const GateTable: React.FC<{ stages: GateStage[] }> = ({ stages }) => (
  <table className="learning-gate">
    <thead><tr><th scope="col">阶段</th><th scope="col">基线</th><th scope="col">候选</th><th scope="col">差值</th><th scope="col">结论</th></tr></thead>
    <tbody>
      {stages.map((stage) => (
        <tr key={stage.split}>
          <th scope="row">{SPLIT_LABELS[stage.split]}（{stage.cases}）</th>
          <td>{formatRate(stage.baseline_pass_rate)}</td>
          <td>{formatRate(stage.candidate_pass_rate)}</td>
          <td>{formatDelta(stage)}</td>
          <td>{stage.split === 'guard' ? (stage.regressions?.length ? `回退：${stage.regressions.join('、')}` : '无回退') : verdictLabel(stage.verdict)}</td>
        </tr>
      ))}
    </tbody>
  </table>
);

const ProposalCard: React.FC<{ proposal: EvolutionProposal; onAction: (action: () => Promise<unknown>, confirmText?: string) => void }> = ({ proposal, onAction }) => {
  const id = proposal.proposal_id;
  const canGate = proposal.kind !== 'eval_case' && ['draft', 'gated', 'not_recommended'].includes(proposal.status);
  return (
    <section className="metrics-card learning-proposal">
      <header className="metrics-card-title">
        <h3>{proposal.title}</h3>
        <span className={`learning-tag status-${proposal.status}`}>{PROPOSAL_STATUS_LABELS[proposal.status]}</span>
      </header>
      <p className="learning-rationale">{proposal.rationale}</p>
      <details><summary>查看改动</summary><pre>{proposal.diff}</pre></details>
      {proposal.gate && <><p className="learning-gate-reason">{proposal.gate.reason}</p>{proposal.gate.stages.length > 0 && <GateTable stages={proposal.gate.stages} />}</>}
      {proposal.monitor && (
        <p className="learning-monitor">线上得分：采纳前 {formatRate(proposal.monitor.before_mean)} → 采纳后 {formatRate(proposal.monitor.after_mean)}（{proposal.monitor.after_traces} 条记录）</p>
      )}
      <div className="learning-actions">
        {proposal.gate_running && <span role="status">评测运行中…</span>}
        {canGate && !proposal.gate_running && (
          <button type="button" onClick={() => onAction(() => startGate(id), '评测会多次调用模型并产生费用，确定开始吗？')}><FlaskConical size={14} /> 运行评测</button>
        )}
        {proposal.status === 'recommended' && (
          <button type="button" className="primary" onClick={() => onAction(() => adoptProposal(id), '采纳后，这条改动会影响之后的每一轮对话。确定采纳吗？')}>采纳</button>
        )}
        {['draft', 'gated', 'recommended', 'not_recommended'].includes(proposal.status) && (
          <button type="button" onClick={() => onAction(() => rejectProposal(id))}>拒绝</button>
        )}
        {proposal.status === 'adopted' && (
          <button type="button" onClick={() => onAction(() => rollbackProposal(id), '确定回滚这条改动吗？')}>回滚</button>
        )}
      </div>
    </section>
  );
};

export const EvolutionTab: React.FC = () => {
  const [proposals, setProposals] = useState<EvolutionProposal[]>([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setProposals((await fetchProposals()).proposals); } catch (cause) { setError(cause instanceof Error ? cause.message : '提案加载失败'); }
  }, []);
  // oxlint-disable-next-line react/set-state-in-effect -- Load proposals once when the panel opens.
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!proposals.some((item) => item.gate_running)) return;
    const timer = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(timer);
  }, [load, proposals]);

  const act = async (action: () => Promise<unknown>, confirmText?: string) => {
    if (confirmText && !window.confirm(confirmText)) return;
    setError('');
    try { await action(); await load(); } catch (cause) { setError(cause instanceof Error ? cause.message : '操作失败'); }
  };
  const analyze = async () => {
    if (!window.confirm('分析会调用模型读取最近的低分记录，确定开始吗？')) return;
    setBusy(true);
    setError('');
    try {
      const result = await analyzeTraces();
      setNotice(`分析了 ${result.traces} 条低分记录，生成 ${result.proposals.length} 条提案、${result.drafts.length} 份评测用例草稿。`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '分析失败');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="metrics-page">
      <div className="metrics-header">
        <div className="metrics-heading"><span><Sparkles size={16} /></span><strong>改进提案</strong></div>
        <span className="learning-row-actions">
          <button type="button" className="metrics-refresh" onClick={() => void analyze()} disabled={busy} title="分析低分记录" aria-label="分析低分记录"><FlaskConical size={14} /></button>
          <button type="button" className="metrics-refresh" onClick={() => void load()} title="刷新" aria-label="刷新提案"><RefreshCw size={14} /></button>
        </span>
      </div>
      {error && <div className="metrics-empty metrics-error" role="alert">{error}</div>}
      {notice && <div className="metrics-empty-small" role="status">{notice}</div>}
      {!proposals.length ? <div className="metrics-empty"><Sparkles size={25} /><span>暂无提案。积累一些执行记录后，点击右上角分析低分记录。</span></div>
        : proposals.map((proposal) => <ProposalCard key={proposal.proposal_id} proposal={proposal} onAction={(action, text) => void act(action, text)} />)}
    </div>
  );
};
