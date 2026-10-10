import React, { useRef, useState } from 'react';
import { FileText, History, ImagePlus, MessageSquare, Paperclip, RotateCcw, Send, Square, Trash2, X } from 'lucide-react';
import { fetchThreadMessages } from '../../api/chatApi';
import { useChatStore } from '../../stores/chatStore';
import { useSideChatStore } from '../../stores/sideChatStore';
import { MessageItem } from '../composer/MessageItem';
import { ApprovalActionButtons } from '../composer/ApprovalActionButtons';
import { ModelDropdown } from '../composer/ModelDropdown';
import { readImageFiles } from '../composer/imageAttachments';
import { ChatImageAttachment } from '../../types/chat';

interface TextAttachment { id: string; name: string; text: string; }
type ContextLimit = 5 | 10 | 20 | 'full';

export const SideChatTab: React.FC = () => {
  const [input, setInput] = useState('');
  const [loadingContext, setLoadingContext] = useState(false);
  const [contextError, setContextError] = useState('');
  const [images, setImages] = useState<ChatImageAttachment[]>([]);
  const [files, setFiles] = useState<TextAttachment[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const mainMessages = useChatStore((state) => state.messages);
  const {
    sourceThreadId, sourceTitle, sourceContext, contextScope, contextLimit, selectedModel, messages, isStreaming,
    currentStatus, approvalRequest, error, sendMessage, confirmAction, interrupt,
    setContextMessages, setSelectedModel, openFromContext, dispose,
  } = useSideChatStore();

  const handleSend = () => {
    if (isStreaming) {
      void interrupt();
      return;
    }
    if (!input.trim() && !images.length && !files.length) return;
    const fileContext = files.map((file) => `\n\n<附件：${file.name}>\n${file.text}\n</附件>`).join('');
    sendMessage(`${input.trim()}${fileContext}`.trim() || '请查看我附上的图片并回答。', images);
    setInput('');
    setImages([]);
    setFiles([]);
  };

  const changeContextLimit = async (limit: ContextLimit) => {
    setLoadingContext(true);
    setContextError('');
    try {
      let context = mainMessages;
      if (sourceThreadId) {
        const result = await fetchThreadMessages(sourceThreadId);
        const anchor = sourceContext[sourceContext.length - 1];
        const anchorIndex = anchor ? result.messages.map((message) => `${message.role}\0${message.content}`).lastIndexOf(`${anchor.role}\0${anchor.content}`) : -1;
        context = anchorIndex >= 0 ? result.messages.slice(0, anchorIndex + 1) : result.messages;
      } else {
        context = sourceContext;
      }
      setContextMessages(context, limit);
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

  const restartSideChat = () => {
    const state = useSideChatStore.getState();
    openFromContext(state.sourceThreadId, state.sourceTitle, state.sourceContext, state.contextScope, state.contextLimit);
  };
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-workspace)', minHeight: 0 }}>
      <div className="side-chat-header">
        <div className="side-chat-heading">
          <span className="side-chat-heading-icon"><MessageSquare size={15} /></span>
          <span>临时追问</span>
        </div>
        <label className="side-chat-context-control" title="选择发送前携带的主对话上下文">
          <History size={13} />
          <select aria-label="侧边聊天上下文范围" value={contextLimit} disabled={loadingContext} onChange={(event) => void changeContextLimit(event.target.value === 'full' ? 'full' : Number(event.target.value) as 5 | 10 | 20)}>
            <option value={5}>最近 5 条</option><option value={10}>最近 10 条</option><option value={20}>最近 20 条</option><option value="full">完整对话</option>
          </select>
        </label>
        <div className="side-chat-header-actions">
          <button type="button" onClick={restartSideChat} title="重新开始临时对话" aria-label="重新开始临时对话"><RotateCcw size={14} /></button>
          <button type="button" onClick={dispose} title="清除临时对话" aria-label="清除临时对话"><Trash2 size={14} /></button>
        </div>
      </div>

      {contextError && <div style={{ padding: '6px 13px', color: 'var(--accent-rose)', fontSize: 11 }}>{contextError}</div>}
      {error && <div style={{ padding: '6px 13px', color: 'var(--accent-rose)', fontSize: 11 }}>{error}</div>}

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '10px 14px', display: 'flex', flexDirection: 'column' }}>
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', margin: 'auto 12px', maxWidth: 300, alignSelf: 'center' }}>
            <MessageSquare size={28} style={{ margin: '0 auto 9px', opacity: .4 }} />
            <div style={{ fontSize: 12.5, fontWeight: 550 }}>就这条回答继续追问</div>
          </div>
        ) : messages.map((message, index) => (
          <MessageItem key={message.id || index} message={message} isStreaming={isStreaming && index === messages.length - 1 && message.role === 'assistant'} streamLabel={currentStatus} />
        ))}
        {approvalRequest && (
          <div style={{ margin: '8px 0', padding: 12, borderRadius: 9, border: '1px solid rgba(245,158,11,.32)', background: 'rgba(245,158,11,.08)' }}>
            <strong style={{ fontSize: 11.5, color: '#fbbf24' }}>工具调用需要审批：{approvalRequest.tool_name || '终端命令'}</strong>
            <pre style={{ marginTop: 7, maxHeight: 120, overflow: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: 'var(--text-secondary)', fontSize: 10.5 }}>{JSON.stringify(approvalRequest.args, null, 2)}</pre>
            <ApprovalActionButtons onConfirm={(choice) => { void confirmAction(choice); }} />
          </div>
        )}
      </div>

      <div className="side-chat-composer glass-panel">
        <input ref={imageInputRef} type="file" accept="image/*" multiple hidden onChange={(event) => { if (event.target.files) void handleFiles(event.target.files); event.target.value = ''; }} />
        <input ref={fileInputRef} type="file" multiple hidden onChange={(event) => { if (event.target.files) void handleFiles(event.target.files); event.target.value = ''; }} />
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleSend(); } }}
          placeholder="追问这条回答…（Shift+Enter 换行）"
          rows={2}
          className="side-chat-composer-input"
        />
        {(images.length > 0 || files.length > 0) && <div className="side-chat-attachments">
          {images.map((image) => <span key={image.id} className="side-chat-attachment"><ImagePlus size={11} />{image.name}<button type="button" aria-label={`移除 ${image.name}`} onClick={() => setImages((current) => current.filter((item) => item.id !== image.id))}><X size={11} /></button></span>)}
          {files.map((file) => <span key={file.id} className="side-chat-attachment"><FileText size={11} />{file.name}<button type="button" aria-label={`移除 ${file.name}`} onClick={() => setFiles((current) => current.filter((item) => item.id !== file.id))}><X size={11} /></button></span>)}
        </div>}
        <div className="side-chat-composer-toolbar">
          <div className="side-chat-composer-actions">
            <button type="button" onClick={() => imageInputRef.current?.click()} title="添加图片" aria-label="添加图片"><ImagePlus size={15} /></button>
            <button type="button" onClick={() => fileInputRef.current?.click()} title="添加文本或代码文件" aria-label="添加文件"><Paperclip size={15} /></button>
            <ModelDropdown value={selectedModel} onChange={setSelectedModel} />
          </div>
          <button type="button" className="side-chat-send" onClick={handleSend} title={isStreaming ? '停止生成' : '发送追问'} aria-label={isStreaming ? '停止生成' : '发送追问'}>
            {isStreaming ? <Square size={13} /> : <Send size={14} />}
          </button>
        </div>
      </div>
    </div>
  );
};
