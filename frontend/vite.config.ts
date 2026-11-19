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
    // El alta de oportunidades va al servicio "automatizador" y tiene que ir
    // antes que '/api/v1' (gana la primera clave que coincide).
    proxy: {
      '/api/v1/alta-oportunidades': 'http://127.0.0.1:8001',
      '/api/v1': 'http://127.0.0.1:8000',
    },
  },
})
