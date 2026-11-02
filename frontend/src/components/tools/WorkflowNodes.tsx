import { Handle, Position, useReactFlow, useViewport, type NodeProps } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Bot, GitBranch, GitFork, Hand, Layers3, Minus, MousePointer2, Plus, Search, Trash2, X } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import type { WorkflowNodeDefinition } from '../../types/project';
import { TextInput } from '../common/Field';
import './workflow.css';

export function WorkflowAgentNode({ data, selected }: NodeProps) {
  const { node } = data as { node: WorkflowNodeDefinition };
  return (
    <div
      style={{
        position: 'relative',
        minWidth: 178,
        maxWidth: 218,
        padding: 'var(--space-3) var(--space-3-5)',
        borderRadius: 'var(--radius-md-wide)',
        border: '1px solid ' + (selected ? 'var(--accent-primary)' : 'var(--border-default)'),
        background: 'var(--bg-card)',
        color: 'var(--text-primary)',
        boxShadow: selected ? 'var(--shadow-md)' : 'var(--shadow-sm)',
      }}
    >
      <Handle type="target" position={Position.Left} />
      <div
        style={{
          fontSize: 'var(--font-size-tiny)',
          color: 'var(--accent-primary)',
          letterSpacing: '.04em',
          marginBottom: 'var(--space-1-5)',
        }}
      >
        业务步骤
      </div>
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-1-75)',
          alignItems: 'center',
          fontSize: 'var(--font-size-sm)',
          fontWeight: 650,
        }}
      >
        <Bot size={14} color="var(--accent-primary)" />
        {node.title}
      </div>
      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginTop: 'var(--space-1-25)' }}>
        {node.role || '对话窗口'} · 结果传给下游
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

export function ConditionNode({ data, selected }: NodeProps) {
  const { node } = data as { node: WorkflowNodeDefinition };
  return (
    <div
      className="workflow-special-node condition-node"
      style={{ borderColor: selected ? 'var(--accent-primary)' : undefined }}
    >
      <Handle type="target" position={Position.Left} />
      <div className="workflow-special-heading">
        <GitBranch size={15} />
        分支判断
      </div>
      <strong>{node.title}</strong>
      <small>{String(node.config?.expression || '配置判断表达式')}</small>
      <Handle id="true" type="source" position={Position.Right} style={{ top: '35%' }} />
      <span className="workflow-port-label true-port">是</span>
      <Handle id="false" type="source" position={Position.Right} style={{ top: '72%' }} />
      <span className="workflow-port-label false-port">否</span>
    </div>
  );
}

export function LoopNode({ data, selected }: NodeProps) {
  const { node } = data as { node: WorkflowNodeDefinition };
  return (
    <div
      className="workflow-special-node loop-node"
      style={{ borderColor: selected ? 'var(--accent-emerald)' : undefined }}
    >
      <Handle id="repeat" type="source" position={Position.Left} />
      <span className="workflow-port-label loop-port">循环</span>
      <Handle id="input" type="target" position={Position.Right} />
      <div className="workflow-special-heading">
        <GitFork size={15} />
        循环控制
      </div>
      <strong>{node.title}</strong>
      <small>左侧回环 · 上下退出 · 上限 {Number(node.config?.max_iterations || 3)} 次</small>
      <Handle id="exit_top" type="source" position={Position.Top} />
      <span className="workflow-port-label loop-exit-top-port">退出</span>
      <Handle id="exit_bottom" type="source" position={Position.Bottom} />
      <span className="workflow-port-label loop-exit-bottom-port">退出</span>
    </div>
  );
}

