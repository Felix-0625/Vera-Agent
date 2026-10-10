import { create } from 'zustand';

interface TerminalState {
  output: string;
  cwd: string;
  shell: string;
  connected: boolean;
  connecting: boolean;
  error: string | null;
  connect: (groupId?: string | null, projectId?: string | null) => void;
  send: (command: string) => void;
  clear: () => void;
}

let socket: WebSocket | null = null;
let activeTarget = '';
const MAX_OUTPUT_CHARS = 600_000;

export const useTerminalStore = create<TerminalState>((set, get) => ({
  output: '',
  cwd: '',
  shell: 'PowerShell',
  connected: false,
  connecting: false,
  error: null,

  connect: (groupId, projectId) => {
    const target = `${projectId || 'current-project'}:${groupId || 'project-root'}`;
    if (activeTarget === target && socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;

    socket?.close();
    socket = null;
    activeTarget = target;
    set({ output: '', cwd: '', shell: 'PowerShell', connected: false, connecting: true, error: null });

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const query = new URLSearchParams();
    if (groupId) query.set('group_id', groupId);
    if (projectId) query.set('project_id', projectId);
    const suffix = query.size ? `?${query.toString()}` : '';
    const nextSocket = new WebSocket(`${protocol}//${window.location.host}/api/terminal/session${suffix}`);
    socket = nextSocket;
    nextSocket.onmessage = (event) => {
      let payload: { type?: string; data?: string; cwd?: string; shell?: string; message?: string; exit_code?: number };
      try {
        payload = JSON.parse(String(event.data));
      } catch {
        return;
      }
      if (payload.type === 'connected') {
        set({ connected: true, connecting: false, cwd: payload.cwd || '', shell: payload.shell || 'PowerShell', error: null });
      } else if (payload.type === 'output' && payload.data) {
        set((state) => ({ output: (state.output + payload.data).slice(-MAX_OUTPUT_CHARS) }));
      } else if (payload.type === 'error') {
        set({ error: payload.message || 'PowerShell 终端启动失败', connecting: false, connected: false });
      } else if (payload.type === 'exit') {
        set({ connected: false, connecting: false, error: `PowerShell 已退出 (exit ${payload.exit_code ?? 0})` });
      }
    };
    nextSocket.onerror = () => set({ connected: false, connecting: false, error: '无法连接本地 PowerShell 终端' });
    nextSocket.onclose = () => {
      if (socket === nextSocket) {
        socket = null;
        set({ connected: false, connecting: false });
      }
    };
  },

  send: (command) => {
    if (!command.trim() || !socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ type: 'input', data: command }));
  },

  clear: () => set({ output: '' }),
}));

if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => socket?.close());
}
