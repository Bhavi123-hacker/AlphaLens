import { test, expect } from '@playwright/test'
import { writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'

// Genuine read-only provider request; isolated TEST_ONLY authentication, no interception.
test('private RELIANCE candles, indicators and exact feature exclusions render', async ({ page }) => {
  await page.goto('/stocks/tejhq%3Aisin%3AINE002A01018')
  const load = page.getByRole('button', { name: 'Load private RELIANCE candles' })
  await expect(load).toBeVisible()
  const replyPromise = page.waitForResponse(r => r.url().endsWith('/providers/upstox-private/reliance'))
  await load.click()
  const reply = await replyPromise
  expect(reply.status()).toBe(200)
  expect(reply.headers()['cache-control']).toContain('no-store')
  const envelope = await reply.json()
  const data = envelope.data
  expect(data.state).toBe('AVAILABLE_PRIVATE_TRANSIENT')
  expect(data.instrument_key).toBe('NSE_EQ|INE002A01018')
  expect(data.retained).toBe(false)
  expect(data.price_basis).toBe('UNKNOWN')
  expect(data.passport.historical_archive_joined).toBe(false)
  expect(data.rows.length).toBeGreaterThan(200)
  expect(Object.keys(data.indicators)).toHaveLength(6)
  expect(data.feature_readiness.required_count).toBe(38)
  expect(data.feature_readiness.model_eligible_count).toBe(0)
  expect(data.feature_readiness.prospective_forecasts).toBe(0)
  writeFileSync(join(dirname(process.env.ALPHALENS_BROWSER_CREDENTIAL_FILE!), 'private-verification.json'), JSON.stringify({ state: data.state, exchange: 'NSE', instrument_key: data.instrument_key, observed_candle_dates: data.rows.length, earliest_session: data.rows[0].session, latest_session: data.latest_session, descriptive_features: data.feature_readiness.descriptive_available_count, model_eligible_features: 0, prospective_forecasts: 0, price_values_retained: false }))
  await expect(page.getByRole('img', { name: new RegExp(`Private Upstox RELIANCE NSE daily candles ending ${data.latest_session}`) })).toBeVisible()
  await page.getByRole('group', { name: 'Private provider date range' }).getByRole('button', { name: '5Y', exact: true }).click()
  await page.getByText('Provider Evidence Passport', { exact: true }).click()
  await expect(page.getByText('NSE_EQ|INE002A01018', { exact: true })).toBeVisible()
  await page.getByText('Current model feature readiness', { exact: true }).click()
  await expect(page.getByRole('cell', { name: 'momentum_percentile_20', exact: true })).toBeVisible()
  await page.goto('/screener')
  await page.getByRole('button', { name: 'Load private watchlist metrics' }).click()
  await expect(page.getByRole('region', { name: 'Private provider watchlist heatmap and screener' })).toBeVisible()
  await page.getByLabel('Private watchlist minimum volume').fill('999999999999')
  await expect(page.getByText('0 private watchlist matches', { exact: true })).toBeVisible()
  await page.getByLabel('Private watchlist minimum volume').fill('')
  await expect(page.getByText('1 private watchlist matches', { exact: true })).toBeVisible()
  // Deliberately no screenshot or provider body persisted by this test.
})
