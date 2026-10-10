import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Check, FileText, Pencil, Save, X } from 'lucide-react';
import { saveExcelFile, saveTextFile } from '../../api/toolApi';
import { useFilePreviewStore, FilePreviewRecord } from '../../stores/filePreviewStore';
import { CodeEditor } from './CodeEditor';

const actionStyle: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 10px', borderRadius: 8,
  background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)', fontSize: 12, cursor: 'pointer',
};

export const FilePreviewPane: React.FC<{
  file: FilePreviewRecord;
  projectKey: string;
  projectId?: string | null;
  groupId?: string | null;
  onClose?: () => void;
  embedded?: boolean;
}> = ({ file, projectKey, projectId, groupId, onClose, embedded = false }) => {
  const [editing, setEditing] = useState(false);
  const [textDraft, setTextDraft] = useState('');
  const [sheetDraft, setSheetDraft] = useState<Array<{ name: string; rows: string[][] }>>([]);
  const [activeSheet, setActiveSheet] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const showPreview = useFilePreviewStore((state) => state.showPreview);
  const canEditExcel = /\.(xlsx|xlsm)$/i.test(file.path);
  const canEditText = /\.(md|markdown|txt|py|pyw|yaml|yml|toml|js|jsx|mjs|cjs|ts|tsx|json|jsonc|sh|bash|zsh|ps1|bat|cmd|html|htm|xml|css|scss|sass|less|sql|ini|cfg|conf|log|go|rs|java|c|h|cpp|hpp|cs|php|rb|vue|svelte|graphql|gql|r)$/i.test(file.path) || /(^|[\\/])\.gitignore$/i.test(file.path);
  const canEdit = canEditText || canEditExcel;

  useEffect(() => {
    setEditing(false);
    setError('');
    setActiveSheet(0);
    if (file.preview.kind === 'text') setTextDraft(file.preview.content);
    if (file.preview.kind === 'excel') setSheetDraft(file.preview.sheets.map((sheet) => ({ name: sheet.name, rows: sheet.rows.map((row) => [...row]) })));
  }, [file.path, file.preview]);

  const columns = useMemo(() => {
    if (file.preview.kind !== 'excel') return 0;
    return Math.max(0, ...file.preview.sheets.flatMap((sheet) => sheet.rows.map((row) => row.length)));
  }, [file.preview]);

  const beginEdit = () => {
    if (file.preview.kind === 'text') setTextDraft(file.preview.content);
    if (file.preview.kind === 'excel') setSheetDraft(file.preview.sheets.map((sheet) => ({ name: sheet.name, rows: sheet.rows.map((row) => [...row]) })));
    setError('');
    setEditing(true);
  };

  const cancelEdit = () => {
    setEditing(false);
    setError('');
    beginEditReset();
  };

  const beginEditReset = () => {
    if (file.preview.kind === 'text') setTextDraft(file.preview.content);
    if (file.preview.kind === 'excel') setSheetDraft(file.preview.sheets.map((sheet) => ({ name: sheet.name, rows: sheet.rows.map((row) => [...row]) })));
  };

  const save = async () => {
    setSaving(true);
    setError('');
    try {
      if (file.preview.kind === 'text') {
        await saveTextFile(file.path, textDraft, groupId || undefined, projectId || undefined);
        showPreview(projectKey, { ...file, preview: { kind: 'text', content: textDraft } });
      } else if (file.preview.kind === 'excel') {
        await saveExcelFile(file.path, sheetDraft, groupId || undefined, projectId || undefined);
        showPreview(projectKey, { ...file, preview: { ...file.preview, sheets: sheetDraft } });
      }
      setEditing(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const updateCell = (rowIndex: number, columnIndex: number, value: string) => {
    setSheetDraft((current) => current.map((sheet, index) => {
      if (index !== activeSheet) return sheet;
      const rows = sheet.rows.map((row) => [...row]);
      while (rows.length <= rowIndex) rows.push([]);
      while (rows[rowIndex].length <= columnIndex) rows[rowIndex].push('');
      rows[rowIndex][columnIndex] = value;
      return { ...sheet, rows };
    }));
  };

  return (
    <section style={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column', background: 'var(--bg-workspace)', color: 'var(--text-primary)' }}>
      <header style={{ minHeight: 48, padding: '0 16px', display: 'flex', alignItems: 'center', gap: 10, borderBottom: '1px solid var(--border-subtle)', flexShrink: 0 }}>
        {onClose && <button onClick={onClose} title="返回对话" aria-label="返回对话" style={{ ...actionStyle, padding: 6 }}><ArrowLeft size={14} /></button>}
        <FileText size={15} color="var(--accent-cyan)" />
        <strong title={file.path} style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 13 }}>{file.name}</strong>
        <span style={{ color: 'var(--text-muted)', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.path}</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, flexShrink: 0 }}>
          {canEdit && !editing && <button style={actionStyle} onClick={beginEdit}><Pencil size={13} />开始修改</button>}
          {editing && <>
            <button style={actionStyle} onClick={cancelEdit} disabled={saving}><X size={13} />取消修改</button>
            <button style={{ ...actionStyle, color: 'white', borderColor: 'transparent', background: 'var(--accent-primary)' }} onClick={save} disabled={saving}><Save size={13} />{saving ? '保存中…' : '保存'}</button>
          </>}
        </div>
      </header>
      {error && <div role="alert" style={{ padding: '8px 16px', color: 'var(--accent-rose)', fontSize: 12, borderBottom: '1px solid var(--border-subtle)' }}>{error}</div>}
      <div style={{ minHeight: 0, flex: 1, overflow: 'auto', padding: embedded ? 12 : 18 }}>
        {file.preview.kind === 'image' && <div style={{ height: '100%', display: 'grid', placeItems: 'center' }}><img src={file.preview.url} alt={file.name} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: 8 }} /></div>}
        {file.preview.kind === 'pdf' && <iframe title={file.name} src={file.preview.url} style={{ width: '100%', height: '100%', minHeight: 400, border: 0, borderRadius: 8, background: 'white' }} />}
        {file.preview.kind === 'text' && (editing ?
          <CodeEditor ariaLabel={`编辑 ${file.name}`} filePath={file.path} value={textDraft} onChange={setTextDraft} /> :
          <CodeEditor ariaLabel={`预览 ${file.name}`} filePath={file.path} value={file.preview.content} onChange={() => undefined} readOnly />)}
        {file.preview.kind === 'ppt' && <div style={{ display: 'grid', gap: 12, maxWidth: 900, margin: '0 auto' }}>{file.preview.slides.map((slide, index) => <article key={index} style={{ minHeight: 190, padding: 22, borderRadius: 12, border: '1px solid var(--border-subtle)', background: 'var(--bg-surface)' }}><div style={{ marginBottom: 16, color: 'var(--text-muted)', fontSize: 11 }}>幻灯片 {index + 1}</div><pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit', lineHeight: 1.65 }}>{slide.text || '（此页没有可提取的文字）'}</pre></article>)}</div>}
        {file.preview.kind === 'excel' && <div style={{ minWidth: '100%', width: 'max-content' }}>
          {file.preview.sheets.length > 1 && <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>{file.preview.sheets.map((sheet, index) => <button key={sheet.name} onClick={() => setActiveSheet(index)} style={{ ...actionStyle, color: activeSheet === index ? 'var(--accent-cyan)' : 'var(--text-secondary)' }}>{sheet.name}</button>)}</div>}
          <table style={{ borderCollapse: 'collapse', fontSize: 12, minWidth: '100%' }}><tbody>{(editing ? sheetDraft[activeSheet]?.rows : file.preview.sheets[activeSheet]?.rows)?.map((row, rowIndex) => <tr key={rowIndex}>{Array.from({ length: Math.max(columns, row.length) }, (_, columnIndex) => <td key={columnIndex} style={{ minWidth: 100, height: 31, padding: 0, border: '1px solid var(--border-subtle)', background: rowIndex === 0 ? 'var(--bg-surface-elevated)' : 'var(--bg-surface)' }}>{editing ? <input aria-label={`${file.preview.kind === 'excel' ? sheetDraft[activeSheet]?.name : ''} 第${rowIndex + 1}行第${columnIndex + 1}列`} value={row[columnIndex] || ''} onChange={(event) => updateCell(rowIndex, columnIndex, event.target.value)} style={{ width: '100%', minWidth: 100, height: 30, padding: '0 8px', border: 0, outline: '1px solid transparent', background: 'transparent', color: 'var(--text-primary)', fontSize: 12 }} /> : <div style={{ padding: '7px 9px', whiteSpace: 'pre-wrap' }}>{row[columnIndex] || ''}</div>}</td>)}</tr>)}</tbody></table>
        </div>}
        {file.preview.kind === 'unsupported' && <div style={{ minHeight: 240, display: 'grid', placeContent: 'center', gap: 10, textAlign: 'center', color: 'var(--text-secondary)' }}><div>{file.preview.message}</div>{file.preview.url && <a href={file.preview.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent-cyan)' }}>在新窗口打开或下载</a>}</div>}
      </div>
    </section>
  );
};
