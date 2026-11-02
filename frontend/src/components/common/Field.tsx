import { Search } from 'lucide-react';
import React from 'react';

type FieldProps = React.InputHTMLAttributes<HTMLInputElement>;

/** Standard theme-aware input for ordinary form fields. */
export const TextInput = React.forwardRef<HTMLInputElement, FieldProps>(({ className, ...props }, ref) => (
  <input {...props} ref={ref} className={['ui-field', className].filter(Boolean).join(' ')} />
));
TextInput.displayName = 'TextInput';

type TextAreaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

/** Standard theme-aware multiline input; specialized editors may keep their own presentation. */
export const TextArea = React.forwardRef<HTMLTextAreaElement, TextAreaProps>(({ className, ...props }, ref) => (
  <textarea {...props} ref={ref} className={['ui-field', 'ui-field--multiline', className].filter(Boolean).join(' ')} />
));
TextArea.displayName = 'TextArea';

type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement>;

/** Standard theme-aware native select for ordinary form fields. */
export const SelectField = React.forwardRef<HTMLSelectElement, SelectProps>(({ className, ...props }, ref) => (
  <select {...props} ref={ref} className={['ui-field', 'ui-field--select', className].filter(Boolean).join(' ')} />
));
SelectField.displayName = 'SelectField';

interface SearchFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  wrapperClassName?: string;
  rightAdornment?: React.ReactNode;
}

/** Consistent search input with a semantic icon and optional trailing content. */
export const SearchField = React.forwardRef<HTMLInputElement, SearchFieldProps>(
  ({ wrapperClassName, rightAdornment, className, type = 'search', ...props }, ref) => (
    <label className={['ui-search-field', wrapperClassName].filter(Boolean).join(' ')}>
      <Search className="ui-search-field__icon" size={14} aria-hidden="true" />
      <input
        {...props}
        ref={ref}
        type={type}
        className={['ui-search-field__input', className].filter(Boolean).join(' ')}
      />
      {rightAdornment}
    </label>
  ),
);
SearchField.displayName = 'SearchField';
