import { describe, expect, it } from 'vitest';
import { getEditorLanguage, highlight, highlightCodeLine } from './codeEditorUtils';

describe('getEditorLanguage', () => {
  it.each([
    ['src/app.py', 'python'],
    ['config/settings.YML', 'yaml'],
    ['frontend/src/App.tsx', 'typescript'],
    ['scripts/start.ps1', 'shell'],
    ['README.md', 'markdown'],
    ['Makefile', 'plain'],
    ['archive.unknown', 'plain'],
  ])('maps %s to %s', (path, language) => {
    expect(getEditorLanguage(path)).toBe(language);
  });
});

describe('highlightCodeLine', () => {
  it('escapes HTML so file content cannot inject markup', () => {
    const html = highlightCodeLine('<script>alert("x")</script>', 'page.txt');
    expect(html).not.toContain('<script>');
    expect(html.replace(/<span[^>]*>|<\/span>/g, '')).toBe('&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;');
  });

  it('marks keywords, strings, numbers, and comments with distinct colors', () => {
    const html = highlightCodeLine('const port = 8000; // dev', 'server.ts');
    expect(html).toContain('<span style="color:var(--accent-primary)">const</span>');
    expect(html).toContain('<span style="color:var(--accent-amber)">8000</span>');
    expect(html).toContain('<span style="color:var(--text-muted)"> // dev</span>');
  });

  it('uses # comments for Python and key coloring for YAML', () => {
    expect(highlightCodeLine('x = 1  # note', 'tool.py')).toContain('<span style="color:var(--text-muted)">  # note</span>');
    expect(highlightCodeLine('name: vera', 'agent.yaml')).toContain('<span style="color:var(--accent-cyan)">name</span>');
  });
});

describe('highlight', () => {
  it('preserves line count and pads a trailing newline for textarea alignment', () => {
    const html = highlight('a\nb\n', 'plain');
    expect(html.split('\n')).toHaveLength(3);
    expect(html.endsWith(' ')).toBe(true);
  });
});
