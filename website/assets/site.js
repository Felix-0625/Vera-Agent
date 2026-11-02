const languageParam = new URLSearchParams(location.search).get("lang");
const storedLanguage = (() => {
  try {
    return localStorage.getItem("veraagent-site-language");
  } catch {
    return null;
  }
})();
const siteLanguage =
  languageParam === "en" || languageParam === "zh"
    ? languageParam
    : storedLanguage === "en"
      ? "en"
      : "zh";
window.veraSiteLanguage = siteLanguage;
document.documentElement.lang = siteLanguage === "en" ? "en" : "zh-CN";
try {
  localStorage.setItem("veraagent-site-language", siteLanguage);
} catch {
  /* Storage may be unavailable. */
}

const englishText = {
  首页: "Home",
  设计: "Design",
  文档: "Docs",
  "GitHub 仓库": "GitHub repository",
  你的个人工作站: "Your personal workspace",
  "在一个工作站中组织 Agent、对话窗口和工具":
    "Bring agents, conversations, and tools into one workspace",
  "任务分派、协作过程与结果清晰可见":
    "See task delegation, collaboration, and results clearly",
  查看仓库: "View repository",
  "在 GitHub 查看源码": "View source on GitHub",
  "VeraAgent 桌面工作站": "VeraAgent desktop workspace",
  "Vera Agent 统筹": "Vera Agent coordinates",
  专业角色各司其职: "Specialists handle their roles",
  "按需委派 · 独立执行 · 结果回传":
    "Delegate · Work independently · Report back",
  "分派 · 汇总 · 实施": "Delegate · Synthesize · Execute",
  调研员: "Researcher",
  "深度探索 · 返回发现": "Investigate · Report findings",
  审查员: "Reviewer",
  "审阅变更 · 返回意见": "Review changes · Send feedback",
  "全局模板 · 组织架构": "Global template · Organization",
  "评测与 RSI": "Evaluation & RSI",
  "低分记录驱动改进，对照评测后人工采纳":
    "Improve from low-scoring runs, compare with the baseline, then approve adoption",
  "评测与 RSI 流程": "Evaluation & RSI process",
  记录执行: "Record runs",
  "轨迹 · 验证 · outcome 评分": "Traces · Verification · Outcome score",
  筛选低分: "Find weak runs",
  "outcome < 0.5 的执行记录": "Runs with outcome < 0.5",
  提出改进: "Propose changes",
  "生成规则或 Skill 候选": "Draft a rule or Skill candidate",
  对照评测: "Compare with baseline",
  "训练不退步 · 留出有提升 · 守护零回归":
    "No train regression · Holdout gain · Zero guard regressions",
  人工采纳: "User adoption",
  通过评测后确认生效: "Approve after evaluation",
  监测回滚: "Monitor and roll back",
  "14 天对照 · 效果下降时回滚": "Compare 14 days · Roll back on decline",
  了解设计: "Explore the design",
  查看使用文档: "Read the user docs",
  组织架构节点图: "Organization chart",
  "CEO 向三位角色分派任务，右侧 CTO 再向 Coder 1 与 Coder 2 分派任务。没有编辑时的浮动工具栏。":
    "The CEO delegates to three roles; the CTO on the right delegates to Coder 1 and Coder 2.",
  直属关系: "Reports to",
  下发任务: "Delegates",
  组织角色: "Org role",
  执行角色: "Worker",
  "全局模板 · 工作流": "Global template · Workflow",
  工作流分支节点图: "Branching workflow diagram",
  "分解任务后，分别执行财务分析、行业分析和竞品分析，再汇总为综合报告。":
    "A task splits into financial, industry, and competitor analyses, then merges into a final report.",
  传递上游结果: "Pass result",
  业务步骤: "Step",
  分解任务: "Split task",
  财务分析: "Finance",
  行业分析: "Industry",
  竞品分析: "Competitors",
  综合报告: "Final report",
  开启你的个人工作站: "Start your personal workspace",
  "在 Windows 上启动 Vera Agent，自定义你的工作站":
    "Launch Vera Agent on Windows and make the workspace your own",
  展开目录: "Show contents",
  收起目录: "Hide contents",
  概述与目标: "Overview and goals",
  整体架构: "Architecture",
  关键设计决策: "Design decisions",
  对话与工具调用链: "Chat and tool flow",
  组织架构与工作流: "Organization and workflow",
  本地数据模型: "Local data model",
  质量属性与边界: "Quality and boundaries",
  已知限制: "Known limitations",
  系统设计文档: "System design",
  "正在载入设计文档…": "Loading design document…",
  文档概览: "Overview",
  快速开始: "Quick start",
  日常使用: "Daily use",
  配置与本地数据: "Configuration and local data",
  环境变量表: "Environment variables",
  接口参考: "API reference",
  排错与限制: "Troubleshooting and limitations",
  使用文档: "User documentation",
  "正在载入文档…": "Loading documentation…",
  "请启用 JavaScript，或直接阅读": "Enable JavaScript, or read the",
  "Markdown 原文": "Markdown source",
  "Markdown 文档目录": "Markdown index",
  "系统设计以仓库源码和测试为准。":
    "The source code and tests are authoritative for the design.",
  "安装、配置与接口说明以当前代码和测试为准。":
    "The current code and tests are authoritative for setup, configuration, and APIs.",
  "快速开始 →": "Quick start →",
  "本地项目中的 Agent 工作站。": "An agent workspace for local projects.",
  "© VeraAgent contributors · 持续开发中":
    "© VeraAgent contributors · In active development",
  "VeraAgent 首页": "VeraAgent home",
  主导航: "Main navigation",
  语言: "Language",
  打开导航: "Open navigation",
  设计文档目录: "Design contents",
  文档目录: "Documentation contents",
  "VeraAgent 工作站界面": "VeraAgent workspace interface",
  "VeraAgent 桌面工作站：左侧为导航与项目入口，中间为对话区":
    "VeraAgent desktop workspace with navigation on the left and conversation in the center",
  "Vera Agent 将任务委派给调研员与审查员，并接收他们的结果":
    "Vera Agent delegates to a researcher and reviewer, then receives their results",
  组织架构与工作流模板预览: "Organization and workflow template previews",
};

