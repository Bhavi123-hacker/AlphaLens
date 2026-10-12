import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { signIn } from './auth-setup'

// Real persisted archive + isolated TEST_ONLY operator, no provider price calls/mock responses.
test('six-provider comparison retains blockers and genuine archive date', async ({ page }) => {
  await page.goto('/settings')
  await expect(page.getByRole('heading', { name: 'NSE provider comparison' })).toBeVisible()
  await expect(page.getByRole('article')).toHaveCount(6)
  await expect(page.getByRole('article', { name: 'TejHQ readiness' })).toContainText('2026-10-06')
  await expect(page.getByRole('article', { name: 'Alpha Vantage readiness' })).toContainText('BSE')
  await page.getByLabel('Compare provider').selectOption('upstox')
  await page.getByLabel('Provider capacity scenario').selectOption('500')
  await expect(page.getByRole('article')).toHaveCount(1)
  await expect(page.getByRole('article', { name: 'Upstox readiness' })).toContainText('500')
  await expect(page.getByText('Daily ML research remains blocked')).toBeVisible()
  const result = await page.request.get('/api/v1/providers/comparison')
  expect(result.status()).toBe(200)
  expect((await result.json()).data.collection_enabled).toBe(false)
})

test('provider controls are keyboard accessible and mobile layout fits', async ({ page }) => {
  await page.goto('/settings')
  await expect(page.getByRole('article')).toHaveCount(6)
  await page.getByLabel('Compare provider').focus()
  await page.keyboard.press('i'); await page.keyboard.press('Enter')
  await expect(page.getByRole('article')).toHaveCount(1)
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()
  expect(result.violations).toEqual([])
})

test('provider diagnostics reject access after logout', async ({ page }) => {
  // Revoke a separate session, preserving the shared setup session for later files.
  await page.context().clearCookies()
  await page.goto('/login')
  await signIn(page)
  await page.goto('/settings')
  await page.getByRole('button', { name: 'Log out', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
  expect((await page.request.get('/api/v1/providers/comparison')).status()).toBe(401)
})
