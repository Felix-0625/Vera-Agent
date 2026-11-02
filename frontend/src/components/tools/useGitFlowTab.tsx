import '@xyflow/react/dist/style.css';
import { GitMerge, Trash2 } from 'lucide-react';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  checkoutBranch,
  createBranch,
  deleteBranch,
  fetchGitFlowTopology,
  mergeBranch,
  requestMergeReview,
} from '../../api/toolApi';
import { useChatStore } from '../../stores/chatStore';
import { BranchInfo, GitFlowTopology } from '../../types/tool';
import { Button } from '../common/Button';
import './gitflow.css';

import { branchCommits } from './gitFlowGraph';
export function useGitFlowTab({ projectId: projectIdOverride }: { projectId?: string | null }) {
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const threads = useChatStore((state) => state.threads);
  const draftProjectId = useChatStore((state) => state.draftProjectId);
  const projectId =
    projectIdOverride !== undefined
      ? projectIdOverride || undefined
      : activeThreadId
        ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id || undefined
        : draftProjectId || undefined;
  const [topology, setTopology] = useState<GitFlowTopology | null>(null);
  const [selectedBranch, setSelectedBranch] = useState<BranchInfo | null>(null);
  const [detailBranch, setDetailBranch] = useState<BranchInfo | null>(null);
  const [reviewResult, setReviewResult] = useState<{ has_conflict: boolean; summary: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [branchName, setBranchName] = useState('');
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState<'local' | 'remote'>('local');
  const loadData = useCallback(async () => {
    if (!projectId) {
      setTopology(null);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const result = await fetchGitFlowTopology(projectId);
      setTopology(result);
      setSelectedBranch((current) =>
        current
          ? result.branches.find((branch) => branch.name === current.name) ||
            result.branches.find((branch) => branch.is_current) ||
            null
          : result.branches.find((branch) => branch.is_current) || null,
      );
      setDetailBranch((current) =>
        current ? result.branches.find((branch) => branch.name === current.name) || null : null,
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setLoading(false);
    }
  }, [projectId]);
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- Refresh Git topology when the conversation's project changes.
    void loadData();
  }, [loadData]);
  const runAction = async (action: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await action();
      await loadData();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  };
  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!branchName.trim() || !projectId) return;
    await runAction(() => createBranch(branchName.trim(), topology?.current_branch || 'HEAD', projectId));
    setBranchName('');
    setShowCreate(false);
  };
  const selectBranch = useCallback((branch: BranchInfo) => {
    setSelectedBranch(branch);
    setReviewResult(null);
  }, []);
  const openBranch = useCallback(
    (branch: BranchInfo) => {
      selectBranch(branch);
      setDetailBranch(branch);
    },
    [selectBranch],
  );
  const commitsForBranch = useMemo(
    () => (selectedBranch && topology ? branchCommits(selectedBranch, topology.commits) : []),
    [selectedBranch, topology],
  );
  const detailCommits = useMemo(
    () => (detailBranch && topology ? branchCommits(detailBranch, topology.commits) : []),
    [detailBranch, topology],
  );
  const branchActions = (branch: BranchInfo) => (
    <div className="gitflow-detail-actions">
      {!branch.is_current && !branch.is_remote && (
        <Button
          disabled={busy}
          onClick={() => void runAction(() => checkoutBranch(branch.name, projectId!))}
          variant="secondary"
          size="sm"
          className="gitflow-action"
        >
          切换到此分支
        </Button>
      )}
      {!branch.is_current && !branch.is_remote && (
        <Button
          disabled={busy}
          onClick={() => {
            if (window.confirm(`将 ${branch.name} 合并到 ${topology?.current_branch}？`))
              void runAction(() => mergeBranch(branch.name, projectId!));
          }}
          variant="secondary"
          size="sm"
          className="gitflow-action"
          icon={<GitMerge size={12} aria-hidden="true" />}
        >
          合并到当前分支
        </Button>
      )}
      {!branch.is_current && !branch.is_remote && (
        <Button
          disabled={busy}
          onClick={() =>
            void runAction(async () =>
              setReviewResult(await requestMergeReview(branch.name, topology!.current_branch, projectId!)),
            )
          }
          variant="secondary"
          size="sm"
          className="gitflow-action"
        >
          合并审查
        </Button>
      )}
      {!branch.is_current && !branch.is_remote && (
        <Button
          disabled={busy}
          onClick={() => {
            if (window.confirm(`安全删除已合并分支 ${branch.name}？`))
              void runAction(() => deleteBranch(branch.name, projectId!));
          }}
          variant="danger"
          size="sm"
          className="gitflow-action"
          icon={<Trash2 size={12} aria-hidden="true" />}
        >
          安全删除
        </Button>
      )}
    </div>
  );
  return {
    projectId,
    topology,
    selectedBranch,
    setSelectedBranch,
    detailBranch,
    setDetailBranch,
    reviewResult,
    loading,
    error,
    showCreate,
    setShowCreate,
    branchName,
    setBranchName,
    busy,
    view,
    setView,
    loadData,
    handleCreate,
    selectBranch,
    openBranch,
    commitsForBranch,
    detailCommits,
    branchActions,
  };
}
