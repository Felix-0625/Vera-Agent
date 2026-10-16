import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { addEdge, applyEdgeChanges, applyNodeChanges, Background, BackgroundVariant, Handle, Position, ReactFlow, ReactFlowProvider, SelectionMode, useEdgesState, useNodesState, useReactFlow, type Connection, type Edge, type EdgeChange, type Node, type NodeChange, type NodeProps } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import './workflow.css';
import { ArrowLeft, Bot, GitBranch, GitFork, Layers3, LocateFixed, Minus, Play, Plus, Redo2, Save, Search, Settings2, Undo2, Workflow, X, Trash2, ZoomIn, ZoomOut, CopyPlus } from 'lucide-react';
import { createGroupInstance, createGroupRun, deleteGroup, fetchGroups, fetchTopologyTemplates, saveTopologyTemplate, updateGroup, updateGroupRun } from '../../api/projectApi';
import { streamChat } from '../../api/chatApi';
import { useChatStore } from '../../stores/chatStore';
import type { Group, TopologyTemplate, WorkflowEdgeDefinition, WorkflowNodeDefinition } from '../../types/project';
import { useOrchestrationInvokeStore } from '../../stores/orchestrationInvokeStore';
import { SelectField, TextArea, TextInput } from '../common/Field';
import { EmptyState } from '../common/EmptyState';
import { Button } from '../common/Button';
import { IconButton } from '../common/IconButton';

