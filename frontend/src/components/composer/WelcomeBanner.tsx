import React from 'react';
import { VeraLogo } from '../common/VeraLogo';


export const WelcomeBanner: React.FC = () => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '80px var(--space-5) 40px',
        userSelect: 'none',
      }}
    >
      {}
      <div style={{ marginBottom: 'var(--space-5)' }}>
        <VeraLogo size={52} />
      </div>

      {}
      <h1
        style={{
          fontSize: 22,
          fontWeight: 600,
          letterSpacing: '3px',
          color: 'var(--text-primary)',
          textAlign: 'center',
          margin: 0,
        }}
      >
        开  始  创  造  吧  ！
      </h1>
    </div>
  );
};
