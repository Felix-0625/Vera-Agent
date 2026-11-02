import { describe, expect, it } from 'vitest';
import type { Group, WorkflowEdgeDefinition, WorkflowNodeDefinition } from '../../types/project';
import {
  executeRun,
  finalizeNodes,
  parseWorkflowControlResult,
  type NodeTurnRequest,
  type RunLogEntry,
  type RunNodeState,
} from './workflowRunner';

type Reply = string | ((request: NodeTurnRequest, call: number) => string);

/** Build a run harness whose model replies are scripted per node thread. */
function harness(
  nodes: WorkflowNodeDefinition[],
  edges: WorkflowEdgeDefinition[],
  replies: Record<string, Reply>,
  mode: Group['group_mode'] = 'workflow',
) {
  const group: Group = { group_id: 'flow_test', name: 'test', group_mode: mode, nodes, edges };
  const sessions = nodes.map((node) => ({ node_id: node.id, thread_id: `th_${node.id}` }));
  const requests: NodeTurnRequest[] = [];
  const saves: RunNodeState[][] = [];
  let log: RunLogEntry[] = [];
  const calls = new Map<string, number>();
  const deps = {
    streamNode: async (request: NodeTurnRequest, onText: (output: string) => void) => {
      requests.push(request);
      const key = request.workflowStage === 'supervisor_review' ? 'supervisor' : request.threadId.slice(3);
      const call = (calls.get(key) || 0) + 1;
      calls.set(key, call);
      const reply = replies[key];
      if (reply === undefined) throw new Error(`unexpected call for ${key}`);
      onText(typeof reply === 'function' ? reply(request, call) : reply);
    },
    saveNodes: async (saved: RunNodeState[]) => {
      saves.push(saved);
    },
    updateLog: (update: (entries: RunLogEntry[]) => RunLogEntry[]) => {
      log = update(log);
    },
  };
  const nodesRef = { current: [] as RunNodeState[] };
  return {
    run: () => executeRun(group, sessions, 'task', deps, nodesRef),
    requests,
    saves,
    log: () => log,
    nodesRef,
    calls,
  };
}

const agentNode = (id: string): WorkflowNodeDefinition => ({ id, type: 'agent', title: id });
const yes = JSON.stringify({ decision: 'YES', reason: 'ok' });
const no = JSON.stringify({ decision: 'NO', reason: 'not yet', feedback: 'try again' });

describe('executeRun: condition branches', () => {
  const nodes = [
    agentNode('a'),
    { id: 'check', type: 'condition' as const, title: 'check', config: { expression: 'passes' } },
    agentNode('yes_path'),
    agentNode('no_path'),
  ];
  const edges: WorkflowEdgeDefinition[] = [
    { source: 'a', target: 'check' },
    { source: 'check', target: 'yes_path', config: { sourceHandle: 'true' } },
    { source: 'check', target: 'no_path', config: { sourceHandle: 'false' } },
  ];

  it('runs only the selected branch, skips the other, and keeps node outputs intact after review', async () => {
    const h = harness(nodes, edges, { a: 'A-OUT', check: no, yes_path: 'Y', no_path: 'N-OUT', supervisor: 'FINAL' });
    const outcome = await h.run();

    expect(outcome.finalAnswer).toBe('FINAL');
    const byId = Object.fromEntries(outcome.nodes.map((node) => [node.node_id, node]));
    expect(byId.yes_path.status).toBe('skipped');
    expect(byId.no_path).toMatchObject({ status: 'completed', output: 'N-OUT' });
    expect(byId.no_path.inputs?.map((input) => input.node_id)).not.toContain('no_path');
    expect(byId.check.output).toContain('判断结果：NO');
    const control = h.requests.find((request) => request.workflowStage === 'control_decision');
    expect(control?.workflowControl).toEqual({ type: 'condition', condition: 'passes' });
    expect(control?.workflowContext.upstream).toEqual([
      { node_id: 'a', title: 'a', relation: undefined, label: undefined, output: 'A-OUT' },
    ]);
  });

  it('stops with a clear error when the control node returns invalid JSON', async () => {
    const h = harness(nodes, edges, { a: 'A', check: 'maybe', supervisor: 'FINAL' });
    await expect(h.run()).rejects.toThrow('有效 JSON');
    expect(h.nodesRef.current.find((node) => node.node_id === 'check')?.status).toBe('failed');
  });
});

