import { Background, BackgroundVariant, ReactFlow, ReactFlowProvider, SelectionMode } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { workflowNodeTypes } from './CanvasParts';
import { useWorkflowCanvas } from './useWorkflowCanvas';
import './workflow.css';
import { CanvasToolbar, FitView, PlaceNodeRequest } from './WorkflowNodes';
export function WorkflowCanvasView({
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
}: ReturnType<typeof useWorkflowCanvas>) {
  return (
    <div
      className={`${architecture ? 'workflow-canvas architecture-canvas' : 'workflow-canvas business-flow-canvas'}${panMode ? ' pan-mode' : ''}`}
      style={{
        height: '100%',
        minHeight: 300,
        background: architecture
          ? 'radial-gradient(ellipse at 50% 0%,color-mix(in srgb, var(--accent-emerald) 11%, transparent),transparent 60%)'
          : 'radial-gradient(ellipse at 0% 50%,color-mix(in srgb, var(--accent-primary) 12%, transparent),transparent 60%)',
      }}
    >
      <ReactFlowProvider>
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          nodeTypes={workflowNodeTypes}
          onNodeClick={(event, node) => {
            const multiSelect = event.ctrlKey || event.metaKey;
            setFlowNodes((current) =>
              current.map((item) => ({
                ...item,
                selected: multiSelect ? (item.id === node.id ? !item.selected : item.selected) : item.id === node.id,
              })),
            );
            onSelectNode?.(node.id);
            onSelectEdge?.('');
          }}
          onPaneClick={() => {
            onSelectNode?.('');
            onSelectEdge?.('');
          }}
          onNodeMouseMove={(event) => {
            lastPointerRef.current = { x: event.clientX, y: event.clientY };
          }}
          onEdgeClick={(_, edge) => {
            onSelectEdge?.(edge.id);
            onSelectNode?.('');
          }}
          onPaneMouseMove={(event) => {
            lastPointerRef.current = { x: event.clientX, y: event.clientY };
          }}
          onNodesChange={handleNodesChange}
          onEdgesChange={handleEdgesChange}
          onConnect={connect}
          deleteKeyCode={['Backspace', 'Delete']}
          nodesDraggable={!readOnly && !panMode}
          nodesConnectable={!readOnly && !architecture}
          elementsSelectable={!readOnly}
          selectionOnDrag={!readOnly && !panMode}
          selectionMode={SelectionMode.Partial}
          multiSelectionKeyCode="Control"
          panOnDrag={readOnly ? [2] : panMode ? true : false}
          panOnScroll={false}
          panActivationKeyCode="Shift"
          zoomOnScroll
          fitView
          fitViewOptions={{ padding: 0.3, maxZoom: 0.72 }}
          minZoom={0.2}
          maxZoom={1.8}
          defaultEdgeOptions={{ type: architecture ? 'step' : 'default', zIndex: 0, animated: false }}
          connectionLineStyle={{
            stroke: architecture ? 'var(--accent-emerald)' : 'var(--accent-primary)',
            strokeWidth: 2,
          }}
          proOptions={{ hideAttribution: true }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={architecture ? 26 : 20}
            size={1}
            color="var(--border-default)"
          />
          <CanvasToolbar
            nodes={nodes}
            selectedNodes={flowNodes.filter((node) => node.selected).map((node) => node.id)}
            readOnly={readOnly}
            panMode={panMode}
            onTogglePan={onTogglePan}
            onTogglePointer={onTogglePointer}
            onDeleteSelected={() => {
              const selectedIds = new Set(flowNodes.filter((node) => node.selected).map((node) => node.id));
              if (!selectedIds.size) return;
              const remainingNodes = nodes.filter((node) => !selectedIds.has(node.id));
              const remainingEdges = edges.filter(
                (edge) => !selectedIds.has(edge.source) && !selectedIds.has(edge.target),
              );
              onChange(remainingNodes, remainingEdges);
              onSelectNode?.('');
              onSelectEdge?.('');
            }}
            onFind={(nodeId) => {
              setFlowNodes((current) => current.map((node) => ({ ...node, selected: node.id === nodeId })));
              onSelectNode?.(nodeId);
              onSelectEdge?.('');
            }}
          />
          <div className="workflow-canvas-legend" aria-label="端口图例">
            {architecture ? (
              <span>
                <i className="legend-org" />
                组织关系
              </span>
            ) : (
              <>
                <span>
                  <i className="legend-input" />
                  输入
                </span>
                <span>
                  <i className="legend-output" />
                  输出
                </span>
                <span>
                  <i className="legend-loop" />
                  回环
                </span>
                <span>
                  <i className="legend-exit" />
                  退出
                </span>
              </>
            )}
          </div>
          <PlaceNodeRequest
            request={addRequest}
            pointerRef={lastPointerRef}
            onPlace={(type, position) => {
              setFlowNodes((current) => current.map((node) => ({ ...node, selected: false })));
              onAddAtPosition?.(type, position);
            }}
            onDone={onAddRequestDone}
          />
          <FitView count={flowNodes.length} />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}
