import { test, expect, type Page } from '@playwright/test'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import AxeBuilder from '@axe-core/playwright'
import { currency, localTime } from '../../src/lib/format'
import { signIn } from './auth-setup'
import type { ProviderInstrument, ProviderSnapshot } from '../../src/api/terminal'

// Actual compiled private app and actual provider; never intercept market responses.
// No trace/video/raw provider body or price-bearing screenshot is retained.
process.env.PLAYWRIGHT_NO_COPY_PROMPT = '1'
test.use({ trace: 'off', screenshot: 'off', video: 'off' })
test.beforeEach(async ({ page }) => { await page.context().clearCookies(); await page.goto('/login'); await signIn(page) })
const identities: ProviderInstrument[] = []
async function find(page: Page, name: string) {
  const response = await page.request.get(`/api/v1/providers/upstox-private/instruments?q=${name}`)
  expect(response.status()).toBe(200)
  const data = (await response.json()).data
  const matches = data.instruments.filter((i: ProviderInstrument) => i.symbol === name)
  expect(matches).toHaveLength(1)
  expect(matches[0].provider_key).toBe('NSE_EQ|' + matches[0].isin)
  return matches[0] as ProviderInstrument
}
async function select(page: Page, name: string) {
  await page.getByLabel('Search current NSE master', { exact: true }).fill(name)
  await page.getByRole('button', { name: 'Find NSE equity', exact: true }).click()
  await page.getByRole('button').filter({ has: page.locator('strong', { hasText: new RegExp('^' + name + '$') }) }).click()
}

test('genuine three-equity mapping, primary quotes/candles, clock and currency equality', async ({ page }) => {
  test.setTimeout(180_000)
  await page.addInitScript(() => {
    const captured = window as unknown as { terminalTooltipSeen: boolean; terminalLongDecimals: boolean }
    captured.terminalTooltipSeen = false; captured.terminalLongDecimals = false
    const original = CanvasRenderingContext2D.prototype.fillText
    CanvasRenderingContext2D.prototype.fillText = function (text, x, y, maxWidth) {
      captured.terminalTooltipSeen ||= /^OHLC\s+O\s/.test(text)
      captured.terminalLongDecimals ||= /\d\.\d{7,}/.test(text)
      if (maxWidth === undefined) original.call(this, text, x, y)
      else original.call(this, text, x, y, maxWidth)
    }
  })
  for (const name of ['BAJFINANCE', 'RELIANCE', 'TCS']) identities.push(await find(page, name))
  const response = await page.request.get('/api/v1/providers/upstox-private/snapshot?instrument_keys=' + encodeURIComponent(identities.map(i => i.provider_key).join(',')))
  expect(response.status()).toBe(200); expect(response.headers()['cache-control']).toContain('no-store')
  const cohort = (await response.json()).data
  expect(cohort.full_nse_coverage).toBe(false); expect(cohort.retained).toBe(false)
  expect(cohort.api_calls_this_request).toBeLessThanOrEqual(6)
  const receipt: object[] = []
  for (const identity of identities) {
    await page.goto('/analysis'); await select(page, identity.symbol)
    await expect(page.getByRole('button', { name: 'Upstox · latest provider observations', exact: true })).toHaveAttribute('aria-pressed', 'true')
    const reply = page.waitForResponse(r => r.url().includes('/upstox-private/snapshot?'))
    await page.getByRole('button', { name: 'Load Upstox observations', exact: true }).click()
    const result = (await (await reply).json()).data
    expect(result.api_calls_this_request).toBe(0)
    const data = result.items[0] as ProviderSnapshot
    expect(data.instrument_key).toBe(identity.provider_key); expect(data.rows.length).toBeGreaterThan(200)
    await expect(page.getByRole('img', { name: `Upstox ${identity.symbol} daily OHLCV ending ${data.latest_session}` })).toBeVisible()
    await page.locator('.terminal-chart-main .chart').hover({ position: { x: 200, y: 140 } })
    await expect.poll(() => page.evaluate(() => (window as unknown as { terminalTooltipSeen: boolean }).terminalTooltipSeen)).toBe(true)
    expect(await page.evaluate(() => (window as unknown as { terminalLongDecimals: boolean }).terminalLongDecimals)).toBe(false)
    const expected = currency(data.quote.state === 'VALIDATED_SNAPSHOT' ? data.quote.ltp : data.latest_close)
    // Boolean assertion keeps real quote values out of failure reports.
    expect(await page.locator('.headline-price').innerText() === '₹' + expected).toBe(true)
    if (data.quote.state === 'VALIDATED_SNAPSHOT') {
      expect(Date.parse(data.quote.snapshot_at!) <= Date.parse(data.quote.clock.local_received_at)).toBe(true)
      await expect(page.getByText('Last traded price · quote snapshot', { exact: true })).toBeVisible()
      await expect(page.getByText(localTime(data.quote.last_trade_at), { exact: true })).toBeVisible()
    } else await expect(page.getByText(/Current quote:/)).toBeVisible()
    await page.getByRole('group', { name: 'Provider date range' }).getByRole('button', { name: '5Y', exact: true }).click()
    await page.getByRole('group', { name: 'Provider chart type' }).getByRole('button', { name: 'Line', exact: true }).click()
    for (const name of ['EMA 12', 'RSI', 'MACD', 'BB upper']) {
      await expect(page.getByRole('button', { name, exact: true })).toBeEnabled()
      await page.getByRole('button', { name, exact: true }).click()
    }
    await page.getByRole('button', { name: 'Expand chart', exact: true }).click()
    await expect(page.locator('.chart-expanded')).toBeVisible(); await page.keyboard.press('Escape')
    await expect(page.locator('.chart-expanded')).toHaveCount(0)
    receipt.push({ symbol: data.symbol, isin: data.identity.isin, instrument_key: data.instrument_key, archive_identity: data.identity.canonical_security_id, latest_daily_session: data.latest_session, quote_state: data.quote.state, quote_snapshot_at: data.quote.snapshot_at, reported_snapshot_at: data.quote.reported_snapshot_at, last_trade_at: data.quote.last_trade_at, current_session_status: data.current_session_status, clock: data.quote.clock, ui_price_equals_same_source_snapshot: true, provider_price_values_retained: false })
  }
  writeFileSync(join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR!, 'sanitized-live-receipt.json'), JSON.stringify(receipt, null, 2))
})

