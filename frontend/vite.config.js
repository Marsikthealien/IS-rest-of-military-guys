import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const api = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, 'src') } },
  server: {
    // усі API-шляхи проксуються на бекенд; /api-префікс знімається
    proxy: { '/api': { target: api, rewrite: (p) => p.replace(/^\/api/, '') } },
  },
})
