/**
 * Display helpers shared by the trace, memory, and evolution panels.
 */
import { GateStage, MemoryKind, ProposalStatus, TraceSpan } from '../../types/learning';

export const MEMORY_KIND_LABELS: Record<MemoryKind, string> = {
  profile: '用户背景',
  preference: '偏好',
  habit: '习惯',
  feedback: '反馈',
  fact: '项目事实',
  episode: '任务经验',
  rule: '规则',
};

export const PROPOSAL_STATUS_LABELS: Record<ProposalStatus, string> = {
  draft: '待评测',
  gated: '已评测',
  recommended: '推荐采纳',
  not_recommended: '不推荐',
  adopted: '已采纳',
  rejected: '已拒绝',
  rolled_back: '已回滚',
};

const VERDICT_LABELS: Record<GateStage['verdict'], string> = {
  better: '显著更好',
  no_difference: '无显著差异',
  worse: '退化',
};

/** `0.734` -> `73%`; null or undefined -> `—`. */
export function formatRate(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : `${Math.round(value * 100)}%`;
}

/** Signed pass-rate delta followed by its 95% interval, e.g. `+0.33` with `+0.10 ~ +0.55`. */
export function formatDelta(stage: Pick<GateStage, 'mean_delta' | 'ci_low' | 'ci_high'>): string {
  const signed = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}`;
  return `${signed(stage.mean_delta)}（95% 区间 ${signed(stage.ci_low)} ~ ${signed(stage.ci_high)}）`;
}

export function verdictLabel(verdict: GateStage['verdict']): string {
  return VERDICT_LABELS[verdict] || verdict;
}

/** Outcome score bucket used for coloring: >= 0.5 is a success in every view. */
export function outcomeTone(value: number | null | undefined): 'good' | 'bad' | 'unknown' {
  if (value === null || value === undefined) return 'unknown';
  return value >= 0.5 ? 'good' : 'bad';
}

/** One-line description of a span for the trace tree. */
export function describeSpan(span: TraceSpan): string {
  const meta = span.metadata || {};
  const duration = span.end_time ? `${((span.end_time - span.start_time) * 1000).toFixed(0)} ms` : '进行中';
  if (span.kind === 'model') {
    const tokens = Number(meta.prompt_tokens || 0) + Number(meta.completion_tokens || 0);
    return `模型 · 第 ${meta.step ?? '?'} 步 · ${tokens ? `${tokens.toLocaleString()} Token · ` : ''}${duration}`;
  }
  const approval = meta.approval
    ? ({ approved: '已批准', rejected: '已拒绝', corrected: '已修正' } as Record<string, string>)[String(meta.approval)]
    : '';
  const code = meta.returncode !== undefined && meta.returncode !== null ? `退出码 ${meta.returncode}` : '';
  return [span.kind === 'subagent' ? `子智能体 ${span.name}` : span.name, approval, code, duration]
    .filter(Boolean)
    .join(' · ');
}
