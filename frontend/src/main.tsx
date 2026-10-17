import { StrictMode, useLayoutEffect } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

export function StartupApp() {
  useLayoutEffect(() => {
    document.getElementById('startup-screen')?.remove()
  }, [])

  return <App />
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <StartupApp />
  </StrictMode>,
)
