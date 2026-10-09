import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'node:path'

const target = process.env.ALPHALENS_API_PROXY_TARGET ?? 'http://127.0.0.1:8017'
const address = new URL(target)
if (address.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(address.hostname)
  || address.username || address.password || address.pathname !== '/' || address.search || address.hash) {
  throw new Error('The API proxy must target an explicit unauthenticated loopback HTTP origin')
}
export default defineConfig({
  plugins: [react(), tailwindcss()],
  cacheDir: process.env.ALPHALENS_WEB_CACHE_DIR ?? 'node_modules/.vite',
  server: { host: '127.0.0.1', port: 5173, strictPort: true,
    cors: { origin: ['http://127.0.0.1:5173', 'http://localhost:5173'] },
    proxy: { '/api': { target, changeOrigin: false } },
    fs: { strict: true, allow: [resolve('.'), resolve('node_modules')],
      deny: ['.env', '.env.*', '**/*.pem', '**/*.key', '**/*.parquet', '**/*.skops', '**/*.sqlite'] } },
  preview: { host: '127.0.0.1', port: 5173, strictPort: true,
    cors: { origin: ['http://127.0.0.1:5173', 'http://localhost:5173'] },
    proxy: { '/api': { target, changeOrigin: false } } },
  build: { outDir: process.env.ALPHALENS_WEB_OUTPUT_DIR ?? 'dist', emptyOutDir: false,
    rollupOptions: { output: { manualChunks: (id) => {
      const name = id.replaceAll('\\', '/')
      if (name.includes('/node_modules/echarts/') || name.includes('/node_modules/zrender/')) return 'charts'
      if (name.includes('/node_modules/@tanstack/')) return 'query'
      if (/\/node_modules\/(react|react-dom|react-router|react-router-dom)\//.test(name)) return 'react'
    } } } },
  test: { environment: 'jsdom', setupFiles: ['tests/setup.ts'], include: ['tests/**/*.test.{ts,tsx}'] },
})
