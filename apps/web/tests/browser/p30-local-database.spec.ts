import { test, expect } from '@playwright/test'
import { signIn } from './auth-setup'

// Acquire an actual session per case; earlier long suites can revoke the setup session.
test.use({ trace: 'off', screenshot: 'off', video: 'off' })
test.beforeEach(async ({ page }) => {
  await page.context().clearCookies()
  await page.goto('/login')
  await signIn(page)
})

test('owned local PostgreSQL has genuine empty read paths and no financial writes', async ({ page }) => {
  for (const [route, api, title] of [
    ['/portfolios', '/api/v1/portfolios', 'No portfolio records'],
    ['/paper', '/api/v1/paper/accounts', 'No paper accounts recorded'],
  ]) {
    await page.goto(route)
    await expect(page.getByText(title, { exact: true })).toBeVisible()
    const reply = await page.request.get(api)
    expect(reply.status()).toBe(200)
    expect((await reply.json()).data).toEqual([])
    expect(reply.headers()['cache-control']).toContain('no-store')
    await expect(page.getByRole('button', { name: /place order|buy|sell/i })).toHaveCount(0)
    expect((await page.request.post(api, { data: {} })).status()).toBe(405)
  }
})
