import { test, expect } from '@playwright/test'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { terminalSchema } from '../../src/api/terminal'
import { currency } from '../../src/lib/format'

// Actual private source; no response interception or price-bearing artifacts.
test.use({ trace: 'off', screenshot: 'off', video: 'off' })
test('genuine selected-stock EOD chart and truthful current-quote state match the compiled terminal', async ({ page }) => {
  test.setTimeout(150_000)
  const master = (await (await page.request.get('/api/v1/providers/upstox-private/instruments?q=RELIANCE')).json()).data
  const identity = master.instruments.find((row: { symbol: string }) => row.symbol === 'RELIANCE')
  expect(identity.provider_key).toBe('NSE_EQ|' + identity.isin)
  await page.goto('/stocks/' + encodeURIComponent('upstox:' + identity.provider_key))
  const pending = page.waitForResponse(reply => reply.url().includes('/upstox-private/snapshot?'))
  await page.getByRole('button', { name: 'Load Upstox observations', exact: true }).click()
  const response = await pending
  expect(response.status()).toBe(200)
  const source = terminalSchema.parse((await response.json()).data)
  const item = source.items[0]
  expect(item.instrument_key).toBe(identity.provider_key)
  expect(item.retained).toBe(false)
  expect(item.rows.length).toBeGreaterThan(200)
  expect(item.rows.at(-1)?.session).toBe(item.latest_session)
  expect(item.latest_session! >= '2026-10-16').toBe(true)
  expect(source.api_calls_this_request).toBeLessThanOrEqual(7)
  await expect(page.getByRole('img', { name: `Upstox RELIANCE daily OHLCV ending ${item.latest_session}` })).toBeVisible()
  const displayed = item.quote.state === 'VALIDATED_SNAPSHOT' ? item.quote : item.indicative_quote
  if (displayed) {
    expect(item.delayed_provider_display?.elapsed_since_network_receipt_seconds).toBeGreaterThanOrEqual(1)
    expect(item.delayed_provider_display?.receipt_unchanged).toBe(true)
    expect(item.delayed_provider_display?.delay_proves_chronology).toBe(false)
    await expect(page.getByTestId('delayed-provider-display')).toContainText('intentional one-second display delay')
    expect(await page.locator('.headline-price').innerText() === '₹' + currency(displayed.ltp)).toBe(true)
  } else {
    expect(item.quote.ltp).toBeUndefined()
    expect(await page.locator('.headline-price').innerText() === '₹' + currency(item.latest_close)).toBe(true)
  }
  expect(Object.keys(item.indicators).length).toBeGreaterThan(5)
  if (process.env.ALPHALENS_BROWSER_OUTPUT_DIR) writeFileSync(join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR, 'selected-eod-metadata.json'), JSON.stringify({ instrument_key: item.instrument_key, symbol: item.symbol, rows: item.rows.length, latest_eod: item.latest_session, quote_state: item.quote.state, indicative_state: item.indicative_quote?.state ?? null, delayed_display: !!item.delayed_provider_display, source_gets: source.api_calls_this_request, chart_visible: true, values_match_backend: true, market_values_retained: false }))
})
