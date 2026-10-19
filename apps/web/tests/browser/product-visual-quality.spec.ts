import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'

// Genuine saved research; isolated TEST_ONLY operator. No provider acquisition.
test.use({ trace: 'off', screenshot: 'off', video: 'off', reducedMotion: 'reduce' })
const folder = () => process.env.ALPHALENS_BROWSER_OUTPUT_DIR!

test('premium dark/light research, keyboard navigation and responsive layouts remain accessible', async ({ page }) => {
  const acquisition: string[] = []
  page.on('request', request => { const path = new URL(request.url()).pathname; if (/upstox-private\/(snapshot|watchlist|reference)/.test(path)) acquisition.push(path) })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Your market workspace', exact: true })).toBeVisible()
  await expect(page.getByRole('meter', { name: 'Retained historical coverage' })).toHaveAttribute('value', '500')
  const audit: { theme: string; width: number; violations: { id: string; impact: string | null | undefined }[] }[] = []
  for (const theme of ['dark', 'light']) {
    if (theme === 'light') await page.getByRole('button', { name: /Switch to light/ }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
    for (const width of [390, 1024, 1920]) {
      await page.setViewportSize({ width, height: 1080 })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true)
    }
    await page.setViewportSize({ width: 1512, height: 1100 })
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
    audit.push({ theme, width: 1512, violations: results.violations.map(v => ({ id: v.id, impact: v.impact })) })
    writeFileSync(join(folder(), `premium-axe-${theme}.json`), JSON.stringify({ violations: results.violations.map(v => ({ id:v.id, impact:v.impact, nodes:v.nodes.map(n=>({target:n.target, checks:n.any.map(c=>({id:c.id,data:c.data}))})) })), incomplete_count:results.incomplete.length }, null, 2))
    await page.screenshot({ path: join(folder(), `premium-dashboard-${theme}.png`) })
    expect(results.violations.map(v => v.id)).toEqual([])
  }
  await page.setViewportSize({ width: 390, height: 844 })
  const open = page.getByRole('button', { name: 'Open navigation', exact: true })
  await open.click()
  await expect(page.getByRole('dialog', { name: 'Primary navigation' })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(open).toBeFocused()
  expect(acquisition).toEqual([])
  writeFileSync(join(folder(), 'premium-accessibility-metadata.json'), JSON.stringify({ audit, mobile_keyboard_escape: true, acquisition_requests: 0, private_screenshots_not_committed: true }, null, 2))
})

test('candidate evidence saves an identity to an existing isolated watchlist and keeps strategy failures visible', async ({ page, baseURL }) => {
  const session = await (await page.request.get('/api/v1/auth/session')).json()
  const headers = { Origin: new URL(baseURL!).origin, 'X-AlphaLens-Local': 'p32', 'X-CSRF-Token': session.csrf_token as string }
  const created = await page.request.post('/api/v1/personal/records/watchlists', { headers, data: { id: '', revision: 0, value: { name: 'TEST_ONLY visual acceptance', instrument_keys: [] } } })
  expect(created.status()).toBe(200)
  const id = (await created.json()).data.id as string
  try {
    await page.goto('/nse-market')
    const table = page.getByRole('table', { name: 'Expanded genuine model rankings' })
    const first = table.locator('tbody tr').first()
    await expect(first).toBeVisible()
    const savedKey = (await first.getAttribute('data-instrument-key'))!
    await first.getByRole('button', { name: 'Why this security qualifies, risks and scenarios' }).click()
    const dialog = page.getByRole('dialog').last()
    await expect(dialog.getByRole('heading', { name: 'Why it could lose money' })).toBeVisible()
    await dialog.getByText('Save to a watchlist', { exact: true }).click()
    await dialog.getByLabel('Existing watchlist').selectOption(id)
    await dialog.getByRole('button', { name: 'Save security identity' }).click()
    await expect(dialog.getByRole('status')).toContainText('Security saved privately')
    await page.screenshot({ path: join(folder(), 'premium-candidate-evidence.png') })
    await page.keyboard.press('Escape')
    const workspace = (await (await page.request.get('/api/v1/personal/workspace')).json()).data
    expect(workspace.watchlists.find((r: { id: string }) => r.id === id).value.instrument_keys).toEqual([savedKey])
    await page.getByRole('link', { name: '03 Compare evidence' }).click()
    const economics = page.getByRole('table', { name: 'Model Top 5 economics at registered costs' })
    await expect(economics).toBeVisible()
    await expect(economics).toContainText('-44.98%')
    await expect(economics).toContainText('-31.77%')
    await expect(page.getByRole('heading', { name: 'Original V2 · a separate evaluation' })).toBeVisible()
    await page.getByRole('link', { name: '04 Follow daily updates' }).click()
    await expect(page.getByText('Fresh-session capture PENDING', { exact: true })).toBeVisible()
    await expect(page.getByText(/Interrupted; not a successful capture/)).toBeVisible()
    writeFileSync(join(folder(), 'premium-candidate-metadata.json'), JSON.stringify({ saved_exact_identity: true, isolated_watchlist: true, negative_cost_evidence_preserved: true, next_session_pending: true, original_records_modified: false, price_bodies_retained: false }, null, 2))
  } finally {
    const workspace = (await (await page.request.get('/api/v1/personal/workspace')).json()).data
    const list = workspace.watchlists.find((r: { id: string }) => r.id === id)
    if (list) expect((await page.request.post(`/api/v1/personal/records/watchlists/${id}/remove`, { headers, data: { revision: list.revision } })).status()).toBe(200)
  }
})
