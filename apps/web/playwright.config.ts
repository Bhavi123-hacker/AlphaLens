import { defineConfig, devices } from '@playwright/test'
export default defineConfig({
  globalSetup: process.env.ALPHALENS_BROWSER_CREDENTIAL_FILE ? './tests/browser/auth-setup.ts' : undefined,
  testDir: './tests/browser', timeout: 90_000, expect: { timeout: 30_000 }, fullyParallel: false, workers: 1,
  testIgnore: 'public-demo.spec.ts',
  retries: 0, reporter: [['list'], ['json', { outputFile: process.env.ALPHALENS_BROWSER_REPORT ?? 'test-results/report.json' }]],
  outputDir: process.env.ALPHALENS_BROWSER_OUTPUT_DIR ?? 'test-results',
  use: { storageState: process.env.ALPHALENS_BROWSER_STATE_FILE, baseURL: process.env.ALPHALENS_BROWSER_BASE_URL ?? 'http://127.0.0.1:5173', ...devices['Desktop Chrome'], channel: 'chromium', launchOptions: { args: process.env.ALPHALENS_BROWSER_LOW_MEMORY === '1' ? ['--renderer-process-limit=2', '--js-flags=--max-old-space-size=256'] : [] }, viewport: { width: 1440, height: 1050 }, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
})
