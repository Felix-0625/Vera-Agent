import {
  Background,
  BackgroundVariant,
  Handle,
  Position,
  ReactFlow,
  useNodesInitialized,
  useNodesState,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { GitBranch, Maximize2, ZoomIn, ZoomOut } from 'lucide-react';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BranchInfo, GitCommitInfo, GitFlowTopology } from '../../types/tool';
import { IconButton } from '../common/IconButton';
import './gitflow.css';
import { BranchNodeData, FlowNode, branchColor, buildGraph } from './gitFlowGraph';
const BranchNode: React.FC<{ data: BranchNodeData; selected?: boolean }> = ({ data, selected }) => {
  const branch = data.branch;
  const color = branchColor(branch.name);
  return (
    <div
      className={`gitflow-branch-node${selected ? ' is-selected' : ''}`}
      style={{ '--branch-color': color } as React.CSSProperties}
    >
      <Handle id="top" type="target" position={Position.Top} className="gitflow-handle" />
      <button
        className="gitflow-branch-card"
        title={`${branch.name} · 单击查看提交，双击查看操作`}
        onClick={(event) => {
          event.stopPropagation();
          data.onSelect(branch);
        }}
        onDoubleClick={(event) => {
          event.stopPropagation();
          data.onOpen(branch);
        }}
      >
        <GitBranch size={14} />
        <span>{branch.name}</span>
        {branch.is_current && <i>当前</i>}
      </button>
      <Handle id="bottom" type="source" position={Position.Bottom} className="gitflow-handle" />
    </div>
  );
};
const nodeTypes = { branch: BranchNode };
export const GraphCanvas: React.FC<{
  topology: GitFlowTopology;
  layoutScope: string;
  selectedBranch: BranchInfo | null;
  onSelectBranch: (branch: BranchInfo) => void;
  onOpenBranch: (branch: BranchInfo) => void;
}> = ({ topology, layoutScope, selectedBranch, onSelectBranch, onOpenBranch }) => {
  const flow = useReactFlow<FlowNode>();
  const [zoom, setZoom] = useState(1);
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>([]);
  const nodesInitialized = useNodesInitialized();
  const layoutKey = `veraagent:gitflow-layout:v3:${layoutScope}`;
  const graph = useMemo(() => {
    let saved: Record<string, { x: number; y: number }> = {};
    try {
      saved = JSON.parse(localStorage.getItem(layoutKey) || '{}');
    } catch {
      /* Ignore invalid saved layout. */
    }
    return buildGraph(topology, onSelectBranch, onOpenBranch, saved);
  }, [topology, onSelectBranch, onOpenBranch, layoutKey]);
  useEffect(() => {
    setNodes((current) =>
      graph.nodes.map((node) => {
        const existing = current.find((item) => item.id === node.id);
        return { ...node, position: existing?.position || node.position, selected: node.id === selectedBranch?.name };
      }),
    );
  }, [graph, selectedBranch, setNodes]);
  useEffect(() => {
    if (!nodesInitialized) return;
    const frame = requestAnimationFrame(() => flow.fitView({ duration: 180, padding: 0.18, maxZoom: 1 }));
    return () => cancelAnimationFrame(frame);
  }, [flow, nodesInitialized, layoutScope, topology.branches.length]);
  const savePositions = useCallback(() => {
    const positions = Object.fromEntries(flow.getNodes().map((node) => [node.id, node.position]));
    localStorage.setItem(layoutKey, JSON.stringify(positions));
  }, [flow, layoutKey]);
  const selectNode = useCallback(
    (_: React.MouseEvent, node: FlowNode) => onSelectBranch(node.data.branch),
    [onSelectBranch],
  );
  const openNode = useCallback((_: React.MouseEvent, node: FlowNode) => onOpenBranch(node.data.branch), [onOpenBranch]);
  return (
    <div className="gitflow-canvas-wrap">
      <ReactFlow
        className="gitflow-canvas"
        nodes={nodes}
        edges={graph.edges}
        onNodesChange={onNodesChange}
        nodeTypes={nodeTypes}
        defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
        onMove={(_, viewport) => setZoom(viewport.zoom)}
        onNodeDragStop={savePositions}
        onNodeClick={selectNode}
        onNodeDoubleClick={openNode}
        minZoom={0.35}
        maxZoom={1.8}
        panOnScroll
        zoomOnScroll={false}
        zoomOnPinch
        zoomOnDoubleClick={false}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="var(--text-primary)" />
      </ReactFlow>
      <div className="gitflow-zoom-controls">
        <IconButton label="缩小" size="sm" onClick={() => flow.zoomOut({ duration: 180 })}>
          <ZoomOut size={14} />
        </IconButton>
        <span>{Math.round(zoom * 100)}%</span>
        <IconButton label="放大" size="sm" onClick={() => flow.zoomIn({ duration: 180 })}>
          <ZoomIn size={14} />
        </IconButton>
        <IconButton label="适应视图" size="sm" onClick={() => flow.fitView({ duration: 250, padding: 0.12 })}>
          <Maximize2 size={13} />
        </IconButton>
      </div>
    </div>
  );
};
export const CommitEntry: React.FC<{ commit: GitCommitInfo; compact?: boolean }> = ({ commit, compact }) => {
  const mergeCommit = commit.parents.length > 1;
  const parentLabel = commit.parents.map((parent) => parent.slice(0, 8)).join(' · ');
  return (
    <div className={`gitflow-commit-row${mergeCommit ? ' is-merge' : ''}`} key={commit.hash}>
      <code>{commit.short_hash}</code>
      <div className="gitflow-commit-content">
        <span title={commit.subject}>{commit.subject || '（无提交说明）'}</span>
        {mergeCommit && <small>合并提交 · 父提交 {parentLabel}</small>}
      </div>
      {mergeCommit && <i className="gitflow-merge-badge">合并</i>}
      <time>
        {new Date(commit.timestamp * 1000).toLocaleString(undefined, compact ? { dateStyle: 'short' } : undefined)}
      </time>
    </div>
  );
};
