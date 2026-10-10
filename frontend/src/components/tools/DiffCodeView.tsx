import React from 'react';
import { CodeEditor, highlightCodeLine } from './CodeEditor';

interface DiffCodeViewProps {
  diffText?: string;
  fileName?: string | null;
  sourceText?: string | null;
  message?: string | null;
}

/**
 * 差异对比查看器的代码差异统一视窗
 */
export const DiffCodeView: React.FC<DiffCodeViewProps> = ({ diffText, fileName, sourceText, message }) => {
  if (sourceText !== null && sourceText !== undefined) {
    return <div style={{ flex: 1, minWidth: 0, overflow: 'auto', padding: 14, fontFamily: 'monospace', fontSize: 12 }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 9 }}>新建文件 · {fileName}</div>
      <CodeEditor ariaLabel={`预览变更 ${fileName || ''}`} filePath={fileName || ''} value={sourceText} onChange={() => undefined} readOnly />
    </div>;
  }
  if (!diffText) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: 20 }}>
        {message || (fileName ? `${fileName} 暂无可显示的预览内容` : '当前工作树没有未提交的差异变动')}
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 14, fontFamily: 'monospace', fontSize: 12 }}>
      <pre style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5, margin: 0 }}>
        {diffText.split('\n').map((line, i) => {
          let color = 'var(--text-secondary)';
          let bg = 'transparent';
          if (line.startsWith('+')) {
            color = 'var(--accent-emerald)';
            bg = 'rgba(16, 185, 129, 0.1)';
          } else if (line.startsWith('-')) {
            color = 'var(--accent-rose)';
            bg = 'rgba(239, 68, 68, 0.1)';
          } else if (line.startsWith('@@')) {
            color = 'var(--accent-cyan)';
          }
          const isChange = line.startsWith('+') || line.startsWith('-');
          const isMeta = line.startsWith('diff --git ') || line.startsWith('index ') || line.startsWith('--- ') || line.startsWith('+++ ') || line.startsWith('\\');
          const prefix = isChange ? line[0] : '';
          const code = isChange ? line.slice(1) : line;
          return <div key={i} style={{ color, backgroundColor: bg, padding: '1px 4px' }}>
            {isChange ? <><span>{prefix}</span><span dangerouslySetInnerHTML={{ __html: highlightCodeLine(code, fileName || '') }} /></> : isMeta || line.startsWith('@@') ? line : <span dangerouslySetInnerHTML={{ __html: highlightCodeLine(line, fileName || '') }} />}
          </div>;
        })}
      </pre>
    </div>
  );
};
