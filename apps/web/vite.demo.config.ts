import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'
import { readFileSync } from 'node:fs'

// A separate static entry. No API proxy, private app imports, secret env or deployment.
export default defineConfig({
  root: resolve('demo'), base: './', plugins: [react(), { name: 'retain-demo-licenses', generateBundle() { for (const [fileName, path] of [['LICENSE.txt', 'demo/LICENSE.txt'], ['third-party-notices.txt', 'public/third-party-notices.txt']]) this.emitFile({ type: 'asset', fileName, source: readFileSync(path, 'utf8') }) } }], envDir: resolve('demo'), envPrefix: 'DEMO_PUBLIC_',
  publicDir: false, server: { host: '127.0.0.1', port: 8031, strictPort: true },
  preview: { host: '127.0.0.1', port: 8031, strictPort: true },
  build: { outDir: process.env.ALPHALENS_DEMO_OUTPUT_DIR ?? resolve('demo-dist'), emptyOutDir: false, sourcemap: false,
    rollupOptions: { output: { manualChunks: id => /node_modules\/(echarts|zrender)/.test(id.replaceAll('\\', '/')) ? 'charts' : undefined } } },
})
