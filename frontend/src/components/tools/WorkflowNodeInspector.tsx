import '@xyflow/react/dist/style.css';
import { X } from 'lucide-react';
import { Button } from '../common/Button';
import { TextArea, TextInput } from '../common/Field';
import { IconButton } from '../common/IconButton';
import { useWorkflowEditor } from './useWorkflowEditor';
import './workflow.css';
export function WorkflowNodeInspector({
  nodes,
  edges,
  setSelectedNodeId,
  selectedNode,
  architecture,
  commitGraph,
  patch,
}: Pick<
  ReturnType<typeof useWorkflowEditor>,
  'nodes' | 'edges' | 'setSelectedNodeId' | 'selectedNode' | 'architecture' | 'commitGraph' | 'patch'
>) {
  return (
    <>
      {selectedNode && (
        <aside className="workflow-node-inspector">
          <div className="workflow-inspector-title">
            <div>
              <h3>{selectedNode.title}</h3>
              <small>
                {architecture
                  ? '职责窗口配置'
                  : selectedNode.type === 'agent'
                    ? '对话窗口配置'
                    : selectedNode.type === 'condition'
                      ? '判断条件配置'
                      : '循环节点配置'}
              </small>
            </div>
            <IconButton label="关闭节点配置" onClick={() => setSelectedNodeId('')} size="sm">
              <X size={14} />
            </IconButton>
          </div>
          <label>
            节点名称
            <TextInput
              value={selectedNode.title}
              onChange={(e) => patch(selectedNode.id, { title: e.target.value })}
              className="workflow-field"
            />
          </label>
          <label>
            角色
            <TextInput
              value={selectedNode.role || ''}
              onChange={(e) => patch(selectedNode.id, { role: e.target.value })}
              className="workflow-field"
            />
          </label>
          {architecture ? (
            <>
              <section className="workflow-node-flow" aria-label="组织关系">
                <div>
                  <strong>上级</strong>
                  {edges
                    .filter((edge) => edge.target === selectedNode.id)
                    .map((edge) => {
                      const parent = nodes.find((node) => node.id === edge.source);
                      return <span key={edge.id || edge.source}>{parent?.title || edge.source}</span>;
                    })}
                  {!edges.some((edge) => edge.target === selectedNode.id) && (
                    <span>无（根节点，直接接收本次任务）</span>
                  )}
                </div>
                <div>
                  <strong>下级</strong>
                  {edges
                    .filter((edge) => edge.source === selectedNode.id)
                    .map((edge) => {
                      const child = nodes.find((node) => node.id === edge.target);
                      return <span key={edge.id || edge.target}>{child?.title || edge.target}</span>;
                    })}
                  {!edges.some((edge) => edge.source === selectedNode.id) && <span>无（末级职责）</span>}
                </div>
                <small>
                  上下级关系通过节点上的“添加下级 /
                  添加同级”建立。执行时自上而下进行：上级完成后，其结果作为任务交给各个下级；全部完成后由 Supervisor
                  汇总。
                </small>
              </section>
            </>
          ) : (
            <>
              <section className="workflow-node-flow" aria-label="节点数据流">
                <div>
                  <strong>输入</strong>
                  {edges
                    .filter((edge) => edge.target === selectedNode.id)
                    .map((edge) => {
                      const source = nodes.find((node) => node.id === edge.source);
                      return (
                        <span key={edge.id || edge.source}>
                          {source?.title || edge.source}
                          {selectedNode.type === 'agent' && ' 的上游结果'}
                          {Boolean(edge.config?.sourceHandle) &&
                            ` · ${edge.config?.sourceHandle === 'true' ? '是' : edge.config?.sourceHandle === 'false' ? '否' : edge.config?.sourceHandle === 'repeat' ? '循环' : '退出'}`}
                        </span>
                      );
                    })}
                  {!edges.some((edge) => edge.target === selectedNode.id) && <span>原始任务</span>}
                </div>
                <div>
                  <strong>输出</strong>
                  {edges
                    .filter((edge) => edge.source === selectedNode.id)
                    .map((edge) => {
                      const target = nodes.find((node) => node.id === edge.target);
                      return (
                        <span key={edge.id || edge.target}>
                          {edge.config?.sourceHandle
                            ? `${edge.config?.sourceHandle === 'true' ? '是' : edge.config?.sourceHandle === 'false' ? '否' : edge.config?.sourceHandle === 'repeat' ? '循环' : '退出'} → `
                            : ''}
                          {target?.title || edge.target}
                        </span>
                      );
                    })}
                  {!edges.some((edge) => edge.source === selectedNode.id) && (
                    <span>流程终端结果由 Supervisor 汇总</span>
                  )}
                </div>
                <small>
                  {selectedNode.type === 'condition'
                    ? '输入为本次任务和所有已完成的上游输出；YES/NO 只控制分支，不会作为业务内容传递。'
                    : selectedNode.type === 'loop'
                      ? '输入为本次任务和本轮上游结果；NO 的反馈会随循环出口返回循环体窗口。'
                      : '已执行的入线结果会并入上游信息；未经过的分支不会提供结果。'}
                </small>
              </section>
            </>
          )}
          {(architecture || selectedNode.type === 'agent') && (
            <label>
              角色
              <TextInput
                value={selectedNode.role || ''}
                onChange={(e) => patch(selectedNode.id, { role: e.target.value })}
                className="workflow-field"
              />
            </label>
          )}
          {selectedNode.type === 'condition' && (
            <>
              <label>
                判断条件
                <TextArea
                  value={String(selectedNode.config?.expression || '')}
                  onChange={(e) =>
                    patch(selectedNode.id, { config: { ...selectedNode.config, expression: e.target.value } })
                  }
                  rows={3}
                  className="workflow-field"
                  placeholder="例如：上游结果已通过验收"
                />
              </label>
              <div className="workflow-capability-note">
                判断依据是本次任务和所有已完成的上游输出。系统会按 JSON Schema 返回 decision（YES/NO）和
                reason（说明）；YES 走“是”出口，NO
                走“否”出口。判断由独立控制节点执行，使用调用对话当前模型，不调用工具。
              </div>
            </>
          )}
          {selectedNode.type === 'loop' && (
            <>
              <label>
                最大总轮数
                <TextInput
                  type="number"
                  min={1}
                  max={20}
                  value={Number(selectedNode.config?.max_iterations || 3)}
                  onChange={(e) =>
                    patch(selectedNode.id, {
                      config: {
                        ...selectedNode.config,
                        max_iterations: Math.max(1, Math.min(20, Number(e.target.value) || 1)),
                      },
                    })
                  }
                  className="workflow-field"
                />
              </label>
              <label>
                循环退出条件
                <TextArea
                  value={String(selectedNode.config?.continue_condition || '')}
                  onChange={(e) =>
                    patch(selectedNode.id, { config: { ...selectedNode.config, continue_condition: e.target.value } })
                  }
                  rows={3}
                  className="workflow-field"
                  placeholder="例如：上游结果已达到项目目标"
                />
              </label>
              <div className="workflow-capability-note">
                判断依据是本次任务和本轮已完成的上游输出。系统按 JSON Schema 返回 decision（YES/NO）、reason（说明）和
                feedback（反馈）。YES 表示达到退出条件，走“退出”出口；NO 表示继续，feedback
                会注入循环体窗口，说明需要修改或补做什么。判断由独立控制节点执行，使用调用对话当前模型，不调用工具；达到最大总轮数后安全退出。
              </div>
            </>
          )}
          {selectedNode.type === 'agent' && (
            <>
              <label>
                角色背景
                <TextArea
                  value={selectedNode.background || ''}
                  onChange={(e) => patch(selectedNode.id, { background: e.target.value })}
                  rows={3}
                  className="workflow-field"
                  placeholder="填写该角色稳定的专业背景和工作环境"
                />
              </label>
              <label>
                职责
                <TextArea
                  value={(selectedNode.responsibilities || []).join('\n')}
                  onChange={(e) =>
                    patch(selectedNode.id, { responsibilities: e.target.value.split('\n').filter(Boolean) })
                  }
                  rows={4}
                  className="workflow-field"
                  placeholder="每行填写一项职责"
                />
              </label>
              <label>
                约束
                <TextArea
                  value={(selectedNode.constraints || []).join('\n')}
                  onChange={(e) => patch(selectedNode.id, { constraints: e.target.value.split('\n').filter(Boolean) })}
                  rows={4}
                  className="workflow-field"
                  placeholder="每行填写一项约束，例如：不得将未验证的信息当作事实"
                />
              </label>
              <label>
                输出规范
                <TextArea
                  value={selectedNode.output_spec || ''}
                  onChange={(e) => patch(selectedNode.id, { output_spec: e.target.value })}
                  rows={4}
                  className="workflow-field"
                  placeholder="说明需要交付的内容、结构和格式"
                />
              </label>
              <div className="workflow-capability-note">
                模型跟随发起对话当前选择。执行上下文由系统规则、项目目标与背景、节点角色配置、本次任务和实际连线到达的上游结果拼接。
              </div>
            </>
          )}
          <Button
            title="删除节点"
            variant="danger"
            size="sm"
            className="workflow-action workflow-node-delete"
            onClick={() => {
              commitGraph(
                nodes.filter((n) => n.id !== selectedNode.id),
                edges.filter((edge) => edge.source !== selectedNode.id && edge.target !== selectedNode.id),
              );
              setSelectedNodeId('');
            }}
          >
            移除节点
          </Button>
        </aside>
      )}
    </>
  );
}
