import '@xyflow/react/dist/style.css';
import {
  ArrowLeft,
  Bot,
  GitBranch,
  GitFork,
  Play,
  Plus,
  Redo2,
  Save,
  Settings2,
  Trash2,
  Undo2,
  Workflow,
  X,
} from 'lucide-react';
import { Button } from '../common/Button';
import { SelectField, TextArea, TextInput } from '../common/Field';
import { IconButton } from '../common/IconButton';
import './workflow.css';
import { Canvas } from './WorkflowCanvas';
import { WorkflowNodeInspector } from './WorkflowNodeInspector';
import { ErrorText } from './WorkflowPanels';

import { useWorkflowEditor } from './useWorkflowEditor';
export function WorkflowEditorView({
  infoPanelRequest,
  globalMode,
  createActionLabel,
  kind,
  name,
  setName,
  description,
  setDescription,
  projectGoal,
  setProjectGoal,
  projectBackground,
  setProjectBackground,
  nodes,
  edges,
  error,
  busy,
  onSave,
  setInfoClosedAtRequest,
  infoOpen,
  paletteOpen,
  setPaletteOpen,
  projectContextOpen,
  setProjectContextOpen,
  setSelectedNodeId,
  selectedEdgeId,
  setSelectedEdgeId,
  canvasError,
  setCanvasError,
  panMode,
  setPanMode,
  addRequest,
  setAddRequest,
  requestCancel,
  selectedNode,
  architecture,
  historyStatus,
  commitGraph,
  moveHistory,
  patch,
  addNode,
  nodeAction,
  handleEditorTypeChange,
  handleEditorAddNode1,
  handleEditorAddNode2,
  handleEditorAddNode3,
}: ReturnType<typeof useWorkflowEditor>) {
  return (
    <div
      style={{ height: '100%', display: 'flex', flexDirection: 'column', color: 'var(--text-primary)', minHeight: 0 }}
    >
      <header
        style={{
          padding: 'var(--space-2-5) var(--space-3-5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <Button
          onClick={requestCancel}
          variant="secondary"
          size="sm"
          className="workflow-action"
          icon={<ArrowLeft size={14} aria-hidden="true" />}
        >
          返回
        </Button>
        <strong>
          {globalMode ? '全局模板' : '项目实例'} · {architecture ? '组织架构' : '工作流'}
        </strong>
        <div style={{ display: 'flex', gap: 'var(--space-1-5)' }}>
          <IconButton
            title="撤销"
            label="撤销"
            disabled={historyStatus.cursor === 0}
            onClick={() => moveHistory(-1)}
            size="sm"
          >
            <Undo2 size={14} />
          </IconButton>
          <IconButton
            title="重做"
            label="重做"
            disabled={historyStatus.cursor >= historyStatus.length - 1}
            onClick={() => moveHistory(1)}
            size="sm"
          >
            <Redo2 size={14} />
          </IconButton>
          {selectedEdgeId && (
            <Button
              variant="danger"
              size="sm"
              className="workflow-action"
              title="删除所选连线"
              onClick={() => {
                commitGraph(
                  nodes,
                  edges.filter((edge) => edge.id !== selectedEdgeId),
                );
                setSelectedEdgeId('');
              }}
              icon={<Trash2 size={14} aria-hidden="true" />}
            >
              删除连线
            </Button>
          )}
          <Button
            variant="primary"
            size="sm"
            className="workflow-action"
            disabled={busy}
            onClick={onSave}
            icon={createActionLabel ? <Play size={14} aria-hidden="true" /> : <Save size={14} aria-hidden="true" />}
          >
            {createActionLabel || (globalMode ? '保存模板' : '保存修改')}
          </Button>
        </div>
      </header>
      {error && <ErrorText text={error} />}
      <div style={{ flex: 1, minHeight: 0, position: 'relative', overflow: 'hidden' }}>
        <Canvas
          key={kind}
          kind={kind}
          nodes={nodes}
          edges={edges}
          onChange={commitGraph}
          selectedNodeId={selectedNode?.id || ''}
          selectedEdgeId={selectedEdgeId}
          onSelectNode={(nodeId) => {
            setSelectedNodeId(nodeId);
            if (nodeId) setSelectedEdgeId('');
            setCanvasError('');
          }}
          onSelectEdge={setSelectedEdgeId}
          onNodeAction={nodeAction}
          onError={setCanvasError}
          panMode={panMode}
          onTogglePan={() => setPanMode((value) => !value)}
          onTogglePointer={() => setPanMode(false)}
          addRequest={addRequest}
          onAddRequestDone={() => setAddRequest(null)}
          onAddAtPosition={(type, position) => addNode(type, 'root', undefined, position)}
        />
        <div className="workflow-canvas-actions">
          <Button
            variant={infoOpen ? 'secondary' : 'ghost'}
            size="sm"
            className="workflow-action"
            onClick={() => {
              const opening = !infoOpen;
              setInfoClosedAtRequest(opening ? null : infoPanelRequest);
              if (opening) {
                setPaletteOpen(false);
                setProjectContextOpen(false);
              }
            }}
            aria-expanded={infoOpen}
            icon={<Settings2 size={14} aria-hidden="true" />}
          >
            基本信息
          </Button>
          {!globalMode && (
            <Button
              variant={projectContextOpen ? 'secondary' : 'ghost'}
              size="sm"
              className="workflow-action"
              onClick={() => {
                const opening = !projectContextOpen;
                setProjectContextOpen(opening);
                if (opening) {
                  setPaletteOpen(false);
                  setInfoClosedAtRequest(infoPanelRequest);
                }
              }}
              aria-expanded={projectContextOpen}
            >
              项目上下文
            </Button>
          )}
          <Button
            variant={paletteOpen ? 'secondary' : 'ghost'}
            size="sm"
            className="workflow-action"
            onClick={() => {
              const opening = !paletteOpen;
              setPaletteOpen(opening);
              if (opening) {
                setInfoClosedAtRequest(infoPanelRequest);
                setProjectContextOpen(false);
              }
            }}
            aria-expanded={paletteOpen}
            icon={<Plus size={14} aria-hidden="true" />}
          >
            添加节点
          </Button>
        </div>
        {infoOpen && (
          <section className="workflow-float-panel workflow-info-panel">
            <Button
              variant="ghost"
              size="md"
              className="workflow-panel-heading"
              onClick={() => setInfoClosedAtRequest(infoPanelRequest)}
            >
              <span>
                <Workflow size={14} />
                基本信息
              </span>
              <X size={14} />
            </Button>
            <div className="workflow-panel-content">
              <label>
                名称
                <TextInput
                  aria-label="编排名称"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="为编排命名"
                  className="workflow-field"
                />
              </label>
              <label>
                类型
                <SelectField
                  aria-label="编排类型"
                  value={kind}
                  onChange={handleEditorTypeChange}
                  className="workflow-field"
                >
                  <option value="workflow">工作流</option>
                  <option value="architecture">组织架构</option>
                </SelectField>
              </label>
              {globalMode ? (
                <label>
                  简介
                  <TextArea
                    aria-label="编排说明"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder={architecture ? '说明组织目标与职责' : '说明工作流目标'}
                    rows={8}
                    className="workflow-field workflow-description-field"
                  />
                </label>
              ) : (
                <div className="workflow-capability-note">
                  项目目标和背景补充在“项目上下文”中编辑，并会注入本次实例运行的各个窗口。
                </div>
              )}
            </div>
          </section>
        )}
        {projectContextOpen && (
          <section className="workflow-float-panel workflow-context-panel" role="dialog" aria-label="项目上下文">
            <Button
              variant="ghost"
              size="md"
              className="workflow-panel-heading"
              onClick={() => setProjectContextOpen(false)}
            >
              <span>
                <Workflow size={14} />
                项目上下文
              </span>
              <X size={14} />
            </Button>
            <div className="workflow-panel-content">
              <label>
                项目目标
                <TextArea
                  aria-label="项目目标"
                  value={projectGoal}
                  onChange={(event) => setProjectGoal(event.target.value)}
                  rows={4}
                  className="workflow-field"
                  placeholder="说明此项目实例要达成的目标"
                />
              </label>
              <label>
                背景补充
                <TextArea
                  aria-label="项目背景补充"
                  value={projectBackground}
                  onChange={(event) => setProjectBackground(event.target.value)}
                  rows={7}
                  className="workflow-field"
                  placeholder="填写项目术语、约定、稳定背景和限制；本次任务由调用时传入"
                />
              </label>
              <div className="workflow-capability-note">
                项目上下文与节点角色配置、本次调用任务和实际连线传入的上游结果共同形成各窗口的上下文。
              </div>
            </div>
          </section>
        )}
        {paletteOpen && (
          <section className="workflow-float-panel workflow-node-panel">
            <Button variant="ghost" size="md" className="workflow-panel-heading" onClick={() => setPaletteOpen(false)}>
              <span>
                <Plus size={14} />
                选择节点
              </span>
              <X size={14} />
            </Button>
            <div className="workflow-panel-content workflow-node-actions">
              <Button
                variant="secondary"
                size="sm"
                className="workflow-action"
                onClick={handleEditorAddNode1}
                icon={<Bot size={13} aria-hidden="true" />}
              >
                {architecture ? '职责窗口' : '对话窗口'}
              </Button>
              {!architecture && (
                <>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="workflow-action"
                    onClick={handleEditorAddNode2}
                    icon={<GitBranch size={13} aria-hidden="true" />}
                  >
                    分支判断
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="workflow-action"
                    onClick={handleEditorAddNode3}
                    icon={<GitFork size={13} aria-hidden="true" />}
                  >
                    循环
                  </Button>
                </>
              )}
              <div className="workflow-capability-note">
                {architecture
                  ? '从根职责窗口开始，再添加下级或同级职责。'
                  : '连线按上游完成顺序传递结果。MCP、Skill 和 HTTP 当前没有节点级执行器。'}
              </div>
            </div>
          </section>
        )}
        {canvasError && (
          <div role="alert" className="workflow-canvas-alert">
            {canvasError}
          </div>
        )}
        <WorkflowNodeInspector
          nodes={nodes}
          edges={edges}
          setSelectedNodeId={setSelectedNodeId}
          selectedNode={selectedNode}
          architecture={architecture}
          commitGraph={commitGraph}
          patch={patch}
        />
      </div>
    </div>
  );
}
