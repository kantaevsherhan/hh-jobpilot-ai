import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) }
  },
  server: {
    port: 5173,
    // Фронт ходит только в собственный API (§4): всё под /api уходит на бэкенд
    proxy: { '/api': 'http://127.0.0.1:8000' }
  },
  test: {
    environment: 'jsdom'
  }
})
