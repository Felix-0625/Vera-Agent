import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';

const inlinePattern = /(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|~~[^~]+~~|\[[^\]]+\]\([^)]+\)|\*[^*\n]+\*|_[^_\n]+_)/g;

function safeHref(value: string): string | null {
  const href = value.trim();
  return /^(https?:\/\/|mailto:)/i.test(href) ? href : null;
}

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const parts = text.split(inlinePattern);
  return parts.map((part, index) => {
    const key = `${keyPrefix}-${index}`;
    if (part.startsWith('`') && part.endsWith('`')) return <code className="markdown-inline-code" key={key}>{part.slice(1, -1)}</code>;
    if ((part.startsWith('**') && part.endsWith('**')) || (part.startsWith('__') && part.endsWith('__'))) return <strong key={key}>{renderInline(part.slice(2, -2), key)}</strong>;
    if (part.startsWith('~~') && part.endsWith('~~')) return <del key={key}>{part.slice(2, -2)}</del>;
    if ((part.startsWith('*') && part.endsWith('*')) || (part.startsWith('_') && part.endsWith('_'))) return <em key={key}>{part.slice(1, -1)}</em>;
    if (part.startsWith('[')) {
      const match = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (match) {
        const href = safeHref(match[2]);
        return href ? <a key={key} href={href} target="_blank" rel="noreferrer noopener">{match[1]}</a> : <span key={key}>{match[1]}</span>;
      }
    }
    return part;
  });
}

function cells(line: string): string[] {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => cell.trim());
}

const CodeBlock: React.FC<{ code: string; language: string }> = ({ code, language }) => {
  const [copied, setCopied] = useState(false);
  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="markdown-code-container">
      <div className="markdown-code-toolbar">
        <span>{language || '代码'}</span>
        <button type="button" onClick={() => void copyCode()} aria-label={copied ? '代码已复制' : '复制代码'} title={copied ? '已复制' : '复制代码'}>
          {copied ? <Check size={13} /> : <Copy size={13} />}{copied ? '已复制' : '复制'}
        </button>
      </div>
      <pre className="markdown-code-block"><code>{code}</code></pre>
    </div>
  );
};

function startsBlock(lines: string[], index: number): boolean {
  const line = lines[index];
  return /^\s{0,3}(#{1,6}\s|>|```|~~~|([-+*]|\d+[.)])\s+)/.test(line)
    || /^\s{0,3}((\*\s*){3,}|(-\s*){3,}|(_\s*){3,})$/.test(line)
    || (line.includes('|') && index + 1 < lines.length && /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[index + 1]));
}

export const MarkdownContent: React.FC<{ content: string }> = ({ content }) => {
  const lines = content.replace(/\r\n?/g, '\n').split('\n');
  const blocks: React.ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index += 1; continue; }

    const fence = line.match(/^\s*(```+|~~~+)\s*([\w.+#-]*)\s*$/);
    if (fence) {
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !new RegExp(`^\\s*${fence[1][0]}{${fence[1].length},}\\s*$`).test(lines[index])) codeLines.push(lines[index++]);
      if (index < lines.length) index += 1;
      blocks.push(<CodeBlock code={codeLines.join('\n')} language={fence[2]} key={`block-${blocks.length}`} />);
      continue;
    }

    const heading = line.match(/^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (heading) {
      const level = heading[1].length;
      blocks.push(React.createElement(`h${level}`, { className: 'markdown-heading', key: `block-${blocks.length}` }, renderInline(heading[2], `heading-${blocks.length}`)));
      index += 1;
      continue;
    }

    if (/^\s{0,3}((\*\s*){3,}|(-\s*){3,}|(_\s*){3,})$/.test(line)) {
      blocks.push(<hr className="markdown-rule" key={`block-${blocks.length}`} />);
      index += 1;
      continue;
    }

    if (line.includes('|') && index + 1 < lines.length && /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[index + 1])) {
      const headers = cells(line);
      index += 2;
      const rows: string[][] = [];
      while (index < lines.length && lines[index].includes('|') && lines[index].trim()) rows.push(cells(lines[index++]));
      blocks.push(<div className="markdown-table-wrap" key={`block-${blocks.length}`}><table className="markdown-table"><thead><tr>{headers.map((cell, cellIndex) => <th key={cellIndex}>{renderInline(cell, `th-${blocks.length}-${cellIndex}`)}</th>)}</tr></thead><tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{headers.map((_, cellIndex) => <td key={cellIndex}>{renderInline(row[cellIndex] || '', `td-${blocks.length}-${rowIndex}-${cellIndex}`)}</td>)}</tr>)}</tbody></table></div>);
      continue;
    }

    const listMatch = line.match(/^\s*(?:([-+*])|(\d+)[.)])\s+(.+)$/);
    if (listMatch) {
      const ordered = Boolean(listMatch[2]);
      const items: string[] = [];
      while (index < lines.length) {
        const item = lines[index].match(/^\s*(?:([-+*])|(\d+)[.)])\s+(.+)$/);
        if (!item || Boolean(item[2]) !== ordered) break;
        items.push(item[3]);
        index += 1;
      }
      const List = ordered ? 'ol' : 'ul';
      blocks.push(<List className="markdown-list" key={`block-${blocks.length}`}>{items.map((item, itemIndex) => <li key={itemIndex}>{renderInline(item, `li-${blocks.length}-${itemIndex}`)}</li>)}</List>);
      continue;
    }

    if (/^\s{0,3}>/.test(line)) {
      const quoteLines: string[] = [];
      while (index < lines.length && /^\s{0,3}>/.test(lines[index])) quoteLines.push(lines[index++].replace(/^\s{0,3}>\s?/, ''));
      blocks.push(<blockquote className="markdown-quote" key={`block-${blocks.length}`}>{renderInline(quoteLines.join(' '), `quote-${blocks.length}`)}</blockquote>);
      continue;
    }

    const paragraph: string[] = [];
    while (index < lines.length && lines[index].trim() && !startsBlock(lines, index)) paragraph.push(lines[index++]);
    if (paragraph.length) blocks.push(<p className="markdown-paragraph" key={`block-${blocks.length}`}>{paragraph.map((text, lineIndex) => <React.Fragment key={lineIndex}>{lineIndex > 0 && <br />}{renderInline(text, `p-${blocks.length}-${lineIndex}`)}</React.Fragment>)}</p>);
    else index += 1;
  }

  return <div className="markdown-content">{blocks}</div>;
};