if (siteLanguage === "en") {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    if (node.parentElement?.closest("script,style,code,pre")) continue;
    const original = node.nodeValue.trim();
    if (englishText[original])
      node.nodeValue = node.nodeValue.replace(original, englishText[original]);
  }
  document.querySelectorAll("[aria-label],[alt],[title]").forEach((element) => {
    for (const attribute of ["aria-label", "alt", "title"]) {
      const original = element.getAttribute(attribute);
      if (englishText[original])
        element.setAttribute(attribute, englishText[original]);
    }
  });
  if (document.body.classList.contains("penpot-landing"))
    document.title = "VeraAgent — Your personal workspace";
}

document
  .querySelectorAll(".language-switch button")
  .forEach((button, index) => {
    const targetLanguage = index === 0 ? "zh" : "en";
    button.disabled = false;
    button.removeAttribute("title");
    button.classList.toggle("is-active", targetLanguage === siteLanguage);
    button.setAttribute(
      "aria-pressed",
      String(targetLanguage === siteLanguage),
    );
    button.addEventListener("click", () => {
      if (targetLanguage === siteLanguage) return;
      try {
        localStorage.setItem("veraagent-site-language", targetLanguage);
      } catch {
        /* Storage may be unavailable. */
      }
      const next = new URL(location.href);
      next.searchParams.set("lang", targetLanguage);
      location.assign(next.href);
    });
  });