const styles: Record<string, React.CSSProperties> = {
  card: { background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)' },
  button: { border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', background: 'var(--bg-surface-elevated)', color: 'var(--text-primary)', padding: 'var(--space-1-75) var(--space-2-5)', display: 'inline-flex', alignItems: 'center', gap: 'var(--space-1-5)', cursor: 'pointer', fontSize: 'var(--font-size-sm)' },
};
const id = (prefix: string) => `${prefix}_${crypto.randomUUID().slice(0, 8)}`;
const edgeLabelStyle: React.CSSProperties = { fill: 'var(--text-muted)', fontSize: 'var(--font-size-xs)', fontWeight: 500 };
const workflowNodeTypes = { workflowAgent: WorkflowAgentNode, architectureAgent: ArchitectureAgentNode, conditionNode: ConditionNode, loopNode: LoopNode };
const agent = (n: number, x = 120, y = 120): WorkflowNodeDefinition => ({ id: id('agent'), type: 'agent', title: `对话窗口 ${n}`, role: 'Agent', responsibilities: [], prompt_template: '你的任务：\n{{input}}\n\n上游信息：\n{{upstream}}', position: { x, y } });
const globalNode = (node: WorkflowNodeDefinition, i: number): WorkflowNodeDefinition => ({ ...node, id: node.id || `agent_${i + 1}`, thread_id: undefined, position: node.position || { x: 130 + i * 230, y: 120 } });

export const WorkflowTab: React.FC<{ projectId?: string | null; conversationKey?: string }> = ({ projectId, conversationKey }) => {
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
  const [nodes, setNodes] = useState<WorkflowNodeDefinition[]>([]);
  const [edges, setEdges] = useState<WorkflowEdgeDefinition[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [runGroup, setRunGroup] = useState<Group | null>(null);
  const [runInput, setRunInput] = useState('');
  const [originThreadId, setOriginThreadId] = useState('');
  const [runLog, setRunLog] = useState<Array<{ title: string; status: string; output: string }>>([]);
  const [templatePickerOpen, setTemplatePickerOpen] = useState(false);
  const [reviseText, setReviseText] = useState('');
  const modelId = useChatStore((s) => s.selectedModel);
  const loadThreads = useChatStore((s) => s.loadThreads);
  const pendingInvocations = useOrchestrationInvokeStore((s) => s.pending);
  const consumeInvocation = useOrchestrationInvokeStore((s) => s.consume);
  const processingInvocations = useRef(new Set<string>());

  const reload = useCallback(async () => {
    try {
      const t = await fetchTopologyTemplates(); setTemplates(t.templates);
      if (projectId) { const g = await fetchGroups(projectId); setGroups(g.groups.filter((item) => item.group_mode === 'workflow' || item.group_mode === 'architecture')); }
      else setGroups([]);
    } catch (e) { setError(e instanceof Error ? e.message : '加载流程编排失败'); }
  }, [projectId]);
  useEffect(() => { void reload(); }, [reload]);
  useEffect(() => {
    const refreshTemplates = () => { void reload(); };
    window.addEventListener('orchestration:templates-updated', refreshTemplates);
    return () => window.removeEventListener('orchestration:templates-updated', refreshTemplates);
  }, [reload]);
  useEffect(() => {
    if (!projectId || !conversationKey) return;
    for (const invocation of pendingInvocations) {
      if (invocation.projectId !== projectId || invocation.conversationKey !== conversationKey || processingInvocations.current.has(invocation.requestId)) continue;
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
      if (group) { setSelectedTemplate(null); setSelectedGroup(group); setEditing(false); setRunGroup(null); }
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
        setDescription(group.goal || '');
        setNodes(arrangeNodes(group.nodes || [], group.edges || [], group.group_mode === 'architecture' ? 'architecture' : 'workflow'));
        setEdges(group.edges || []);
        setInfoPanelRequest((request) => request + 1);
      }
    };
    window.addEventListener('orchestration:edit-instance', editInstance);
    return () => window.removeEventListener('orchestration:edit-instance', editInstance);
  }, [projectId]);

  const startNew = () => { setSelectedTemplate(null); setSelectedGroup(null); setEditing(true); setKind('workflow'); setName(''); setDescription(''); setNodes([agent(1)]); setEdges([]); setError(''); };
  const chooseTemplate = (template: TopologyTemplate) => { setSelectedTemplate(template); setSelectedGroup(null); setKind(template.topology_type === 'architecture' ? 'architecture' : 'workflow'); setName(template.name); setDescription(template.description || ''); setNodes(arrangeNodes(template.nodes.map(globalNode), template.edges || [], template.topology_type === 'architecture' ? 'architecture' : 'workflow')); setEdges(template.edges || []); setEditing(true); setTemplatePickerOpen(false); };
  const editTemplate = (template: TopologyTemplate) => { setSelectedTemplate(template); setSelectedGroup(null); setEditing(true); setKind((template.topology_type === 'architecture' ? 'architecture' : 'workflow')); setName(template.name); setDescription(template.description || ''); setNodes(arrangeNodes(template.nodes.map(globalNode), template.edges || [], template.topology_type === 'architecture' ? 'architecture' : 'workflow')); setEdges(template.edges || []); };
  const editGroup = (group: Group) => { setSelectedGroup(group); setSelectedTemplate(null); setEditing(true); setKind(group.group_mode === 'architecture' ? 'architecture' : 'workflow'); setName(group.name); setDescription(group.goal || ''); setNodes(arrangeNodes(group.nodes || [], group.edges || [], group.group_mode === 'architecture' ? 'architecture' : 'workflow')); setEdges(group.edges || []); setInfoPanelRequest((request) => request + 1); };
  const saveDefinition = async () => {
    setBusy(true); setError('');
    try {
      if (!name.trim() || !nodes.some((n) => n.type === 'agent')) throw new Error('名称和至少一个对话窗口为必填项');
      if (globalMode) {
        const response = await saveTopologyTemplate({ template_id: selectedTemplate?.template_id, name: name.trim(), description, topology_type: kind, nodes, edges });
        setSelectedTemplate(response.template);
        window.dispatchEvent(new Event('orchestration:templates-updated'));
      } else if (projectId) {
        if (selectedGroup) await updateGroup(selectedGroup.group_id, { name: name.trim(), goal: description, group_mode: kind, nodes, edges, layout: {} }, projectId);
        else {
          const source = selectedTemplate;
          const result = await createGroupInstance({ project_id: projectId, template_id: source?.template_id, template_name: source?.name || name.trim(), group_mode: kind, name: name.trim(), description, nodes, edges, layout: {} });
          setSelectedGroup(result.group);
        }
        await loadThreads();
        window.dispatchEvent(new CustomEvent('orchestration:instances-updated', { detail: { projectId } }));
      }
      setEditing(false); await reload();
    } catch (e) { setError(e instanceof Error ? e.message : '保存失败'); }
    finally { setBusy(false); }
  };

  const run = async (choice: 'Y' | 'N' | 'O') => {
    if (choice === 'N') { setRunGroup(null); setRunLog([]); return; }
    if (choice === 'O') { setReviseText(runInput); return; }
    if (!projectId || !runGroup || !runInput.trim()) return;
    setBusy(true); setRunLog([]); setError('');
    let activeRunId = '';
    let savedRunNodes: Array<{ node_id: string; status: string; output: string }> = [];
    try {
      const { run: current } = await createGroupRun(runGroup.group_id, { project_id: projectId, confirmation: 'Y', input: runInput });
      await loadThreads();
      activeRunId = current.run_id;
      await updateGroupRun(runGroup.group_id, projectId, { run_id: current.run_id, status: 'running' });
      const runNodes: Array<{ node_id: string; status: string; output: string }> = [];
      const outputs = new Map<string, string>();
      const executionOrder: string[] = [];
      const byId = new Map((runGroup.nodes || []).map((n) => [n.id, n]));
      const sessionsByNode = new Map(current.sessions.map((session) => [session.node_id, session]));
      const allNodes = runGroup.nodes || [];
      const allEdges = runGroup.edges || [];
      const incoming = (nodeId: string) => allEdges.filter((edge) => edge.target === nodeId);
      const outgoing = (nodeId: string) => allEdges.filter((edge) => edge.source === nodeId);
      const root = allNodes.find((node) => node.type === 'agent' && !incoming(node.id).some((edge) => byId.get(edge.source)?.type !== 'loop'));
      if (!root) throw new Error('找不到流程起始对话窗口。请确保有一个没有上游窗口的起始节点。');
      const executionCount = new Map<string, number>();
      const loopCount = new Map<string, number>();
      const executed = new Set<string>();
      const stepLimit = Math.min(1000, Math.max(40, allNodes.length * 22));
      let steps = 0;
      let finalReviewContext = '';
      const invokeNode = async (node: WorkflowNodeDefinition, stage?: 'supervisor_review'): Promise<string> => {
        const session = sessionsByNode.get(node.id);
        if (!session) throw new Error(`节点「${node.title}」没有运行会话。`);
        const upstream = stage === 'supervisor_review' ? finalReviewContext : incoming(node.id).map((edge) => `${byId.get(edge.source)?.title || edge.source}: ${outputs.get(edge.source) || ''}`).filter(Boolean).join('\n\n');
        const count = (executionCount.get(node.id) || 0) + 1;
        executionCount.set(node.id, count);
        const logTitle = count > 1 ? `${node.title}（第 ${count} 轮）` : node.title;
        let output = '';
        setRunLog((old) => [...old, { title: logTitle, status: '运行中', output: '' }]);
        await new Promise<void>((resolve, reject) => {
          streamChat({ thread_id: session.thread_id, project_id: projectId, group_id: runGroup.group_id, model_id: modelId,
            content: stage === 'supervisor_review'
              ? `原始任务：\n${runInput}\n\n以下是流程终端窗口的执行结果，请逐项检查并形成最终答复：\n${upstream}`
              : `用户本次请求：\n${runInput}\n\n上游窗口传递的信息：\n${upstream || '（无）'}${node.type === 'condition' ? `\n\n判断条件：${String(node.config?.expression || '')}` : ''}${node.type === 'loop' ? `\n\n循环继续条件：${String(node.config?.continue_condition || '')}` : ''}`,
            workflow_input: runInput, workflow_upstream: upstream, workflow_stage: stage,
            onTextChunk: (chunk) => { output += chunk; setRunLog((old) => old.map((entry) => entry.title === logTitle ? { ...entry, output } : entry)); },
            onFinish: (payload) => payload.exit_status === 'finish' ? resolve() : reject(new Error(payload.exit_status === 'interrupted' ? `节点「${node.title}」被中断。` : `节点「${node.title}」对话失败。`)), onError: reject });
        });
        outputs.set(node.id, output);
        if (!stage && node.type === 'agent') executionOrder.push(node.id);
        runNodes.push({ node_id: node.id, status: 'completed', output });
        savedRunNodes = [...runNodes];
        await updateGroupRun(runGroup.group_id, projectId, { run_id: current.run_id, status: 'running', nodes: savedRunNodes });
        setRunLog((old) => old.map((entry) => entry.title === logTitle ? { ...entry, status: '已完成', output } : entry));
        return output;
      };
      const evaluateControl = async (node: WorkflowNodeDefinition): Promise<boolean> => {
        const result = (await invokeNode(node)).trim().toUpperCase();
        const answer = result.match(/^(YES|NO)[.!]?$/)?.[1];
        if (!answer) throw new Error(`节点「${node.title}」的判断结果不是严格的 YES/NO（收到：${result.slice(0, 80) || '空结果'}），已停止流程以免错误分支。`);
        return answer === 'YES';
      };
      if (runGroup.group_mode === 'architecture') {
        const queue = [root.id];
        while (queue.length) {
          if (++steps > stepLimit) throw new Error('架构超过安全执行步数，已停止。');
          const nodeId = queue.shift()!;
          if (executed.has(nodeId)) continue;
          const node = byId.get(nodeId);
          if (!node || node.type !== 'agent') continue;
          executed.add(nodeId); await invokeNode(node);
          outgoing(nodeId).forEach((edge) => queue.push(edge.target));
        }
      } else {
        const queue: Array<{ nodeId: string; via?: WorkflowEdgeDefinition }> = [{ nodeId: root.id }];
        while (queue.length) {
          if (++steps > stepLimit) throw new Error(`流程超过安全执行步数（${stepLimit}），已停止以防止死循环。`);
          const item = queue.shift()!;
          const nodeId = item.nodeId;
          const node = byId.get(nodeId);
          if (!node) continue;
          if (node.type === 'agent') {
            const wasExecuted = executed.has(nodeId);
            const isLoopReentry = item.via?.config?.sourceHandle === 'repeat' && byId.get(item.via.source)?.type === 'loop';
            if (wasExecuted && !isLoopReentry) continue;
            executed.add(nodeId); await invokeNode(node);
            outgoing(nodeId).forEach((edge) => queue.push({ nodeId: edge.target, via: edge }));
          } else if (node.type === 'condition') {
            const yes = await evaluateControl(node);
            outputs.set(nodeId, incoming(nodeId).map((edge) => `${byId.get(edge.source)?.title || edge.source}: ${outputs.get(edge.source) || ''}`).filter(Boolean).join('\n\n'));
            const handle = yes ? 'true' : 'false';
            const route = outgoing(nodeId).filter((edge) => edge.config?.sourceHandle === handle);
            if (!route.length) throw new Error(`判断节点「${node.title}」缺少“${yes ? '是' : '否'}”出口连线。`);
            route.forEach((edge) => queue.push({ nodeId: edge.target, via: edge }));
          } else if (node.type === 'loop') {
            const repeat = await evaluateControl(node);
            // The loop is a router: pass the worker's latest result back to the body,
            // rather than leaking the control token YES/NO as if it were task data.
            outputs.set(nodeId, incoming(nodeId).map((edge) => `${byId.get(edge.source)?.title || edge.source}: ${outputs.get(edge.source) || ''}`).filter(Boolean).join('\n\n'));
            const completedIterations = loopCount.get(nodeId) || 0;
            const maxIterations = Math.max(1, Math.min(20, Number(node.config?.max_iterations) || 3));
            const shouldRepeat = repeat && completedIterations < maxIterations;
            const handle = shouldRepeat ? 'repeat' : 'exit';
            const route = outgoing(nodeId).filter((edge) => edge.config?.sourceHandle === handle);
            if (!route.length) throw new Error(`循环节点「${node.title}」缺少“${shouldRepeat ? '循环' : '退出'}”出口连线。`);
            if (shouldRepeat) loopCount.set(nodeId, completedIterations + 1);
            else if (repeat) setRunLog((old) => [...old, { title: node.title, status: '达到次数上限，安全退出', output: `最多回跳 ${maxIterations} 次。` }]);
            route.forEach((edge) => queue.push({ nodeId: edge.target, via: edge }));
          } else throw new Error(`节点「${node.title}」的类型 ${node.type} 当前没有执行器。`);
        }
      }
      const reviewUpstream = allNodes.filter((node) => node.type === 'agent' && outputs.has(node.id)).map((node) => `${node.title}: ${outputs.get(node.id) || '（空结果）'}`).join('\n\n');
      finalReviewContext = reviewUpstream;
      const finalReviewerNode = byId.get(executionOrder.at(-1) || root.id) || root;
      const finalAnswer = await invokeNode(finalReviewerNode, 'supervisor_review');
      if (!finalAnswer.trim()) throw new Error('Supervisor 没有生成最终答复，未向原对话写入空结果。');
      setRunLog((old) => [...old, { title: `${finalReviewerNode.title} · Supervisor 验证`, status: '已完成并回传', output: finalAnswer }]);
      await updateGroupRun(runGroup.group_id, projectId, { run_id: current.run_id, status: 'completed', nodes: runNodes });
      if (originThreadId) {
        try { await useChatStore.getState().appendOrchestrationResult(originThreadId, { project_id: projectId, group_id: runGroup.group_id, run_id: current.run_id, input: runInput, content: finalAnswer }); }
        catch (deliveryError) { setError(`流程运行已完成，但回传原对话失败：${deliveryError instanceof Error ? deliveryError.message : '未知错误'}`); }
      }
    } catch (e) { setError(e instanceof Error ? e.message : '流程运行失败'); if (activeRunId && runGroup) await updateGroupRun(runGroup.group_id, projectId, { run_id: activeRunId, status: 'failed', nodes: savedRunNodes }).catch(() => undefined); }
    finally { setBusy(false); }
  };

  if (editing) return <Editor infoPanelRequest={infoPanelRequest} globalMode={globalMode} createActionLabel={!globalMode&&!selectedGroup?'创建分组并生成会话':undefined} kind={kind} setKind={setKind} name={name} setName={setName} description={description} setDescription={setDescription} nodes={nodes} setNodes={setNodes} edges={edges} setEdges={setEdges} error={error} busy={busy} onSave={() => void saveDefinition()} onCancel={() => setEditing(false)} />;
  if (globalMode) return <div style={{ height: '100%', overflow: 'auto', padding: 'var(--space-5)', color: 'var(--text-primary)' }}><header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}><div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)' }}>全局定义 · 项目使用时会创建独立副本</div><button style={styles.button} onClick={startNew}><Plus size={14}/>新建模板</button></header>{error && <ErrorText text={error}/>}<div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(230px,1fr))', gap: 'var(--space-2-5)' }}>{templates.map((template) => <article key={template.template_id} style={{ ...styles.card, padding: 'var(--space-3-5)' }}><div style={{ display: 'flex', justifyContent: 'space-between' }}><strong>{template.name}</strong>{template.topology_type === 'architecture' ? <Layers3 size={15} color="var(--accent-primary)"/> : <Workflow size={15} color="var(--accent-primary)"/>}</div><div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)', margin: 'var(--space-2) 0 var(--space-3)' }}>{template.topology_type === 'architecture' ? '架构' : '工作流'} · {template.nodes?.length || 0} 个窗口</div><button style={styles.button} onClick={() => editTemplate(template)}>编辑模板</button></article>)}</div>{templates.length === 0 && <Empty message="还没有全局模板，先创建一个架构或工作流。"/>}</div>;
  // The empty string is reserved for global-template management; only a missing project means no project scope.
  if (projectId === null || projectId === undefined) return <Empty message="请先打开项目，再创建项目内的流程编排实例。"/>;
  if (runGroup) return <div style={{ height: '100%', overflow: 'auto', padding: 'var(--space-4-5)', color: 'var(--text-primary)' }}><button style={styles.button} onClick={() => setRunGroup(null)}><ArrowLeft size={14}/>返回</button><h3>{runGroup.name} · 执行</h3><label style={{ display: 'block', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-2)' }}>本次任务<TextArea value={runInput} onChange={(e) => setRunInput(e.target.value)} rows={3} className="workflow-field workflow-run-input"/></label>{reviseText && <div style={{ color: 'var(--accent-primary)', fontSize: 'var(--font-size-compact)', marginBottom: 'var(--space-2)' }}>O 已选择修改：编辑上方任务内容后，点击 Y 执行才会启动。</div>}<div style={{ ...styles.card, padding: 'var(--space-3)', margin: 'var(--space-3) 0', fontSize: 'var(--font-size-sm)' }}><strong>Y 执行</strong> · N 取消 · O 修改后再执行。任务会进入起始窗口，工作结果由 Supervisor 验证后回传到发起对话。</div><div style={{ display: 'flex', gap: 'var(--space-1-75)' }}><button style={styles.button} disabled={busy || !runInput.trim()} onClick={() => void run('Y')}><Play size={13}/>Y 执行</button><button style={styles.button} disabled={busy} onClick={() => void run('N')}>N 取消</button><button style={styles.button} disabled={busy} onClick={() => void run('O')}>O 修改</button></div>{error && <ErrorText text={error}/>}<div style={{ marginTop: 'var(--space-4)' }}>{runLog.map((item, i) => <section key={`${item.title}-${i}`} style={{ ...styles.card, padding: 'var(--space-3)', marginBottom: 'var(--space-2)' }}><strong>{item.title}</strong><span style={{ marginLeft: 'var(--space-2-5)', color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)' }}>{item.status}</span><pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 'var(--font-size-sm)', lineHeight: 1.5 }}>{item.output || (item.status === '运行中' ? '正在接收模型流…' : '')}</pre></section>)}</div></div>;
  if (selectedGroup) return <div style={{ height: '100%', overflow: 'auto', padding: 'var(--space-4-5)', color: 'var(--text-primary)' }}><button style={styles.button} onClick={() => setSelectedGroup(null)}><ArrowLeft size={14}/>流程编排</button><header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'var(--space-4)' }}><div><h2 style={{ margin: 0, fontSize: 16 }}>{selectedGroup.name}</h2><div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)', marginTop: 'var(--space-1-25)' }}>{selectedGroup.group_mode === 'architecture' ? '架构' : '工作流'} · 来自模板「{selectedGroup.template_name || '自定义'}」</div></div><button style={styles.button} onClick={() => editGroup(selectedGroup)}>编辑</button></header><div style={{ height: '70%', marginTop: 'var(--space-3-5)' }}><Canvas kind={selectedGroup.group_mode === 'architecture' ? 'architecture' : 'workflow'} nodes={selectedGroup.nodes || []} edges={selectedGroup.edges || []} onChange={() => undefined} readOnly/></div></div>;
  return <div style={{ height: '100%', overflow: 'auto', padding: 'var(--space-4-5)', color: 'var(--text-primary)' }}><header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}><div><h2 style={{ margin: 0, fontSize: 16 }}>流程编排</h2><div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)', marginTop: 'var(--space-1-25)' }}>当前项目 · {groups.length} 个实例</div></div><div style={{ display: 'flex', gap: 'var(--space-1-75)' }}><button style={styles.button} onClick={startNew}><Plus size={14}/>空白编排</button><button style={styles.button} onClick={() => setTemplatePickerOpen(true)}><CopyPlus size={14}/>从全局模板创建</button></div></header>{error && <ErrorText text={error}/>}<div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(230px,1fr))', gap: 'var(--space-2-5)' }}>{groups.map((group) => <article key={group.group_id} style={{ ...styles.card, padding: 'var(--space-3-5)' }}><div style={{ display: 'flex', justifyContent: 'space-between' }}><strong>{group.name}</strong>{group.group_mode === 'architecture' ? <Layers3 size={15} color="var(--accent-primary)"/> : <Workflow size={15} color="var(--accent-primary)"/>}</div><div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)', margin: 'var(--space-1-75) 0 var(--space-3)' }}>{group.group_mode === 'architecture' ? '架构' : '工作流'} · {group.nodes?.length || 0} 个窗口 · {group.threads?.length || 0} 个会话窗口</div><div style={{ display: 'flex', gap: 'var(--space-1-5)' }}><button style={styles.button} onClick={() => editGroup(group)}>编辑</button><button style={styles.button} onClick={async () => { await deleteGroup(group.group_id, projectId); await reload(); await loadThreads(); }}>删除</button></div></article>)}</div>{groups.length === 0 && <Empty message="项目中还没有流程编排实例。选择全局模板后创建项目内副本。"/>}{templatePickerOpen&&<div role="presentation" onMouseDown={(event)=>{if(event.target===event.currentTarget)setTemplatePickerOpen(false)}} style={{position:'fixed',inset:0,zIndex:1000,background:'var(--overlay-scrim)',display:'grid',placeItems:'center',padding: 'var(--space-5)'}}><section role="dialog" aria-modal="true" aria-label="选择全局模板" style={{...styles.card,width:'min(560px,100%)',maxHeight:'min(620px,90vh)',padding: 'var(--space-4-5)',boxShadow:'var(--shadow-lg)',overflow:'auto'}}><header style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom: 'var(--space-3-5)'}}><div><strong style={{fontSize: 'var(--font-size-lg)'}}>从全局模板创建</strong><div style={{fontSize: 'var(--font-size-compact)',color:'var(--text-muted)',marginTop: 'var(--space-1)'}}>选择后会复制到当前项目，可继续编辑</div></div><button aria-label="关闭" style={styles.button} onClick={()=>setTemplatePickerOpen(false)}><X size={14}/></button></header>{templates.length===0?<Empty message="暂无全局模板，请先创建模板。"/>:<div style={{display:'grid',gap: 'var(--space-2)'}}>{templates.map((template)=><button key={template.template_id} onClick={()=>chooseTemplate(template)} style={{...styles.card,display:'flex',alignItems:'center',gap: 'var(--space-3)',padding: 'var(--space-3)',textAlign:'left',cursor:'pointer'}}><span style={{width:34,height:34,borderRadius: 'var(--radius-md-plus)',display:'grid',placeItems:'center',background:template.topology_type==='architecture'?'var(--bg-success-soft)':'var(--bg-info-soft)'}}>{template.topology_type==='architecture'?<Layers3 size={17} color="var(--accent-primary)"/>:<Workflow size={17} color="var(--accent-primary)"/>}</span><span style={{minWidth:0,flex:1}}><strong style={{display:'block'}}>{template.name}</strong><small style={{display:'block',color:'var(--text-muted)',marginTop: 'var(--space-1)'}}>{template.topology_type==='architecture'?'组织架构':'工作流'} · {template.nodes?.filter(node=>node.type==='agent').length||0} 个对话窗口</small></span><ArrowLeft size={14} style={{transform:'rotate(180deg)',color:'var(--text-muted)'}}/></button>)}</div>}</section></div>}</div>;
};

