import React from 'react';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title?: string;
  description?: string;
  className?: string;
  children?: React.ReactNode;
}

/** Theme-aware empty or waiting state with a consistent icon and text hierarchy. */
export const EmptyState: React.FC<EmptyStateProps> = ({ icon, title, description, className, children }) => (
  <div className={['ui-empty-state', className].filter(Boolean).join(' ')} role="status">
    {icon && <span className="ui-empty-state__icon" aria-hidden="true">{icon}</span>}
    {title && <strong className="ui-empty-state__title">{title}</strong>}
    {description && <span className="ui-empty-state__description">{description}</span>}
    {children}
  </div>
);
