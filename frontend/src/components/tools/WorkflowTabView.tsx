import '@xyflow/react/dist/style.css';
import { ArrowLeft, CopyPlus, Layers3, Play, Plus, Workflow, X } from 'lucide-react';
import { deleteGroup } from '../../api/projectApi';
import { TextArea } from '../common/Field';
import { Canvas } from './WorkflowCanvas';
import { Editor } from './WorkflowEditor';
import { Empty, ErrorText, RunLogCard } from './WorkflowPanels';
import { useWorkflowTab } from './useWorkflowTab';
import './workflow.css';
import { styles } from './workflowShared';

export function WorkflowTabView({
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
}: ReturnType<typeof useWorkflowTab>) {
  if (editing)
    return (
      <Editor
        infoPanelRequest={infoPanelRequest}
        globalMode={globalMode}
        createActionLabel={!globalMode && !selectedGroup ? '创建分组并生成会话' : undefined}
        kind={kind}
        setKind={setKind}
        name={name}
        setName={setName}
        description={description}
        setDescription={setDescription}
        projectGoal={projectGoal}
        setProjectGoal={setProjectGoal}
        projectBackground={projectBackground}
        setProjectBackground={setProjectBackground}
        nodes={nodes}
        setNodes={setNodes}
        edges={edges}
        setEdges={setEdges}
        error={error}
        busy={busy}
        onSave={() => void saveDefinition()}
        onCancel={() => setEditing(false)}
      />
    );
  if (globalMode)
    return (
      <div style={{ height: '100%', overflow: 'auto', padding: 'var(--space-5)', color: 'var(--text-primary)' }}>
        <header
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 'var(--space-4)',
          }}
        >
          <div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)' }}>
            全局定义 · 项目使用时会创建独立副本
          </div>
          <button style={styles.button} onClick={startNew}>
            <Plus size={14} />
            新建模板
          </button>
        </header>
        {error && <ErrorText text={error} />}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill,minmax(230px,1fr))',
            gap: 'var(--space-2-5)',
          }}
        >
          {templates.map((template) => (
            <article key={template.template_id} style={{ ...styles.card, padding: 'var(--space-3-5)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong>{template.name}</strong>
                {template.topology_type === 'architecture' ? (
                  <Layers3 size={15} color="var(--accent-primary)" />
                ) : (
                  <Workflow size={15} color="var(--accent-primary)" />
                )}
              </div>
              <div
                style={{
                  color: 'var(--text-muted)',
                  fontSize: 'var(--font-size-compact)',
                  margin: 'var(--space-2) 0 var(--space-3)',
                }}
              >
                {template.topology_type === 'architecture' ? '架构' : '工作流'} · {template.nodes?.length || 0} 个窗口
              </div>
              <button style={styles.button} onClick={() => editTemplate(template)}>
                编辑模板
              </button>
            </article>
          ))}
        </div>
        {templates.length === 0 && <Empty message="还没有全局模板，先创建一个架构或工作流。" />}
      </div>
    );
  if (projectId === null || projectId === undefined)
    return <Empty message="请先打开项目，再创建项目内的流程编排实例。" />;
  if (runGroup)
    return (
      <div style={{ height: '100%', overflow: 'auto', padding: 'var(--space-4-5)', color: 'var(--text-primary)' }}>
        <button style={styles.button} onClick={() => setRunGroup(null)}>
          <ArrowLeft size={14} />
          返回
        </button>
        <h3>{runGroup.name} · 执行</h3>
        <label style={{ display: 'block', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-2)' }}>
          本次任务
          <TextArea
            value={runInput}
            onChange={(e) => setRunInput(e.target.value)}
            rows={3}
            className="workflow-field workflow-run-input"
          />
        </label>
        {reviseText && (
          <div
            style={{
              color: 'var(--accent-primary)',
              fontSize: 'var(--font-size-compact)',
              marginBottom: 'var(--space-2)',
            }}
          >
            O 已选择修改：编辑上方任务内容后，点击 Y 执行才会启动。
          </div>
        )}
        <div
          style={{
            ...styles.card,
            padding: 'var(--space-3)',
            margin: 'var(--space-3) 0',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          <strong>Y 执行</strong> · N 取消 · O 修改后再执行。任务会进入起始窗口，工作结果由 Supervisor
          验证后回传到发起对话。
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-1-75)' }}>
          <button style={styles.button} disabled={busy || !runInput.trim()} onClick={() => void run('Y')}>
            <Play size={13} />Y 执行
          </button>
          <button style={styles.button} disabled={busy} onClick={() => void run('N')}>
            N 取消
          </button>
          <button style={styles.button} disabled={busy} onClick={() => void run('O')}>
            O 修改
          </button>
        </div>
        {error && <ErrorText text={error} />}
        <div style={{ marginTop: 'var(--space-4)' }}>
          {runLog.map((item, i) => (
            <RunLogCard key={`${item.title}-${i}`} item={item} />
          ))}
        </div>
      </div>
    );
  if (selectedGroup)
    return (
      <div style={{ height: '100%', overflow: 'auto', padding: 'var(--space-4-5)', color: 'var(--text-primary)' }}>
        <button style={styles.button} onClick={() => setSelectedGroup(null)}>
          <ArrowLeft size={14} />
          流程编排
        </button>
        <header
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: 'var(--space-4)',
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: 16 }}>{selectedGroup.name}</h2>
            <div
              style={{
                color: 'var(--text-muted)',
                fontSize: 'var(--font-size-compact)',
                marginTop: 'var(--space-1-25)',
              }}
            >
              {selectedGroup.group_mode === 'architecture' ? '架构' : '工作流'} · 来自模板「
              {selectedGroup.template_name || '自定义'}」
            </div>
          </div>
          <button style={styles.button} onClick={() => editGroup(selectedGroup)}>
            编辑
          </button>
        </header>
        <div style={{ height: '70%', marginTop: 'var(--space-3-5)' }}>
          <Canvas
            kind={selectedGroup.group_mode === 'architecture' ? 'architecture' : 'workflow'}
            nodes={selectedGroup.nodes || []}
            edges={selectedGroup.edges || []}
            onChange={() => undefined}
            readOnly
          />
        </div>
      </div>
    );
  return (
    <div style={{ height: '100%', overflow: 'auto', padding: 'var(--space-4-5)', color: 'var(--text-primary)' }}>
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--space-4)',
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: 16 }}>流程编排</h2>
          <div
            style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-compact)', marginTop: 'var(--space-1-25)' }}
          >
            当前项目 · {groups.length} 个实例
          </div>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-1-75)' }}>
          <button style={styles.button} onClick={startNew}>
            <Plus size={14} />
            空白编排
          </button>
          <button style={styles.button} onClick={() => setTemplatePickerOpen(true)}>
            <CopyPlus size={14} />
            从全局模板创建
          </button>
        </div>
      </header>
      {error && <ErrorText text={error} />}
      <div
        style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(230px,1fr))', gap: 'var(--space-2-5)' }}
      >
        {groups.map((group) => (
          <article key={group.group_id} style={{ ...styles.card, padding: 'var(--space-3-5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <strong>{group.name}</strong>
              {group.group_mode === 'architecture' ? (
                <Layers3 size={15} color="var(--accent-primary)" />
              ) : (
                <Workflow size={15} color="var(--accent-primary)" />
              )}
            </div>
            <div
              style={{
                color: 'var(--text-muted)',
                fontSize: 'var(--font-size-compact)',
                margin: 'var(--space-1-75) 0 var(--space-3)',
              }}
            >
              {group.group_mode === 'architecture' ? '架构' : '工作流'} · {group.nodes?.length || 0} 个窗口 ·{' '}
              {group.threads?.length || 0} 个会话窗口
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-1-5)' }}>
              <button style={styles.button} onClick={() => editGroup(group)}>
                编辑
              </button>
              <button
                style={styles.button}
                onClick={async () => {
                  await deleteGroup(group.group_id, projectId);
                  await reload();
                  await loadThreads();
                }}
              >
                删除
              </button>
            </div>
          </article>
        ))}
      </div>
      {groups.length === 0 && <Empty message="项目中还没有流程编排实例。选择全局模板后创建项目内副本。" />}
      {templatePickerOpen && (
        <div
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setTemplatePickerOpen(false);
          }}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1000,
            background: 'var(--overlay-scrim)',
            display: 'grid',
            placeItems: 'center',
            padding: 'var(--space-5)',
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-label="选择全局模板"
            style={{
              ...styles.card,
              width: 'min(560px,100%)',
              maxHeight: 'min(620px,90vh)',
              padding: 'var(--space-4-5)',
              boxShadow: 'var(--shadow-lg)',
              overflow: 'auto',
            }}
          >
            <header
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 'var(--space-3-5)',
              }}
            >
              <div>
                <strong style={{ fontSize: 'var(--font-size-lg)' }}>从全局模板创建</strong>
                <div
                  style={{
                    fontSize: 'var(--font-size-compact)',
                    color: 'var(--text-muted)',
                    marginTop: 'var(--space-1)',
                  }}
                >
                  选择后会复制到当前项目，可继续编辑
                </div>
              </div>
              <button aria-label="关闭" style={styles.button} onClick={() => setTemplatePickerOpen(false)}>
                <X size={14} />
              </button>
            </header>
            {templates.length === 0 ? (
              <Empty message="暂无全局模板，请先创建模板。" />
            ) : (
              <div style={{ display: 'grid', gap: 'var(--space-2)' }}>
                {templates.map((template) => (
                  <button
                    key={template.template_id}
                    onClick={() => chooseTemplate(template)}
                    style={{
                      ...styles.card,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--space-3)',
                      padding: 'var(--space-3)',
                      textAlign: 'left',
                      cursor: 'pointer',
                    }}
                  >
                    <span
                      style={{
                        width: 34,
                        height: 34,
                        borderRadius: 'var(--radius-md-plus)',
                        display: 'grid',
                        placeItems: 'center',
                        background:
                          template.topology_type === 'architecture' ? 'var(--bg-success-soft)' : 'var(--bg-info-soft)',
                      }}
                    >
                      {template.topology_type === 'architecture' ? (
                        <Layers3 size={17} color="var(--accent-primary)" />
                      ) : (
                        <Workflow size={17} color="var(--accent-primary)" />
                      )}
                    </span>
                    <span style={{ minWidth: 0, flex: 1 }}>
                      <strong style={{ display: 'block' }}>{template.name}</strong>
                      <small style={{ display: 'block', color: 'var(--text-muted)', marginTop: 'var(--space-1)' }}>
                        {template.topology_type === 'architecture' ? '组织架构' : '工作流'} ·{' '}
                        {template.nodes?.filter((node) => node.type === 'agent').length || 0} 个对话窗口
                      </small>
                    </span>
                    <ArrowLeft size={14} style={{ transform: 'rotate(180deg)', color: 'var(--text-muted)' }} />
                  </button>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
