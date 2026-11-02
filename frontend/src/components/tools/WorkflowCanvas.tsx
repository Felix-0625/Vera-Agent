import { useWorkflowCanvas } from './useWorkflowCanvas';
import { WorkflowCanvasView } from './WorkflowCanvasView';
export function Canvas(props: Parameters<typeof useWorkflowCanvas>[0]) {
  const view = useWorkflowCanvas(props);
  return <WorkflowCanvasView {...view} />;
}
