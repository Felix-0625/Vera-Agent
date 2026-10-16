import React from 'react';

interface PageHeadingProps {
  title: string;
  description: string;
  actions?: React.ReactNode;
  divider?: boolean;
}

/** Shared title and description hierarchy for top-level pages and settings tabs. */
export const PageHeading: React.FC<PageHeadingProps> = ({ title, description, actions, divider = false }) => (
  <header className={`page-heading${divider ? ' page-heading--divided' : ''}`}>
    <div className="page-heading__copy">
      <h2>{title}</h2>
      <p>{description}</p>
    </div>
    {actions && <div className="page-heading__actions">{actions}</div>}
  </header>
);
