import '@xyflow/react/dist/style.css';
import React from 'react';
import './gitflow.css';
import { GitFlowTabView } from './GitFlowTabView';
import { useGitFlowTab } from './useGitFlowTab';
export const GitFlowTab: React.FC<{ projectId?: string | null }> = (props) => {
  const view = useGitFlowTab(props);
  return <GitFlowTabView {...view} />;
};
