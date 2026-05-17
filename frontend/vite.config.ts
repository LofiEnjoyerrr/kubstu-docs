import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backendHost = process.env.BACKEND_HOST ?? 'localhost:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': { target: `http://${backendHost}`, changeOrigin: true },
      '/ws':  { target: `ws://${backendHost}`,  ws: true, changeOrigin: true },
      '/media': { target: `http://${backendHost}`, changeOrigin: true },
    },
  },
})
