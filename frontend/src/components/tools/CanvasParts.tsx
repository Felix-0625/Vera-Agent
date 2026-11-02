import '@xyflow/react/dist/style.css';
import type { WorkflowEdgeDefinition, WorkflowNodeDefinition } from '../../types/project';
import './workflow.css';
import { ArchitectureAgentNode, ConditionNode, LoopNode, WorkflowAgentNode } from './WorkflowNodes';
export const workflowNodeTypes = {
  workflowAgent: WorkflowAgentNode,
  architectureAgent: ArchitectureAgentNode,
  conditionNode: ConditionNode,
  loopNode: LoopNode,
};
export function arrangeNodes(
  nodes: WorkflowNodeDefinition[],
  edges: WorkflowEdgeDefinition[],
  kind: 'workflow' | 'architecture',
) {
  const agents = nodes.filter((node) => node.type === 'agent');
  const agentIds = new Set(agents.map((node) => node.id));
  const links = new Map<string, string[]>();
  edges
    .filter((edge) => agentIds.has(edge.source) && agentIds.has(edge.target))
    .forEach((edge) => links.set(edge.source, [...(links.get(edge.source) || []), edge.target]));
  const positions = new Map<string, { x: number; y: number }>();
  if (kind === 'workflow') {
    agents.forEach((node, index) => positions.set(node.id, node.position || { x: 100 + index * 250, y: 140 }));
  } else {
    let leafColumn = 0;
    const visited = new Set<string>();
    const place = (nodeId: string, level: number): number => {
      if (visited.has(nodeId)) return leafColumn++;
      visited.add(nodeId);
      const children = (links.get(nodeId) || []).filter((child) => !visited.has(child));
      let center: number;
      if (children.length === 0) center = leafColumn++;
      else {
        const childColumns = children.map((child) => place(child, level + 1));
        center = (Math.min(...childColumns) + Math.max(...childColumns)) / 2;
      }
      positions.set(nodeId, { x: 100 + center * 260, y: 85 + level * 190 });
      return center;
    };
    const roots = agents.filter((node) => !edges.some((edge) => edge.target === node.id && agentIds.has(edge.source)));
    roots.forEach((root) => place(root.id, 0));
    agents.forEach((node) => {
      if (!visited.has(node.id)) place(node.id, 0);
    });
  }
  return nodes.map((node) =>
    node.type === 'agent' ? { ...node, position: positions.get(node.id) || node.position } : node,
  );
}