function Editor({ infoPanelRequest, globalMode, createActionLabel, kind, setKind, name, setName, description, setDescription, nodes, setNodes, edges, setEdges, error, busy, onSave, onCancel }: { infoPanelRequest:number; globalMode: boolean; createActionLabel?:string; kind: 'workflow'|'architecture'; setKind: (kind: 'workflow'|'architecture')=>void; name: string; setName: (value:string)=>void; description: string; setDescription:(value:string)=>void; nodes: WorkflowNodeDefinition[]; setNodes: React.Dispatch<React.SetStateAction<WorkflowNodeDefinition[]>>; edges: WorkflowEdgeDefinition[]; setEdges: React.Dispatch<React.SetStateAction<WorkflowEdgeDefinition[]>>; error:string; busy:boolean; onSave:()=>void; onCancel:()=>void }) {
  const [infoClosedAtRequest, setInfoClosedAtRequest] = useState<number | null>(null);
  const infoOpen = infoClosedAtRequest !== infoPanelRequest;
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState('');
  const [selectedEdgeId, setSelectedEdgeId] = useState('');
  const [canvasError, setCanvasError] = useState('');
  const selectedNode = nodes.find((node) => node.id === selectedNodeId);
  const architecture = kind === 'architecture';
  const historyRef = useRef<Array<{nodes:WorkflowNodeDefinition[];edges:WorkflowEdgeDefinition[]}>>([{nodes,edges}]);
  const cursorRef = useRef(0);
  const [historyStatus, setHistoryStatus] = useState({ cursor: 0, length: 1 });
  const refreshHistoryStatus = () => setHistoryStatus({ cursor: cursorRef.current, length: historyRef.current.length });
  const commitGraph = (nextNodes:WorkflowNodeDefinition[],nextEdges:WorkflowEdgeDefinition[]) => {
    setNodes(nextNodes); setEdges(nextEdges);
    historyRef.current=[...historyRef.current.slice(0,cursorRef.current+1),{nodes:nextNodes,edges:nextEdges}].slice(-50);
    cursorRef.current=historyRef.current.length-1; refreshHistoryStatus();
  };
  const moveHistory = useCallback((direction:-1|1) => {
    const next=Math.max(0,Math.min(historyRef.current.length-1,cursorRef.current+direction));
    if(next===cursorRef.current)return;
    cursorRef.current=next; const snapshot=historyRef.current[next]; setNodes(snapshot.nodes); setEdges(snapshot.edges); setSelectedEdgeId(''); refreshHistoryStatus();
  }, [setEdges, setNodes]);
  useEffect(()=>{const handleKey=(event:KeyboardEvent)=>{if(!(event.ctrlKey||event.metaKey)||event.key.toLowerCase()!=='z')return;const target=event.target as HTMLElement|null;if(target?.matches('input,textarea,[contenteditable="true"]'))return;event.preventDefault();moveHistory(event.shiftKey?1:-1)};window.addEventListener('keydown',handleKey);return()=>window.removeEventListener('keydown',handleKey)},[moveHistory]);
  const patch = (nodeId: string, changes: Partial<WorkflowNodeDefinition>) => commitGraph(nodes.map((node) => node.id === nodeId ? { ...node, ...changes } : node),edges);
  const addNode = (type: 'agent'|'condition'|'loop' = 'agent', placement: 'root'|'child'|'peer' = 'root', anchorId?:string) => {
    const anchor=nodes.find((node)=>node.id===(anchorId||selectedNodeId)&&node.type==='agent');
    const count=nodes.filter((node)=>node.type==='agent').length;
    const parentEdge = anchor ? edges.find((edge) => edge.target === anchor.id) : undefined;
    const parentId = architecture ? (placement === 'child' ? anchor?.id : placement === 'peer' ? parentEdge?.source : undefined) : undefined;
    const next: WorkflowNodeDefinition = type === 'agent' ? agent(count+1, 120+nodes.length*260, 140) : { id:id(type), type, title:type==='condition'?'分支判断':'循环', role:type==='condition'?'按条件选择后续路径':'满足条件时回到指定窗口', prompt_template:'', config:type==='condition'?{expression:'{{upstream}} 包含“完成”'}:{max_iterations:3}, position:{x:120+nodes.length*260,y:140} };
    const nextEdges = parentId ? [...edges, { id: id('edge'), source: parentId, target: next.id, relation: '组织汇报', label: '汇报关系' }] : edges;
    commitGraph(arrangeNodes([...nodes,next],nextEdges,kind),nextEdges);
    setCanvasError(''); setSelectedNodeId(next.id); setSelectedEdgeId(''); setPaletteOpen(false);
  };
  const nodeAction=(nodeId:string,action:'child'|'peer')=>{setSelectedNodeId(nodeId);addNode('agent',action,nodeId)};
  return <div style={{ height:'100%', display:'flex', flexDirection:'column', color:'var(--text-primary)', minHeight:0 }}>
    <header style={{ padding: 'var(--space-2-5) var(--space-3-5)', display:'flex', alignItems:'center', justifyContent:'space-between', borderBottom:'1px solid var(--border-subtle)' }}>
      <Button onClick={onCancel} variant="secondary" size="sm" className="workflow-action" icon={<ArrowLeft size={14} aria-hidden="true"/>}>返回</Button>
      <strong>{globalMode?'全局模板':'项目实例'} · {architecture?'组织架构':'工作流'}</strong>
      <div style={{display:'flex',gap: 'var(--space-1-5)'}}>
        <IconButton title="撤销" label="撤销" disabled={historyStatus.cursor===0} onClick={()=>moveHistory(-1)} size="sm"><Undo2 size={14}/></IconButton>
        <IconButton title="重做" label="重做" disabled={historyStatus.cursor>=historyStatus.length-1} onClick={()=>moveHistory(1)} size="sm"><Redo2 size={14}/></IconButton>
        {selectedEdgeId&&<Button variant="danger" size="sm" className="workflow-action" title="删除所选连线" onClick={()=>{commitGraph(nodes,edges.filter((edge)=>edge.id!==selectedEdgeId));setSelectedEdgeId('')}} icon={<Trash2 size={14} aria-hidden="true"/>}>删除连线</Button>}
        <Button variant="primary" size="sm" className="workflow-action" disabled={busy} onClick={onSave} icon={createActionLabel?<Play size={14} aria-hidden="true"/>:<Save size={14} aria-hidden="true"/>}>{createActionLabel|| (globalMode?'保存模板':'保存修改')}</Button>
      </div>
    </header>
    {error&&<ErrorText text={error}/>}
    <div style={{ flex:1,minHeight:0,position:'relative',overflow:'hidden' }}>
      <Canvas kind={kind} nodes={nodes} edges={edges} onChange={commitGraph} selectedNodeId={selectedNode?.id || ''} selectedEdgeId={selectedEdgeId} onSelectNode={(nodeId)=>{setSelectedNodeId(nodeId);if(nodeId)setSelectedEdgeId('');setCanvasError('')}} onSelectEdge={setSelectedEdgeId} onNodeAction={nodeAction} onError={setCanvasError}/>
      <div className="workflow-canvas-actions"><Button variant={infoOpen?'secondary':'ghost'} size="sm" className="workflow-action" onClick={()=>setInfoClosedAtRequest(infoOpen ? infoPanelRequest : null)} aria-expanded={infoOpen} icon={<Settings2 size={14} aria-hidden="true"/>}>基本信息</Button>{!architecture&&<Button variant={paletteOpen?'secondary':'ghost'} size="sm" className="workflow-action" onClick={()=>setPaletteOpen((v)=>!v)} aria-expanded={paletteOpen} icon={<Plus size={14} aria-hidden="true"/>}>添加节点</Button>}</div>
      {infoOpen&&<section className="workflow-float-panel workflow-info-panel"><Button variant="ghost" size="md" className="workflow-panel-heading" onClick={()=>setInfoClosedAtRequest(infoPanelRequest)}><span><Workflow size={14}/>基本信息</span><X size={14}/></Button><div className="workflow-panel-content"><label>名称<TextInput aria-label="编排名称" value={name} onChange={(e)=>setName(e.target.value)} placeholder="为编排命名" className="workflow-field"/></label><label>类型<SelectField aria-label="编排类型" value={kind} onChange={(e)=>{const next=e.target.value as 'workflow'|'architecture';setKind(next);commitGraph(arrangeNodes(nodes,edges,next),edges);setSelectedNodeId('')}} className="workflow-field"><option value="workflow">工作流</option><option value="architecture">组织架构</option></SelectField></label><label>简介<TextArea aria-label="编排说明" value={description} onChange={(e)=>setDescription(e.target.value)} placeholder={architecture?'说明组织目标与职责':'说明工作流目标'} rows={8} className="workflow-field workflow-description-field"/></label></div></section>}
      {paletteOpen&&!architecture&&<section className="workflow-float-panel workflow-node-panel"><Button variant="ghost" size="md" className="workflow-panel-heading" onClick={()=>setPaletteOpen(false)}><span><Plus size={14}/>选择节点</span><X size={14}/></Button><div className="workflow-panel-content workflow-node-actions"><Button variant="secondary" size="sm" className="workflow-action" onClick={()=>addNode('agent')} icon={<Bot size={13} aria-hidden="true"/>}>对话窗口</Button><Button variant="secondary" size="sm" className="workflow-action" onClick={()=>addNode('condition')} icon={<GitBranch size={13} aria-hidden="true"/>}>分支判断</Button><Button variant="secondary" size="sm" className="workflow-action" onClick={()=>addNode('loop')} icon={<GitFork size={13} aria-hidden="true"/>}>循环</Button><div className="workflow-capability-note">MCP、Skill 和 HTTP 当前没有节点级执行器，暂不能保证被强制调用。</div></div></section>}
      {canvasError&&<div role="alert" className="workflow-canvas-alert">{canvasError}</div>}
      {selectedNode&&<aside className="workflow-node-inspector"><div className="workflow-inspector-title"><div><h3>{selectedNode.title}</h3><small>{architecture?'职责窗口配置':selectedNode.type==='agent'?'对话窗口配置':selectedNode.type==='condition'?'判断条件配置':'循环节点配置'}</small></div><IconButton label="关闭节点配置" onClick={()=>setSelectedNodeId('')} size="sm"><X size={14}/></IconButton></div><label>节点名称<TextInput value={selectedNode.title} onChange={(e)=>patch(selectedNode.id,{title:e.target.value})} className="workflow-field"/></label><label>{architecture?'职位 / 职责':'说明'}<TextInput value={selectedNode.role||''} onChange={(e)=>patch(selectedNode.id,{role:e.target.value})} className="workflow-field"/></label>
        {selectedNode.type==='condition'&&<><label>判断条件<TextArea value={String(selectedNode.config?.expression||'')} onChange={(e)=>patch(selectedNode.id,{config:{...selectedNode.config,expression:e.target.value}})} rows={3} className="workflow-field" placeholder="描述判断条件，例如：上游结果已经通过验收"/></label><div className="workflow-capability-note">运行时由模型根据任务和上游结果判断是/否；只有严格返回 YES/NO 才继续，无法判断会停止流程。</div></>}
        {selectedNode.type==='loop'&&<><label>最大回跳次数<TextInput type="number" min={1} max={20} value={Number(selectedNode.config?.max_iterations||3)} onChange={(e)=>patch(selectedNode.id,{config:{...selectedNode.config,max_iterations:Math.max(1,Math.min(20,Number(e.target.value)||1))}})} className="workflow-field"/></label><label>继续循环的条件<TextArea value={String(selectedNode.config?.continue_condition||'')} onChange={(e)=>patch(selectedNode.id,{config:{...selectedNode.config,continue_condition:e.target.value}})} rows={3} className="workflow-field" placeholder="例如：实现结果未通过检查，需要返回修改"/></label><div className="workflow-capability-note">YES 沿“循环”出口把最新工作结果送回目标窗口；NO 沿“退出”出口前进。最多回跳 1–20 次，到上限强制走退出出口。每次判断不明确或连线缺失都会停止。</div></>}
        {selectedNode.type==='agent'&&<><label>{architecture?'职责范围':'任务提示词'}<TextArea value={architecture?(selectedNode.responsibilities||[]).join('\n'):(selectedNode.prompt_template||'')} onChange={(e)=>patch(selectedNode.id,architecture?{responsibilities:e.target.value.split('\n').filter(Boolean)}:{prompt_template:e.target.value})} rows={architecture?4:8} className="workflow-field" placeholder={architecture?'每行一项职责':'任务说明；可使用 {{input}} 与 {{upstream}}'}/></label>{!architecture&&<div className="workflow-capability-note">MCP / Skill 目前不能在此节点强制绑定；避免只靠提示词宣称工具必定执行。</div>}</>}
        <Button title="删除节点" variant="danger" size="sm" className="workflow-action workflow-node-delete" onClick={()=>{commitGraph(nodes.filter((n)=>n.id!==selectedNode.id),edges.filter((edge)=>edge.source!==selectedNode.id&&edge.target!==selectedNode.id));setSelectedNodeId('')}}>移除节点</Button>
      </aside>}
    </div>
  </div>;
}
function arrangeNodes(nodes: WorkflowNodeDefinition[], edges: WorkflowEdgeDefinition[], kind: 'workflow'|'architecture') {
  const agents = nodes.filter((node) => node.type === 'agent');
  const agentIds = new Set(agents.map((node) => node.id));
  const links = new Map<string, string[]>();
  edges.filter((edge) => agentIds.has(edge.source) && agentIds.has(edge.target)).forEach((edge) => links.set(edge.source, [...(links.get(edge.source) || []), edge.target]));
  const positions = new Map<string, {x:number;y:number}>();
  if (kind === 'workflow') {
    agents.forEach((node,index)=>positions.set(node.id,node.position||{x:100+index*250,y:140}));
  } else {
    let leafColumn=0;
    const visited=new Set<string>();
    const place=(nodeId:string,level:number):number=>{
      if(visited.has(nodeId)) return leafColumn++;
      visited.add(nodeId);
      const children=(links.get(nodeId)||[]).filter((child)=>!visited.has(child));
      let center:number;
      if(children.length===0) center=leafColumn++;
      else {const childColumns=children.map((child)=>place(child,level+1));center=(Math.min(...childColumns)+Math.max(...childColumns))/2;}
      positions.set(nodeId,{x:100+center*260,y:85+level*190});
      return center;
    };
    const roots=agents.filter((node)=>!edges.some((edge)=>edge.target===node.id&&agentIds.has(edge.source)));
    roots.forEach((root)=>place(root.id,0));
    agents.forEach((node)=>{if(!visited.has(node.id))place(node.id,0);});
  }
  return nodes.map((node)=>node.type==='agent'?{...node,position:positions.get(node.id)||node.position}:node);
}
function Canvas({kind,nodes,edges,onChange,readOnly=false,selectedNodeId,selectedEdgeId,onSelectNode,onSelectEdge,onNodeAction,onError}:{kind:'workflow'|'architecture';nodes:WorkflowNodeDefinition[];edges:WorkflowEdgeDefinition[];onChange:(nodes:WorkflowNodeDefinition[],edges:WorkflowEdgeDefinition[])=>void;readOnly?:boolean;selectedNodeId?:string;selectedEdgeId?:string;onSelectNode?:(id:string)=>void;onSelectEdge?:(id:string)=>void;onNodeAction?:(id:string,action:'child'|'peer')=>void;onError?:(message:string)=>void}) {
 const architecture = kind === 'architecture';
 const [collapsedIds,setCollapsedIds]=useState<Set<string>>(()=>new Set());
 const hiddenIds=useMemo(()=>{const hidden=new Set<string>();const visit=(parent:string)=>edges.filter((edge)=>edge.source===parent).forEach((edge)=>{if(hidden.has(edge.target))return;hidden.add(edge.target);if(collapsedIds.has(edge.target))return;visit(edge.target)});collapsedIds.forEach((parent)=>edges.filter((edge)=>edge.source===parent).forEach((edge)=>{if(!hidden.has(edge.target)){hidden.add(edge.target);visit(edge.target)}}));return hidden},[edges,collapsedIds]);
 const initialNodes=useMemo(()=>nodes.map((item)=>({id:item.id,position:item.position||{x:120,y:100},data:{node:item,hasChildren:edges.some((edge)=>edge.source===item.id),collapsed:collapsedIds.has(item.id),onToggle:()=>setCollapsedIds((old)=>{const next=new Set(old);if(next.has(item.id))next.delete(item.id);else next.add(item.id);return next})},type:architecture?'architectureAgent':item.type==='condition'?'conditionNode':item.type==='loop'?'loopNode':'workflowAgent',hidden:architecture&&hiddenIds.has(item.id),selected:item.id===selectedNodeId} as Node)),[nodes,edges,architecture,collapsedIds,hiddenIds,selectedNodeId]);
 const [flowNodes,setFlowNodes]=useNodesState(initialNodes); const [flowEdges,setFlowEdges]=useEdgesState(edges.map((item,index)=>({id:item.id||'edge_'+index,source:item.source,target:item.target,label:item.label||item.relation,labelStyle:edgeLabelStyle,labelShowBg:false,sourceHandle:architecture?'bottom':item.config?.sourceHandle as string|undefined,targetHandle:architecture?'top':undefined,style:{stroke:architecture?'var(--accent-emerald)':'var(--accent-primary)',strokeWidth:1.7},type:architecture?'smoothstep':'bezier'} as Edge)));
   useEffect(()=>{setFlowNodes(current=>{const currentById=new Map(current.map(node=>[node.id,node]));return nodes.map(def=>{const existing=currentById.get(def.id);return {id:def.id,position:def.position||existing?.position||{x:120,y:100},data:{node:def,hasChildren:edges.some((edge)=>edge.source===def.id),hasParent:edges.some((edge)=>edge.target===def.id),collapsed:collapsedIds.has(def.id),onToggle:()=>setCollapsedIds((old)=>{const next=new Set(old);if(next.has(def.id))next.delete(def.id);else next.add(def.id);return next}),onAction:(action:'child'|'peer')=>onNodeAction?.(def.id,action)},type:architecture?'architectureAgent':def.type==='condition'?'conditionNode':def.type==='loop'?'loopNode':'workflowAgent',hidden:architecture&&hiddenIds.has(def.id),selected:def.id===selectedNodeId} as Node})})},[nodes,edges,architecture,selectedNodeId,hiddenIds,collapsedIds,onNodeAction,setFlowNodes]);
   useEffect(()=>{setFlowEdges(edges.map((edge,index)=>({id:edge.id||'edge_'+index,source:edge.source,target:edge.target,label:edge.label||edge.relation,labelStyle:edgeLabelStyle,labelShowBg:false,sourceHandle:architecture?'bottom':edge.config?.sourceHandle as string|undefined,targetHandle:architecture?'top':undefined,style:{stroke:architecture?'var(--accent-emerald)':'var(--accent-primary)',strokeWidth:1.7},type:architecture?'smoothstep':'bezier',selected:(edge.id||'edge_'+index)===selectedEdgeId} as Edge)))},[edges,architecture,selectedEdgeId,setFlowEdges]);
 const serializeNodes=useCallback((updated:Node[])=>nodes.filter((def)=>updated.some((node)=>node.id===def.id)).map((def)=>({...def,position:updated.find((node)=>node.id===def.id)?.position||def.position})),[nodes]);
 const serializeEdges=useCallback((updated:Edge[])=>updated.map((edge)=>({id:edge.id,source:edge.source||'',target:edge.target||'',label:String(edge.label||''),relation:String(edge.label||(architecture?'组织汇报':'信息传递')),config:edge.sourceHandle?{sourceHandle:edge.sourceHandle}:undefined})),[architecture]);
 const handleNodesChange=useCallback((changes:NodeChange[])=>{
   const updated=applyNodeChanges(changes,flowNodes) as Node[];
   setFlowNodes(updated);
   if(changes.some((change)=>change.type==='remove'||(change.type==='position'&&change.dragging!==true))) {
     const survivingIds=new Set(updated.map((node)=>node.id));
     const survivingEdges=flowEdges.filter((edge)=>survivingIds.has(edge.source)&&survivingIds.has(edge.target));
     onChange(serializeNodes(updated),serializeEdges(survivingEdges));
   }
 },[flowNodes,flowEdges,setFlowNodes,onChange,serializeNodes,serializeEdges]);
 const handleEdgesChange=useCallback((changes:EdgeChange[])=>{
   const updated=applyEdgeChanges(changes,flowEdges) as Edge[];
   setFlowEdges(updated);
    if(changes.some((change)=>change.type==='remove')) { onSelectEdge?.(''); onChange(serializeNodes(flowNodes),serializeEdges(updated)); }
  },[flowNodes,flowEdges,setFlowEdges,onChange,serializeNodes,serializeEdges,onSelectEdge]);
  const connect=useCallback((connection:Connection)=>{
   if (!connection.source || !connection.target || connection.source === connection.target) return;
    const reachesTarget=(from:string,target:string,seen=new Set<string>()):boolean=>{if(from===target)return true;if(seen.has(from))return false;seen.add(from);return flowEdges.filter((edge)=>edge.source===from).some((edge)=>reachesTarget(edge.target,target,seen));};
    if (architecture) {
      if (flowEdges.some((edge)=>edge.target===connection.target)) { onError?.('每个职责窗口只能有一个直接上级。'); return; }
      if (reachesTarget(connection.target,connection.source)) { onError?.('该连线会形成循环，请按层级关系连接。'); return; }
    } else if (reachesTarget(connection.target,connection.source)) {
      const sourceNode=nodes.find((node)=>node.id===connection.source);
      const maxIterations=Number(sourceNode?.config?.max_iterations||0);
      if (sourceNode?.type!=='loop'||connection.sourceHandle!=='repeat'||!Number.isInteger(maxIterations)||maxIterations<1||maxIterations>20) {
        onError?.('回流必须从“循环”节点的循环出口连接，并设置 1–20 次上限；判断节点的“否”出口请先连接到循环节点。'); return;
      }
    }
   onError?.('');
   const sourceNode=nodes.find((node)=>node.id===connection.source);
    const routeLabel=sourceNode?.type==='condition'?(connection.sourceHandle==='false'?'否':'是'):sourceNode?.type==='loop'?(connection.sourceHandle==='repeat'?'循环':'退出'):architecture?'汇报关系':'传递上游结果';
   const updated=addEdge({...connection,label:routeLabel,labelStyle:edgeLabelStyle,labelShowBg:false,type:architecture?'smoothstep':'bezier',style:{stroke:architecture?'var(--accent-emerald)':'var(--accent-primary)',strokeWidth:1.7}},flowEdges);
   setFlowEdges(updated);
   onChange(serializeNodes(flowNodes),serializeEdges(updated));
  },[setFlowEdges,architecture,flowEdges,onError,flowNodes,nodes,onChange,serializeNodes,serializeEdges]);
  return <div className={architecture?'workflow-canvas architecture-canvas':'workflow-canvas business-flow-canvas'} style={{height:'100%',minHeight:300,background:architecture?'radial-gradient(ellipse at 50% 0%,color-mix(in srgb, var(--accent-emerald) 11%, transparent),transparent 60%)':'radial-gradient(ellipse at 0% 50%,color-mix(in srgb, var(--accent-primary) 12%, transparent),transparent 60%)'}}>
    <ReactFlowProvider><ReactFlow nodes={flowNodes} edges={flowEdges} nodeTypes={workflowNodeTypes} onNodeClick={(_,node)=>{onSelectNode?.(node.id);onSelectEdge?.('')}} onEdgeClick={(_,edge)=>{onSelectEdge?.(edge.id);onSelectNode?.('')}} onNodesChange={handleNodesChange} onEdgesChange={handleEdgesChange} onConnect={connect} deleteKeyCode={['Backspace','Delete']} nodesDraggable={!readOnly} nodesConnectable={!readOnly} elementsSelectable={!readOnly} selectionOnDrag={!readOnly} selectionMode={SelectionMode.Partial} panOnDrag={[1,2]} fitView fitViewOptions={{padding:.3,maxZoom:.72}} minZoom={.2} maxZoom={1.8} defaultEdgeOptions={{type:architecture?'smoothstep':'bezier', animated:true}} connectionLineStyle={{stroke:architecture?'var(--accent-emerald)':'var(--accent-primary)',strokeWidth:2}} proOptions={{hideAttribution:true}}>
    <Background variant={BackgroundVariant.Dots} gap={architecture?26:20} size={1} color="var(--border-default)"/><CanvasToolbar nodes={nodes} selectedNodes={flowNodes.filter((node)=>node.selected).map((node)=>node.id)} readOnly={readOnly} onDeleteSelected={()=>{const selectedIds=new Set(flowNodes.filter((node)=>node.selected).map((node)=>node.id));if(!selectedIds.size)return;const remainingNodes=nodes.filter((node)=>!selectedIds.has(node.id));const remainingEdges=edges.filter((edge)=>!selectedIds.has(edge.source)&&!selectedIds.has(edge.target));onChange(remainingNodes,remainingEdges);onSelectNode?.('');onSelectEdge?.('')}} onFind={(nodeId)=>{onSelectNode?.(nodeId);onSelectEdge?.('')}}/><FitView count={flowNodes.length}/>
   </ReactFlow></ReactFlowProvider>
 </div>;
}
function WorkflowAgentNode({data,selected}:NodeProps){const {node}=data as {node:WorkflowNodeDefinition};return <div style={{minWidth:178,maxWidth:218,padding: 'var(--space-3) var(--space-3-5)',borderRadius: 'var(--radius-md-wide)',border:'1px solid '+(selected?'var(--accent-primary)':'var(--border-default)'),background:'var(--bg-card)',color:'var(--text-primary)',boxShadow:selected?'var(--shadow-md)':'var(--shadow-sm)'}}><Handle type="target" position={Position.Left}/><div style={{fontSize:'var(--font-size-tiny)',color: 'var(--accent-primary)',letterSpacing:'.04em',marginBottom: 'var(--space-1-5)'}}>业务步骤</div><div style={{display:'flex',gap: 'var(--space-1-75)',alignItems:'center',fontSize: 'var(--font-size-sm)',fontWeight:650}}><Bot size={14} color="var(--accent-primary)"/>{node.title}</div><div style={{fontSize: 'var(--font-size-xs)',color:'var(--text-muted)',marginTop: 'var(--space-1-25)'}}>{node.role||'对话窗口'} · 输出传给下游</div><Handle type="source" position={Position.Right}/></div>}
function ConditionNode({data,selected}:NodeProps){const {node}=data as {node:WorkflowNodeDefinition};return <div className="workflow-special-node condition-node" style={{borderColor:selected?'var(--accent-primary)':undefined}}><Handle type="target" position={Position.Left}/><div className="workflow-special-heading"><GitBranch size={15}/>分支判断</div><strong>{node.title}</strong><small>{String(node.config?.expression||'配置判断表达式')}</small><Handle id="true" type="source" position={Position.Right} style={{top:'35%',background: 'color-mix(in srgb, var(--accent-emerald) 9%, var(--bg-surface))'}}/><span className="workflow-port-label true-port">是</span><Handle id="false" type="source" position={Position.Right} style={{top:'72%',background: 'color-mix(in srgb, var(--accent-amber) 9%, var(--bg-surface))'}}/><span className="workflow-port-label false-port">否</span></div>}
function LoopNode({data,selected}:NodeProps){const {node}=data as {node:WorkflowNodeDefinition};return <div className="workflow-special-node loop-node" style={{borderColor:selected?'var(--accent-emerald)':undefined}}><Handle type="target" position={Position.Left}/><div className="workflow-special-heading"><GitFork size={15}/>循环</div><strong>{node.title}</strong><small>最多 {Number(node.config?.max_iterations||3)} 次 · 连接“循环”出口回到窗口</small><Handle id="repeat" type="source" position={Position.Bottom} style={{background: 'color-mix(in srgb, var(--accent-amber) 9%, var(--bg-surface))'}}/><span className="workflow-port-label loop-port">循环</span><Handle id="exit" type="source" position={Position.Right} style={{background: 'color-mix(in srgb, var(--accent-emerald) 9%, var(--bg-surface))'}}/></div>}
function ArchitectureAgentNode({data,selected}:NodeProps){const {node,hasChildren,hasParent,collapsed,onToggle,onAction}=data as {node:WorkflowNodeDefinition;hasChildren:boolean;hasParent:boolean;collapsed:boolean;onToggle:()=>void;onAction:(action:'child'|'peer')=>void};const act=(event:React.MouseEvent,action:'child'|'peer')=>{event.stopPropagation();onAction(action)};return <div className="architecture-node-card" style={{borderColor:selected?'var(--accent-emerald)':undefined}}><Handle id="top" type="target" position={Position.Top}/><div className="architecture-node-actions" role="toolbar" aria-label={`${node.title} 节点操作`}><button title="添加下级" aria-label="添加下级" onClick={(event)=>act(event,'child')}><Plus size={14}/></button><button title="添加同级" aria-label="添加同级" disabled={!hasParent} onClick={(event)=>act(event,'peer')}><GitBranch size={13}/></button></div><div className="architecture-node-eyebrow">组织职责窗口</div><div className="architecture-node-name"><Layers3 size={14} color="var(--accent-emerald)"/>{node.title}</div><div className="architecture-node-role">{node.role||'职责待定义'}</div>{node.responsibilities?.[0]&&<div className="architecture-node-responsibility">{node.responsibilities[0]}</div>}<Handle id="bottom" type="source" position={Position.Bottom}/>{hasChildren&&<button className="architecture-collapse-button" aria-label={collapsed?'展开下级':'收起下级'} title={collapsed?'展开下级':'收起下级'} onClick={(event)=>{event.stopPropagation();onToggle()}}>{collapsed?<Plus size={12}/>:<Minus size={12}/>}</button>}</div>}
function CanvasToolbar({nodes,selectedNodes,readOnly,onDeleteSelected,onFind}:{nodes:WorkflowNodeDefinition[];selectedNodes:string[];readOnly:boolean;onDeleteSelected:()=>void;onFind:(id:string)=>void}) {
 const {zoomIn,zoomOut,fitView}=useReactFlow();
 const [query,setQuery]=useState('');
 const [open,setOpen]=useState(false);
 const matches=nodes.filter((item)=>`${item.title} ${item.role||''} ${(item.responsibilities||[]).join(' ')}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())).slice(0,8);
 const choose=(node:WorkflowNodeDefinition)=>{onFind(node.id);setOpen(false);void fitView({nodes:[{id:node.id}],duration:300,padding:.5,maxZoom:1.1})};
 return <><div className="workflow-canvas-toolbar">
  <button className="workflow-icon-button" title="放大" aria-label="放大" onClick={()=>void zoomIn({duration:120})}><ZoomIn size={17}/></button>
  <button className="workflow-icon-button" title="缩小" aria-label="缩小" onClick={()=>void zoomOut({duration:120})}><ZoomOut size={17}/></button>
  <button className="workflow-icon-button" title="适配全部节点" aria-label="适配全部节点" onClick={()=>void fitView({duration:220,padding:.3})}><LocateFixed size={17}/></button>
  <button className="workflow-icon-button" title="搜索节点" aria-label="搜索节点" onClick={()=>{setOpen(true);setQuery('')}}><Search size={17}/></button>
  {selectedNodes.length>1&&!readOnly&&<button className="workflow-selection-delete" title={`删除选中的 ${selectedNodes.length} 个节点`} onClick={onDeleteSelected}><Trash2 size={14}/><span>删除 {selectedNodes.length}</span></button>}
 </div>{open&&<div className="workflow-search-backdrop" onMouseDown={(event)=>{if(event.target===event.currentTarget)setOpen(false)}}><section className="workflow-search-dialog" role="dialog" aria-modal="true" aria-label="搜索节点">
  <div className="workflow-search-input-wrap"><Search size={17}/><TextInput autoFocus value={query} onChange={(event)=>setQuery(event.target.value)} onKeyDown={(event)=>{if(event.key==='Enter'&&matches[0])choose(matches[0]);if(event.key==='Escape')setOpen(false)}} placeholder="搜索名称或职责…" aria-label="搜索名称或职责"/><button className="workflow-icon-button" aria-label="关闭搜索" onClick={()=>setOpen(false)}><X size={16}/></button></div>
  <div className="workflow-search-results">{query.trim()?matches.length?matches.map((node)=><button key={node.id} className="workflow-search-result" onClick={()=>choose(node)}><strong>{node.title}</strong><span>{node.role||node.type}</span></button>):'没有找到匹配的节点':'搜索名称或职责…'}</div>
 </section></div>}</>;
}
function FitView({count}:{count:number}){const {fitView}=useReactFlow();useEffect(()=>{const timer=setTimeout(()=>void fitView({padding:.3,maxZoom:.72,duration:180}),60);return()=>clearTimeout(timer)},[count,fitView]);return null}
function Empty({message}:{message:string}){return <EmptyState icon={<Workflow size={25}/>} description={message} className="workflow-empty-state" />}
function ErrorText({text}:{text:string}){return <div role="alert" style={{margin: 'var(--space-2) var(--space-3)',padding: 'var(--space-2-25)',color: 'var(--accent-rose)',background:'var(--bg-danger-soft)',border:'1px solid var(--border-danger-soft)',borderRadius: 'var(--radius-sm-plus)',fontSize: 'var(--font-size-compact)'}}>{text}</div>}
