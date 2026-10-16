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
  const [preview, setPreview] = useState<FilePreviewData | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!path || !projectId) {
      setPreview(null);
      setError('');
      return;
    }
    let disposed = false;
    setPreview(null);
    setError('');
    fetchFilePreview(path, groupId || undefined, projectId || undefined).then((data) => { if (!disposed) setPreview(data); }).catch((cause: unknown) => {
      if (!disposed) setError(cause instanceof Error ? cause.message : '文件预览失败');
    });
    return () => { disposed = true; };
  }, [groupId, path, projectId]);

  if (!projectId) return <div style={{ padding: 'var(--space-5)', color: 'var(--text-muted)' }}>当前对话未绑定项目，无法打开项目文件。</div>;
  if (!path) return <div style={{ padding: 'var(--space-5)', color: 'var(--text-muted)' }}>没有指定文件。</div>;
  if (error) return <div role="alert" style={{ padding: 'var(--space-5)', color: 'var(--accent-rose)' }}>{error}</div>;
  if (!preview) return <div style={{ padding: 'var(--space-5)', color: 'var(--text-muted)' }}>正在打开 {path}…</div>;
  return <FilePreviewPane file={{ path, name: path.split(/[\\/]/).pop() || path, preview }} projectKey={projectKey} projectId={projectId} groupId={groupId} embedded />;
};
