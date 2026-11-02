import React from 'react';
import { ProjectRowProps } from './ProjectRowParts';
import { ProjectRowView } from './ProjectRowView';
import { useProjectRow } from './useProjectRow';
export const ProjectRow: React.FC<ProjectRowProps> = (props) => {
  const view = useProjectRow(props);
  return <ProjectRowView {...view} />;
};
