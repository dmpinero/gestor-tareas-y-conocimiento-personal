import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // El cliente API llama a rutas relativas ('/api/v1/...' por defecto); en
    // desarrollo se reenvían al backend local. En producción cumple el mismo
    // papel el proxy de Nginx (ver nginx.conf).
    proxy: {
      '/api/v1': 'http://127.0.0.1:8000',
    },
  },
})
