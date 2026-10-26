import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import type { WorkflowEdgeDefinition, WorkflowNodeDefinition } from '../../types/project';
import { executeRun } from './workflowRunner';

/** Parse BUILTIN_TEMPLATES from session/templates.py (role keys, topology type, edges). */
function builtinTemplates() {
  const path = fileURLToPath(new URL('../../../../vera-agent/src/vera_agent/session/templates.py', import.meta.url));
  const source = readFileSync(path, 'utf-8');
  return [...source.matchAll(/template_id="(\w+)"[\s\S]*?topology_type="(\w+)"([\s\S]*?)edges=\[([\s\S]*?)\]\s*,\s*\)/g)].map((match) => ({
    id: match[1],
    mode: match[2] as 'workflow' | 'architecture',
    nodes: [...match[3].matchAll(/role_key="(\w+)"/g)].map((node) => node[1]),
    edges: [...match[4].matchAll(/source_role="(\w+)", target_role="(\w+)"/g)].map((edge) => ({ source: edge[1], target: edge[2] })),
  }));
}

describe('built-in templates run in the scheduler', () => {
  const templates = builtinTemplates();
  it('finds all four built-in templates', () => expect(templates.map((t) => t.id)).toEqual(['supervisor_dev', 'sequential_workflow', 'adversarial_audit', 'swarm_mesh']));
  for (const template of templates) {
    it(`${template.id} (${template.mode}) runs every node once and reaches the Supervisor`, async () => {
      const nodes: WorkflowNodeDefinition[] = template.nodes.map((id) => ({ id, type: 'agent', title: id }));
      const edges: WorkflowEdgeDefinition[] = template.edges;
      const called: string[] = [];
      const outcome = await executeRun(
        { group_id: 'g', name: template.id, group_mode: template.mode, nodes, edges },
        template.nodes.map((id) => ({ node_id: id, thread_id: id })),
        'task',
        { streamNode: async (request, onText) => { called.push(request.workflowStage || request.threadId); onText(`out:${request.threadId}`); }, saveNodes: async () => {}, updateLog: () => {} },
        { current: [] },
      );
      expect(called.filter((call) => call !== 'supervisor_review').sort()).toEqual([...template.nodes].sort());
      expect(called.at(-1)).toBe('supervisor_review');
      expect(outcome.nodes.every((node) => node.status === 'completed')).toBe(true);
    });
  }
});
