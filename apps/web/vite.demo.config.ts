import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'
import { readFileSync } from 'node:fs'

const sourceCommit = process.env.GITHUB_SHA ?? process.env.RENDER_GIT_COMMIT ?? 'local'
if (sourceCommit !== 'local' && !/^[a-f0-9]{40}$/.test(sourceCommit)) throw new Error('Invalid synthetic release source identity')

// A separate static entry. No API proxy, private app imports, secret env or deployment.
export default defineConfig({
  root: resolve('demo'), base: './', plugins: [react(), { name: 'retain-demo-licenses', generateBundle() { for (const [fileName, path] of [['LICENSE.txt', 'demo/LICENSE.txt'], ['third-party-notices.txt', 'public/third-party-notices.txt']]) this.emitFile({ type: 'asset', fileName, source: readFileSync(path, 'utf8') }); this.emitFile({ type: 'asset', fileName: 'release.json', source: JSON.stringify({ schema_version: 1, source_commit: sourceCommit, data_mode: 'SYNTHETIC_ONLY', backend: false, provider_requests: false }) + '\n' }) } }], envDir: resolve('demo'), envPrefix: 'DEMO_PUBLIC_',
  publicDir: false, server: { host: '127.0.0.1', port: 8031, strictPort: true },
  preview: { host: '127.0.0.1', port: 8031, strictPort: true },
  build: { outDir: process.env.ALPHALENS_DEMO_OUTPUT_DIR ?? resolve('demo-dist'), emptyOutDir: false, sourcemap: false,
    rollupOptions: { output: { manualChunks: id => /node_modules\/(echarts|zrender)/.test(id.replaceAll('\\', '/')) ? 'charts' : undefined } } },
})
