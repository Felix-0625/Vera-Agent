const scenarioList = document.querySelector('#scenario-list');
const messages = document.querySelector('#demo-messages');
const inspector = document.querySelector('#inspector-panel');
const projectTitle = document.querySelector('#demo-project');
const taskId = document.querySelector('#demo-task-id');
const runStatus = document.querySelector('#run-status');
const input = document.querySelector('#demo-input');
const runButton = document.querySelector('.send-button');

const scenarios = [
  {
    id: 'VA-101',
    title: '排查任务状态同步',
    priority: '高',
    status: 'todo',
    prompt: '检查任务从 Agent 执行完成后，任务板状态是否会同步；给出需要验证的边界。',
    goal: '确认任务状态与 Agent 对话的关联边界，并列出验证路径。',
    background: '这是一个本地项目；任务板记录状态，关联的对话属于同一项目。',
    phases: [
      { id: 'main', role: '主 Agent', title: '拆解目标', detail: '明确要核对的状态转换、会话关联和项目归属。', result: '目标拆为状态转换、对话归属和异常恢复三项。', tool: '读取任务板约定（模拟）' },
      { id: 'research', role: '分析 Agent', title: '检查数据流', detail: '沿任务状态更新和对话关联路径检查输入输出。', result: '状态更新需要携带版本；会话必须属于同一项目。', tool: '检查 API 约定（模拟）' },
      { id: 'review', role: '审查 Agent', title: '核对边界', detail: '检查并发修改、跨项目关联和失败后的状态。', result: '重点验证冲突返回、跨项目拒绝，以及失败后不误标完成。', tool: '整理验证点（模拟）' },
      { id: 'summary', role: '主 Agent', title: '汇总结果', detail: '整合分析与审查输出，返回任务板关联对话。', result: '给出可执行的验证清单，不宣称本地代码已被修改或测试。', tool: '汇总协作结果（模拟）' },
    ],
    output: '建议验证四条路径：成功运行后状态进入“进行中”并可标记完成；Agent 失败时不能标成完成；并发更新返回冲突后刷新再试；跨项目对话关联必须被拒绝。此演示只呈现预设建议，没有读取或修改真实代码。',
  },
  {
    id: 'VA-102',
    title: '审查工作流信息传递',
    priority: '中',
    status: 'todo',
    prompt: '梳理工作流节点如何接收上游结果、输出给下游，并指出需要观察的运行记录。',
    goal: '检查节点输入、输出和运行轨迹是否可以追溯。',
    background: '工作流实例包含对话窗口与控制节点；每次运行独立记录节点状态。',
    phases: [
      { id: 'main', role: '主 Agent', title: '拆解目标', detail: '明确需要检查输入来源、节点结果和最终返回。', result: '运行检查分为上游注入、节点输出和终态回传。', tool: '读取工作流说明（模拟）' },
      { id: 'research', role: '流程 Agent', title: '沿节点追踪', detail: '逐步核对节点之间的依赖与结果传递关系。', result: '下游节点应收到明确标注来源的上游输出。', tool: '检查节点连线（模拟）' },
      { id: 'review', role: '审查 Agent', title: '检查运行状态', detail: '核对成功、失败、跳过和结果回传等状态。', result: '每个节点需要可见状态、输入来源和输出摘要；失败应停止后续步骤。', tool: '核对运行事件（模拟）' },
      { id: 'summary', role: '主 Agent', title: '汇总结果', detail: '将可观测要求整理为验收清单。', result: '建议按一次真实运行记录核验每个节点的输入、输出、状态和最终结果。', tool: '生成核验清单（模拟）' },
    ],
    output: '运行记录至少要能回答：哪个节点在执行、收到了什么上游内容、返回了什么、是否失败或跳过，以及最终结果返回到哪个对话。单看模板连线或 HTTP 成功响应不足以证明流程执行完成。',
  },
  {
    id: 'VA-103',
    title: '规划一次代码审查协作',
    priority: '中',
    status: 'backlog',
    prompt: '为一次小型代码审查安排分析、实现建议和复核角色，说明结果如何汇总。',
    goal: '演示组织架构中的角色分工与主 Agent 汇总。',
    background: '每个 Agent 窗口有自己的职责；模型配置沿用发起对话的选择。',
    phases: [
      { id: 'main', role: '主 Agent', title: '分配任务', detail: '按角色将审查目标拆给协作窗口。', result: '主 Agent 保留目标和边界，分配可独立完成的检查项。', tool: '生成角色任务（模拟）' },
      { id: 'research', role: '分析 Agent', title: '定位风险', detail: '先找调用路径与关键状态边界。', result: '提交风险位置、证据和不确定点。', tool: '检查代码范围（模拟）' },
      { id: 'review', role: '复核 Agent', title: '独立复核', detail: '检查分析是否有证据，识别遗漏的测试场景。', result: '只保留可复现的问题与可验证的建议。', tool: '核验检查清单（模拟）' },
      { id: 'summary', role: '主 Agent', title: '返回结论', detail: '整合角色结果并返回到发起任务的对话。', result: '输出问题、证据、测试建议和未确认项。', tool: '汇总角色结果（模拟）' },
    ],
    output: '这类任务适合由主 Agent 负责拆分与汇总，分析窗口负责找证据，复核窗口独立挑战结论。角色分工是示例；本页面不会真的创建对话窗口或调用模型。',
  },
];

