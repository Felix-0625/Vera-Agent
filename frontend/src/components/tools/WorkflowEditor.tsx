import { useWorkflowEditor } from './useWorkflowEditor';
import { WorkflowEditorView } from './WorkflowEditorView';
export function Editor(props: Parameters<typeof useWorkflowEditor>[0]) {
  const view = useWorkflowEditor(props);
  return <WorkflowEditorView {...view} />;
}
