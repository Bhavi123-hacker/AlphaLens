import { test, expect } from '@playwright/test'
import { signIn } from './auth-setup'

// Genuine selected RELIANCE regression, no interception or retained provider body.
process.env.PLAYWRIGHT_NO_COPY_PROMPT = '1'
test.use({ trace: 'off', screenshot: 'off', video: 'off' })
test.beforeEach(async ({ page }) => { await page.context().clearCookies(); await page.goto('/login'); await signIn(page) })
test('private RELIANCE uses the reusable primary provider chart and preserves inference gates', async ({ page }) => {
  await page.goto('/analysis')
  await page.getByLabel('Search current NSE master', { exact: true }).fill('RELIANCE')
  await page.getByRole('button', { name: 'Find NSE equity', exact: true }).click()
  await page.getByRole('button').filter({ has: page.locator('strong', { hasText: /^RELIANCE$/ }) }).click()
  const pending = page.waitForResponse(r => r.url().includes('/upstox-private/snapshot?'))
  await page.getByRole('button', { name: 'Load Upstox observations', exact: true }).click()
  const reply = await pending
  expect(reply.status()).toBe(200); expect(reply.headers()['cache-control']).toContain('no-store')
  const data = (await reply.json()).data.items[0]
  expect(data.state).toBe('AVAILABLE_PRIVATE_TRANSIENT'); expect(data.symbol).toBe('RELIANCE')
  expect(data.instrument_key).toBe('NSE_EQ|' + data.identity.isin)
  expect(data.retained).toBe(false); expect(data.price_basis).toBe('UNKNOWN')
  expect(data.passport.historical_archive_joined).toBe(false)
  expect(data.passport.current_inference).toBe('UNAVAILABLE')
  expect(data.rows.length).toBeGreaterThan(200); expect(Object.keys(data.indicators)).toHaveLength(12)
  await expect(page.getByRole('img', { name: `Upstox RELIANCE daily OHLCV ending ${data.latest_session}` })).toBeVisible()
  await page.getByText('Source, identity and clock evidence', { exact: true }).click()
  await expect(page.getByText('UNKNOWN · no archive merge', { exact: true })).toBeVisible()
  expect((await page.request.get('/api/v1/daily/predictions')).status()).toBe(503)
})
