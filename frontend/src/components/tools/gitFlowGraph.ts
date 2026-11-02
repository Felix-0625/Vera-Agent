import { Edge, MarkerType, Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import React from 'react';
import { BranchInfo, GitCommitInfo, GitFlowTopology } from '../../types/tool';
import './gitflow.css';
export type BranchNodeData = {
  branch: BranchInfo;
  onSelect: (branch: BranchInfo) => void;
  onOpen: (branch: BranchInfo) => void;
};
export type FlowNode = Node<BranchNodeData>;
export const branchColor = (name: string) =>
  name === 'main' || name === 'master'
    ? 'var(--accent-primary)'
    : name === 'develop' || name === 'development'
      ? 'var(--accent-cyan)'
      : name.startsWith('feature/') || name.startsWith('feat/')
        ? 'var(--accent-emerald)'
        : name.startsWith('release/')
          ? 'var(--accent-amber)'
          : name.startsWith('hotfix/')
            ? 'var(--accent-rose)'
            : 'var(--text-muted)';
export function buildGraph(
  topology: GitFlowTopology,
  onSelect: (branch: BranchInfo) => void,
  onOpen: (branch: BranchInfo) => void,
  saved: Record<string, { x: number; y: number }> = {},
) {
  const branches = topology.branches.filter((branch) => !branch.is_remote);
  const byName = new Map(branches.map((branch) => [branch.name, branch]));
  const commitByHash = new Map(topology.commits.map((commit) => [commit.hash, commit]));
  const ancestorCache = new Map<string, Set<string>>();
  const ancestors = (head?: string): Set<string> => {
    if (!head) return new Set();
    const known = ancestorCache.get(head);
    if (known) return known;
    const found = new Set<string>();
    const pending = [head];
    while (pending.length) {
      const hash = pending.pop()!;
      if (found.has(hash)) continue;
      found.add(hash);
      pending.push(...(commitByHash.get(hash)?.parents || []));
    }
    ancestorCache.set(head, found);
    return found;
  };
  const roots = branches.filter((branch) => branch.name === 'main' || branch.name === 'master');
  const parentOf = (branch: BranchInfo): string | undefined => {
    if (branch.parent && byName.has(branch.parent)) return branch.parent;
    const lower = branch.name.toLowerCase();
    const candidates =
      lower === 'develop' || lower === 'development'
        ? roots
        : /^(feature|feat|bugfix|fix|release)\//.test(lower)
          ? branches.filter((candidate) => /^(develop|development)$/i.test(candidate.name))
          : lower.startsWith('hotfix/')
            ? roots
            : [];
    const childAncestors = ancestors(branch.head);
    return candidates.find(
      (parent) => parent.name !== branch.name && [...childAncestors].some((hash) => ancestors(parent.head).has(hash)),
    )?.name;
  };
  const parentByName = new Map(branches.map((branch) => [branch.name, parentOf(branch)]));
  const children = new Map<string, BranchInfo[]>();
  branches.forEach((branch) => {
    const parent = parentByName.get(branch.name);
    if (parent && byName.has(parent)) children.set(parent, [...(children.get(parent) || []), branch]);
  });
  const treeRoots = branches
    .filter((branch) => !parentByName.get(branch.name) || !byName.has(parentByName.get(branch.name)!))
    .sort((a, b) => Number(b.is_current) - Number(a.is_current) || a.name.localeCompare(b.name));
  const positions: Record<string, { x: number; y: number }> = {};
  let nextLeafX = 0;
  const place = (branch: BranchInfo, y: number): number => {
    const childList = (children.get(branch.name) || []).sort((a, b) => a.name.localeCompare(b.name));
    if (childList.length === 0) {
      const x = nextLeafX;
      nextLeafX += 250;
      positions[branch.name] = { x, y };
      return x;
    }
    const childXs = childList.map((child) => place(child, y + 116));
    const x = (childXs[0] + childXs[childXs.length - 1]) / 2;
    positions[branch.name] = { x, y };
    return x;
  };
  treeRoots.forEach((root) => {
    place(root, 24);
  });
  const nodes: FlowNode[] = branches.map((branch) => ({
    id: branch.name,
    type: 'branch',
    position: saved[branch.name] || positions[branch.name] || { x: 0, y: 24 },
    data: { branch, onSelect, onOpen },
    draggable: true,
    selected: branch.name === topology.current_branch,
  }));
  const edges: Edge[] = branches
    .filter((branch) => parentByName.get(branch.name) && byName.has(parentByName.get(branch.name)!))
    .map((branch) => ({
      id: `${parentByName.get(branch.name)}->${branch.name}`,
      source: parentByName.get(branch.name)!,
      target: branch.name,
      type: 'smoothstep',
      sourceHandle: 'bottom',
      targetHandle: 'top',
      markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--text-muted)' },
      style: { stroke: 'var(--text-muted)', strokeWidth: 1.5 },
    }));
  return { nodes, edges };
}
export function branchCommits(branch: BranchInfo, commits: GitCommitInfo[]): GitCommitInfo[] {
  if (!branch.head) return [];
  const byHash = new Map(commits.map((commit) => [commit.hash, commit]));
  const visited = new Set<string>();
  const stack = [branch.head];
  while (stack.length) {
    const hash = stack.pop()!;
    if (visited.has(hash)) continue;
    visited.add(hash);
    const commit = byHash.get(hash);
    if (commit) stack.push(...commit.parents);
  }
  return commits.filter((commit) => visited.has(commit.hash));
}
export const modalBackdrop: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 30,
  display: 'grid',
  placeItems: 'center',
  background: 'var(--overlay-scrim)',
};
export const modal: React.CSSProperties = {
  width: 'min(620px, calc(100vw - 32px))',
  maxHeight: 'min(760px, calc(100vh - 32px))',
  display: 'flex',
  flexDirection: 'column',
  gap: 'var(--space-3-5)',
  padding: 'var(--space-5)',
  border: '1px solid var(--border-default)',
  borderRadius: 'var(--radius-lg-plus)',
  background: 'var(--bg-surface-elevated)',
  boxShadow: 'var(--shadow-lg)',
  overflow: 'auto',
};
