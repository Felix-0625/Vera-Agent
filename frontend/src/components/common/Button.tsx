import React from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'success' | 'danger' | 'ghost' | 'outline';
type ButtonSize = 'sm' | 'compact' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'secondary',
  size = 'md',
  icon,
  className,
  style,
  type = 'button',
  disabled,
  ...props
}) => (
  <button
    {...props}
    type={type}
    disabled={disabled}
    className={['ui-button', `ui-button--${variant}`, `ui-button--${size}`, className]
      .filter(Boolean)
      .join(' ')}
    style={{ opacity: disabled ? 0.55 : undefined, ...style }}
  >
    {icon}
    {children}
  </button>
);