const panelNames = { trace: '执行', workflow: '工作流', team: '协作', result: '结果' };
let selectedId = scenarios[0].id;
let activePanel = 'trace';
let isRunning = false;

function currentScenario() {
  return scenarios.find((scenario) => scenario.id === selectedId) ?? scenarios[0];
}

function statusLabel(status) {
  return ({ todo: '待处理', in_progress: '运行中', done: '已完成', backlog: '待规划' })[status] ?? status;
}

function renderTasks() {
  scenarioList.replaceChildren();
  scenarios.forEach((scenario) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `scenario-button${scenario.id === selectedId ? ' is-selected' : ''}`;
    button.disabled = isRunning;
    button.setAttribute('aria-pressed', String(scenario.id === selectedId));

    const heading = document.createElement('span');
    heading.className = 'scenario-title';
    heading.textContent = scenario.title;
    const metadata = document.createElement('span');
    metadata.className = 'scenario-meta';
    metadata.textContent = `${scenario.id} · ${scenario.priority}优先级`;
    const status = document.createElement('span');
    status.className = `task-status task-status-${scenario.status}`;
    status.textContent = statusLabel(scenario.status);
    button.append(heading, metadata, status);
    button.addEventListener('click', () => selectScenario(scenario.id));
    scenarioList.append(button);
  });
  document.querySelector('#task-count').textContent = String(scenarios.length);
}

