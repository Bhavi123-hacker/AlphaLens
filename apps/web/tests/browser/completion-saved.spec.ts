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
  const market = page.getByRole('table', { name: 'Saved NSE market movements' })
  await expect(market).toBeVisible({ timeout: 120_000 })
  await page.getByLabel('Search saved NSE prices').fill('RELIANCE')
  await expect(market).toContainText('RELIANCE')
  const reliance = market.getByRole('row').filter({ has: page.getByRole('link', { name: 'RELIANCE', exact: true }) })
  await expect(reliance).toHaveCount(1)
  await expect(reliance.getByRole('cell').nth(1)).not.toHaveText('Unavailable')
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
  await page.getByText('Inspect point-in-time prospective evidence', { exact: true }).click()
  await expect(page.getByText('PROSPECTIVE_EVALUATION_PENDING', { exact: true })).toBeVisible()
  await expect(page.getByRole('table', { name: 'Prospective model and baseline evaluation' })).toContainText('Unavailable')
  await ranks.locator('tbody tr').first().getByRole('link').first().click()
  await expect(page.getByRole('heading', { name: 'Saved private OHLCV chart', exact: true })).toBeVisible()
  await expect(page.getByRole('img', { name: /Saved .* daily price and volume/ })).toBeVisible()
  await page.getByText('Inspect experimental predictions, baselines and observed historical outcomes', { exact: true }).click()
  await expect(page.getByText('Recorded prospective forecasts and matured outcomes', { exact: true })).toBeVisible({ timeout: 120_000 })
  await page.getByText('Recorded prospective forecasts and matured outcomes', { exact: true }).click()
  await expect(page.locator('pre').filter({ hasText: 'forecast_id' }).first()).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  expect(forbidden).toEqual([])
})

test('complete dated master discovery opens missing-price and insufficient-history equities', async ({ page, baseURL }) => {
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
  await expect(page.getByRole('heading', { name: 'Measured NSE universe coverage' })).toBeVisible()
  await expect(page.getByText(/Latest-session predictions/, { exact: true })).toBeVisible()
  await page.getByLabel('Search current NSE common equities').fill('AAKAAR')
  const identities = page.getByRole('table', { name: 'Verified current NSE universe' })
  await expect(identities.getByRole('link', { name: 'AAKAAR', exact: true })).toBeVisible()
  await expect(page.getByText(/verified master is dated/)).toBeVisible()
  await identities.getByRole('link', { name: 'AAKAAR', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'No saved candles for this identity' })).toBeVisible()
  await expect(page.getByText(/Exact saved identity: NSE_EQ\|INE1GYP01013/)).toBeVisible()
  await expect(page.getByText(/ML evidence: No compatible saved prediction/i)).toBeVisible()
  await page.goto('/stocks/' + encodeURIComponent('upstox:NSE_EQ|INE05FR01029'))
  await expect(page.getByRole('img', { name: 'Saved AGOL daily price and volume' })).toBeVisible()
  await expect(page.getByText(/ML evidence:.*Missing lookback slot/i)).toBeVisible()
  await page.goto('/stocks/' + encodeURIComponent('upstox:NSE_EQ|INE674K07150'))
  await expect(page.getByRole('heading', { name: 'No saved candles for this identity' })).toBeVisible()
  await expect(page.getByText(/Unsupported instrument/i)).toBeVisible()
  expect(forbidden).toEqual([])
})
