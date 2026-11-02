import React from 'react';

interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  tone?: 'neutral' | 'danger';
  size?: 'sm' | 'md';
  active?: boolean;
}

/** Accessible icon-only action with a consistent hit target and hover state. */
export const IconButton: React.FC<IconButtonProps> = ({
  label,
  tone = 'neutral',
  size = 'md',
  active = false,
  className,
  children,
  type = 'button',
  ...props
}) => (
  <button
    {...props}
    type={type}
    aria-label={props['aria-label'] ?? label}
    title={props.title ?? label}
    aria-pressed={props['aria-pressed'] ?? (active ? true : undefined)}
    className={[
      'ui-icon-button',
      `ui-icon-button--${tone}`,
      `ui-icon-button--${size}`,
      active && 'ui-icon-button--active',
      className,
    ]
      .filter(Boolean)
      .join(' ')}
  >
    {children}
  </button>
);
