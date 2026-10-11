import { chromium } from '@playwright/test'
import { readFile, writeFile } from 'node:fs/promises'

const credentials = JSON.parse(await readFile(process.env.ALPHALENS_BROWSER_CREDENTIAL_FILE, 'utf8'))
const browser = await chromium.launch({ channel: 'chromium' })
const result = []
try {
  for (const route of ['/market', '/backtests']) {
    const context = await browser.newContext()
    const response = await context.request.post('http://127.0.0.1:5173/api/v1/auth/login', {
      headers: { Origin: 'http://127.0.0.1:5173', 'X-AlphaLens-Local': 'p21' }, data: credentials,
    })
    if (response.status() !== 200) throw new Error('TEST_ONLY_LOGIN_FAILED')
    const page = await context.newPage()
    const started = performance.now()
    await page.goto(`http://127.0.0.1:5173${route}`)
    await page.getByRole('heading', { name: route === '/market' ? 'Market explorer' : 'Backtesting evidence', exact: true }).waitFor()
    await page.getByRole('cell').first().waitFor()
    const readyMs = performance.now() - started
    const resources = await page.evaluate(() => performance.getEntriesByType('resource').filter(r => r.name.endsWith('.js')).map(r => ({ name: r.name.split('/').at(-1), decodedBytes: r.decodedBodySize, transferBytes: r.transferSize })))
    result.push({ route, readyMs, jsDecodedBytes: resources.reduce((n, r) => n + r.decodedBytes, 0), chartsRequested: resources.some(r => /^charts-/.test(r.name)), resources })
    await context.close()
  }
  await writeFile(process.env.ALPHALENS_BENCHMARK_OUTPUT, JSON.stringify({ version: 'p23.browser.v1', classification: 'REAL_RESEARCH_READS_TEST_ONLY_AUTH', measuredAt: new Date().toISOString(), coldBrowserCache: true, limitations: 'Two first-load samples; timing is descriptive, not statistical. OS/cache/background load not controlled.', result }, null, 2), { flag: 'wx' })
} finally { await browser.close() }
