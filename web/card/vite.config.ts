import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/card/',
  build: {
    outDir: '../../services/analyst/static/iframe',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
  },
})
