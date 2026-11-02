import { X } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { useTerminalStore } from '../../stores/terminalStore';

export const TerminalTab: React.FC<{ onClose?: () => void; projectId?: string | null }> = ({
  onClose,
  projectId: projectIdOverride,
}) => {
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const threads = useChatStore((state) => state.threads);
  const draftProjectId = useChatStore((state) => state.draftProjectId);
  const projectId =
    projectIdOverride !== undefined
      ? projectIdOverride
      : activeThreadId
        ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id || null
        : draftProjectId;
  const { output, cwd, connected, connecting, error, targetKey, connect, send } = useTerminalStore();
  const expectedTargetKey = `${projectId || 'current-project'}:project-root`;
  const isCurrentTarget = targetKey === expectedTargetKey;
  const currentOutput = isCurrentTarget ? output : '';
  const currentError = isCurrentTarget ? error : null;
  const currentConnected = isCurrentTarget && connected;
  const currentConnecting = !isCurrentTarget || connecting;
  const [command, setCommand] = useState('');
  const [caret, setCaret] = useState(0);
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const terminalRef = useRef<HTMLDivElement>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    connect(null, projectId);
  }, [connect, projectId]);
  useEffect(() => {
    outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight });
  }, [output]);
  useEffect(() => {
    if (connected) terminalRef.current?.focus();
  }, [connected]);

  const trailingPrompt = /(?:^|\n)(PS [^\r\n]*?> ?|PS> ?)$/.exec(currentOutput);
  const priorOutput = trailingPrompt
    ? currentOutput.slice(0, trailingPrompt.index! + (trailingPrompt[0].startsWith('\n') ? 1 : 0))
    : currentOutput;
  const prompt = trailingPrompt?.[1] || (currentConnected ? (cwd ? `PS ${cwd}> ` : 'PS> ') : '');

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.ctrlKey && event.key.toLowerCase() === 'c') {
      event.preventDefault();
      setCommand('');
      setCaret(0);
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      if (!currentConnected || !command.trim()) return;
      send(command);
      setHistory((items) => [...items, command]);
      setHistoryIndex(-1);
      setCommand('');
      setCaret(0);
      return;
    }
    if (event.key === 'Backspace' || event.key === 'Delete') {
      event.preventDefault();
      if (event.key === 'Backspace' && caret > 0) {
        setCommand(command.slice(0, caret - 1) + command.slice(caret));
        setCaret(caret - 1);
      }
      if (event.key === 'Delete' && caret < command.length)
        setCommand(command.slice(0, caret) + command.slice(caret + 1));
      return;
    }
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight' || event.key === 'Home' || event.key === 'End') {
      event.preventDefault();
      setCaret(
        event.key === 'ArrowLeft'
          ? Math.max(0, caret - 1)
          : event.key === 'ArrowRight'
            ? Math.min(command.length, caret + 1)
            : event.key === 'Home'
              ? 0
              : command.length,
      );
      return;
    }
    if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
      event.preventDefault();
      const next =
        event.key === 'ArrowUp' ? Math.min(history.length - 1, historyIndex + 1) : Math.max(-1, historyIndex - 1);
      setHistoryIndex(next);
      const value = next < 0 ? '' : history[history.length - next - 1] || '';
      setCommand(value);
      setCaret(value.length);
      return;
    }
    if (event.key.length === 1 && !event.ctrlKey && !event.altKey && currentConnected) {
      event.preventDefault();
      setCommand(command.slice(0, caret) + event.key + command.slice(caret));
      setCaret(caret + 1);
    }
  };

  return (
    <div
      ref={terminalRef}
      tabIndex={0}
      role="application"
      aria-label="PowerShell 终端，点击后直接输入命令"
      onKeyDown={handleKeyDown}
      onClick={() => terminalRef.current?.focus()}
      style={{
        height: '100%',
        minHeight: 0,
        position: 'relative',
        overflow: 'hidden',
        background: 'color-mix(in srgb, var(--accent-primary) 8%, var(--bg-surface))',
        color: 'var(--accent-primary)',
        fontFamily: 'Consolas, "Cascadia Mono", monospace',
        outline: 'none',
        userSelect: 'text',
      }}
    >
      {onClose && (
        <button
          onClick={onClose}
          title="关闭终端"
          aria-label="关闭终端"
          style={{
            position: 'absolute',
            zIndex: 2,
            right: 8,
            top: 7,
            padding: 'var(--space-0-75)',
            color: 'var(--accent-primary)',
            background: 'transparent',
          }}
        >
          <X size={15} />
        </button>
      )}
      <div
        ref={outputRef}
        style={{
          height: '100%',
          overflowY: 'auto',
          padding: 'var(--space-3) var(--space-3-5)',
          fontSize: 'var(--font-size-sm)',
          lineHeight: 1.55,
          whiteSpace: 'pre-wrap',
          overflowWrap: 'anywhere',
        }}
      >
        <span>{priorOutput}</span>
        {currentError && <span style={{ color: 'var(--accent-rose)' }}>{`\n${currentError}\n`}</span>}
        {currentConnecting && !currentOutput && (
          <span style={{ color: 'var(--accent-primary)' }}>正在启动 PowerShell…</span>
        )}
        {currentConnected && (
          <span>
            {prompt}
            {command.slice(0, caret)}
            <span
              style={{
                background: 'color-mix(in srgb, var(--accent-primary) 8%, var(--bg-surface))',
                color: 'var(--accent-primary)',
              }}
            >
              {command[caret] || ' '}
            </span>
            {command.slice(caret + 1)}
          </span>
        )}
      </div>
    </div>
  );
};
