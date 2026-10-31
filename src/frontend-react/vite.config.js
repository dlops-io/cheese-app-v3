import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// The browser always calls /api/... on its own origin. In dev, Vite forwards that to the API
// container by name, on cheese-app-network; in production, nginx does (nginx.conf.template).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true, // listen on all interfaces, so the container's published port reaches it
    port: 5173,
    strictPort: true,
    proxy: { '/api': process.env.API_URL || 'http://cheese-app-api-service:9000' },
  },
})
