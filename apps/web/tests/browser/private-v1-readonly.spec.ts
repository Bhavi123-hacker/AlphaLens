import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { credentials } from './auth-setup'

// Actual saved-data deployment only. Auth sessions are owned test actions;
// financial records, providers, models and scheduler state are never mutated.
test('private V1 routes, responsive navigation, accessibility and auth boundaries', async ({ browser, baseURL }) => {
  test.skip(process.env.ALPHALENS_PRIVATE_V1_BROWSER !== '1', 'Requires actual private release')
  test.setTimeout(600_000)
  const context = await browser.newContext({ baseURL, storageState: { cookies: [], origins: [] }, viewport: { width: 1600, height: 1000 }, reducedMotion: 'reduce' })
  const page = await context.newPage()
  const errors: string[] = [], consoleErrors: string[] = [], forbidden: string[] = [], serverErrors: string[] = []
  const expectedAuthRejections: string[] = []
  let unsignedBoundary = true
  const routes: { route: string; title: string; widths: number[] }[] = []
  const accessibility: { route: string; violations: string[] }[] = []
  await page.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url())
    if (url.origin !== new URL(baseURL!).origin || url.searchParams.get('refresh') === 'true'
      || url.pathname.includes('upstox-private')
      || (!['GET', 'HEAD'].includes(request.method()) && !url.pathname.startsWith('/api/v1/auth/'))) {
      forbidden.push(`${request.method()} ${url.pathname}`); return route.abort()
    }
    return route.continue()
  })
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => {
    if (message.type() !== 'error') return
    // The intentional unsigned session check returns 401; retain its evidence.
    // Every other console error, including provider/status failures, still fails.
    const url = new URL(message.location().url || '/', baseURL)
    if (unsignedBoundary && url.origin === new URL(baseURL!).origin && url.pathname === '/api/v1/auth/session'
      && message.text() === 'Failed to load resource: the server responded with a status of 401 (Unauthorized)') {
      expectedAuthRejections.push(message.text())
    } else consoleErrors.push(message.text())
  })
  page.on('response', response => { if (response.status() >= 500) serverErrors.push(new URL(response.url()).pathname) })
  try {
    expect((await page.request.get(`${baseURL}/api/v1/nse-market/research`)).status()).toBe(401)
    await page.goto('/notifications')
    await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
    expect(new URL(page.url()).pathname).toBe('/login')
    const value = credentials()
    await page.getByLabel('Username', { exact: true }).fill(value.username)
    await page.getByLabel('Password', { exact: true }).fill(value.password)
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toHaveCount(0)
    unsignedBoundary = false
    const cookie = (await context.cookies()).find(value => value.name === 'alphalens_session')
    expect(cookie?.httpOnly).toBe(true); expect(cookie?.sameSite).toBe('Strict')
    for (const route of ['/', '/nse-market', '/watchlists', '/my-portfolio', '/preferences', '/journal',
      '/decision-desk', '/notifications', '/research-alerts', '/research', '/backtests', '/portfolios',
      '/paper', '/data-health', '/settings', '/opportunities', '/experimental-ai', '/experimental-ai-v2',
      '/intelligence', '/copilot', '/heatmap', '/screener', '/compare']) {
      await page.goto(route)
      const heading = page.locator('main h1').first()
      await expect(heading).toBeVisible({ timeout: 120_000 })
      expect((await heading.innerText()).trim().length).toBeGreaterThan(0)
      const widths: number[] = []
      for (const width of [1600, 1366, 768, 390, 320]) {
        await page.setViewportSize({ width, height: 1000 })
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${route} width=${width}`).toBe(true)
        widths.push(width)
      }
      routes.push({ route, title: await heading.innerText(), widths })
    }
    for (const route of ['/nse-market', '/settings', '/watchlists', '/my-portfolio']) {
      await page.setViewportSize({ width: 1366, height: 1000 })
      await page.goto(route)
      await expect(page.locator('main h1').first()).toBeVisible()
      const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
      accessibility.push({ route, violations: audit.violations.map(row => row.id) })
      expect(audit.violations.map(row => row.id), route).toEqual([])
    }
    await page.setViewportSize({ width: 390, height: 844 })
    const navigation = page.getByRole('button', { name: 'Open navigation', exact: true })
    await navigation.click()
    await expect(page.getByRole('dialog', { name: 'Primary navigation' })).toBeVisible()
    await page.keyboard.press('Escape'); await expect(navigation).toBeFocused()
    const session = await (await page.request.get(`${baseURL}/api/v1/auth/session`)).json() as { csrf_token: string }
    const headers = { Origin: new URL(baseURL!).origin, 'X-AlphaLens-Local': 'p21' }
    expect((await page.request.post(`${baseURL}/api/v1/auth/logout`, { headers, data: {} })).status()).toBe(403)
    expect((await page.request.post(`${baseURL}/api/v1/auth/logout`, { headers: { ...headers, Origin: 'https://untrusted.invalid', 'X-CSRF-Token': session.csrf_token }, data: {} })).status()).toBe(403)
    expect((await page.request.get(`${baseURL}/api/v1/auth/session`)).status()).toBe(200)
    await page.reload(); await expect(page.locator('main h1').first()).toBeVisible()
    expect((await page.request.post(`${baseURL}/api/v1/auth/logout`, { headers: { ...headers, 'X-CSRF-Token': session.csrf_token }, data: {} })).status()).toBe(200)
    expect((await page.request.get(`${baseURL}/api/v1/nse-market/research`)).status()).toBe(401)
    expect(errors).toEqual([]); expect(consoleErrors).toEqual([]); expect(serverErrors).toEqual([]); expect(forbidden).toEqual([])
  } finally {
    const output = process.env.ALPHALENS_BROWSER_OUTPUT_DIR
    if (output) writeFileSync(join(output, 'private-v1-routes.json'), JSON.stringify({ routes, accessibility, errors, consoleErrors, expectedAuthRejections, forbidden, serverErrors }, null, 2))
    await context.close()
  }
})