test('canonical archive switch stays independent and exposes actual age', async ({ page }) => {
  const identity = identities[0] || await find(page, 'BAJFINANCE')
  expect(Boolean(identity.canonical_security_id)).toBe(true)
  await page.goto('/stocks/' + encodeURIComponent(identity.canonical_security_id!))
  await expect(page.getByRole('button', { name: 'Upstox · latest provider observations', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await page.getByRole('button', { name: /^AlphaLens Historical Archive ·/ }).click()
  await expect(page.getByRole('img', { name: /^Historical OHLCV for BAJFINANCE/ })).toBeVisible()
  await expect(page.getByText(/Frozen historical archive through .* calendar days old/)).toBeVisible()
  await expect(page.getByText('Last archive close in selected range', { exact: true })).toBeVisible()
  await page.screenshot({ path: join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR!, 'archive-desktop.png'), fullPage: false })
})

test('selected watchlist heatmap, screener and provider comparison work without universe claims', async ({ page }) => {
  await page.goto('/screener')
  for (const name of ['BAJFINANCE', 'RELIANCE', 'TCS']) await select(page, name)
  await page.getByRole('button', { name: 'Load selected watchlist', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Selected provider watchlist heatmap' })).toBeVisible()
  await expect(page.getByText(/3 queried identities · selected watchlist/)).toBeVisible()
  await page.getByLabel('Private watchlist minimum volume').fill('999999999999')
  await expect(page.getByText(/^0 private watchlist matches/)).toBeVisible()
  await page.getByLabel('Private watchlist minimum volume').fill('')
  await expect(page.getByText(/^3 private watchlist matches/)).toBeVisible()
  await page.goto('/compare')
  for (const name of ['BAJFINANCE', 'RELIANCE']) await select(page, name)
  await page.getByRole('button', { name: 'Load selected watchlist', exact: true }).click()
  await expect(page.getByRole('img', { name: 'Selected Upstox daily close comparison' })).toBeVisible()
})

test('desktop/laptop/mobile source hierarchy, readable text and compiled chart resizing', async ({ page }) => {
  const identity = identities[0] || await find(page, 'BAJFINANCE')
  await page.goto('/stocks/' + encodeURIComponent(identity.canonical_security_id || 'upstox:' + identity.provider_key))
  await page.getByRole('button', { name: 'Load Upstox observations', exact: true }).click()
  await expect(page.locator('.headline-price')).toBeVisible()
  for (const width of [1600, 1366, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    expect(await page.locator('.source-switch button').first().evaluate(e => parseFloat(getComputedStyle(e).fontSize))).toBeGreaterThanOrEqual(13)
    await page.screenshot({ path: join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR!, `provider-${width}-redacted.png`), fullPage: false, maskColor: '#24364a', mask: [page.locator('.headline-price'), page.locator('.stock-quote-header > div:first-child > span:last-child'), page.locator('.chart'), page.locator('.stock-insights')] })
  }
})

test('research automation remains separately blocked and home diagnostics collapsed', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Your market workspace', exact: true })).toBeVisible()
  expect(await page.locator('.automation-diagnostics').getAttribute('open')).toBeNull()
  await page.getByText('Research automation diagnostics · retained ingestion and inference restrictions', { exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Research automation', exact: true })).toBeVisible()
  await expect(page.getByText('Daily activation blocked', { exact: true })).toBeVisible()
  expect((await page.request.get('/api/v1/daily/predictions')).status()).toBe(503)
  const a11y = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(a11y.violations.map(v => ({ id: v.id, impact: v.impact }))).toEqual([])
})

test('compiled application authentication and logout protect generic provider APIs', async ({ page }) => {
  await page.context().clearCookies(); await page.goto('/login'); await signIn(page)
  await page.goto('/settings'); await page.getByRole('button', { name: 'Log out', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
  expect((await page.request.get('/api/v1/providers/upstox-private/instruments?q=BAJFINANCE')).status()).toBe(401)
  await signIn(page)
  expect((await page.request.get('/api/v1/providers/upstox-private/instruments?q=BAJFINANCE')).status()).toBe(200)
})
