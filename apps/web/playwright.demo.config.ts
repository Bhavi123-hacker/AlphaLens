import { defineConfig, devices } from '@playwright/test'
const baseURL = process.env.ALPHALENS_DEMO_BASE_URL ?? 'http://127.0.0.1:8031'
if (!['127.0.0.1','localhost'].includes(new URL(baseURL).hostname)) throw new Error('Demo verification must remain loopback-only')
export default defineConfig({ testDir: './tests/browser', testMatch: 'public-demo.spec.ts', timeout: 60_000, expect: { timeout: 15_000 }, workers: 1, retries: 0,
  reporter: [['list'], ['json', { outputFile: process.env.ALPHALENS_DEMO_REPORT ?? 'test-results/demo-report.json' }]],
  outputDir: process.env.ALPHALENS_DEMO_BROWSER_OUTPUT ?? 'test-results/demo',
  webServer: { command: 'npm run preview:demo', url: baseURL, reuseExistingServer: !process.env.CI, timeout: 30_000 },
  use: { ...devices['Desktop Chrome'], channel: 'chromium', baseURL, viewport: { width: 1440, height: 1050 }, screenshot: 'only-on-failure', trace: 'retain-on-failure' },
})
