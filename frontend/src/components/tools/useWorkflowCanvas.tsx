import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  MarkerType,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { WorkflowEdgeDefinition, WorkflowNodeDefinition } from '../../types/project';
import './workflow.css';
import { canvasSourceHandle, canvasTargetHandle, edgeLabelStyle } from './workflowShared';
export function useWorkflowCanvas({
  kind,
  nodes,
  edges,
  onChange,
  readOnly = false,
  selectedNodeId,
  selectedEdgeId,
  onSelectNode,
  onSelectEdge,
  onNodeAction,
  onError,
  panMode = false,
  onTogglePan = () => {},
  onTogglePointer = () => {},
  addRequest,
  onAddRequestDone,
  onAddAtPosition,
}: {
  kind: 'workflow' | 'architecture';
  nodes: WorkflowNodeDefinition[];
  edges: WorkflowEdgeDefinition[];
  onChange: (nodes: WorkflowNodeDefinition[], edges: WorkflowEdgeDefinition[]) => void;
  readOnly?: boolean;
  selectedNodeId?: string;
  selectedEdgeId?: string;
  onSelectNode?: (id: string) => void;
  onSelectEdge?: (id: string) => void;
  onNodeAction?: (id: string, action: 'child' | 'peer') => void;
  onError?: (message: string) => void;
  panMode?: boolean;
  onTogglePan?: () => void;
  onTogglePointer?: () => void;
  addRequest?: { id: number; type: 'agent' | 'condition' | 'loop' } | null;
  onAddRequestDone?: () => void;
  onAddAtPosition?: (type: 'agent' | 'condition' | 'loop', position: { x: number; y: number }) => void;
}) {
  const lastPointerRef = useRef<{ x: number; y: number } | null>(null);
  const architecture = kind === 'architecture';
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(() => new Set());
  const hiddenIds = useMemo(() => {
    const hidden = new Set<string>();
    const visit = (parent: string) =>
      edges
        .filter((edge) => edge.source === parent)
        .forEach((edge) => {
          if (hidden.has(edge.target)) return;
          hidden.add(edge.target);
          if (collapsedIds.has(edge.target)) return;
          visit(edge.target);
        });
    collapsedIds.forEach((parent) =>
      edges
        .filter((edge) => edge.source === parent)
        .forEach((edge) => {
          if (!hidden.has(edge.target)) {
            hidden.add(edge.target);
            visit(edge.target);
          }
        }),
    );
    return hidden;
  }, [edges, collapsedIds]);
  const initialNodes = useMemo(
    () =>
      nodes.map(
        (item) =>
          ({
            id: item.id,
            position: item.position || { x: 120, y: 100 },
            data: {
              node: item,
              hasChildren: edges.some((edge) => edge.source === item.id),
              collapsed: collapsedIds.has(item.id),
              onToggle: () =>
                setCollapsedIds((old) => {
                  const next = new Set(old);
                  if (next.has(item.id)) next.delete(item.id);
                  else next.add(item.id);
                  return next;
                }),
            },
            type: architecture
              ? 'architectureAgent'
              : item.type === 'condition'
                ? 'conditionNode'
                : item.type === 'loop'
                  ? 'loopNode'
                  : 'workflowAgent',
            hidden: architecture && hiddenIds.has(item.id),
            selected: item.id === selectedNodeId,
          }) as Node,
      ),
    [nodes, edges, architecture, collapsedIds, hiddenIds, selectedNodeId],
  );
  const [flowNodes, setFlowNodes] = useNodesState(initialNodes);
  const [flowEdges, setFlowEdges] = useEdgesState(
    edges.map(
      (item, index) =>
        ({
          id: item.id || 'edge_' + index,
          source: item.source,
          target: item.target,
          label: item.label || item.relation,
          labelStyle: edgeLabelStyle,
          labelShowBg: false,
          sourceHandle: canvasSourceHandle(item, nodes, architecture),
          targetHandle: canvasTargetHandle(item, nodes, architecture),
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: architecture ? 'var(--accent-emerald)' : 'var(--accent-primary)',
          },
          style: { stroke: architecture ? 'var(--accent-emerald)' : 'var(--accent-primary)', strokeWidth: 1.7 },
          type: architecture ? 'step' : 'default',
          zIndex: 0,
          animated: false,
        }) as Edge,
    ),
  );
  useEffect(() => {
    setFlowNodes((current) => {
      const currentById = new Map(current.map((node) => [node.id, node]));
      return nodes.map((def) => {
        const existing = currentById.get(def.id);
        return {
          id: def.id,
          position: def.position || existing?.position || { x: 120, y: 100 },
          data: {
            node: def,
            hasChildren: edges.some((edge) => edge.source === def.id),
            hasParent: edges.some((edge) => edge.target === def.id),
            collapsed: collapsedIds.has(def.id),
            onToggle: () =>
              setCollapsedIds((old) => {
                const next = new Set(old);
                if (next.has(def.id)) next.delete(def.id);
                else next.add(def.id);
                return next;
              }),
            onAction: (action: 'child' | 'peer') => {
              setFlowNodes((currentNodes) => currentNodes.map((item) => ({ ...item, selected: false })));
              onNodeAction?.(def.id, action);
            },
          },
          type: architecture
            ? 'architectureAgent'
            : def.type === 'condition'
              ? 'conditionNode'
              : def.type === 'loop'
                ? 'loopNode'
                : 'workflowAgent',
          hidden: architecture && hiddenIds.has(def.id),
          selected: existing?.selected ?? def.id === selectedNodeId,
        } as Node;
      });
    });
  }, [nodes, edges, architecture, selectedNodeId, hiddenIds, collapsedIds, onNodeAction, setFlowNodes]);
  useEffect(() => {
    setFlowEdges(
      edges.map(
        (edge, index) =>
          ({
            id: edge.id || 'edge_' + index,
            source: edge.source,
            target: edge.target,
            label: edge.label || edge.relation,
            labelStyle: edgeLabelStyle,
            labelShowBg: false,
            sourceHandle: canvasSourceHandle(edge, nodes, architecture),
            targetHandle: canvasTargetHandle(edge, nodes, architecture),
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: architecture ? 'var(--accent-emerald)' : 'var(--accent-primary)',
            },
            style: { stroke: architecture ? 'var(--accent-emerald)' : 'var(--accent-primary)', strokeWidth: 1.7 },
            type: architecture ? 'step' : 'default',
            zIndex: 0,
            animated: false,
            selected: (edge.id || 'edge_' + index) === selectedEdgeId,
          }) as Edge,
      ),
    );
  }, [edges, nodes, architecture, selectedEdgeId, setFlowEdges]);
  const serializeNodes = useCallback(
    (updated: Node[]) =>
      nodes
        .filter((def) => updated.some((node) => node.id === def.id))
        .map((def) => ({ ...def, position: updated.find((node) => node.id === def.id)?.position || def.position })),
    [nodes],
  );
  const serializeEdges = useCallback(
    (updated: Edge[]) =>
      updated.map((edge) => ({
        id: edge.id,
        source: edge.source || '',
        target: edge.target || '',
        label: String(edge.label || ''),
        relation: String(edge.label || (architecture ? '组织汇报' : '信息传递')),
        config:
          edge.sourceHandle || edge.targetHandle
            ? { sourceHandle: edge.sourceHandle, targetHandle: edge.targetHandle }
            : undefined,
      })),
    [architecture],
  );
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const updated = applyNodeChanges(changes, flowNodes) as Node[];
      setFlowNodes(updated);
      if (
        changes.some((change) => change.type === 'remove' || (change.type === 'position' && change.dragging !== true))
      ) {
        const survivingIds = new Set(updated.map((node) => node.id));
        const survivingEdges = flowEdges.filter(
          (edge) => survivingIds.has(edge.source) && survivingIds.has(edge.target),
        );
        onChange(serializeNodes(updated), serializeEdges(survivingEdges));
      }
    },
    [flowNodes, flowEdges, setFlowNodes, onChange, serializeNodes, serializeEdges],
  );
  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      const updated = applyEdgeChanges(changes, flowEdges) as Edge[];
      setFlowEdges(updated);
      if (changes.some((change) => change.type === 'remove')) {
        onSelectEdge?.('');
        onChange(serializeNodes(flowNodes), serializeEdges(updated));
      }
    },
    [flowNodes, flowEdges, setFlowEdges, onChange, serializeNodes, serializeEdges, onSelectEdge],
  );
  const connect = useCallback(
    (connection: Connection) => {
      // Reporting lines in an organization are created only by the node's add-child / add-peer actions.
      if (architecture) return;
      if (!connection.source || !connection.target || connection.source === connection.target) return;
      const reachesTarget = (from: string, target: string, seen = new Set<string>()): boolean => {
        if (from === target) return true;
        if (seen.has(from)) return false;
        seen.add(from);
        return flowEdges
          .filter((edge) => edge.source === from)
          .some((edge) => reachesTarget(edge.target, target, seen));
      };
      if (architecture) {
        if (flowEdges.some((edge) => edge.target === connection.target)) {
          onError?.('每个职责窗口只能有一个直接上级。');
          return;
        }
        if (reachesTarget(connection.target, connection.source)) {
          onError?.('该连线会形成循环，请按层级关系连接。');
          return;
        }
      } else if (reachesTarget(connection.target, connection.source)) {
        const sourceNode = nodes.find((node) => node.id === connection.source);
        const maxIterations = Number(sourceNode?.config?.max_iterations || 0);
        if (
          sourceNode?.type !== 'loop' ||
          connection.sourceHandle !== 'repeat' ||
          !Number.isInteger(maxIterations) ||
          maxIterations < 1 ||
          maxIterations > 20
        ) {
          onError?.('回流必须从“循环”节点的循环出口连接，并设置 1–20 次上限；判断节点的“否”出口请先连接到循环节点。');
          return;
        }
      }
      onError?.('');
      const sourceNode = nodes.find((node) => node.id === connection.source);
      const routeLabel =
        sourceNode?.type === 'condition'
          ? connection.sourceHandle === 'false'
            ? '否'
            : '是'
          : sourceNode?.type === 'loop'
            ? connection.sourceHandle === 'repeat'
              ? '循环'
              : '退出'
            : architecture
              ? '汇报关系'
              : '传递上游结果';
      const updated = addEdge(
        {
          ...connection,
          label: routeLabel,
          labelStyle: edgeLabelStyle,
          labelShowBg: false,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: architecture ? 'var(--accent-emerald)' : 'var(--accent-primary)',
          },
          animated: false,
          type: architecture ? 'step' : 'default',
          zIndex: 0,
          style: { stroke: architecture ? 'var(--accent-emerald)' : 'var(--accent-primary)', strokeWidth: 1.7 },
        },
        flowEdges,
      );
      setFlowEdges(updated);
      onChange(serializeNodes(flowNodes), serializeEdges(updated));
    },
    [setFlowEdges, architecture, flowEdges, onError, flowNodes, nodes, onChange, serializeNodes, serializeEdges],
  );
  return {
    nodes,
    edges,
    onChange,
    readOnly,
    onSelectNode,
    onSelectEdge,
    panMode,
    onTogglePan,
    onTogglePointer,
    addRequest,
    onAddRequestDone,
    onAddAtPosition,
    lastPointerRef,
    architecture,
    flowNodes,
    setFlowNodes,
    flowEdges,
    handleNodesChange,
    handleEdgesChange,
    connect,
  };
}
