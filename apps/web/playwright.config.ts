import { defineConfig, devices } from '@playwright/test'
export default defineConfig({
  testDir: './tests/browser', timeout: 90_000, expect: { timeout: 30_000 }, fullyParallel: false, workers: 1,
  retries: 0, reporter: [['list'], ['json', { outputFile: process.env.ALPHALENS_BROWSER_REPORT ?? 'test-results/report.json' }]],
  outputDir: process.env.ALPHALENS_BROWSER_OUTPUT_DIR ?? 'test-results',
  use: { baseURL: 'http://127.0.0.1:5173', ...devices['Desktop Chrome'], channel: 'chromium', viewport: { width: 1440, height: 1050 }, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
})
