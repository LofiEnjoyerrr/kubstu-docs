import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      // Keep API + WS in lockstep with the Django/Daphne container.
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
      // DOCX import stores image URLs as ``/media/docs/N/images/x.png``.
      // Without this proxy the dev server would 404 them.
      '/media': 'http://localhost:8000',
      '/static': 'http://localhost:8000',
    },
  },
})
