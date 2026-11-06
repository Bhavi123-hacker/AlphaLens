import { expect, test } from '@playwright/test'
import { randomBytes } from 'node:crypto'
import { writeFileSync } from 'node:fs'
import { credentials, signIn } from './auth-setup'

test.use({ storageState: { cookies: [], origins: [] } })
test('real password change revokes sessions and permits login only with the replacement', async ({ page }) => {
  await page.goto('/settings'); await signIn(page)
  await expect(page.getByRole('heading', { name: 'Account security' })).toBeVisible()
  const original = credentials(); const password = randomBytes(32).toString('base64url')
  await page.getByLabel('Current password', { exact: true }).fill(original.password)
  await page.getByLabel('New password', { exact: true }).fill(password)
  await page.getByLabel('Confirm new password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Change password', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
  expect((await page.request.get('/api/v1/alerts')).status()).toBe(401)
  // Keep the isolated TEST_ONLY credential receipt usable; never a Git/app credential.
  writeFileSync(process.env.ALPHALENS_BROWSER_CREDENTIAL_FILE!, JSON.stringify({ username: original.username, password }))
  await signIn(page)
  await expect(page.getByRole('heading', { name: 'Account security' })).toBeVisible()
})
