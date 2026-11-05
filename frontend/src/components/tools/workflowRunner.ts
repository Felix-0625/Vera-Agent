import type {
  RunInputRecord,
  RunnerDeps,
  RunNodeState,
  RunOutcome,
  RunSession,
  RunStage,
  WorkflowControlResult,
} from './workflowRunTypes';
export type {
  NodeTurnRequest,
  RunInputRecord,
  RunLogEntry,
  RunnerDeps,
  RunNodeState,
  RunOutcome,
  RunSession,
  RunStage,
  WorkflowControlResult,
} from './workflowRunTypes';
/**
 * Workflow / organization run scheduler.
 *
 * Executes a project instance node by node: every node runs in its own isolated session through
 * the chat stream, outputs travel along active edges, `condition` and `loop` nodes make strict
 * YES/NO control decisions, and a final Supervisor turn reviews the collected outputs. All side
 * effects (model calls, run persistence, log display) are injected through `RunnerDeps`, so the
 * scheduling rules can be unit-tested without a browser or backend. Backend counterpart:
 * `vera-agent/src/vera_agent/server/routes/runs.py` (run/node state validation).
 */
import type { Group, WorkflowEdgeDefinition, WorkflowNodeDefinition } from '../../types/project';

/** Body of one node turn sent to `POST /api/chat/stream` (thread/project/model are added by the caller). */

const SKIPPED_OUTPUT = '未进入本次选中的执行路径，因此未运行。';

const edgeKey = (edge: WorkflowEdgeDefinition) =>
  edge.id ||
  [
    edge.source,
    edge.target,
    edge.config?.sourceHandle || '',
    edge.config?.targetHandle || '',
    edge.relation || '',
    edge.label || '',
  ].join('->');

export function parseWorkflowControlResult(raw: string, type: 'condition' | 'loop'): WorkflowControlResult {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    throw new Error('判断节点未返回有效 JSON Schema 结果，流程已停止。');
  }
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('判断结果必须是 JSON 对象，流程已停止。');
  const result = value as Record<string, unknown>;
  if (
    (result.decision !== 'YES' && result.decision !== 'NO') ||
    typeof result.reason !== 'string' ||
    !result.reason.trim()
  ) {
    throw new Error('判断结果缺少有效的 decision 或 reason，流程已停止。');
  }
  if (type === 'loop' && result.decision === 'NO' && (typeof result.feedback !== 'string' || !result.feedback.trim())) {
    throw new Error('循环判断为 NO 时必须提供具体的 feedback，流程已停止。');
  }
  return {
    decision: result.decision,
    reason: result.reason.trim(),
    ...(typeof result.feedback === 'string' ? { feedback: result.feedback.trim() } : {}),
  };
}

function formatWorkflowControlResult(type: 'condition' | 'loop', result: WorkflowControlResult): string {
  const route =
    type === 'loop' ? (result.decision === 'YES' ? '退出循环' : '继续循环') : result.decision === 'YES' ? '是' : '否';
  return [
    `判断结果：${result.decision}（${route}）`,
    `说明：${result.reason}`,
    ...(type === 'loop' && result.decision === 'NO' ? [`返回循环体的处理要求：${result.feedback}`] : []),
  ].join('\n');
}

/** Mark nodes that never started as skipped once a run finishes. */
export function finalizeNodes(sessions: RunSession[], nodes: RunNodeState[]): RunNodeState[] {
  return sessions.map((session) => {
    const state = nodes.find((item) => item.node_id === session.node_id) || {
      node_id: session.node_id,
      status: 'skipped',
      output: '',
      inputs: [],
    };
    return state.status === 'pending' ? { ...state, status: 'skipped', output: SKIPPED_OUTPUT } : state;
  });
}

/**
 * Execute `group` for one run and return the Supervisor's final answer.
 *
 * `nodesRef.current` always holds the latest node states, so a caller can persist them as
 * `failed` if this throws. The run's terminal status (`completed`/`failed`) is saved by the caller.
 */
