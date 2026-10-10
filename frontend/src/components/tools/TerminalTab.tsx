import React, { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useTerminalStore } from '../../stores/terminalStore';

export const TerminalTab: React.FC<{ onClose?: () => void }> = ({ onClose }) => {
  const activeThreadId = useChatStore((state) => state.activeThreadId);
  const threads = useChatStore((state) => state.threads);
  const draftProjectId = useChatStore((state) => state.draftProjectId);
  const projectId = activeThreadId ? threads.find((thread) => thread.thread_id === activeThreadId)?.project_id || null : draftProjectId;
  const { output, cwd, connected, connecting, error, connect, send } = useTerminalStore();
  const [command, setCommand] = useState('');
  const [caret, setCaret] = useState(0);
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const terminalRef = useRef<HTMLDivElement>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  useEffect(() => { connect(null, projectId); }, [connect, projectId]);
  useEffect(() => { outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight }); }, [output]);
  useEffect(() => { if (connected) terminalRef.current?.focus(); }, [connected]);

  const trailingPrompt = /(?:^|\n)(PS [^\r\n]*?> ?|PS> ?)$/.exec(output);
  const priorOutput = trailingPrompt ? output.slice(0, trailingPrompt.index! + (trailingPrompt[0].startsWith('\n') ? 1 : 0)) : output;
  const prompt = trailingPrompt?.[1] || (connected ? (cwd ? `PS ${cwd}> ` : 'PS> ') : '');

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.ctrlKey && event.key.toLowerCase() === 'c') {
      event.preventDefault();
      setCommand(''); setCaret(0);
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      if (!connected || !command.trim()) return;
      send(command);
      setHistory((items) => [...items, command]); setHistoryIndex(-1); setCommand(''); setCaret(0);
      return;
    }
    if (event.key === 'Backspace' || event.key === 'Delete') {
      event.preventDefault();
      if (event.key === 'Backspace' && caret > 0) { setCommand(command.slice(0, caret - 1) + command.slice(caret)); setCaret(caret - 1); }
      if (event.key === 'Delete' && caret < command.length) setCommand(command.slice(0, caret) + command.slice(caret + 1));
      return;
    }
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight' || event.key === 'Home' || event.key === 'End') {
      event.preventDefault();
      setCaret(event.key === 'ArrowLeft' ? Math.max(0, caret - 1) : event.key === 'ArrowRight' ? Math.min(command.length, caret + 1) : event.key === 'Home' ? 0 : command.length);
      return;
    }
    if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
      event.preventDefault();
      const next = event.key === 'ArrowUp' ? Math.min(history.length - 1, historyIndex + 1) : Math.max(-1, historyIndex - 1);
      setHistoryIndex(next);
      const value = next < 0 ? '' : history[history.length - next - 1] || '';
      setCommand(value); setCaret(value.length);
      return;
    }
    if (event.key.length === 1 && !event.ctrlKey && !event.altKey && connected) {
      event.preventDefault();
      setCommand(command.slice(0, caret) + event.key + command.slice(caret)); setCaret(caret + 1);
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
      style={{ height: '100%', minHeight: 0, position: 'relative', overflow: 'hidden', background: '#090A0F', color: '#D7DEE8', fontFamily: 'Consolas, "Cascadia Mono", monospace', outline: 'none', userSelect: 'text' }}
    >
      {onClose && <button onClick={onClose} title="关闭终端" aria-label="关闭终端" style={{ position: 'absolute', zIndex: 2, right: 8, top: 7, padding: 3, color: '#94A3B8', background: 'transparent' }}><X size={15} /></button>}
      <div ref={outputRef} style={{ height: '100%', overflowY: 'auto', padding: '12px 14px', fontSize: 12, lineHeight: 1.55, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
        <span>{priorOutput}</span>
        {error && <span style={{ color: '#F87171' }}>{`\n${error}\n`}</span>}
        {connecting && !output && <span style={{ color: '#94A3B8' }}>正在启动 PowerShell…</span>}
        {connected && <span>{prompt}{command.slice(0, caret)}<span style={{ background: '#D7DEE8', color: '#090A0F' }}>{command[caret] || ' '}</span>{command.slice(caret + 1)}</span>}
      </div>
    </div>
  );
};
