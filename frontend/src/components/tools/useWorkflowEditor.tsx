import '@xyflow/react/dist/style.css';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import type { WorkflowEdgeDefinition, WorkflowNodeDefinition } from '../../types/project';
import { arrangeNodes } from './CanvasParts';
import './workflow.css';
import { agent, id } from './workflowShared';

export function useWorkflowEditor({
  infoPanelRequest,
  globalMode,
  createActionLabel,
  kind,
  setKind,
  name,
  setName,
  description,
  setDescription,
  projectGoal,
  setProjectGoal,
  projectBackground,
  setProjectBackground,
  nodes,
  setNodes,
  edges,
  setEdges,
  error,
  busy,
  onSave,
  onCancel,
}: {
  infoPanelRequest: number;
  globalMode: boolean;
  createActionLabel?: string;
  kind: 'workflow' | 'architecture';
  setKind: (kind: 'workflow' | 'architecture') => void;
  name: string;
  setName: (value: string) => void;
  description: string;
  setDescription: (value: string) => void;
  projectGoal: string;
  setProjectGoal: (value: string) => void;
  projectBackground: string;
  setProjectBackground: (value: string) => void;
  nodes: WorkflowNodeDefinition[];
  setNodes: React.Dispatch<React.SetStateAction<WorkflowNodeDefinition[]>>;
  edges: WorkflowEdgeDefinition[];
  setEdges: React.Dispatch<React.SetStateAction<WorkflowEdgeDefinition[]>>;
  error: string;
  busy: boolean;
  onSave: () => void;
  onCancel: () => void;
}) {
  const [infoClosedAtRequest, setInfoClosedAtRequest] = useState<number | null>(null);
  const infoOpen = infoClosedAtRequest !== infoPanelRequest;
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [projectContextOpen, setProjectContextOpen] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState('');
  const [selectedEdgeId, setSelectedEdgeId] = useState('');
  const [canvasError, setCanvasError] = useState('');
  const [panMode, setPanMode] = useState(false);
  const [addRequest, setAddRequest] = useState<{ id: number; type: 'agent' | 'condition' | 'loop' } | null>(null);
  const addRequestId = useRef(0);
  const drafts = useRef<
    Record<
      'workflow' | 'architecture',
      { name: string; description: string; nodes: WorkflowNodeDefinition[]; edges: WorkflowEdgeDefinition[] }
    >
  >({
    workflow: { name, description, nodes: kind === 'workflow' ? nodes : [], edges: kind === 'workflow' ? edges : [] },
    architecture: {
      name,
      description,
      nodes: kind === 'architecture' ? nodes : [],
      edges: kind === 'architecture' ? edges : [],
    },
  });
  const [initialSnapshot] = useState(() =>
    JSON.stringify({ kind, name, description, projectGoal, projectBackground, nodes, edges }),
  );
  const isDirty =
    JSON.stringify({ kind, name, description, projectGoal, projectBackground, nodes, edges }) !== initialSnapshot;
  useEffect(() => {
    if (!isDirty) return;
    const warnBeforeClose = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warnBeforeClose);
    return () => window.removeEventListener('beforeunload', warnBeforeClose);
  }, [isDirty]);
  const requestCancel = () => {
    if (isDirty && !window.confirm('当前编排有未保存的修改。确定放弃并退出吗？')) return;
    onCancel();
  };
  const selectedNode = nodes.find((node) => node.id === selectedNodeId);
  const architecture = kind === 'architecture';
  const historyRef = useRef<Array<{ nodes: WorkflowNodeDefinition[]; edges: WorkflowEdgeDefinition[] }>>([
    { nodes, edges },
  ]);
  const cursorRef = useRef(0);
  const [historyStatus, setHistoryStatus] = useState({ cursor: 0, length: 1 });
  const refreshHistoryStatus = () => setHistoryStatus({ cursor: cursorRef.current, length: historyRef.current.length });
  const commitGraph = (nextNodes: WorkflowNodeDefinition[], nextEdges: WorkflowEdgeDefinition[]) => {
    setNodes(nextNodes);
    setEdges(nextEdges);
    historyRef.current = [
      ...historyRef.current.slice(0, cursorRef.current + 1),
      { nodes: nextNodes, edges: nextEdges },
    ].slice(-50);
    cursorRef.current = historyRef.current.length - 1;
    refreshHistoryStatus();
  };
  const moveHistory = useCallback(
    (direction: -1 | 1) => {
      const next = Math.max(0, Math.min(historyRef.current.length - 1, cursorRef.current + direction));
      if (next === cursorRef.current) return;
      cursorRef.current = next;
      const snapshot = historyRef.current[next];
      setNodes(snapshot.nodes);
      setEdges(snapshot.edges);
      setSelectedEdgeId('');
      refreshHistoryStatus();
    },
    [setEdges, setNodes],
  );
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== 'z') return;
      const target = event.target as HTMLElement | null;
      if (target?.matches('input,textarea,[contenteditable="true"]')) return;
      event.preventDefault();
      moveHistory(event.shiftKey ? 1 : -1);
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [moveHistory]);
  const patch = (nodeId: string, changes: Partial<WorkflowNodeDefinition>) =>
    commitGraph(
      nodes.map((node) => (node.id === nodeId ? { ...node, ...changes } : node)),
      edges,
    );
  const addNode = (
    type: 'agent' | 'condition' | 'loop' = 'agent',
    placement: 'root' | 'child' | 'peer' = 'root',
    anchorId?: string,
    position?: { x: number; y: number },
  ) => {
    const anchor = nodes.find((node) => node.id === (anchorId || selectedNodeId) && node.type === 'agent');
    const count = nodes.filter((node) => node.type === 'agent').length;
    const parentEdge = anchor ? edges.find((edge) => edge.target === anchor.id) : undefined;
    const parentId = architecture
      ? placement === 'child'
        ? anchor?.id
        : placement === 'peer'
          ? parentEdge?.source
          : undefined
      : undefined;
    const nextPosition = position || { x: 140 + (nodes.length % 4) * 230, y: 140 + Math.floor(nodes.length / 4) * 170 };
    const next: WorkflowNodeDefinition =
      type === 'agent'
        ? {
            ...agent(count + 1, nextPosition.x, nextPosition.y),
            prompt_template: '',
            background: '',
            responsibilities: [],
            constraints: [],
            output_spec: '',
          }
        : {
            id: id(type),
            type,
            title: type === 'condition' ? '分支判断' : '循环',
            prompt_template: '',
            config:
              type === 'condition'
                ? { expression: '上游结果已通过验收' }
                : { max_iterations: 3, continue_condition: '上游结果仍未达到预期，需要继续修改' },
            position: nextPosition,
          };
    const nextEdges = parentId
      ? [...edges, { id: id('edge'), source: parentId, target: next.id, relation: '组织汇报', label: '汇报关系' }]
      : edges;
    commitGraph(arrangeNodes([...nodes, next], nextEdges, kind), nextEdges);
    setCanvasError('');
    setSelectedNodeId(next.id);
    setSelectedEdgeId('');
    setPaletteOpen(false);
  };
  const nodeAction = (nodeId: string, action: 'child' | 'peer') => {
    setSelectedNodeId(nodeId);
    addNode('agent', action, nodeId);
  };
  const handleEditorTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const next = e.target.value as 'workflow' | 'architecture';
    if (next === kind) return;
    drafts.current[kind] = { name, description, nodes, edges };
    const draft = drafts.current[next];
    setKind(next);
    setName(draft.name);
    setDescription(draft.description);
    setNodes(draft.nodes);
    setEdges(draft.edges);
    historyRef.current = [{ nodes: draft.nodes, edges: draft.edges }];
    cursorRef.current = 0;
    refreshHistoryStatus();
    setSelectedNodeId('');
    setSelectedEdgeId('');
    setAddRequest(null);
  };
  const handleEditorAddNode1 = () => {
    addRequestId.current += 1;
    setAddRequest({ id: addRequestId.current, type: 'agent' });
    setPaletteOpen(false);
  };
  const handleEditorAddNode2 = () => {
    addRequestId.current += 1;
    setAddRequest({ id: addRequestId.current, type: 'condition' });
    setPaletteOpen(false);
  };
  const handleEditorAddNode3 = () => {
    addRequestId.current += 1;
    setAddRequest({ id: addRequestId.current, type: 'loop' });
    setPaletteOpen(false);
  };
  return {
    handleEditorTypeChange,
    handleEditorAddNode1,
    handleEditorAddNode2,
    handleEditorAddNode3,
    infoPanelRequest,
    globalMode,
    createActionLabel,
    kind,
    setKind,
    name,
    setName,
    description,
    setDescription,
    projectGoal,
    setProjectGoal,
    projectBackground,
    setProjectBackground,
    nodes,
    setNodes,
    edges,
    setEdges,
    error,
    busy,
    onSave,
    setInfoClosedAtRequest,
    infoOpen,
    paletteOpen,
    setPaletteOpen,
    projectContextOpen,
    setProjectContextOpen,
    selectedNodeId,
    setSelectedNodeId,
    selectedEdgeId,
    setSelectedEdgeId,
    canvasError,
    setCanvasError,
    panMode,
    setPanMode,
    addRequest,
    setAddRequest,
    addRequestId,
    drafts,
    requestCancel,
    selectedNode,
    architecture,
    historyRef,
    cursorRef,
    historyStatus,
    refreshHistoryStatus,
    commitGraph,
    moveHistory,
    patch,
    addNode,
    nodeAction,
  };
}
