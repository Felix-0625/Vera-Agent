import { ReactFlowProvider } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { ArrowLeft, GitBranch, GitCommitHorizontal, Maximize2, Plus, RefreshCw } from 'lucide-react';
import { Button } from '../common/Button';
import { EmptyState } from '../common/EmptyState';
import { TextInput } from '../common/Field';
import { IconButton } from '../common/IconButton';
import './gitflow.css';
import { branchColor, branchCommits, modal, modalBackdrop } from './gitFlowGraph';
import { CommitEntry, GraphCanvas } from './GitFlowTabParts';
import { useGitFlowTab } from './useGitFlowTab';
export function GitFlowTabView({
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
}: ReturnType<typeof useGitFlowTab>) {
  return (
    <div
      style={{
        height: '100%',
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        color: 'var(--text-primary)',
        background: 'var(--bg-workspace)',
      }}
    >
      <header
        style={{
          padding: 'var(--space-3) var(--space-4)',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--space-3)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2-25)', minWidth: 0 }}>
          <span
            style={{
              width: 30,
              height: 30,
              display: 'grid',
              placeItems: 'center',
              borderRadius: 'var(--radius-md-plus)',
              color: 'var(--accent-primary)',
              background: 'color-mix(in srgb, var(--accent-primary) 9%, var(--bg-surface))',
            }}
          >
            <GitBranch size={16} />
          </span>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 'var(--font-size-md)', fontWeight: 650 }}>GitFlow</div>
            <div
              style={{
                color: 'var(--text-muted)',
                fontSize: 'var(--font-size-xs)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {topology?.repo_name || '分支工作流'}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-1-75)', alignItems: 'center' }}>
          {topology?.is_git !== false && topology && (
            <span
              style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)', marginRight: 'var(--space-0-75)' }}
            >
              HEAD · <b style={{ color: 'var(--accent-emerald)' }}>{topology.current_branch}</b>
            </span>
          )}
          {topology?.is_git !== false && (
            <Button
              disabled={!projectId || busy || !topology}
              onClick={() => setShowCreate(true)}
              variant="primary"
              size="sm"
              className="gitflow-action"
              icon={<Plus size={13} aria-hidden="true" />}
            >
              新建分支
            </Button>
          )}
          <IconButton label="刷新拓扑" title="刷新拓扑" onClick={() => void loadData()} disabled={loading} size="sm">
            <RefreshCw size={14} className={loading ? 'pulse-glow' : ''} />
          </IconButton>
        </div>
      </header>
      {error && (
        <div
          style={{
            padding: 'var(--space-1-75) var(--space-3-5)',
            color: 'var(--accent-rose)',
            background: 'color-mix(in srgb, var(--accent-rose) 8%, var(--bg-surface))',
            fontSize: 'var(--font-size-compact)',
          }}
        >
          {error}
        </div>
      )}
      {!projectId ? (
        <EmptyState
          className="gitflow-empty-state"
          icon={<GitBranch size={24} />}
          title="此对话未绑定项目"
          description="GitFlow 是项目级工具，请先为对话选择项目。"
        />
      ) : !topology && loading ? (
        <EmptyState className="gitflow-empty-state" title="正在读取项目仓库…" />
      ) : topology ? (
        <>
          {topology.is_git === false ? (
            <EmptyState
              className="gitflow-empty-state"
              icon={<GitBranch size={25} />}
              title="此项目目录不是 Git 仓库"
              description="当前目录没有 Git 分支和提交记录。"
            />
          ) : (
            <>
              <div className="gitflow-subtabs">
                <button className={view === 'local' ? 'active' : ''} onClick={() => setView('local')}>
                  本地分支 <span>{topology.branches.filter((branch) => !branch.is_remote).length}</span>
                </button>
                <button className={view === 'remote' ? 'active' : ''} onClick={() => setView('remote')}>
                  远程状态 <span>{topology.branches.filter((branch) => branch.is_remote).length}</span>
                </button>
              </div>
              {view === 'local' ? (
                <>
                  <div className="gitflow-topology-title">
                    <div>
                      <strong>本地分支关系</strong>
                      <span>仅显示仓库现有分支；拖动节点可调整位置。</span>
                    </div>
                    <span className="gitflow-branch-total">
                      {topology.branches.filter((branch) => !branch.is_remote).length} 个分支
                    </span>
                  </div>
                  {topology.branches.some((branch) => !branch.is_remote) ? (
                    <div className="gitflow-graph-frame">
                      <ReactFlowProvider>
                        <GraphCanvas
                          topology={topology}
                          layoutScope={projectId}
                          selectedBranch={selectedBranch}
                          onSelectBranch={selectBranch}
                          onOpenBranch={openBranch}
                        />
                      </ReactFlowProvider>
                    </div>
                  ) : (
                    <EmptyState
                      className="gitflow-empty-state"
                      icon={<GitBranch size={24} />}
                      title="仓库还没有分支"
                      description="创建首个提交后，Git 才会生成可展示的分支。"
                    />
                  )}
                  {selectedBranch && !selectedBranch.is_remote ? (
                    <>
                      <div className="gitflow-commit-heading">
                        <div>
                          <GitCommitHorizontal size={14} />
                          <b>{selectedBranch.name} · 提交记录</b>
                        </div>
                        <IconButton onClick={() => openBranch(selectedBranch)} label="查看分支操作" size="sm">
                          <Maximize2 size={13} />
                        </IconButton>
                      </div>
                      <div className="gitflow-commit-list">
                        {commitsForBranch.length ? (
                          commitsForBranch
                            .slice(0, 4)
                            .map((commit) => <CommitEntry commit={commit} compact key={commit.hash} />)
                        ) : (
                          <div className="gitflow-no-commits">此分支暂无可读取的提交记录</div>
                        )}
                      </div>
                    </>
                  ) : (
                    <div className="gitflow-no-commits">选择本地分支查看提交记录</div>
                  )}
                </>
              ) : (
                <div className="gitflow-remote-list">
                  {topology.branches.filter((branch) => branch.is_remote).length ? (
                    topology.branches
                      .filter((branch) => branch.is_remote)
                      .map((branch) => {
                        const local = topology.branches.find(
                          (candidate) =>
                            !candidate.is_remote &&
                            (candidate.upstream === branch.name || branch.name === `origin/${candidate.name}`),
                        );
                        const localCommits = local ? branchCommits(local, topology.commits) : [];
                        const remoteCommits = branchCommits(branch, topology.commits);
                        const ahead =
                          local?.ahead ??
                          localCommits.filter(
                            (commit) => !remoteCommits.some((remoteCommit) => remoteCommit.hash === commit.hash),
                          ).length;
                        const behind =
                          local?.behind ??
                          remoteCommits.filter(
                            (commit) => !localCommits.some((localCommit) => localCommit.hash === commit.hash),
                          ).length;
                        return (
                          <button
                            key={branch.name}
                            className="gitflow-remote-row"
                            onClick={() => setSelectedBranch(branch)}
                          >
                            <GitBranch size={14} />
                            <strong>{branch.name}</strong>
                            <span>
                              {local ? `关联 ${local.name} · 未推送 ${ahead} · 待拉取 ${behind}` : '远程跟踪引用'}
                            </span>
                            <code>{branch.head?.slice(0, 8)}</code>
                          </button>
                        );
                      })
                  ) : (
                    <EmptyState
                      className="gitflow-empty-state"
                      icon={<GitBranch size={24} />}
                      title="暂无远程分支引用"
                      description="此页只列出本地仓库已获取的远程跟踪分支。"
                    />
                  )}
                </div>
              )}
            </>
          )}
        </>
      ) : (
        <EmptyState
          className="gitflow-empty-state"
          icon={<GitBranch size={25} />}
          title="无法读取仓库"
          description={error || '检查项目目录和 Git 仓库状态。'}
        />
      )}
      {detailBranch && topology && (
        <div
          style={modalBackdrop}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setDetailBranch(null);
          }}
        >
          <section style={modal} role="dialog" aria-modal="true" aria-label={`${detailBranch.name} 分支详情`}>
            <div className="gitflow-detail-header">
              <IconButton onClick={() => setDetailBranch(null)} label="返回" size="sm">
                <ArrowLeft size={16} />
              </IconButton>
              <div>
                <strong style={{ color: branchColor(detailBranch.name) }}>{detailBranch.name}</strong>
                <small>
                  {detailBranch.is_current ? '当前分支' : detailBranch.is_remote ? '远程跟踪分支' : '本地分支'}
                  {detailBranch.head ? ` · HEAD ${detailBranch.head.slice(0, 8)}` : ''}
                </small>
              </div>
              <GitBranch size={18} color="var(--accent-primary)" />
            </div>
            <div className="gitflow-detail-section">
              <b>分支操作</b>
              {branchActions(detailBranch)}
              {reviewResult && (
                <p className={reviewResult.has_conflict ? 'gitflow-review-error' : 'gitflow-review-ok'}>
                  {reviewResult.summary}
                </p>
              )}
            </div>
            <div className="gitflow-detail-section">
              <b>
                提交记录 <span>{detailCommits.length} · 合并提交标注父提交关系</span>
              </b>
              <div className="gitflow-detail-commits">
                {detailCommits.length ? (
                  detailCommits.map((commit) => <CommitEntry commit={commit} key={commit.hash} />)
                ) : (
                  <div className="gitflow-no-commits">此分支暂无可读取的提交记录</div>
                )}
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button onClick={() => setDetailBranch(null)} variant="secondary" size="sm" className="gitflow-action">
                完成
              </Button>
            </div>
          </section>
        </div>
      )}
      {showCreate && (
        <div
          style={modalBackdrop}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setShowCreate(false);
          }}
        >
          <form onSubmit={handleCreate} style={{ ...modal, width: 320 }}>
            <b style={{ fontSize: 'var(--font-size-body)' }}>新建分支</b>
            <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)' }}>
              从当前分支 {topology?.current_branch || 'HEAD'} 创建
            </span>
            <TextInput
              autoFocus
              value={branchName}
              onChange={(event) => setBranchName(event.target.value)}
              placeholder="feature/your-branch"
              className="gitflow-branch-name-input"
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
              <Button
                type="button"
                onClick={() => setShowCreate(false)}
                variant="secondary"
                size="sm"
                className="gitflow-action"
              >
                取消
              </Button>
              <Button
                type="submit"
                disabled={!branchName.trim() || busy}
                variant="primary"
                size="sm"
                className="gitflow-action"
              >
                创建分支
              </Button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
