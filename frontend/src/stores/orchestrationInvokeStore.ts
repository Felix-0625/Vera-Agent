import { create } from 'zustand';

export interface OrchestrationInvocation {
  requestId: string;
  conversationKey: string;
  projectId: string;
  groupId: string;
  originThreadId: string;
  input: string;
}

interface OrchestrationInvocationState {
  pending: OrchestrationInvocation[];
  enqueue: (invocation: Omit<OrchestrationInvocation, 'requestId'>) => void;
  consume: (requestId: string) => void;
}

/** Keep workflow invocations until the matching conversation panel is mounted. */
export const useOrchestrationInvokeStore = create<OrchestrationInvocationState>((set) => ({
  pending: [],
  enqueue: (invocation) => set((state) => ({
    pending: [...state.pending, { ...invocation, requestId: crypto.randomUUID() }],
  })),
  consume: (requestId) => set((state) => ({
    pending: state.pending.filter((item) => item.requestId !== requestId),
  })),
}));
