import '@xyflow/react/dist/style.css';
import { useCallback, useEffect, useRef, useState } from 'react';
import { streamChat } from '../../api/chatApi';
import {
  createGroupInstance,
  createGroupRun,
  fetchGroups,
  fetchTopologyTemplates,
  saveTopologyTemplate,
  updateGroup,
  updateGroupRun,
} from '../../api/projectApi';
import { useChatStore } from '../../stores/chatStore';
import { useOrchestrationInvokeStore } from '../../stores/orchestrationInvokeStore';
import type { Group, TopologyTemplate, WorkflowEdgeDefinition, WorkflowNodeDefinition } from '../../types/project';
import { arrangeNodes } from './CanvasParts';
import './workflow.css';
import { executeRun, type RunLogEntry, type RunNodeState } from './workflowRunner';
import { globalNode } from './workflowShared';

export function useWorkflowTab({
  projectId,
  conversationKey,
}: {
  projectId?: string | null;
  conversationKey?: string;
}) {
  const globalMode = projectId === '';
  const [templates, setTemplates] = useState<TopologyTemplate[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<TopologyTemplate | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
  const [editing, setEditing] = useState(false);
  const [infoPanelRequest, setInfoPanelRequest] = useState(0);
  const [kind, setKind] = useState<'workflow' | 'architecture'>('workflow');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [projectGoal, setProjectGoal] = useState('');
  const [projectBackground, setProjectBackground] = useState('');
  const [nodes, setNodes] = useState<WorkflowNodeDefinition[]>([]);
  const [edges, setEdges] = useState<WorkflowEdgeDefinition[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [runGroup, setRunGroup] = useState<Group | null>(null);
  const [runInput, setRunInput] = useState('');
  const [originThreadId, setOriginThreadId] = useState('');
  const [runLog, setRunLog] = useState<RunLogEntry[]>([]);
  const [templatePickerOpen, setTemplatePickerOpen] = useState(false);
  const [reviseText, setReviseText] = useState('');
  const modelId = useChatStore((s) => s.selectedModel);
  const loadThreads = useChatStore((s) => s.loadThreads);
  const pendingInvocations = useOrchestrationInvokeStore((s) => s.pending);
  const consumeInvocation = useOrchestrationInvokeStore((s) => s.consume);
  const processingInvocations = useRef(new Set<string>());
  const reload = useCallback(async () => {
    try {
      const t = await fetchTopologyTemplates();
      setTemplates(t.templates);
      if (projectId) {
        const g = await fetchGroups(projectId);
        setGroups(g.groups.filter((item) => item.group_mode === 'workflow' || item.group_mode === 'architecture'));
      } else setGroups([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载流程编排失败');
    }
  }, [projectId]);
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- Load templates and project instances when the workspace scope changes.
    void reload();
  }, [reload]);
  useEffect(() => {
    const refreshTemplates = () => {
      void reload();
    };
    window.addEventListener('orchestration:templates-updated', refreshTemplates);
    return () => window.removeEventListener('orchestration:templates-updated', refreshTemplates);
  }, [reload]);
  useEffect(() => {
    if (!projectId || !conversationKey) return;
    for (const invocation of pendingInvocations) {
      if (
        invocation.projectId !== projectId ||
        invocation.conversationKey !== conversationKey ||
        processingInvocations.current.has(invocation.requestId)
      )
        continue;
      processingInvocations.current.add(invocation.requestId);
      void (async () => {
        try {
          const data = await fetchGroups(projectId);
          const group = data.groups.find((item) => item.group_id === invocation.groupId);
          if (!group) throw new Error('当前项目中找不到待调用的流程实例。');
          setSelectedGroup(null);
          setRunGroup(group);
          setRunInput(invocation.input);
          setOriginThreadId(invocation.originThreadId);
          setRunLog([]);
          setReviseText('');
        } catch (error) {
          setError(error instanceof Error ? error.message : '无法打开项目流程');
        } finally {
          processingInvocations.current.delete(invocation.requestId);
          consumeInvocation(invocation.requestId);
        }
      })();
    }
  }, [consumeInvocation, conversationKey, pendingInvocations, projectId]);
  useEffect(() => {
    const openInstance = async (event: Event) => {
      const detail = (event as CustomEvent<{ projectId: string; groupId: string }>).detail;
      if (!projectId || detail?.projectId !== projectId) return;
      const data = await fetchGroups(projectId);
      const group = data.groups.find((item) => item.group_id === detail.groupId);
      if (group) {
        setSelectedTemplate(null);
        setSelectedGroup(group);
        setEditing(false);
        setRunGroup(null);
      }
    };
    window.addEventListener('orchestration:open-instance', openInstance);
    return () => window.removeEventListener('orchestration:open-instance', openInstance);
  }, [projectId]);
  useEffect(() => {
    const editInstance = async (event: Event) => {
      const detail = (event as CustomEvent<{ projectId: string; groupId: string }>).detail;
      if (!projectId || detail?.projectId !== projectId) return;
      const data = await fetchGroups(projectId);
      const group = data.groups.find((item) => item.group_id === detail.groupId);
      if (group) {
        setSelectedGroup(group);
        setSelectedTemplate(null);
        setEditing(true);
        setRunGroup(null);
        setKind(group.group_mode === 'architecture' ? 'architecture' : 'workflow');
        setName(group.name);
        setProjectGoal(group.goal || '');
        setProjectBackground(group.background || '');
        setNodes(
          arrangeNodes(
            group.nodes || [],
            group.edges || [],
            group.group_mode === 'architecture' ? 'architecture' : 'workflow',
          ),
        );
        setEdges(group.edges || []);
        setInfoPanelRequest((request) => request + 1);
      }
    };
    window.addEventListener('orchestration:edit-instance', editInstance);
    return () => window.removeEventListener('orchestration:edit-instance', editInstance);
  }, [projectId]);
  const startNew = () => {
    setSelectedTemplate(null);
    setSelectedGroup(null);
    setEditing(true);
    setKind('workflow');
    setName('');
    setDescription('');
    setProjectGoal('');
    setProjectBackground('');
    setNodes([]);
    setEdges([]);
    setError('');
  };
  const chooseTemplate = (template: TopologyTemplate) => {
    setSelectedTemplate(template);
    setSelectedGroup(null);
    setKind(template.topology_type === 'architecture' ? 'architecture' : 'workflow');
    setName(template.name);
    setDescription(globalMode ? template.description || '' : '');
    setProjectGoal('');
    setProjectBackground('');
    setNodes(
      arrangeNodes(
        template.nodes.map(globalNode),
        template.edges || [],
        template.topology_type === 'architecture' ? 'architecture' : 'workflow',
      ),
    );
    setEdges(template.edges || []);
    setEditing(true);
    setTemplatePickerOpen(false);
  };
  const editTemplate = (template: TopologyTemplate) => {
    setSelectedTemplate(template);
    setSelectedGroup(null);
    setEditing(true);
    setKind(template.topology_type === 'architecture' ? 'architecture' : 'workflow');
    setName(template.name);
    setDescription(template.description || '');
    setNodes(
      arrangeNodes(
        template.nodes.map(globalNode),
        template.edges || [],
        template.topology_type === 'architecture' ? 'architecture' : 'workflow',
      ),
    );
    setEdges(template.edges || []);
  };
  const editGroup = (group: Group) => {
    setSelectedGroup(group);
    setSelectedTemplate(null);
    setEditing(true);
    setKind(group.group_mode === 'architecture' ? 'architecture' : 'workflow');
    setName(group.name);
    setProjectGoal(group.goal || '');
    setProjectBackground(group.background || '');
    setNodes(
      arrangeNodes(
        group.nodes || [],
        group.edges || [],
        group.group_mode === 'architecture' ? 'architecture' : 'workflow',
      ),
    );
    setEdges(group.edges || []);
    setInfoPanelRequest((request) => request + 1);
  };
  const saveDefinition = async () => {
    setBusy(true);
    setError('');
    try {
      if (!name.trim() || !nodes.some((n) => n.type === 'agent')) throw new Error('名称和至少一个对话窗口为必填项');
      if (globalMode) {
        const response = await saveTopologyTemplate({
          template_id: selectedTemplate?.template_id,
          name: name.trim(),
          description,
          topology_type: kind,
          nodes,
          edges,
        });
        setSelectedTemplate(response.template);
        window.dispatchEvent(new Event('orchestration:templates-updated'));
      } else if (projectId) {
        if (selectedGroup)
          await updateGroup(
            selectedGroup.group_id,
            {
              name: name.trim(),
              goal: projectGoal,
              background: projectBackground,
              group_mode: kind,
              nodes,
              edges,
              layout: {},
            },
            projectId,
          );
        else {
          const source = selectedTemplate;
          const result = await createGroupInstance({
            project_id: projectId,
            template_id: source?.template_id,
            template_name: source?.name || name.trim(),
            group_mode: kind,
            name: name.trim(),
            goal: projectGoal,
            background: projectBackground,
            nodes,
            edges,
            layout: {},
          });
          setSelectedGroup(result.group);
        }
        await loadThreads();
        window.dispatchEvent(new CustomEvent('orchestration:instances-updated', { detail: { projectId } }));
      }
      setEditing(false);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败');
    } finally {
      setBusy(false);
    }
  };
  const run = async (choice: 'Y' | 'N' | 'O') => {
    if (choice === 'N') {
      setRunGroup(null);
      setRunLog([]);
      return;
    }
    if (choice === 'O') {
      setReviseText(runInput);
      return;
    }
    if (!projectId || !runGroup || !runInput.trim()) return;
    setBusy(true);
    setRunLog([]);
    setError('');
    let activeRunId = '';
    const nodesRef: { current: RunNodeState[] } = { current: [] };
    try {
      const { run: current } = await createGroupRun(runGroup.group_id, {
        project_id: projectId,
        confirmation: 'Y',
        input: runInput,
      });
      await loadThreads();
      activeRunId = current.run_id;
      await updateGroupRun(runGroup.group_id, projectId, { run_id: current.run_id, status: 'running' });
      const outcome = await executeRun(
        runGroup,
        current.sessions,
        runInput,
        {
          streamNode: (request, onText) =>
            new Promise<void>((resolve, reject) => {
              let output = '';
              streamChat({
                thread_id: request.threadId,
                project_id: projectId,
                group_id: runGroup.group_id,
                model_id: modelId,
                content: request.content,
                workflow_input: request.workflowInput,
                workflow_context: request.workflowContext,
                workflow_control: request.workflowControl,
                workflow_stage: request.workflowStage,
                onTextChunk: (chunk) => {
                  output += chunk;
                  onText(output);
                },
                onFinish: (payload) =>
                  payload.exit_status === 'finish'
                    ? resolve()
                    : reject(new Error(payload.exit_status === 'interrupted' ? '节点被中断。' : '节点对话失败。')),
                onError: reject,
              });
            }),
          saveNodes: async (nodes) => {
            await updateGroupRun(runGroup.group_id, projectId, { run_id: current.run_id, status: 'running', nodes });
          },
          updateLog: setRunLog,
        },
        nodesRef,
      );
      await updateGroupRun(runGroup.group_id, projectId, {
        run_id: current.run_id,
        status: 'completed',
        nodes: outcome.nodes,
        final_output: outcome.finalAnswer,
      });
      if (originThreadId) {
        const reviewTitle = `${outcome.finalReviewerTitle} · Supervisor 验证`;
        try {
          await useChatStore.getState().appendOrchestrationResult(originThreadId, {
            project_id: projectId,
            group_id: runGroup.group_id,
            run_id: current.run_id,
            input: runInput,
            content: outcome.finalAnswer,
          });
          setRunLog((old) =>
            old.map((entry) => (entry.title === reviewTitle ? { ...entry, status: '已完成并回传' } : entry)),
          );
        } catch (deliveryError) {
          setError(
            `流程运行已完成，但回传原对话失败：${deliveryError instanceof Error ? deliveryError.message : '未知错误'}`,
          );
          setRunLog((old) =>
            old.map((entry) => (entry.title === reviewTitle ? { ...entry, status: '已完成，回传失败' } : entry)),
          );
        }
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : '流程运行失败';
      setError(message);
      const failedNodes = nodesRef.current.map((node) =>
        node.status === 'pending' || node.status === 'running' ? { ...node, status: 'skipped' } : node,
      );
      setRunLog((old) =>
        old.map((entry) =>
          entry.status === '运行中' || entry.status === '判断中' || entry.status === '复核中'
            ? { ...entry, status: '已停止' }
            : entry,
        ),
      );
      if (activeRunId && runGroup)
        await updateGroupRun(runGroup.group_id, projectId, {
          run_id: activeRunId,
          status: 'failed',
          error: message,
          nodes: failedNodes,
        }).catch(() => undefined);
    } finally {
      setBusy(false);
    }
  };
  return {
    projectId,
    globalMode,
    templates,
    groups,
    selectedGroup,
    setSelectedGroup,
    editing,
    setEditing,
    infoPanelRequest,
    kind,
    setKind,
    name,
    setName,
    description,
    setDescription,
    projectGoal,
    setProjectGoal,
    projectBackground,
    setProjectBackground,
    nodes,
    setNodes,
    edges,
    setEdges,
    error,
    busy,
    runGroup,
    setRunGroup,
    runInput,
    setRunInput,
    runLog,
    templatePickerOpen,
    setTemplatePickerOpen,
    reviseText,
    loadThreads,
    reload,
    startNew,
    chooseTemplate,
    editTemplate,
    editGroup,
    saveDefinition,
    run,
  };
}
