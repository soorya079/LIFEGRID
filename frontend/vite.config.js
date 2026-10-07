import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  base: '/LIFEGRID/',
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
  },
})