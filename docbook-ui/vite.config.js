import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  optimizeDeps: {
    include: ['vue-sonner', 'dompurify', 'reka-ui']
  },
  server: {
    port: 8080,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      // QR passes and uploaded files are served by Frappe from /files —
      // without this proxy they 404 on the dev server and the QR breaks.
      '/files': { target: 'http://localhost:8000', changeOrigin: true },
      '/assets': { target: 'http://localhost:8000', changeOrigin: true },
    }
  }
})