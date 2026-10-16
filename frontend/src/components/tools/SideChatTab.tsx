import React, { useRef, useState } from 'react';
import { FileText, History, ImagePlus, MessageSquare, Paperclip, Send, Square, X } from 'lucide-react';
import { fetchThreadMessages } from '../../api/chatApi';
import { useChatStore } from '../../stores/chatStore';
import { useSideChatStore } from '../../stores/sideChatStore';
import { MessageItem } from '../composer/MessageItem';
import { IconButton } from '../common/IconButton';
import { Button } from '../common/Button';
import { SelectField, TextArea } from '../common/Field';
import { ApprovalActionButtons } from '../composer/ApprovalActionButtons';
import { ModelDropdown } from '../composer/ModelDropdown';
import { readImageFiles } from '../composer/imageAttachments';
import { ChatImageAttachment } from '../../types/chat';

interface TextAttachment { id: string; name: string; text: string; }
type ContextLimit = 0 | 5 | 10 | 20 | 'full';

export const SideChatTab: React.FC<{ sessionId: string }> = ({ sessionId }) => {
  const [input, setInput] = useState('');
  const [loadingContext, setLoadingContext] = useState(false);
  const [contextError, setContextError] = useState('');
  const [images, setImages] = useState<ChatImageAttachment[]>([]);
  const [files, setFiles] = useState<TextAttachment[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const mainMessages = useChatStore((state) => state.messages);
  const session = useSideChatStore((state) => state.sessions[sessionId]);
  const { sendMessage, confirmAction, interrupt, setContextMessages, setSelectedModel } = useSideChatStore();
  const sourceThreadId = session?.sourceThreadId || null;
  const sourceTitle = session?.sourceTitle || '';
  const sourceContext = session?.sourceContext || [];
  const contextLimit = session?.contextLimit ?? 5;
  const selectedModel = session?.selectedModel || 'deepseek/deepseek-chat';
  const messages = session?.messages || [];
  const isStreaming = session?.isStreaming || false;
  const currentStatus = session?.currentStatus || '';
  const approvalRequest = session?.approvalRequest || null;
  const error = session?.error || null;

  const handleSend = () => {
    if (isStreaming) {
      void interrupt(sessionId);
      return;
    }
    if (!input.trim() && !images.length && !files.length) return;
    const fileContext = files.map((file) => `\n\n<附件：${file.name}>\n${file.text}\n</附件>`).join('');
    sendMessage(sessionId, `${input.trim()}${fileContext}`.trim() || '请查看我附上的图片并回答。', images);
    setInput('');
    setImages([]);
    setFiles([]);
  };

  const changeContextLimit = async (limit: ContextLimit) => {
    setLoadingContext(true);
    setContextError('');
    try {
      if (limit === 0) {
        setContextMessages(sessionId, sourceContext || [], 0);
        return;
      }
      let context = mainMessages;
      if (sourceThreadId) {
        const result = await fetchThreadMessages(sourceThreadId);
        const anchor = sourceContext[sourceContext.length - 1];
        const anchorIndex = anchor ? result.messages.map((message) => `${message.role}\0${message.content}`).lastIndexOf(`${anchor.role}\0${anchor.content}`) : -1;
        context = anchorIndex >= 0 ? result.messages.slice(0, anchorIndex + 1) : result.messages;
      } else {
        context = sourceContext;
      }
      setContextMessages(sessionId, context, limit);
    } catch (loadError) {
      setContextError(loadError instanceof Error ? loadError.message : '加载完整上下文失败');
    } finally {
      setLoadingContext(false);
    }
  };

  const handleFiles = async (selected: FileList | File[]) => {
    const acceptedText: TextAttachment[] = [];
    const rejected: string[] = [];
    for (const file of Array.from(selected)) {
      if (file.type.startsWith('image/')) continue;
      if (file.size > 1_000_000) { rejected.push(`${file.name}（超过 1 MB）`); continue; }
      if (!/\.(txt|md|markdown|json|ya?ml|toml|ini|csv|tsv|log|py|ts|tsx|js|jsx|css|html?|xml|sql|sh|ps1|bat|rs|go|java|c|cpp|h|hpp)$/i.test(file.name) && !file.type.startsWith('text/')) { rejected.push(`${file.name}（暂不支持此文件类型）`); continue; }
      acceptedText.push({ id: `${Date.now()}-${Math.random()}`, name: file.name, text: await file.text() });
    }
    if (acceptedText.length) setFiles((current) => [...current, ...acceptedText]);
    const pickedImages = Array.from(selected).filter((file) => file.type.startsWith('image/'));
    if (pickedImages.length) {
      const loadedImages = await readImageFiles(pickedImages);
      setImages((current) => [...current, ...loadedImages].slice(0, 4));
    }
    setContextError(rejected.length ? `未添加：${rejected.join('、')}` : '');
  };

  if (!session) return <div style={{ padding: 'var(--space-4)', color: 'var(--text-muted)' }}>侧边对话已关闭</div>;
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-workspace)', minHeight: 0 }}>
      <div className="side-chat-header">
        <div className="side-chat-heading">
          <span className="side-chat-heading-icon"><MessageSquare size={15} /></span>
          <span>临时追问{sourceTitle ? ` · ${sourceTitle}` : ''}</span>
        </div>
        <label className="side-chat-context-control" title="选择发送前携带的主对话上下文；完整对话最多携带最近 100 条消息">
          <History size={13} />
          <SelectField className="side-chat-context-select" aria-label="侧边聊天上下文范围" value={contextLimit} disabled={loadingContext} onChange={(event) => void changeContextLimit(event.target.value === 'full' ? 'full' : Number(event.target.value) as 0 | 5 | 10 | 20)}>
            <option value={0}>不带上下文（0 条）</option><option value={5}>最近 5 条</option><option value={10}>最近 10 条</option><option value={20}>最近 20 条</option><option value="full">完整对话（最多 100 条）</option>
          </SelectField>
        </label>
      </div>

      {contextError && <div style={{ padding: 'var(--space-1-5) var(--space-3-25)', color: 'var(--accent-rose)', fontSize: 'var(--font-size-compact)' }}>{contextError}</div>}
      {error && <div style={{ padding: 'var(--space-1-5) var(--space-3-25)', color: 'var(--accent-rose)', fontSize: 'var(--font-size-compact)' }}>{error}</div>}

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: 'var(--space-2-5) var(--space-3-5)', display: 'flex', flexDirection: 'column' }}>
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', margin: 'auto var(--space-3)', maxWidth: 300, alignSelf: 'center' }}>
            <MessageSquare size={28} style={{ margin: '0 auto var(--space-2-25)', opacity: .4 }} />
            <div style={{ fontSize: 'var(--font-size-control)', fontWeight: 550 }}>就这条回答继续追问</div>
          </div>
        ) : messages.map((message, index) => (
          <MessageItem key={message.id || index} message={message} isStreaming={isStreaming && index === messages.length - 1 && message.role === 'assistant'} streamLabel={currentStatus} />
        ))}
        {approvalRequest && (
          <div style={{ margin: 'var(--space-2) 0', padding: 'var(--space-3)', borderRadius: 'var(--radius-md-plus)', border: '1px solid var(--border-warning-soft)', background: 'var(--bg-warning-soft)' }}>
            <strong style={{ fontSize: 'var(--font-size-label)', color: 'var(--accent-amber)' }}>工具调用需要审批：{approvalRequest.tool_name || '终端命令'}</strong>
            <pre style={{ marginTop: 'var(--space-1-75)', maxHeight: 120, overflow: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: 'var(--text-secondary)', fontSize: 'var(--font-size-subtle)' }}>{JSON.stringify(approvalRequest.args, null, 2)}</pre>
            <ApprovalActionButtons onConfirm={(choice) => { void confirmAction(sessionId, choice); }} />
          </div>
        )}
      </div>

      <div className="side-chat-composer glass-panel">
        <input ref={imageInputRef} type="file" accept="image/*" multiple hidden onChange={(event) => { if (event.target.files) void handleFiles(event.target.files); event.target.value = ''; }} />
        <input ref={fileInputRef} type="file" multiple hidden onChange={(event) => { if (event.target.files) void handleFiles(event.target.files); event.target.value = ''; }} />
        <TextArea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleSend(); } }}
          placeholder="追问这条回答…（Shift+Enter 换行）"
          rows={2}
          className="side-chat-composer-input"
        />
        {(images.length > 0 || files.length > 0) && <div className="side-chat-attachments">
          {images.map((image) => <span key={image.id} className="side-chat-attachment"><ImagePlus size={11} /><span>{image.name}</span><IconButton label={`移除图片 ${image.name}`} size="sm" onClick={() => setImages((current) => current.filter((item) => item.id !== image.id))}><X size={12} /></IconButton></span>)}
          {files.map((file) => <span key={file.id} className="side-chat-attachment"><FileText size={11} /><span>{file.name}</span><IconButton label={`移除文件 ${file.name}`} size="sm" onClick={() => setFiles((current) => current.filter((item) => item.id !== file.id))}><X size={12} /></IconButton></span>)}
        </div>}
        <div className="side-chat-composer-toolbar">
          <div className="side-chat-composer-actions">
            <IconButton label="添加图片" size="sm" onClick={() => imageInputRef.current?.click()}><ImagePlus size={15} /></IconButton>
            <IconButton label="添加文本或代码文件" size="sm" onClick={() => fileInputRef.current?.click()}><Paperclip size={15} /></IconButton>
            <ModelDropdown value={selectedModel} onChange={(model) => setSelectedModel(sessionId, model)} />
          </div>
          <Button type="button" variant="primary" size="compact" className="side-chat-send" onClick={handleSend} title={isStreaming ? '停止生成' : '发送追问'} aria-label={isStreaming ? '停止生成' : '发送追问'}>
            {isStreaming ? <Square size={13} /> : <Send size={14} />}
          </Button>
        </div>
      </div>
    </div>
  );
};
