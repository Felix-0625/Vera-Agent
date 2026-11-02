import { describe, expect, it } from 'vitest';
import { describeSpan, formatDelta, formatRate, outcomeTone, verdictLabel } from './learningFormat';
import { TraceSpan } from '../../types/learning';

const span = (overrides: Partial<TraceSpan>): TraceSpan => ({
  span_id: 's',
  parent_id: null,
  kind: 'tool',
  name: 'bash',
  start_time: 10,
  end_time: 10.25,
  status: 'ok',
  input: null,
  output: null,
  metadata: {},
  ...overrides,
});

describe('learningFormat', () => {
  it('formats rates and missing values', () => {
    expect(formatRate(0.734)).toBe('73%');
    expect(formatRate(null)).toBe('—');
  });

  it('formats signed deltas with their interval', () => {
    expect(formatDelta({ mean_delta: 0.333, ci_low: -0.1, ci_high: 0.55 })).toBe('+0.33（95% 区间 -0.10 ~ +0.55）');
  });

  it('treats 0.5 as the success boundary', () => {
    expect(outcomeTone(0.5)).toBe('good');
    expect(outcomeTone(0.49)).toBe('bad');
    expect(outcomeTone(undefined)).toBe('unknown');
  });

  it('labels verdicts in Chinese', () => {
    expect(verdictLabel('better')).toBe('显著更好');
  });

  it('describes tool spans with approval, exit code, and duration', () => {
    expect(describeSpan(span({ metadata: { approval: 'rejected', returncode: 1 } }))).toBe(
      'bash · 已拒绝 · 退出码 1 · 250 ms',
    );
  });

  it('describes model spans with tokens', () => {
    const model = span({
      kind: 'model',
      name: 'deepseek',
      metadata: { step: 2, prompt_tokens: 1200, completion_tokens: 34 },
    });
    expect(describeSpan(model)).toBe('模型 · 第 2 步 · 1,234 Token · 250 ms');
  });
});