describe('executeRun: loops', () => {
  const nodes = [
    agentNode('writer'),
    { id: 'loop', type: 'loop' as const, title: 'loop', config: { max_iterations: 2, continue_condition: 'good' } },
    agentNode('end'),
  ];
  const edges: WorkflowEdgeDefinition[] = [
    { source: 'writer', target: 'loop', config: { targetHandle: 'input' } },
    { source: 'loop', target: 'writer', config: { sourceHandle: 'repeat' } },
    { source: 'loop', target: 'end', config: { sourceHandle: 'exit' } },
  ];

  it('repeats the loop body with feedback until YES', async () => {
    const h = harness(nodes, edges, {
      writer: (_r, call) => `draft ${call}`,
      loop: (_r, call) => (call === 1 ? no : yes),
      end: 'done',
      supervisor: 'FINAL',
    });
    await h.run();
    expect(h.calls.get('writer')).toBe(2);
    const secondWriter = h.requests.filter((request) => request.threadId === 'th_writer')[1];
    expect(secondWriter.workflowContext.upstream[0].output).toContain('try again');
  });

  it('exits after max_iterations even if the decision stays NO', async () => {
    const h = harness(nodes, edges, { writer: 'draft', loop: no, end: 'done', supervisor: 'FINAL' });
    const outcome = await h.run();
    expect(h.calls.get('writer')).toBe(3);
    expect(outcome.nodes.find((node) => node.node_id === 'end')?.status).toBe('completed');
    expect(h.log().some((entry) => entry.status === '达到总轮数上限，退出循环')).toBe(true);
  });
});

describe('executeRun: organizations', () => {
  it('runs roles top-down and passes the lead output to both reports', async () => {
    const nodes = [agentNode('lead'), agentNode('dev'), agentNode('qa')];
    const edges = [
      { source: 'lead', target: 'dev' },
      { source: 'lead', target: 'qa' },
    ];
    const h = harness(nodes, edges, { lead: 'PLAN', dev: 'CODE', qa: 'TESTS', supervisor: 'FINAL' }, 'architecture');
    const outcome = await h.run();
    expect(h.requests.map((request) => request.threadId)).toEqual(['th_lead', 'th_dev', 'th_qa', 'th_qa']);
    for (const id of ['dev', 'qa']) {
      expect(outcome.nodes.find((node) => node.node_id === id)?.inputs?.[0]).toMatchObject({
        node_id: 'lead',
        output: 'PLAN',
      });
    }
    const review = h.requests.at(-1)!;
    expect(review.workflowStage).toBe('supervisor_review');
    expect(review.workflowContext.upstream.map((input) => input.output)).toEqual(['PLAN', 'CODE', 'TESTS']);
  });

  it('rejects an instance without a root agent', async () => {
    const h = harness(
      [agentNode('a'), agentNode('b')],
      [
        { source: 'a', target: 'b' },
        { source: 'b', target: 'a' },
      ],
      {},
    );
    await expect(h.run()).rejects.toThrow('起始对话窗口');
  });
});

describe('helpers', () => {
  it('requires feedback for a NO loop decision', () => {
    expect(() => parseWorkflowControlResult(JSON.stringify({ decision: 'NO', reason: 'x' }), 'loop')).toThrow(
      'feedback',
    );
    expect(parseWorkflowControlResult(JSON.stringify({ decision: 'NO', reason: ' x ' }), 'condition')).toEqual({
      decision: 'NO',
      reason: 'x',
    });
  });

  it('marks never-started nodes as skipped', () => {
    const nodes = finalizeNodes(
      [
        { node_id: 'a', thread_id: 't' },
        { node_id: 'b', thread_id: 't2' },
      ],
      [{ node_id: 'a', status: 'completed', output: 'x' }],
    );
    expect(nodes.map((node) => node.status)).toEqual(['completed', 'skipped']);
  });
});
