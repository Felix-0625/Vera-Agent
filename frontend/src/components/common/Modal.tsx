import React, { useEffect } from 'react';
import { X } from 'lucide-react';

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
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
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
        backgroundColor: 'rgba(0, 0, 0, 0.72)',
        backdropFilter: 'blur(8px)',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="animate-fade-in glass-panel"
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
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid var(--border-subtle)',
            ...headerStyle,
          }}
        >
          <h3 style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', ...titleStyle }}>
            {title}
          </h3>
          <button
            onClick={onClose}
            style={{
              padding: 4,
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-muted)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <X size={18} />
          </button>
        </div>}
        {hideHeader && <button onClick={onClose} aria-label="关闭" title="关闭" style={{ position: 'absolute', top: 12, right: 14, zIndex: 2, padding: 5, borderRadius: 7, color: 'var(--text-muted)', background: 'rgba(15,18,25,.68)' }}><X size={18} /></button>}

        {/* Content */}
        <div style={{ padding: 20, overflowY: 'auto', flex: 1, ...contentStyle }}>
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div
            style={{
              padding: '12px 20px',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 10,
              backgroundColor: 'rgba(10, 11, 15, 0.5)',
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
