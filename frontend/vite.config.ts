import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    base: mode === 'desktop' ? './' : '/',
    define: {
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify(
        mode === 'desktop' ? 'http://127.0.0.1:8000' : env.VITE_API_BASE_URL || '',
      ),
    },
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000',
          changeOrigin: true,
          ws: true,
        },
      },
    },
  }
})
