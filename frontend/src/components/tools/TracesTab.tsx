import React, { useCallback, useEffect, useState } from 'react';
import { GitCommitVertical, RefreshCw, ThumbsDown, ThumbsUp } from 'lucide-react';
import { fetchTrace, fetchTraceSummary, fetchTraces, sendTraceFeedback } from '../../api/learningApi';
import { TaskTypeSuccess, TraceDetail, TraceSummary } from '../../types/learning';
import { describeSpan, formatRate, outcomeTone } from './learningFormat';

const TraceTree: React.FC<{ trace: TraceDetail; onFeedback: (value: number) => void }> = ({ trace, onFeedback }) => (
  <section className="metrics-card learning-detail">
    <header className="metrics-card-title">
      <h3 title={trace.input}>{trace.input || '(无输入)'}</h3>
      <span className="metrics-total">{trace.exit_status} · {trace.steps} 步 · {trace.duration.toFixed(1)} s</span>
    </header>
    <ul className="learning-scores" aria-label="评分">
      {trace.scores.map((score) => (
        <li key={score.score_id} className={`learning-score ${outcomeTone(score.value)}`} title={score.comment}>
          {score.name} {score.value.toFixed(2)} <small>{score.source}</small>
        </li>
      ))}
    </ul>
    <ol className="learning-spans">
      {trace.spans.map((span) => (
        <li key={span.span_id} className={`learning-span ${span.kind} ${span.status}`}>
          <GitCommitVertical size={13} aria-hidden="true" />
          <details>
            <summary>{describeSpan(span)}</summary>
            {span.input !== null && <pre>{typeof span.input === 'string' ? span.input : JSON.stringify(span.input, null, 2)}</pre>}
            {span.output !== null && <pre>{String(span.output)}</pre>}
          </details>
        </li>
      ))}
    </ol>
    <div className="learning-actions">
      <span>这一轮的结果：</span>
      <button type="button" onClick={() => onFeedback(1)} aria-label="结果正确"><ThumbsUp size={14} /> 正确</button>
      <button type="button" onClick={() => onFeedback(0)} aria-label="结果有问题"><ThumbsDown size={14} /> 有问题</button>
    </div>
  </section>
);

export const TracesTab: React.FC<{ projectId?: string | null }> = ({ projectId }) => {
  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [summary, setSummary] = useState<TaskTypeSuccess[]>([]);
  const [selected, setSelected] = useState<TraceDetail | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [list, stats] = await Promise.all([fetchTraces({ projectId, days: 30 }), fetchTraceSummary(30)]);
      setTraces(list.traces);
      setSummary(stats.task_types);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '记录加载失败');
    } finally {
      setLoading(false);
    }
  }, [projectId]);
  // oxlint-disable-next-line react/set-state-in-effect -- The request must begin when the selected project changes.
  useEffect(() => { void load(); }, [load]);

  const open = async (traceId: string) => {
    try { setSelected((await fetchTrace(traceId)).trace); } catch (cause) { setError(cause instanceof Error ? cause.message : '记录加载失败'); }
  };
  const feedback = async (value: number) => {
    if (!selected) return;
    await sendTraceFeedback(selected.trace_id, value);
    await open(selected.trace_id);
  };

  return (
    <div className="metrics-page">
      <div className="metrics-header">
        <div className="metrics-heading"><span><GitCommitVertical size={16} /></span><strong>执行记录</strong></div>
        <button className="metrics-refresh" onClick={() => void load()} title="刷新" aria-label="刷新执行记录" disabled={loading}><RefreshCw size={14} /></button>
      </div>
      {error && <div className="metrics-empty metrics-error" role="alert">{error}</div>}
      <div className="metrics-summary">
        {summary.slice(0, 4).map((row) => (
          <div className="metrics-summary-card" key={row.task_type}>
            <span>{row.task_type}</span><strong>{formatRate(row.success_rate)}</strong><small>{row.scored}/{row.traces} 已评分</small>
          </div>
        ))}
      </div>
      {selected && <TraceTree trace={selected} onFeedback={(value) => void feedback(value)} />}
      <section className="metrics-card">
        <header className="metrics-card-title"><h3>最近 30 天</h3><span className="metrics-total">{traces.length} 条</span></header>
        {!traces.length ? <div className="metrics-empty-small">暂无执行记录</div> : (
          <ul className="learning-list">
            {traces.map((trace) => (
              <li key={trace.trace_id}>
                <button type="button" className={selected?.trace_id === trace.trace_id ? 'active' : ''} onClick={() => void open(trace.trace_id)}>
                  <span className={`learning-dot ${outcomeTone(trace.outcome)}`} aria-label={`得分 ${trace.outcome ?? '未评分'}`} />
                  <span className="learning-list-text" title={trace.input}>{trace.input || trace.task_type}</span>
                  <small>{new Date(trace.start_time * 1000).toLocaleString()}</small>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
};
