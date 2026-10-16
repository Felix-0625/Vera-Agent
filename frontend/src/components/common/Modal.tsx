import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { IconButton } from './IconButton';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  width?: number | string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  hideHeader?: boolean;
  titleStyle?: React.CSSProperties;
  headerStyle?: React.CSSProperties;
  contentStyle?: React.CSSProperties;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  width = 600,
  children,
  footer,
  hideHeader = false,
  titleStyle,
  headerStyle,
  contentStyle,
}) => {
  const titleId = React.useId();
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'var(--overlay-scrim)',
        backdropFilter: 'blur(8px)',
      }}
    >
      <div
        className="animate-fade-in glass-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={hideHeader ? undefined : titleId}
        aria-label={hideHeader ? title : undefined}
        style={{
          position: 'relative',
          width,
          maxWidth: '92vw',
          maxHeight: '90vh',
          borderRadius: 'var(--radius-lg)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: 'var(--shadow-lg)',
          overflow: 'hidden',
        }}
      >
        {!hideHeader && <div
          style={{
            padding: 'var(--space-4) var(--space-5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid var(--border-subtle)',
            ...headerStyle,
          }}
        >
          <h3 id={titleId} style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--text-primary)', ...titleStyle }}>
            {title}
          </h3>
          <IconButton label="关闭" onClick={onClose} size="sm">
            <X size={18} />
          </IconButton>
        </div>}
        {hideHeader && <IconButton label="关闭" onClick={onClose} size="sm" style={{ position: 'absolute', top: 12, right: 14, zIndex: 2, background: 'var(--bg-card-hover)' }}><X size={18} /></IconButton>}

        {/* Content */}
        <div style={{ padding: 'var(--space-5)', overflowY: 'auto', flex: 1, ...contentStyle }}>
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div
            style={{
              padding: 'var(--space-3) var(--space-5)',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 'var(--space-2-5)',
              backgroundColor: 'var(--bg-surface-elevated)',
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
