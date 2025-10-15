import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/extract': 'http://127.0.0.1:5000',
      '/translate': 'http://127.0.0.1:5000'
    }
  }
})
