const messages = document.querySelector('#demo-messages');
const inspector = document.querySelector('#inspector-panel');
const projectTitle = document.querySelector('#demo-project');
const input = document.querySelector('#demo-input');
const sendButton = document.querySelector('.send-button');

const demos = {
  login: {
    title: 'vera-demo / 登录流程',
    user: '检查登录失败处理，特别是 token 过期后的行为。',
    intro: '我会先查看认证入口和相关测试，再整理过期 token 的处理路径。下面展示的是预设的模拟执行过程。',
    tools: [
      ['读取文件 · src/auth/session.ts', '读取 refreshSession 与 handleAuthError 的模拟结果：过期后尝试刷新；刷新失败时清除本地 session 并返回未认证状态。'],
      ['读取文件 · tests/auth/session.test.ts', '找到 4 个预设测试：正常刷新、刷新失败、无 refresh token、重复请求合并。'],
      ['运行测试 · auth/session.test.ts', '模拟结果：4 passed · 0 failed · 0.42s']
    ],
    result: '检查完成。刷新失败时会清除 session 并转为未认证状态；当前演示数据没有显示到登录页的导航行为，建议补一条集成测试覆盖完整跳转。',
    trace: [['读取项目规则', 'AGENTS.md · 已载入的模拟规则'], ['查看认证实现', 'src/auth/session.ts · 2.1 KB'], ['检查相关测试', 'tests/auth/session.test.ts · 4 tests'], ['返回摘要', '无真实模型调用']],
    files: ['src/auth/session.ts　只读检查', 'tests/auth/session.test.ts　只读检查'],
    context: ['项目：vera-demo', '规则：AGENTS.md（模拟）', '会话：当前演示会话', '模型：无 · 预设响应']
  },
  diff: {
    title: 'vera-demo / 工作区变更',
    user: '总结一下当前工作区的变更，并指出需要重点复查的地方。',
    intro: '我会模拟检查 Git 状态和变更摘要，再列出适合人工复核的内容。这里不会读取真实 Git 仓库。',
    tools: [
      ['查看 Git 状态', '模拟状态：2 个已修改文件 · 1 个新增文件 · 工作区未提交'],
      ['查看差异摘要', '模拟统计：src/auth/session.ts (+12/-4) · tests/auth/session.test.ts (+18/-0)'],
      ['整理复核点', '已生成面向人的变更摘要（预设内容）']
    ],
    result: '本次模拟变更主要涉及刷新 token 失败后的 session 清理，以及对应测试覆盖。建议复查错误分支是否会误清除可恢复的会话，并确认新增测试包含刷新接口超时场景。',
    trace: [['读取 Git 状态', '2 modified · 1 untracked'], ['汇总文件差异', '2 files · +30 / -4'], ['生成复核建议', '固定模拟响应']],
    files: ['src/auth/session.ts　+12 / −4', 'tests/auth/session.test.ts　+18 / −0', 'notes/review.md　新增（模拟）'],
    context: ['项目：vera-demo', '分支：feature/session-refresh（模拟）', '工作区：2 modified · 1 untracked', '数据：脚本预设']
  },
  context: {
    title: 'vera-demo / 项目上下文',
    user: '这个项目的规则、当前会话和模型上下文分别是什么？',
    intro: '我会区分项目规则、会话内容和模型服务配置。演示里的值都是虚构的占位信息。',
    tools: [
      ['读取项目说明', '模拟发现 AGENTS.md：测试优先、保持变更范围小、修改后运行目标测试。'],
      ['检查会话状态', '当前演示会话包含 3 条消息；没有读取任何真实历史会话。'],
      ['查看模型配置', '模型状态：此交互演示未配置、未请求任何模型。']
    ],
    result: '项目规则用于提供仓库级工作约定；会话只描述本轮对话内容；模型配置决定真实桌面应用向哪个服务发送请求。本演示不加载真实项目规则、对话记录或凭据。',
    trace: [['读取项目说明', 'AGENTS.md · 模拟数据'], ['查看演示会话', '3 messages · mock only'], ['检查模型状态', '未连接模型服务']],
    files: ['AGENTS.md　演示占位内容', '用户配置文件　未访问', '真实 `.agents` 数据　未访问'],
    context: ['项目规则：仓库工作约定（模拟）', '会话：当前浏览器中的演示', '模型：未连接', '隐私：未发送网络请求']
  }
};