function addMessage(role, title, content, meta = '') {
  const article = document.createElement('article');
  article.className = `demo-message ${role}`;
  const avatar = document.createElement('span');
  avatar.className = 'message-avatar';
  avatar.textContent = role === 'user' ? '你' : role === 'system' ? '·' : 'A';
  const body = document.createElement('div');
  body.className = 'message-content';
  const heading = document.createElement('div');
  heading.className = 'message-meta';
  heading.textContent = meta || title;
  const paragraph = document.createElement('p');
  paragraph.textContent = content;
  body.append(heading, paragraph);
  article.append(avatar, body);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

function renderConversation() {
  const scenario = currentScenario();
  messages.replaceChildren();
  addMessage('system', '', '选中一项任务后，启动模拟运行。你可以补充本轮目标；所有 Agent 输出和阶段结果均为预设内容。', '任务已载入 · 本地模拟');
  if (scenario.status === 'done') {
    addMessage('user', '', input.value.trim() || scenario.prompt, '已完成的示例任务');
    addMessage('assistant', '', scenario.output, '主 Agent · 示例结果');
  }
}

function renderTrace() {
  const scenario = currentScenario();
  const list = document.createElement('ol');
  list.className = 'trace-list';
  scenario.phases.forEach((phase, index) => {
    const item = document.createElement('li');
    item.className = `trace-step trace-${phase.status ?? 'pending'}`;
    const marker = document.createElement('span');
    marker.className = 'trace-marker';
    marker.setAttribute('aria-hidden', 'true');
    const content = document.createElement('div');
    const title = document.createElement('b');
    title.textContent = `${phase.role} · ${phase.title}`;
    const detail = document.createElement('small');
    detail.textContent = phase.status === 'completed' ? phase.result : phase.status === 'running' ? '正在处理当前节点……' : `步骤 ${index + 1} · ${phase.tool}`;
    content.append(title, detail);
    item.append(marker, content);
    list.append(item);
  });
  inspector.append(list);
}

function renderWorkflow() {
  const scenario = currentScenario();
  const flow = document.createElement('div');
  flow.className = 'workflow-preview';
  const intro = document.createElement('p');
  intro.className = 'panel-description';
  intro.textContent = '每个步骤接收任务目标和可追溯的上游结果，再把自己的输出交给主 Agent 汇总。';
  flow.append(intro);
  scenario.phases.forEach((phase, index) => {
    const node = document.createElement('div');
    node.className = `workflow-node workflow-${phase.status ?? 'pending'}`;
    const label = document.createElement('span');
    label.textContent = phase.title;
    const role = document.createElement('small');
    role.textContent = phase.role;
    node.append(label, role);
    flow.append(node);
    if (index < scenario.phases.length - 1) {
      const connector = document.createElement('div');
      connector.className = 'workflow-connector';
      connector.setAttribute('aria-hidden', 'true');
      flow.append(connector);
    }
  });
  inspector.append(flow);
}

function renderTeam() {
  const scenario = currentScenario();
  const team = document.createElement('div');
  team.className = 'team-preview';
  const intro = document.createElement('p');
  intro.className = 'panel-description';
  intro.textContent = '主 Agent 接收用户目标、分配角色任务并汇总结果。分析与复核窗口各自返回独立产物。';
  team.append(intro);
  scenario.phases.forEach((phase, index) => {
    const member = document.createElement('div');
    member.className = `team-member team-${phase.status ?? 'pending'}`;
    const role = document.createElement('b');
    role.textContent = phase.role;
    const task = document.createElement('span');
    task.textContent = phase.title;
    const state = document.createElement('small');
    state.textContent = index === 0 || index === scenario.phases.length - 1 ? '主对话' : '协作窗口';
    member.append(role, task, state);
    team.append(member);
  });
  inspector.append(team);
}

function renderResult() {
  const scenario = currentScenario();
  const result = document.createElement('div');
  result.className = 'result-preview';
  const heading = document.createElement('h2');
  heading.textContent = scenario.status === 'done' ? '协作结果' : '结果将在运行后出现';
  const body = document.createElement('p');
  body.textContent = scenario.status === 'done' ? scenario.output : '完成主 Agent 拆解、协作窗口处理和复核后，汇总内容会返回发起任务的对话。';
  result.append(heading, body);
  if (scenario.status === 'done') {
    const checks = document.createElement('ul');
    ['节点状态可查看', '上游输入来源可追溯', '主 Agent 返回汇总'].forEach((label) => {
      const item = document.createElement('li');
      item.textContent = label;
      checks.append(item);
    });
    result.append(checks);
  }
  inspector.append(result);
}

function renderInspector() {
  const scenario = currentScenario();
  inspector.replaceChildren();
  inspector.setAttribute('aria-labelledby', `tab-${activePanel}`);
  if (activePanel === 'workflow') renderWorkflow();
  else if (activePanel === 'team') renderTeam();
  else if (activePanel === 'result') renderResult();
  else renderTrace();

  document.querySelectorAll('[data-panel]').forEach((button) => {
    const active = button.dataset.panel === activePanel;
    button.classList.toggle('is-active', active);
    button.setAttribute('aria-selected', String(active));
    button.tabIndex = active ? 0 : -1;
  });
  runButton.disabled = isRunning;
  runButton.textContent = scenario.status === 'done' ? '再次演示' : isRunning ? '运行中…' : '开始演示';
}

function selectScenario(id) {
  if (isRunning) return;
  selectedId = id;
  const scenario = currentScenario();
  projectTitle.textContent = scenario.title;
  taskId.textContent = scenario.id;
  runStatus.textContent = statusLabel(scenario.status);
  input.value = scenario.prompt;
  renderTasks();
  renderConversation();
  renderInspector();
}

function delay(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function runScenario(event) {
  event.preventDefault();
  if (isRunning) return;
  const scenario = currentScenario();
  const taskInput = input.value.trim();
  if (!taskInput) {
    input.focus();
    return;
  }

  isRunning = true;
  scenario.status = 'in_progress';
  scenario.phases.forEach((phase) => { phase.status = 'pending'; });
  projectTitle.textContent = scenario.title;
  runStatus.textContent = '运行中';
  addMessage('user', '', taskInput, '本轮任务目标');
  renderTasks();
  renderInspector();

  try {
    for (const phase of scenario.phases) {
      phase.status = 'running';
      runStatus.textContent = `${phase.role}处理中`;
      renderInspector();
      await delay(650);
      phase.status = 'completed';
      addMessage('assistant', '', phase.result, `${phase.role} · ${phase.title}`);
      renderInspector();
    }
    scenario.status = 'done';
    runStatus.textContent = '已完成';
    addMessage('assistant', '', scenario.output, '主 Agent · 汇总结果（预设）');
  } finally {
    isRunning = false;
    renderTasks();
    renderInspector();
  }
}

document.querySelectorAll('[data-panel]').forEach((button) => {
  button.addEventListener('click', () => {
    activePanel = button.dataset.panel;
    renderInspector();
  });
});

document.querySelector('#demo-form').addEventListener('submit', runScenario);
document.querySelectorAll('[role="tab"]').forEach((tab) => {
  tab.addEventListener('keydown', (event) => {
    if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    event.preventDefault();
    const tabs = [...document.querySelectorAll('[role="tab"]')];
    const index = tabs.indexOf(tab);
    const offset = event.key === 'ArrowRight' ? 1 : -1;
    tabs[(index + offset + tabs.length) % tabs.length].click();
    tabs[(index + offset + tabs.length) % tabs.length].focus();
  });
});

renderTasks();
selectScenario(selectedId);
