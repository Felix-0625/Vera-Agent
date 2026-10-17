import React, { useMemo, useRef } from 'react';
import { editorTextColor, getEditorLanguage, highlight } from './codeEditorUtils';

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
    <pre ref={codeRef} aria-hidden="true" style={{ position: 'absolute', inset: 0, margin: 0, padding: 'var(--space-3-5) var(--space-4-5) var(--space-3-5) 62px', overflow: 'hidden', color: editorTextColor, fontFamily: font, fontSize: 'var(--font-size-md)', lineHeight: 1.65, whiteSpace: 'pre', tabSize: 2 }} dangerouslySetInnerHTML={{ __html: highlighted }} />
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
