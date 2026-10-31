import { expect, test } from '@playwright/test'

// Opt-in private acceptance over genuine saved observations and real backend.
// No market response stubbing, provider acquisition, record writes or model fits.
test('saved NSE candles to model Top-N, history and pending forward evaluation', async ({ page, baseURL }) => {
  test.skip(process.env.ALPHALENS_COMPLETION_SAVED_BROWSER !== '1', 'Requires isolated private saved-data deployment')
  test.setTimeout(360_000)
  const forbidden: string[] = []
  await page.route('**/*', async route => {
    const url = new URL(route.request().url())
    if (url.origin !== new URL(baseURL!).origin || url.searchParams.get('refresh') === 'true'
      || /upstox-private/.test(url.pathname)) {
      forbidden.push(url.pathname); return route.abort()
    }
    return route.continue()
  })
  await page.goto('/nse-market')
  const healthResponse = await page.request.get('/api/v1/nse-market/collection-health')
  expect(healthResponse.status()).toBe(200)
  const health = (await healthResponse.json()).data as { accepted_securities: number; configured_securities: number; local_alerts: { total: number }; operational_readiness: { forecasts: { matured_outcomes: number; measurement_status: string }; collector_runtime: { cutover_status: string } } }
  await expect(page.getByRole('heading', { name: 'Collection monitoring and local alerts' })).toBeVisible()
  const acceptedStat = page.locator('.stat').filter({ has: page.getByText('Accepted / configured securities', { exact: true }) })
  await expect(acceptedStat.getByText(`${health.accepted_securities.toLocaleString()} / ${health.configured_securities.toLocaleString()}`, { exact: true })).toBeVisible()
  if (health.local_alerts.total > 0) await expect(page.getByRole('table', { name: 'Local collection alerts' })).toBeVisible()
  const acceptance = page.getByRole('region', { name: 'Unified operational readiness' })
  await expect(acceptance).toBeVisible()
  await expect(acceptance).toContainText(health.operational_readiness.collector_runtime.cutover_status)
  if (health.operational_readiness.forecasts.matured_outcomes === 0) {
    expect(health.operational_readiness.forecasts.measurement_status).toBe('NOT_YET_MEASURABLE')
    await expect(acceptance).toContainText('NOT_YET_MEASURABLE')
  }
  const market = page.getByRole('table', { name: 'Saved NSE market movements' })
  await expect(market).toBeVisible({ timeout: 120_000 })
  await page.getByLabel('Search saved NSE prices').fill('RELIANCE')
  await expect(market).toContainText('RELIANCE')
  const reliance = market.getByRole('row').filter({ has: page.getByRole('link', { name: 'RELIANCE', exact: true }) })
  await expect(reliance).toHaveCount(1)
  await expect(reliance.getByRole('cell').nth(1)).not.toHaveText('Unavailable')
  const previewResponse = page.waitForResponse(reply => new URL(reply.url()).pathname === '/api/v1/nse-market/saved-history')
  await reliance.getByRole('button', { name: 'Preview RELIANCE saved chart' }).click()
  expect((await previewResponse).status()).toBe(200)
  const workspace = page.getByRole('complementary', { name: 'Saved chart workspace' })
  await expect(workspace.getByRole('img', { name: 'Saved RELIANCE daily price and volume' })).toBeVisible()
  await expect(workspace).toContainText('NOT A LIVE QUOTE')
  await workspace.getByRole('button', { name: 'Line', exact: true }).click()
  await expect(workspace.getByRole('button', { name: 'Line', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  await page.setViewportSize({ width: 1600, height: 1000 })
  await workspace.getByRole('button', { name: 'Close preview' }).click()
  await expect(workspace.getByText('Your market research workspace')).toBeVisible()
  const ranks = page.getByRole('table', { name: 'Expanded genuine model rankings' })
  await expect(ranks).toBeVisible({ timeout: 120_000 })
  for (const n of [5, 10, 20]) {
    await page.getByLabel('Expanded research list size').selectOption(String(n))
    await expect(ranks.locator('tbody tr')).toHaveCount(n)
  }
  await ranks.getByRole('button', { name: 'Why this security qualifies, risks and scenarios' }).first().click()
  await expect(page.getByRole('heading', { name: 'Why it qualified' })).toBeVisible()
  await expect(page.getByText(/weight one is an unvalidated engineering assumption/)).toBeVisible()
  await page.keyboard.press('Escape')
  const evaluationReply = page.waitForResponse(reply => new URL(reply.url()).pathname === '/api/v1/nse-market/prospective-evaluation')
  await page.getByText('Inspect point-in-time prospective evidence', { exact: true }).click()
  expect((await evaluationReply).status()).toBe(200)
  await expect(page.getByText('PROSPECTIVE_EVALUATION_PENDING', { exact: true })).toBeVisible()
  await expect(page.getByRole('table', { name: 'Prospective model and baseline evaluation' })).toContainText('Unavailable')
  await ranks.locator('tbody tr').first().getByRole('link').first().click()
  await expect(page.getByRole('heading', { name: 'Saved private OHLCV chart', exact: true })).toBeVisible()
  await expect(page.getByRole('img', { name: /Saved .* daily price and volume/ })).toBeVisible()
  await page.getByText('Inspect experimental predictions, baselines and observed historical outcomes', { exact: true }).click()
  await expect(page.getByText('Recorded prospective forecasts and matured outcomes', { exact: true })).toBeVisible({ timeout: 120_000 })
  await page.getByText('Recorded prospective forecasts and matured outcomes', { exact: true }).click()
  await expect(page.getByRole('table', { name: 'Saved stock forecast and outcome history' })).toBeVisible()
  await expect(page.getByRole('table', { name: 'Saved stock forecast and outcome history' })).toContainText('Pending qualified future evidence')
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  expect(forbidden).toEqual([])
})

test('complete saved master discovery opens missing-price and insufficient-history equities', async ({ page, baseURL }) => {
  test.skip(process.env.ALPHALENS_COMPLETION_SAVED_BROWSER !== '1', 'Requires isolated private saved-data deployment')
  test.setTimeout(360_000)
  const forbidden: string[] = []
  await page.route('**/*', async route => {
    const url = new URL(route.request().url())
    if (url.origin !== new URL(baseURL!).origin || url.searchParams.get('refresh') === 'true'
      || /upstox-private/.test(url.pathname)) {
      forbidden.push(url.pathname); return route.abort()
    }
    return route.continue()
  })
  await page.goto('/nse-market')
  const coverageResponse = await page.request.get('/api/v1/nse-market/universe-coverage')
  expect(coverageResponse.status()).toBe(200)
  const coverage = await coverageResponse.json() as { data: { identity: { state: string } } }
  await expect(page.getByRole('heading', { name: 'Measured NSE universe coverage' })).toBeVisible()
  await expect(page.getByText(/Latest-session predictions/, { exact: true })).toBeVisible()
  await page.getByLabel('Equity exchange').selectOption('NSE')
  await page.getByLabel('Search current NSE / BSE common equities').fill('AAKAAR')
  const identities = page.getByRole('table', { name: 'Verified dated NSE / BSE universe' })
  await expect(identities.getByRole('link', { name: 'AAKAAR', exact: true })).toBeVisible()
  if (coverage.data.identity.state === 'STALE') {
    await expect(page.getByText(/verified master is dated/)).toBeVisible()
  } else {
    expect(coverage.data.identity.state).toBe('FRESH')
    await expect(page.getByText(/verified master is dated/)).toHaveCount(0)
  }
  await identities.getByRole('link', { name: 'AAKAAR', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'No saved candles for this identity' })).toBeVisible()
  await expect(page.getByText(/Exact saved identity: NSE_EQ\|INE1GYP01013/)).toBeVisible()
  await expect(page.getByText(/ML evidence: No compatible saved prediction/i)).toBeVisible()
  // HINDADH has 47 retained observations at this release cutoff and lacks a
  // complete lookback. AGOL now lacks the latest session after the partial run.
  await page.goto('/stocks/' + encodeURIComponent('upstox:NSE_EQ|INE074C01013'))
  await expect(page.getByRole('img', { name: 'Saved HINDADH daily price and volume' })).toBeVisible()
  await expect(page.getByText(/ML evidence:.*Missing lookback slot/i)).toBeVisible()
  await page.goto('/stocks/' + encodeURIComponent('upstox:NSE_EQ|INE674K07150'))
  await expect(page.getByRole('heading', { name: 'No saved candles for this identity' })).toBeVisible()
  await expect(page.getByText(/Unsupported instrument/i)).toBeVisible()
  expect(forbidden).toEqual([])
})
