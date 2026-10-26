const languageParam = new URLSearchParams(location.search).get('lang');
const storedLanguage = (() => { try { return localStorage.getItem('veraagent-site-language'); } catch { return null; } })();
const siteLanguage = languageParam === 'en' || languageParam === 'zh'
  ? languageParam : storedLanguage === 'en' ? 'en' : 'zh';
window.veraSiteLanguage = siteLanguage;
document.documentElement.lang = siteLanguage === 'en' ? 'en' : 'zh-CN';
try { localStorage.setItem('veraagent-site-language', siteLanguage); } catch { /* Storage may be unavailable. */ }

const englishText = {
  '设计': 'Design', '文档': 'Docs', '演示': 'Demo', 'GitHub 仓库': 'GitHub repository',
  '你的个人工作站': 'Your personal workspace',
  '在一个工作站中组织 Agent、对话窗口和工具': 'Bring agents, conversations, and tools into one workspace',
  '任务分派、协作过程与结果清晰可见': 'See task delegation, collaboration, and results clearly',
  '查看仓库': 'View repository', '观看演示': 'Watch demo',
  'VeraAgent 桌面工作站': 'VeraAgent desktop workspace',
  'Vera Agent 统筹': 'Vera Agent coordinates', '专业角色各司其职': 'Specialists handle their roles',
  '按需委派 · 独立执行 · 结果回传': 'Delegate · Work independently · Report back',
  '分派 · 汇总 · 实施': 'Delegate · Synthesize · Execute',
  '调研员': 'Researcher', '深度探索 · 返回发现': 'Investigate · Report findings',
  '审查员': 'Reviewer', '审阅变更 · 返回意见': 'Review changes · Send feedback',
  '全局模板 · 组织架构': 'Global template · Organization',
  '组织架构节点图': 'Organization chart',
  'CEO 向三位角色分派任务，右侧 CTO 再向 Coder 1 与 Coder 2 分派任务。没有编辑时的浮动工具栏。': 'The CEO delegates to three roles; the CTO on the right delegates to Coder 1 and Coder 2.',
  '直属关系': 'Reports to', '下发任务': 'Delegates', '组织角色': 'Org role', '执行角色': 'Worker',
  '全局模板 · 工作流': 'Global template · Workflow', '工作流分支节点图': 'Branching workflow diagram',
  '分解任务后，分别执行财务分析、行业分析和竞品分析，再汇总为综合报告。': 'A task splits into financial, industry, and competitor analyses, then merges into a final report.',
  '传递上游结果': 'Pass result', '业务步骤': 'Step', '分解任务': 'Split task',
  '财务分析': 'Finance', '行业分析': 'Industry', '竞品分析': 'Competitors', '综合报告': 'Final report',
  '开启你的个人工作站': 'Start your personal workspace',
  '在 Windows 上启动 Vera Agent，自定义你的工作站': 'Launch Vera Agent on Windows and make the workspace your own',
  '展开目录': 'Show contents', '收起目录': 'Hide contents',
  '概述与目标': 'Overview and goals', '整体架构': 'Architecture', '关键设计决策': 'Design decisions',
  '对话与工具调用链': 'Chat and tool flow', '组织架构与工作流': 'Organization and workflow',
  '本地数据模型': 'Local data model', '质量属性与边界': 'Quality and boundaries', '已知限制': 'Known limitations',
  '系统设计文档': 'System design', '正在载入设计文档…': 'Loading design document…',
  '文档概览': 'Overview', '快速开始': 'Quick start', '日常使用': 'Daily use',
  '配置与本地数据': 'Configuration and local data', '环境变量表': 'Environment variables',
  '接口参考': 'API reference', '排错与限制': 'Troubleshooting and limitations',
  '使用文档': 'User documentation', '正在载入文档…': 'Loading documentation…',
  '请启用 JavaScript，或直接阅读': 'Enable JavaScript, or read the',
  'Markdown 原文': 'Markdown source', 'Markdown 文档目录': 'Markdown index',
  '系统设计以仓库源码和测试为准。': 'The source code and tests are authoritative for the design.',
  '安装、配置与接口说明以当前代码和测试为准。': 'The current code and tests are authoritative for setup, configuration, and APIs.',
  '观看 VeraAgent 演示': 'Watch the VeraAgent demo',
  '从任务输入到 Agent 协作，了解工作站中的过程呈现。': 'See how the workspace presents tasks and agent collaboration.',
  '当前浏览器无法播放此视频。': 'Your browser cannot play this video.',
  '视频录制自此前的预设演示页面，展示的是示例流程，不会连接模型或执行工具。若要实际操作，请按': 'This recording shows a preset example. It does not connect to a model or execute tools. To try VeraAgent yourself, follow the',
  '快速开始 →': 'Quick start →', '启动 VeraAgent。': 'to launch VeraAgent.',
  '本地项目中的 Agent 工作站。': 'An agent workspace for local projects.',
  '© VeraAgent contributors · 持续开发中': '© VeraAgent contributors · In active development',
  'VeraAgent 首页': 'VeraAgent home', '主导航': 'Main navigation', '语言': 'Language',
  '打开导航': 'Open navigation', '设计文档目录': 'Design contents', '文档目录': 'Documentation contents',
  'VeraAgent 工作站界面': 'VeraAgent workspace interface',
  'VeraAgent 桌面工作站：左侧为导航与项目入口，中间为对话区': 'VeraAgent desktop workspace with navigation on the left and conversation in the center',
  'Vera Agent 将任务委派给调研员与审查员，并接收他们的结果': 'Vera Agent delegates to a researcher and reviewer, then receives their results',
  '组织架构与工作流模板预览': 'Organization and workflow template previews',
  'VeraAgent 演示视频': 'VeraAgent demo video', 'VeraAgent 预设流程演示视频': 'VeraAgent preset-flow demo video',
};

