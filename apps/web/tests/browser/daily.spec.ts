import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { join } from 'node:path'

test('actual P19 receipt status stays blocked and accessible on desktop and mobile', async ({ page }) => {
  await page.goto('/data-health')
  await expect(page.getByText('Daily activation blocked', { exact: true })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: 'Evidence blockers', exact: true })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'Historical replay', exact: true }).first()).toBeVisible()
  await expect(page.getByText('2026-10-06', { exact: true }).first()).toBeVisible()
  expect((await page.request.get('/api/v1/daily/predictions')).status()).toBe(503)
  await expect(page.getByRole('heading', { name: 'Prospective research', exact: true })).toBeVisible()
  await expect(page.getByText('Daily shortlist unavailable', { exact: true })).toBeVisible()
  const prospective = (await (await page.request.get('/api/v1/daily/prospective/status')).json()).data
  expect(prospective.forecasts).toBe(0)
  if (prospective.configured) expect(prospective.metrics.forecasts).toBe(0)
  else expect(prospective.metrics).toBeNull()
  expect((await (await page.request.get('/api/v1/daily/forecasts')).json()).page.total).toBe(0)
  await page.screenshot({ path: join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR ?? 'test-results', 'p19-data-health-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  const accessibility = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(accessibility.violations).toEqual([])
  await page.screenshot({ path: join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR ?? 'test-results', 'p19-data-health-mobile.png'), fullPage: true })
})
