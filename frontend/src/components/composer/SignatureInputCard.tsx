import React, { useEffect, useState, useRef } from 'react';
import { Plus, ArrowRight, ImagePlus, Pause, Play, Pencil, Trash2, CornerUpRight, Check, X } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { PlusMenu } from './PlusMenu';
import { ModelDropdown } from './ModelDropdown';
import { AttachedBadges } from './AttachedBadges';
import { readImageFiles } from './imageAttachments';
import { ImageAttachmentStrip } from './ImageAttachmentStrip';
import { fetchGroups } from '../../api/projectApi';
import { useToolTabsStore } from '../../stores/toolTabsStore';
import { ensureRightSidebarOpen } from '../../stores/rightSidebarLayout';
import { useLayoutStore } from '../../stores/layoutStore';
import { useOrchestrationInvokeStore } from '../../stores/orchestrationInvokeStore';
import { Button } from '../common/Button';
import { IconButton } from '../common/IconButton';
import { TextArea } from '../common/Field';
import { extractWorkflowTaskInput } from './workflowInvocation';

/**
 * 中间区域核心输入卡片 (对齐 Penpot 签名级胶囊输入框)
 */
export const SignatureInputCard: React.FC = () => {
  const {
    sendMessage,
    isStreaming,
    ruleTrigger,
    attachedSkills,
    attachedMcps,
    draftImages,
    addDraftImages,
    removeDraftImage,
    queuedPrompts,
    queuePaused,
    removeQueuedPrompt,
    editQueuedPrompt,
    guideQueuedPrompt,
    resumeQueue,
    pauseQueue,
  } = useChatStore();

  const [input, setInput] = useState('');
  const [plusOpen, setPlusOpen] = useState(false);
  const [editingQueueId, setEditingQueueId] = useState<string | null>(null);
  const [queueDraft, setQueueDraft] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const openTab = useToolTabsStore((state) => state.openTab);
  const setNewTaskDialogOpen = useLayoutStore((state) => state.setNewTaskDialogOpen);
  const enqueueOrchestrationInvoke = useOrchestrationInvokeStore((state) => state.enqueue);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = '52px';
    textarea.style.height = `${Math.min(200, Math.max(52, textarea.scrollHeight))}px`;
    textarea.style.overflowY = textarea.scrollHeight > 200 ? 'auto' : 'hidden';
  }, [input]);

  const handleImageFiles = async (files: FileList | File[]) => {
    addDraftImages(await readImageFiles(files));
  };

  const handlePaste = async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const files = Array.from(e.clipboardData.items)
      .filter((item) => item.kind === 'file' && item.type.startsWith('image/'))
      .map((item) => item.getAsFile())
      .filter((file): file is File => Boolean(file));
    if (files.length) {
      e.preventDefault();
      await handleImageFiles(files);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    } else if (e.key === '/' && input.trim() === '') {
      setPlusOpen(true);
    }
  };

  const handleSend = async () => {
    if (!input.trim() && draftImages.length === 0) return;
    const commandMatch = input.trim().match(/^\/(goal|plan|learn|grill-me|schedule)(?:\s+|$)([\s\S]*)$/i);
    if (input.trim() === '/') { setPlusOpen(true); return; }
    let message = input.trim();
    if (commandMatch) {
      const command = commandMatch[1].toLowerCase();
      message = commandMatch[2].trim();
      if (command === 'schedule') {
        setNewTaskDialogOpen(true, message);
        setInput('');
        setPlusOpen(false);
        return;
      }
      const trigger = command as Exclude<import('../../types/chat').RuleTrigger, null>;
      useChatStore.getState().setRuleTrigger(trigger);
      if (!message && draftImages.length === 0) {
        setInput('');
        setPlusOpen(false);
        return;
      }
    }
    const chat = useChatStore.getState();
    const projectId = chat.activeThreadId ? chat.threads.find((thread) => thread.thread_id === chat.activeThreadId)?.project_id : chat.draftProjectId;
    const explicitInvocation = /调用|运行|执行|启动|使用/.test(message) && /工作流|架构|流程/.test(message);
    if (projectId && explicitInvocation) {
      try {
        const { groups } = await fetchGroups(projectId);
        const matched = groups.find((group) => (group.group_mode === 'workflow' || group.group_mode === 'architecture') && message.includes(group.name));
        if (matched) {
          const originThreadId = chat.activeThreadId || await chat.newThread(`流程任务 · ${matched.name}`, undefined, projectId);
          const conversationKey = `conversation:${originThreadId}`;
          ensureRightSidebarOpen(conversationKey);
          openTab('workflow', '流程编排', conversationKey, projectId);
          enqueueOrchestrationInvoke({
            conversationKey,
            projectId,
            groupId: matched.group_id,
            originThreadId,
            input: extractWorkflowTaskInput(message, matched.name),
          });
          setInput(''); setPlusOpen(false); return;
        }
      } catch { /* A normal message still works if the project flow list is unavailable. */ }
    }
    sendMessage(message);
    setInput('');
    setPlusOpen(false);
  };

  return (
    <div
      className="glass-panel composer-input-card"
      style={{
        width: '100%',
        maxWidth: 762,
        borderRadius: 'var(--radius-xl)',
        backgroundColor: 'var(--bg-surface-elevated)',
        border: '1px solid var(--border-default)',
        boxShadow: 'var(--shadow-lg)',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* 顶部微渐变细分割线 */}
      <div
        style={{
          height: 1,
          width: '96%',
          margin: '0 auto',
          background: 'linear-gradient(90deg, transparent 0%, color-mix(in srgb, var(--accent-primary) 9%, transparent) 50%, transparent 100%)',
        }}
      />

      {/* '+' 与 '/' 唤起的宽度对齐能力拓展浮窗 */}
      <PlusMenu isOpen={plusOpen} onClose={() => setPlusOpen(false)} requestText={input} onConsumeRequest={() => setInput('')} onSelectRuleTrigger={(trigger) => setInput((current) => current.replace(new RegExp(`^/${trigger}\\b\\s*`, 'i'), ''))} />

      <ImageAttachmentStrip images={draftImages} onRemove={removeDraftImage} />

      {(isStreaming || queuedPrompts.length > 0 || queuePaused) && (
        <div className="message-queue-panel">
          <div className="message-queue-header">
            {queuePaused ? <Pause size={13} /> : <span className="message-queue-live-dot" />}
            <span>{queuePaused ? '队列已暂停' : isStreaming ? '正在处理当前消息' : '消息队列'}</span>
            <span className="message-queue-count">{queuedPrompts.length} 条待处理</span>
            {queuePaused || (!isStreaming && queuedPrompts.length > 0) ? <button type="button" className="message-queue-control" onClick={resumeQueue}><Play size={12} fill="currentColor" />继续</button> : isStreaming ? <button type="button" className="message-queue-control" onClick={() => void pauseQueue().catch(() => undefined)}><Pause size={12} />暂停</button> : null}
          </div>
          {queuedPrompts.map((prompt) => (
            <div className="message-queue-item" key={prompt.id}>
              {editingQueueId === prompt.id ? <TextArea autoFocus value={queueDraft} onChange={(event) => setQueueDraft(event.target.value)} aria-label="编辑排队消息" className="message-queue-edit-input" /> : <span className="message-queue-content">{prompt.content}</span>}
              <div className="message-queue-actions">
                {editingQueueId === prompt.id ? <>
                  <button type="button" title="保存修改" aria-label="保存修改" onClick={() => { editQueuedPrompt(prompt.id, queueDraft); setEditingQueueId(null); }}><Check size={13} /></button>
                  <button type="button" title="取消编辑" aria-label="取消编辑" onClick={() => setEditingQueueId(null)}><X size={13} /></button>
                </> : <>
                  <button type="button" title="当前执行阶段结束后优先接收这条指令" aria-label="引导" onClick={() => void guideQueuedPrompt(prompt.id)}><CornerUpRight size={13} /><span>引导</span></button>
                  {queuePaused && <button type="button" title="编辑排队消息" aria-label="编辑排队消息" onClick={() => { setQueueDraft(prompt.content); setEditingQueueId(prompt.id); }}><Pencil size={13} /></button>}
                  <button type="button" title="移除排队消息" aria-label="移除排队消息" onClick={() => removeQueuedPrompt(prompt.id)}><Trash2 size={13} /></button>
                </>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 附加模式与拓展技能徽章 */}
      <AttachedBadges
        ruleTrigger={ruleTrigger}
        attachedSkills={attachedSkills}
        attachedMcps={attachedMcps}
      />

      {/* 文本输入区域 */}
      <TextArea
        ref={textareaRef}
        value={input}
        onChange={(e) => {
          setInput(e.target.value);
          if (e.target.value.startsWith('/')) setPlusOpen(true);
        }}
        onPaste={handlePaste}
        onKeyDown={handleKeyDown}
        placeholder="输入任务内容，或输入 / 使用快捷指令…"
        rows={2}
        className="composer-prompt-input"
      />

      {/* 底部动作工具条 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-1) var(--space-3) var(--space-2-5)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <input ref={imageInputRef} type="file" accept="image/*" multiple hidden onChange={(e) => { if (e.target.files) void handleImageFiles(e.target.files); e.target.value = ''; }} />
          <IconButton onClick={() => setPlusOpen(!plusOpen)} label="添加 MCP 或 Skill" active={plusOpen} size="sm">
            <Plus size={16} />
          </IconButton>

          <IconButton onClick={() => imageInputRef.current?.click()} label="添加图片" size="sm">
            <ImagePlus size={15} />
          </IconButton>

          <ModelDropdown />
        </div>

        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Button
            onClick={handleSend}
            title="发送指令或加入消息队列"
            aria-label="发送指令或加入消息队列"
            variant="primary"
            size="compact"
            className="composer-send-button"
          >
            <ArrowRight size={15} />
          </Button>
        </div>
      </div>
    </div>
  );
};
