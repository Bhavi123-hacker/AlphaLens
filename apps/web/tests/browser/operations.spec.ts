import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('deployed monitoring shows real measurements and preserves source restrictions', async ({ page }) => {
  await page.goto('/data-health')
  await expect(page.getByRole('heading', { name: 'Local system monitoring', exact: true })).toBeVisible()
  const status = await page.request.get('/api/v1/operations/status')
  expect(status.status()).toBe(200)
  const data = (await status.json()).data
  expect(data.components.authentication.status).toBe('HEALTHY')
  expect(data.components.catalog.observed_identities).toBeGreaterThan(0)
  expect(data.components.live_source.status).toBe('BLOCKED_BY_POLICY')
  expect(data.production_ready).toBe(false)
  expect(data.components.storage.free_bytes).toBeGreaterThan(0)
  const metrics = (await (await page.request.get('/api/v1/operations/metrics')).json()).data
  expect(Object.values(metrics.requests).some((f) => (f as { count: number }).count > 0)).toBe(true)
  await page.getByRole('button', { name: 'Refresh system status', exact: true }).click()
  await expect(page.getByText(/Blocked by policy/i).first()).toBeVisible()
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1050 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  }
  const shell = await page.request.get('/login')
  expect(shell.headers()['content-security-policy']).toContain("script-src 'self'")
  expect((await page.request.get('/api/v1/nonexistent')).status()).toBe(404)
  expect((await page.request.get('/.env')).status()).toBe(404)
})
