import React, { useEffect, useRef, useState } from 'react';

interface InlineThreadRenameProps {
  title: string;
  onSave: (title: string) => Promise<void>;
  onCancel: () => void;
}

export const InlineThreadRename: React.FC<InlineThreadRenameProps> = ({ title, onSave, onCancel }) => {
  const [value, setValue] = useState(title);
  const inputRef = useRef<HTMLInputElement>(null);
  const savingRef = useRef(false);
  const cancelledRef = useRef(false);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const save = async () => {
    if (savingRef.current || cancelledRef.current) return;
    const nextTitle = value.trim();
    if (!nextTitle || nextTitle === title) {
      onCancel();
      return;
    }
    savingRef.current = true;
    try {
      await onSave(nextTitle);
    } catch {
      savingRef.current = false;
      inputRef.current?.focus();
    }
  };

  return <input
    ref={inputRef}
    aria-label="对话名称"
    value={value}
    onChange={event => setValue(event.target.value)}
    onClick={event => event.stopPropagation()}
    onKeyDown={event => {
      event.stopPropagation();
      if (event.key === 'Enter') {
        event.preventDefault();
        void save();
      } else if (event.key === 'Escape') {
        event.preventDefault();
        cancelledRef.current = true;
        onCancel();
      }
    }}
    onBlur={() => void save()}
    style={{ minWidth: 0, width: '100%', height: 25, padding: '1px 5px', borderRadius: 5, border: '1px solid rgba(75,145,255,.72)', background: 'rgba(75,145,255,.08)', color: 'var(--text-primary)', fontSize: 'inherit', outline: 'none' }}
  />;
};
