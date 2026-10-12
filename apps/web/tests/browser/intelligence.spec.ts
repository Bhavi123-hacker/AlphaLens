import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { signIn } from './auth-setup'

// Genuine frozen archive, isolated TEST_ONLY operator. No mocked market responses.
test('archival regime, reliability and drift retain evidence gates', async ({ page }) => {
  test.setTimeout(180_000)
  await page.goto('/intelligence')
  await page.getByLabel('Intelligence timeline sessions').selectOption('2')
  await expect(page.getByRole('img', { name: 'Archival regime momentum timeline' })).toBeVisible({ timeout: 120_000 })
  await expect(page.getByText('Unknown original availability cannot become eligible knowledge')).toBeVisible()
  await page.getByRole('button', { name: 'Drift & stability', exact: true }).click()
  await expect(page.getByRole('img', { name: 'return_20 past and current archival quantiles' })).toBeVisible()
  await page.getByRole('button', { name: 'ML reliability', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Model Reliability Matrix' })).toBeVisible()
  await page.getByLabel('Reliability evidence phase').selectOption('2025')
  await page.getByLabel('Reliability metric').selectOption('brier_score')
  await expect(page.getByRole('img', { name: 'Stored calibration reliability diagram' })).toBeVisible()
  expect((await page.request.get('/api/v1/daily/predictions')).status()).toBe(503)
})

test('canonical RELIANCE passport exposes exact blockers and keyboard drawer', async ({ page }) => {
  await page.goto('/stocks/tejhq%3Aisin%3AINE002A01018')
  await expect(page.getByLabel('From', { exact: true })).toHaveValue('2025-10-06')
  await expect(page.getByLabel('To', { exact: true })).toHaveValue('2026-10-06')
  await expect(page.getByRole('heading', { name: 'AlphaLens Evidence Passport' })).toBeVisible()
  await expect(page.getByText('CURRENT SHORTLIST UNAVAILABLE')).toBeVisible()
  await page.getByLabel('Evidence blocker layer').selectOption('model')
  await expect(page.getByText('Independent model acceptance not passed')).toBeVisible()
  await page.getByRole('button', { name: 'Inspect passport details' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('dialog', { name: 'Detailed Evidence Passport' })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(result.violations).toEqual([])
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})

test('logout revokes protected intelligence without revoking other test sessions', async ({ page }) => {
  await page.context().clearCookies()
  await page.goto('/login'); await signIn(page)
  await page.goto('/intelligence')
  await page.getByRole('button', { name: 'Log out', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
  for (const path of ['regime', 'drift', 'reliability', 'passport/tejhq%3Aisin%3AINE002A01018']) {
    expect((await page.request.get(`/api/v1/intelligence/${path}`)).status()).toBe(401)
  }
})