if (siteLanguage === "en") {
  document.querySelectorAll("a[href]").forEach((link) => {
    const raw = link.getAttribute("href");
    if (!raw || raw.startsWith("#") || /^(https?:|mailto:)/i.test(raw)) return;
    const target = new URL(raw, location.href);
    if (
      target.origin !== location.origin ||
      !/\/$|\.html$/.test(target.pathname)
    )
      return;
    target.searchParams.set("lang", "en");
    link.href = target.href;
  });
}

const menuButton = document.querySelector(".menu-toggle");
const mainNav = document.querySelector(".main-nav");
if (menuButton && mainNav)
  menuButton.addEventListener("click", () => {
    const open = mainNav.classList.toggle("is-open");
    menuButton.setAttribute("aria-expanded", String(open));
  });

const landingHeader = document.querySelector(".penpot-landing .topbar");
const landingHero = document.querySelector(".penpot-hero");
const landingWorkspacePreview = document.querySelector(
  ".penpot-workspace-preview",
);
if (landingHeader && landingHero && landingWorkspacePreview) {
  let dockThreshold = 0;
  let languageHideThreshold = 0;
  const updateHeader = () => {
    landingHeader.classList.toggle(
      "is-docked",
      window.scrollY >= dockThreshold,
    );
    landingHeader.classList.toggle(
      "is-language-hidden",
      window.scrollY >= languageHideThreshold,
    );
  };
  const measureHeader = () => {
    dockThreshold =
      landingHero.getBoundingClientRect().bottom + window.scrollY - 170;
    languageHideThreshold =
      landingWorkspacePreview.getBoundingClientRect().top +
      window.scrollY -
      170;
    updateHeader();
  };
  window.addEventListener("scroll", updateHeader, { passive: true });
  window.addEventListener("resize", measureHeader);
  measureHeader();
}

const contentHeader = document.querySelector(
  ":is(.content-page,.playground-shell) .topbar",
);
if (contentHeader) {
  const updateContentHeader = () => {
    contentHeader.classList.toggle("is-docked", window.scrollY > 120);
    if (document.body.classList.contains("content-page")) {
      contentHeader.classList.toggle(
        "is-content-hidden",
        window.scrollY >= window.innerHeight * 2,
      );
    }
  };
  window.addEventListener("scroll", updateContentHeader, { passive: true });
  window.addEventListener("resize", updateContentHeader);
  updateContentHeader();
}

const docsToggle = document.querySelector(".docs-mobile-toggle");
const docsAside = document.querySelector(".docs-aside");
if (docsToggle && docsAside)
  docsToggle.addEventListener("click", () => {
    const open = docsAside.classList.toggle("is-open");
    docsToggle.setAttribute("aria-expanded", String(open));
    docsToggle.querySelector("span").textContent =
      siteLanguage === "en"
        ? open
          ? "Hide contents"
          : "Show contents"
        : open
          ? "收起目录"
          : "展开目录";
  });

const sections = [...document.querySelectorAll(".docs-section[id]")];
if (
  sections.length &&
  document.body.dataset.documentKind !== "docs" &&
  "IntersectionObserver" in window
) {
  const observer = new IntersectionObserver(
    (entries) =>
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        document.querySelectorAll(".docs-aside a").forEach((link) => {
          const active = link.hash === `#${entry.target.id}`;
          link.classList.toggle("is-current", active);
          if (active) link.setAttribute("aria-current", "location");
          else link.removeAttribute("aria-current");
        });
      }),
    { rootMargin: "-18% 0px -68% 0px" },
  );
  sections.forEach((section) => observer.observe(section));
}
document.querySelectorAll(".docs-aside a").forEach((link) =>
  link.addEventListener("click", () => {
    if (
      matchMedia("(max-width: 680px)").matches &&
      docsAside?.classList.contains("is-open")
    ) {
      docsAside.classList.remove("is-open");
      docsToggle?.setAttribute("aria-expanded", "false");
      if (docsToggle)
        docsToggle.querySelector("span").textContent =
          siteLanguage === "en" ? "Show contents" : "展开目录";
    }
  }),
);
