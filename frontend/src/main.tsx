import { StrictMode, useLayoutEffect } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';

export function StartupApp() {
  useLayoutEffect(() => {
    document.getElementById('startup-screen')?.remove();
  }, []);

  return <App />;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <StartupApp />
  </StrictMode>,
);
