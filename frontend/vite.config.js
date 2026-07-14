import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The dev server proxies /api -> FastAPI backend, so the browser sees a single
// origin (no CORS) and SSE streams through untouched.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
    },
  },
  build: { outDir: 'dist' },
})
