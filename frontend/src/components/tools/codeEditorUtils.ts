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

const keywordSet = new Set(
  'const let var function return if else for while do switch case break continue try catch finally throw new class extends implements interface type enum import from export default as async await void null undefined true false this super public private protected static readonly get set typeof instanceof in of delete yield await def self pass lambda with raise except elif and or not is global nonlocal None True False'.split(
    /\s+/,
  ),
);
const punctuationSet = new Set('{}[](),.:;=<>+*/!?|&-');

function tokenizeLine(line: string, language: string): Token[] {
  const tokens: Token[] = [];
  const yaml = language === 'yaml' || language === 'toml';
  let index = 0;
  const push = (value: string, kind: TokenKind) => {
    if (value) tokens.push({ value, kind });
  };

  while (index < line.length) {
    const rest = line.slice(index);
    const comment =
      language === 'python' || yaml || language === 'shell' || language === 'ini'
        ? rest.match(/^\s*#.*$/)
        : rest.match(/^\s*\/\/.*$/);
    if (comment) {
      push(comment[0], 'comment');
      break;
    }

    const quote = rest.match(/^(?:"""[\s\S]*?"""|'''[\s\S]*?'''|`(?:\\.|[^`])*`|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/);
    if (quote) {
      push(quote[0], 'string');
      index += quote[0].length;
      continue;
    }

    const number = rest.match(/^\b(?:0x[\da-f]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?)\b/i);
    if (number) {
      push(number[0], 'number');
      index += number[0].length;
      continue;
    }

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

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function getEditorLanguage(path: string): string {
  const extension = path.split('.').pop()?.toLowerCase() || '';
  const languages: Record<string, string> = {
    py: 'python',
    pyw: 'python',
    yaml: 'yaml',
    yml: 'yaml',
    toml: 'toml',
    js: 'javascript',
    jsx: 'javascript',
    mjs: 'javascript',
    cjs: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    json: 'json',
    jsonc: 'json',
    sh: 'shell',
    bash: 'shell',
    zsh: 'shell',
    ps1: 'shell',
    html: 'html',
    htm: 'html',
    xml: 'html',
    css: 'css',
    scss: 'css',
    sql: 'sql',
    md: 'markdown',
    markdown: 'markdown',
  };
  return languages[extension] || 'plain';
}

export function highlightCodeLine(line: string, filePath: string): string {
  return tokenizeLine(line, getEditorLanguage(filePath))
    .map(({ value, kind }) => {
      const text = escapeHtml(value);
      return kind === 'plain' ? text : `<span style="color:${palettes[kind]}">${text}</span>`;
    })
    .join('');
}

export function highlight(source: string, language: string): string {
  return (
    source
      .split('\n')
      .map((line) =>
        tokenizeLine(line, language)
          .map(({ value, kind }) => {
            const text = escapeHtml(value);
            return kind === 'plain' ? text : `<span style="color:${palettes[kind]}">${text}</span>`;
          })
          .join(''),
      )
      .join('\n') + (source.endsWith('\n') ? ' ' : '')
  );
}

export const editorTextColor = palettes.plain;