export async function executeRun(
  group: Group,
  sessions: RunSession[],
  input: string,
  deps: RunnerDeps,
  nodesRef: { current: RunNodeState[] },
): Promise<RunOutcome> {
  const runNodes: RunNodeState[] = sessions.map((session) => ({
    node_id: session.node_id,
    status: 'pending',
    output: '',
    inputs: [],
  }));
  nodesRef.current = [...runNodes];
  const outputs = new Map<string, string>();
  const executionOrder: string[] = [];
  const allNodes = group.nodes || [];
  const allEdges = group.edges || [];
  const byId = new Map(allNodes.map((n) => [n.id, n]));
  const sessionsByNode = new Map(sessions.map((session) => [session.node_id, session]));
  const incoming = (nodeId: string) => allEdges.filter((edge) => edge.target === nodeId);
  const outgoing = (nodeId: string) => allEdges.filter((edge) => edge.source === nodeId);
  const root = allNodes.find(
    (node) => node.type === 'agent' && !incoming(node.id).some((edge) => byId.get(edge.source)?.type !== 'loop'),
  );
  if (!root) throw new Error('找不到流程起始对话窗口。请确保有一个没有上游窗口的起始节点。');
  const executionCount = new Map<string, number>();
  const loopCount = new Map<string, number>();
  const executed = new Set<string>();
  const visited = new Set<string>();
  const activeEdges = new Set<string>();
  const stepLimit = Math.min(1000, Math.max(40, allNodes.length * 22));
  let steps = 0;

  const activeInputs = (nodeId: string): RunInputRecord[] =>
    incoming(nodeId)
      .filter((edge) => activeEdges.has(edgeKey(edge)) && outputs.has(edge.source))
      .map((edge) => ({
        node_id: edge.source,
        title: byId.get(edge.source)?.title || edge.source,
        relation: edge.relation,
        label: edge.label,
        output: outputs.get(edge.source) || '',
      }));

  const persistNodeState = async (
    nodeId: string,
    status: string,
    output: string,
    inputs: RunInputRecord[] = [],
    error = '',
  ) => {
    const snapshot: RunNodeState = { node_id: nodeId, status, output, error, inputs };
    const savedIndex = runNodes.findIndex((item) => item.node_id === nodeId);
    if (savedIndex >= 0) runNodes[savedIndex] = snapshot;
    else runNodes.push(snapshot);
    nodesRef.current = [...runNodes];
    await deps.saveNodes(nodesRef.current);
  };

  const invokeNode = async (
    node: WorkflowNodeDefinition,
    stage?: RunStage,
    controlNode?: WorkflowNodeDefinition,
  ): Promise<string> => {
    const session = sessionsByNode.get(node.id);
    if (!session) throw new Error(`节点「${node.title}」没有运行会话。`);
    const upstreamRecords =
      stage === 'supervisor_review'
        ? allNodes
            .filter((item) => item.type === 'agent' && outputs.has(item.id))
            .map((item) => ({ node_id: item.id, title: item.title, output: outputs.get(item.id) || '' }))
        : activeInputs(stage === 'control_decision' ? controlNode?.id || node.id : node.id);
    const countKey = stage ? `${node.id}:${stage}` : node.id;
    const count = (executionCount.get(countKey) || 0) + 1;
    executionCount.set(countKey, count);
    const logTitle =
      stage === 'supervisor_review'
        ? `${node.title} · Supervisor 验证`
        : stage === 'control_decision'
          ? `${controlNode?.title || node.title} · 判断（${node.title}）${count > 1 ? `（第 ${count} 次）` : ''}`
          : count > 1
            ? `${node.title}（第 ${count} 轮）`
            : node.title;
    let output = '';
    // The Supervisor review is a run-level step: its result is stored as `final_output`, so it must not
    // overwrite the reviewing node's own persisted state, output, or upstream provenance.
    const runNodeId =
      stage === 'supervisor_review' ? '' : stage === 'control_decision' ? controlNode?.id || node.id : node.id;
    deps.updateLog((old) => [
      ...old,
      {
        title: logTitle,
        status: stage === 'control_decision' ? '判断中' : stage === 'supervisor_review' ? '复核中' : '运行中',
        output: '',
        inputs: upstreamRecords,
      },
    ]);
    if (runNodeId) await persistNodeState(runNodeId, 'running', '', upstreamRecords);
    try {
      await deps.streamNode(
        {
          threadId: session.thread_id,
          content:
            stage === 'supervisor_review'
              ? '请检查系统提供的原始任务和结构化节点结果，并形成最终答复。'
              : stage === 'control_decision'
                ? '请按系统提示中的控制节点定义，基于任务和已完成的上游结果作出判断。'
                : `请根据系统提供的任务与结构化上游结果完成本窗口职责。${node.type === 'condition' ? `\n\n判断条件：${String(node.config?.expression || '')}` : ''}${node.type === 'loop' ? `\n\n循环继续条件：${String(node.config?.continue_condition || '')}` : ''}`,
          workflowInput: input,
          workflowContext: { task: input, upstream: upstreamRecords },
          workflowControl:
            stage === 'control_decision' && controlNode
              ? {
                  type: controlNode.type === 'loop' ? 'loop' : 'condition',
                  condition: String(
                    controlNode.type === 'loop'
                      ? controlNode.config?.continue_condition || ''
                      : controlNode.config?.expression || '',
                  ),
                  ...(controlNode.type === 'loop'
                    ? { max_iterations: Math.max(1, Math.min(20, Number(controlNode.config?.max_iterations) || 3)) }
                    : {}),
                }
              : undefined,
          workflowStage: stage,
        },
        (text) => {
          output = text;
          deps.updateLog((old) => old.map((entry) => (entry.title === logTitle ? { ...entry, output } : entry)));
        },
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : '节点运行失败';
      if (runNodeId)
        await persistNodeState(runNodeId, 'failed', output, upstreamRecords, message).catch(() => undefined);
      deps.updateLog((old) =>
        old.map((entry) => (entry.title === logTitle ? { ...entry, status: '失败', output, error: message } : entry)),
      );
      throw error;
    }
    if (!stage) outputs.set(node.id, output);
    if (!stage && node.type === 'agent') executionOrder.push(node.id);
    if (!stage) await persistNodeState(node.id, 'completed', output, upstreamRecords);
    deps.updateLog((old) =>
      old.map((entry) => (entry.title === logTitle ? { ...entry, status: '已完成', output } : entry)),
    );
    return output;
  };

  const evaluateControl = async (node: WorkflowNodeDefinition): Promise<WorkflowControlResult> => {
    const controlType = node.type === 'loop' ? 'loop' : 'condition';
    const raw = await invokeNode(node, 'control_decision', node);
    let result: WorkflowControlResult;
    try {
      result = parseWorkflowControlResult(raw, controlType);
    } catch (error) {
      const message = error instanceof Error ? error.message : '控制节点返回无效结构。';
      await persistNodeState(node.id, 'failed', raw, [], message);
      deps.updateLog((old) =>
        old.map((entry) =>
          entry.title.startsWith(`${node.title} · 判断`)
            ? { ...entry, status: '失败', output: raw, error: message }
            : entry,
        ),
      );
      throw new Error(message);
    }
    const formatted = formatWorkflowControlResult(controlType, result);
    await persistNodeState(node.id, 'completed', formatted, activeInputs(node.id));
    deps.updateLog((old) =>
      old.map((entry) =>
        entry.title.startsWith(`${node.title} · 判断`)
          ? { ...entry, status: `已判断：${result.decision}`, output: formatted }
          : entry,
      ),
    );
    return result;
  };

  const upstreamSummary = (nodeId: string) =>
    incoming(nodeId)
      .filter((edge) => activeEdges.has(edgeKey(edge)))
      .map((edge) => `${byId.get(edge.source)?.title || edge.source}: ${outputs.get(edge.source) || ''}`)
      .filter(Boolean)
      .join('\n\n');

  if (group.group_mode === 'architecture') {
    // Organizations run top-down: a role starts once every role above it has finished.
    const queue = [root.id];
    const deferred: string[] = [];
    const readyAfterDrain = new Set<string>();
    while (queue.length || deferred.length) {
      if (!queue.length) {
        const pendingId = deferred.shift()!;
        const unresolved = incoming(pendingId).filter((edge) => !executed.has(edge.source) && visited.has(edge.source));
        if (unresolved.length)
          throw new Error(`架构节点「${byId.get(pendingId)?.title || pendingId}」存在未闭合的循环依赖。`);
        readyAfterDrain.add(pendingId);
        queue.push(pendingId);
      }
      if (++steps > stepLimit) throw new Error('架构超过安全执行步数，已停止。');
      const nodeId = queue.shift()!;
      if (executed.has(nodeId)) continue;
      const node = byId.get(nodeId);
      if (!node || node.type !== 'agent') continue;
      visited.add(nodeId);
      if (!readyAfterDrain.delete(nodeId) && incoming(nodeId).some((edge) => !executed.has(edge.source))) {
        deferred.push(nodeId);
        continue;
      }
      await invokeNode(node);
      executed.add(nodeId);
      outgoing(nodeId).forEach((edge) => {
        activeEdges.add(edgeKey(edge));
        queue.push(edge.target);
      });
    }
  } else {
    const queue: Array<{ nodeId: string; via?: WorkflowEdgeDefinition }> = [{ nodeId: root.id }];
    const deferred: Array<{ nodeId: string; via?: WorkflowEdgeDefinition }> = [];
    const readyAfterDrain = new Set<string>();
    while (queue.length || deferred.length) {
      if (!queue.length) {
        const pending = deferred.shift()!;
        const unresolved = incoming(pending.nodeId).filter(
          (edge) => !executed.has(edge.source) && visited.has(edge.source),
        );
        if (unresolved.length)
          throw new Error(
            `流程节点「${byId.get(pending.nodeId)?.title || pending.nodeId}」存在未闭合的循环依赖，请用循环节点表达回路。`,
          );
        readyAfterDrain.add(pending.nodeId);
        queue.push(pending);
      }
      if (++steps > stepLimit) throw new Error(`流程超过安全执行步数（${stepLimit}），已停止以防止死循环。`);
      const item = queue.shift()!;
      const nodeId = item.nodeId;
      const node = byId.get(nodeId);
      if (!node) continue;
      visited.add(nodeId);
      const isLoopReentry = item.via?.config?.sourceHandle === 'repeat' && byId.get(item.via.source)?.type === 'loop';
      if (node.type !== 'loop' && executed.has(nodeId) && !isLoopReentry) continue;
      if (!readyAfterDrain.delete(nodeId) && incoming(nodeId).some((edge) => !executed.has(edge.source))) {
        deferred.push(item);
        continue;
      }
      if (node.type === 'agent') {
        executed.add(nodeId);
        await invokeNode(node);
        outgoing(nodeId).forEach((edge) => {
          activeEdges.add(edgeKey(edge));
          queue.push({ nodeId: edge.target, via: edge });
        });
      } else if (node.type === 'condition') {
        const judgment = await evaluateControl(node);
        executed.add(nodeId);
        outputs.set(nodeId, upstreamSummary(nodeId));
        const handle = judgment.decision === 'YES' ? 'true' : 'false';
        const route = outgoing(nodeId).filter((edge) => edge.config?.sourceHandle === handle);
        if (!route.length)
          throw new Error(`判断节点「${node.title}」缺少“${judgment.decision === 'YES' ? '是' : '否'}”出口连线。`);
        deps.updateLog((old) =>
          old.map((entry) =>
            entry.title.startsWith(`${node.title} · 判断`)
              ? { ...entry, status: `选择${judgment.decision === 'YES' ? '是' : '否'}路径` }
              : entry,
          ),
        );
        route.forEach((edge) => {
          activeEdges.add(edgeKey(edge));
          queue.push({ nodeId: edge.target, via: edge });
        });
      } else if (node.type === 'loop') {
        const judgment = await evaluateControl(node);
        executed.add(nodeId);
        const upstreamResult = upstreamSummary(nodeId);
        const completedIterations = loopCount.get(nodeId) || 0;
        const maxIterations = Math.max(1, Math.min(20, Number(node.config?.max_iterations) || 3));
        const shouldRepeat = judgment.decision === 'NO' && completedIterations < maxIterations;
        const reachedLimit = judgment.decision === 'NO' && !shouldRepeat;
        const handle = shouldRepeat ? 'repeat' : 'exit';
        outputs.set(
          nodeId,
          shouldRepeat
            ? `${upstreamResult}\n\n循环判断说明：${judgment.reason}\n返回循环体的处理要求（第 ${completedIterations + 1} / ${maxIterations} 轮）：${judgment.feedback || ''}`
            : `${upstreamResult}\n\n循环退出说明：${judgment.reason}${reachedLimit ? `\n已达到最大总轮数（${maxIterations}），为避免无限循环而退出。` : ''}`,
        );
        const routeCandidates = outgoing(nodeId).filter((edge) =>
          handle === 'exit'
            ? ['exit', 'exit_top', 'exit_bottom'].includes(String(edge.config?.sourceHandle))
            : edge.config?.sourceHandle === handle,
        );
        const route = handle === 'exit' ? routeCandidates.slice(0, 1) : routeCandidates;
        if (!route.length)
          throw new Error(`循环节点「${node.title}」缺少“${shouldRepeat ? '循环' : '退出'}”出口连线。`);
        if (shouldRepeat) loopCount.set(nodeId, completedIterations + 1);
        deps.updateLog((old) =>
          old.map((entry) =>
            entry.title.startsWith(`${node.title} · 判断`)
              ? {
                  ...entry,
                  status: shouldRepeat
                    ? `继续循环：第 ${completedIterations + 1} / ${maxIterations} 轮`
                    : reachedLimit
                      ? `达到总轮数上限，退出循环`
                      : '退出循环',
                  ...(reachedLimit
                    ? { output: `${entry.output}\n已达到最大总轮数（${maxIterations}），为避免无限循环而退出。` }
                    : {}),
                }
              : entry,
          ),
        );
        route.forEach((edge) => {
          activeEdges.add(edgeKey(edge));
          queue.push({ nodeId: edge.target, via: edge });
        });
      } else throw new Error(`节点「${node.title}」的类型 ${node.type} 当前没有执行器。`);
    }
  }

  const finalReviewerNode = byId.get(executionOrder.at(-1) || root.id) || root;
  const finalAnswer = await invokeNode(finalReviewerNode, 'supervisor_review');
  if (!finalAnswer.trim()) throw new Error('Supervisor 没有生成最终答复，未向原对话写入空结果。');
  const nodes = finalizeNodes(sessions, runNodes);
  nodesRef.current = nodes;
  const skippedIds = new Set(nodes.filter((node) => node.status === 'skipped').map((node) => node.node_id));
  const skipped = allNodes.filter((node) => skippedIds.has(node.id));
  if (skipped.length)
    deps.updateLog((old) => [
      ...old,
      ...skipped.map((node) => ({ title: node.title, status: '已跳过', output: SKIPPED_OUTPUT })),
    ]);
  return { finalAnswer, finalReviewerTitle: finalReviewerNode.title, nodes };
}
