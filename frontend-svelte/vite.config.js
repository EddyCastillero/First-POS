import { svelte } from '@sveltejs/vite-plugin-svelte'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    svelte(),
    tailwindcss()
  ],
  server: {
    port: 5173,
    proxy: {
      '/pos': 'http://localhost:8090',
      '/inventory': 'http://localhost:8090'
    }
  }
})

