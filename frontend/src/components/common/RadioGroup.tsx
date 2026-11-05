import React from 'react';

interface RadioOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface RadioGroupProps {
  label: string;
  value: string;
  options: RadioOption[];
  onChange: (value: string) => void;
  className?: string;
  disabled?: boolean;
}

/** Accessible, theme-aware radio group for mutually exclusive choices. */
export const RadioGroup: React.FC<RadioGroupProps> = ({ label, value, options, onChange, className, disabled }) => {
  const groupId = React.useId();

  return (
    <div className={['ui-radio-group', className].filter(Boolean).join(' ')} role="radiogroup" aria-label={label}>
      {options.map((option) => {
        const optionId = `${groupId}-${option.value}`;
        const optionDisabled = disabled || option.disabled;
        return (
          <label className="ui-radio-option" key={option.value} htmlFor={optionId}>
            <input
              className="ui-radio-option__input"
              id={optionId}
              name={groupId}
              type="radio"
              value={option.value}
              checked={value === option.value}
              disabled={optionDisabled}
              onChange={() => onChange(option.value)}
            />
            <span className="ui-radio-option__label">{option.label}</span>
          </label>
        );
      })}
    </div>
  );
};
