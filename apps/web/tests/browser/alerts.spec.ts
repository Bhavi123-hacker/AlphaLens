import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { join } from 'node:path'

test('persisted notification history filters and evidence details work with keyboard access', async ({ page }) => {
  await page.goto('/notifications')
  await expect(page.getByRole('heading', { name: 'Notifications', exact: true })).toBeVisible()
  await page.getByLabel('Severity', { exact: true }).selectOption('WARNING')
  await page.getByLabel('Category', { exact: true }).selectOption('DATA_SOURCE')
  const row = page.getByRole('button', { name: /Daily source is blocked/ }).first()
  await row.focus(); await page.keyboard.press('Enter')
  const details = page.getByRole('dialog', { name: 'Daily source is blocked' })
  await expect(details.getByText('VERIFIED_PERSISTED_EVENT')).toHaveCount(0) // Human-readable evidence status.
  await expect(details.getByText('P19', { exact: true })).toBeVisible()
  await expect(details.getByText('SOURCE_BLOCKED', { exact: true })).toHaveCount(0) // Fixed title, no raw payload.
  const enabled = (await (await page.request.get('/api/v1/alerts/preferences')).json()).data.mutations_enabled
  if (enabled) {
    const read = details.getByRole('button', { name: 'Mark read' })
    if (await read.isEnabled()) {
      await read.click()
      await expect(details.getByText('READ', { exact: true })).toBeVisible()
    }
    const acknowledge = details.getByRole('button', { name: 'Acknowledge', exact: true })
    if (await acknowledge.isEnabled()) await acknowledge.click()
    await expect(details.getByText('ACKNOWLEDGED', { exact: true })).toBeVisible()
  } else {
    await expect(details.getByRole('button', { name: 'Mark read' })).toBeDisabled()
    await expect(details.getByText(/Alert controls require explicit local operator opt-in/)).toBeVisible()
  }
  await page.keyboard.press('Escape')
  await expect(details).toHaveCount(0)
  await page.getByLabel('Search alerts').fill('UNMATCHED_P20_BROWSER_QUERY')
  await expect(page.getByText('No matching notifications', { exact: true })).toBeVisible()
  expect((await page.request.get('/api/v1/daily/signals')).status()).toBe(503)
})

test('notification preferences respect operator opt-in and external channel restrictions', async ({ page }) => {
  await page.goto('/settings')
  const response = await page.request.get('/api/v1/alerts/preferences')
  const data = (await response.json()).data
  const original = data.preferences
  if (!data.mutations_enabled) {
    await expect(page.getByRole('button', { name: 'Save notification preferences' })).toBeDisabled()
    await expect(page.getByText(/Local mutation is disabled/)).toBeVisible()
    expect(original.email).toBe(false); expect(original.desktop).toBe(false)
    return
  }
  await page.getByLabel('Deliver informational successes').check()
  await page.getByLabel('Quiet hours for INFO and WARNING (Asia/Kolkata)').check()
  await page.getByLabel('Quiet hours start', { exact: true }).fill('23:00')
  await page.getByRole('button', { name: 'Save notification preferences' }).click()
  await expect(page.getByText(/Notification preferences saved/)).toBeVisible()
  const saved = (await (await page.request.get('/api/v1/alerts/preferences')).json()).data.preferences
  expect(saved.include_info).toBe(true); expect(saved.quiet_start).toBe('23:00')
  expect(saved.email).toBe(false); expect(saved.desktop).toBe(false)
  const restore = await page.request.post('/api/v1/alerts/preferences', { headers: { Origin: process.env.ALPHALENS_BROWSER_BASE_URL ?? 'http://127.0.0.1:5173', 'X-AlphaLens-Local': 'p20', 'X-CSRF-Token': (await (await page.request.get('/api/v1/auth/session')).json()).csrf_token }, data: original })
  expect(restore.status()).toBe(200)
})

test('notification layout and controls remain accessible on desktop and mobile', async ({ page }) => {
  await page.goto('/notifications')
  await page.getByLabel('Category', { exact: true }).selectOption('DATA_SOURCE')
  await expect(page.getByRole('button', { name: /Daily source is blocked/ }).first()).toBeVisible()
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1050 })
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
    await page.screenshot({ path: join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR ?? 'test-results', `p20-notifications-${width}.png`), fullPage: true })
  }
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.getByRole('button', { name: /^Notifications,/ }).click()
  await expect(page.getByRole('dialog', { name: 'Recent notifications' })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog', { name: 'Recent notifications' })).toHaveCount(0)
})