export function ArchitectureAgentNode({ data, selected }: NodeProps) {
  const { node, hasChildren, hasParent, collapsed, onToggle, onAction } = data as {
    node: WorkflowNodeDefinition;
    hasChildren: boolean;
    hasParent: boolean;
    collapsed: boolean;
    onToggle: () => void;
    onAction: (action: 'child' | 'peer') => void;
  };
  const act = (event: React.MouseEvent, action: 'child' | 'peer') => {
    event.stopPropagation();
    onAction(action);
  };
  return (
    <div className="architecture-node-card" style={{ borderColor: selected ? 'var(--accent-emerald)' : undefined }}>
      <Handle id="top" type="target" position={Position.Top} isConnectable={false} />
      <span className="workflow-handle-label architecture-input-label">上级</span>
      <div className="architecture-node-actions" role="toolbar" aria-label={`${node.title} 节点操作`}>
        <button title="添加下级" aria-label="添加下级" onClick={(event) => act(event, 'child')}>
          <Plus size={14} />
        </button>
        <button title="添加同级" aria-label="添加同级" disabled={!hasParent} onClick={(event) => act(event, 'peer')}>
          <GitBranch size={13} />
        </button>
      </div>
      <div className="architecture-node-eyebrow">组织职责窗口</div>
      <div className="architecture-node-name">
        <Layers3 size={14} color="var(--accent-emerald)" />
        {node.title}
      </div>
      <div className="architecture-node-role">{node.role || '职责待定义'}</div>
      {node.responsibilities?.[0] && <div className="architecture-node-responsibility">{node.responsibilities[0]}</div>}
      <Handle id="bottom" type="source" position={Position.Bottom} isConnectable={false} />
      <span className="workflow-handle-label architecture-output-label">下级</span>
      {hasChildren && (
        <button
          className="architecture-collapse-button"
          aria-label={collapsed ? '展开下级' : '收起下级'}
          title={collapsed ? '展开下级' : '收起下级'}
          onClick={(event) => {
            event.stopPropagation();
            onToggle();
          }}
        >
          {collapsed ? <Plus size={12} /> : <Minus size={12} />}
        </button>
      )}
    </div>
  );
}

export function PlaceNodeRequest({
  request,
  pointerRef,
  onPlace,
  onDone,
}: {
  request: { id: number; type: 'agent' | 'condition' | 'loop' } | null | undefined;
  pointerRef: React.RefObject<{ x: number; y: number } | null>;
  onPlace?: (type: 'agent' | 'condition' | 'loop', position: { x: number; y: number }) => void;
  onDone?: () => void;
}) {
  const { screenToFlowPosition } = useReactFlow();
  const handled = useRef(0);
  useEffect(() => {
    if (!request || request.id === handled.current || !onPlace) return;
    handled.current = request.id;
    const canvas = document.querySelector<HTMLElement>('.workflow-canvas');
    const bounds = canvas?.getBoundingClientRect();
    const point =
      pointerRef.current ||
      (bounds
        ? { x: bounds.left + bounds.width / 2, y: bounds.top + bounds.height / 2 }
        : { x: window.innerWidth / 2, y: window.innerHeight / 2 });
    const x = bounds
      ? Math.max(
          bounds.left + 130,
          Math.min(point.x, bounds.right - (document.querySelector('.workflow-node-inspector') ? 360 : 160)),
        )
      : point.x;
    const y = bounds ? Math.max(bounds.top + 100, Math.min(point.y, bounds.bottom - 110)) : point.y;
    onPlace(request.type, screenToFlowPosition({ x, y }));
    onDone?.();
  }, [request, onPlace, onDone, pointerRef, screenToFlowPosition]);
  return null;
}

