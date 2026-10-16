const menuButton = document.querySelector('.menu-toggle');
const mainNav = document.querySelector('.main-nav');
if (menuButton && mainNav) menuButton.addEventListener('click', () => {
  const open = mainNav.classList.toggle('is-open');
  menuButton.setAttribute('aria-expanded', String(open));
});

const docsToggle = document.querySelector('.docs-mobile-toggle');
const docsAside = document.querySelector('.docs-aside');
if (docsToggle && docsAside) docsToggle.addEventListener('click', () => {
  const open = docsAside.classList.toggle('is-open');
  docsToggle.setAttribute('aria-expanded', String(open));
  docsToggle.querySelector('span').textContent = open ? '收起目录' : '展开目录';
});

const sections = [...document.querySelectorAll('.docs-section[id]')];
if (sections.length && 'IntersectionObserver' in window) {
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
    if (docsToggle) docsToggle.querySelector('span').textContent = '展开目录';
  }
}));
