import React from 'react';

interface SwitchProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'onChange'> {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export const Switch: React.FC<SwitchProps> = ({ label, checked, onChange, className, ...props }) => (
  <button
    {...props}
    type="button"
    role="switch"
    aria-checked={checked}
    aria-label={label}
    className={['ui-switch', checked && 'ui-switch--checked', className]
      .filter(Boolean)
      .join(' ')}
    onClick={(event) => {
      props.onClick?.(event);
      if (!event.defaultPrevented && !props.disabled) onChange(!checked);
    }}
  >
    <span className="ui-switch__thumb" aria-hidden="true" />
  </button>
);