export function CanvasToolbar({
  nodes,
  selectedNodes,
  readOnly,
  panMode,
  onTogglePan,
  onTogglePointer,
  onDeleteSelected,
  onFind,
}: {
  nodes: WorkflowNodeDefinition[];
  selectedNodes: string[];
  readOnly: boolean;
  panMode: boolean;
  onTogglePan: () => void;
  onTogglePointer: () => void;
  onDeleteSelected: () => void;
  onFind: (id: string) => void;
}) {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const { zoom } = useViewport();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const matches = nodes
    .filter((item) =>
      `${item.title} ${item.role || ''} ${(item.responsibilities || []).join(' ')}`
        .toLocaleLowerCase()
        .includes(query.trim().toLocaleLowerCase()),
    )
    .slice(0, 8);
  const choose = (node: WorkflowNodeDefinition) => {
    onFind(node.id);
    setOpen(false);
    void fitView({ nodes: [{ id: node.id }], duration: 300, padding: 0.5, maxZoom: 1.1 });
  };
  return (
    <>
      <div className="workflow-canvas-toolbar">
        {!readOnly && (
          <>
            <button
              className={`workflow-icon-button${!panMode ? ' is-active' : ''}`}
              title="指针：移动节点并框选"
              aria-label="指针：移动节点并框选"
              aria-pressed={!panMode}
              onClick={onTogglePointer}
            >
              <MousePointer2 size={17} />
            </button>
            <button
              className={`workflow-icon-button${panMode ? ' is-active' : ''}`}
              title="手形：拖动画布"
              aria-label="手形：拖动画布"
              aria-pressed={panMode}
              onClick={onTogglePan}
            >
              <Hand size={17} />
            </button>
          </>
        )}
        <button
          className="workflow-icon-button"
          title="搜索节点"
          aria-label="搜索节点"
          onClick={() => {
            setOpen(true);
            setQuery('');
          }}
        >
          <Search size={17} />
        </button>
        <div className="workflow-zoom-control" role="group" aria-label="画布缩放">
          <button
            className="workflow-icon-button"
            title="缩小"
            aria-label="缩小"
            onClick={() => void zoomOut({ duration: 120 })}
          >
            <Minus size={16} />
          </button>
          <span aria-live="polite">{Math.round(zoom * 100)}%</span>
          <button
            className="workflow-icon-button"
            title="放大"
            aria-label="放大"
            onClick={() => void zoomIn({ duration: 120 })}
          >
            <Plus size={16} />
          </button>
        </div>
        {selectedNodes.length > 1 && !readOnly && (
          <button
            className="workflow-selection-delete"
            title={`删除选中的 ${selectedNodes.length} 个节点`}
            onClick={onDeleteSelected}
          >
            <Trash2 size={14} />
            <span>删除 {selectedNodes.length}</span>
          </button>
        )}
      </div>
      {open && (
        <div
          className="workflow-search-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setOpen(false);
          }}
        >
          <section className="workflow-search-dialog" role="dialog" aria-modal="true" aria-label="搜索节点">
            <div className="workflow-search-input-wrap">
              <Search size={17} />
              <TextInput
                autoFocus
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && matches[0]) choose(matches[0]);
                  if (event.key === 'Escape') setOpen(false);
                }}
                placeholder="搜索名称或职责…"
                aria-label="搜索名称或职责"
              />
              <button className="workflow-icon-button" aria-label="关闭搜索" onClick={() => setOpen(false)}>
                <X size={16} />
              </button>
            </div>
            <div className="workflow-search-results">
              {query.trim()
                ? matches.length
                  ? matches.map((node) => (
                      <button key={node.id} className="workflow-search-result" onClick={() => choose(node)}>
                        <strong>{node.title}</strong>
                        <span>{node.role || node.type}</span>
                      </button>
                    ))
                  : '没有找到匹配的节点'
                : '搜索名称或职责…'}
            </div>
          </section>
        </div>
      )}
    </>
  );
}

export function FitView({ count }: { count: number }) {
  const { fitView } = useReactFlow();
  const fitted = useRef(false);
  useEffect(() => {
    if (!count || fitted.current) return;
    fitted.current = true;
    const timer = setTimeout(() => void fitView({ padding: 0.3, maxZoom: 0.72, duration: 180 }), 60);
    return () => clearTimeout(timer);
  }, [count, fitView]);
  return null;
}
