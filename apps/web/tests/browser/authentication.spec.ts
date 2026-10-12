import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { execFileSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { credentials, signIn } from './auth-setup'

test.use({ storageState: { cookies: [], origins: [] } })
test('real login, refresh and logout enforce research and notification privacy', async ({ page }) => {
  await page.goto('/notifications')
  await expect(page).toHaveURL(/login$/)
  expect((await page.request.get('/api/v1/alerts')).status()).toBe(401)
  await signIn(page)
  await expect(page.getByRole('heading', { name: 'Notifications', exact: true })).toBeVisible()
  const cookie = (await page.context().cookies()).find((c) => c.name === 'alphalens_session')
  expect(cookie?.httpOnly).toBe(true); expect(cookie?.sameSite).toBe('Strict'); expect(cookie?.secure).toBe(false)
  await page.reload()
  await page.getByLabel('Category', { exact: true }).selectOption('DATA_SOURCE')
  await expect(page.getByRole('button', { name: /Daily source is blocked/ }).first()).toBeVisible()
  expect((await page.request.get('/api/v1/daily/predictions')).status()).toBe(503)
  await page.goto('/settings'); await page.getByRole('button', { name: 'Log out' }).click()
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
  expect((await page.request.get('/api/v1/alerts')).status()).toBe(401)
  await page.goBack(); await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
  expect((await page.request.get('/api/v1/daily/forecasts')).status()).toBe(401)
  expect((await page.request.get('/api/v1/daily/prospective/status')).status()).toBe(401)
  expect(await page.evaluate(() => Object.keys(localStorage).some((k) => /session|csrf|password|token/i.test(k)))).toBe(false)
})

test('real invalid login is generic and keyboard login works', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Username').fill(credentials().username)
  await page.getByLabel('Password', { exact: true }).fill('TEST_ONLY invalid password value')
  await page.getByRole('button', { name: 'Show password' }).click()
  await expect(page.getByLabel('Password', { exact: true })).toHaveAttribute('type', 'text')
  await page.getByLabel('Password', { exact: true }).press('Enter')
  await expect(page.getByRole('alert')).toHaveText(/Sign-in failed/)
  await expect(page.getByLabel('Password', { exact: true })).toHaveValue('')
  await signIn(page); await expect(page.getByRole('heading', { name: 'Research overview', exact: true })).toBeVisible()
})

test('server-side revoked session redirects to login and conceals cached private pages', async ({ page }) => {
  await page.goto('/research'); await signIn(page)
  await expect(page.getByRole('heading', { name: 'ML research lab', exact: true })).toBeVisible()
  const session = await (await page.request.get('/api/v1/auth/session')).json()
  const revoked = await page.request.post('/api/v1/auth/sessions/revoke', {
    headers: { Origin: process.env.ALPHALENS_BROWSER_BASE_URL ?? 'http://127.0.0.1:5173', 'X-CSRF-Token': session.csrf_token }, data: { session_id: session.session_id },
  })
  expect(revoked.status()).toBe(200)
  await page.goto('/notifications')
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'ML research lab', exact: true })).toHaveCount(0)
})

test('login is responsive, keyboard accessible and supports reduced motion', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
  await page.emulateMedia({ reducedMotion: 'reduce' })
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  }
  await page.getByLabel('Username').focus(); await page.keyboard.press('Tab')
  await expect(page.getByLabel('Password', { exact: true })).toBeFocused()
})

test('account session inspection and revocation work through authenticated UI', async ({ page }) => {
  await page.goto('/settings'); await signIn(page)
  await page.getByRole('button', { name: 'Inspect sessions' }).click()
  const item = page.locator('.session-list li').filter({ hasText: 'Current session' })
  await expect(item).toContainText('Active')
  await item.getByRole('button', { name: 'Revoke session' }).click()
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
  expect((await page.request.get('/api/v1/paper/accounts')).status()).toBe(401)
})

test('actual expired server session removes private history on the next read', async ({ page }) => {
  await page.goto('/notifications'); await signIn(page)
  await expect(page.getByRole('heading', { name: 'Notifications', exact: true })).toBeVisible()
  const session = await (await page.request.get('/api/v1/auth/session')).json()
  const root = process.env.ALPHALENS_BROWSER_AUTH_ROOT ?? dirname(process.env.ALPHALENS_BROWSER_CREDENTIAL_FILE!)
  const normalized = root.replaceAll('\\', '/')
  if (!normalized.includes('/TEST_ONLY_browser_auth') && !normalized.endsWith('/p22-p25-runtime/platform-test/auth') && !normalized.endsWith('/final-completion-runtime/TEST_ONLY_platform/auth')) throw new Error('Expiry injection requires isolated TEST_ONLY auth storage')
  // Only the isolated test session's expiration changes. No token or market input.
  execFileSync(resolve('../../.venv/Scripts/python.exe'), ['-c',
    'import sys; from pathlib import Path; from alphalens_api.auth.store import AuthStore; s=AuthStore(Path(sys.argv[1])); c=s.connection(write=True); db=c.__enter__(); db.execute("UPDATE sessions SET absolute_expires=0 WHERE session_id=?",(sys.argv[2],)); c.__exit__(None,None,None)',
    root, session.session_id], { stdio: 'pipe' })
  await page.getByRole('link', { name: 'Settings', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Account security' })).toHaveCount(0)
})

test('logout clears another open tab without leaving cached research visible', async ({ page, context }) => {
  await page.goto('/settings'); await signIn(page)
  const other = await context.newPage()
  await other.goto('/notifications')
  await expect(other.getByRole('heading', { name: 'Notifications', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Log out' }).click()
  await expect(other.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
  await expect(other.getByRole('heading', { name: 'Notifications', exact: true })).toHaveCount(0)
})
