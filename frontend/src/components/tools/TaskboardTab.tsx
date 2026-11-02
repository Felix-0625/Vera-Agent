import React from 'react';
import './taskboard.css';
import { TaskboardTabProps } from './TaskboardTabParts';
import { TaskboardTabView } from './TaskboardTabView';
import { useTaskboardTab } from './useTaskboardTab';
export const TaskboardTab: React.FC<TaskboardTabProps> = (props) => {
  const view = useTaskboardTab(props);
  return <TaskboardTabView {...view} />;
};