let selected = 'login';
let activePanel = 'trace';
let busy = false;

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
}

function addMessage(role, content, tools = []) {
  const article = document.createElement('article');
  article.className = `demo-message ${role}`;
  const avatar = document.createElement('span');
  avatar.className = 'message-avatar';
  avatar.textContent = role === 'user' ? '你' : 'V';
  const body = document.createElement('div');
  body.className = 'message-content';
  if (role === 'assistant') {
    const meta = document.createElement('div');
    meta.className = 'message-meta';
    meta.textContent = '模拟响应 · 非真实模型输出';
    body.append(meta);
  }
  const paragraph = document.createElement('p');
  paragraph.textContent = content;
  body.append(paragraph);
  tools.forEach(([name, output], index) => {
    const item = document.createElement('div');
    item.className = 'mock-tool';
    const label = document.createElement('span');
    label.textContent = name;
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = '查看模拟输出';
    button.setAttribute('aria-expanded', 'false');
    const details = document.createElement('div');
    details.className = 'tool-output';
    details.textContent = output;
    button.addEventListener('click', () => {
      const open = details.classList.toggle('is-open');
      button.textContent = open ? '收起' : '查看模拟输出';
      button.setAttribute('aria-expanded', String(open));
    });
    item.append(label, button, details);
    body.append(item);
  });
  article.append(avatar, body);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

function renderInspector() {
  const demo = demos[selected];
  if (activePanel === 'trace') {
    inspector.innerHTML = `<h2 class="inspector-title">预设执行步骤</h2>${demo.trace.map(([title, detail], index) => `<div class="trace-step">${String(index + 1).padStart(2, '0')} · ${escapeHtml(title)}<small>${escapeHtml(detail)}</small></div>`).join('')}`;
  } else {
    const values = activePanel === 'files' ? demo.files : demo.context;
    inspector.innerHTML = `<h2 class="inspector-title">${activePanel === 'files' ? '模拟文件视图' : '模拟上下文'}</h2><div class="inspector-placeholder">${values.map((value) => `<div class="trace-step">${escapeHtml(value)}</div>`).join('')}</div>`;
  }
}

function loadScenario(key) {
  selected = key;
  const demo = demos[key];
  projectTitle.textContent = demo.title;
  messages.replaceChildren();
  addMessage('user', demo.user);
  addMessage('assistant', demo.intro, demo.tools);
  addMessage('assistant', demo.result);
  renderInspector();
  document.querySelectorAll('.scenario-button').forEach((button) => button.classList.toggle('is-selected', button.dataset.scenario === key));
}

document.querySelectorAll('[data-scenario]').forEach((button) => button.addEventListener('click', () => loadScenario(button.dataset.scenario)));
document.querySelectorAll('[data-panel]').forEach((button) => button.addEventListener('click', () => {
  activePanel = button.dataset.panel;
  document.querySelectorAll('[data-panel]').forEach((tab) => {
    const active = tab === button;
    tab.classList.toggle('is-active', active);
    tab.setAttribute('aria-selected', String(active));
  });
  renderInspector();
}));

document.querySelector('#demo-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const task = input.value.trim();
  if (!task || busy) return;
  busy = true;
  sendButton.disabled = true;
  addMessage('user', task);
  input.value = '';
  const pending = document.createElement('article');
  pending.className = 'demo-message';
  pending.innerHTML = '<span class="message-avatar">V</span><div class="message-content"><div class="message-meta">本地模拟</div><p>正在按预设逻辑整理演示回复…</p></div>';
  messages.append(pending);
  messages.scrollTop = messages.scrollHeight;
  window.setTimeout(() => {
    pending.remove();
    addMessage('assistant', `已收到“${task}”。这段回复由本地演示脚本生成，没有请求模型。你可以从左侧选择预设任务，查看对应的模拟工具轨迹和结果。`);
    busy = false;
    sendButton.disabled = false;
    input.focus();
  }, 650);
});

input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    document.querySelector('#demo-form').requestSubmit();
  }
});

loadScenario(selected);
