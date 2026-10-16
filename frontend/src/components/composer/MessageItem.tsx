import React, { useState } from 'react';
import { Check, ChevronDown, ChevronRight, Copy, FileCode, LoaderCircle, MessageCircleMore, Pencil, Terminal } from 'lucide-react';
import { ChatMessage } from '../../types/chat';
import { MarkdownContent } from './MarkdownContent';
import { TextArea } from '../common/Field';

interface MessageItemProps {
  message: ChatMessage;
  isStreaming?: boolean;
  streamLabel?: string;
  onAskDetails?: (message: ChatMessage) => void;
  onEditMessage?: (message: ChatMessage, content: string) => Promise<void>;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message, isStreaming = false, streamLabel, onAskDetails, onEditMessage }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const [thinkingExpanded, setThinkingExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editedText, setEditedText] = useState(message.content);
  const toolActivityEntries = (message.extra?.activity || []).filter((event) =>
    event.label !== '分析请求' && !/^执行步骤\s*\d+$/.test(event.label),
  );
  const childActivityEntries = (message.extra?.subagents || []).flatMap((run) => run.activities.map((activity, index) => ({
    id: `${run.id}-activity-${index}`,
    kind: 'tool' as const,
    label: `${run.title} · ${activity.label}`,
    detail: activity.detail,
    status: activity.status === 'working' ? 'working' as const : activity.status === 'error' ? 'error' as const : 'done' as const,
  })));
  const activityEntries = [...toolActivityEntries, ...childActivityEntries];

  const copyAnswer = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  };

  if (isSystem) {
    return (
      <div style={{ padding: 'var(--space-2) var(--space-3)', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--bg-danger-soft)', color: 'var(--accent-rose)', fontSize: 'var(--font-size-sm)', margin: 'var(--space-2) 0' }}>
        {message.content}
      </div>
    );
  }

  return (
    <div
      className={isUser ? 'user-message-row' : undefined}
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        padding: 'var(--space-2-25) 0',
        width: '100%',
      }}
    >
      <div
        style={{
          width: isUser ? '78%' : '100%',
          maxWidth: isUser ? '680px' : '100%',
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: isUser ? 'flex-end' : 'flex-start',
          gap: 'var(--space-1-75)',
        }}
      >
        {!isUser && (isStreaming || message.extra?.duration !== undefined || Boolean(activityEntries.length)) && (
          <div className="assistant-process">
            <button className="assistant-process-toggle" type="button" aria-expanded={thinkingExpanded} onClick={() => setThinkingExpanded((expanded) => !expanded)}>
              {isStreaming && <LoaderCircle size={13} className="assistant-process-spinner" />}
              <span>{isStreaming ? (streamLabel || 'Thinking…') : message.extra?.duration === undefined ? '未完成' : `用时 ${formatDuration(message.extra.duration)}`}</span>
              {thinkingExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
            <div className="assistant-process-divider" />
            {thinkingExpanded && Boolean(activityEntries.length) && (
              <div className="assistant-process-list">
                {activityEntries.map((event) => (
                  <div className="assistant-process-item" key={event.id}>
                    {event.status === 'working' ? <LoaderCircle size={13} className="assistant-process-spinner" /> : <span className={`assistant-process-dot ${event.status}`} />}
                    <span className="assistant-process-label">{formatActivityLabel(event.label)}</span>
                    {event.detail && <span className="assistant-process-detail">{event.detail}</span>}
                  </div>
                ))}
              </div>
            )}
            {thinkingExpanded && isStreaming && !activityEntries.length && (
              <div className="assistant-process-empty">只展示模型连接、工具调用和执行状态，不展示模型的私有思维链。</div>
            )}
          </div>
        )}
        <div className={isUser ? `user-message-bubble${editing ? ' user-message-editing' : ''}` : undefined} style={isUser ? { width: '100%' } : undefined}>
        {/* Extra triggers if user */}
        {isUser && message.extra?.rule_trigger && (
          <div style={{ display: 'inline-flex' }}>
            <span
              style={{
                fontSize: 'var(--font-size-compact)',
                padding: 'var(--space-0-5) var(--space-2)',
                borderRadius: 'var(--radius-full)',
                backgroundColor: 'var(--bg-accent-soft)',
                color: 'var(--accent-primary)',
              }}
            >
              /{message.extra.rule_trigger} 模式
            </span>
          </div>
        )}

        {isUser && message.extra?.images?.length ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
            {message.extra.images.map((image) => <img key={image.id} src={image.data_url} alt={image.name} style={{ maxWidth: 320, maxHeight: 260, objectFit: 'contain', borderRadius: 'var(--radius-md-wide)', border: '1px solid var(--border-subtle)', background: 'var(--bg-card)' }} />)}
          </div>
        ) : null}

        {/* Text body */}
        <div
          style={{
            fontSize: 'var(--font-size-subheading)',
            lineHeight: 1.6,
            color: 'var(--text-primary)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            width: '100%',
            textAlign: 'left',
          }}
        >
          {isUser ? (editing ? <TextArea autoFocus value={editedText} onChange={(event) => setEditedText(event.target.value)} aria-label="编辑用户消息" className="user-message-edit-input" /> : message.content) : <MarkdownContent content={message.content} />}
        </div>
        {isUser && editing && <div className="user-message-edit-actions">
          <button type="button" onClick={() => { setEditedText(message.content); setEditing(false); }}>取消</button>
          <button type="button" disabled={!editedText.trim() || !onEditMessage} onClick={() => { if (onEditMessage && editedText.trim()) void onEditMessage(message, editedText.trim()).then(() => setEditing(false)); }}>发送</button>
        </div>}
        </div>

        {/* Tool actions list if present */}
        {message.extra?.actions && message.extra.actions.length > 0 && (
          <div style={{ marginTop: 'var(--space-1-5)', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
            {message.extra.actions.map((act, idx) => (
              <div
                key={idx}
                style={{
                  padding: 'var(--space-1-5) var(--space-2-5)',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: 'var(--font-size-sm)',
                  fontFamily: 'monospace',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-2)',
                }}
              >
                {act.tool_name === 'bash' ? <Terminal size={14} color="var(--accent-amber)" /> : <FileCode size={14} color="var(--accent-cyan)" />}
                <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>
                  {act.tool_name}:
                </span>
                <span style={{ color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {JSON.stringify(act)}
                </span>
              </div>
            ))}
          </div>
        )}

        {!isUser && !isStreaming && Boolean(message.content) && (
          <div className="assistant-message-actions">
            <button type="button" className="assistant-message-action" onClick={() => void copyAnswer()} title={copied ? '已复制回答' : '复制回答'} aria-label={copied ? '已复制回答' : '复制回答'}>
              {copied ? <Check size={14} /> : <Copy size={14} />}
              <span>{copied ? '已复制' : '复制'}</span>
            </button>
            {onAskDetails && <button type="button" className="assistant-message-action" onClick={() => onAskDetails(message)} title="在侧边对话中询问细节" aria-label="在侧边对话中询问细节"><MessageCircleMore size={14} /><span>询问细节</span></button>}
          </div>
        )}
        {isUser && Boolean(message.content) && !editing && (
          <div className="user-message-actions">
            <>
              <button type="button" className="user-message-copy" onClick={() => void copyAnswer()} title={copied ? '已复制消息' : '复制消息'} aria-label={copied ? '已复制消息' : '复制消息'}>
                {copied ? <Check size={12} /> : <Copy size={12} />}
              </button>
              {onEditMessage && <button type="button" className="user-message-copy" onClick={() => { setEditedText(message.content); setEditing(true); }} title="编辑并重新发送" aria-label="编辑并重新发送"><Pencil size={12} /></button>}
            </>
          </div>
        )}
      </div>
    </div>
  );
};

function formatDuration(seconds: number): string {
  if (seconds >= 60) return `${Math.floor(seconds / 60)}分${Math.round(seconds % 60)}秒`;
  return `${seconds.toFixed(1)}秒`;
}

function formatActivityLabel(label: string): string {
  if (/Analyzing instructions/i.test(label)) return '分析请求';
  const step = label.match(/Executing step (\d+)/i);
  if (step) return `执行步骤 ${step[1]}`;
  return label;
}
