// Render the checked-in Markdown as the source of the design and usage pages.
const documentKind = document.body.dataset.documentKind;
const documentMount = document.querySelector('[data-markdown-viewer]');
const english = window.veraSiteLanguage === 'en';

if (documentMount && (documentKind === 'design' || documentKind === 'docs')) {
  const docs = english ? [
    ['index', 'Overview'], ['quick-start', 'Quick start'], ['usage', 'Daily use'],
    ['configuration', 'Configuration and local data'], ['environment-variables', 'Environment variables'],
    ['api', 'API reference'], ['troubleshooting', 'Troubleshooting and limitations'],
  ] : [
    ['index', '文档概览'], ['quick-start', '快速开始'], ['usage', '日常使用'],
    ['configuration', '配置与本地数据'], ['environment-variables', '环境变量表'],
    ['api', '接口参考'], ['troubleshooting', '排错与限制'],
  ];
  const allowedPages = new Set(docs.map(([slug]) => slug));
  const requestedPage = new URLSearchParams(location.search).get('page') || 'index';
  const page = allowedPages.has(requestedPage) ? requestedPage : 'index';
  const languageRoot = english ? '../content/en' : '../content';
  const source = documentKind === 'design'
    ? `${languageRoot}/design/index.md`
    : `${languageRoot}/docs/${page}.md`;
  const sourceUrl = new URL(source, location.href);

  if (documentKind === 'docs') {
    const aside = document.querySelector('.docs-aside');
    aside.replaceChildren();
    const label = document.createElement('p');
    label.className = 'docs-aside-label';
    label.textContent = 'VERAAGENT DOCS';
    aside.append(label);
    for (const [slug, title] of docs) {
      const link = document.createElement('a');
      link.href = slug === 'index' ? (english ? '?lang=en' : './')
        : `?page=${slug}${english ? '&lang=en' : ''}`;
      link.textContent = title;
      if (slug === page) {
        link.classList.add('is-current');
        link.setAttribute('aria-current', 'page');
      }
      aside.append(link);
    }
  }

  const rewriteLink = (raw) => {
    if (raw.startsWith('#')) return raw;
    if (/^(https?:|mailto:)/i.test(raw)) return raw;
    const repositoryPrefix = english ? '../../../../' : '../../../';
    if (raw.startsWith(repositoryPrefix)) {
      return `https://github.com/Felix-0625/Agents/blob/main/${raw.slice(repositoryPrefix.length)}`;
    }
    const target = new URL(raw, sourceUrl);
    const docsMatch = target.pathname.match(/\/content\/(?:en\/)?docs\/([a-z-]+)\.md$/);
    if (docsMatch && allowedPages.has(docsMatch[1])) {
      return docsMatch[1] === 'index' ? `../docs/${english ? '?lang=en' : ''}`
        : `../docs/?page=${docsMatch[1]}${english ? '&lang=en' : ''}`;
    }
    if (/\/content\/(?:en\/)?design\/index\.md$/.test(target.pathname)) return `../design/${english ? '?lang=en' : ''}`;
    return raw;
  };

  const render = (markdown) => {
    const template = document.createElement('template');
    template.innerHTML = marked.parse(markdown, { gfm: true });
    const prohibited = 'script,style,iframe,object,embed,form,svg,math,link,meta,base,input,button,textarea,select';
    template.content.querySelectorAll(prohibited).forEach((element) => element.remove());
    template.content.querySelectorAll('*').forEach((element) => {
      for (const attribute of [...element.attributes]) {
        if (attribute.name.startsWith('on') || attribute.name === 'style' || attribute.name === 'srcdoc') {
          element.removeAttribute(attribute.name);
        }
      }
    });
    template.content.querySelectorAll('a[href]').forEach((link) => {
      const rewritten = rewriteLink(link.getAttribute('href'));
      if (!/^(https?:|mailto:|#|\.\.?\/|\?)/i.test(rewritten)) {
        link.removeAttribute('href');
        return;
      }
      link.setAttribute('href', rewritten);
      if (/^https?:/i.test(rewritten)) {
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
      }
    });
    template.content.querySelectorAll('img[src]').forEach((image) => {
      const target = new URL(image.getAttribute('src'), sourceUrl);
      if (target.origin !== location.origin || !/^https?:$/.test(target.protocol)) {
        image.remove();
        return;
      }
      image.src = target.href;
      image.loading = 'lazy';
      image.decoding = 'async';
    });

    documentMount.replaceChildren();
    const sectionIds = ['overview', 'architecture', 'decisions', 'chat-flow', 'organization', 'data-model', 'quality', 'limitations'];
    let section = null;
    let sectionIndex = 0;
    for (const node of [...template.content.childNodes]) {
      if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'H2') {
        section = document.createElement('section');
        section.className = 'docs-section';
        section.id = documentKind === 'design' ? sectionIds[sectionIndex] : `section-${sectionIndex + 1}`;
        sectionIndex += 1;
        documentMount.append(section);
      }
      (section || documentMount).append(node);
    }
    const heading = documentMount.querySelector('h1');
    if (heading) {
      document.title = `${heading.textContent} — VeraAgent`;
      const lead = heading.nextElementSibling;
      if (lead?.tagName === 'P') lead.classList.add('docs-lead');
    }
    const sourceLink = document.createElement('p');
    sourceLink.className = 'docs-source-link';
    const link = document.createElement('a');
    link.href = source;
    link.textContent = english ? 'View Markdown source ↗' : '查看 Markdown 原文 ↗';
    sourceLink.append(link);
    documentMount.append(sourceLink);

    if (documentKind === 'design' && 'IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          document.querySelectorAll('.docs-aside a').forEach((link) => {
            const active = link.hash === `#${entry.target.id}`;
            link.classList.toggle('is-current', active);
            if (active) link.setAttribute('aria-current', 'location');
            else link.removeAttribute('aria-current');
          });
        }
      }, { rootMargin: '-18% 0px -68% 0px' });
      documentMount.querySelectorAll('.docs-section').forEach((item) => observer.observe(item));
    }
  };

  fetch(sourceUrl)
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.text();
    })
    .then(render)
    .catch(() => {
      documentMount.innerHTML = english
        ? '<h1>Document unavailable</h1><p class="docs-lead">Open this site with a local static server, or read the Markdown source in the repository.</p>'
        : '<h1>文档暂时无法载入</h1><p class="docs-lead">请通过本地静态服务器打开网站，或查看仓库中的 Markdown 原文。</p>';
      const link = document.createElement('a');
      link.href = source;
      link.textContent = english ? 'Open Markdown source ↗' : '打开 Markdown 原文 ↗';
      documentMount.append(link);
    });
}
