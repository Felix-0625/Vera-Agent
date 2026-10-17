import React from 'react';
import { CodeEditor } from './CodeEditor';
import { highlightCodeLine } from './codeEditorUtils';

interface DiffCodeViewProps {
  diffText?: string;
  fileName?: string | null;
  sourceText?: string | null;
  message?: string | null;
}


export const DiffCodeView: React.FC<DiffCodeViewProps> = ({ diffText, fileName, sourceText, message }) => {
  if (sourceText !== null && sourceText !== undefined) {
    return <div style={{ flex: 1, minWidth: 0, overflow: 'auto', padding: 'var(--space-3-5)', fontFamily: 'monospace', fontSize: 'var(--font-size-sm)' }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 'var(--space-2-25)' }}>新建文件 · {fileName}</div>
      <CodeEditor ariaLabel={`预览变更 ${fileName || ''}`} filePath={fileName || ''} value={sourceText} onChange={() => undefined} readOnly />
    </div>;
  }
  if (!diffText) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 'var(--font-size-md)', textAlign: 'center', padding: 'var(--space-5)' }}>
        {message || (fileName ? `${fileName} 暂无可显示的预览内容` : '当前工作树没有未提交的差异变动')}
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-3-5)', fontFamily: 'monospace', fontSize: 'var(--font-size-sm)' }}>
      <pre style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5, margin: 0 }}>
        {diffText.split('\n').map((line, i) => {
          let color = 'var(--text-secondary)';
          let bg = 'transparent';
          if (line.startsWith('+')) {
            color = 'var(--accent-emerald)';
            bg = 'var(--bg-success-soft)';
          } else if (line.startsWith('-')) {
            color = 'var(--accent-rose)';
            bg = 'var(--bg-danger-soft)';
          } else if (line.startsWith('@@')) {
            color = 'var(--accent-cyan)';
          }
          const isChange = line.startsWith('+') || line.startsWith('-');
          const isMeta = line.startsWith('diff --git ') || line.startsWith('index ') || line.startsWith('--- ') || line.startsWith('+++ ') || line.startsWith('\\');
          const prefix = isChange ? line[0] : '';
          const code = isChange ? line.slice(1) : line;
          return <div key={i} style={{ color, backgroundColor: bg, padding: '1px var(--space-1)' }}>
            {isChange ? <><span>{prefix}</span><span dangerouslySetInnerHTML={{ __html: highlightCodeLine(code, fileName || '') }} /></> : isMeta || line.startsWith('@@') ? line : <span dangerouslySetInnerHTML={{ __html: highlightCodeLine(line, fileName || '') }} />}
          </div>;
        })}
      </pre>
    </div>
  );
};
