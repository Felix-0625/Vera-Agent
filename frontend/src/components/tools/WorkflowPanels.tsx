import '@xyflow/react/dist/style.css';
import { Workflow } from 'lucide-react';
import { EmptyState } from '../common/EmptyState';
import './workflow.css';
import { type RunLogEntry } from './workflowRunner';
import { styles } from './workflowShared';

export function RunLogCard({ item }: { item: RunLogEntry }) {
  return (
    <section style={{ ...styles.card, padding: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
      <strong>{item.title}</strong>
      <span
        style={{
          marginLeft: 'var(--space-2-5)',
          color: item.status === '失败' ? 'var(--accent-rose)' : 'var(--text-muted)',
          fontSize: 'var(--font-size-compact)',
        }}
      >
        {item.status}
      </span>
      {item.inputs?.length ? (
        <details style={{ marginTop: 'var(--space-2)', fontSize: 'var(--font-size-compact)' }}>
          <summary>查看传入的 {item.inputs.length} 份上游结果</summary>
          {item.inputs.map((input, index) => (
            <div
              key={`${input.node_id}-${index}`}
              style={{
                marginTop: 'var(--space-2)',
                padding: 'var(--space-2)',
                borderLeft: '2px solid var(--border-active)',
              }}
            >
              <strong>{input.title}</strong>
              {input.label && <span> · {input.label}</span>}
              <pre
                style={{
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'inherit',
                  fontSize: 'var(--font-size-sm)',
                  lineHeight: 1.5,
                }}
              >
                {input.output}
              </pre>
            </div>
          ))}
        </details>
      ) : null}
      {item.error && (
        <div role="alert" style={{ marginTop: 'var(--space-2)', color: 'var(--accent-rose)' }}>
          {item.error}
        </div>
      )}
      <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 'var(--font-size-sm)', lineHeight: 1.5 }}>
        {item.output ||
          (item.status === '运行中' || item.status === '判断中' || item.status === '复核中' ? '正在接收模型流…' : '')}
      </pre>
    </section>
  );
}

export function Empty({ message }: { message: string }) {
  return <EmptyState icon={<Workflow size={25} />} description={message} className="workflow-empty-state" />;
}

export function ErrorText({ text }: { text: string }) {
  return (
    <div
      role="alert"
      style={{
        margin: 'var(--space-2) var(--space-3)',
        padding: 'var(--space-2-25)',
        color: 'var(--accent-rose)',
        background: 'var(--bg-danger-soft)',
        border: '1px solid var(--border-danger-soft)',
        borderRadius: 'var(--radius-sm-plus)',
        fontSize: 'var(--font-size-compact)',
      }}
    >
      {text}
    </div>
  );
}
