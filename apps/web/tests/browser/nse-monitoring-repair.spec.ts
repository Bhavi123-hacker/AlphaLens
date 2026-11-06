import { expect, test } from '@playwright/test'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'

// Compiled authenticated isolated server, genuine saved data; provider blocked server-side.
test.use({ trace: 'off', screenshot: 'off', video: 'off' })
test('read-only collection and matured-only evaluation match actual saved backend evidence', async ({ page }) => {
  const paths: string[] = []
  page.on('request', request => paths.push(new URL(request.url()).pathname))
  const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/nse-market/research')
  await page.goto('/nse-market')
  const reply = await response
  expect(reply.status()).toBe(200)
  const data = (await reply.json()).data
  expect(data.coverage.latest_session_coverage.verified_securities).toBe(499)
  expect(data.coverage.latest_session_coverage.pending_securities).toBe(1)
  expect(data.scores.observation_session).toBe('2026-10-19')
  expect(data.operations.shared_provider_usage.recorded_get_attempts).toBe(1004)
  expect(data.operations.reservations.reserved_get_attempts).toBe(1200)
  await expect(page.getByTestId('collection-coverage-summary')).toContainText('499 verified, 1 pending, 0 failed')
  await expect(page.getByTestId('forecast-publication-status')).toContainText('302 scored securities')
  await expect(page.getByTestId('expanded-model-score')).toHaveCount(5)
  const loaded = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/nse-market/prospective-evaluation')
  await page.getByText('Inspect point-in-time prospective evidence').click()
  const evaluation = await loaded
  expect(evaluation.status()).toBe(200)
  const actual = (await evaluation.json()).data
  expect(actual.raw_forecast_records).toBe(633)
  expect(actual.matured_outcomes).toBe(0)
  expect(actual.metrics.score.accuracy).toBeNull()
  expect(actual.provider_requests).toBe(0)
  await expect(page.getByText('Frozen V2 forecast records').locator('..')).toContainText('633')
  const table = page.getByRole('table', { name: 'Prospective model and baseline evaluation' })
  await expect(table).toContainText('Unavailable')
  await expect(table).not.toContainText('0.00%')
  expect(paths.some(path => /upstox-private\/(snapshot|watchlist|reference)/.test(path))).toBe(false)
  const accessibility = await new AxeBuilder({page}).include('#daily-research').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()
  expect(accessibility.violations).toEqual([])
  if (process.env.ALPHALENS_BROWSER_OUTPUT_DIR) {
    await page.getByRole('heading', {name:'Daily updates and prospective validation',exact:true}).scrollIntoViewIfNeeded()
    await page.screenshot({path:join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR,'operations-desktop.private.png')})
    await page.setViewportSize({width:390,height:844})
    await expect(page.getByTestId('collection-coverage-summary')).toBeVisible()
    await page.screenshot({path:join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR,'operations-mobile.private.png')})
  }
})

test('authenticated historical cutoff excludes later forecasts and rejects future or naive cutoffs', async ({ request, playwright }) => {
  const past = await request.get('/api/v1/nse-market/prospective-evaluation?as_of=2026-10-20T15%3A00%3A00Z')
  expect(past.status()).toBe(200)
  const saved = (await past.json()).data
  expect(saved.raw_forecast_records).toBe(331)
  expect(saved.unique_decisions).toBe(300)
  expect(saved.future_forecast_records_ignored).toBe(302)
  expect(saved.metrics.score.accuracy).toBeNull()
  expect((await request.get('/api/v1/nse-market/prospective-evaluation?as_of=2100-01-01T00%3A00%3A00Z')).status()).toBe(422)
  expect((await request.get('/api/v1/nse-market/prospective-evaluation?as_of=2026-10-20T15%3A00%3A00')).status()).toBe(422)
  const anonymous = await playwright.request.newContext({ storageState: { cookies: [], origins: [] } })
  try {
    expect((await anonymous.get(process.env.ALPHALENS_BROWSER_BASE_URL + '/api/v1/nse-market/prospective-evaluation')).status()).toBe(401)
  } finally { await anonymous.dispose() }
})
