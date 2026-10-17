import React, { useEffect, useState } from 'react';
import { Activity, Clock3, RefreshCw, RotateCcw } from 'lucide-react';
import { fetchDraftContextStatus, fetchThreadContextStatus, rebirthGroupThreadContext, ThreadContextStatus } from '../../api/chatApi';
import { useChatStore } from '../../stores/chatStore';
import { IconButton } from '../common/IconButton';

export const ContextUsageIndicator: React.FC = () => {
  const threadId = useChatStore((state) => state.activeThreadId);
  const modelId = useChatStore((state) => state.selectedModel);
  const streaming = useChatStore((state) => state.isStreaming);
  const [status, setStatus] = useState<ThreadContextStatus | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [rebirthing, setRebirthing] = useState(false);
  const [actionError, setActionError] = useState('');

  const refresh = async () => {
    setLoading(true);
    try { setStatus(threadId ? await fetchThreadContextStatus(threadId, modelId) : await fetchDraftContextStatus(modelId)); }
    catch { setStatus(null); }
    finally { setLoading(false); }
  };

  const startNewContextEpoch = async () => {
    if (!threadId || rebirthing) return;
    setRebirthing(true);
    setActionError('');
    try {
      if (!threadId) return;
      await rebirthGroupThreadContext(threadId, modelId);
      await refresh();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : '换血失败');
    } finally { setRebirthing(false); }
  };

  useEffect(() => {
    let alive = true;
    // oxlint-disable-next-line react/set-state-in-effect -- Context usage is external state and must refresh for thread/model/stream changes.
    setLoading(true);
    const request = threadId ? fetchThreadContextStatus(threadId, modelId) : fetchDraftContextStatus(modelId);
    request.then((value) => { if (alive) setStatus(value); }).catch(() => { if (alive) setStatus(null); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [threadId, modelId, streaming]);

  const limit = status?.context_limit;
  const used = status?.used_tokens;
  const percent = status?.used_percent;

  return <div className="context-usage-wrap">
    <button className="context-usage-trigger" onClick={() => setOpen((value) => !value)} aria-expanded={open} title="查看对话上下文状态">
      <Activity size={13} />
      <span>上下文</span>
      <strong>{percent != null ? `${Math.round(percent)}%` : loading ? '…' : '—'}</strong>
    </button>
    {open && <div className="context-usage-popover">
      <div className="context-usage-heading"><div><Activity size={14} /><strong>对话上下文</strong></div><IconButton label="刷新上下文状态" onClick={() => (threadId ? fetchThreadContextStatus(threadId, modelId) : fetchDraftContextStatus(modelId)).then(setStatus)} size="sm"><RefreshCw size={13} /></IconButton></div>
      <div className="context-usage-stats">
        <div><span>窗口上限</span><strong>{limit != null ? `${limit.toLocaleString()} Token` : '暂不可用'}</strong></div>
        <div><span>已用</span><strong>{used != null ? `${used.toLocaleString()} Token` : '暂无用量'}</strong></div>
      </div>
      <div className="context-usage-source">{status?.model ? `${status.model} 上限：${limit != null ? `${limit.toLocaleString()} Token` : '暂不可用'}` : '模型上限：暂不可用'}</div>
      <div className="context-usage-progress-label"><span>使用量 / 上限</span><strong>{used != null && limit != null ? `${used.toLocaleString()} / ${limit.toLocaleString()} Token` : '暂无实际用量'}</strong></div>
      {percent != null && <div className="context-usage-meter"><span style={{ width: `${Math.min(100, Math.max(0, percent))}%` }} /></div>}
      <div className="context-usage-section-title"><Clock3 size={12} /> 压缩与换血记录</div>
      {status?.rebirth_logs.length ? <div className="context-usage-logs">{status.rebirth_logs.slice().reverse().map((log, index) => <div key={`${log.timestamp}-${index}`}><span>{log.kind}</span><p>{log.detail}</p><time>{log.timestamp ? new Date(log.timestamp * 1000).toLocaleString() : '时间未记录'}</time></div>)}</div> : <div className="context-usage-empty">暂无实际压缩或换血记录</div>}
      {status?.can_manual_rebirth && <div className="context-usage-rebirth">
        <button type="button" onClick={startNewContextEpoch} disabled={rebirthing || streaming} title={streaming ? '请先暂停或结束当前执行' : '归档当前上下文，并为此分组节点开启新的上下文阶段'}>
          <RotateCcw size={13} /> {rebirthing ? '正在整理并换血…' : '分组节点：手动换血'}
        </button>
        {actionError && <p role="alert">{actionError}</p>}
      </div>}
    </div>}
  </div>;
};
