import React, { Suspense } from 'react';
import { useLayoutStore } from '../../stores/layoutStore';
import { Modal } from '../common/Modal';

const WorkflowTab = React.lazy(() =>
  import('../tools/WorkflowTab').then((module) => ({ default: module.WorkflowTab })),
);

export const WorkflowTemplatesModal: React.FC = () => {
  const { workflowTemplatesOpen, setWorkflowTemplatesOpen } = useLayoutStore();

  return (
    <Modal
      isOpen={workflowTemplatesOpen}
      onClose={() => setWorkflowTemplatesOpen(false)}
      title="流程架构模板"
      width="96vw"
      contentStyle={{ padding: 0, overflow: 'hidden', minHeight: 0 }}
    >
      <div style={{ height: 'min(86vh, 920px)', minHeight: 560, overflow: 'auto' }}>
        <Suspense
          fallback={<div style={{ padding: 'var(--space-4)', color: 'var(--text-muted)' }}>正在加载流程模板…</div>}
        >
          <WorkflowTab projectId="" />
        </Suspense>
      </div>
    </Modal>
  );
};
