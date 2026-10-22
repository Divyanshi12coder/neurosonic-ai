import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_PROXY || 'http://localhost:8000'
  return {
    plugins: [react()],
    server: { port: 5173, proxy: { '/api': { target, changeOrigin: true } } },
    preview: { port: 5173, proxy: { '/api': { target, changeOrigin: true } } },
    build: {
      rollupOptions: {
        output: { manualChunks: { vendor: ['react', 'react-dom', 'react-router-dom'], motion: ['framer-motion'], charts: ['recharts'] } },
      },
    },
  }
})
