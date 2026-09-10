import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './', // CRITICAL: Permite cargar el dist desde el sistema de archivos (file://) en PyWebView
})
