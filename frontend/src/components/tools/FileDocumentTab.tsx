import React, { useEffect, useState } from 'react';
import { fetchFilePreview } from '../../api/toolApi';
import { FilePreviewData } from '../../types/tool';
import { FilePreviewPane } from './FilePreviewPane';
import { useChatStore } from '../../stores/chatStore';

export const FileDocumentTab: React.FC<{ path?: string; projectId?: string | null }> = ({ path, projectId: projectIdOverride }) => {
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const threads = useChatStore((state) => state.threads);
  const draftProjectId = useChatStore((state) => state.draftProjectId);
  const projectId = projectIdOverride !== undefined ? projectIdOverride : activeThreadId ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id || null : draftProjectId;
  const groupId = undefined;
  const projectKey = projectId || 'workspace';
  const [loadedPreview, setLoadedPreview] = useState<{ key: string; preview: FilePreviewData } | null>(null);
  const [loadFailure, setLoadFailure] = useState<{ key: string; message: string } | null>(null);
  const requestKey = `${projectId || ''}:${path || ''}`;
  useEffect(() => {
    if (!path || !projectId) return;
    let disposed = false;
    fetchFilePreview(path, groupId || undefined, projectId || undefined).then((data) => { if (!disposed) setLoadedPreview({ key: requestKey, preview: data }); }).catch((cause: unknown) => {
      if (!disposed) setLoadFailure({ key: requestKey, message: cause instanceof Error ? cause.message : '文件预览失败' });
    });
    return () => { disposed = true; };
  }, [groupId, path, projectId, requestKey]);

  if (!projectId) return <div style={{ padding: 'var(--space-5)', color: 'var(--text-muted)' }}>当前对话未绑定项目，无法打开项目文件。</div>;
  if (!path) return <div style={{ padding: 'var(--space-5)', color: 'var(--text-muted)' }}>没有指定文件。</div>;
  if (loadFailure?.key === requestKey) return <div role="alert" style={{ padding: 'var(--space-5)', color: 'var(--accent-rose)' }}>{loadFailure.message}</div>;
  if (loadedPreview?.key !== requestKey) return <div style={{ padding: 'var(--space-5)', color: 'var(--text-muted)' }}>正在打开 {path}…</div>;
  return <FilePreviewPane key={path} file={{ path, name: path.split(/[\\/]/).pop() || path, preview: loadedPreview.preview }} projectKey={projectKey} projectId={projectId} groupId={groupId} embedded />;
};
