import '@xyflow/react/dist/style.css';
import React from 'react';
import type { WorkflowEdgeDefinition, WorkflowNodeDefinition } from '../../types/project';
import './workflow.css';

export const styles: Record<string, React.CSSProperties> = {
  card: {
    background: 'var(--bg-surface-elevated)',
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-lg)',
  },
  button: {
    border: '1px solid var(--border-subtle)',
    borderRadius: 'var(--radius-md)',
    background: 'var(--bg-surface-elevated)',
    color: 'var(--text-primary)',
    padding: 'var(--space-1-75) var(--space-2-5)',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 'var(--space-1-5)',
    cursor: 'pointer',
    fontSize: 'var(--font-size-sm)',
  },
};

export const id = (prefix: string) => `${prefix}_${crypto.randomUUID().slice(0, 8)}`;

export const edgeLabelStyle: React.CSSProperties = {
  fill: 'var(--text-muted)',
  fontSize: 'var(--font-size-xs)',
  fontWeight: 500,
};

export function canvasSourceHandle(
  edge: WorkflowEdgeDefinition,
  nodes: WorkflowNodeDefinition[],
  architecture: boolean,
): string | undefined {
  if (architecture) return 'bottom';
  const handle = edge.config?.sourceHandle;
  if (handle === 'exit' && nodes.some((node) => node.id === edge.source && node.type === 'loop')) return 'exit_bottom';
  return typeof handle === 'string' ? handle : undefined;
}

export function canvasTargetHandle(
  edge: WorkflowEdgeDefinition,
  nodes: WorkflowNodeDefinition[],
  architecture: boolean,
): string | undefined {
  if (architecture) return 'top';
  const handle = edge.config?.targetHandle;
  if (typeof handle === 'string') return handle;
  return nodes.some((node) => node.id === edge.target && node.type === 'loop') ? 'input' : undefined;
}

export const agent = (n: number, x = 120, y = 120): WorkflowNodeDefinition => ({
  id: id('agent'),
  type: 'agent',
  title: `对话窗口 ${n}`,
  role: 'Agent',
  responsibilities: [],
  prompt_template: '你的任务：\n{{input}}\n\n上游信息：\n{{upstream}}',
  position: { x, y },
});

export const globalNode = (node: WorkflowNodeDefinition, i: number): WorkflowNodeDefinition => ({
  ...node,
  id: node.id || `agent_${i + 1}`,
  thread_id: undefined,
  position: node.position || { x: 130 + i * 230, y: 120 },
});