if (siteLanguage === 'en') {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    if (node.parentElement?.closest('script,style,code,pre')) continue;
    const original = node.nodeValue.trim();
    if (englishText[original]) node.nodeValue = node.nodeValue.replace(original, englishText[original]);
  }
  document.querySelectorAll('[aria-label],[alt],[title]').forEach((element) => {
    for (const attribute of ['aria-label', 'alt', 'title']) {
      const original = element.getAttribute(attribute);
      if (englishText[original]) element.setAttribute(attribute, englishText[original]);
    }
  });
  if (document.body.classList.contains('penpot-landing')) document.title = 'VeraAgent — Your personal workspace';
  if (document.body.classList.contains('playground-shell')) document.title = 'Demo video — VeraAgent';
}

document.querySelectorAll('.language-switch button').forEach((button, index) => {
  const targetLanguage = index === 0 ? 'zh' : 'en';
  button.disabled = false;
  button.removeAttribute('title');
  button.classList.toggle('is-active', targetLanguage === siteLanguage);
  button.setAttribute('aria-pressed', String(targetLanguage === siteLanguage));
  button.addEventListener('click', () => {
    if (targetLanguage === siteLanguage) return;
    try { localStorage.setItem('veraagent-site-language', targetLanguage); } catch { /* Storage may be unavailable. */ }
    const next = new URL(location.href);
    next.searchParams.set('lang', targetLanguage);
    location.assign(next.href);
  });
});

if (siteLanguage === 'en') {
  document.querySelectorAll('a[href]').forEach((link) => {
    const raw = link.getAttribute('href');
    if (!raw || raw.startsWith('#') || /^(https?:|mailto:)/i.test(raw)) return;
    const target = new URL(raw, location.href);
    if (target.origin !== location.origin || !/\/$|\.html$/.test(target.pathname)) return;
    target.searchParams.set('lang', 'en');
    link.href = target.href;
  });
}

const menuButton = document.querySelector('.menu-toggle');
const mainNav = document.querySelector('.main-nav');
if (menuButton && mainNav) menuButton.addEventListener('click', () => {
  const open = mainNav.classList.toggle('is-open');
  menuButton.setAttribute('aria-expanded', String(open));
});

const landingHeader = document.querySelector('.penpot-landing .topbar');
const landingHero = document.querySelector('.penpot-hero');
const landingThirdSection = document.querySelector('.penpot-collaboration');
if (landingHeader && landingHero && landingThirdSection) {
  let dockThreshold = 0;
  let languageHideThreshold = 0;
  const updateHeader = () => {
    landingHeader.classList.toggle('is-docked', window.scrollY >= dockThreshold);
    landingHeader.classList.toggle('is-language-hidden', window.scrollY >= languageHideThreshold);
  };
  const measureHeader = () => {
    dockThreshold = landingHero.getBoundingClientRect().bottom + window.scrollY - 170;
    languageHideThreshold = landingThirdSection.getBoundingClientRect().top + window.scrollY - 170;
    updateHeader();
  };
  window.addEventListener('scroll', updateHeader, { passive: true });
  window.addEventListener('resize', measureHeader);
  measureHeader();
}

const contentHeader = document.querySelector(':is(.content-page,.playground-shell) .topbar');
if (contentHeader) {
  const updateContentHeader = () => {
    contentHeader.classList.toggle('is-docked', window.scrollY > 120);
    if (document.body.classList.contains('content-page')) {
      contentHeader.classList.toggle('is-content-hidden', window.scrollY >= window.innerHeight * 2);
    }
  };
  window.addEventListener('scroll', updateContentHeader, { passive: true });
  window.addEventListener('resize', updateContentHeader);
  updateContentHeader();
}

const docsToggle = document.querySelector('.docs-mobile-toggle');
const docsAside = document.querySelector('.docs-aside');
if (docsToggle && docsAside) docsToggle.addEventListener('click', () => {
  const open = docsAside.classList.toggle('is-open');
  docsToggle.setAttribute('aria-expanded', String(open));
  docsToggle.querySelector('span').textContent = siteLanguage === 'en'
    ? (open ? 'Hide contents' : 'Show contents') : (open ? '收起目录' : '展开目录');
});

const sections = [...document.querySelectorAll('.docs-section[id]')];
if (sections.length && document.body.dataset.documentKind !== 'docs' && 'IntersectionObserver' in window) {
  const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
    if (!entry.isIntersecting) return;
    document.querySelectorAll('.docs-aside a').forEach((link) => {
      const active = link.hash === `#${entry.target.id}`;
      link.classList.toggle('is-current', active);
      if (active) link.setAttribute('aria-current', 'location'); else link.removeAttribute('aria-current');
    });
  }), { rootMargin: '-18% 0px -68% 0px' });
  sections.forEach((section) => observer.observe(section));
}
document.querySelectorAll('.docs-aside a').forEach((link) => link.addEventListener('click', () => {
  if (matchMedia('(max-width: 680px)').matches && docsAside?.classList.contains('is-open')) {
    docsAside.classList.remove('is-open'); docsToggle?.setAttribute('aria-expanded', 'false');
    if (docsToggle) docsToggle.querySelector('span').textContent = siteLanguage === 'en' ? 'Show contents' : '展开目录';
  }
}));
