import React, { useMemo, useRef } from 'react';

type TokenKind = 'keyword' | 'string' | 'comment' | 'number' | 'key' | 'punctuation' | 'plain';
type Token = { value: string; kind: TokenKind };

const palettes: Record<TokenKind, string> = {
  keyword: 'var(--accent-primary)',
  string: 'var(--accent-emerald)',
  comment: 'var(--text-muted)',
  number: 'var(--accent-amber)',
  key: 'var(--accent-cyan)',
  punctuation: 'var(--text-secondary)',
  plain: 'var(--text-primary)',
};

const keywordSet = new Set(('const let var function return if else for while do switch case break continue try catch finally throw new class extends implements interface type enum import from export default as async await void null undefined true false this super public private protected static readonly get set typeof instanceof in of delete yield await def self pass lambda with raise except elif and or not is global nonlocal None True False').split(/\s+/));
const punctuationSet = new Set('{}[](),.:;=<>+*/!?|&-');

function tokenizeLine(line: string, language: string): Token[] {
  const tokens: Token[] = [];
  const yaml = language === 'yaml' || language === 'toml';
  let index = 0;
  const push = (value: string, kind: TokenKind) => { if (value) tokens.push({ value, kind }); };

  while (index < line.length) {
    const rest = line.slice(index);
    const comment = (language === 'python' || yaml || language === 'shell' || language === 'ini')
      ? rest.match(/^\s*#.*$/)
      : rest.match(/^\s*\/\/.*$/);
    if (comment) { push(comment[0], 'comment'); break; }

    const quote = rest.match(/^(?:"""[\s\S]*?"""|'''[\s\S]*?'''|`(?:\\.|[^`])*`|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/);
    if (quote) { push(quote[0], 'string'); index += quote[0].length; continue; }

    const number = rest.match(/^\b(?:0x[\da-f]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?)\b/i);
    if (number) { push(number[0], 'number'); index += number[0].length; continue; }

    const word = rest.match(/^[A-Za-z_$][\w$-]*/);
    if (word) {
      const afterWord = line.slice(index + word[0].length);
      const isKey = yaml && /^\s*:/.test(afterWord);
      const kind: TokenKind = isKey ? 'key' : keywordSet.has(word[0]) ? 'keyword' : 'plain';
      push(word[0], kind);
      index += word[0].length;
      continue;
    }

    const character = line[index];
    push(character, punctuationSet.has(character) ? 'punctuation' : 'plain');
    index += 1;
  }
  return tokens;
}

export function highlightCodeLine(line: string, filePath: string): string {
  return tokenizeLine(line, getEditorLanguage(filePath)).map(({ value, kind }) => {
    const text = escapeHtml(value);
    return kind === 'plain' ? text : `<span style="color:${palettes[kind]}">${text}</span>`;
  }).join('');
}

function escapeHtml(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function highlight(source: string, language: string): string {
  return source.split('\n').map((line) => tokenizeLine(line, language).map(({ value, kind }) => {
    const text = escapeHtml(value);
    return kind === 'plain' ? text : `<span style="color:${palettes[kind]}">${text}</span>`;
  }).join('')).join('\n') + (source.endsWith('\n') ? ' ' : '');
}

export function getEditorLanguage(path: string): string {
  const extension = path.split('.').pop()?.toLowerCase() || '';
  const languages: Record<string, string> = {
    py: 'python', pyw: 'python', yaml: 'yaml', yml: 'yaml', toml: 'toml',
    js: 'javascript', jsx: 'javascript', mjs: 'javascript', cjs: 'javascript',
    ts: 'typescript', tsx: 'typescript', json: 'json', jsonc: 'json',
    sh: 'shell', bash: 'shell', zsh: 'shell', ps1: 'shell',
    html: 'html', htm: 'html', xml: 'html', css: 'css', scss: 'css', sql: 'sql',
    md: 'markdown', markdown: 'markdown',
  };
  return languages[extension] || 'plain';
}

export const CodeEditor: React.FC<{
  value: string;
  onChange: (value: string) => void;
  filePath: string;
  ariaLabel: string;
  readOnly?: boolean;
}> = ({ value, onChange, filePath, ariaLabel, readOnly = false }) => {
  const language = getEditorLanguage(filePath);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const codeRef = useRef<HTMLPreElement>(null);
  const gutterRef = useRef<HTMLPreElement>(null);
  const highlighted = useMemo(() => highlight(value, language), [language, value]);
  const lineCount = Math.max(1, value.split('\n').length);
  const font = 'ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace';

  return <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: 360, overflow: 'hidden', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md-wide)', background: 'var(--bg-surface)' }}>
    <pre ref={gutterRef} aria-hidden="true" style={{ position: 'absolute', zIndex: 1, top: 0, bottom: 0, left: 0, width: 48, margin: 0, padding: 'var(--space-3-5) var(--space-2-25) var(--space-3-5) 0', overflow: 'hidden', borderRight: '1px solid var(--border-subtle)', color: 'var(--text-muted)', background: 'var(--bg-surface-elevated)', textAlign: 'right', fontFamily: font, fontSize: 'var(--font-size-md)', lineHeight: 1.65, whiteSpace: 'pre' }}>{Array.from({ length: lineCount }, (_, index) => String(index + 1)).join('\n')}</pre>
    <pre ref={codeRef} aria-hidden="true" style={{ position: 'absolute', inset: 0, margin: 0, padding: 'var(--space-3-5) var(--space-4-5) var(--space-3-5) 62px', overflow: 'hidden', color: palettes.plain, fontFamily: font, fontSize: 'var(--font-size-md)', lineHeight: 1.65, whiteSpace: 'pre', tabSize: 2 }} dangerouslySetInnerHTML={{ __html: highlighted }} />
    <textarea
      ref={textareaRef}
      aria-label={ariaLabel}
      value={value}
      readOnly={readOnly}
      onChange={(event) => onChange(event.target.value)}
      onScroll={(event) => {
        if (codeRef.current) {
          codeRef.current.scrollTop = event.currentTarget.scrollTop;
          codeRef.current.scrollLeft = event.currentTarget.scrollLeft;
        }
        if (gutterRef.current) gutterRef.current.scrollTop = event.currentTarget.scrollTop;
      }}
      onKeyDown={(event) => {
        if (readOnly) return;
        if (event.key === 'Tab') {
          event.preventDefault();
          const input = event.currentTarget;
          const start = input.selectionStart;
          const end = input.selectionEnd;
          const next = `${value.slice(0, start)}  ${value.slice(end)}`;
          onChange(next);
          requestAnimationFrame(() => input.setSelectionRange(start + 2, start + 2));
        }
      }}
      spellCheck={false}
      autoCapitalize="off"
      autoCorrect="off"
      style={{ position: 'absolute', zIndex: 2, inset: 0, width: '100%', height: '100%', minHeight: 360, resize: 'none', padding: 'var(--space-3-5) var(--space-4-5) var(--space-3-5) 62px', overflow: 'auto', border: 0, outline: 'none', background: 'transparent', color: 'transparent', caretColor: readOnly ? 'transparent' : 'var(--text-primary)', WebkitTextFillColor: 'transparent', fontFamily: font, fontSize: 'var(--font-size-md)', lineHeight: 1.65, whiteSpace: 'pre', tabSize: 2, cursor: readOnly ? 'text' : 'auto' }}
    />
  </div>;
};
