import '@xyflow/react/dist/style.css';
import React from 'react';
import { useWorkflowTab } from './useWorkflowTab';
import './workflow.css';
import { WorkflowTabView } from './WorkflowTabView';
export const WorkflowTab: React.FC<{ projectId?: string | null; conversationKey?: string }> = ({
  projectId,
  conversationKey,
}) => {
  const view = useWorkflowTab({ projectId, conversationKey });
  return <WorkflowTabView {...view} />;
};
