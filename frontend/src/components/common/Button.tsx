import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'secondary',
  size = 'md',
  icon,
  style,
  disabled,
  ...props
}) => {
  const getStyles = (): React.CSSProperties => {
    const base: React.CSSProperties = {
      fontWeight: 500,
      borderRadius: 'var(--radius-md)',
      transition: 'all 0.15s ease',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      ...style,
    };

    if (size === 'sm') {
      base.padding = '4px 10px';
      base.fontSize = '12px';
    } else if (size === 'lg') {
      base.padding = '10px 20px';
      base.fontSize = '14px';
    } else {
      base.padding = '6px 14px';
      base.fontSize = '13px';
    }

    if (variant === 'primary') {
      base.background = 'var(--accent-gradient)';
      base.color = '#FFFFFF';
      base.border = 'none';
      base.boxShadow = 'var(--shadow-sm)';
    } else if (variant === 'danger') {
      base.background = 'rgba(239, 68, 68, 0.15)';
      base.color = 'var(--accent-rose)';
      base.border = '1px solid rgba(239, 68, 68, 0.3)';
    } else if (variant === 'ghost') {
      base.background = 'transparent';
      base.color = 'var(--text-secondary)';
      base.border = 'none';
    } else if (variant === 'outline') {
      base.background = 'transparent';
      base.color = 'var(--text-primary)';
      base.border = '1px solid var(--border-default)';
    } else {
      // secondary
      base.background = 'var(--bg-card)';
      base.color = 'var(--text-primary)';
      base.border = '1px solid var(--border-subtle)';
    }

    return base;
  };

  return (
    <button style={getStyles()} disabled={disabled} {...props}>
      {icon}
      {children}
    </button>
  );
};
